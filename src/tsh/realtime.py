"""GTFS-RT（リアルタイムのバス位置）を使った「次のバスがあと何分で来るか」の推定。

検証（validate_p1）で使ったのと同じ考え方:
  乗車停留所より手前を走っている同じ路線のバスの現在位置を、路線の停留所列に寄せ（300m 以内の最寄り停留所）、
  そこから乗車停留所までの乗車時間をモデルで足して到着時刻を出す。最も早いバスまでの時間を待ち時間とする。
  手前にバスが見えなければ None（呼び出し側が過去の実績の待ち時間を使う）。
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests

from . import common as C

URL = "https://dts-backend.transportstack.in/api/dataset/otd/get-file"
PARAMS = {"agency": "delhi-buses", "category": "realtime_gtfs", "filename": "VehiclePositions.pb"}
IST = timezone(timedelta(hours=5, minutes=30))


def api_key() -> str | None:
    k = os.environ.get("DTS_API_KEY")
    env = C.ROOT / ".env"
    if not k and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("DTS_API_KEY="):
                k = line.split("=", 1)[1].strip()
    return k


class LiveFeed:
    def __init__(self, planner, ttl: int = 30):
        self.p = planner
        self.ttl = ttl
        self._t = 0.0
        self._by_route: dict[str, list] = {}
        self.feed_time = None
        self.error = None

    def refresh(self) -> None:
        if time.time() - self._t < self.ttl:
            return
        self._t = time.time()
        key = api_key()
        if not key:
            self.error = "API キーがありません（.env の DTS_API_KEY）"
            return
        try:
            from google.transit import gtfs_realtime_pb2
            r = requests.get(URL, params=PARAMS, headers={"x-api-key": key}, timeout=20)
            r.raise_for_status()
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(r.content)
        except Exception as e:  # noqa: BLE001
            self.error = f"取得失敗: {e}"
            return
        by = {}
        for e in feed.entity:
            if not e.HasField("vehicle"):
                continue
            v = e.vehicle
            by.setdefault(str(v.trip.route_id), []).append(
                (v.position.latitude, v.position.longitude, v.timestamp or feed.header.timestamp))
        self._by_route = by
        self.feed_time = datetime.fromtimestamp(feed.header.timestamp, IST)
        self.error = None

    def wait_fn(self, now_tol_min: int = 15):
        """planner.plan(live_wait=...) に渡す関数。出発時刻が今から ±15 分以内のときだけ使う。"""
        def f(route_id: str, i: int, t: datetime):
            now = datetime.now(IST).replace(tzinfo=None)
            if abs((t - now).total_seconds()) > now_tol_min * 60:
                return None
            self.refresh()
            veh = self._by_route.get(str(route_id))
            if not veh:
                return None
            xy = self.p.seq_xy[route_id]
            best = None
            for lat, lng, ts in veh:
                d = C.dist_m(lat, lng, xy[:, 0], xy[:, 1])
                k = int(np.argmin(d))
                if d[k] > 300 or k >= i:
                    continue
                t_k = datetime.fromtimestamp(ts, IST).replace(tzinfo=None)
                eta = t_k + timedelta(seconds=self.p.tt.ride_sec(route_id, k, i, t_k))
                w = (eta - t).total_seconds()
                if w >= -60 and (best is None or w < best):
                    best = max(w, 0.0)
            return best
        return f
