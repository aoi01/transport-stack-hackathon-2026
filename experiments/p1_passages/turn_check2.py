"""turn_check.py の「途中で引き返した」と判定した組を 1 日分で確かめる: 次の便の最初の通過のあとに、
前の便の終点へ向かっていないか（番号だけ先に替わり、終点へ走り続けていた可能性）。
次の便の通過が順に進んでいるか（逆向きの停留所を誤って拾っていないか）も見る。"""
from __future__ import annotations
import json, re, sys
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
st = C.stops().set_index("stop_id")
out = []
for d in [date(2026, 10, 27), date(2026, 10, 28)]:
    t = load_day(con, d)
    t["route_id"] = t.route_id.astype(str); t["L"] = t.route_id.map(L)
    t = t.dropna(subset=["L"]).sort_values(["vehicle_id", "p0"]).reset_index(drop=True)
    full = t[(t.s1 >= t.L - 1) & (t.s0 <= 1)]
    v = (full.assign(m=[cum[r][int(b)] - cum[r][int(a)] for r, a, b in zip(full.route_id, full.s0, full.s1)])
             .assign(sp=lambda x: x.m / (x.p1 - x.p0)).query("sp > 1 and sp < 20").groupby("route_id").sp.median())
    nx = t.groupby("vehicle_id").shift(-1)
    p = t.join(nx, rsuffix="_b")
    p = p[p.trip_id_b.notna() & (p.route_id != p.route_id_b)].copy()
    p["left_m"] = [cum[r][-1] - cum[r][int(s)] for r, s in zip(p.route_id, p.s1)]
    p = p[p.left_m > 1000].copy()
    p["need_s"] = 2 * p.left_m / p.route_id.map(v)
    p["gap_s"] = p.p0_b - p.p1
    p = p[(p.gap_s < 0.5 * p.need_s)].copy()            # 往復できない短い時間で次の便へ
    p["k"] = np.arange(len(p))
    term = p.route_id.map(last_stop)
    sub = pd.DataFrame({"k": p.k, "vehicle_id": p.vehicle_id, "t2": p.p0_b, "t3": p.p0_b + p.need_s,
                        "tlat": term.map(st.stop_lat), "tlng": term.map(st.stop_lon),
                        "ylat": p.stop1.map(st.stop_lat), "ylng": p.stop1.map(st.stop_lon)})
    con.register("sub", sub)
    g = con.execute(f"""select k, min(sqrt(pow((lat-tlat)*110540,2)+pow((lng-tlng)*97800,2))) after_min_to_term_m,
            max(sqrt(pow((lat-ylat)*110540,2)+pow((lng-ylng)*97800,2))) after_max_from_y_m
        from sub s join '{C.ROOT / "data/interim/bus_gps"}/date={d}/*.parquet' g
          on g.vehicle_id = s.vehicle_id and epoch(g.ts) between s.t2 and s.t3 group by k""").df()
    con.unregister("sub")
    p = p.merge(g, on="k", how="left")
    # 次の便の通過が前に進んでいるか: 通過した停留所の数と、最初から最後までの路線上の距離
    p["b_km"] = [(cum[r][int(b)] - cum[r][int(a)]) / 1000 if r in cum else np.nan for r, a, b in zip(p.route_id_b, p.s0_b, p.s1_b)]
    out.append(p)
p = pd.concat(out, ignore_index=True)
went_after = p.after_min_to_term_m <= 500
res = {"組（2 日分、往復できない短い時間で次の便へ）": int(len(p)),
       "次の便が始まった後、前の便の終点の 500m 以内に行った_%": round(float(went_after.mean()) * 100, 1),
       "次の便の通過が 3 km 以上前に進んだ_%": round(float((p.b_km >= 3).mean()) * 100, 1),
       "次の便の通過の数（中央値）": float(p.n_pass_b.median()),
       "前の便の終点に行かず、次の便が 3 km 以上進んだ（本当に途中で引き返した）_%":
           round(float((~went_after & (p.b_km >= 3)).mean()) * 100, 1),
       "終点まで残り km（中央値）": round(float(p.left_m.median()) / 1000, 1)}
print(json.dumps(res, ensure_ascii=False, indent=1))
