"""Delhi Transport Stack の GTFS-RT (VehiclePositions) API が使えるか確認する。

使い方:
  1. リポジトリ直下の .env に  DTS_API_KEY=<メールで届いたキー>  と書く（.env は git 管理外）
  2. python scripts/check_gtfs_rt.py

gtfs-realtime-bindings が入っていれば中身（車両数・時刻・例）も表示する:
  pip install gtfs-realtime-bindings
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# 承認メールに記載のエンドポイント（手順書 PDF では delhi.transportstack.in だったが、メールは dts-backend）
URL = "https://dts-backend.transportstack.in/api/dataset/otd/get-file"
PARAMS = {"agency": "delhi-buses", "category": "realtime_gtfs", "filename": "VehiclePositions.pb"}


def load_key() -> str:
    key = os.environ.get("DTS_API_KEY")
    env = Path(__file__).resolve().parent.parent / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DTS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit(".env に DTS_API_KEY がありません")
    return key


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows コンソールでの文字化け対策
    r =requests.get(URL, params=PARAMS, headers={"x-api-key": load_key()}, timeout=60)
    print(f"HTTP {r.status_code}, {len(r.content):,} bytes, Content-Type: {r.headers.get('Content-Type')}")
    if r.status_code != 200:
        print(r.text[:500])
        sys.exit(1)

    try:
        from google.transit import gtfs_realtime_pb2
    except ImportError:
        print("（gtfs-realtime-bindings 未インストールのため中身の解析は省略）")
        return

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    ts = datetime.fromtimestamp(feed.header.timestamp, tz=timezone.utc)
    vehicles = [e.vehicle for e in feed.entity if e.HasField("vehicle")]
    print(f"フィード時刻: {ts.isoformat()}  エンティティ数: {len(feed.entity)}  車両位置: {len(vehicles)}")
    for v in vehicles[:3]:
        print(f"  vehicle={v.vehicle.id} route={v.trip.route_id} trip={v.trip.trip_id} "
              f"lat={v.position.latitude:.5f} lng={v.position.longitude:.5f} t={v.timestamp}")


if __name__ == "__main__":
    main()
