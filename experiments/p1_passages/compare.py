"""補間した通過（docs 17章）の比較: 今のモデル（60m の通過で作成）と、補間した通過で作り直したモデルを、
同じ正解（補間した通過から作った、検証週 10/25〜31）で測る。

python experiments/p1_passages/compare.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "p1_journey"))
from bridge_compare import paired, top_metrics  # noqa: E402

A, B = HERE / "results_v1_truthv2", HERE / "results_v2"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 240)
    res = {}
    for name, tag in {"前もって計画": "", "今すぐ出る": "_live"}.items():
        a, b = pd.read_csv(A / f"journey_replay_samples{tag}.csv"), pd.read_csv(B / f"journey_replay_samples{tag}.csv")
        res[(name, "今のモデル")] = top_metrics(a)
        res[(name, "補間で作り直し")] = top_metrics(b)
        print(f"{name}: " + paired(a, b))
    print(pd.DataFrame(res).T.to_string())
    for f in ("p1_metrics.json", "journey_arrive_metrics.json"):
        print(f"\n== {f}")
        for d in (A, B):
            print(d.name, json.dumps(json.loads((d / f).read_text(encoding="utf-8")), ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
