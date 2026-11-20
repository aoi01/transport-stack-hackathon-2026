"""乗り換えの案を捨てる規則を直す前（16.8）と後（16.9）で、経路全体の検証を比べる。

直す前の結果は out/prefilter/、後は results/。直したのは「2 本目の路線に出発地から直接乗れて 5 分以上速くならない
乗り換えの案を捨てる」ときに比べる直通を、後ろへ回していないものだけにしたこと（tsh.planner.Planner.plan）。

python experiments/p1_journey/filter_compare.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge_compare import paired, top_metrics  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PRE = ROOT / "experiments/p1_journey/out/prefilter"
NEW = ROOT / "results"
TAGS = {"前もって計画": "", "今すぐ出る": "_live", "較正の週（livecal）": "_live_cal"}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 240)
    res = {}
    for name, tag in TAGS.items():
        f_pre, f_new = PRE / f"journey_replay_samples{tag}.csv", NEW / f"journey_replay_samples{tag}.csv"
        if not f_pre.exists() or not f_new.exists():
            continue
        pre, new = pd.read_csv(f_pre), pd.read_csv(f_new)
        res[(name, "直す前")] = top_metrics(pre)
        res[(name, "直した後")] = top_metrics(new)
        a = pre[pre["rank"] == 0].set_index("pair")
        b = new[new["rank"] == 0].set_index("pair")
        c = a.index.intersection(b.index)
        chg = c[(a.loc[c, "pred_s"] - b.loc[c, "pred_s"]).abs() >= 60]
        print(f"== {name}: 1 位の案の予測が 1 分以上変わった組 {len(chg)} / {len(c)}")
        if len(chg):
            x = pd.DataFrame({"予測_前": a.loc[chg, "pred_s"] / 60, "予測_後": b.loc[chg, "pred_s"] / 60,
                              "実際_前": a.loc[chg, "actual_s"] / 60, "実際_後": b.loc[chg, "actual_s"] / 60,
                              "状態_前": a.loc[chg, "status"], "状態_後": b.loc[chg, "status"],
                              "後ろ_前": a.loc[chg, "unreliable"], "後ろ_後": b.loc[chg, "unreliable"],
                              "乗換_前": a.loc[chg, "transfers"], "乗換_後": b.loc[chg, "transfers"]})
            print(x.round(1).head(30).to_string())
        print("  " + paired(pre, new) + "\n")
    print(pd.DataFrame(res).T.to_string())
    plan, live = pd.read_csv(NEW / "journey_replay_samples.csv"), pd.read_csv(NEW / "journey_replay_samples_live.csv")
    print("\n前もって計画 → 今すぐ出る（直した後）: " + paired(plan, live))


if __name__ == "__main__":
    main()
