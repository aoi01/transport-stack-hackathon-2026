"""同じ車両の 1 本の走りが、2 つの便（trip_id）に分かれて記録されている組を数える（docs 16.8）。

検証週の停留所の通過で、車両ごとに便を時刻順に並べ、隣り合う 2 便 A→B が
  - 同じ路線（同じ向き）で、
  - B の最初の停留所が A の最後の停留所より先（または同じ）、B の最初の通過が A の最後の通過より後
なら「続きの候補」とする。間の時間と、その区間を普通に走ったときの時間（モデルの中央値）を比べ、
便の名前（route_時_分）が同じか、間に何停留所あるかも数える。

python experiments/p1_journey/split_trips.py [train|test]
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.traveltime import TravelTimeModel  # noqa: E402
from tsh.validate_journeys import load_passages  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))


def pieces(ps: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(ps.ts)
    ts = ts.dt.tz_localize(C.TZ) if ts.dt.tz is None else ts
    ps = ps.assign(t=ts.dt.tz_convert("UTC").dt.tz_localize(None).astype("datetime64[ns]").astype("int64") / 1e9)
    g = ps.groupby(["date", "vehicle_id", "trip_id"]).agg(
        route_id=("route_id", "first"), s0=("seq", "min"), s1=("seq", "max"), t0=("t", "min"), t1=("t", "max"),
        n=("seq", "size")).reset_index()
    return g.sort_values(["date", "vehicle_id", "t0"]).reset_index(drop=True)


def pairs(g: pd.DataFrame, tt) -> pd.DataFrame:
    nx = g.groupby(["date", "vehicle_id"]).shift(-1)
    m = nx.route_id.notna()
    a, b = g[m], nx[m]
    df = pd.DataFrame({
        "date": a.date, "vehicle_id": a.vehicle_id, "route_id": a.route_id, "trip_a": a.trip_id, "trip_b": b.trip_id,
        "same_route": (a.route_id == b.route_id).to_numpy(), "a_s0": a.s0, "a_s1": a.s1, "b_s0": b.s0.astype(int),
        "b_s1": b.s1.astype(int), "a_t1": a.t1, "b_t0": b.t0, "a_n": a.n, "b_n": b.n.astype(int)})
    df = df[df.same_route & (df.b_s0 >= df.a_s1) & (df.b_t0 > df.a_t1)].copy()
    df["gap_s"] = df.b_t0 - df.a_t1
    df["gap_stops"] = df.b_s0 - df.a_s1
    df["same_name"] = df.trip_a.str.split("_").str[:3].str.join("_") == df.trip_b.str.split("_").str[:3].str.join("_")
    exp = []
    for r in df.itertuples():
        t = datetime.fromtimestamp(r.a_t1, IST).replace(tzinfo=None)
        exp.append(tt.ride_sec(str(r.route_id), int(r.a_s1), int(r.b_s0), t) if r.b_s0 > r.a_s1 else 0.0)
    df["exp_s"] = exp
    df["excess_s"] = df.gap_s - df.exp_s
    return df


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    days = C.TRAIN_DAYS if (sys.argv[1:] or ["test"])[0] == "train" else C.TEST_DAYS
    tt = TravelTimeModel("train")
    g = pieces(load_passages(days))
    df = pairs(g, tt)
    nv = g.groupby(["date", "vehicle_id"]).ngroups
    print(f"便 {len(g):,}（車両×日 {nv:,}）。同じ路線で前の便の先から続く次の便: {len(df):,} 組（便の {len(df) / len(g) * 100:.1f}%）")
    print(f"  便の名前（路線_時_分）が同じ: {df.same_name.mean() * 100:.1f}%")
    print("\n間の停留所数:")
    print(df.gap_stops.clip(upper=10).value_counts().sort_index().to_string())
    print("\n間の時間 − 普通に走ったときの時間（分）の分位点:")
    q = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
    print(pd.DataFrame({"全部": (df.excess_s / 60).quantile(q), "名前が同じ": (df[df.same_name].excess_s / 60).quantile(q),
                        "名前が違う": (df[~df.same_name].excess_s / 60).quantile(q)}).round(1).to_string())
    print("\n間の時間（分）の分位点:", (df.gap_s / 60).quantile(q).round(1).tolist())
    for lim in (5, 10, 15, 20, 30):
        print(f"  余分 ≤ {lim} 分: {(df.excess_s <= lim * 60).mean() * 100:.1f}%  （名前が違う組の中で {(df[~df.same_name].excess_s <= lim * 60).mean() * 100:.1f}%）")
    print("\n例:")
    print(df.sample(12, random_state=3)[["vehicle_id", "trip_a", "trip_b", "a_s0", "a_s1", "b_s0", "b_s1", "gap_s", "exp_s"]].round(0).to_string())


if __name__ == "__main__":
    main()
