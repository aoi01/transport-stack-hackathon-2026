"""試す順番 1: 検証週（10/25〜31）の誤差を、日付・時間帯・曜日・層ごとに分ける（外部データは使わない）。

元にするのは、検証で保存した標本（results/ の *_samples.csv）。
  乗車時間: p1_segml_samples.csv（20,000 区間。区間 LightGBM の過去のみ／過去＋直近）
  待ち時間: p1_wait_samples.csv（3,000 件。採用した方式を W1・W2・W4 から組み立てる）
  待ち時間込み: p1_door_samples.csv と上の待ち時間
  経路全体: journey_replay_samples.csv（1 位の案）
指標: 誤差の絶対値の割合の中央値（MedAPE）と、符号つきの誤差の中央値（予測 − 実測、実測に対する割合。負は短く見積もり）。
使い方: python -X utf8 experiments/p1_external/diagnose.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "results"


def stat(pred, actual) -> pd.Series:
    e = (np.asarray(pred) - np.asarray(actual)) / np.asarray(actual)
    return pd.Series({"n": len(e), "MedAPE%": np.median(np.abs(e)) * 100, "符号つき%": np.median(e) * 100})


def table(df, pred, actual, by):
    return df.groupby(by).apply(lambda g: stat(g[pred], g[actual])).round(1)


def main():
    pd.set_option("display.width", 200)
    # 乗車時間
    s = pd.read_csv(R / "p1_segml_samples.csv")
    s["t"] = pd.to_datetime(s.t0, unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
    s["date"] = s.t.dt.strftime("%m-%d %a")
    live, hist = "pred_区間LightGBM（過去＋直近）", "pred_区間LightGBM（過去のみ）"
    print("== 乗車時間（区間 LightGBM、過去＋直近）全体", stat(s[live], s.actual_s).round(1).to_dict())
    print("   過去のみ", stat(s[hist], s.actual_s).round(1).to_dict())
    print("\n日付ごと（過去＋直近 / 過去のみ）")
    print(pd.concat([table(s, live, "actual_s", "date"), table(s, hist, "actual_s", "date").add_suffix("_過去のみ")], axis=1).to_string())
    s["band"] = pd.cut(s.hr0, [-1, 6, 10, 16, 20, 24], labels=["0-6", "7-10", "11-16", "17-20", "21-23"])
    print("\n日付 × 時間帯（過去＋直近、MedAPE%）")
    print(s.groupby(["date", "band"]).apply(lambda g: stat(g[live], g.actual_s)["MedAPE%"]).unstack().round(1).to_string())
    print("\n日付 × 時間帯（過去のみ、符号つき%）")
    print(s.groupby(["date", "band"]).apply(lambda g: stat(g[hist], g.actual_s)["符号つき%"]).unstack().round(1).to_string())

    # 待ち時間（採用: 手前のバスが見えれば W1、見えず折り返しがあれば (W4+W2)/2、どちらも無ければ W2）
    w = pd.read_csv(R / "p1_wait_samples.csv", parse_dates=["depart"])
    w["adopt"] = np.where(w.up, w.W1, np.where(w.chain, 0.5 * w.W4 + 0.5 * w.W2, w.W2))
    w["aw"] = w.actual_wait.clip(lower=30)
    w["date"] = w.depart.dt.strftime("%m-%d %a")
    w["layer"] = np.where(w.up, "手前のバスが見える", np.where(w.chain, "折り返しだけ見える", "どちらも見えない"))
    print("\n== 待ち時間（採用した方式）全体", stat(w.adopt, w.aw).round(1).to_dict())
    print(table(w, "adopt", "aw", "layer").to_string())
    print(table(w, "adopt", "aw", "date").to_string())

    # 待ち時間込み
    d = pd.read_csv(R / "p1_door_samples.csv", parse_dates=["depart"]).merge(
        w[["route_id", "i", "j", "depart", "adopt", "layer"]], on=["route_id", "i", "j", "depart"])
    d["tot"] = d.actual_s + d.actual_wait_s
    d["pred"] = d.realtime_s.fillna(d.model_s) + d.adopt
    d["date"] = d.depart.dt.strftime("%m-%d %a")
    print("\n== 待ち時間込み 全体", stat(d.pred, d.tot).round(1).to_dict())
    print(table(d, "pred", "tot", "date").to_string())

    # 経路全体（1 位の案）
    j = pd.read_csv(R / "journey_replay_samples.csv", parse_dates=["depart"])
    j = j[(j["rank"] == 0) & j.actual_s.notna()].copy()
    j["date"] = j.depart.dt.strftime("%m-%d %a")
    print("\n== 経路全体（1 位の案）全体", stat(j.pred_s, j.actual_s).round(1).to_dict())
    print(table(j, "pred_s", "actual_s", "date").to_string())
    print(table(j, "pred_s", "actual_s", "transfers").to_string())


if __name__ == "__main__":
    main()
