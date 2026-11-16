"""試す順番 2: 異常日の暦で「いつもの値」（過去の実績）を洗う。

過去の推定 = 区間（隣り合う停留所）× 平日/休日 × 時間帯 の所要時間の対数平均を、乗る区間について足したもの
（seg_ml の「過去の推定の合計」と同じ考え方。件数 3 未満のマスは 平日/休日 全体 → 全日 に退避）。
学習期間 10/1〜24 の観測から作り、検証週の同じ 20,000 区間（results/p1_ride_samples.csv）で比べる。

  A 今のまま（祝日は 10/2 だけ）
  B 10/20（ダシャラー）も祝日（休日扱い）
  C B ＋ 異常日を「いつもの値」の計算から外す: 11（約30か所の迂回）・12（朝の大雨と冠水、治安上の規制）・
    13（規制の続き）・18（ハーフマラソン）
  D B ＋ 12・18 日だけ外す
  E・F B ＋ 直近の 2 週・1 週だけで作る（10月の後半ほど遅くなる流れがあるかを見る）
使い方: python -X utf8 experiments/p1_external/calendar_exp.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402

OBS = (C.PROCESSED / "improve" / "obs_train.parquet").as_posix()
OCT = lambda d: date(2026, 10, d)  # noqa: E731


def main():
    con = C.connect()
    con.execute(f"""CREATE TABLE o AS SELECT from_stop, to_stop, ln(link_s) AS ls,
                   CAST(timezone('{C.TZ}', to_timestamp(t)) AS DATE) AS d, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr
                   FROM '{OBS}' WHERE link_s > 0""")
    s = pd.read_csv(C.ROOT / "results" / "p1_ride_samples.csv", parse_dates=["t_i"], dtype={"route_id": str})
    s["sid"] = np.arange(len(s))
    pat = C.patterns()[["route_id", "seq", "stop_id"]]
    rows = []
    stops = {r: g.stop_id.tolist() for r, g in pat.groupby("route_id")}
    for sid, r, i, j, t in zip(s.sid, s.route_id, s.i, s.j, s.t_i):
        st = stops[r]
        wk = "weekend" if t.weekday() >= 5 else "weekday"
        for k in range(i, j):
            rows.append((sid, st[k], st[k + 1], wk, t.hour))
    con.register("tl", pd.DataFrame(rows, columns=["sid", "a", "b", "dt", "hr"]))
    days = {d: ("weekend" if d.weekday() >= 5 else "weekday") for d in C.TRAIN_DAYS}
    variants = {
        "A 今のまま": ({OCT(2)}, set()),
        "B 10/20 も祝日": ({OCT(2), OCT(20)}, set()),
        "C B＋異常日（11・12・13・18）を外す": ({OCT(2), OCT(20)}, {OCT(11), OCT(12), OCT(13), OCT(18)}),
        "D B＋12・18 日だけ外す": ({OCT(2), OCT(20)}, {OCT(12), OCT(18)}),
        "E B＋直近 2 週（10/11〜24）だけ": ({OCT(2), OCT(20)}, {OCT(d) for d in range(1, 11)}),
        "F B＋直近 1 週（10/18〜24）だけ": ({OCT(2), OCT(20)}, {OCT(d) for d in range(1, 18)}),
    }
    out = {}
    for name, (hol, drop) in variants.items():
        dtab = pd.DataFrame({"d": list(days), "dt": ["weekend" if (d in hol or v == "weekend") else "weekday" for d, v in days.items()],
                             "keep": [d not in drop for d in days]})
        con.register("dtab", dtab)
        con.execute("""CREATE OR REPLACE TABLE ob AS SELECT o.*, dtab.dt FROM o JOIN dtab USING (d) WHERE dtab.keep""")
        con.execute("CREATE OR REPLACE TABLE m1 AS SELECT from_stop a, to_stop b, dt, hr, avg(ls) m, count(*) n FROM ob GROUP BY ALL")
        con.execute("CREATE OR REPLACE TABLE m2 AS SELECT from_stop a, to_stop b, dt, avg(ls) m, count(*) n FROM ob GROUP BY ALL")
        con.execute("CREATE OR REPLACE TABLE m3 AS SELECT from_stop a, to_stop b, avg(ls) m FROM ob GROUP BY ALL")
        p = con.execute("""
            SELECT tl.sid, sum(exp(coalesce(CASE WHEN m1.n >= 3 THEN m1.m END, CASE WHEN m2.n >= 3 THEN m2.m END, m3.m))) AS pred,
                   count(*) FILTER (WHERE m3.m IS NULL) AS miss
            FROM tl LEFT JOIN m1 ON m1.a = tl.a AND m1.b = tl.b AND m1.dt = tl.dt AND m1.hr = tl.hr
                    LEFT JOIN m2 ON m2.a = tl.a AND m2.b = tl.b AND m2.dt = tl.dt
                    LEFT JOIN m3 ON m3.a = tl.a AND m3.b = tl.b
            GROUP BY tl.sid""").df()
        out[name] = s.merge(p, on="sid")
    base_ok = set(out["A 今のまま"].query("miss == 0").sid)
    for v in out.values():
        base_ok &= set(v.query("miss == 0").sid)
    print(f"比べる区間（全リンクに過去の値がある）: {len(base_ok):,} / {len(s):,}")
    res = []
    for name, df in out.items():
        df = df[df.sid.isin(base_ok)].copy()
        e = (df.pred - df.actual_s) / df.actual_s
        df["e"] = e
        df["dow"] = df.t_i.dt.strftime("%a")
        row = {"方法": name, "MedAPE%": np.median(e.abs()) * 100, "符号つき%": np.median(e) * 100}
        for dw, g in df.groupby("dow"):
            row[f"{dw} MedAPE"] = np.median(g.e.abs()) * 100
            row[f"{dw} 符号"] = np.median(g.e) * 100
        res.append(row)
        out[name] = df
    r = pd.DataFrame(res).set_index("方法").round(2)
    pd.set_option("display.width", 250)
    print(r.to_string())
    # 対の差のブートストラップ（A との差、MedAPE）
    a = out["A 今のまま"].set_index("sid").e.abs()
    rng = np.random.default_rng(0)
    idx = a.index.to_numpy()
    for name, df in out.items():
        if name.startswith("A"):
            continue
        b = df.set_index("sid").e.abs().reindex(idx)
        diffs = []
        for _ in range(300):
            k = rng.choice(idx, len(idx))
            diffs.append(np.median(b.loc[k]) - np.median(a.loc[k]))
        lo, hi = np.percentile(diffs, [2.5, 97.5]) * 100
        print(f"{name} − A: MedAPE の差 {np.median(b) * 100 - np.median(a) * 100:+.2f} ポイント（95% 区間 {lo:+.2f}〜{hi:+.2f}）")


if __name__ == "__main__":
    main()
