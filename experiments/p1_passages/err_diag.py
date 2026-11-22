"""「今すぐ出る」の 1 位の案を検証週の GPS で再現し、区間ごとの予測と実際を細かく記録する（誤差の理由を探す材料）。

reach.py の今の版と同じ設定・同じ組の引き方（乱数の種 2027）で、組を増やして記録する。
区間ごとに: 路線・乗る/降りる停留所の番号・路線の停留所の数・待ちの出どころ・予測の待ちと乗車、
予測の「停留所に着く時刻」と実際の「停留所に着く時刻」（前の区間の実際から）・実際に乗った時刻・降りた時刻。
出力: results/err_diag_samples.pkl（元データ由来の行単位データなのでコミットしない）
使い方: PYTHONPATH="src;experiments/p1_passages" python experiments/p1_passages/err_diag.py [組の数]
"""
from __future__ import annotations

import pickle
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from tsh import common as C
from tsh.live_excess import load as load_excess
from tsh.plan_calib import load as load_calib
from tsh.planner import Planner
from tsh.segmodel import SegModel
from tsh.validate_journeys import Replay, SimLive, load_passages
from tsh.waitmodel import PassageTimetable

RNG = np.random.default_rng(2027)


def setup():
    P = Planner("train")
    P.seg = SegModel(train_only=True)
    P.plan_wait = PassageTimetable(C.TRAIN_DAYS)
    P.plan_replay = True
    P.keep_tot = False
    P.plan_calib = load_calib()
    P.live_excess = load_excess()
    rp = Replay(load_passages(C.TEST_DAYS), P.tt.cum, tt=P.tt)
    sim = SimLive(P, rp, C.TRAIN_DAYS)
    return P, rp, sim


def legs_detail(rp, o, d, t0):
    """区間ごとの記録と、止まった区間（ok / nobusN / untrackedN）。"""
    t_act, t_pred, out, n = t0, t0, [], 0
    status = "ok"
    for leg in o["legs"]:
        if leg["mode"] == "walk":
            t_act += leg["minutes"] * 60
            t_pred += leg["minutes"] * 60
            continue
        rid, i, j = leg["route_id"], leg["board"]["seq"], leg["alight"]["seq"]
        rec = {"n": n, "route_id": rid, "i": i, "j": j, "L": len(rp.cum.get(rid, [])),
               "src": leg["wait_source"], "wait_pred_s": leg["wait_min"] * 60, "ride_pred_s": leg["ride_min"] * 60,
               "t_stop_pred": t_pred, "t_stop_act": t_act, "board_act": None, "alight_act": None}
        out.append(rec)
        t_pred += (leg["wait_min"] + leg["ride_min"]) * 60
        if status != "ok":
            n += 1
            continue
        r = rp.ride_detail(rid, d, i, j, t_act)
        if r is None:
            status = f"nobus{n}"
        else:
            rec["board_act"], rec["alight_act"] = r
            if r[1] is None:
                status = f"untracked{n}"
            else:
                t_act = r[1]
        n += 1
    return out, status


def main(n: int = 1000) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    t_start = time.time()
    P, rp, sim = setup()
    xy = C.stops()[["stop_lat", "stop_lon"]].to_numpy()
    rows, tries = [], 0
    while len(rows) < n and tries < n * 5:
        tries += 1
        a, b = RNG.integers(len(xy), size=2)
        km = float(C.dist_m(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1])) / 1000
        if not 3 <= km <= 15:
            continue
        d = C.TEST_DAYS[int(RNG.integers(len(C.TEST_DAYS)))]
        dep = datetime(d.year, d.month, d.day) + timedelta(seconds=int(RNG.integers(7 * 3600, 21 * 3600)))
        t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
        r = P.plan(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], dep, max_options=3, live_wait=sim.wait_fn(d, dep))
        if not r["options"]:
            continue
        o = r["options"][0]
        legs, status = legs_detail(rp, o, d, t0)
        t_end = None
        if status == "ok":
            t_end = legs[-1]["alight_act"] + o["legs"][-1]["minutes"] * 60
        rows.append({"pair": len(rows), "km": km, "date": d, "depart": dep, "t0": t0,
                     "o": (xy[a, 0], xy[a, 1]), "dest": (xy[b, 0], xy[b, 1]),
                     "pred_s": o["total_min"] * 60, "actual_s": (t_end - t0) if t_end else None, "status": status,
                     "transfers": o["transfers"], "walk_s": [l["minutes"] * 60 for l in o["legs"] if l["mode"] == "walk"],
                     "total_source": o.get("total_source"), "legs": legs})
        if len(rows) % 100 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)
    with open(C.RESULTS / "err_diag_samples.pkl", "wb") as f:
        pickle.dump(rows, f)
    print(f"→ {C.RESULTS / 'err_diag_samples.pkl'}（{len(rows)} 組、{time.time() - t_start:.0f}s）")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
