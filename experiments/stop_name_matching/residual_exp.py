"""Residual analysis on match_exp2_out.csv: (1) top-N coverage of residual names, (2) for names that exist
elsewhere in GTFS, distance from those same-key stops to the nearest stop on the ticket's route pattern
(i.e. would a 'global name -> nearest route stop within X m' fallback resolve them?)."""
import math
import re
import sys

import numpy as np
import pandas as pd

sys.argv = sys.argv[:1] + ["unused"]
exec(open("match_exp2.py", encoding="utf-8").read().split("stops = pd.read_csv")[0])  # reuse normalisers only

ROOT = "C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data"
R = pd.read_csv("match_exp2_out.csv")
T = R.n.sum()
stops = pd.read_csv(ROOT + "/raw/gtfs_static/stops.txt", dtype={"stop_id": str})
routes = pd.read_csv(ROOT + "/raw/gtfs_static/routes.txt", dtype=str)
pat = pd.read_parquet(ROOT + "/processed/patterns.parquet")
pat["stop_id"] = pat.stop_id.astype(str)
pat = pat.merge(stops[["stop_id", "stop_lat", "stop_lon"]].rename(columns={"stop_lat": "la", "stop_lon": "lo"}), on="stop_id")
rid = routes.set_index("route_short_name").route_id.to_dict()

parts = []
for r in stops.itertuples():
    for p in [r.stop_name] + (r.stop_name.split("/") if "/" in r.stop_name else []):
        parts.append((r.stop_id, r.stop_lat, r.stop_lon, key_fold(p), key_skel(p)))
P = pd.DataFrame(parts, columns=["stop_id", "lat", "lon", "k2", "kk"])
by_k2 = {k: g[["lat", "lon"]].to_numpy() for k, g in P.groupby("k2")}
by_kk = {k: g[["lat", "lon"]].to_numpy() for k, g in P.groupby("kk")}
pat_xy = {r: g[["la", "lo"]].to_numpy() for r, g in pat.groupby("route_id")}

def hav(a, b):
    la1, lo1 = np.radians(a[:, None, 0]), np.radians(a[:, None, 1])
    la2, lo2 = np.radians(b[None, :, 0]), np.radians(b[None, :, 1])
    d = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * np.arcsin(np.sqrt(d))

sub = R[(R.imp == "none") & (R.cause == "in_gtfs_not_on_route")].copy()
dmin = []
for r in sub.itertuples():
    xy = by_k2.get(key_fold(r.name))
    if xy is None:
        xy = by_kk.get(key_skel(r.name))
    rx = pat_xy.get(rid.get(r.route))
    dmin.append(float(hav(xy, rx).min()) if (xy is not None and rx is not None) else np.nan)
sub["dmin"] = dmin
print("in_gtfs_not_on_route: ends %", round(sub.n.sum() / T * 100, 2))
for thr in [100, 200, 400, 600, 800, 1000, 1500]:
    print(f"  share of these ends whose same-key GTFS stop is within {thr} m of the route pattern:",
          round(sub[sub.dmin <= thr].n.sum() / sub.n.sum() * 100, 1), "%")
print("  far examples (>1000 m):")
print(sub[sub.dmin > 1000].sort_values("n", ascending=False).head(12)[["route", "name", "n", "dmin"]].round(0).to_string())

res = R[R.imp == "none"].groupby("name").n.sum().sort_values(ascending=False)
c = res.cumsum() / res.sum()
print("\nresidual unmatched names:", len(res), " ends %:", round(res.sum() / T * 100, 2))
for k in [25, 50, 100, 200, 400, 800]:
    print(f"  top {k} names cover {c.iloc[min(k, len(c)) - 1] * 100:.1f}% of residual unmatched ends")
nf = R[(R.imp == "none") & (R.cause == "not_in_gtfs_by_key")]
sl = nf[nf.name.str.contains("/")]
print("\nnot_in_gtfs residual containing '/':", round(sl.n.sum() / T * 100, 2), "% of ends")
print("distinct ticket names overall:", R.name.nunique(), " with '/':", R.name[R.name.str.contains('/')].nunique())
