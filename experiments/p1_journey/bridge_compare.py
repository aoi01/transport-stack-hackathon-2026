"""経路全体の検証を、正解で分かれて記録された便をつなぐ前（16.7 まで）と後（16.8）で比べる。

つなぐ前の結果は out/prebridge/、後は results/。予測（検索の結果）は同じなので、変わるのは正解だけ
（「今すぐ出る」は見えていたバスも少し変わる）。

python experiments/p1_journey/bridge_compare.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRE = ROOT / "experiments/p1_journey/out/prebridge"
NEW = ROOT / "results"
TAGS = {"前もって計画（16.3）": "", "今すぐ出る（16.7）": "_live", "較正の週（livecal）": "_live_cal",
        "区間ごとの和（sum）": "_sum", "到着間隔（old）": "_old"}
RNG = np.random.default_rng(0)


def top_metrics(df: pd.DataFrame) -> dict:
    top = df[df["rank"] == 0]
    ok = top[top.status == "ok"]
    err = ok.pred_s - ok.actual_s
    ape = err.abs() / ok.actual_s * 100
    sch = ok[ok.sched_s.notna()]
    s = ok[ok.safe_s.notna()] if "safe_s" in ok else ok.iloc[:0].assign(safe_s=[])
    st = top.status.value_counts(normalize=True) * 100
    return {
        "再現できた": len(ok), "来ない_%": round(float(st.get("nobus", 0)), 1),
        "追えない_%": round(float(st.get("untracked", 0)), 1),
        "誤差の中央値_%": round(float(ape.median()), 1), "予測−実際の中央値_分": round(float(err.median()) / 60, 1),
        "平均の偏り_分": round(float(err.mean()) / 60, 1),
        "±5分_%": round(float((err.abs() <= 300).mean() * 100), 1), "±10分_%": round(float((err.abs() <= 600).mean() * 100), 1),
        "時刻表_%": round(float(((sch.sched_s - sch.actual_s).abs() / sch.actual_s * 100).median()), 1),
        "余裕あり": len(s), "余裕の内_%": round(float((s.actual_s <= s.safe_s + 59).mean() * 100), 1) if len(s) else None,
        "最速を選んだ_%": fastest(df),
    }


def fastest(df: pd.DataFrame) -> float:
    hit = n = 0
    for _, g in df.groupby("pair"):
        ok = g[g.actual_s.notna() & g.sched_s.notna()]
        if len(ok) < 2:
            continue
        n += 1
        hit += ok.loc[ok.pred_s.idxmin(), "actual_s"] == ok.actual_s.min()
    return round(hit / max(n, 1) * 100, 1)


def paired(a: pd.DataFrame, b: pd.DataFrame) -> str:
    a = a[(a["rank"] == 0) & (a.status == "ok")].set_index("pair")
    b = b[(b["rank"] == 0) & (b.status == "ok")].set_index("pair")
    c = a.index.intersection(b.index)
    ea = ((a.loc[c, "pred_s"] - a.loc[c, "actual_s"]).abs() / a.loc[c, "actual_s"] * 100).to_numpy()
    eb = ((b.loc[c, "pred_s"] - b.loc[c, "actual_s"]).abs() / b.loc[c, "actual_s"] * 100).to_numpy()
    wa = ((a.loc[c, "pred_s"] - a.loc[c, "actual_s"]).abs() <= 600).mean() * 100
    wb = ((b.loc[c, "pred_s"] - b.loc[c, "actual_s"]).abs() <= 600).mean() * 100
    idx = np.arange(len(c))
    bs = [np.median(eb[s]) - np.median(ea[s]) for s in (RNG.choice(idx, len(idx)) for _ in range(2000))]
    return (f"同じ {len(c)} 組: 誤差の中央値 {np.median(ea):.1f}% → {np.median(eb):.1f}%（差 {np.median(eb) - np.median(ea):+.1f}、"
            f"95% 区間 {np.quantile(bs, 0.025):+.1f}〜{np.quantile(bs, 0.975):+.1f}）、±10 分 {wa:.1f}% → {wb:.1f}%")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 240)
    res = {}
    for name, tag in TAGS.items():
        f_pre, f_new = PRE / f"journey_replay_samples{tag}.csv", NEW / f"journey_replay_samples{tag}.csv"
        if not f_pre.exists() or not f_new.exists():
            continue
        pre, new = pd.read_csv(f_pre), pd.read_csv(f_new)
        res[(name, "つなぐ前")] = top_metrics(pre)
        res[(name, "つないだ後")] = top_metrics(new)
        # ほぼ同じ予測（1 位の案の予測の差が 1 分未満の組）で、正解がどう変わったか。
        # 「今すぐ出る」は外れ方の分布を作り直したので、予測が数秒ずつ変わる
        a = pre[pre["rank"] == 0].set_index("pair")
        b = new[new["rank"] == 0].set_index("pair")
        c = a.index.intersection(b.index)
        same = c[(a.loc[c, "pred_s"] - b.loc[c, "pred_s"]).abs() < 60]
        tr = pd.crosstab(a.loc[same, "status"], b.loc[same, "status"])
        both = same[(a.loc[same, "status"] == "ok") & (b.loc[same, "status"] == "ok")]
        d = (b.loc[both, "actual_s"] - a.loc[both, "actual_s"]) / 60
        print(f"== {name}: 1 位の予測の差が 1 分未満の {len(same)} 組。正解の状態（行: つなぐ前、列: 後）")
        print(tr.to_string())
        print(f"  両方で再現できた {len(both)} 組のうち、実際の所要時間が変わった {(d.abs() > 0.01).mean() * 100:.1f}%"
              f"（短くなった {(d < -0.01).sum()} 組、中央値 {d[d < -0.01].median():.1f} 分）")
        print("  " + paired(pre, new) + "\n")
    print(pd.DataFrame(res).T.to_string())
    # 今すぐ出る vs 前もって計画（つないだ後）
    plan, live = pd.read_csv(NEW / "journey_replay_samples.csv"), pd.read_csv(NEW / "journey_replay_samples_live.csv")
    print("\n前もって計画 → 今すぐ出る（つないだ後）: " + paired(plan, live))


if __name__ == "__main__":
    main()
