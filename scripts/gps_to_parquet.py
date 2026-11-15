"""バス GPS（1日1つの SQLite）を Parquet に変換する。

7z から1日分ずつ取り出し → 型を直して重複を落とし Parquet に保存 → 取り出した .db を消す。
全展開（124 GB）をせずに31日分を処理できる。

使い方:
  python scripts/gps_to_parquet.py 2026-10-01             # 1日分
  python scripts/gps_to_parquet.py 2026-10-01 2026-10-07  # 期間
  python scripts/gps_to_parquet.py all                    # 31日分
  --keep-db を付けると取り出した .db を消さない

出力: data/interim/bus_gps/date=YYYY-MM-DD/part.parquet
列: vehicle_id, ts (UTC, TIMESTAMPTZ), lat, lng, speed, route_id, trip_id
"""
import argparse
import shutil
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data/raw/bus_gps/delhi-dtc-bus-gtfs-rt-2026-10.7z"
TMP = ROOT / "data/raw/bus_gps/tmp"
OUT = ROOT / "data/interim/bus_gps"
SEVEN_ZIP = Path(r"C:\Program Files\7-Zip\7z.exe")


def extract(day: date) -> Path:
    name = f"bus_movements_{day:%Y_%m_%d}.db"
    db = TMP / name
    if db.exists():
        return db
    TMP.mkdir(parents=True, exist_ok=True)
    if SEVEN_ZIP.exists() or shutil.which("7z"):
        exe = str(SEVEN_ZIP) if SEVEN_ZIP.exists() else "7z"
        subprocess.run([exe, "x", str(ARCHIVE), name, f"-o{TMP}", "-y", "-bso0", "-bsp0"], check=True)
    else:
        import py7zr
        with py7zr.SevenZipFile(ARCHIVE) as z:
            z.extract(path=TMP, targets=[name])
    return db


def convert(day: date, keep_db: bool) -> dict:
    t0 = time.time()
    db = extract(day)
    t1 = time.time()
    out_dir = OUT / f"date={day:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "part.parquet"

    con = duckdb.connect()
    con.execute("SET threads TO 16; SET memory_limit = '16GB';")
    con.execute("INSTALL sqlite; LOAD sqlite;")
    con.execute(f"ATTACH '{db.as_posix()}' AS src (TYPE sqlite, READ_ONLY)")
    raw_rows = con.execute("SELECT count(*) FROM src.vehicle_feed").fetchone()[0]
    # 型を直し、明らかに壊れた行と完全重複（同じ車両・同じ時刻・同じ位置）を落とす
    con.execute(f"""
        COPY (
            SELECT DISTINCT
                vehicle_id,
                to_timestamp(CAST(timestamp AS BIGINT)) AS ts,
                TRY_CAST(lat AS DOUBLE) AS lat,
                TRY_CAST(lng AS DOUBLE) AS lng,
                CAST(speed AS REAL) AS speed,
                CAST(route_id AS INTEGER) AS route_id,
                trip_id
            FROM src.vehicle_feed
            WHERE vehicle_id IS NOT NULL
              AND TRY_CAST(timestamp AS BIGINT) IS NOT NULL
              AND TRY_CAST(lat AS DOUBLE) BETWEEN 27.5 AND 29.5
              AND TRY_CAST(lng AS DOUBLE) BETWEEN 76.5 AND 78.0
            ORDER BY vehicle_id, ts
        ) TO '{out.as_posix()}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 1000000)
    """)
    rows = con.execute(f"SELECT count(*) FROM '{out.as_posix()}'").fetchone()[0]
    con.close()
    t2 = time.time()

    db_size = db.stat().st_size
    if not keep_db:
        db.unlink()
    for side in (db.with_name(db.name + "-wal"), db.with_name(db.name + "-shm")):
        side.unlink(missing_ok=True)  # 読み込み時に作られる SQLite の補助ファイル
    return {
        "date": f"{day}", "raw_rows": raw_rows, "rows": rows,
        "dropped": raw_rows - rows,
        "db_gb": db_size / 1e9, "parquet_gb": out.stat().st_size / 1e9,
        "extract_s": t1 - t0, "convert_s": t2 - t1,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("start")
    ap.add_argument("end", nargs="?")
    ap.add_argument("--keep-db", action="store_true")
    a = ap.parse_args()
    if a.start == "all":
        start, end = date(2026, 10, 1), date(2026, 10, 31)
    else:
        start = date.fromisoformat(a.start)
        end = date.fromisoformat(a.end) if a.end else start
    d = start
    while d <= end:
        r = convert(d, a.keep_db)
        print(f"{r['date']}: {r['raw_rows']:,} 行 → {r['rows']:,} 行（除外 {r['dropped']:,}）"
              f" | {r['db_gb']:.2f} GB → {r['parquet_gb']:.2f} GB"
              f" | 取り出し {r['extract_s']:.0f}s・変換 {r['convert_s']:.0f}s", flush=True)
        d += timedelta(days=1)


if __name__ == "__main__":
    main()
