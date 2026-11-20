"""検証週の券を無作為に半分に分けた A・B（1 回分）をマスごとに保存する（ノイズの床をどの切り口でも測れるように）。"""
from base import *  # noqa: F401,F403
import duckdb
tk = pd.read_parquet(C.PROCESSED / "tickets_matched.parquet", columns=["route_id", "date", "hr", "day_type", "i", "j", "pax"])
tk = tk[(tk.j > tk.i) & tk.date.isin(set(C.TEST_DAYS))].reset_index(drop=True)
tk["h"] = np.random.default_rng(0).integers(0, 2, len(tk))
con = duckdb.connect(); con.register("tk", tk)
s = con.execute("""
    WITH s AS (SELECT * FROM tk, range(0, 400) r(k) WHERE k >= i AND k < j)
    SELECT route_id, k AS seq, day_type, hr,
           sum(CASE WHEN h=0 THEN pax ELSE 0 END) AS pa, sum(CASE WHEN h=1 THEN pax ELSE 0 END) AS pb
    FROM s GROUP BY ALL""").df()
s.to_parquet(OUT / "test_split_half.parquet", index=False)
print(len(s))
