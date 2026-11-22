"""「今すぐ出る」で、手前にバスが見えないときの 1 本目の待ちを、折り返し・始発の発車の時刻表・経過時間の組み合わせではなく、
過去の実際の通過の時刻表（その停留所を実際に通った時刻、PassageTimetable）に任せると良くなるかを測る（検証週）。

理由（err_diag.py・alt_eval.py、10/25〜31 の 1000 組）:
  - 始発の発車の時刻表は「次のバスは始発から出る」とみなすが、便の 45% は始発付近以外から走り始める（車庫から途中へ入る・
    1 日に 2 系統以上を走る車両が 86%）。予測が 13 分長すぎた（中央値）
  - 折り返しは「反対方向の路線のバスが終点で折り返して来る」とみなすが、車両が系統を移る・終点の手前で終わるので外れる。
    そのうち 26% は 3 時間以内にバスが来なかった
  - 同じ区間で停留所の実際の通過の時刻表に置き換えると、誤差の中央値が 27.5 → 15.5 分、16.1 → 10.8 分
見えないときは live_wait が None を返し、計画側は過去の通過の時刻表と過去の日ごとの再現（着けた日の割合・較正）を使う。
同じ組で今の版と比べる。
使い方: PYTHONPATH="src;experiments/p1_passages" python experiments/p1_passages/nolive_hist.py [組の数]
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from tsh import common as C
from tsh.validate_journeys import SimLive

from err_diag import legs_detail, setup
from intercept import record, summary

RNG = np.random.default_rng(2027)


class SimUpstreamOnly:
    """手前を走るバスが見えるときだけリアルタイムの待ちを返す。"""

    def __init__(self, base: SimLive):
        self.base = base

    def wait_fn(self, d, now):
        f = self.base.wait_fn(d, now)

        def g(route_id, i, t):
            r = f(route_id, i, t)
            if r is None or "手前" not in (r[1] or ""):
                return None
            return r
        return g


def main(n: int = 1000) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    t_start = time.time()
    P, rp, sim = setup()
    sims = {"base": sim, "hist": SimUpstreamOnly(sim)}
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
        row = {"pair": len(rows), "km": km, "depart": dep}
        for name, s in sims.items():
            r = P.plan(*args, max_options=3, live_wait=s.wait_fn(d, dep))
            if not r["options"]:
                row = None
                break
            o = r["options"][0]
            rec = record(rp, o, d, dep, t0)
            rec["legs"], rec["leg_status"] = legs_detail(rp, o, d, t0)
            rec["unreliable"] = bool(o.get("unreliable", False))
            row[name] = rec
        if row is None:
            continue
        rows.append(row)
        if len(rows) % 100 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)

    res = {"pairs": len(rows)}
    for name in sims:
        res[name] = summary(rows, name)
    # 1 本目の待ちが見えないバス由来だった組（今の版で）だけ
    nv = [r for r in rows if "手前" not in (r["base"]["src0"] or "")]
    res["今の版で1本目にバスが見えなかった組"] = {"n": len(nv), **{k: summary(nv, k) for k in sims}}
    both = [r for r in rows if r["base"]["actual_s"] is not None and r["hist"]["actual_s"] is not None]
    for sub, rs in (("全部", both), ("見えなかった組", [r for r in both if "手前" not in (r["base"]["src0"] or "")])):
        if not rs:
            continue
        e_b = np.array([abs(r["base"]["pred_s"] - r["base"]["actual_s"]) for r in rs]) / 60
        e_h = np.array([abs(r["hist"]["pred_s"] - r["hist"]["actual_s"]) for r in rs]) / 60
        dl = np.array([r["hist"]["actual_s"] - r["base"]["actual_s"] for r in rs]) / 60
        res[f"両方再現できた組（{sub}）"] = {
            "n": len(rs), "誤差の絶対値_中央値_分（今 / 新）": [round(float(np.median(e_b)), 1), round(float(np.median(e_h)), 1)],
            "誤差の絶対値_平均_分（今 / 新）": [round(float(np.mean(e_b)), 1), round(float(np.mean(e_h)), 1)],
            "実際の所要時間の差_平均_分（新 − 今）": round(float(np.mean(dl)), 2),
            "実際の所要時間の差_中央値_分（新 − 今）": round(float(np.median(dl)), 2),
            "新が1分以上速い/遅い_%": [round(float(np.mean(dl <= -1)) * 100, 1), round(float(np.mean(dl >= 1)) * 100, 1)]}
    res["1位の案が変わった組_%"] = round(float(np.mean([r["base"]["routes"] != r["hist"]["routes"]
                                                  or r["base"]["board"] != r["hist"]["board"] for r in rows])) * 100, 1)
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    print(txt)
    (C.RESULTS / "nolive_hist_metrics.json").write_text(txt, encoding="utf-8")
    import pickle
    with open(C.RESULTS / "nolive_hist_samples.pkl", "wb") as f:
        pickle.dump(rows, f)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
