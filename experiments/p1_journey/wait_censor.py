"""前もって計画するときの待ち時間（実際の通過の時刻表、W11）で、「4 時間以内にバスが来なかった日」を捨てている影響。

今の tsh.waitmodel.PassageTimetable は、同じ平日/休日の各日について「出発時刻以降、次のバスまで」を出し、
4 時間以内に来なかった日を捨ててから中央値を取る。来なかった日を捨てると、待ち時間を短く見積もる方向に偏る。
ここでは同じ 3,000 件（results/p1_wait_samples.csv、検証週 10/25〜31、学習 10/1〜24）で比べる:
  drop    今の方式（来なかった日を捨てる、3 日分以上なければ None → 過去の到着間隔）
  censor  来なかった日を「4 時間待った」として中央値に入れる（打ち切り）
  frac    来なかった日の割合
使い方: python -X utf8 experiments/p1_journey/wait_censor.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.waitmodel import PassageTimetable  # noqa: E402

CAP = 4 * 3600


def gaps(pt: PassageTimetable, rid, i, t):
    dt = C.day_type(t.date())
    se = pt.idx.get((str(rid), int(i), dt))
    if se is None:
        return None
    x = pt.v[se[0]:se[1]]
    sec = t.hour * 3600 + t.minute * 60 + t.second
    out = []
    for k in pt.days_of[dt]:
        p = np.searchsorted(x, k * 86400 + sec)
        g = x[p] - (k * 86400 + sec) if p < len(x) and x[p] < (k + 1) * 86400 else np.inf
        out.append(min(g, np.inf))
    return np.asarray(out, float)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    w = pd.read_csv(C.ROOT / "results" / "p1_wait_samples.csv", parse_dates=["depart"], dtype={"route_id": str})
    a = w.actual_wait.clip(lower=30).to_numpy()
    base = w.W0.to_numpy()
    pt = PassageTimetable(C.TRAIN_DAYS)
    drop, cens, frac, q = [], [], [], {0.4: [], 0.5: [], 0.6: []}
    for r in w.itertuples():
        g = gaps(pt, r.route_id, r.i, r.depart.to_pydatetime())
        if g is None or len(g) == 0:
            drop.append(np.nan); cens.append(np.nan); frac.append(np.nan)
            for k in q:
                q[k].append(np.nan)
            continue
        ok = g[g <= CAP]
        drop.append(float(np.median(ok)) if len(ok) >= 3 else np.nan)
        gc = np.minimum(g, CAP)
        n_ok = int((g <= CAP).sum())
        cens.append(float(np.median(gc)) if n_ok >= 3 else np.nan)
        frac.append(1 - n_ok / len(g))
        for k in q:
            q[k].append(float(np.quantile(gc, k)) if n_ok >= 3 else np.nan)
    drop, cens, frac = map(np.asarray, (drop, cens, frac))

    def st(p):
        p = np.where(np.isnan(p), base, p)
        e = (p - a) / a
        return f"誤差の中央値 {np.median(np.abs(e)) * 100:5.1f}%  符号の中央値 {np.median(e) * 100:+6.1f}%  平均の偏り {np.mean(p - a) / 60:+6.1f} 分"
    print(f"{len(w)} 件。来なかった日がある標本 {np.nanmean(frac > 0) * 100:.1f}%、来なかった日の割合の平均 {np.nanmean(frac) * 100:.1f}%")
    print("  今（捨てる）      ", st(drop))
    print("  打ち切りで入れる  ", st(cens))
    for k in q:
        print(f"  打ち切り {int(k * 100)}% 点    ", st(np.asarray(q[k])))
    m = frac > 0
    print(f"  来なかった日がある標本だけ（{m.sum()} 件）: 実際の待ちの平均 {a[m].mean() / 60:.1f} 分")
    for nm, p in (("捨てる", drop), ("打ち切り", cens)):
        pp = np.where(np.isnan(p), base, p)[m]
        print(f"    {nm}: 予測の平均 {pp.mean() / 60:.1f} 分、誤差の中央値 {np.median(np.abs(pp - a[m]) / a[m]) * 100:.1f}%")


if __name__ == "__main__":
    main()
