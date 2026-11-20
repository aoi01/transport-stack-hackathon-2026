"""「今すぐ出る」検索の 1 本目の待ちの外れ方（docs 16.6）。

リアルタイムの 1 本目の待ち（手前を走るバスの到着予測・折り返してくるバス・前のバスからの経過）は点の予測なので、
余裕を見た到着（85% 点）に待ちのばらつきが入っていなかった。検証週では見えていたバスが乗る停留所に来ない場面が 15% あり、
85% 点の内に着いたのは 68.7% だけだった（16.5）。

ここでは学習期間の中だけで「予測した待ち」と「実際に最初に来たバスまでの待ち」の差（外れ方）を集める:
  部品（運行間隔・折り返しの組・実際の発車・過去の通過）は 10/1〜17 だけで作り、10/18〜24 の 600 組で「今すぐ出る」を
  検索して（python -m tsh.validate_journeys livecal）、上位 3 案の 1 本目について 差 = 実際 − 予測 を記録する。
  3 時間以内にバスが来なかったものは inf（着けない）として入れる。
出どころ（手前のバス / 折り返し / 経過）と予測した待ちの長さで分け、差の分位点を 40 個だけ持つ。
経路検索（Planner._replay）は、待ち = max(予測 + 差, 0) の 40 通りそれぞれで到着を出し、
全部を合わせた 85% 点を余裕を見た到着にする（乗り換えから先は過去の日ごとの再現、乗車時間のばらつきも足す）。

作り方: python -m tsh.live_excess（results/journey_replay_samples_live_cal.csv から data/processed/serve/live_wait_excess.json）
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from . import common as C

PATH = C.PROCESSED / "serve" / "live_wait_excess.json"
N_Q = 40            # 持っておく分位点の数（乗り換えの案はこの数だけ過去の日ごとの再現を回す）
MIN_N = 30          # 区分に少なくともこれだけの件数が無ければ、上の区分（出どころ全体 → リアルタイム全体）を使う
# 予測した待ちの区切り（2 分・15 分・30 分）。較正の週（10/18〜24）だけを見て決めた（16.6）:
# 手前のバスで 2 分以内と出たものは 24% で 10 分以上長かった（停留所をちょうど過ぎたバスを「もうすぐ来る」と数える）、
# 2〜30 分は 7〜15%、30 分を超えると 38%
PRED_EDGES_S = [120.0, 900.0, 1800.0]


def classify(src: str | None) -> str | None:
    """1 本目の待ちの出どころ → 区分。過去の記録（過去の実績・実際の通過の時刻表・実際の発車の時刻表）は None。"""
    if not src:
        return None
    if src.startswith("リアルタイム"):
        return "upstream"
    if "折り返" in src:
        return "chain"
    if src.startswith("前のバスが"):
        return "elapsed"
    return None


def _bin(pred_s: float) -> int:
    return int(np.searchsorted(PRED_EDGES_S, pred_s, side="right"))


def _quantiles(e: np.ndarray) -> list:
    lv = (np.arange(N_Q) + 0.5) / N_Q
    q = np.quantile(e, lv, method="inverted_cdf")
    return [None if not np.isfinite(x) else round(float(x), 1) for x in q]


def fit(samples: pd.DataFrame) -> dict:
    """samples: src0, wait0_pred_s, wait0_act_s（NaN＝3 時間以内に来なかった）。"""
    df = samples.copy()
    df["cls"] = df.src0.map(classify)
    df = df[df.cls.notna()].copy()
    df["e"] = (df.wait0_act_s - df.wait0_pred_s).fillna(np.inf)
    df["bin"] = df.wait0_pred_s.map(_bin)
    out = {"n_q": N_Q, "pred_edges_s": PRED_EDGES_S, "all": _quantiles(df.e.to_numpy()), "n_all": int(len(df)),
           "classes": {}, "stats": {}}
    for cls, g in df.groupby("cls"):
        c = {"n": int(len(g)), "q": _quantiles(g.e.to_numpy()) if len(g) >= MIN_N else None, "bins": {}}
        for b, gb in g.groupby("bin"):
            if len(gb) >= MIN_N:
                c["bins"][str(int(b))] = {"n": int(len(gb)), "q": _quantiles(gb.e.to_numpy())}
        out["classes"][cls] = c
    # 確認用: 区分ごとの件数・来なかった割合・10 分以上長かった割合・差の中央値と 85% 点
    for (cls, b), g in df.groupby(["cls", "bin"]):
        e = g.e.to_numpy()
        out["stats"][f"{cls}/{b}"] = {"n": int(len(g)), "nobus_%": round(float(np.mean(~np.isfinite(e))) * 100, 1),
                                      "late10_%": round(float(np.mean(e > 600)) * 100, 1),
                                      "median_min": round(float(np.median(e)) / 60, 1),
                                      "q85_min": round(float(np.quantile(e, 0.85, method="inverted_cdf")) / 60, 1)}
    return out


def load() -> dict | None:
    if not PATH.exists():
        return None
    return json.loads(PATH.read_text(encoding="utf-8"))


def samples_for(ex: dict | None, src: str | None, pred_s: float):
    """この出どころ・予測の待ちに対する差の分位点（秒の配列、来ない分は inf）。区分が無ければ None。"""
    cls = classify(src)
    if ex is None or cls is None:
        return None
    c = ex["classes"].get(cls)
    q = None
    if c is not None:
        b = c["bins"].get(str(_bin(pred_s)))
        q = b["q"] if b is not None else c["q"]
    if q is None:
        q = ex["all"]
    return np.array([np.inf if x is None else x for x in q], float)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    src = C.RESULTS / "journey_replay_samples_live_cal.csv"
    df = pd.read_csv(src)
    ex = fit(df)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(ex, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"n_all": ex["n_all"], "classes": {k: {"n": v["n"], "bins": {b: x["n"] for b, x in v["bins"].items()}}
                                                        for k, v in ex["classes"].items()},
                      "stats": ex["stats"]}, ensure_ascii=False, indent=1))
    print(f"→ {PATH}")


if __name__ == "__main__":
    main()
