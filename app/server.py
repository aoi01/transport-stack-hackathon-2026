"""経路検索 API とお試し画面。

起動:
  PYTHONPATH=src python -m uvicorn app.server:app --port 8000
  → http://localhost:8000/        地図の画面
  → http://localhost:8000/docs    API の説明（自動生成）

API:
  GET /journeys?from=28.6676,77.2285&to=28.5494,77.2510&depart=2026-11-17T08:30&sort=fastest|comfort|fewer_transfers&realtime=true
  GET /journeys?from=...&to=...&arrive=2026-11-17T09:30   （到着時刻を指定。85% の日で間に合う最も遅い出発）
  GET /stops?q=nehru           停留所名の検索
  GET /passages                停留所の通過を地図で確かめる画面（API は /viz/api/...、app/viz.py）
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
from tsh.crowding2 import CrowdingModel2  # noqa: E402
from tsh.planner import Planner  # noqa: E402
from tsh.livelinks import LiveLinks  # noqa: E402
from tsh.realtime import LiveFeed  # noqa: E402
from tsh.segmodel import SegModel  # noqa: E402
from tsh.live_excess import load as live_wait_excess  # noqa: E402
from tsh.waitmodel import PassageTimetable, WaitModel  # noqa: E402

from app.viz import router as viz_router  # noqa: E402  停留所の通過を確かめる画面（/passages）
from app import i18n  # noqa: E402  説明文を英語にする（lang=en、既定）

IST = timezone(timedelta(hours=5, minutes=30))
app = FastAPI(title="Delhi bus journey planner (Transport Stack Hackathon 2026)",
              description="観測 GPS にもとづく所要時間と、乗車券にもとづく混雑度を示すバスの経路検索")
app.include_router(viz_router)
planner = Planner("all")
live = LiveFeed(planner)
live_links = LiveLinks(planner.tt)   # tsh.recorder が記録した GTFS-RT から直近 30 分の区間実績
try:
    planner.seg = SegModel()          # 乗る区間全体の LightGBM（中央値・85% 点）
except Exception as e:  # noqa: BLE001  モデルが無ければ従来の方式で動かす
    print("区間モデルを読み込めませんでした（従来の方式を使います）:", e)
wait_model = WaitModel(planner.tt)    # 折り返し・前のバスからの経過を使う待ち時間
try:
    # 前もって計画するとき: 待ちは「実際の通過の時刻表」（14章）、合計時間と順位は「過去の同じ種類の日に同じ時刻に
    # 出ていたら」の再現の中央値。過去の半分以上の日でバスが来ていない案は後ろへ回す（16章）
    planner.plan_wait = PassageTimetable(C.TRAIN_DAYS + C.TEST_DAYS)
    planner.plan_replay = True
    # 選ぶことによる偏りの較正（17章）: 再現の分布の読み替え。無ければ再現の中央値・85% 点のまま
    from tsh.plan_calib import load as load_plan_calib
    planner.plan_calib = load_plan_calib()
    if planner.plan_calib is None:
        print("plan_calib.json が無いので、前もって計画の較正なしで動かします（python -m tsh.plan_calib で作る）")
except Exception as e:  # noqa: BLE001
    print("通過の時刻表を読み込めませんでした（区間ごとの予測の和を使います）:", e)
# 「今すぐ出る」で 1 本目の待ちがリアルタイムのとき、余裕を見た到着に「見えていたバスが来ない」場合も入れる（16.6）
planner.live_excess = live_wait_excess()
if planner.live_excess is None:
    print("live_wait_excess.json が無いので、リアルタイムの余裕を見た到着は点の予測のまま（python -m tsh.live_excess で作る）")
try:
    planner.cr = CrowdingModel2("all")  # 便ベース＋縮小推定、路線ごとの拡大係数、車種別の定員、混雑の確率
except Exception as e:  # noqa: BLE001
    print("改良版の混雑モデルを読み込めませんでした（従来の方式を使います）:", e)


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
             arrive: str | None = Query(None, description="到着時刻を指定するとき（ISO 形式、IST）。過去の同じ種類の日の "
                                        "85% で間に合う最も遅い出発を返す（depart より優先、リアルタイムは使わない）"),
             sort: str = Query("fastest", pattern="^(fastest|comfort|fewer_transfers)$"),
             realtime: bool = Query(True, description="出発が今から15分以内なら GTFS-RT で待ち時間を出す"),
             n: int = Query(3, ge=1, le=6),
             lang: str = Query("en", pattern="^(en|ja)$", description="説明文の言語（en / ja）")):
    o, d = _pt(from_), _pt(to)
    tr = i18n.response if lang == "en" else (lambda x: x)
    if arrive:
        return tr(planner.plan_arrive(o[0], o[1], d[0], d[1], datetime.fromisoformat(arrive), sort=sort, max_options=n))
    t = datetime.fromisoformat(depart) if depart else datetime.now(IST).replace(tzinfo=None, microsecond=0)
    res = planner.plan(o[0], o[1], d[0], d[1], t, sort=sort, max_options=n,
                       live_wait=live.wait_fn(wait_model=wait_model, live_links=live_links) if realtime else None,
                       live_links=live_links if realtime else None)
    res["realtime_feed"] = {"time": live.feed_time.isoformat() if live.feed_time else None, "error": live.error}
    res["live_links"] = live_links.stats
    return tr(res)


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
