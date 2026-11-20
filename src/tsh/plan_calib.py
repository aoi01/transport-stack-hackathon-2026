"""前もって計画するときの、選ぶことによる偏りの較正（docs 17章）。

前もって計画する場合、各案の合計時間は「過去の同じ種類の日に同じ時刻（±10 分）に出ていたら」の再現の分布
（tsh.waitmodel.PassageTimetable.journey）の中央値、余裕を見た到着は 85% 点にしている。分布そのものは偏りが無くても、
40 ほどの候補から最も短い案を選ぶと、選ばれた案は「たまたま過去の日にバスがうまく来ていた案」になりやすく、
実際はそれより長くなる（最適化の呪い。停留所の通過の数え落としを直したら表に出た）。

学習期間の中だけで直す: 部品を 10/1〜17 だけで作り、10/18〜24 の 600 組で前もって計画を検索して
（python -m tsh.validate_journeys plancal）、1 位の案について「実際の所要時間が、再現の分布のどの位置に来たか」
u = P(再現 < 実際) + P(再現 = 実際)/2 を集める（降りる停留所まで追えた案だけ）。u の 50% 点・85% 点を p50・p85 とし、
経路検索では再現の分布の p50 点を合計時間、p85 点を余裕を見た到着にする（分位点の較正、Kuleshov ら ICML 2018）。
乗り換えの回数（0 回・1 回）で分ける（件数が MIN_N 未満なら全体の値）。

作り方: python -m tsh.plan_calib（results/journey_replay_samples_plan_cal.csv → data/processed/serve/plan_calib.json）
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from . import common as C

PATH = C.PROCESSED / "serve" / "plan_calib.json"
MIN_N = 50


def _levels(u: np.ndarray) -> dict:
    return {"n": int(len(u)), "p50": round(float(np.quantile(u, 0.5)), 3), "p85": round(float(np.quantile(u, 0.85)), 3)}


def fit(samples: pd.DataFrame) -> dict:
    df = samples[(samples["rank"] == 0) & samples.pit.notna()]
    out = {"levels": {"all": _levels(df.pit.to_numpy())}}
    for tr, g in df.groupby(df.transfers.clip(upper=1)):
        out["levels"][str(int(tr))] = _levels(g.pit.to_numpy()) if len(g) >= MIN_N else out["levels"]["all"]
    return out


def load() -> dict | None:
    return json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    src = C.RESULTS / f"journey_replay_samples_plan_cal{sys.argv[1] if len(sys.argv) > 1 else ''}.csv"
    cal = fit(pd.read_csv(src))
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(cal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(cal, ensure_ascii=False, indent=1), f"\n→ {PATH}")


if __name__ == "__main__":
    main()
