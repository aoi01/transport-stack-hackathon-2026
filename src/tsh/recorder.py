"""GTFS-RT（バスの現在位置）を定期的に取得して記録する。

- 20 秒ごとに VehiclePositions を取得し、車両ごとに前回より新しい点だけを残す（同じ点の重複を防ぐ）。
- 60 秒ごとに data/raw/gtfs_rt/date=YYYY-MM-DD/part-HHMMSS.parquet に書き出す（IST の日付で分ける）。
  経路検索 API は、このファイルから直近 30 分の区間の実績を作る。
- 取得に失敗しても止まらずに続ける（指数的に間隔を延ばして再試行）。ログは data/raw/gtfs_rt/recorder.log。

起動:  PYTHONPATH=src python -m tsh.recorder
止める: Ctrl+C（Windows ではタスクを終了）
列: vehicle_id, route_id, trip_id, lat, lng, speed, ts（GPS の時刻・UTC epoch 秒）, fetched（取得時刻・UTC epoch 秒）
"""
from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from . import common as C
from .realtime import PARAMS, URL, api_key

OUT = C.ROOT / "data/raw/gtfs_rt"
IST = timezone(timedelta(hours=5, minutes=30))
POLL_S = 20
FLUSH_S = 60
LOCK_PORT = 47811


def fetch(key: str):
    from google.transit import gtfs_realtime_pb2
    r = requests.get(URL, params=PARAMS, headers={"x-api-key": key}, timeout=30)
    r.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    now = time.time()
    rows = []
    for e in feed.entity:
        if not e.HasField("vehicle"):
            continue
        v = e.vehicle
        rows.append((v.vehicle.id or e.id, v.trip.route_id, v.trip.trip_id, v.position.latitude,
                     v.position.longitude, v.position.speed, int(v.timestamp or feed.header.timestamp), now))
    return rows, feed.header.timestamp, len(r.content)


def flush(buf: list) -> int:
    if not buf:
        return 0
    df = pd.DataFrame(buf, columns=["vehicle_id", "route_id", "trip_id", "lat", "lng", "speed", "ts", "fetched"])
    df["day"] = pd.to_datetime(df.ts, unit="s", utc=True).dt.tz_convert(C.TZ).dt.strftime("%Y-%m-%d")
    stamp = datetime.now(IST).strftime("%H%M%S")
    for day, g in df.groupby("day"):
        d = OUT / f"date={day}"
        d.mkdir(parents=True, exist_ok=True)
        g.drop(columns="day").to_parquet(d / f"part-{stamp}.parquet", index=False, compression="zstd")
    return len(df)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.FileHandler(OUT / "recorder.log", encoding="utf-8"), logging.StreamHandler()])
    key = api_key()
    if not key:
        sys.exit(".env に DTS_API_KEY がありません")
    # 二重起動の防止: ローカルのポートを1つ確保できたときだけ動く（2つ目は即終了）
    import socket
    guard = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        guard.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        logging.info("すでに記録が動いているので終了します")
        return
    last_ts: dict[str, int] = {}
    buf: list = []
    last_flush = time.time()
    backoff = POLL_S
    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    logging.info("記録を開始（%d 秒ごとに取得、%d 秒ごとに保存）", POLL_S, FLUSH_S)
    while not stop["flag"]:
        t0 = time.time()
        try:
            rows, feed_ts, size = fetch(key)
            new = [r for r in rows if r[6] > last_ts.get(r[0], 0)]
            for r in new:
                last_ts[r[0]] = r[6]
            buf.extend(new)
            backoff = POLL_S
            logging.info("取得 %d 台（新しい点 %d）フィード時刻 %s・%d KB",
                         len(rows), len(new), datetime.fromtimestamp(feed_ts, IST).strftime("%H:%M:%S"), size // 1024)
        except Exception as e:  # noqa: BLE001
            backoff = min(backoff * 2, 300)
            logging.warning("取得失敗: %s（%d 秒後に再試行）", e, backoff)
        if time.time() - last_flush >= FLUSH_S:
            n = flush(buf)
            buf = []
            last_flush = time.time()
            if n:
                logging.info("保存 %d 点", n)
        time.sleep(max(0.0, backoff - (time.time() - t0)))
    flush(buf)
    logging.info("記録を終了")


if __name__ == "__main__":
    main()
