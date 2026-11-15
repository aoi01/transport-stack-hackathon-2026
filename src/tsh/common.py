"""共通部品: パス、GTFS の路線パターン（停留所の並び）、距離計算、日付の区分。"""
from __future__ import annotations

import math
from datetime import date
from functools import lru_cache
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GTFS = ROOT / "data/raw/gtfs_static"
GPS = ROOT / "data/interim/bus_gps"
TICKETS = ROOT / "data/raw/ticketing/October-Delhi.csv"
INTERIM = ROOT / "data/interim"
PROCESSED = ROOT / "data/processed"
TZ = "Asia/Kolkata"

# 学習期間と検証期間（時系列で分ける：最後の1週間を検証に使う）
TRAIN_DAYS = [date(2026, 10, d) for d in range(1, 25)]   # 10/1〜10/24
TEST_DAYS = [date(2026, 10, d) for d in range(25, 32)]   # 10/25〜10/31
# 祝日（平日扱いにしない）。10/2 はガンディー生誕記念日（全国の祝日）
HOLIDAYS = {date(2026, 10, 2)}

M_PER_DEG_LAT = 110_540.0
M_PER_DEG_LNG = 111_320.0 * math.cos(math.radians(28.6))  # デリー付近


def day_type(d: date) -> str:
    """weekday / weekend（祝日は weekend 扱い）"""
    return "weekend" if d.weekday() >= 5 or d in HOLIDAYS else "weekday"


def dist_m(lat1, lng1, lat2, lng2):
    """近距離用の平面近似（デリー周辺では誤差 1% 未満）"""
    dy = (np.asarray(lat2) - np.asarray(lat1)) * M_PER_DEG_LAT
    dx = (np.asarray(lng2) - np.asarray(lng1)) * M_PER_DEG_LNG
    return np.sqrt(dx * dx + dy * dy)


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false; SET threads TO 16; SET memory_limit = '20GB';")
    return con


@lru_cache(maxsize=1)
def stops() -> pd.DataFrame:
    s = pd.read_csv(GTFS / "stops.txt", dtype={"stop_id": str})
    return s[["stop_id", "stop_name", "stop_lat", "stop_lon"]]


@lru_cache(maxsize=1)
def routes() -> pd.DataFrame:
    return pd.read_csv(GTFS / "routes.txt", dtype={"route_id": str})


@lru_cache(maxsize=1)
def patterns() -> pd.DataFrame:
    """路線ごとの代表パターン（停留所の並び）。

    GTFS では上り・下りが別の route_id。1つの route_id に FULL/SHORT など複数の停留所列が
    あるので、FULL の便の中で最も多い停留所列を代表とする（FULL が無ければ全便から）。
    返り値: route_id, seq（0始まり）, stop_id, stop_lat, stop_lon, cum_m（始点からの累積距離）
    """
    out = PROCESSED / "patterns.parquet"
    if out.exists():
        return pd.read_parquet(out)
    con = connect()
    df = con.execute(f"""
        WITH st AS (
            SELECT trip_id, stop_id, CAST(stop_sequence AS INTEGER) AS seq
            FROM read_csv('{(GTFS / 'stop_times.txt').as_posix()}', all_varchar=true)
        ), tr AS (
            SELECT trip_id, route_id, trip_id LIKE '%\\_FULL\\_%' ESCAPE '\\' AS is_full
            FROM read_csv('{(GTFS / 'trips.txt').as_posix()}', all_varchar=true)
        ), seqs AS (
            SELECT st.trip_id, any_value(tr.route_id) AS route_id, any_value(tr.is_full) AS is_full,
                   string_agg(st.stop_id, ',' ORDER BY st.seq) AS sig
            FROM st JOIN tr USING (trip_id) GROUP BY st.trip_id
        ), ranked AS (
            SELECT route_id, sig, count(*) AS n, max(is_full::INT) AS full,
                   row_number() OVER (PARTITION BY route_id ORDER BY max(is_full::INT) DESC, count(*) DESC, sig) AS rk
            FROM seqs GROUP BY route_id, sig
        )
        SELECT route_id, sig FROM ranked WHERE rk = 1
    """).df()
    rows = []
    for r in df.itertuples():
        for i, sid in enumerate(r.sig.split(",")):
            rows.append((r.route_id, i, sid))
    p = pd.DataFrame(rows, columns=["route_id", "seq", "stop_id"]).merge(stops(), on="stop_id", how="left")
    p = p.dropna(subset=["stop_lat"]).sort_values(["route_id", "seq"]).reset_index(drop=True)
    p["seq"] = p.groupby("route_id").cumcount()
    d = dist_m(p["stop_lat"].shift(), p["stop_lon"].shift(), p["stop_lat"], p["stop_lon"])
    d = np.where(p["route_id"].eq(p["route_id"].shift()), d, 0.0)
    p["cum_m"] = pd.Series(d).groupby(p["route_id"]).cumsum().values
    p = p.merge(routes()[["route_id", "route_short_name", "route_desc", "agency_id"]], on="route_id", how="left")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    p.to_parquet(out, index=False)
    return p


def gps_glob(days) -> str:
    files = [(GPS / f"date={d:%Y-%m-%d}" / "part.parquet").as_posix() for d in days]
    return "[" + ",".join(f"'{f}'" for f in files) + "]"
