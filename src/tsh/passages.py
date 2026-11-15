"""GPS の点列から「どの便が、どの停留所を、何時に通過したか」を求める（問題1の土台）。

方法:
  1. GPS の各点を、その点の route_id の代表パターンの停留所と突き合わせ、60m 以内にある停留所を候補にする。
  2. 便（日付・車両・trip_id）× 停留所ごとに、停留所に最も近づいた点の時刻を通過時刻とする。
  3. 停留所の順番どおりに時刻が増えていない通過（GPS ノイズ・折り返し・同じ停留所の再通過）を除く。
  4. 通過を検出できた停留所が 5 つ未満の便は捨てる。

出力: data/interim/stop_passages/date=YYYY-MM-DD/part.parquet
列: date, vehicle_id, trip_id, route_id, seq, stop_id, ts（UTC）, dist_m
"""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta

from . import common as C

RADIUS_M = 60.0
OUT = C.INTERIM / "stop_passages"


def run_day(con, d: date) -> int:
    out_dir = OUT / f"date={d:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "part.parquet"
    dlat = RADIUS_M / C.M_PER_DEG_LAT
    dlng = RADIUS_M / C.M_PER_DEG_LNG
    con.execute(f"""
        COPY (
        WITH g AS (
            SELECT vehicle_id, trip_id, route_id, ts, lat, lng
            FROM read_parquet({C.gps_glob([d])})
        ), cand AS (
            SELECT g.vehicle_id, g.trip_id, g.route_id, g.ts, p.seq, p.stop_id,
                   sqrt(pow((g.lat - p.stop_lat) * {C.M_PER_DEG_LAT}, 2)
                      + pow((g.lng - p.stop_lon) * {C.M_PER_DEG_LNG}, 2)) AS dist_m
            FROM g JOIN pat p
              ON g.route_id = p.route_id
             AND g.lat BETWEEN p.stop_lat - {dlat} AND p.stop_lat + {dlat}
             AND g.lng BETWEEN p.stop_lon - {dlng} AND p.stop_lon + {dlng}
        ), best AS (
            SELECT vehicle_id, trip_id, route_id, seq, any_value(stop_id) AS stop_id,
                   arg_min(ts, dist_m) AS ts, min(dist_m) AS dist_m
            FROM cand WHERE dist_m <= {RADIUS_M}
            GROUP BY vehicle_id, trip_id, route_id, seq
        ), mono AS (
            SELECT *, max(ts) OVER (PARTITION BY vehicle_id, trip_id ORDER BY seq
                                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prev_max
            FROM best
        ), ok AS (
            SELECT * EXCLUDE (prev_max) FROM mono WHERE prev_max IS NULL OR ts > prev_max
        )
        SELECT DATE '{d}' AS date, * FROM ok
        WHERE (vehicle_id, trip_id) IN (
            SELECT (vehicle_id, trip_id) FROM ok GROUP BY vehicle_id, trip_id HAVING count(*) >= 5)
        ORDER BY vehicle_id, trip_id, seq
        ) TO '{out.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    return con.execute(f"SELECT count(*) FROM '{out.as_posix()}'").fetchone()[0]


def main(argv=None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    argv = argv or sys.argv[1:]
    start = date.fromisoformat(argv[0]) if argv else date(2026, 10, 1)
    end = date.fromisoformat(argv[1]) if len(argv) > 1 else (start if argv else date(2026, 10, 31))
    con = C.connect()
    pat = C.patterns()[["route_id", "seq", "stop_id", "stop_lat", "stop_lon"]].copy()
    pat["route_id"] = pat["route_id"].astype(int)
    con.register("pat_df", pat)
    con.execute("CREATE TABLE pat AS SELECT * FROM pat_df")
    d = start
    while d <= end:
        t = time.time()
        n = run_day(con, d)
        print(f"{d}: 通過 {n:,} 件（{time.time() - t:.0f}s）", flush=True)
        d += timedelta(days=1)


if __name__ == "__main__":
    main()
