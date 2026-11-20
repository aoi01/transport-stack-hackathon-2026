"""経路検索の網羅性と速さの確認。

デリー市内の停留所からランダムに 3〜15km 離れた出発地・目的地の組を 200 組作り、
平日 9:00 発で検索して、経路が見つかる割合・候補の中身・1回の検索時間を測る。
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd

from . import common as C
from .planner import Planner


def main(n: int = 200) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rng = np.random.default_rng(7)
    P = Planner("all")
    st = C.stops()
    xy = st[["stop_lat", "stop_lon"]].to_numpy()
    rows = []
    while len(rows) < n:
        a, b = rng.integers(len(xy), size=2)
        d = float(C.dist_m(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1]))
        if not 3000 <= d <= 15000:
            continue
        t = time.time()
        r = P.plan(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], datetime(2026, 11, 17, 9, 0))
        el = time.time() - t
        o = r["options"][0] if r["options"] else None
        rows.append({"km": d / 1000, "found": o is not None, "sec": el,
                     "total_min": o["total_min"] if o else np.nan,
                     "transfers": o["transfers"] if o else np.nan,
                     "crowd_known": (o is not None and all(l["crowding"]["level"] != "不明"
                                                          for l in o["legs"] if l["mode"] == "bus"))})
    df = pd.DataFrame(rows)
    f = df[df.found]
    res = {
        "pairs": n, "found_%": round(df.found.mean() * 100, 1),
        "median_total_min": round(float(f.total_min.median()), 1),
        "direct_%": round(float((f.transfers == 0).mean() * 100), 1),
        "crowding_known_on_all_legs_%": round(float(f.crowd_known.mean() * 100), 1),
        "search_sec_median": round(float(df.sec.median()), 2), "search_sec_p90": round(float(df.sec.quantile(.9)), 2),
        "kmh_door_to_door_median": round(float((f.km / (f.total_min / 60)).median()), 1),
    }
    print(json.dumps(res, ensure_ascii=False, indent=1))
    out = C.RESULTS
    out.mkdir(exist_ok=True)
    (out / "planner_coverage.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
