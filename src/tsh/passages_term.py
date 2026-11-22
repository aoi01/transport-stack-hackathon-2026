"""終点の手前で途切れた便に、終点までの残りの停留所の通過を足す（tsh.passages_v2 の後処理）。

passages_v2 は「便の最初と最後の目印（tsh.passages の通過）の間」の停留所しか出さないので、
終点が道から外れた待機場にあって GPS が 60m の円に入らないときや、終点で止まっている間に目印が弾かれたときに、
最後の 1〜2 停留所が抜ける。検証週の 1 日（10/26）で、終点まで行かずに途切れた便のうち
「その後 30 分以内に GPS が終点の 500m 以内に来た」ものを見ると、終点近くの最初の点の 94% は同じ路線のラベルで、
途切れてから中央値 0.9 分で着いており、抜けた停留所は中央値 1 つだった（experiments/p1_passages/reach_why.py）。

足し方: 便ごとに最後の通過（停留所 s、時刻 t_s）のあと、
  - 同じ車両・同じ路線のラベルの GPS が
  - t_s から 30 分以内、かつその車両の次の便の最初の通過より前に
  - 終点の停留所の 200m 以内に来た
なら、その最初の点の時刻を終点の通過 t_L とし、s+1〜終点の通過を路線の距離で t_s〜t_L の間に線形に割り振る。
終点までの残りが 5km を超える便は足さない。
足した行は filled = true（detected = false、ts_arr・ts_dep・gap_s・ts_near・dist_m は空）。元の行は filled = false。

出力: data/interim/stop_passages_v3/date=YYYY-MM-DD/part.parquet（列は v2 と同じ + filled）
使うとき: TSH_PASSAGES / TSH_TRUTH_PASSAGES に stop_passages_v3 を入れる
python -m tsh.passages_term [開始日 [終了日]]
"""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta

from . import common as C
from .passages_v2 import OUT as V2

OUT = C.INTERIM / "stop_passages_v3"
WIN_S = 1800        # 最後の通過からこの秒数以内に終点に来たものだけ
NEAR_M = 200.0      # 終点の停留所からこの距離以内に来たら着いたとみなす
MAX_LEFT_M = 5000.0  # 終点までの残りがこれより長い便には足さない


def setup(con) -> None:
    p = C.patterns()[["route_id", "seq", "stop_id", "stop_lat", "stop_lon", "cum_m"]].copy()
    p["route_id"] = p["route_id"].astype(int)
    con.register("pat_df", p)
    con.execute("CREATE OR REPLACE TABLE pat AS SELECT * FROM pat_df")
    con.execute("""
        CREATE OR REPLACE TABLE term AS
        SELECT route_id, arg_max(seq, seq) AS L, arg_max(stop_lat, seq) AS tlat, arg_max(stop_lon, seq) AS tlng,
               max(cum_m) AS cum_L
        FROM pat GROUP BY route_id""")


def run_day(con, d: date) -> tuple[int, int]:
    out_dir = OUT / f"date={d:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "part.parquet"
    v2 = (V2 / f"date={d:%Y-%m-%d}" / "part.parquet").as_posix()
    LAT, LNG = C.M_PER_DEG_LAT, C.M_PER_DEG_LNG
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE fill AS
        WITH ps AS (
            SELECT vehicle_id, trip_id, route_id, seq, epoch(ts) AS t FROM read_parquet('{v2}')
        ), tr AS (
            SELECT vehicle_id, trip_id, any_value(route_id) AS route_id, max(seq) AS s, arg_max(t, seq) AS ts_,
                   min(t) AS t_first
            FROM ps GROUP BY vehicle_id, trip_id
        ), tr2 AS (
            SELECT *, lead(t_first) OVER (PARTITION BY vehicle_id ORDER BY t_first) AS t_next FROM tr
        ), cand AS (
            SELECT tr2.*, term.L, term.tlat, term.tlng, term.cum_L, pa.cum_m AS cum_s,
                   least(tr2.ts_ + {WIN_S}, coalesce(tr2.t_next, 1e12)) AS w1
            FROM tr2 JOIN term ON term.route_id = tr2.route_id
            JOIN pat pa ON pa.route_id = tr2.route_id AND pa.seq = tr2.s
            WHERE tr2.s < term.L AND term.cum_L - pa.cum_m <= {MAX_LEFT_M}
        ), hit AS (
            SELECT c.vehicle_id, c.trip_id, min(epoch(g.ts)) AS tL
            FROM cand c JOIN read_parquet({C.gps_glob([d])}) g
              ON g.vehicle_id = c.vehicle_id AND g.route_id = c.route_id
             AND epoch(g.ts) > c.ts_ AND epoch(g.ts) < c.w1
            WHERE sqrt(pow((g.lat - c.tlat) * {LAT}, 2) + pow((g.lng - c.tlng) * {LNG}, 2)) <= {NEAR_M}
            GROUP BY c.vehicle_id, c.trip_id
        )
        SELECT c.vehicle_id, c.trip_id, c.route_id, p.seq, p.stop_id,
               c.ts_ + CASE WHEN c.cum_L > c.cum_s THEN (p.cum_m - c.cum_s) / (c.cum_L - c.cum_s) ELSE 1 END
                       * (h.tL - c.ts_) AS t
        FROM cand c JOIN hit h USING (vehicle_id, trip_id)
        JOIN pat p ON p.route_id = c.route_id AND p.seq > c.s AND p.seq <= c.L""")
    con.execute(f"""
        COPY (
            SELECT *, false AS filled FROM read_parquet('{v2}')
            UNION ALL
            SELECT DATE '{d}' AS date, vehicle_id, trip_id, route_id, seq, stop_id, to_timestamp(t) AS ts,
                   CAST(NULL AS TIMESTAMPTZ) AS ts_arr, CAST(NULL AS TIMESTAMPTZ) AS ts_dep, CAST(NULL AS FLOAT) AS gap_s,
                   false AS detected, CAST(NULL AS TIMESTAMPTZ) AS ts_near, CAST(NULL AS FLOAT) AS dist_m, true AS filled
            FROM fill
            ORDER BY vehicle_id, trip_id, seq
        ) TO '{out.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    n_fill = con.execute("SELECT count(*) FROM fill").fetchone()[0]
    n_trip = con.execute("SELECT count(DISTINCT (vehicle_id, trip_id)) FROM fill").fetchone()[0]
    return n_fill, n_trip


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
        n, k = run_day(con, d)
        print(f"{d}: 足した通過 {n:,} 件・{k:,} 便（{time.time() - t:.0f}s）", flush=True)
        d += timedelta(days=1)


if __name__ == "__main__":
    main()
