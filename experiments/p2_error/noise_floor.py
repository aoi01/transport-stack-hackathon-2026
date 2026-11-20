"""検証週の正解そのもののばらつき（ノイズの床）を、券を無作為に半分に分けて測る。

検証週の券を 2 つに分け、それぞれ 2 倍して同じ便数で割った A・B を作る。A と B は同じ平均のまわりの独立な標本なので、
(A − B)/2 のばらつきは、検証週の推定 F = (A+B)/2 のばらつきと同じ大きさ（券の標本誤差）。
→ 完璧な予測（本当の平均）を出しても避けられない誤差の目安 = median(|A − B| / (A + B))。
"""
from base import *  # noqa: F401,F403
import duckdb
sys.stdout.reconfigure(encoding="utf-8")

tk = pd.read_parquet(C.PROCESSED / "tickets_matched.parquet", columns=["route_id", "date", "hr", "day_type", "i", "j", "pax"])
tk = tk[(tk.j > tk.i) & tk.date.isin(set(C.TEST_DAYS))].reset_index(drop=True)
truth = test_truth()
res = []
for rep in range(3):
    rng = np.random.default_rng(rep)
    tk["h"] = rng.integers(0, 2, len(tk))
    con = duckdb.connect(); con.register("tk", tk)
    s = con.execute("""
        WITH s AS (SELECT * FROM tk, range(0, 400) r(k) WHERE k >= i AND k < j)
        SELECT route_id, k AS seq, day_type, hr,
               sum(CASE WHEN h=0 THEN pax ELSE 0 END) AS pa, sum(CASE WHEN h=1 THEN pax ELSE 0 END) AS pb
        FROM s GROUP BY ALL""").df()
    m = truth.merge(s, on=K)
    assert np.allclose(m.pa + m.pb, m.pax_te), "検証週の人数が合わない"
    for mn in [5, 10, 20, 30, 50, 100]:
        x = m[m.n_te >= mn]
        r = ((x.pa - x.pb).abs() / (x.pa + x.pb))
        res.append({"rep": rep, "min_n_te": mn, "cells": len(x), "noise_floor_median_%": round(r.median() * 100, 2)})
df = pd.DataFrame(res).groupby("min_n_te").agg(cells=("cells", "first"), floor=("noise_floor_median_%", "mean")).round(2)
print(df.to_string())
df.to_csv(OUT / "noise_floor.csv")
