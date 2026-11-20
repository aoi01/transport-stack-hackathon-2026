"""1 位の案の最初の待ちが、なぜ予測（17.5 分）より実際（52.5 分）でずっと長いのかを切り分ける。

1 位の案と、それ以外の案の最初の区間について、出発時刻の「次のバスまで」を次の 3 つで比べる:
  train   学習期間（10/1〜24）の同じ平日/休日の各日の中央値（今の予測と同じ。4 時間以内に来なかった日は捨てる）
  test    検証週（10/25〜31）の同じ平日/休日の各日の中央値（同じ作り方）
  actual  再現で実際に乗った便までの待ち（検証週のその日）
さらに、学習期間のうち「4 時間以内にバスが来た日」の割合と、日ごとの待ちのばらつき（四分位の幅）も出す。
  - train と test が近く actual だけ長い → その日の偶然 ＋ 選び方の偏り
  - test も長い → 検証週に運行が変わった（または GPS が少ない）
使い方: python -X utf8 experiments/p1_journey/wait_gap.py
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

OUT = Path(__file__).resolve().parent / "out"
CAP = 4 * 3600


def gaps(pt, rid, i, dt, sec):
    se = pt.idx.get((str(rid), int(i), dt))
    if se is None:
        return np.array([])
    x = pt.v[se[0]:se[1]]
    out = []
    for k in pt.days_of[dt]:
        p = np.searchsorted(x, k * 86400 + sec)
        g = x[p] - (k * 86400 + sec) if p < len(x) and x[p] < (k + 1) * 86400 else np.inf
        out.append(g)
    return np.asarray(out, float)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    o = pd.read_parquet(OUT / "options.parquet")
    lg = pd.read_parquet(OUT / "legs.parquet")
    first = lg[lg.leg == 0].merge(o[["pair", "rank", "depart", "day_type"]], on=["pair", "rank"])
    first = first[first.act_wait_s.notna()]
    tr, te = PassageTimetable(C.TRAIN_DAYS), PassageTimetable(C.TEST_DAYS)
    rows = []
    for r in first.itertuples():
        dep = pd.Timestamp(r.depart)
        sec = dep.hour * 3600 + dep.minute * 60 + dep.second + r.walk_before_s
        g1, g2 = gaps(tr, r.route_id, r.i, r.day_type, sec), gaps(te, r.route_id, r.i, r.day_type, sec)
        ok1, ok2 = g1[g1 <= CAP], g2[g2 <= CAP]
        rows.append({"rank": r.rank, "pred": r.pred_wait_s, "act": r.act_wait_s,
                     "train_med": np.median(ok1) if len(ok1) >= 3 else np.nan,
                     "test_med": np.median(ok2) if len(ok2) >= 1 else np.nan,
                     "train_days": len(g1), "train_served": (len(ok1) / len(g1)) if len(g1) else np.nan,
                     "train_iqr": (np.quantile(ok1, 0.75) - np.quantile(ok1, 0.25)) if len(ok1) >= 3 else np.nan,
                     "test_served": (len(ok2) / len(g2)) if len(g2) else np.nan})
    d = pd.DataFrame(rows)
    res = {}
    for nm, g in (("1位", d[d["rank"] == 0]), ("2〜5位", d[d["rank"].between(1, 4)]), ("6位より下", d[d["rank"] >= 5])):
        res[nm] = {"n": int(len(g)),
                   "予測の平均（分）": round(float(g.pred.mean() / 60), 1),
                   "学習期間の中央値の平均（分）": round(float(g.train_med.mean() / 60), 1),
                   "検証週の中央値の平均（分）": round(float(g.test_med.mean() / 60), 1),
                   "実際の平均（分）": round(float(g.act.mean() / 60), 1),
                   "学習期間に4時間以内に来た日の割合_%": round(float(g.train_served.mean() * 100), 1),
                   "検証週に4時間以内に来た日の割合_%": round(float(g.test_served.mean() * 100), 1),
                   "学習期間の日ごとの四分位の幅の平均（分）": round(float(g.train_iqr.mean() / 60), 1),
                   "学習期間の日数の中央値": float(g.train_days.median())}
    # 1 位の案: 実際が予測より 30 分以上長かったものの内訳
    t = d[d["rank"] == 0]
    bad = t[t.act - t.pred > 1800]
    res["1位で30分以上長かった"] = {"n": int(len(bad)), "うち検証週の中央値も予測より30分以上長い": int((bad.test_med - bad.pred > 1800).sum()),
                            "学習期間に来た日の割合の平均_%": round(float(bad.train_served.mean() * 100), 1)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (OUT / "wait_gap.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    d.to_parquet(OUT / "wait_gap.parquet", index=False)


if __name__ == "__main__":
    main()
