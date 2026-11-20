"""問2の誤差実験の共通部品。

正解（検証週 10/25〜31）は今の検証（tsh.validate_p2）と同じ test/crowding.parquet のマス。
ただし 1 便 100 人の頭打ち（CRUSH）は、券の多いマスの誤差を機械的に 0 にしてしまうので、
比べるのは頭打ちの前の「1 便あたりの標本人数」（sample_per_trip = 人数 / 便数）。拡大係数は両側で同じなので、相対誤差には効かない。
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402

K = ["route_id", "seq", "day_type", "hr"]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)


def test_truth() -> pd.DataFrame:
    te = pd.read_parquet(C.PROCESSED / "test" / "crowding.parquet",
                         columns=K + ["pax", "n_tickets", "trips_total", "sample_per_trip"])
    return te.rename(columns={"pax": "pax_te", "n_tickets": "n_te", "trips_total": "T_te", "sample_per_trip": "y_te"})


def daily(tag: str = "train") -> tuple[pd.DataFrame, pd.DataFrame]:
    """期間（train / test）の (路線, 区間, 日, 時間帯) の人数・枚数と、(路線, 日, 時間帯) の便数（GPS と時刻表）。"""
    d = pd.read_parquet(C.PROCESSED / tag / "crowding_daily.parquet")
    tr = pd.read_parquet(C.PROCESSED / tag / "crowding.parquet", columns=["route_id", "trips_src"]).drop_duplicates()
    g = pd.read_parquet(C.PROCESSED / tag / "trips_per_day_hour.parquet")
    g["date"] = pd.to_datetime(g.date).dt.date
    sched = pd.read_parquet(C.PROCESSED / "schedule.parquet")
    first = sched.groupby(["route_id", "trip_id"]).t_s.min().reset_index()
    first["hr"] = (first.t_s // 3600) % 24
    sh = first.groupby(["route_id", "hr"]).size().rename("sched_trips").reset_index()
    # 便数の出どころは今の推定（<tag>/crowding.parquet）と同じにする
    src = tr.set_index("route_id").trips_src
    gps_routes = set(src[src == "GPS"].index)
    days = C.TRAIN_DAYS if tag == "train" else C.TEST_DAYS
    grid = pd.MultiIndex.from_product([sorted(set(d.route_id) | set(g.route_id)), days, range(24)],
                                      names=["route_id", "date", "hr"]).to_frame(index=False)
    grid = grid.merge(g, on=["route_id", "date", "hr"], how="left").merge(sh, on=["route_id", "hr"], how="left")
    grid["trips"] = grid.trips.fillna(0)
    grid["sched_trips"] = grid.sched_trips.fillna(0)
    grid["gps"] = grid.route_id.isin(gps_routes)
    grid["day_type"] = grid.date.map(C.day_type)
    return d, grid[["route_id", "date", "hr", "day_type", "trips", "sched_trips", "gps"]]


def train_daily():
    return daily("train")


def cells_from_daily(d: pd.DataFrame, grid: pd.DataFrame, w: dict | None = None, dt_of=None) -> pd.DataFrame:
    """日の重み w（date → 重み、無ければ 1）で、マスごとの 人数・枚数・便数 を足す。dt_of は日 → 区分（既定は平日/休日）。"""
    d = d.copy(); grid = grid.copy()
    if dt_of is not None:
        d["day_type"] = d.date.map(dt_of); grid["day_type"] = grid.date.map(dt_of)
    if w is not None:
        d["w"] = d.date.map(w).fillna(0.0); grid["w"] = grid.date.map(w).fillna(0.0)
    else:
        d["w"] = 1.0; grid["w"] = 1.0
    d = d[d.w > 0]; grid = grid[grid.w > 0]
    d["wp"] = d.pax * d.w; d["wn"] = d.n_tickets * d.w
    a = d.groupby(K).agg(pax=("wp", "sum"), n=("wn", "sum"), days=("date", "nunique")).reset_index()
    grid["wg"] = grid.trips * grid.w; grid["ws"] = grid.sched_trips * grid.w
    t = grid.groupby(["route_id", "day_type", "hr"]).agg(Tg=("wg", "sum"), Ts=("ws", "sum"), gps=("gps", "first")).reset_index()
    # 今の推定と同じ: GPS の路線でも、その区分・時間帯に GPS の便が 1 つも無ければ時刻表の便数
    t["T"] = np.where(t.gps & (t.Tg > 0), t.Tg, t.Ts)
    a = a.merge(t[["route_id", "day_type", "hr", "T"]], on=["route_id", "day_type", "hr"], how="left")
    d["wd"] = d.w
    wd = d.drop_duplicates(K + ["date"]).groupby(K).wd.sum().rename("wdays").reset_index()
    a = a.merge(wd, on=K, how="left")
    a["T"] = np.fmax(a["T"].fillna(0), a.wdays)   # 券が出た日には少なくとも 1 便は走っている
    return a


def evaluate(pred: pd.DataFrame, truth: pd.DataFrame, col: str = "pred", min_n: int = 5, label: str = "") -> dict:
    m = truth[truth.n_te >= min_n].merge(pred[K + [col]], on=K, how="inner")
    m = m[np.isfinite(m[col]) & (m[col] > 0)]
    rel = (m[col] - m.y_te).abs() / m.y_te
    return {"label": label, "cells": int(len(m)), "median_rel_%": round(float(rel.median() * 100), 2),
            "WAPE_%": round(float((m[col] - m.y_te).abs().sum() / m.y_te.sum() * 100), 2),
            "bias_med_log": round(float(np.median(np.log(m[col] / m.y_te))), 3),
            "corr": round(float(np.corrcoef(m[col], m.y_te)[0, 1]), 3)}
