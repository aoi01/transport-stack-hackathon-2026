"""経路全体の誤差を、待ち時間・乗車時間・乗り換えの待ちに分ける（12.4 の再現と同じ 600 組）。

tsh.validate_journeys と同じ乱数で同じ組・出発時刻を選び、学習期間だけのモデルで経路検索する。
上位 3 案だけでなく、評価した候補（最大 40 案）を全部、検証週の GPS で再現し、
案ごと・乗る区間ごとに「予測した待ち・乗車」と「実際の待ち・乗車」を残す。
これで次のことを調べる:
  - 1 位の案の誤差のうち、最初の待ち・乗車・乗り換えの待ちがそれぞれ何分か
  - 予測が最も短い案を選ぶことによる偏り（勝者の呪い）: 1 位の案と、ほかの案の偏りの差
  - 順位の付け方を変えたとき（あとで offline に比べる）の実際の所要時間と誤差

出力: experiments/p1_journey/out/legs.parquet（乗る区間ごと）、options.parquet（案ごと）
使い方: python -X utf8 experiments/p1_journey/decompose.py [old]
  old: 待ち時間を過去の到着間隔だけで出す（14 章より前の方式）
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.planner import Planner  # noqa: E402
from tsh.segmodel import SegModel  # noqa: E402
from tsh.validate_journeys import Replay, schedule_option  # noqa: E402
from tsh.validate_p1 import load_test_passages  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def ride_detail(rp: Replay, rid, d, i, j, t_arrive_stop: float):
    """Replay.ride と同じ規則で (乗車時刻, 降車時刻 or None, i を通った便の数) を返す。"""
    cum = rp.cum.get(rid)
    best = None
    for seqs, ts in rp.trips.get((rid, d), []):
        if seqs.min() > i or seqs.max() < i:
            continue
        ti = float(np.interp(cum[i], cum[seqs], ts))
        if ti < t_arrive_stop or ti - t_arrive_stop > 3 * 3600:
            continue
        if best is None or ti < best[0]:
            tj = float(np.interp(cum[j], cum[seqs], ts)) if seqs.max() >= j else None
            best = (ti, tj)
    return best


def main(plan_wait: bool = True, tag: str = "", n_pairs: int = 600):
    sys.stdout.reconfigure(encoding="utf-8")
    rng = np.random.default_rng(2026)          # tsh.validate_journeys.RNG と同じ
    t_start = time.time()
    P = Planner("train")
    P.seg = SegModel(train_only=True)
    if plan_wait:
        from tsh.waitmodel import PassageTimetable
        P.plan_wait = PassageTimetable(C.TRAIN_DAYS)
    ps = load_test_passages()
    rp = Replay(ps, P.tt.cum)
    st = C.stops()
    xy = st[["stop_lat", "stop_lon"]].to_numpy()
    legs, opts_rows = [], []
    pairs = tries = 0
    while pairs < n_pairs and tries < n_pairs * 5:
        tries += 1
        a, b = rng.integers(len(xy), size=2)
        km = float(C.dist_m(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1])) / 1000
        if not 3 <= km <= 15:
            continue
        d = C.TEST_DAYS[int(rng.integers(len(C.TEST_DAYS)))]
        dep = datetime(d.year, d.month, d.day) + timedelta(seconds=int(rng.integers(7 * 3600, 21 * 3600)))
        res = P.plan(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], dep, max_options=40)
        if not res["options"]:
            continue
        t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
        for k, o in enumerate(res["options"]):
            t = t0
            ok = True
            nb = 0
            walk_before = 0.0
            for leg in o["legs"]:
                if leg["mode"] == "walk":
                    t += leg["minutes"] * 60
                    walk_before = leg["minutes"] * 60
                    continue
                r = ride_detail(rp, leg["route_id"], d, leg["board"]["seq"], leg["alight"]["seq"], t) if ok else None
                row = {"pair": pairs, "rank": k, "leg": nb, "route_id": leg["route_id"],
                       "i": leg["board"]["seq"], "j": leg["alight"]["seq"], "walk_before_s": walk_before,
                       "pred_wait_s": leg["wait_min"] * 60, "pred_ride_s": leg["ride_min"] * 60,
                       "pred_ride_p85_s": (leg["ride_min_p85"] or np.nan) * 60, "wait_source": leg["wait_source"],
                       "ride_tt_s": (leg["ride_min_timetable"] or np.nan) * 60,
                       "act_wait_s": np.nan, "act_ride_s": np.nan, "reached_board": r is not None}
                if r is not None:
                    row["act_wait_s"] = r[0] - t
                    if r[1] is not None:
                        row["act_ride_s"] = r[1] - r[0]
                        t = r[1]
                    else:
                        ok = False
                else:
                    ok = False
                legs.append(row)
                nb += 1
            sch = schedule_option(P, o, dep) if k < 3 else None
            opts_rows.append({"pair": pairs, "km": km, "depart": dep, "day_type": C.day_type(d), "rank": k,
                              "n_opts": len(res["options"]), "transfers": o["transfers"],
                              "pred_s": o["total_min"] * 60, "pred_walk_s": o["walk_min"] * 60,
                              "walk_last_s": o["legs"][-1]["minutes"] * 60,
                              "pred_wait_s": o["wait_min"] * 60, "pred_ride_s": o["ride_min"] * 60,
                              "perceived_s": o["perceived_min"] * 60,
                              "actual_s": (t - t0) if ok else np.nan, "sched_s": sch})
        pairs += 1
        if pairs % 50 == 0:
            print(f"  {pairs} 組（{time.time() - t_start:.0f}s）", flush=True)
    pd.DataFrame(legs).to_parquet(OUT / f"legs{tag}.parquet", index=False)
    pd.DataFrame(opts_rows).to_parquet(OUT / f"options{tag}.parquet", index=False)
    print("書いた", OUT, f"{time.time() - t_start:.0f}s")


if __name__ == "__main__":
    old = len(sys.argv) > 1 and sys.argv[1] == "old"
    main(plan_wait=not old, tag="_old" if old else "")
