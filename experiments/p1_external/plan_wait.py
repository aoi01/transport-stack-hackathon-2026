"""事前計画（リアルタイムを使わない）の待ち時間と、土曜を分ける効果。

比べる待ち時間（検証週 10/25〜31 の 3,000 件、results/p1_wait_samples.csv。学習は 10/1〜24 だけ）:
  W0   今の事前計画: 路線 × 平日/休日 × 時間帯 の実際の到着間隔 H から E[H²]/(2E[H])
  W11  実際の通過の時刻表: 学習期間の同じ日の種類の各日に、乗車停留所をバスが実際に通った時刻を並べ、
       「出発時刻以降、次のバスまでの時間」を日ごとに出して中央値（3 日分以上。無ければ W0）
  W12  W0 と W11 の平均
日の種類: 2 分類（平日 / 土日・祝日）と 3 分類（平日 / 土曜 / 日曜・祝日）。
土曜は日曜より道が混み（区間所要時間がいつもの 1.04〜1.08 倍）、待ち時間の誤差も土曜が最大だった（14 章）。
使い方: python -X utf8 experiments/p1_external/plan_wait.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.improve_wait import headway_samples  # noqa: E402
from tsh.traveltime import passages_glob  # noqa: E402


def dt2(d):
    return C.day_type(d)


def dt3(d):
    if d in C.HOLIDAYS or d.weekday() == 6:
        return "sunday"
    return "saturday" if d.weekday() == 5 else "weekday"


def main():
    w = pd.read_csv(C.ROOT / "results" / "p1_wait_samples.csv", parse_dates=["depart"], dtype={"route_id": str})
    w["aw"] = w.actual_wait.clip(lower=30)
    w["date"] = w.depart.dt.date
    keys = w[["route_id", "i"]].drop_duplicates()
    con = C.connect()
    k2 = keys.assign(route_id=keys.route_id.astype(int))
    con.register("keys", k2)
    ps = con.execute(f"""
        SELECT CAST(p.route_id AS VARCHAR) AS route_id, p.seq AS i, p.date,
               hour(timezone('{C.TZ}', p.ts)) * 3600 + minute(timezone('{C.TZ}', p.ts)) * 60 + second(timezone('{C.TZ}', p.ts)) AS sec
        FROM read_parquet({passages_glob(C.TRAIN_DAYS)}) p JOIN keys k ON k.route_id = p.route_id AND k.i = p.seq""").df()
    ps["date"] = pd.to_datetime(ps.date).dt.date
    days_pass = {k: [np.sort(g.sec.to_numpy()) for _, g in gg.groupby("date")] for k, gg in ps.groupby(["route_id", "i"])}
    day_of = {k: sorted(gg.date.unique()) for k, gg in ps.groupby(["route_id", "i"])}
    by_key_day = {(k[0], k[1], d): np.sort(g.sec.to_numpy()) for k, gg in ps.groupby(["route_id", "i"]) for d, g in gg.groupby("date")}
    hw = headway_samples(C.TRAIN_DAYS)          # route_id, day_type, hr, hw（2 分類）
    # 3 分類の到着間隔: headway_samples は日付を返さないので、土曜を分けた版は通過の時刻表から作る
    res = {}
    for name, f in [("2分類", dt2), ("3分類", dt3)]:
        w0, w11 = [], []
        # W0（3 分類）: 停留所 i の通過間隔から E[H²]/(2E[H])（同じ日の種類・時間帯）
        for r in w.itertuples():
            kind = f(r.date)
            sec = r.depart.hour * 3600 + r.depart.minute * 60 + r.depart.second
            gaps, hws = [], []
            for d in day_of.get((r.route_id, r.i), []):
                if f(d) != kind:
                    continue
                x = by_key_day[(r.route_id, r.i, d)]
                nxt = x[x >= sec]
                if len(nxt) and nxt[0] - sec <= 4 * 3600:
                    gaps.append(nxt[0] - sec)
                h = np.diff(x)
                hr_mask = (x[:-1] // 3600) == r.depart.hour
                hws.extend(h[hr_mask & (h >= 120) & (h <= 4 * 3600)])
            hws = np.asarray(hws, float)
            w0.append(float((hws ** 2).mean() / (2 * hws.mean())) if len(hws) >= 5 else np.nan)
            w11.append(float(np.median(gaps)) if len(gaps) >= 3 else np.nan)
        res[name] = (np.asarray(w0), np.asarray(w11))
    base = w.W0.to_numpy()                          # 今の API の W0（基準停留所の到着間隔、2 分類）

    def st(p, a, mask=None):
        p = np.where(np.isnan(p), base, p)
        e = (p - a) / a
        if mask is not None:
            e = e[mask]
        return f"MedAPE {np.median(np.abs(e)) * 100:5.1f}%  符号 {np.median(e) * 100:+6.1f}%"
    a = w.aw.to_numpy()
    sat = (w.depart.dt.weekday == 5).to_numpy()
    sun = (w.depart.dt.weekday == 6).to_numpy()
    print(f"全体 {len(w)} 件（土曜 {sat.sum()}・日曜 {sun.sum()}）")
    print(f"  今の W0（API）            全体 {st(base, a)} | 土曜 {st(base, a, sat)} | 日曜 {st(base, a, sun)}")
    for name, (w0, w11) in res.items():
        print(f"  W0 停留所の間隔（{name}）  全体 {st(w0, a)} | 土曜 {st(w0, a, sat)} | 日曜 {st(w0, a, sun)}")
        print(f"  W11 通過の時刻表（{name}） 全体 {st(w11, a)} | 土曜 {st(w11, a, sat)} | 日曜 {st(w11, a, sun)}")
        w12 = np.where(np.isnan(w11), base, 0.5 * np.where(np.isnan(w0), base, w0) + 0.5 * w11)
        print(f"  W12 平均（{name}）         全体 {st(w12, a)} | 土曜 {st(w12, a, sat)} | 日曜 {st(w12, a, sun)}")
    # ブートストラップ: W11（3分類）と W11（2分類）の、今の W0 との差
    rng = np.random.default_rng(0)
    eb = np.abs(base - a) / a
    for name in res:
        p = np.where(np.isnan(res[name][1]), base, res[name][1])
        e = np.abs(p - a) / a
        d = [np.median(e[k]) - np.median(eb[k]) for k in (rng.integers(0, len(a), len(a)) for _ in range(1000))]
        print(f"W11（{name}） − 今の W0: {np.median(e) * 100 - np.median(eb) * 100:+.1f} ポイント（95% 区間 {np.percentile(d, 2.5) * 100:+.1f}〜{np.percentile(d, 97.5) * 100:+.1f}）")
    w.assign(W11_2=res["2分類"][1], W11_3=res["3分類"][1]).to_csv(Path(__file__).parent / "out_plan_wait.csv", index=False)


if __name__ == "__main__":
    main()
