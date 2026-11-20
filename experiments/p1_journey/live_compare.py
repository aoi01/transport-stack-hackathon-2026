"""「今すぐ出る」の 16.6（余裕だけ直した）と 16.7（乗り遅れの規則・外れ方を入れた中央値で順位）を、検証週の同じ 600 組で比べる。

python experiments/p1_journey/live_compare.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh.live_excess import classify  # noqa: E402

RUNS = {
    "16.6 余裕だけ": ROOT / "experiments/p1_journey/out/journey_replay_samples_live_v3_safe.csv",
    "16.7 乗り遅れ込み": ROOT / "results/journey_replay_samples_live.csv",
}
RNG = np.random.default_rng(0)


def top_metrics(df: pd.DataFrame) -> dict:
    top = df[df["rank"] == 0]
    ok = top[top.status == "ok"]
    err = ok.pred_s - ok.actual_s
    ape = (err.abs() / ok.actual_s * 100)
    s = ok[ok.safe_s.notna()]
    w = top[top.src0.map(classify) == "upstream"]
    w2 = w[w.wait0_pred_s <= 120]
    late = lambda x: float(((x.wait0_act_s - x.wait0_pred_s).fillna(np.inf) > 600).mean() * 100)
    return {
        "再現できた": len(ok), "誤差の中央値_%": round(float(ape.median()), 1),
        "平均の偏り_分": round(float(err.mean()) / 60, 1), "誤差の中央値_分": round(float(err.median()) / 60, 1),
        "±5分_%": round(float((err.abs() <= 300).mean() * 100), 1), "±10分_%": round(float((err.abs() <= 600).mean() * 100), 1),
        "バスが来ない_%": round(float((top.status == "nobus").mean() * 100), 1),
        "余裕あり": len(s), "余裕の内_%": round(float((s.actual_s <= s.safe_s + 59).mean() * 100), 1),
        "手前のバス2分以内_件": len(w2), "うち10分以上長い_%": round(late(w2), 1) if len(w2) else None,
        "手前のバス全体の10分以上長い_%": round(late(w), 1),
    }


def fastest(df: pd.DataFrame) -> float:
    hit = n = 0
    for _, g in df.groupby("pair"):
        ok = g[g.actual_s.notna()]
        if len(ok) < 2:
            continue
        n += 1
        hit += ok.loc[ok.pred_s.idxmin(), "actual_s"] == ok.actual_s.min()
    return round(hit / max(n, 1) * 100, 1)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    dfs = {k: pd.read_csv(v) for k, v in RUNS.items()}
    res = {k: {**top_metrics(d), "実際に最速を選んだ_%": fastest(d)} for k, d in dfs.items()}
    print(pd.DataFrame(res).T.to_string())
    # 両方とも 1 位の案を再現できた組で、誤差の中央値の差（組ごとのブートストラップ）
    a, b = [d[(d["rank"] == 0) & (d.status == "ok")].set_index("pair") for d in dfs.values()]
    common = a.index.intersection(b.index)
    ea = (a.loc[common, "pred_s"] - a.loc[common, "actual_s"]).abs() / a.loc[common, "actual_s"] * 100
    eb = (b.loc[common, "pred_s"] - b.loc[common, "actual_s"]).abs() / b.loc[common, "actual_s"] * 100
    same = (a.loc[common, "actual_s"] == b.loc[common, "actual_s"]).mean() * 100
    boots = []
    idx = np.arange(len(common))
    for _ in range(2000):
        s = RNG.choice(idx, len(idx))
        boots.append(np.median(eb.to_numpy()[s]) - np.median(ea.to_numpy()[s]))
    print(f"\n同じ {len(common)} 組（1 位の案が同じ実際の所要時間 {same:.0f}%）: 誤差の中央値 {ea.median():.1f}% → {eb.median():.1f}%"
          f"（差 {np.median(eb) - np.median(ea):+.1f} ポイント、95% 区間 {np.quantile(boots, 0.025):+.1f}〜{np.quantile(boots, 0.975):+.1f}）")
    ma, mb = (a.loc[common, "pred_s"] - a.loc[common, "actual_s"]), (b.loc[common, "pred_s"] - b.loc[common, "actual_s"])
    print(f"  平均の偏り {ma.mean() / 60:+.1f} → {mb.mean() / 60:+.1f} 分、±10 分 {(ma.abs() <= 600).mean() * 100:.1f}% → {(mb.abs() <= 600).mean() * 100:.1f}%")


if __name__ == "__main__":
    main()
