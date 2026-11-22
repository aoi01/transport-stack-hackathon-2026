"""「今すぐ出る」で、乗り換え（2 本目）の待ちを、出発の時点で見えている 2 本目の路線のバスから出すと良くなるかを測る（検証週）。

理由（alt_eval.py、10/25〜31 の 1000 組）: 乗り換えの待ちは誤差の 2 乗の合計の約 3 割を占める。出発の時点で手前を走る
2 本目の路線のバスが見えていれば、その到着予測で乗り換えの乗車時刻の誤差の中央値が、乗り換えまで 20 分以内なら
7.3 → 2.9 分になった（36 組）。20 分より先は良くならなかった。
そこで乗り換えの停留所に着く予測が出発から 20 分以内のときだけ、2 本目の待ちを見えているバスから出し
（SimLive.transfer_fn）、所要時間の分布（_live_dist）にも入れる。同じ組（err_diag.py と同じ乱数の種 2027）で今の版と比べる。
使い方: PYTHONPATH="src;experiments/p1_passages" python experiments/p1_passages/transfer_live.py [組の数 [乱数の種]]
種 2027 以外では、新しい版で一度も乗り換えに見えているバスを使わなかった組は今の版と同じ結果になるので、今の版を計算しない
（速くするため）。出力の名前には種が付く。

本番につなぐ条件（種 2028 で数を増やして確かめる前に決めた）:
  1. 使った組で、所要時間の誤差の絶対値の差（新 − 今）の平均の 95% 区間（ブートストラップ）が 0 より下
  2. 使った組で、余裕を見た到着時刻までに着いた割合の低下が 5 ポイント以内
  3. 使った組で、実際の所要時間の差（新 − 今）の平均の 95% 区間の上が +2 分以内（悪い案を選ぶようにならない）
  4. 全部の組で、誤差の中央値が悪くならない
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from tsh import common as C

from err_diag import legs_detail, setup
from intercept import record, summary

SRC = "乗り換えの手前"


def boot_ci(x, k: int = 4000):
    x = np.asarray(x, float)
    g = np.random.default_rng(0)
    m = x[g.integers(len(x), size=(k, len(x)))].mean(axis=1)
    return [round(float(x.mean()), 2), round(float(np.quantile(m, 0.025)), 2), round(float(np.quantile(m, 0.975)), 2)]


def main(n: int = 1000, seed: int = 2027) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    RNG = np.random.default_rng(seed)
    tag = "" if seed == 2027 else f"_s{seed}"
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
        args = (xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], dep)
        row = {"pair": len(rows), "km": km, "depart": dep}
        tf = sim.transfer_fn(d, dep)
        fired = []

        def lt(rid, i, t):
            v = tf(rid, i, t)
            if v is not None:
                fired.append(1)
            return v
        for name, f in (("xfer", lt), ("base", None)):
            if name == "base" and not fired and seed != 2027:
                row["base"] = row["xfer"]     # どの候補でも使わなかったので、今の版と同じ
                break
            r = P.plan(*args, max_options=3, live_wait=sim.wait_fn(d, dep), live_transfer=f)
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
        row["fired"] = bool(fired)
        rows.append(row)
        if len(rows) % 100 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)

    res = {"pairs": len(rows)}
    for name in ("base", "xfer"):
        res[name] = summary(rows, name)
    used = [r for r in rows if any(SRC in (l["src"] or "") for l in r["xfer"]["legs"])]
    res["新しい版で乗り換えに見えているバスを使った組"] = {"n": len(used),
                                           **({k: summary(used, k) for k in ("base", "xfer")} if used else {})}
    # 乗り換えの乗車時刻の誤差（見えているバスを使った区間だけ。区間ごとに実際の前の区間から辿った乗車と比べる）
    e = []
    for r in used:
        l = r["xfer"]["legs"][1]
        if l["board_act"] is not None:
            e.append((l["board_act"] - (l["t_stop_pred"] + l["wait_pred_s"])) / 60)
    if e:
        e = np.array(e)
        res["見えているバスを使った乗り換えの乗車時刻（実際−予測）"] = {
            "n": len(e), "誤差の絶対値_中央値_分": round(float(np.median(np.abs(e))), 1),
            "中央値_分": round(float(np.median(e)), 1), "10分以上ずれた_%": round(float(np.mean(np.abs(e) >= 10)) * 100, 1)}
    for sub, rs in (("全部", rows), ("使った組", used)):
        both = [r for r in rs if r["base"]["actual_s"] is not None and r["xfer"]["actual_s"] is not None]
        if not both:
            continue
        e_b = np.array([abs(r["base"]["pred_s"] - r["base"]["actual_s"]) for r in both]) / 60
        e_x = np.array([abs(r["xfer"]["pred_s"] - r["xfer"]["actual_s"]) for r in both]) / 60
        dl = np.array([r["xfer"]["actual_s"] - r["base"]["actual_s"] for r in both]) / 60
        bias_b = np.array([r["base"]["pred_s"] - r["base"]["actual_s"] for r in both]) / 60
        bias_x = np.array([r["xfer"]["pred_s"] - r["xfer"]["actual_s"] for r in both]) / 60
        res[f"両方再現できた組（{sub}）"] = {
            "n": len(both), "誤差の絶対値_中央値_分（今 / 新）": [round(float(np.median(e_b)), 1), round(float(np.median(e_x)), 1)],
            "誤差の絶対値_平均_分（今 / 新）": [round(float(np.mean(e_b)), 1), round(float(np.mean(e_x)), 1)],
            "予測−実際_中央値_分（今 / 新）": [round(float(np.median(bias_b)), 1), round(float(np.median(bias_x)), 1)],
            "実際の所要時間の差_平均_分（新 − 今）": round(float(np.mean(dl)), 2),
            "実際の所要時間の差_中央値_分（新 − 今）": round(float(np.median(dl)), 2),
            "誤差の絶対値の差_平均と95%区間_分（新 − 今）": boot_ci(e_x - e_b),
            "実際の所要時間の差_平均と95%区間_分（新 − 今）": boot_ci(dl)}
    res["どこかの候補で使った組_%"] = round(float(np.mean([r["fired"] for r in rows])) * 100, 1)
    res["1位の案が変わった組_%"] = round(float(np.mean([r["base"]["routes"] != r["xfer"]["routes"]
                                                  or r["base"]["board"] != r["xfer"]["board"] for r in rows])) * 100, 1)
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    print(txt)
    (C.RESULTS / f"transfer_live_metrics{tag}.json").write_text(txt, encoding="utf-8")
    with open(C.RESULTS / f"transfer_live_samples{tag}.pkl", "wb") as f:
        pickle.dump(rows, f)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000, int(sys.argv[2]) if len(sys.argv) > 2 else 2027)
