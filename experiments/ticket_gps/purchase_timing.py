"""車両番号つきの乗車券は、乗車停留所をバスが通る前に買われたか、後に買われたか。

同じ車両（券の vehicle_number = GPS の vehicle_id）について、2つの見方で確かめる。
  A. 通過時刻との差: 購入時刻 − その車両が乗車停留所（券の路線の seq=i）を通った時刻
  B. 購入時刻のバスの位置: 購入の直前の GPS の点を、券の路線の停留所の並びの最寄りに当て、
     乗車停留所から路線に沿って何 m 先（負なら手前）にいたか

対象: 両端が名前の完全一致で対応した券（照合の誤りを避けるため）。
使い方: python -X utf8 experiments/ticket_gps/purchase_timing.py 2026-10-13 2026-10-16
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
TK = (ROOT / "data/processed/tickets_matched.parquet").as_posix()
PAT = (ROOT / "data/processed/patterns.parquet").as_posix()


def days_between(a: str, b: str):
    d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
    return [d0 + timedelta(n) for n in range((d1 - d0).days + 1)]


def main(a="2026-10-13", b="2026-10-16"):
    days = days_between(a, b)
    con = duckdb.connect()
    con.execute("SET timezone='Asia/Kolkata'; SET threads TO 16; SET memory_limit='20GB';")
    ps = [(ROOT / f"data/interim/stop_passages/date={d}/part.parquet").as_posix() for d in days]
    gp = [(ROOT / f"data/interim/bus_gps/date={d}/part.parquet").as_posix() for d in days]
    dl = ", ".join(f"DATE '{d}'" for d in days)
    con.execute(f"""
        CREATE TABLE tk AS
        SELECT row_number() OVER () AS tid, vehicle_number AS vid, CAST(route_id AS INT) AS rid,
               i, j, created_at, date, match, pax
        FROM read_parquet('{TK}')
        WHERE vehicle_number IS NOT NULL AND route_id IS NOT NULL AND i >= 0 AND j > i
          AND date IN ({dl})
    """)
    con.execute(f"CREATE TABLE ps AS SELECT vehicle_id AS vid, route_id AS rid, seq, ts, trip_id, date FROM read_parquet({ps})")
    con.execute(f"CREATE TABLE pat AS SELECT CAST(route_id AS INT) AS rid, seq, stop_lat, stop_lon, cum_m FROM read_parquet('{PAT}')")
    n_all = con.execute("SELECT count(*), count(*) FILTER (WHERE match='exact') FROM tk").fetchone()
    print(f"対象期間 {a}〜{b}: 車両番号つきで両端が対応した券 {n_all[0]:,} 枚（うち両端が完全一致 {n_all[1]:,} 枚）")

    # 車両が GPS に現れるか
    cov = con.execute(f"""
        WITH v AS (SELECT DISTINCT vehicle_id AS vid, date, route_id AS rid FROM read_parquet({gp}))
        SELECT count(*) AS n,
               count(*) FILTER (WHERE EXISTS (SELECT 1 FROM v WHERE v.vid = tk.vid AND v.date = tk.date)) AS same_day,
               count(*) FILTER (WHERE EXISTS (SELECT 1 FROM v WHERE v.vid = tk.vid AND v.date = tk.date AND v.rid = tk.rid)) AS same_route
        FROM tk WHERE match = 'exact'
    """).fetchone()
    print(f"  その車両が同じ日の GPS にいる {cov[1]/cov[0]:.1%}、同じ日に券と同じ路線を走っている {cov[2]/cov[0]:.1%}")

    # A. 通過時刻との差（同じ車両・同じ路線・乗車停留所、±90分で最も近い通過）
    con.execute("""
        CREATE TABLE a AS
        WITH j AS (
            SELECT tk.tid, tk.i, tk.match, epoch(tk.created_at) - epoch(ps.ts) AS dt
            FROM tk JOIN ps ON ps.vid = tk.vid AND ps.rid = tk.rid AND ps.seq = tk.i AND ps.date = tk.date
            WHERE abs(epoch(tk.created_at) - epoch(ps.ts)) <= 5400
        )
        SELECT tid, any_value(i) AS i, any_value(match) AS match, arg_min(dt, abs(dt)) AS dt FROM j GROUP BY tid
    """)
    print("\nA. 購入時刻 − その車両が乗車停留所を通った時刻（両端が完全一致の券）")
    for label, cond in [("全体", "TRUE"), ("起点（seq=0）で乗った券", "i = 0"), ("途中の停留所で乗った券", "i > 0")]:
        r = con.execute(f"""
            SELECT count(*), median(dt)/60, quantile_cont(dt, 0.25)/60, quantile_cont(dt, 0.75)/60,
                   avg((dt < -120)::INT), avg((dt >= -120 AND dt < 0)::INT), avg((dt >= 0 AND dt < 120)::INT),
                   avg((dt >= 120 AND dt < 300)::INT), avg((dt >= 300 AND dt < 900)::INT), avg((dt >= 900)::INT)
            FROM a WHERE match = 'exact' AND {cond}
        """).fetchone()
        base = con.execute(f"SELECT count(*) FROM tk WHERE match='exact' AND {cond}").fetchone()[0]
        print(f"  {label}: 通過が見つかった {r[0]:,} / {base:,} 枚（{r[0]/max(base,1):.1%}）")
        print(f"    中央値 {r[1]:+.1f} 分（四分位 {r[2]:+.1f}〜{r[3]:+.1f}）")
        print(f"    通過の2分超前 {r[4]:.1%} / 0〜2分前 {r[5]:.1%} / 0〜2分後 {r[6]:.1%} / 2〜5分後 {r[7]:.1%} / 5〜15分後 {r[8]:.1%} / 15分超後 {r[9]:.1%}")

    # B. 購入時刻のバスの位置（直前の GPS の点、60 秒以内）
    con.execute(f"""
        CREATE TABLE g AS
        SELECT vehicle_id AS vid, ts, lat, lng, route_id AS grid
        FROM read_parquet({gp}) WHERE vehicle_id IN (SELECT DISTINCT vid FROM tk)
    """)
    con.execute("""
        CREATE TABLE pos AS
        SELECT tk.tid, tk.rid, tk.i, tk.match, g.lat, g.lng, g.grid, epoch(tk.created_at) - epoch(g.ts) AS lag
        FROM tk ASOF JOIN g ON g.vid = tk.vid AND g.ts <= tk.created_at
        WHERE tk.match = 'exact'
    """)
    con.execute("""
        CREATE TABLE b AS
        WITH c AS (
            SELECT pos.tid, pos.rid, pos.i, pos.grid = pos.rid AS same_route, pat.seq, pat.cum_m,
                   sqrt(pow((pos.lat - pat.stop_lat) * 110540, 2) + pow((pos.lng - pat.stop_lon) * 97700, 2)) AS d
            FROM pos JOIN pat ON pat.rid = pos.rid
            WHERE pos.lag <= 60
        ), best AS (
            SELECT tid, any_value(rid) AS rid, any_value(i) AS i, any_value(same_route) AS same_route,
                   arg_min(seq, d) AS seq_near, arg_min(cum_m, d) AS m_near, min(d) AS d_near
            FROM c GROUP BY tid
        )
        SELECT best.*, best.m_near - p.cum_m AS along_m
        FROM best JOIN pat p ON p.rid = best.rid AND p.seq = best.i
    """)
    r = con.execute("""
        SELECT count(*), avg(same_route::INT), avg((d_near <= 300)::INT),
               median(along_m) FILTER (WHERE d_near <= 300),
               avg((seq_near < i)::INT) FILTER (WHERE d_near <= 300),
               avg((seq_near = i)::INT) FILTER (WHERE d_near <= 300),
               avg((seq_near = i + 1)::INT) FILTER (WHERE d_near <= 300),
               avg((seq_near = i + 2)::INT) FILTER (WHERE d_near <= 300),
               avg((seq_near > i + 2)::INT) FILTER (WHERE d_near <= 300)
        FROM b
    """).fetchone()
    print("\nB. 購入時刻のバスの位置（直前60秒以内の GPS の点を、券の路線の最寄りの停留所に当てる）")
    print(f"  位置が取れた券 {r[0]:,} 枚。そのとき GPS 上も券と同じ路線を走っていた {r[1]:.1%}、路線の停留所から300m以内 {r[2]:.1%}")
    print(f"  （300m以内の券で）乗車停留所からの路線に沿った距離の中央値 {r[3]:+.0f} m")
    print(f"  最寄りの停留所が 乗車より手前 {r[4]:.1%} / 乗車停留所 {r[5]:.1%} / 1つ先 {r[6]:.1%} / 2つ先 {r[7]:.1%} / 3つ以上先 {r[8]:.1%}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
