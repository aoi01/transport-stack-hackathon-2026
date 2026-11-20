"""本当に途中で引き返した便（turn_check2 の判定）は、どんな場面で起きているか。2 日分。
比べる相手: 同じ路線の、終点まで走った便が同じ停留所を通った場面。
- 時間帯
- 前のバスとの間隔（同じ路線で直前にその停留所を通ったバスから何分）: 団子運転なら短い
- 1 本前の便からの遅れ: 同じ車両の前の便の終わりから、この便の始まりまで（折り返しの余裕）
- 引き返した停留所の近く（1 km 以内）に車庫の名前の停留所があるか
- 引き返した後の逆向きの便は、何 km 走ったか"""
from __future__ import annotations
import json, sys
from datetime import date
import numpy as np, pandas as pd
from tsh import common as C
sys.path.insert(0, str(C.ROOT / "experiments/p1_passages"))
from trip_switch import load_day

sys.stdout.reconfigure(encoding="utf-8")
con = C.connect()
pat = pd.read_parquet(C.PROCESSED / "patterns.parquet").sort_values(["route_id", "seq"])
cum = {r: g.cum_m.to_numpy() for r, g in pat.groupby("route_id")}
last_stop = pat.groupby("route_id").stop_id.last().to_dict()
L = pat.groupby("route_id").seq.max().to_dict()
st = C.stops()
depots = st[st.stop_name.str.contains("depot", case=False, na=False)][["stop_lat", "stop_lon"]].to_numpy()
sti = st.set_index("stop_id")
def near_depot(sid, r=1000):
    if sid not in sti.index:
        return False
    a = sti.loc[sid]
    return bool((C.dist_m(a.stop_lat, a.stop_lon, depots[:, 0], depots[:, 1]) <= r).any())
rows = []
for d in [date(2026, 10, 27), date(2026, 10, 28)]:
    t = load_day(con, d).drop(columns=["stops"])
    t["route_id"] = t.route_id.astype(str); t["L"] = t.route_id.map(L)
    t = t.dropna(subset=["L"]).sort_values(["vehicle_id", "p0"]).reset_index(drop=True)
    full = t[(t.s1 >= t.L - 1) & (t.s0 <= 1)]
    v = (full.assign(m=[cum[r][int(b)] - cum[r][int(a)] for r, a, b in zip(full.route_id, full.s0, full.s1)])
             .assign(sp=lambda x: x.m / (x.p1 - x.p0)).query("sp > 1 and sp < 20").groupby("route_id").sp.median())
    prv = t.groupby("vehicle_id").shift(1)
    t["turnaround_s"] = t.p0 - prv.p1                       # 同じ車両の前の便の終わりからこの便の始まりまで
    nx = t.groupby("vehicle_id").shift(-1)
    p = t.join(nx, rsuffix="_b")
    p = p[p.trip_id_b.notna()].copy()
    p["left_m"] = [cum[r][-1] - cum[r][int(s)] for r, s in zip(p.route_id, p.s1)]
    p["need_s"] = 2 * p.left_m / p.route_id.map(v)
    p["gap_s"] = p.p0_b - p.p1
    turned = p[(p.route_id != p.route_id_b) & (p.left_m > 1000) & (p.gap_s < 0.5 * p.need_s)].copy()
    turned["b_km"] = [(cum[r][int(b)] - cum[r][int(a)]) / 1000 if r in cum else np.nan
                      for r, a, b in zip(turned.route_id_b, turned.s0_b, turned.s1_b)]
    turned = turned[turned.b_km >= 3]
    # 前のバスとの間隔: その日の通過から、同じ路線・同じ停留所の直前の通過
    ps = con.execute(f"""select route_id::varchar route_id, stop_id, vehicle_id, trip_id, epoch(ts) t
                         from '{C.INTERIM / "stop_passages_v2"}/date={d}/*.parquet'""").df()
    ps = ps.sort_values(["route_id", "stop_id", "t"])
    ps["hw_prev_s"] = ps.groupby(["route_id", "stop_id"]).t.diff()
    ps["hw_next_s"] = -ps.groupby(["route_id", "stop_id"]).t.diff(-1)
    key = ["vehicle_id", "trip_id", "stop_id"]
    turned = turned.merge(ps.rename(columns={"stop_id": "stop1"})[["vehicle_id", "trip_id", "stop1", "hw_prev_s", "hw_next_s"]],
                          on=["vehicle_id", "trip_id", "stop1"], how="left")
    # 比べる相手: 引き返した停留所を、終点まで走った便が通った場面
    fullt = t[t.s1 >= t.L - 1][["vehicle_id", "trip_id", "route_id", "turnaround_s", "p0"]]
    ref = ps.merge(fullt, on=["vehicle_id", "trip_id", "route_id"])
    ref = ref.merge(turned[["route_id", "stop1"]].drop_duplicates().rename(columns={"stop1": "stop_id"}), on=["route_id", "stop_id"])
    turned["hour"] = ((turned.p1 + 19800) % 86400) // 3600
    ref["hour"] = ((ref.t + 19800) % 86400) // 3600
    turned["depot"] = [near_depot(s) for s in turned.stop1]
    rows.append((turned, ref))
T = pd.concat([a for a, _ in rows]); R = pd.concat([b for _, b in rows])
q = lambda s: [round(float(x), 1) for x in np.nanpercentile(s, [10, 25, 50, 75, 90])]
hb = lambda h: pd.cut(h, [0, 7, 10, 16, 20, 24], right=False, labels=["〜7時", "7〜10時", "10〜16時", "16〜20時", "20時〜"])
st_depot_all = np.mean([near_depot(s) for s in R.stop_id.drop_duplicates()])
res = {"引き返した便（2 日）": int(len(T)), "比べる相手（同じ停留所を終点まで走った便が通った場面）": int(len(R)),
       "時間帯_%": {"引き返した": (hb(T.hour).value_counts(normalize=True).sort_index() * 100).round(1).to_dict(),
                  "終点まで走った": (hb(R.hour).value_counts(normalize=True).sort_index() * 100).round(1).to_dict()},
       "前のバスとの間隔（分）": {"引き返した": q(T.hw_prev_s / 60), "終点まで走った": q(R.hw_prev_s / 60)},
       "前のバスとの間隔が 3 分以内_%": {"引き返した": round(float((T.hw_prev_s <= 180).mean()) * 100, 1),
                                  "終点まで走った": round(float((R.hw_prev_s <= 180).mean()) * 100, 1)},
       "前の便の終わりからこの便の始まりまで（分）": {"引き返した": q(T.turnaround_s / 60), "終点まで走った": q(R.turnaround_s / 60)},
       "引き返した停留所の 1 km 以内に車庫の名前の停留所_%": round(float(T.depot.mean()) * 100, 1),
       "参考: 同じ停留所の集合で車庫が 1 km 以内の割合_%": round(st_depot_all * 100, 1),
       "終点まで残り km": q(T.left_m / 1000),
       "引き返した後の便が走った km": q(T.b_km)}
print(json.dumps(res, ensure_ascii=False, indent=1))
(C.RESULTS / "turn_why.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
