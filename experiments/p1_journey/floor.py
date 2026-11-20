"""経路全体の誤差のうち、その日の偶然（バスがいつ来るか）で避けられない分（ノイズの床）を見積もる。

1 位の案（今の順位、再現できた 247 組）について、予測を次のものに置き換えて誤差を比べる:
  今の予測
  学習期間の日ごとの再現の中央値（dayreplay.py の dr_med）
  神託 A: 検証週のほかの日（同じ平日/休日、その日を除く）の日ごとの再現の中央値
          ＝ 検証週の運行の様子は知っているが、その日の偶然は知らない予測
  神託 B: 検証週のその日も含めた中央値
神託 A の誤差が、学習期間だけで作る予測ではまず越えられない目安になる。
使い方: python -X utf8 experiments/p1_journey/floor.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.waitmodel import PassageTimetable  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dayreplay import next_pass  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def totals(pt, legs, sec, dt, walk_last, skip_k=None):
    out = []
    for k in pt.days_of[dt]:
        if k == skip_k:
            continue
        t = sec
        ok = True
        for lg in legs:
            t += lg.walk_before_s
            b = next_pass(pt, lg.route_id, lg.i, dt, k, t)
            if b is None:
                ok = False
                break
            t = b + lg.pred_ride_s
        if ok:
            out.append(t + walk_last - sec)
    return np.asarray(out, float)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    o = pd.read_parquet(OUT / "options_dr.parquet")
    lg = pd.read_parquet(OUT / "legs.parquet")
    top = o[(o["rank"] == 0) & o.actual_s.notna()].copy()
    te = PassageTimetable(C.TEST_DAYS)
    kday = {d: k for k, d in enumerate(C.TEST_DAYS)}
    lgs = {k: g.sort_values("leg") for k, g in lg[lg["rank"] == 0].groupby("pair")}
    a, b = [], []
    for r in top.itertuples():
        dep = pd.Timestamp(r.depart)
        sec = dep.hour * 3600 + dep.minute * 60 + dep.second
        legs = list(lgs[r.pair].itertuples())
        ta = totals(te, legs, sec, r.day_type, r.walk_last_s, skip_k=kday[dep.date()])
        tb = totals(te, legs, sec, r.day_type, r.walk_last_s)
        a.append(np.median(ta) if len(ta) else np.nan)
        b.append(np.median(tb) if len(tb) else np.nan)
    top["oracle_a"], top["oracle_b"] = a, b

    def m(p, act):
        p = p.fillna(top.pred_s)
        e = (p - act) / act
        return {"medAPE_%": round(float(np.median(np.abs(e)) * 100), 1), "median_rel_err_%": round(float(np.median(e) * 100), 1),
                "mean_err_min": round(float(np.mean(p - act) / 60), 1)}
    res = {"n": int(len(top)),
           "今の予測": m(top.pred_s, top.actual_s),
           "学習期間の日ごとの再現（中央値）": m(top.dr_med, top.actual_s),
           "神託A: 検証週のほかの日の中央値": m(top.oracle_a, top.actual_s),
           "神託B: その日も含めた検証週の中央値": m(top.oracle_b, top.actual_s),
           "神託A が使えた割合_%": round(float(top.oracle_a.notna().mean() * 100), 1)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (OUT / "floor.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
