"""1 位の案で「乗る停留所に 3 時間以内に GPS のバスが来ない」組（600 組中 163 組）の中身を調べる。

各組の最初の区間（路線 r、乗車停留所 i、その日、到着時刻 t）について:
  - その日、路線 r の GPS の便が 1 本でもあったか、停留所 i を範囲に含む便があったか
  - t の前後 3 時間に、路線 r の便が（i を含むかに関係なく）走っていたか
  - 学習期間の同じ平日/休日の日のうち、t から 1 時間以内・4 時間以内に i をバスが通った日の割合
  - 車両番号つきの乗車券で、その日その路線に券が出ていたか（GPS に映らないバスが走っていた手がかり）
使い方: python -X utf8 experiments/p1_journey/nobus.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.validate_p1 import load_test_passages  # noqa: E402
from tsh.waitmodel import PassageTimetable  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    o = pd.read_parquet(OUT / "options.parquet")
    lg = pd.read_parquet(OUT / "legs.parquet")
    f = lg[(lg["rank"] == 0) & (lg.leg == 0)].merge(o[o["rank"] == 0][["pair", "depart", "day_type"]], on="pair")
    ps = load_test_passages()
    ps["date"] = pd.to_datetime(ps.date).dt.date
    ps["sec"] = ps.ts.dt.hour * 3600 + ps.ts.dt.minute * 60 + ps.ts.dt.second
    trips = ps.groupby(["route_id", "date", "vehicle_id", "trip_id"]).agg(smin=("seq", "min"), smax=("seq", "max"),
                                                                           s0=("sec", "min"), s1=("sec", "max")).reset_index()
    by = {k: g for k, g in trips.groupby(["route_id", "date"])}
    tr = PassageTimetable(C.TRAIN_DAYS)
    tk = pd.read_parquet(C.PROCESSED / "tickets_matched.parquet", columns=None)
    cols = tk.columns.tolist()
    rcol = "route_id" if "route_id" in cols else None
    dcol = next((c for c in ("date", "service_date") if c in cols), None)
    tk_days = set()
    if rcol and dcol:
        tk_days = set(zip(tk[rcol].astype(str), pd.to_datetime(tk[dcol]).dt.date))
    rows = []
    for r in f.itertuples():
        dep = pd.Timestamp(r.depart)
        d = dep.date()
        t = dep.hour * 3600 + dep.minute * 60 + dep.second + r.walk_before_s
        g = by.get((r.route_id, d))
        n_trips = 0 if g is None else len(g)
        cover = 0 if g is None else int(((g.smin <= r.i) & (g.smax >= r.i)).sum())
        near = 0 if g is None else int(((g.s1 >= t - 3 * 3600) & (g.s0 <= t + 3 * 3600)).sum())
        se = tr.idx.get((str(r.route_id), int(r.i), r.day_type))
        s1h = s4h = np.nan
        if se is not None:
            x = tr.v[se[0]:se[1]]
            hit1 = hit4 = 0
            ks = tr.days_of[r.day_type]
            for k in ks:
                p = np.searchsorted(x, k * 86400 + t)
                gap = x[p] - (k * 86400 + t) if p < len(x) and x[p] < (k + 1) * 86400 else np.inf
                hit1 += gap <= 3600
                hit4 += gap <= 4 * 3600
            s1h, s4h = hit1 / len(ks), hit4 / len(ks)
        rows.append({"pair": r.pair, "nobus": not r.reached_board, "trips_that_day": n_trips, "trips_cover_i": cover,
                     "trips_near_time": near, "train_served_1h": s1h, "train_served_4h": s4h,
                     "ticket_that_day": (str(r.route_id), d) in tk_days if tk_days else np.nan,
                     "pred_wait_min": r.pred_wait_s / 60})
    d = pd.DataFrame(rows)
    nb, ok = d[d.nobus], d[~d.nobus]
    res = {"1位の案": int(len(d)), "3時間以内に来ない": int(len(nb))}
    for nm, g in (("来ない組", nb), ("来た組", ok)):
        res[nm] = {"その日その路線の GPS の便が 0 本_%": round(float((g.trips_that_day == 0).mean() * 100), 1),
                   "便はあるが停留所 i を通る便が 0 本_%": round(float(((g.trips_that_day > 0) & (g.trips_cover_i == 0)).mean() * 100), 1),
                   "前後3時間に走っていた便が 0 本_%": round(float((g.trips_near_time == 0).mean() * 100), 1),
                   "学習期間に1時間以内に来た日の割合の平均_%": round(float(g.train_served_1h.mean() * 100), 1),
                   "学習期間に4時間以内に来た日の割合の平均_%": round(float(g.train_served_4h.mean() * 100), 1),
                   "予測した待ちの平均（分）": round(float(g.pred_wait_min.mean()), 1)}
        if tk_days:
            res[nm]["その日その路線に乗車券がある_%"] = round(float(g.ticket_that_day.mean() * 100), 1)
    # 学習期間に 1 時間以内に来た日の割合で分けて、来ない組の割合
    d["band"] = pd.cut(d.train_served_1h, [-0.01, 0.5, 0.8, 0.95, 1.0])
    res["学習期間に1時間以内に来た日の割合ごと"] = {str(k): {"組": int(len(g)), "来ない_%": round(float(g.nobus.mean() * 100), 1)}
                                      for k, g in d.groupby("band", observed=True)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (OUT / "nobus.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
