"""本数の多い路線の、乗り換えなしの区間だけで精度を測る（検証週 10/25〜31）。

本数の多い路線: 学習期間の平日 7〜21 時の 1 時間あたりの便数の平均が上位 50 の路線。
各組: その路線の停留所 i → j（路線に沿って 2〜8 km）、検証週の 7〜21 時のランダムな時刻に出発。
停留所から停留所へ検索し、上位 3 案のうち乗り換えなしで一番上の案を測る。前もって計画と今すぐ出るの両方。
使い方: PYTHONPATH=src python experiments/p1_passages/major_direct.py [組の数]
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from tsh import common as C
from tsh.live_excess import load as load_excess
from tsh.plan_calib import load as load_calib
from tsh.planner import Planner
from tsh.segmodel import SegModel
from tsh.validate_journeys import Replay, SimLive, load_passages, replay_option_status, schedule_option
from tsh.waitmodel import PassageTimetable

RNG = np.random.default_rng(7)


def summarize(rows, key):
    r = [x for x in rows if x[key] is not None and x[key]["act"] is not None]
    if not r:
        return {}
    act = np.array([x[key]["act"] for x in r]); pred = np.array([x[key]["pred"] for x in r])
    ape = np.abs(pred - act) / act
    out = {"n": len(r), "median_err_%": round(float(np.median(ape)) * 100, 1),
           "within_5min_%": round(float(np.mean(np.abs(pred - act) <= 300)) * 100, 1),
           "within_10min_%": round(float(np.mean(np.abs(pred - act) <= 600)) * 100, 1),
           "median_bias_min": round(float(np.median(pred - act)) / 60, 1),
           "actual_median_min": round(float(np.median(act)) / 60, 1)}
    sch = np.array([x[key]["sched"] if x[key]["sched"] is not None else np.nan for x in r])
    out["timetable_median_err_%"] = round(float(np.nanmedian(np.abs(sch - act) / act)) * 100, 1)
    sf = [(x[key]["act"], x[key]["safe"]) for x in r if x[key]["safe"] is not None]
    if sf:
        out["arrived_by_safe_%"] = round(float(np.mean([a <= s + 59 for a, s in sf])) * 100, 1)
    st = [x[key]["status"] for x in rows if x[key] is not None]
    out["nobus_%"] = round(st.count("nobus") / len(st) * 100, 1)
    out["untracked_%"] = round(st.count("untracked") / len(st) * 100, 1)
    return out


def main(n: int = 300) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
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

    f = pd.read_parquet(C.PROCESSED / "all/route_freq.parquet")
    f = f[(f.day_type == "weekday") & f.hr.between(7, 20)].assign(route_id=lambda x: x.route_id.astype(str))
    top = f.groupby("route_id").trips_per_hour.mean().sort_values(ascending=False)
    major = [r for r in top.index if r in P.tt.cum][:50]
    print("本数の多い路線 50: 1 時間あたり", round(top[major].min(), 1), "〜", round(top[major].max(), 1), "便", flush=True)
    st = C.stops().set_index("stop_id")

    rows, tries = [], 0
    while len(rows) < n and tries < n * 20:
        tries += 1
        rid = major[int(RNG.integers(len(major)))]
        cum, ids = P.tt.cum[rid], P.tt.stop_ids[rid]
        i = int(RNG.integers(len(ids) - 1))
        js = [j for j in range(i + 1, len(ids)) if 2000 <= cum[j] - cum[i] <= 8000]
        if not js:
            continue
        j = js[int(RNG.integers(len(js)))]
        a, b = st.loc[ids[i]], st.loc[ids[j]]
        d = C.TEST_DAYS[int(RNG.integers(len(C.TEST_DAYS)))]
        dep = datetime(d.year, d.month, d.day) + timedelta(seconds=int(RNG.integers(7 * 3600, 21 * 3600)))
        t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
        row = {"route": rid, "km": (cum[j] - cum[i]) / 1000, "depart": dep}
        for key, lw in (("plan", None), ("live", sim.wait_fn(d, dep))):
            res = P.plan(a.stop_lat, a.stop_lon, b.stop_lat, b.stop_lon, dep, max_options=3, live_wait=lw)
            o = next((o for o in res["options"] if o["transfers"] == 0), None)
            if o is None:
                row[key] = None
                continue
            act, stt = replay_option_status(rp, o, d, t0)
            safe = None
            if o.get("arrive_safe"):
                hh, mm = map(int, o["arrive_safe"].split(":"))
                safe = (datetime(dep.year, dep.month, dep.day, hh, mm) - dep).total_seconds()
                safe = safe + 86400 if safe < 0 else safe
            row[key] = {"pred": o["total_min"] * 60, "act": act, "status": stt, "safe": safe,
                        "sched": schedule_option(P, o, dep), "same_route": o["legs"][1]["route_id"] == rid,
                        "wait_pred": o["legs"][1]["wait_min"] * 60}
        rows.append(row)
        if len(rows) % 50 == 0:
            print(f"  {len(rows)} 組", flush=True)

    res = {"pairs": len(rows), "plan": summarize(rows, "plan"), "live": summarize(rows, "live")}
    # 短め（2〜5 km）と長め（5〜8 km）
    for lo, hi in ((2, 5), (5, 8)):
        sub = [r for r in rows if lo <= r["km"] < hi]
        res[f"{lo}-{hi}km"] = {"plan": summarize(sub, "plan"), "live": summarize(sub, "live")}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    flat = [{"route": r["route"], "km": r["km"], "depart": r["depart"], "mode": k, **(r[k] or {})}
            for r in rows for k in ("plan", "live")]
    pd.DataFrame(flat).to_csv(C.RESULTS / "major_direct_samples.csv", index=False)
    (C.RESULTS / "major_direct_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
