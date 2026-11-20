"""停留所の通過時刻を、路線の上の位置に投影した GPS から補間で求める（docs 17章、tsh.passages の改良版）。

tsh.passages は「停留所から 60m 以内で最も近づいた点の時刻」を通過とするので、
  - 点が 60m の円に入らなかった停留所（約 4 分の 1）は通過が抜ける
  - 時刻は「最も近い点」の時刻なので、点の間隔（中央値 11 秒）の分だけずれる
  - 停留所に止まっていた時間（停車時間）と走っていた時間を分けられない
という弱点がある。ここでは tsh.passages の通過（順番の確認を通ったもの）を「確かにそこを通った」目印にして、
  1. 便の GPS の各点を、前後の目印の停留所の間（と 1 つ外側）の、停留所どうしを結んだ線に投影し、
     路線の始点からの位置（m）にする（線から 150m 以上離れた点は捨てる）
  2. 位置を時刻順に累積最大にして、後戻りしないようにする（GPS のぶれ）
  3. 続く 2 点の間で位置が停留所 s の位置 c_s をまたいだら、時刻を線形補間して通過時刻にする。
     同じく c_s − 30m（着いた時刻）と c_s + 30m（出た時刻）をまたいだ時刻も出す。その差が停留所のまわりの停車時間
  4. 便の最初と最後の目印の間の停留所だけを出す（その外は本当に走ったか分からない）
出力: data/interim/stop_passages_v2/date=YYYY-MM-DD/part.parquet
列: date, vehicle_id, trip_id, route_id, seq, stop_id, ts（補間した通過時刻）, ts_arr, ts_dep（±30m をまたいだ時刻）,
    gap_s（通過をはさむ 2 点の間隔、秒）, detected（tsh.passages でも検出していたか）, ts_near（その時刻）, dist_m

python -m tsh.passages_v2 [開始日 [終了日]]
"""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta

from . import common as C
from .passages import OUT as V1

OUT = C.INTERIM / "stop_passages_v2"
DWELL_R = 30.0      # 停留所の前後これだけの範囲にいた時間を停車時間とみなす（m）
OFF_ROUTE_M = 150.0  # 路線の線からこれ以上離れた点は使わない


def run_day(con, d: date) -> int:
    out_dir = OUT / f"date={d:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "part.parquet"
    v1 = (V1 / f"date={d:%Y-%m-%d}" / "part.parquet").as_posix()
    LAT, LNG = C.M_PER_DEG_LAT, C.M_PER_DEG_LNG
    con.execute(f"""
        COPY (
        WITH anc AS (
            SELECT vehicle_id, trip_id, route_id, seq, epoch(ts) AS t FROM read_parquet('{v1}')
        ), rng AS (
            SELECT vehicle_id, trip_id, any_value(route_id) AS route_id, min(seq) AS s_min, max(seq) AS s_max,
                   min(t) AS t_min, max(t) AS t_max
            FROM anc GROUP BY vehicle_id, trip_id
        ), g AS (
            SELECT g.vehicle_id, g.trip_id, g.route_id, epoch(g.ts) AS t, g.lng * {LNG} AS px, g.lat * {LAT} AS py
            FROM read_parquet({C.gps_glob([d])}) g
            JOIN rng ON rng.vehicle_id = g.vehicle_id AND rng.trip_id = g.trip_id AND rng.route_id = g.route_id
            WHERE epoch(g.ts) BETWEEN rng.t_min AND rng.t_max
        ), ga AS (   -- 前の目印
            SELECT g.*, a.seq AS sa FROM g ASOF JOIN anc a
              ON a.vehicle_id = g.vehicle_id AND a.trip_id = g.trip_id AND g.t >= a.t
        ), gb AS (   -- 後ろの目印
            SELECT ga.*, b.seq AS sb FROM ga ASOF JOIN (SELECT vehicle_id, trip_id, seq, -t AS nt FROM anc) b
              ON b.vehicle_id = ga.vehicle_id AND b.trip_id = ga.trip_id AND -ga.t >= b.nt
        ), proj AS (
            SELECT gb.vehicle_id, gb.trip_id, gb.route_id, gb.t, s.cum0, s.len,
                   greatest(0.0, least(1.0, CASE WHEN s.len > 0 THEN
                        ((gb.px - s.x0) * (s.x1 - s.x0) + (gb.py - s.y0) * (s.y1 - s.y0)) / (s.len * s.len) ELSE 0 END)) AS u,
                   s.x0, s.y0, s.x1, s.y1, gb.px, gb.py
            FROM gb JOIN seg s ON s.route_id = gb.route_id AND s.seq BETWEEN gb.sa - 1 AND greatest(gb.sb, gb.sa)
        ), pd AS (
            SELECT vehicle_id, trip_id, route_id, t, cum0 + u * len AS pos,
                   sqrt(pow(px - (x0 + u * (x1 - x0)), 2) + pow(py - (y0 + u * (y1 - y0)), 2)) AS d
            FROM proj
        ), pt AS (
            SELECT vehicle_id, trip_id, any_value(route_id) AS route_id, t, arg_min(pos, d) AS pos, min(d) AS d
            FROM pd GROUP BY vehicle_id, trip_id, t
        ), mono AS (
            SELECT vehicle_id, trip_id, route_id, t,
                   max(pos) OVER (PARTITION BY vehicle_id, trip_id ORDER BY t ROWS UNBOUNDED PRECEDING) AS pos
            FROM pt WHERE d <= {OFF_ROUTE_M}
        ), pairs AS (
            SELECT vehicle_id, trip_id, route_id, t AS t0, pos AS p0,
                   lead(t) OVER w AS t1, lead(pos) OVER w AS p1
            FROM mono WINDOW w AS (PARTITION BY vehicle_id, trip_id ORDER BY t)
        ), tg AS (   -- 便ごとの対象（停留所 × 3 つの位置）
            SELECT r.vehicle_id, r.trip_id, r.route_id, k.seq, k.stop_id, k.kind, k.c
            FROM rng r JOIN tgt k ON k.route_id = r.route_id AND k.seq BETWEEN r.s_min AND r.s_max
        ), cross_ AS (
            SELECT tg.vehicle_id, tg.trip_id, tg.route_id, tg.seq, tg.stop_id, tg.kind,
                   p.t0 + (tg.c - p.p0) / (p.p1 - p.p0) * (p.t1 - p.t0) AS t, p.t1 - p.t0 AS gap
            FROM tg JOIN pairs p
              ON p.vehicle_id = tg.vehicle_id AND p.trip_id = tg.trip_id
             AND p.p1 > p.p0 AND tg.c > p.p0 AND tg.c <= p.p1
        ), piv AS (
            SELECT vehicle_id, trip_id, any_value(route_id) AS route_id, seq, any_value(stop_id) AS stop_id,
                   max(t) FILTER (WHERE kind = 0) AS t, max(gap) FILTER (WHERE kind = 0) AS gap_s,
                   max(t) FILTER (WHERE kind = -1) AS t_arr, max(t) FILTER (WHERE kind = 1) AS t_dep
            FROM cross_ GROUP BY vehicle_id, trip_id, seq
        )
        SELECT DATE '{d}' AS date, p.vehicle_id, p.trip_id, p.route_id, p.seq, p.stop_id,
               to_timestamp(p.t) AS ts, to_timestamp(p.t_arr) AS ts_arr, to_timestamp(p.t_dep) AS ts_dep,
               CAST(p.gap_s AS FLOAT) AS gap_s, a.t IS NOT NULL AS detected,
               to_timestamp(a.t) AS ts_near, CAST(v.dist_m AS FLOAT) AS dist_m
        FROM piv p
        LEFT JOIN anc a ON a.vehicle_id = p.vehicle_id AND a.trip_id = p.trip_id AND a.seq = p.seq
        LEFT JOIN read_parquet('{v1}') v ON v.vehicle_id = p.vehicle_id AND v.trip_id = p.trip_id AND v.seq = p.seq
        WHERE p.t IS NOT NULL
        ORDER BY p.vehicle_id, p.trip_id, p.seq
        ) TO '{out.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    return con.execute(f"SELECT count(*) FROM '{out.as_posix()}'").fetchone()[0]


def setup(con) -> None:
    p = C.patterns()[["route_id", "seq", "stop_id", "stop_lat", "stop_lon", "cum_m"]].copy()
    p["route_id"] = p["route_id"].astype(int)
    p["x"] = p.stop_lon * C.M_PER_DEG_LNG
    p["y"] = p.stop_lat * C.M_PER_DEG_LAT
    con.register("p_df", p)
    # 停留所 seq → seq+1 の線分
    con.execute("""
        CREATE OR REPLACE TABLE seg AS
        SELECT a.route_id, a.seq, a.x AS x0, a.y AS y0, b.x AS x1, b.y AS y1, a.cum_m AS cum0, b.cum_m - a.cum_m AS len
        FROM p_df a JOIN p_df b ON b.route_id = a.route_id AND b.seq = a.seq + 1""")
    con.execute(f"""
        CREATE OR REPLACE TABLE tgt AS
        SELECT route_id, seq, stop_id, k AS kind, cum_m + k * {DWELL_R} AS c
        FROM p_df, (SELECT unnest([-1, 0, 1]) AS k)""")


def main(argv=None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    argv = argv or sys.argv[1:]
    start = date.fromisoformat(argv[0]) if argv else date(2026, 10, 1)
    end = date.fromisoformat(argv[1]) if len(argv) > 1 else (start if argv else date(2026, 10, 31))
    con = C.connect()
    setup(con)
    d = start
    while d <= end:
        t = time.time()
        n = run_day(con, d)
        print(f"{d}: 通過 {n:,} 件（{time.time() - t:.0f}s）", flush=True)
        d += timedelta(days=1)


if __name__ == "__main__":
    main()
