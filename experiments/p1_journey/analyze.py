"""decompose.py の出力から、経路全体の誤差の内訳と、選び方の偏り（勝者の呪い）を出す。

使い方: python -X utf8 experiments/p1_journey/analyze.py [tag]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"


def med_ape(pred, act):
    return float(np.median(np.abs(pred - act) / act) * 100)


def main(tag=""):
    sys.stdout.reconfigure(encoding="utf-8")
    o = pd.read_parquet(OUT / f"options{tag}.parquet")
    lg = pd.read_parquet(OUT / f"legs{tag}.parquet")
    res = {}
    top = o[(o["rank"] == 0) & o.actual_s.notna()]
    res["top1"] = {"n": len(top), "medAPE_%": round(med_ape(top.pred_s, top.actual_s), 1),
                   "mean_err_min": round(float((top.pred_s - top.actual_s).mean() / 60), 1),
                   "median_err_min": round(float((top.pred_s - top.actual_s).median() / 60), 1),
                   "actual_mean_min": round(float(top.actual_s.mean() / 60), 1)}
    # 内訳（1 位の案、再現できたもの）: 誤差 = 予測 − 実際（−は短く予測）
    L = lg.merge(top[["pair"]], on="pair")
    L = L[L["rank"] == 0].copy()
    L["e_wait"] = L.pred_wait_s - L.act_wait_s
    L["e_ride"] = L.pred_ride_s - L.act_ride_s
    comp = {}
    for nm, sel in {"最初の待ち": L.leg == 0, "乗り換えの待ち": L.leg == 1}.items():
        x = L[sel]
        comp[nm] = {"n": int(len(x)), "pred_mean_min": round(float(x.pred_wait_s.mean() / 60), 1),
                    "act_mean_min": round(float(x.act_wait_s.mean() / 60), 1),
                    "mean_err_min": round(float(x.e_wait.mean() / 60), 1),
                    "median_err_min": round(float(x.e_wait.median() / 60), 1),
                    "medAPE_%": round(med_ape(x.pred_wait_s, x.act_wait_s.clip(lower=30)), 1)}
    x = L
    comp["乗車（全区間）"] = {"n": int(len(x)), "pred_mean_min": round(float(x.pred_ride_s.mean() / 60), 1),
                         "act_mean_min": round(float(x.act_ride_s.mean() / 60), 1),
                         "mean_err_min": round(float(x.e_ride.mean() / 60), 1),
                         "median_err_min": round(float(x.e_ride.median() / 60), 1),
                         "medAPE_%": round(med_ape(x.pred_ride_s, x.act_ride_s), 1)}
    res["内訳（1位の案）"] = comp
    # 待ちの予測の出どころ別（最初の待ち）
    w0 = L[L.leg == 0]
    res["最初の待ち：出どころ別"] = {
        s: {"n": int(len(g)), "mean_err_min": round(float(g.e_wait.mean() / 60), 1),
            "median_err_min": round(float(g.e_wait.median() / 60), 1),
            "medAPE_%": round(med_ape(g.pred_wait_s, g.act_wait_s.clip(lower=30)), 1)}
        for s, g in w0.groupby("wait_source")}
    # 勝者の呪い: 順位ごとの偏り（再現できた案）。同じ組の中で比べる
    ok = o[o.actual_s.notna()].copy()
    ok["rel_err"] = (ok.pred_s - ok.actual_s) / ok.actual_s
    by_rank = {}
    for r, g in ok.groupby(ok["rank"].clip(upper=10)):
        by_rank[int(r)] = {"n": int(len(g)), "mean_rel_err_%": round(float(g.rel_err.mean() * 100), 1),
                           "median_rel_err_%": round(float(g.rel_err.median() * 100), 1),
                           "medAPE_%": round(float(g.rel_err.abs().median() * 100), 1)}
    res["順位ごとの偏り（10 は 10 位以下）"] = by_rank
    # 最初の待ちの予測が短いほど 1 位になりやすいか: 1 位の案と 2〜5 位の案の、最初の待ちの誤差
    lw = lg[(lg.leg == 0) & lg.act_wait_s.notna()].copy()
    lw["e"] = lw.pred_wait_s - lw.act_wait_s
    res["最初の待ちの誤差：順位別（分）"] = {
        str(k): round(float(g.e.mean() / 60), 1) for k, g in lw.groupby(lw["rank"].clip(upper=5))}
    # 再現できない理由（1 位の案）
    t0 = o[o["rank"] == 0]
    res["再現"] = {"1位の案": int(len(t0)), "再現できた": int(t0.actual_s.notna().sum())}
    l0 = lg[lg["rank"] == 0]
    first = l0.groupby("pair").first()
    res["再現"]["最初の便が乗車停留所に 3 時間以内に来ない"] = int((~first.reached_board).sum())
    res["再現"]["乗った便が降車停留所まで追えない"] = int((first.reached_board & first.act_ride_s.isna()).sum())
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (OUT / f"analyze{tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
