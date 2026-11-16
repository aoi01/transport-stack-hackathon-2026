"""試す順番 3: 近くにバスが見えない場面の待ち時間を、「時刻表の始発便 × 実際に走る確率」で出す。

今の方式（W2）: 乗車停留所を最後のバスが通ってからの経過時間 e で条件づけた、運行間隔の残り E[H − e | H > e]。
新しい方式（W7）: 手前にも折り返しにもバスが見えない ＝ 次のバスはまだ始発を出ていない、とみなす。
  - 時刻表（GTFS v32、全日同じ）の始発停留所の発車時刻 d_k
  - その便が実際に走る確率 p（路線 × 平日/休日 × 時間帯ごと、学習期間 10/1〜24 の GPS で走った便 ÷ 時刻表の便）
  - 始発から乗車停留所までの所要時間 T（学習期間の区間の過去の値の合計、tsh.traveltime）
  E[待ち] = Σ_k P(最初に走るのが k 番目) × (d_k + T − 今)、P = p_k Π_{m<k}(1 − p_m)
  （今より前に出た便は、走っていれば見えているはずなので候補にしない）
W8 = W2 と W7 の平均。
W9（実際の発車の時刻表）: 時刻表の代わりに、学習期間の同じ平日/休日の各日に GPS で始発付近（seq ≤ 3）を出た時刻を使う。
  各日について「今」以降の最初の発車までの時間を出し、その中央値 + T。W10 = W2 と W9 の平均。
  （2026-11-17 の結果: GTFS の時刻表は実際の発車と合わず W7 は大きく外れた。時刻表の時間帯の 24% では便がほとんど走っていない）比べるのは results/p1_wait_samples.csv の「どちらも見えない」541 件と、採用した方式全体（3,000 件）。
使い方: python -X utf8 experiments/p1_external/missing_trips.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.traveltime import TravelTimeModel, passages_glob  # noqa: E402


def run_prob() -> dict:
    """路線 × 平日/休日 × 時間帯 の「時刻表の便のうち GPS で走った割合」（学習期間）。"""
    con = C.connect()
    con.register("daytypes", pd.DataFrame({"date": C.TRAIN_DAYS, "day_type": [C.day_type(d) for d in C.TRAIN_DAYS]}))
    g = con.execute(f"""
        WITH t AS (SELECT date, vehicle_id, trip_id, route_id, min(ts) AS t0, min(seq) AS s0
                   FROM read_parquet({passages_glob(C.TRAIN_DAYS)}) GROUP BY ALL HAVING max(seq) - min(seq) >= 5)
        SELECT CAST(route_id AS VARCHAR) AS route_id, dt.day_type, hour(timezone('{C.TZ}', t0)) AS hr, count(*) AS runs
        FROM t JOIN daytypes dt USING (date) WHERE s0 <= 3 GROUP BY ALL""").df()
    nd = pd.Series([C.day_type(d) for d in C.TRAIN_DAYS]).value_counts().to_dict()
    sch = pd.read_parquet(C.PROCESSED / "schedule.parquet")
    first = sch[sch.seq == 0].assign(hr=lambda d: (d.t_s // 3600) % 24)
    plan = first.groupby(["route_id", "hr"]).size().rename("plan").reset_index()
    out = {}
    for dt in ("weekday", "weekend"):
        x = plan.merge(g[g.day_type == dt], on=["route_id", "hr"], how="left").fillna({"runs": 0})
        x["p"] = (x.runs / (x.plan * nd[dt])).clip(0.05, 1.0)
        out.update({(r, dt, h): p for r, h, p in zip(x.route_id, x.hr, x.p)})
    return out, first


def actual_departures() -> dict:
    """（路線, 平日/休日）→ {日付: 始発付近を出た時刻（その日の 0 時からの秒）の並び}（学習期間の GPS）。"""
    con = C.connect()
    g = con.execute(f"""
        WITH t AS (SELECT date, vehicle_id, trip_id, route_id, min(ts) AS t0, min(seq) AS s0
                   FROM read_parquet({passages_glob(C.TRAIN_DAYS)}) GROUP BY ALL HAVING max(seq) - min(seq) >= 5)
        SELECT CAST(route_id AS VARCHAR) AS route_id, date,
               hour(timezone('{C.TZ}', t0)) * 3600 + minute(timezone('{C.TZ}', t0)) * 60 + second(timezone('{C.TZ}', t0)) AS sec
        FROM t WHERE s0 <= 3""").df()
    out = {}
    for (r, d), x in g.groupby(["route_id", "date"]):
        dd = pd.Timestamp(d).date()
        out.setdefault((r, C.day_type(dd)), {})[dd] = np.sort(x.sec.to_numpy())
    return out


def _compute():
    tt = TravelTimeModel("train")
    pr, first = run_prob()
    act = actual_departures()
    deps = {r: np.sort(g.t_s.to_numpy() % 86400) for r, g in first.groupby("route_id")}
    w = pd.read_csv(C.ROOT / "results" / "p1_wait_samples.csv", parse_dates=["depart"], dtype={"route_id": str})
    w["adopt"] = np.where(w.up, w.W1, np.where(w.chain, 0.5 * w.W4 + 0.5 * w.W2, w.W2))
    w7, w9 = [], []
    for r in w.itertuples():
        rid, dep = r.route_id, r.depart
        dt = C.day_type(dep.date())
        now = dep.hour * 3600 + dep.minute * 60 + dep.second
        ids, cum = tt.stop_ids.get(rid), tt.cum.get(rid)
        d = deps.get(rid)
        if ids is None or d is None or r.i >= len(ids):
            w7.append(np.nan); w9.append(np.nan); continue
        gaps = [x[x >= now][0] - now for x in act.get((rid, dt), {}).values() if (x >= now).any() and x[x >= now][0] - now <= 4 * 3600]
        T = sum(tt.link_sec(ids[k], ids[k + 1], cum[k + 1] - cum[k], dt, (dep.hour + int(k > 0)) % 24) for k in range(r.i))
        cand = np.concatenate([d[d >= now], d + 86400])[:30]
        surv, ew, mass = 1.0, 0.0, 0.0
        for dk in cand:
            p = pr.get((rid, dt, int(dk // 3600) % 24), 0.5)
            ew += surv * p * (dk + T - now); mass += surv * p; surv *= (1 - p)
            if surv < 1e-3:
                break
        w7.append(ew / mass if mass > 0 else np.nan)
        w9.append(np.median(gaps) + T if len(gaps) >= 3 else np.nan)
    w["W7"] = w7
    w["W9"] = w9
    w["W9"] = w.W9.fillna(w.W2)
    w["W10"] = 0.5 * w.W2 + 0.5 * w.W9
    w["W7"] = w.W7.fillna(w.W2)
    w["W8"] = 0.5 * w.W2 + 0.5 * w.W7
    w["aw"] = w.actual_wait.clip(lower=30)
    return w


def main():
    w = _compute()

    def st(p, a):
        e = (p - a) / a
        return f"MedAPE {np.median(np.abs(e)) * 100:5.1f}%  符号 {np.median(e) * 100:+6.1f}%  MAE {np.mean(np.abs(p - a)) / 60:5.1f} 分"
    nv = w[~w.up & ~w.chain]
    print(f"どちらも見えない {len(nv)} 件")
    for k in ["W2", "W7", "W8", "W9", "W10"]:
        print(f"  {k}: {st(nv[k], nv.aw)}")
    print("全体（見えない層だけ差し替え）")
    for k in ["W2", "W7", "W8", "W9", "W10"]:
        p = np.where(~w.up & ~w.chain, w[k], w.adopt)
        print(f"  {k}: {st(p, w.aw)}")
    # 折り返しだけ見える層にも W7 を混ぜると？
    ch = w[~w.up & w.chain]
    print(f"折り返しだけ見える {len(ch)} 件")
    for name, p in [("今（W4 と W2 の平均）", ch.adopt), ("W4・W2・W7 の平均", (ch.W4 + ch.W2 + ch.W7) / 3), ("W4・W2・W9 の平均", (ch.W4 + ch.W2 + ch.W9) / 3)]:
        print(f"  {name}: {st(p, ch.aw)}")





def combo_report():
    """見えない層を W9、折り返しだけの層を (W4+W2+W9)/3 にした版を、今の採用方式と比べる（ブートストラップ）。"""
    import io, contextlib
    buf = io.StringIO()
    g = {}
    with contextlib.redirect_stdout(buf):
        g = _compute()
    w = g
    new = np.where(w.up, w.W1, np.where(w.chain, (w.W4 + w.W2 + w.W9) / 3, w.W9))
    a = w.aw.to_numpy()
    e_old, e_new = np.abs(w.adopt.to_numpy() - a) / a, np.abs(new - a) / a
    rng = np.random.default_rng(0)
    d = [np.median(e_new[k]) - np.median(e_old[k]) for k in (rng.integers(0, len(a), len(a)) for _ in range(1000))]
    print(f"待ち時間 全体: 今 {np.median(e_old) * 100:.1f}% → 新 {np.median(e_new) * 100:.1f}%"
          f"（差 {np.median(e_new) * 100 - np.median(e_old) * 100:+.1f} ポイント、95% 区間 {np.percentile(d, 2.5) * 100:+.1f}〜{np.percentile(d, 97.5) * 100:+.1f}）"
          f"  符号 {np.median((new - a) / a) * 100:+.1f}%  MAE {np.mean(np.abs(new - a)) / 60:.1f} 分（今 {np.mean(np.abs(w.adopt - a)) / 60:.1f} 分）")
    # 待ち時間込み（tsh.improve_wait と同じ: 待ち時間 + 今の乗車時間モデルで乗車停留所を出る時刻からの乗車時間。
    # 標本の actual_s は「出発から降車停留所まで」の実際の合計）
    from datetime import timedelta
    tt = TravelTimeModel("train")
    t = w.assign(new=new).dropna(subset=["actual_s"])
    for name, col in [("今", "adopt"), ("新", "new")]:
        tot = np.array([x + tt.ride_sec(r.route_id, r.i, r.j, r.depart.to_pydatetime() + timedelta(seconds=float(x)))
                        for x, r in zip(t[col], t.itertuples())])
        e = (tot - t.actual_s.to_numpy()) / t.actual_s.to_numpy()
        print(f"待ち時間込み（{len(t)} 件） {name}: MedAPE {np.median(np.abs(e)) * 100:.1f}%  符号 {np.median(e) * 100:+.1f}%")


if __name__ == "__main__":
    main()
    combo_report()
