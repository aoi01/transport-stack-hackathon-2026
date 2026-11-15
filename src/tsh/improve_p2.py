"""問題2の精度改善の実験。

評価: 「ある期間の券から作った推定」で「後の期間の 1便あたりの人数（標本）」をどれだけ当てられるか。
  - 調整用:   10/1〜17 で推定 → 10/18〜24 を当てる（縮小の強さ α を選ぶ）
  - 報告用:   10/1〜24 で推定 → 10/25〜31 を当てる（最初の検証と同じ期間）
  指標: 相関、誤差（拡大後の人数）、混雑レベルの一致率。後の期間で券が 5 枚以上あるマスで比べる（最初の検証と同じ条件）。

試す手法:
  B0  最初の版: 乗客は乗車した時間帯のまま全区間に乗っているとみなす。マスごとに 人数 / 便数。
  B1  時間のずれの補正: 問題1の所要時間モデルで「乗車してから区間 k に着くまでの時間」を足し、
      区間 k を通る時刻の時間帯に数える（長く乗る人ほど後ろの区間は次の時間帯になる）。
  B2  縮小推定（ポアソン・ガンマの経験ベイズ）: マスの率（1便あたり人数）を
        (人数 + α × 事前の率) / (便数 + α)
      で推定する。事前の率は、同じ路線・時間帯の前後 2 区間の平均（車内人数は区間ごとに滑らかに変わるため）。
      α は「事前の値を何便ぶんのデータとして信じるか」。
  B3  B1 + B2
"""
from __future__ import annotations

import json
import sys
from datetime import date

import numpy as np
import pandas as pd

from . import common as C
from . import crowding as K
from .traveltime import passages_glob

OUT = C.PROCESSED / "improve_p2"
DAYS_A = [date(2026, 10, d) for d in range(1, 18)]
DAYS_B = [date(2026, 10, d) for d in range(18, 25)]


def route_cum_time(tag: str = "train") -> pd.DataFrame:
    """路線 × 平日/休日 × 乗車時間帯 × seq の「始点からの典型的な経過秒」（問題1のモデルから）。"""
    out = OUT / f"cumtime_{tag}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    from .traveltime import TravelTimeModel
    m = TravelTimeModel(tag)
    rows = []
    for rid, ids in m.stop_ids.items():
        cum = m.cum[rid]
        for dt in ("weekday", "weekend"):
            for hr in range(24):
                t = 0.0
                rows.append((rid, dt, hr, 0, 0.0))
                for k in range(len(ids) - 1):
                    t += m.link_sec(ids[k], ids[k + 1], cum[k + 1] - cum[k], dt, hr)
                    rows.append((rid, dt, hr, k + 1, t))
    df = pd.DataFrame(rows, columns=["route_id", "day_type", "hr", "seq", "cum_s"])
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return df


def segment_counts(days, shift: bool) -> pd.DataFrame:
    """路線 × 区間 × 平日/休日 × 時間帯 の人数・券数。shift=True なら区間を通る時刻の時間帯で数える。"""
    tk = K.build_tickets()
    tk = tk[(tk.j > tk.i) & tk.date.isin(set(days))].copy()
    tk["sec"] = tk.created_at.dt.hour * 3600 + tk.created_at.dt.minute * 60 + tk.created_at.dt.second
    con = C.connect()
    con.register("tk", tk[["route_id", "date", "day_type", "hr", "sec", "i", "j", "pax"]])
    if shift:
        con.register("ct", route_cum_time())
        q = """
            WITH s AS (SELECT tk.*, k FROM tk, range(0, 400) r(k) WHERE k >= i AND k < j),
            t AS (
                SELECT s.*, a.cum_s AS c_i, b.cum_s AS c_k
                FROM s LEFT JOIN ct a ON a.route_id = s.route_id AND a.day_type = s.day_type AND a.hr = s.hr AND a.seq = s.i
                       LEFT JOIN ct b ON b.route_id = s.route_id AND b.day_type = s.day_type AND b.hr = s.hr AND b.seq = s.k
            )
            SELECT route_id, k AS seq, day_type,
                   CAST(floor((sec + coalesce(c_k - c_i, 0)) / 3600) AS INT) % 24 AS hr,
                   sum(pax) AS pax, count(*) AS n_tickets
            FROM t GROUP BY ALL
        """
    else:
        q = """
            WITH s AS (SELECT * FROM tk, range(0, 400) r(k) WHERE k >= i AND k < j)
            SELECT route_id, k AS seq, day_type, hr, sum(pax) AS pax, count(*) AS n_tickets FROM s GROUP BY ALL
        """
    return con.execute(q).df()


def trips_table(days) -> pd.DataFrame:
    """路線 × 平日/休日 × 時間帯 の便数（期間合計）。GPS の捕捉が半分未満の路線は時刻表 × 日数。"""
    trips, sched = K.trips_per_hour(days)
    trips["date"] = pd.to_datetime(trips.date).dt.date
    di = pd.DataFrame({"date": days, "day_type": [C.day_type(d) for d in days]})
    nd = di.groupby("day_type").size()
    g = trips.merge(di, on="date").groupby(["route_id", "day_type", "hr"]).trips.sum().reset_index()
    cov = (trips.groupby("route_id").trips.sum() / (sched.groupby("route_id").sched_trips.sum() * len(days)))
    low = set(cov[cov < 0.5].index) | (set(sched.route_id) - set(trips.route_id))
    s = sched.merge(pd.DataFrame({"day_type": nd.index, "nd": nd.values}), how="cross")
    s["trips_s"] = s.sched_trips * s.nd
    t = s[["route_id", "day_type", "hr", "trips_s"]].merge(g, on=["route_id", "day_type", "hr"], how="outer")
    t["trips"] = np.where(t.route_id.isin(low) | t.trips.isna(), t.trips_s, t.trips)
    return t[["route_id", "day_type", "hr", "trips"]].dropna()


def estimate(seg: pd.DataFrame, trips: pd.DataFrame, alpha: float | None) -> pd.DataFrame:
    e = seg.merge(trips, on=["route_id", "day_type", "hr"], how="left")
    e["trips"] = e.trips.fillna(0).clip(lower=1)
    e["rate"] = e.pax / e.trips
    if alpha is not None:
        e = e.sort_values(["route_id", "day_type", "hr", "seq"])
        grp = e.groupby(["route_id", "day_type", "hr"])
        # 前後 2 区間（自分を除く）の人数・便数の合計から事前の率を作る
        roll_p = grp.pax.transform(lambda x: x.rolling(5, center=True, min_periods=1).sum()) - e.pax
        roll_t = grp.trips.transform(lambda x: x.rolling(5, center=True, min_periods=1).sum()) - e.trips
        prior = np.where(roll_t > 0, roll_p / roll_t.clip(lower=1e-9), e.rate)
        e["rate"] = (e.pax + alpha * prior) / (e.trips + alpha)
    e["load"] = (e.rate * K.EXPANSION).clip(upper=K.CRUSH)
    return e


def compare(est: pd.DataFrame, later_seg: pd.DataFrame, later_trips: pd.DataFrame) -> dict:
    k = ["route_id", "seq", "day_type", "hr"]
    lat = later_seg.merge(later_trips, on=["route_id", "day_type", "hr"], how="left")
    lat["trips"] = lat.trips.fillna(0).clip(lower=1)
    lat["load"] = (lat.pax / lat.trips * K.EXPANSION).clip(upper=K.CRUSH)
    m = est[k + ["load"]].merge(lat[k + ["load", "n_tickets"]], on=k, suffixes=("_e", "_l"))
    m = m[m.n_tickets >= 5]
    lv = lambda x: np.select([x <= K.SEATS, x <= K.COMFORT], [0, 1], 2)
    a, b = lv(m.load_e), lv(m.load_l)
    return {"cells": int(len(m)),
            "pearson_r": round(float(np.corrcoef(m.load_e, m.load_l)[0, 1]), 3),
            "MAE_people": round(float((m.load_e - m.load_l).abs().mean()), 2),
            "median_abs_rel_err_%": round(float(((m.load_e - m.load_l).abs() / m.load_l).median() * 100), 1),
            "level_agree_%": round(float((a == b).mean() * 100), 1),
            "level_within1_%": round(float((np.abs(a - b) <= 1).mean() * 100), 1)}


def run(early, later, alpha_grid, label) -> dict:
    res = {}
    t_e, t_l = trips_table(early), trips_table(later)
    for shift in (False, True):
        se, sl = segment_counts(early, shift), segment_counts(later, shift)
        for a in alpha_grid:
            name = ("B1" if shift else "B0") if a is None else ("B3" if shift else "B2") + f"_a{a:g}"
            res[name] = compare(estimate(se, t_e, a), sl, t_l)
            print(label, name, res[name], flush=True)
    return res


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    route_cum_time()
    tune = run(DAYS_A, DAYS_B, [None, 2, 5, 10, 20, 50], "[調整 10/1-17→10/18-24]")
    # α は調整用の期間で選ぶ（相関が最も高いもの）
    best_a = {s: max((k for k in tune if k.startswith(s + "_")), key=lambda k: tune[k]["pearson_r"]) for s in ("B2", "B3")}
    alphas = sorted({float(v.split("_a")[1]) for v in best_a.values()})
    print("選んだ α:", best_a)
    final = run(C.TRAIN_DAYS, C.TEST_DAYS, [None] + alphas, "[報告 10/1-24→10/25-31]")
    out = {"tuning": tune, "chosen": best_a, "report": final}
    (C.ROOT / "results" / "p2_improve_metrics.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
