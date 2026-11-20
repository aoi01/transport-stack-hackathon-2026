"""経路の選び方（順位の付け方）と、出す所要時間の作り方を比べる（dayreplay.py の出力を使う）。

選び方（各組で、点の最も小さい案を 1 位にする）:
  S0 今      : 点 = 今の予測（区間ごとの予測の和）
  S1 日ごと  : 点 = 学習期間の日ごとの再現の中央値（バスが来なかった日は捨てる）
  S2 日ごと（来なかった日も入れる）: 点 = 着けなかった日を inf として入れた中央値。半分以上の日に着けない案は選ばない
  S3 今＋足切り: 点 = 今の予測。ただし学習期間に着けた日が半分未満の案は選ばない
出す所要時間は、S2 は「着けなかった日も入れた中央値」、ほかは点と同じ。どの組も、候補が全部選べないときは S0 と同じ案。
学習期間（10/1〜24）だけで作る。検証週で決めた値は無い（半分＝中央値の定義から）。

比べるもの:
  1 位の案の状態: 再現できた / 乗る停留所に 3 時間以内にバスが来ない / 乗ったバスが降りる停留所まで追えない
  再現できた 1 位の案の誤差、実際に最速だった割合と後悔（実際の差）
使い方: python -X utf8 experiments/p1_journey/rank_eval.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"


def status(lg: pd.DataFrame) -> pd.Series:
    st = {}
    for (p, r), g in lg.sort_values("leg").groupby(["pair", "rank"]):
        s = "ok"
        for x in g.itertuples():
            if np.isnan(x.act_ride_s):
                s = "nobus" if not x.reached_board else "untracked"
                break
        st[(p, r)] = s
    return pd.Series(st)


def metrics(pred, act):
    e = (pred - act) / act
    return {"n": int(len(act)), "medAPE_%": round(float(np.median(np.abs(e)) * 100), 1),
            "median_rel_err_%": round(float(np.median(e) * 100), 1),
            "mean_err_min": round(float(np.mean(pred - act) / 60), 1),
            "within_10min_%": round(float(np.mean(np.abs(pred - act) <= 600) * 100), 1),
            "within_15min_%": round(float(np.mean(np.abs(pred - act) <= 900) * 100), 1)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    o = pd.read_parquet(OUT / "options_dr.parquet")
    lg = pd.read_parquet(OUT / "legs.parquet")
    st = status(lg)
    o["status"] = [st.get((p, r), "ok") for p, r in zip(o.pair, o["rank"])]
    o.loc[o.actual_s.notna(), "status"] = "ok"
    served = o.dr_served.fillna(1.0)
    strategies = {
        "S0 今": (o.pred_s, o.pred_s),
        "S1 日ごと（来なかった日は捨てる）": (o.dr_med.fillna(o.pred_s), o.dr_med.fillna(o.pred_s)),
        "S2 日ごと（来なかった日も入れる）": (o.dr_all_med.fillna(o.pred_s), o.dr_all_med.where(np.isfinite(o.dr_all_med), o.pred_s)),
        "S3 今＋足切り（着けた日が半分未満は選ばない）": (o.pred_s.where(served >= 0.5, np.inf), o.pred_s),
    }
    res = {}
    picks = {}
    for nm, (score, shown) in strategies.items():
        o["score"], o["shown"] = score.values, shown.values
        rows = []
        for p, g in o.groupby("pair"):
            if np.isfinite(g.score).any():
                c = g.loc[g.score.idxmin()]
            else:
                c = g[g["rank"] == 0].iloc[0]
            rows.append({"pair": p, "rank": int(c["rank"]), "status": c.status, "pred": c.shown, "act": c.actual_s,
                         "q85": c.dr_all_q85})
        P = pd.DataFrame(rows).set_index("pair")
        picks[nm] = P
        ok = P[P.status == "ok"]
        res[nm] = {"1位が今と違う組_%": None,
                   "1位の案の状態_%": {k: round(float((P.status == k).mean() * 100), 1) for k in ("ok", "nobus", "untracked")},
                   "再現できた1位の案の誤差": metrics(ok.pred, ok.act)}
        # 余裕を見た時間＝日ごとの再現の 85% 点（着けなかった日も入れる）。有限のときに実際がその内に着いた割合
        fin = ok[np.isfinite(ok.q85)]
        res[nm]["85%点が出せた_%"] = round(float(np.isfinite(ok.q85).mean() * 100), 1)
        res[nm]["85%点以内に着いた_%"] = round(float((fin.act <= fin.q85).mean() * 100), 1) if len(fin) else None
        res[nm]["85%点−予測の平均（分）"] = round(float((fin.q85 - fin.pred).mean() / 60), 1) if len(fin) else None
    base = picks["S0 今"]
    for nm, P in picks.items():
        res[nm]["1位が今と違う組_%"] = round(float((P["rank"] != base["rank"]).mean() * 100), 1)
        both = P[(P.status == "ok") & (base.status == "ok")]
        b0 = base.loc[both.index]
        res[nm]["両方再現できた組で実際の所要時間の平均（今 → この方式, 分）"] = [round(float(b0.act.mean() / 60), 1), round(float(both.act.mean() / 60), 1)]
        # 実際に最速だったか（再現できた案が 2 つ以上ある組）。選んだ案が再現できないときは外れとする
        hit, reg, n = 0, [], 0
        for p, g in o.groupby("pair"):
            okg = g[g.status == "ok"]
            if len(okg) < 2:
                continue
            n += 1
            best = okg.actual_s.min()
            c = P.loc[p]
            if c.status == "ok":
                hit += c.act <= best + 1e-6
                reg.append(c.act - best)
        res[nm]["実際に最速の案を選んだ_%（再現できた案が2つ以上の組）"] = round(hit / n * 100, 1)
        res[nm]["後悔の平均（分、選んだ案が再現できた組）"] = round(float(np.mean(reg) / 60), 1)
        res[nm]["比べた組"] = n
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (OUT / "rank_eval.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
