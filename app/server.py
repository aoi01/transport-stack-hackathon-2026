"""経路検索 API とお試し画面。

起動:
  PYTHONPATH=src python -m uvicorn app.server:app --port 8000
  → http://localhost:8000/        地図の画面
  → http://localhost:8000/docs    API の説明（自動生成）

API:
  GET /journeys?from=28.6676,77.2285&to=28.5494,77.2510&depart=2026-11-17T08:30&sort=fastest|comfort&realtime=true
  GET /stops?q=nehru           停留所名の検索
  GET /health
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

from tsh import common as C  # noqa: E402
from tsh.planner import Planner  # noqa: E402
from tsh.livelinks import LiveLinks  # noqa: E402
from tsh.realtime import LiveFeed  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
app = FastAPI(title="Delhi bus journey planner (Transport Stack Hackathon 2026)",
              description="観測 GPS にもとづく所要時間と、乗車券にもとづく混雑度を示すバスの経路検索")
planner = Planner("all")
live = LiveFeed(planner)
live_links = LiveLinks(planner.tt)   # tsh.recorder が記録した GTFS-RT から直近 30 分の区間実績


def _pt(s: str):
    try:
        a, b = s.split(",")
        return float(a), float(b)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"座標は 'lat,lng' で指定してください: {s}") from e


@app.get("/journeys")
def journeys(from_: str = Query(..., alias="from", examples=["28.6676,77.2285"]),
             to: str = Query(..., examples=["28.5494,77.2510"]),
             depart: str | None = Query(None, description="ISO 形式（IST）。省略時は現在時刻"),
             sort: str = Query("fastest", pattern="^(fastest|comfort)$"),
             realtime: bool = Query(True, description="出発が今から15分以内なら GTFS-RT で待ち時間を出す"),
             n: int = Query(3, ge=1, le=6)):
    o, d = _pt(from_), _pt(to)
    t = datetime.fromisoformat(depart) if depart else datetime.now(IST).replace(tzinfo=None, microsecond=0)
    res = planner.plan(o[0], o[1], d[0], d[1], t, sort=sort, max_options=n,
                       live_wait=live.wait_fn() if realtime else None,
                       live_links=live_links if realtime else None)
    res["realtime_feed"] = {"time": live.feed_time.isoformat() if live.feed_time else None, "error": live.error}
    res["live_links"] = live_links.stats
    return res


@app.get("/live")
def live_status():
    """GTFS-RT の記録と直近の区間実績の状況。"""
    live_links.refresh(force=True)
    return live_links.stats


@app.get("/stops")
def stops(q: str, limit: int = 10):
    s = C.stops()
    hit = s[s.stop_name.str.contains(q, case=False, na=False)].head(limit)
    return [{"stop_id": r.stop_id, "name": r.stop_name, "lat": r.stop_lat, "lng": r.stop_lon} for r in hit.itertuples()]


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")
