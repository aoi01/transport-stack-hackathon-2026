"""trip_switch.py の続き: 終点の手前で終わった便が、終点まであと何 km・何停留所で終わったか。
同じ路線で毎日同じ所で終わるか（決まった折り返し場所か）も見る。"""
from __future__ import annotations
import json, re, sys
import numpy as np, pandas as pd
from tsh import common as C
sys.path.insert(0, str(C.ROOT / "experiments/p1_passages"))
from trip_switch import load_day, DAYS

sys.stdout.reconfigure(encoding="utf-8")
con = C.connect()
pat = pd.read_parquet(C.PROCESSED / "patterns.parquet")
L = pat.groupby("route_id").seq.max().to_dict()
cum = {r: g.sort_values("seq").cum_m.to_numpy() for r, g in pat.groupby("route_id")}
routes = pd.read_csv(C.GTFS / "routes.txt", dtype=str)
line = {r: re.sub(r"(UP|DOWN|DN)$", "", (n or "").upper().strip()) for r, n in zip(routes.route_id, routes.route_short_name)}
t = pd.concat([load_day(con, d) for d in DAYS], ignore_index=True).drop(columns=["stops"])
t["route_id"] = t.route_id.astype(str)
t["L"] = t.route_id.map(L)
t = t.dropna(subset=["L"]).sort_values(["date", "vehicle_id", "p0"]).reset_index(drop=True)
nx = t.groupby(["date", "vehicle_id"]).shift(-1)
p = t.join(nx, rsuffix="_b")
p = p[p.trip_id_b.notna()].copy()
p["left_stops"] = p.L - p.s1
p["left_km"] = [(cum[r][-1] - cum[r][int(s)]) / 1000 for r, s in zip(p.route_id, p.s1)]
p["len_km"] = [cum[r][-1] / 1000 for r in p.route_id]
same = p.route_id == p.route_id_b
p["cat"] = np.select([same & (p.s0_b >= p.s1), same, p.route_id.map(line) == p.route_id_b.map(line)],
                     ["番号だけ付け替え", "同じ路線で戻る", "逆向き"], "別の系統")
q = lambda s: [round(float(x), 2) for x in np.nanpercentile(s, [10, 25, 50, 75, 90])]
res = {}
for cat, g in p.groupby("cat"):
    res[cat] = {"組（終点まで含む全部）": int(len(g)),
                "終点まで残りの停留所（10/25/50/75/90%点）": q(g.left_stops),
                "終点まで残りの km": q(g.left_km),
                "残り 1 km 以下_%": round(float((g.left_km <= 1).mean()) * 100, 1),
                "路線の半分より手前で終わった_%": round(float((g.left_km > g.len_km / 2).mean()) * 100, 1)}
# 逆向き・別の系統で、残り 1 km 超の所で終わった組: 同じ路線で終わる停留所が日をまたいで決まっているか
o = p[p.cat.isin(["逆向き", "別の系統"]) & (p.left_km > 1)]
top = o.groupby(["route_id", "stop1"]).size().rename("n").reset_index()
top["share_in_route"] = top.n / top.groupby("route_id").n.transform("sum")
days = o.groupby(["route_id", "stop1"]).date.nunique().rename("days").reset_index()
top = top.merge(days, on=["route_id", "stop1"])
res["残り 1 km 超で路線が変わった組"] = {
    "組": int(len(o)),
    "その路線でいちばん多い終わり方の停留所に集中している割合（組の重み）": round(float(
        top.sort_values("n").groupby("route_id").tail(1).n.sum() / len(o)) * 100, 1),
    "同じ路線・同じ停留所で 5 日以上起きた組の割合": round(float(top[top.days >= 5].n.sum() / len(o)) * 100, 1),
}
st = C.stops().set_index("stop_id").stop_name
big = top[top.days >= 5].sort_values("n", ascending=False).head(15)
res["よく起きる所（上位 15）"] = [{"路線": routes.set_index("route_id").route_short_name.get(r.route_id), "停留所": st.get(r.stop1),
                               "組": int(r.n), "日数": int(r.days), "路線の中の割合_%": round(r.share_in_route * 100)}
                              for r in big.itertuples()]
print(json.dumps(res, ensure_ascii=False, indent=1))
(C.RESULTS / "trip_switch_where.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
