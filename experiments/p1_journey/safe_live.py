"""「今すぐ出る」の余裕を見た到着（85% 点）が、実際にどれだけ守られたか（docs 16.6）。

比べるもの（どれも 1 位の案）:
  前もって計画（16.3）          results/journey_replay_samples.csv
  今すぐ・点の予測（16.5）       out/journey_replay_samples_live_v2_pointsafe.csv
  今すぐ・外れ方入り（16.6）     results/journey_replay_samples_live.csv
  較正の週の内側の確認           results/journey_replay_samples_live_cal_check.csv
指標:
  守れた: 再現できた（ok）案のうち、余裕を見た到着（+59 秒）までに着いた割合（validate_journeys と同じ）
  来ない込み: バスが 3 時間来なかった案（nobus）も「守れなかった」に数えた割合
  出せない: 余裕を見た到着を出さなかった（15% より多くの場合に着けない）割合
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh.live_excess import classify  # noqa: E402

FILES = {
    "前もって計画（16.3）": ROOT / "results/journey_replay_samples.csv",
    "今すぐ・点の予測（16.5）": ROOT / "experiments/p1_journey/out/journey_replay_samples_live_v2_pointsafe.csv",
    "今すぐ・外れ方入り（16.6）": ROOT / "results/journey_replay_samples_live.csv",
    "較正の週・内側の確認": ROOT / "results/journey_replay_samples_live_cal_check.csv",
}


def summary(df: pd.DataFrame) -> dict:
    top = df[df["rank"] == 0]
    ok = top[top.status == "ok"]
    s_ok = ok[ok.safe_s.notna()]
    hit = s_ok.actual_s <= s_ok.safe_s + 59
    with_nb = top[top.status.isin(["ok", "nobus"]) & top.safe_s.notna()]
    hit_nb = (with_nb.status == "ok") & (with_nb.actual_s <= with_nb.safe_s + 59)
    return {
        "1位の案": len(top), "再現できた": len(ok),
        "余裕あり": len(s_ok), "守れた_%": round(hit.mean() * 100, 1),
        "来ない込み_%": round(hit_nb.mean() * 100, 1),
        "出せない_%（再現できた中）": round(ok.safe_s.isna().mean() * 100, 1),
        "余裕の幅_分（中央値）": round(float(np.median(s_ok.safe_s - s_ok.pred_s)) / 60, 1),
    }


def by_class(df: pd.DataFrame) -> pd.DataFrame:
    top = df[(df["rank"] == 0) & (df.status == "ok")].copy()
    top["区分"] = top.src0.map(lambda s: classify(s) or "過去の記録") if "src0" in top else "過去の記録"
    rows = []
    for c, g in top.groupby("区分"):
        s = g[g.safe_s.notna()]
        rows.append({"区分": c, "再現できた": len(g), "余裕あり": len(s),
                     "守れた_%": round(float((s.actual_s <= s.safe_s + 59).mean() * 100), 1) if len(s) else None,
                     "出せない_%": round(float(g.safe_s.isna().mean() * 100), 1)})
    return pd.DataFrame(rows)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 200)
    out = {}
    for name, f in FILES.items():
        if not f.exists():
            print("無い:", f)
            continue
        df = pd.read_csv(f)
        out[name] = summary(df)
        print(f"\n== {name}")
        print(by_class(df).to_string(index=False))
    print()
    print(pd.DataFrame(out).T.to_string())


if __name__ == "__main__":
    main()
