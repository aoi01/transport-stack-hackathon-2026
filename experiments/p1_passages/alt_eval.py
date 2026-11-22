"""err_diag.py の記録（1 位の案の区間）の上で、待ちの別の出し方を試す（案の選び直しはしない。区間の当たり方だけ）。

1 本目の待ち（手前にバスが見えないとき）:
  今の版 / 停留所 i の実際の通過の時刻表（PassageTimetable.wait）/ 前のバスからの経過で条件づけた残りの待ち
2 本目の待ち（乗り換え）: 予測の乗車時刻（予測の着く時刻 + 待ち）を
  今の版（過去の実際の通過の時刻表）/ 出発の時点で見えていた 2 本目の路線のバスの到着予測（着く時刻より後で最初のもの）
  と過去の時刻表の早いほう
正解の別の定義: 停留所 i を最初に通ったバスではなく、「i を通って降りる停留所 j まで行ったバス」の最初のもの
（行き先の表示を見て、手前で終わるバスには乗らない）。
使い方: PYTHONPATH="src;experiments/p1_passages" python experiments/p1_passages/alt_eval.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from tsh import common as C
from tsh.validate_journeys import _Links

from err_diag import setup

IST = timezone(timedelta(hours=5, minutes=30))


def dt_of(ep):
    return datetime.fromtimestamp(ep, IST).replace(tzinfo=None)


def first_reaching(rp, rid, d, i, j, t):
    """t 以降 3 時間以内に i を通り、j まで行った最初のバスの (乗車, 降車)。"""
    cum = rp.cum.get(rid)
    best = None
    for seqs, ts in rp.trips.get((rid, d), []):
        if seqs.min() > i or seqs.max() < j:
            continue
        ti = float(np.interp(cum[i], cum[seqs], ts))
        if ti < t or ti - t > 3 * 3600:
            continue
        if best is None or ti < best[0]:
            best = (ti, float(np.interp(cum[j], cum[seqs], ts)))
    return best


def live_etas(sim, P, rid, i, d, now_ep):
    xy = P.seq_xy.get(rid)
    out = []
    if xy is None:
        return out
    for lat, lng, ts in sim.vehicles(rid, d, now_ep):
        dd = C.dist_m(lat, lng, xy[:, 0], xy[:, 1])
        k = int(np.argmin(dd))
        if dd[k] > 300 or k >= i:
            continue
        out.append(ts + P.tt.ride_sec(rid, k, i, dt_of(ts)))
    return sorted(out)


def stats(e):
    e = np.asarray([x for x in e if x is not None and np.isfinite(x)], float) / 60
    if not len(e):
        return None
    return {"n": int(len(e)), "誤差の絶対値_中央値_分": round(float(np.median(np.abs(e))), 1),
            "実際−予測_中央値_分": round(float(np.median(e)), 1),
            "10分以上ずれた_%": round(float(np.mean(np.abs(e) >= 10)) * 100, 1),
            "誤差の絶対値_平均_分": round(float(np.mean(np.abs(e))), 1)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import pickle
    rows = pickle.load(open(C.RESULTS / "err_diag_samples.pkl", "rb"))
    P, rp, sim = setup()
    res = {}
    # ---- 1 本目
    recs = []
    for r in rows:
        l = r["legs"][0]
        d, t = r["date"], l["t_stop_act"]
        src = l["src"] or ""
        cls = "upstream" if "手前" in src else ("chain" if "折り返し" in src else ("departures" if "始発を出る前" in src else "other"))
        act = l["board_act"] - t if l["board_act"] else None
        act2 = first_reaching(rp, l["route_id"], d, l["i"], l["j"], t)
        ptt = P.plan_wait.wait(l["route_id"], l["i"], dt_of(t))
        cond, _ = sim.wm.conditional_wait(l["route_id"], l["i"], dt_of(t), _Links(sim, d, r["t0"]))
        recs.append({"cls": cls, "pred": l["wait_pred_s"], "act": act, "act2": act2[0] - t if act2 else None,
                     "ptt": ptt, "cond": cond, "status": r["status"]})
    R = pd.DataFrame(recs)
    out0 = {}
    for cls, g in R.groupby("cls"):
        ok = g[g.act.notna()]
        o = {"n": len(g), "3時間来ない_%": round(float(g.act.isna().mean()) * 100, 1),
             "j まで行くバスが3時間来ない_%": round(float(g.act2.isna().mean()) * 100, 1),
             "今の版": stats(ok.act - ok.pred)}
        for k in ("ptt", "cond"):
            m = ok[ok[k].notna()]
            o[f"{k}（使えた {len(m)}）"] = {"今の版": stats(m.act - m.pred), "別の出し方": stats(m.act - m[k])}
        m = ok[ok.ptt.notna() & ok.cond.notna()]
        o["ptt と cond の平均"] = stats(m.act - (m.ptt + m.cond) / 2)
        m = g[g.act2.notna()]
        o["正解を「j まで行くバス」にしたとき 今の版"] = stats(m.act2 - m.pred)
        out0[cls] = o
    res["1本目の待ち"] = out0
    # ---- 2 本目
    recs = []
    for r in rows:
        if len(r["legs"]) < 2 or r["status"] not in ("ok", "nobus1", "untracked1"):
            continue
        l = r["legs"][1]
        d = r["date"]
        t_pred = l["t_stop_pred"]
        board_pred = t_pred + l["wait_pred_s"]
        etas = [e for e in live_etas(sim, P, l["route_id"], l["i"], d, r["t0"]) if e >= t_pred + C.CATCH_MIN_S]
        live = etas[0] if etas else None
        recs.append({"act_board": l["board_act"], "act_stop": l["t_stop_act"], "t_pred": t_pred, "board_pred": board_pred,
                     "live": live, "lead_min": (t_pred - r["t0"]) / 60})
    R = pd.DataFrame(recs)
    ok = R[R.act_board.notna()]
    out1 = {"n": len(R), "3時間来ない_%": round(float(R.act_board.isna().mean()) * 100, 1),
            "乗り換えの停留所に着く時刻（実際−予測）": stats(ok.act_stop - ok.t_pred),
            "乗車時刻 今の版": stats(ok.act_board - ok.board_pred)}
    m = ok[ok.live.notna()]
    out1[f"見えているバスで当たる（{len(m)}、{len(m) / max(len(ok), 1) * 100:.0f}%）"] = {
        "今の版": stats(m.act_board - m.board_pred),
        "見えているバスの到着": stats(m.act_board - m.live),
        "早いほう": stats(m.act_board - np.minimum(m.live, m.board_pred))}
    for lo, hi in ((0, 20), (20, 40), (40, 300)):
        mm = m[(m.lead_min >= lo) & (m.lead_min < hi)]
        out1[f"  出発から乗り換えまで {lo}〜{hi} 分"] = {"今の版": stats(mm.act_board - mm.board_pred),
                                                "見えているバス": stats(mm.act_board - mm.live),
                                                "早いほう": stats(mm.act_board - np.minimum(mm.live, mm.board_pred))}
    res["2本目の乗車時刻"] = out1
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    print(txt)
    (C.RESULTS / "alt_eval.json").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main()
