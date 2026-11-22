"""「今すぐ出る」で、乗る停留所を動いているバスとの合流点で選ぶと良くなるかを測る（検証週）。

今の検索は 1 つの路線につき乗る停留所を距離の概算だけで 1 つに決め、その停留所でだけリアルタイムの待ちを見る
（planner._candidates の「同じ路線の組み合わせは1つに」）。合流点の版は、800 m 以内にある同じ路線の別の停留所
（降りる停留所より手前）も候補に足し、停留所ごとに「歩いて着く時刻」と「見えているバスが来る時刻」から
待ちを出して、合計時間（live_excess の分布の中央値）が一番短いものを選ぶ。

同じ組（出発地・目的地・出発時刻）で今の版と合流点の版を両方検索し、1 位の案を検証週の GPS で再現して比べる。
使い方: PYTHONPATH=src python experiments/p1_passages/intercept.py [組の数]
"""
from __future__ import annotations

import json
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
from tsh.validate_journeys import Replay, SimLive, load_passages, replay_option_status
from tsh.waitmodel import PassageTimetable

RNG = np.random.default_rng(2026)
ALT_PER_CAND = 4          # 1 つの案につき足す別の乗車の停留所の数（歩く距離の短い順）


def expand(P: Planner, orig):
    def cand_x(o_lat, o_lng, d_lat, d_lng):
        cand, nO, nD = orig(o_lat, o_lng, d_lat, d_lng)
        O = P.near_stops(o_lat, o_lng)
        out, seen = [], set()
        for est, st in cand:
            out.append((est, st)); seen.add(st)
            bus0 = st[0]
            _, rid, i, k, s, s1 = bus0
            rest_bus = tuple(x for x in st[1:] if isinstance(x, tuple))
            walks = [x for x in st if not isinstance(x, tuple)]
            alts = []
            for s2, wm2 in O:
                if s2 == s:
                    continue
                for r, i2 in P.serving[s2]:
                    if r == rid and i2 < k and i2 != i:
                        alts.append((wm2, i2, s2))
            for wm2, i2, s2 in sorted(alts)[:ALT_PER_CAND]:
                st2 = (("bus", rid, i2, k, s2, s1),) + rest_bus + (wm2,) + tuple(walks[1:])
                if st2 not in seen:
                    seen.add(st2); out.append((est, st2))
        return out, nO, nD
    return cand_x


def plan_dedup(P, *a, **kw):
    """全部の案を評価して並べ、同じ路線の組み合わせは一番上だけ残す。"""
    res = P.plan(*a, max_options=500, **kw)
    seen, opts = set(), []
    for o in res["options"]:
        key = tuple(l["route_id"] for l in o["legs"] if l["mode"] == "bus")
        if key in seen:
            continue
        seen.add(key); opts.append(o)
    res["options"] = opts[:3]
    return res


def record(rp, o, d, dep, t0):
    act, stt = replay_option_status(rp, o, d, t0)
    safe = None
    if o.get("arrive_safe"):
        hh, mm = map(int, o["arrive_safe"].split(":"))
        safe = (datetime(dep.year, dep.month, dep.day, hh, mm) - dep).total_seconds()
        safe = safe + 86400 if safe < 0 else safe
    l0, w_walk = o["legs"][1], o["legs"][0]["minutes"] * 60
    r0 = rp.ride_detail(l0["route_id"], d, l0["board"]["seq"], l0["alight"]["seq"], t0 + w_walk)
    return {"pred_s": o["total_min"] * 60, "actual_s": act, "status": stt, "safe_s": safe,
            "walk0_s": w_walk, "wait0_pred_s": l0["wait_min"] * 60,
            "wait0_act_s": (r0[0] - t0 - w_walk) if r0 else None,
            "routes": "+".join(l["route_id"] for l in o["legs"] if l["mode"] == "bus"),
            "board": f'{l0["route_id"]}:{l0["board"]["seq"]}', "src0": l0["wait_source"],
            "transfers": o["transfers"]}


def summary(rows, key):
    tops = [r[key] for r in rows]
    ok = [x for x in tops if x["actual_s"] is not None]
    act = np.array([x["actual_s"] for x in ok]); pred = np.array([x["pred_s"] for x in ok])
    w_ok = [x for x in tops if x["wait0_act_s"] is not None]
    wa = np.array([x["wait0_act_s"] for x in w_ok]); wp = np.array([x["wait0_pred_s"] for x in w_ok])
    sf = [(x["actual_s"], x["safe_s"]) for x in ok if x["safe_s"] is not None]
    st = [x["status"] for x in tops]
    m = lambda v: round(float(v) / 60, 1)
    return {"n": len(tops), "replayable": len(ok),
            "status_%": {s: round(st.count(s) / len(st) * 100, 1) for s in ("ok", "nobus", "untracked")},
            "actual_min_median": m(np.median(act)), "actual_min_mean": m(np.mean(act)),
            "abs_err_min_median": m(np.median(np.abs(pred - act))),
            "ape_median_%": round(float(np.median(np.abs(pred - act) / act)) * 100, 1),
            "walk0_min_median": m(np.median([x["walk0_s"] for x in tops])),
            "wait0_act_min_median": m(np.median(wa)), "wait0_act_min_mean": m(np.mean(wa)),
            "wait0_abs_err_min_median": m(np.median(np.abs(wa - wp))),
            # 予測より 5 分以上長く待った（見えていたバスに乗れなかった）割合
            "wait0_missed_5min_%": round(float(np.mean(wa - wp > 300)) * 100, 1),
            "arrived_by_safe_%": round(float(np.mean([a <= s + 59 for a, s in sf])) * 100, 1) if sf else None}


def main(n: int = 600) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    t_start = time.time()
    P = Planner("train")
    P.seg = SegModel(train_only=True)
    P.plan_wait = PassageTimetable(C.TRAIN_DAYS)
    P.plan_replay = True
    P.keep_tot = False
    P.plan_calib = load_calib()
    P.live_excess = load_excess()
    ps = load_passages(C.TEST_DAYS)
    rp = Replay(ps, P.tt.cum, tt=P.tt)
    sim = SimLive(P, rp, C.TRAIN_DAYS)
    orig = P._candidates
    cand_x = expand(P, orig)
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
        args = (xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], dep)
        P._candidates = orig
        base = P.plan(*args, max_options=3, live_wait=sim.wait_fn(d, dep))
        if not base["options"]:
            continue
        P._candidates = cand_x
        icp = plan_dedup(P, *args, live_wait=sim.wait_fn(d, dep))
        rows.append({"pair": len(rows), "km": km, "depart": dep,
                     "base": record(rp, base["options"][0], d, dep, t0),
                     "icp": record(rp, icp["options"][0], d, dep, t0)})
        if len(rows) % 50 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)

    res = {"pairs": len(rows), "今の版": summary(rows, "base"), "合流点の版": summary(rows, "icp")}
    ch = [r for r in rows if r["base"]["board"] != r["icp"]["board"] or r["base"]["routes"] != r["icp"]["routes"]]
    chs = [r for r in rows if r["base"]["routes"] == r["icp"]["routes"] and r["base"]["board"] != r["icp"]["board"]]
    res["1位の乗る停留所が変わった組_%"] = round(len(chs) / len(rows) * 100, 1)
    res["1位の案（路線か乗る停留所）が変わった組_%"] = round(len(ch) / len(rows) * 100, 1)
    if ch:
        res["変わった組だけ"] = {"今の版": summary(ch, "base"), "合流点の版": summary(ch, "icp")}
        both = [r for r in ch if r["base"]["actual_s"] is not None and r["icp"]["actual_s"] is not None]
        if both:
            dlt = np.array([r["icp"]["actual_s"] - r["base"]["actual_s"] for r in both]) / 60
            res["変わった組の実際の所要時間の差（合流点 − 今、分）"] = {
                "n": len(both), "中央値": round(float(np.median(dlt)), 1), "平均": round(float(np.mean(dlt)), 1),
                "10/25/75/90%点": [round(float(x), 1) for x in np.percentile(dlt, [10, 25, 75, 90])],
                "合流点のほうが 1 分以上速い_%": round(float(np.mean(dlt <= -1)) * 100, 1),
                "合流点のほうが 1 分以上遅い_%": round(float(np.mean(dlt >= 1)) * 100, 1)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (C.RESULTS / "intercept_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    flat = [{"pair": r["pair"], "km": r["km"], "depart": r["depart"], "variant": k, **r[k]}
            for r in rows for k in ("base", "icp")]
    pd.DataFrame(flat).to_csv(C.RESULTS / "intercept_samples.csv", index=False)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 600)
