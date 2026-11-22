"""走り（分かれて記録された便をつないだもの）を、車両の番号つきで日ごとに作る。reach_why.py・reach_model.py が使う。"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from tsh import common as C
from tsh.validate_journeys import bridge_split_runs, load_passages

IST = 19800


def route_meta():
    pat = pd.read_parquet(C.PROCESSED / "patterns.parquet").sort_values(["route_id", "seq"])
    pat["route_id"] = pat.route_id.astype(str)
    cum = {r: g.cum_m.to_numpy() for r, g in pat.groupby("route_id")}
    st = C.stops().set_index("stop_id")
    xy = {r: np.c_[g.stop_id.map(st.stop_lat).to_numpy(), g.stop_id.map(st.stop_lon).to_numpy()]
          for r, g in pat.groupby("route_id")}
    routes = pd.read_csv(C.GTFS / "routes.txt", dtype=str)
    line = {r: re.sub(r"(UP|DOWN|DN)$", "", (n or "").upper().strip()) for r, n in zip(routes.route_id, routes.route_short_name)}
    return cum, xy, line


def build_day(d, tt) -> pd.DataFrame:
    """1 日分の走り: date, vehicle_id, run, route_id, smin, smax, t0, t1, seqs, ts（ts は本当の epoch 秒）。"""
    ps = load_passages([d])
    ts = pd.to_datetime(ps.ts)
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(C.TZ)
    ps["t"] = ts.dt.tz_convert("UTC").dt.tz_localize(None).astype("datetime64[ns]").astype("int64") / 1e9
    ps = bridge_split_runs(ps, tt)
    ps = ps.sort_values(["run", "seq"])
    out = []
    for (v, run), g in ps.groupby(["vehicle_id", "run"], sort=False):
        s = g.seq.to_numpy(); t = g.t.to_numpy()
        out.append((d, v, run, str(g.route_id.iat[0]), int(s.min()), int(s.max()), float(t.min()), float(t.max()), s, t))
    r = pd.DataFrame(out, columns=["date", "vehicle_id", "run", "route_id", "smin", "smax", "t0", "t1", "seqs", "ts"])
    return r.sort_values(["vehicle_id", "t0"]).reset_index(drop=True)
