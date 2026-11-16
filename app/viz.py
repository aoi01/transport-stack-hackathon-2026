"""停留所の通過を地図と「時間・距離の図」で見せる画面（問題1の土台の確かめ用）。

GPS の点から「どのバスが、どの停留所を、何時に通ったか」を出す方法（tsh.passages）を、1便ずつ目で確かめられるようにする。
  - 地図: 路線の形、停留所（判定ごとに色分け）、停留所のまわり 60m の円、その便の GPS の点（時刻で色が変わる）、
          通過とみなした点と停留所を結ぶ線。再生ボタンでバスの動きをたどれる。
  - 時間・距離の図（マーレイ図）: 横が時刻、縦が始点からの距離。その日の全便の通過を線で描き、
          選んだ便の GPS の点と時刻表の線を重ねる。線の傾きが速さ、線どうしの間隔が運行間隔になる。

画面:  http://localhost:8000/passages （app.server に組み込み済み）
単体:  python -m uvicorn app.viz:app --app-dir . --port 8001  → http://localhost:8001/passages
API:
  GET /viz/api/routes?q=764
  GET /viz/api/trips?route_id=2232&date=2026-10-15
  GET /viz/api/trip?route_id=2232&date=2026-10-15&vehicle_id=DL1PD5165&trip_id=2232_08_23_474
  GET /viz/api/marey?route_id=2232&date=2026-10-15
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tsh import common as C  # noqa: E402
from tsh.passages import OUT as PASS_DIR, RADIUS_M  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
DAYS = [date(2026, 10, d) for d in range(1, 32)]
STATUS = {"pass": "通過", "order": "近くを通ったが順番の確認で除外", "none": f"{RADIUS_M:.0f}m 以内に GPS の点なし"}

router = APIRouter()


def _day(s: str) -> date:
    try:
        d = date.fromisoformat(s)
    except ValueError as e:
        raise HTTPException(400, f"日付は YYYY-MM-DD で指定してください: {s}") from e
    if d not in DAYS:
        raise HTTPException(400, "データがあるのは 2026-10-01〜2026-10-31 です")
    return d


def _files(d: date) -> tuple[str, str]:
    return ((PASS_DIR / f"date={d:%Y-%m-%d}" / "part.parquet").as_posix(),
            (C.GPS / f"date={d:%Y-%m-%d}" / "part.parquet").as_posix())


def _hm(ep: float) -> str:
    return datetime.fromtimestamp(ep, IST).strftime("%H:%M:%S")


@lru_cache(maxsize=1)
def _pat() -> pd.DataFrame:
    p = C.patterns().copy()
    p["route_id"] = p.route_id.astype(str)
    return p


def _route(route_id: str) -> pd.DataFrame:
    g = _pat()[_pat().route_id == str(route_id)].sort_values("seq")
    if g.empty:
        raise HTTPException(404, f"路線 {route_id} は時刻表にありません")
    return g


@lru_cache(maxsize=1)
def _route_shape_ids() -> dict:
    tr = pd.read_csv(C.GTFS / "trips.txt", dtype=str, usecols=["route_id", "shape_id"]).dropna()
    return tr.groupby("route_id").shape_id.agg(lambda s: s.value_counts().index[0]).to_dict()


@lru_cache(maxsize=1)
def _shapes() -> dict:
    s = pd.read_csv(C.GTFS / "shapes.txt", dtype={"shape_id": str})
    s = s.sort_values(["shape_id", "shape_pt_sequence"])
    return {k: g[["shape_pt_lat", "shape_pt_lon"]].round(6).to_numpy().tolist() for k, g in s.groupby("shape_id")}


@lru_cache(maxsize=1)
def _schedule() -> pd.DataFrame:
    return pd.read_parquet(C.PROCESSED / "schedule.parquet")


def _project(lat, lng, slat, slon, cum):
    """点を停留所を結んだ折れ線に投影して、始点からの距離（m）と線からの距離（m）を返す。"""
    if len(slat) < 2 or len(lat) == 0:
        return np.zeros(len(lat)), np.zeros(len(lat))
    py = (np.asarray(lat)[:, None] - slat[None, :-1]) * C.M_PER_DEG_LAT
    px = (np.asarray(lng)[:, None] - slon[None, :-1]) * C.M_PER_DEG_LNG
    sy = (slat[1:] - slat[:-1])[None, :] * C.M_PER_DEG_LAT
    sx = (slon[1:] - slon[:-1])[None, :] * C.M_PER_DEG_LNG
    L2 = np.maximum(sx * sx + sy * sy, 1e-9)
    t = np.clip((px * sx + py * sy) / L2, 0, 1)
    d = np.hypot(px - t * sx, py - t * sy)
    k = np.argmin(d, axis=1)
    r = np.arange(len(lat))
    along = cum[:-1][k] + t[r, k] * np.sqrt(L2[0, k])
    return along, d[r, k]


@router.get("/viz/api/routes")
def routes(q: str = Query("", description="路線番号の一部（例: 764, 534）"), limit: int = 30,
           route_id: str | None = Query(None, description="この route_id の路線だけを返す")):
    p = _pat()
    g = p.groupby("route_id").agg(name=("route_short_name", "first"), desc=("route_desc", "first"),
                                   n_stops=("seq", "size"), km=("cum_m", "max")).reset_index()
    if route_id:
        g = g[g.route_id == str(route_id)]
    elif q:
        g = g[g.name.str.contains(q, case=False, na=False) | g.desc.str.contains(q, case=False, na=False)]
    g = g.sort_values("name").head(limit)
    return [{"route_id": r.route_id, "name": r.name, "desc": r.desc, "n_stops": int(r.n_stops),
             "km": round(float(r.km) / 1000, 1)} for r in g.itertuples()]


@router.get("/viz/api/trips")
def trips(route_id: str, date: str):
    d = _day(date)
    pf, _ = _files(d)
    n_stops = len(_route(route_id))
    with duckdb.connect() as con:
        df = con.execute(f"""
            SELECT vehicle_id, trip_id, count(*) AS n, min(seq) AS s0, max(seq) AS s1,
                   epoch(min(ts)) AS t0, epoch(max(ts)) AS t1, median(dist_m) AS med_d
            FROM '{pf}' WHERE route_id = ? GROUP BY ALL ORDER BY t0""", [int(route_id)]).df()
    return {"route_id": route_id, "date": str(d), "n_stops": n_stops,
            "trips": [{"vehicle_id": r.vehicle_id, "trip_id": r.trip_id, "n": int(r.n), "s0": int(r.s0), "s1": int(r.s1),
                       "start": _hm(r.t0), "end": _hm(r.t1), "minutes": round((r.t1 - r.t0) / 60, 1),
                       "med_dist_m": round(float(r.med_d), 1)} for r in df.itertuples()]}


@router.get("/viz/api/trip")
def trip(route_id: str, date: str, vehicle_id: str, trip_id: str):
    d = _day(date)
    pf, gf = _files(d)
    st = _route(route_id)
    with duckdb.connect() as con:
        ps = con.execute(f"SELECT seq, epoch(ts) AS t, dist_m FROM '{pf}' WHERE route_id = ? AND vehicle_id = ? AND trip_id = ? ORDER BY seq",
                         [int(route_id), vehicle_id, trip_id]).df()
        gp = con.execute(f"SELECT epoch(ts) AS t, lat, lng, speed FROM '{gf}' WHERE vehicle_id = ? AND trip_id = ? ORDER BY ts",
                         [vehicle_id, trip_id]).df()
    if gp.empty:
        raise HTTPException(404, "この便の GPS の点が見つかりません")
    slat, slon, cum = st.stop_lat.to_numpy(), st.stop_lon.to_numpy(), st.cum_m.to_numpy()
    # 停留所ごとの判定（tsh.passages と同じ考え方を、この便の点だけで再現する）
    dd = C.dist_m(slat[:, None], slon[:, None], gp.lat.to_numpy()[None, :], gp.lng.to_numpy()[None, :])
    near_i = dd.argmin(axis=1)
    near_d = dd[np.arange(len(st)), near_i]
    passed = dict(zip(ps.seq, zip(ps.t, ps.dist_m)))
    stops, prev = [], None
    for k, r in enumerate(st.itertuples()):
        if r.seq in passed:
            t, dm = passed[r.seq]
            status = "pass"
            # 通過に使った点（停留所に最も近い点）
            j = int(np.argmin(np.abs(gp.t.to_numpy() - t)))
            link = None
            if prev is not None:
                link = {"from_seq": prev[0], "sec": round(t - prev[1]), "m": round(float(r.cum_m - prev[2]))}
            prev = (int(r.seq), t, float(r.cum_m))
            stops.append({"seq": int(r.seq), "name": r.stop_name, "lat": r.stop_lat, "lng": r.stop_lon,
                          "km": round(float(r.cum_m) / 1000, 3), "status": status, "label": STATUS[status],
                          "t": t, "time": _hm(t), "dist_m": round(float(dm), 1),
                          "point": [float(gp.lat.iloc[j]), float(gp.lng.iloc[j])], "link": link})
        else:
            status = "order" if near_d[k] <= RADIUS_M else "none"
            stops.append({"seq": int(r.seq), "name": r.stop_name, "lat": r.stop_lat, "lng": r.stop_lon,
                          "km": round(float(r.cum_m) / 1000, 3), "status": status, "label": STATUS[status],
                          "t": None, "time": None, "dist_m": round(float(near_d[k]), 1),
                          "near_time": _hm(gp.t.iloc[int(near_i[k])])})
    along, off = _project(gp.lat.to_numpy(), gp.lng.to_numpy(), slat, slon, cum)
    gaps = np.diff(gp.t.to_numpy())
    sid = _route_shape_ids().get(str(route_id))
    shape = _shapes().get(sid) if sid else None
    return {
        "route_id": route_id, "name": st.route_short_name.iloc[0], "desc": st.route_desc.iloc[0],
        "date": str(d), "vehicle_id": vehicle_id, "trip_id": trip_id, "radius_m": RADIUS_M,
        "summary": {"n_stops": len(st), "n_pass": int((ps.seq >= 0).sum()),
                    "n_order": sum(s["status"] == "order" for s in stops),
                    "n_none": sum(s["status"] == "none" for s in stops),
                    "n_points": len(gp), "interval_s": float(np.median(gaps)) if len(gaps) else None,
                    "med_dist_m": round(float(ps.dist_m.median()), 1) if len(ps) else None,
                    "start": _hm(gp.t.iloc[0]), "end": _hm(gp.t.iloc[-1])},
        "stops": stops,
        "gps": [{"t": float(t), "time": _hm(t), "lat": float(a), "lng": float(b), "speed": None if pd.isna(v) else float(v),
                 "km": round(float(x) / 1000, 3), "off_m": round(float(o), 1)}
                for t, a, b, v, x, o in zip(gp.t, gp.lat, gp.lng, gp.speed, along, off)],
        "shape": shape or st[["stop_lat", "stop_lon"]].to_numpy().tolist(),
        "shape_source": "GTFS の shapes.txt" if shape else "停留所を直線で結んだもの",
    }


@router.get("/viz/api/marey")
def marey(route_id: str, date: str):
    """その日の全便の通過（時刻, 距離）と、時刻表の便。"""
    d = _day(date)
    pf, _ = _files(d)
    st = _route(route_id)
    cum = dict(zip(st.seq, st.cum_m))
    with duckdb.connect() as con:
        df = con.execute(f"SELECT vehicle_id, trip_id, seq, epoch(ts) AS t FROM '{pf}' WHERE route_id = ? ORDER BY vehicle_id, trip_id, seq",
                         [int(route_id)]).df()
    out = []
    for (v, tid), g in df.groupby(["vehicle_id", "trip_id"], sort=False):
        out.append({"vehicle_id": v, "trip_id": tid,
                    "pts": [[float(t), round(float(cum[s]) / 1000, 3)] for s, t in zip(g.seq, g.t) if s in cum]})
    sc = _schedule()
    sc = sc[sc.route_id == str(route_id)]
    day0 = datetime(d.year, d.month, d.day, tzinfo=IST).timestamp()
    sched = [[[day0 + float(t), round(float(cum[s]) / 1000, 3)] for s, t in zip(g.seq, g.t_s) if s in cum]
             for _, g in sc.sort_values(["trip_id", "seq"]).groupby("trip_id")]
    return {"route_id": route_id, "date": str(d), "day0": day0,
            "stops": [{"seq": int(r.seq), "name": r.stop_name, "km": round(float(r.cum_m) / 1000, 3)} for r in st.itertuples()],
            "trips": out, "schedule": sched}


@router.get("/passages")
def passages_page():
    return FileResponse(ROOT / "app" / "static" / "passages.html")


app = FastAPI(title="停留所の通過の確かめ（単体）")
app.include_router(router)
