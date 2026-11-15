"""問題2の検証。車内人数の実測（APC など）は無いので、ブリーフの評価方法に沿って次の4点で確かめる。

(1) 既知のパターン: 時間帯別の平均車内人数に朝・夕のピークが出るか、平日と休日で違うか。
(2) 時間的な安定性（予測としての検証）: 10/1〜10/24 から作った推定で、10/25〜10/31 の推定を当てられるか。
    マス（路線 × 区間 × 平日/休日 × 時間帯）ごとの相関・混雑レベルの一致率を、信頼度の段階別に出す。
(3) 全体量の整合: 拡大後の1日の乗車人数を、公表されている DTC＋クラスターバスの利用者数と比べる。
(4) 停留所の対応づけの検証: 車両番号のある券について、発券時刻のそのバスの GPS 位置と、
    名前から対応づけた乗車停留所の距離を測る（名前の照合が正しいかの独立した確認）。
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from . import common as C
from . import crowding as K

OUT = C.ROOT / "results"
OFFICIAL_DAILY_RIDERS = 4_141_000   # 2023年 DTC＋クラスター 41.41 lakh/日（Delhi Economic Survey 等の報道値）


def hourly_profile(a: pd.DataFrame) -> pd.DataFrame:
    w = a.assign(wl=a.load * a.trips_total)
    g = w.groupby(["day_type", "hr"]).agg(wl=("wl", "sum"), t=("trips_total", "sum"))
    return (g.wl / g.t).unstack(0).round(1)


def stability(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    k = ["route_id", "seq", "day_type", "hr"]
    m = train[k + ["load", "n_tickets", "level", "confidence"]].merge(
        test[k + ["load", "n_tickets", "level"]], on=k, suffixes=("_tr", "_te"))
    res = {}
    lv = {name: i for i, name in enumerate(K.LEVELS)}
    for conf in ["高", "中", "低", "全体"]:
        x = m if conf == "全体" else m[m.confidence == conf]
        x = x[x.n_tickets_te >= 5]   # 検証側も最低限の標本があるマスだけ
        if len(x) < 10:
            continue
        a, b = x.level_tr.map(lv), x.level_te.map(lv)
        res[conf] = {
            "cells": int(len(x)),
            "pearson_r": round(float(np.corrcoef(x.load_tr, x.load_te)[0, 1]), 3),
            "spearman_r": round(float(x.load_tr.rank().corr(x.load_te.rank())), 3),
            "MAE_people": round(float((x.load_tr - x.load_te).abs().mean()), 1),
            "median_abs_rel_err_%": round(float(((x.load_tr - x.load_te).abs() / x.load_te).median() * 100), 1),
            "level_agree_%": round(float((a == b).mean() * 100), 1),
            "level_within1_%": round(float(((a - b).abs() <= 1).mean() * 100), 1),
        }
    return res


def ridership(tk: pd.DataFrame) -> dict:
    daily = tk.groupby("date").pax.sum()
    est = daily.mean() * K.EXPANSION
    return {
        "e_ticket_pax_per_day": int(daily.mean()),
        "expanded_riders_per_day": int(est),
        "official_riders_per_day": OFFICIAL_DAILY_RIDERS,
        "ratio_expanded_to_official": round(float(est / OFFICIAL_DAILY_RIDERS), 2),
        "implied_e_ticket_share_%": round(float(daily.mean() / OFFICIAL_DAILY_RIDERS * 100), 2),
    }


def gps_check(tk: pd.DataFrame, sample: int = 200_000) -> dict:
    """車両番号つきの券で、発券時刻（±2分）のバスの GPS 位置と、対応づけた乗車停留所の距離。"""
    t = tk[(tk.j > tk.i) & tk.vehicle_number.notna()].sample(n=sample, random_state=0)
    pat = C.patterns()[["route_id", "seq", "stop_lat", "stop_lon"]]
    t = t.merge(pat.rename(columns={"seq": "i"}), on=["route_id", "i"])
    t["ts_utc"] = t.created_at.dt.tz_convert("UTC")
    con = C.connect()
    con.register("t", t[["vehicle_number", "ts_utc", "stop_lat", "stop_lon", "match", "date"]])
    days = sorted(t.date.unique())
    r = con.execute(f"""
        SELECT t.match,
               sqrt(pow((g.lat - t.stop_lat) * {C.M_PER_DEG_LAT}, 2) + pow((g.lng - t.stop_lon) * {C.M_PER_DEG_LNG}, 2)) AS d_m,
               epoch(t.ts_utc - g.ts) AS lag_s
        FROM t ASOF JOIN read_parquet({C.gps_glob(days)}) g
          ON t.vehicle_number = g.vehicle_id AND t.ts_utc >= g.ts
    """).df()
    r = r[r.lag_s.abs() <= 120]
    out = {"tickets_checked": int(len(r)), "share_with_gps_within_2min_%": round(len(r) / sample * 100, 1)}
    for mt, g in list(r.groupby("match")) + [("全体", r)]:
        out[mt] = {"n": int(len(g)), "median_m": round(float(g.d_m.median())),
                   "within_300m_%": round(float((g.d_m <= 300).mean() * 100), 1),
                   "within_1km_%": round(float((g.d_m <= 1000).mean() * 100), 1)}
    return out


def top_segments(a: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    x = a[(a.day_type == "weekday") & a.hr.between(8, 10) & (a.confidence == "高")]
    x = x.sort_values("load", ascending=False).drop_duplicates("route_id").head(n)
    r = C.routes()[["route_id", "route_short_name", "route_desc"]]
    return x.merge(r, on="route_id")[["route_short_name", "route_desc", "stop_name", "hr", "load", "n_tickets", "level"]]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    tr = pd.read_parquet(C.PROCESSED / "train" / "crowding.parquet")
    te = pd.read_parquet(C.PROCESSED / "test" / "crowding.parquet")
    tk = K.build_tickets()
    tkv = tk[tk.j > tk.i]

    prof = hourly_profile(tr)
    prof.to_csv(OUT / "p2_hourly_profile.csv")
    stab = stability(tr, te)
    ride = ridership(tk)
    gps = gps_check(tkv)
    top = top_segments(tr)
    top.to_csv(OUT / "p2_top_segments_weekday_am.csv", index=False)
    match = {
        "tickets": int(len(tk)),
        "route_matched_%": round(float(tk.route_id.notna().mean() * 100), 1),
        "stops_matched_%": round(float((tk.j > tk.i).mean() * 100), 1),
        "by_method_%": {k: round(v * 100, 1) for k, v in tkv.match.value_counts(normalize=True).items()},
        "capped_cells_%": round(float(tr.capped.mean() * 100), 2),
        "confidence_cells_%": {k: round(v * 100, 1) for k, v in tr.confidence.value_counts(normalize=True).items()},
        "level_cells_%": {k: round(v * 100, 1) for k, v in tr.level.value_counts(normalize=True).items()},
    }
    peak = {
        "weekday_peak_hour": int(prof["weekday"].idxmax()),
        "weekday_am_peak(8-10)": float(prof.loc[8:10, "weekday"].mean().round(1)),
        "weekday_midday(12-15)": float(prof.loc[12:15, "weekday"].mean().round(1)),
        "weekday_pm_peak(17-20)": float(prof.loc[17:20, "weekday"].mean().round(1)),
        "weekend_am(8-10)": float(prof.loc[8:10, "weekend"].mean().round(1)),
        "weekend_pm(17-20)": float(prof.loc[17:20, "weekend"].mean().round(1)),
    }
    res = {"matching": match, "peaks": peak, "stability_train_vs_test": stab, "ridership": ride, "gps_check": gps}
    (OUT / "p2_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(prof.to_string())
    print(top.to_string())
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 3.5))
        for col, lab in [("weekday", "Weekday"), ("weekend", "Weekend / holiday")]:
            ax.plot(prof.index, prof[col], marker="o", ms=3, label=lab)
        ax.set_xlabel("Hour of day (IST)"); ax.set_ylabel("Avg. estimated passengers on board")
        ax.set_xticks(range(0, 24, 2)); ax.grid(alpha=.3); ax.legend()
        ax.set_title("Estimated bus load by hour (train: Oct 1-24)")
        fig.tight_layout(); fig.savefig(OUT / "p2_hourly_profile.png", dpi=130)
    except Exception as e:  # noqa: BLE001
        print("図は作れませんでした:", e)


if __name__ == "__main__":
    main()
