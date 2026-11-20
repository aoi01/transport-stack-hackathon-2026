"""途中（終点まで 1 km 超）で終わった便が、GPS の見えない間に終点まで行って戻ったのか、本当に途中で引き返したのか。

前の便の最後の通過（停留所 Y、時刻 t1）と、次の便（同じ系統の逆向き・別の系統）の最初の通過（停留所 Z、時刻 t2）について:
- 間の時間 t2 − t1 と、Y から終点まで往復するのにかかる時間（Y→終点の区間を、その路線のふだんの速さで走った時間 × 2）
- 間の GPS の点: 数・最も長い途切れ・終点にいちばん近づいた距離・Y から最も離れた距離
使い方: PYTHONPATH=src python experiments/p1_passages/turn_check.py
"""
from __future__ import annotations
import json, re, sys
import numpy as np, pandas as pd
from tsh import common as C
sys.path.insert(0, str(C.ROOT / "experiments/p1_passages"))
from trip_switch import load_day, DAYS

sys.stdout.reconfigure(encoding="utf-8")
con = C.connect()
pat = pd.read_parquet(C.PROCESSED / "patterns.parquet").sort_values(["route_id", "seq"])
cum = {r: g.cum_m.to_numpy() for r, g in pat.groupby("route_id")}
last_stop = pat.groupby("route_id").stop_id.last().to_dict()
L = pat.groupby("route_id").seq.max().to_dict()
st = C.stops().set_index("stop_id")
routes = pd.read_csv(C.GTFS / "routes.txt", dtype=str)
line = {r: re.sub(r"(UP|DOWN|DN)$", "", (n or "").upper().strip()) for r, n in zip(routes.route_id, routes.route_short_name)}

rows = []
for d in DAYS:
    t = load_day(con, d).drop(columns=["stops"])
    t["route_id"] = t.route_id.astype(str)
    t["L"] = t.route_id.map(L)
    t = t.dropna(subset=["L"]).sort_values(["vehicle_id", "p0"]).reset_index(drop=True)
    # 終点まで走った便の、路線ごとのふだんの速さ（m/s、通過の最初から最後まで）
    full = t[(t.s1 >= t.L - 1) & (t.s0 <= 1)]
    v = (full.assign(m=[cum[r][int(b)] - cum[r][int(a)] for r, a, b in zip(full.route_id, full.s0, full.s1)])
             .assign(sp=lambda x: x.m / (x.p1 - x.p0)).query("sp > 1 and sp < 20").groupby("route_id").sp.median())
    nx = t.groupby("vehicle_id").shift(-1)
    p = t.join(nx, rsuffix="_b")
    p = p[p.trip_id_b.notna() & (p.route_id != p.route_id_b)].copy()
    p["left_m"] = [cum[r][-1] - cum[r][int(s)] for r, s in zip(p.route_id, p.s1)]
    p = p[p.left_m > 1000].copy()
    p["kind"] = np.where(p.route_id.map(line) == p.route_id_b.map(line), "逆向き", "別の系統")
    p["speed"] = p.route_id.map(v)
    p = p.dropna(subset=["speed"])
    p["need_s"] = 2 * p.left_m / p.speed          # 終点まで往復する時間（停車・折り返しの待ちを含まない下限に近い）
    p["gap_s"] = p.p0_b - p.p1
    p["date"] = d
    # 間の GPS
    sub = p[["vehicle_id", "p1", "p0_b", "stop1", "route_id"]].copy()
    sub["k"] = np.arange(len(sub))
    sub["ylat"] = sub.stop1.map(st.stop_lat); sub["ylng"] = sub.stop1.map(st.stop_lon)
    term = sub.route_id.map(last_stop)
    sub["tlat"] = term.map(st.stop_lat); sub["tlng"] = term.map(st.stop_lon)
    con.register("sub", sub)
    g = con.execute(f"""
        with pts as (
          select s.k, epoch(g.ts) t, g.lat, g.lng, s.ylat, s.ylng, s.tlat, s.tlng
          from sub s join '{C.ROOT / "data/interim/bus_gps"}/date={d}/*.parquet' g
            on g.vehicle_id = s.vehicle_id and epoch(g.ts) > s.p1 and epoch(g.ts) < s.p0_b)
        select k, count(*) n_pts,
               min(sqrt(pow((lat-tlat)*110540,2)+pow((lng-tlng)*97800,2))) min_to_term_m,
               max(sqrt(pow((lat-ylat)*110540,2)+pow((lng-ylng)*97800,2))) max_from_y_m,
               max(t) - min(t) span_s, list(t order by t) ts
        from pts group by k""").df()
    con.unregister("sub")
    g["max_hole_s"] = [float(np.max(np.diff(x))) if len(x) > 1 else np.nan for x in g.ts]
    p = p.reset_index(drop=True)
    p["k"] = np.arange(len(p))
    p = p.merge(g.drop(columns=["ts"]), on="k", how="left")
    p["n_pts"] = p.n_pts.fillna(0)
    rows.append(p)
    print(d, len(p), flush=True)

p = pd.concat(rows, ignore_index=True)
p["ratio"] = p.gap_s / p.need_s
# 判定
went = (p.min_to_term_m <= 500)                                      # GPS が終点の 500 m 以内に来た
short_time = p.gap_s < 0.5 * p.need_s                                # 往復の半分の時間もない
gps_ok = (p.n_pts >= 5) & (p.max_hole_s <= 300)                      # 間の GPS がほぼ途切れていない（5 分超の穴なし）
p["verdict"] = np.select(
    [went, short_time & ~went, gps_ok & ~went],
    ["終点まで行った（GPS が終点の 500m 以内）", "往復できない短い時間で逆向きに（途中で引き返した）",
     "GPS は途切れず、終点に近づかずに次の便へ（途中で引き返した）"],
    "判断できない（GPS の穴が大きく、時間も往復できる長さ）")
q = lambda s: [round(float(x), 2) for x in np.nanpercentile(s, [10, 25, 50, 75, 90])]
res = {"組（終点まで 1 km 超で終わり、次が別の路線）": int(len(p))}
for kind, g in [("全部", p)] + list(p.groupby("kind")):
    res[kind] = {"組": int(len(g)),
                 "判定_%": {k: round(v * 100, 1) for k, v in g.verdict.value_counts(normalize=True).items()},
                 "終点まで残り km": q(g.left_m / 1000),
                 "間の時間 ÷ 往復に要る時間": q(g.ratio),
                 "間の時間（分）": q(g.gap_s / 60),
                 "間の GPS の最大の穴（分）": q(g.max_hole_s / 60)}
# 決まった場所（同じ路線・同じ停留所で 5 日以上）だけ
days = p.groupby(["route_id", "stop1"]).date.transform("nunique")
fx = p[days >= 5]
res["決まった場所（同じ路線・停留所で 5 日以上）"] = {"組": int(len(fx)),
    "判定_%": {k: round(v * 100, 1) for k, v in fx.verdict.value_counts(normalize=True).items()}}
for rn, sname in [("764UP", "Pumposh Enclave"), ("307UP", "Trilokpuri 13 Block"), ("753BDOWN", "Loha Mandi")]:
    rid = routes.set_index("route_short_name").route_id.get(rn)
    g = p[(p.route_id == rid) & (p.stop1.map(st.stop_name) == sname)]
    res[f"例: {rn} {sname}"] = {"組": int(len(g)), "終点まで残り km": round(float(g.left_m.median()) / 1000, 1),
                               "間の時間 中央値（分）": round(float(g.gap_s.median()) / 60, 1),
                               "往復に要る時間 中央値（分）": round(float(g.need_s.median()) / 60, 1),
                               "判定_%": {k: round(v * 100, 1) for k, v in g.verdict.value_counts(normalize=True).items()}}
print(json.dumps(res, ensure_ascii=False, indent=1))
(C.RESULTS / "turn_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
