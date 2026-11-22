"""停留所の通過を地図と「時間・距離の図」で見せる画面（問題1の土台の確かめ用）。

GPS の点から「どのバスが、どの停留所を、何時に通ったか」を出す方法（tsh.passages）を、1便ずつ目で確かめられるようにする。
  - 地図: 路線の形、停留所（判定ごとに色分け）、停留所のまわり 60m の円、その便の GPS の点（時刻で色が変わる）、
          通過とみなした点と停留所を結ぶ線。再生ボタンでバスの動きをたどれる。
  - 時間・距離の図（マーレイ図）: 横が時刻、縦が始点からの距離。その日の全便の通過を線で描き、
          選んだ便の GPS の点と時刻表の線を重ねる。線の傾きが速さ、線どうしの間隔が運行間隔になる。
  - 同じ系統の全バス: 選んだ便のほか、その日にこの系統（上り・下り）を走った全バスを、再生の時刻に合わせて地図で動かす。
  - 停留所ごとの検出率: その日にこの停留所の前後を走った便のうち、通過を検出できた便の割合。

画面:  http://localhost:8000/passages （app.server に組み込み済み）
単体:  python -m uvicorn app.viz:app --app-dir . --port 8001  → http://localhost:8001/passages
API:
  GET /viz/api/routes?q=764
  GET /viz/api/trips?route_id=2232&date=2026-10-15
  GET /viz/api/trip?route_id=2232&date=2026-10-15&vehicle_id=DL1PD5165&trip_id=2232_08_23_474
  GET /viz/api/marey?route_id=2232&date=2026-10-15
  GET /viz/api/fleet?route_id=2232&date=2026-10-15     （上り・下りの全バスの GPS、30秒おきに間引き）
  GET /viz/api/overview                                 （10月の全体と日ごとの、検出した路線・車両・便・通過の数）
"""
from __future__ import annotations

import re
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
STATUS = {"pass": "passed", "order": "passed nearby, dropped by the stop-order check", "none": f"no GPS point within {RADIUS_M:.0f} m"}

router = APIRouter()


def _day(s: str) -> date:
    try:
        d = date.fromisoformat(s)
    except ValueError as e:
        raise HTTPException(400, f"Date must be YYYY-MM-DD: {s}") from e
    if d not in DAYS:
        raise HTTPException(400, "Data covers 2026-10-01 to 2026-10-31 only")
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
        raise HTTPException(404, f"Route {route_id} is not in the timetable")
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
    st = _route(route_id)
    n_stops = len(st)
    with duckdb.connect() as con:
        df = con.execute(f"""
            SELECT vehicle_id, trip_id, count(*) AS n, min(seq) AS s0, max(seq) AS s1,
                   epoch(min(ts)) AS t0, epoch(max(ts)) AS t1, median(dist_m) AS med_d
            FROM '{pf}' WHERE route_id = ? GROUP BY ALL ORDER BY t0""", [int(route_id)]).df()
        per = con.execute(f"""
            WITH p AS (SELECT vehicle_id, trip_id, seq FROM '{pf}' WHERE route_id = ?),
                 t AS (SELECT vehicle_id, trip_id, min(seq) AS s0, max(seq) AS s1 FROM p GROUP BY ALL)
            SELECT p.seq, count(*) AS n, count(*) FILTER (WHERE t.s0 < p.seq AND p.seq < t.s1) AS n_in
            FROM p JOIN t USING (vehicle_id, trip_id) GROUP BY p.seq""", [int(route_id)]).df()
    # 停留所ごとの検出率: 最初と最後に検出した停留所の「間」にこの停留所がある便（＝確実にここを通った便）のうち、
    # ここでも通過を検出できた便の割合。最初・最後の停留所そのものは、検出した便しか数えられないので率を出さない
    n_all, n_in = dict(zip(per.seq, per.n)), dict(zip(per.seq, per.n_in))
    s0, s1 = df.s0.to_numpy(), df.s1.to_numpy()
    seq_stats = [{"seq": int(q), "n": int(n_all.get(q, 0)), "n_in": int(n_in.get(q, 0)),
                  "cover": int(((s0 < q) & (s1 > q)).sum())} for q in st.seq]
    return {"route_id": route_id, "date": str(d), "n_stops": n_stops, "seq_stats": seq_stats,
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
        raise HTTPException(404, "No GPS points found for this trip")
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
        "shape_source": "GTFS shapes.txt" if shape else "straight lines between stops",
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


def _pair(route_id: str) -> list[dict]:
    """選んだ路線と、同じ系統の逆向きの路線（764UP ↔ 764DOWN）。"""
    p = _pat().drop_duplicates("route_id")
    names = dict(zip(p.route_id, p.route_short_name))
    name = names.get(str(route_id)) or ""
    out = [{"route_id": str(route_id), "name": name, "dir": "same"}]
    m = re.match(r"^(.*?)(UP|DOWN)$", name)
    if m:
        other = m.group(1) + ("DOWN" if m.group(2) == "UP" else "UP")
        out += [{"route_id": r, "name": n, "dir": "opposite"} for r, n in names.items() if n == other]
    return out


@router.get("/viz/api/fleet")
def fleet(route_id: str, date: str, step_s: int = Query(30, ge=5, le=120)):
    """その日にこの系統（上り・下り）を走った全バスの GPS。地図で全バスを同時に動かすために、step_s 秒おきに間引く。"""
    d = _day(date)
    _, gf = _files(d)
    pair = _pair(route_id)
    ids = [int(r["route_id"]) for r in pair]
    with duckdb.connect() as con:
        df = con.execute(f"""
            SELECT route_id, vehicle_id, trip_id, CAST(epoch(ts) AS BIGINT) AS t, round(lat, 5) AS lat, round(lng, 5) AS lng
            FROM '{gf}' WHERE route_id IN ({",".join("?" * len(ids))})
            ORDER BY route_id, vehicle_id, trip_id, ts""", ids).df()
    df["b"] = df.t // step_s
    df = df.drop_duplicates(["route_id", "vehicle_id", "trip_id", "b"])
    dirs = {int(r["route_id"]): r["dir"] for r in pair}
    trips = []
    for (rid, v, tid), g in df.groupby(["route_id", "vehicle_id", "trip_id"], sort=False):
        if len(g) < 5:   # 数点しかない便（GPS の乱れや便の区切りの誤り）は出さない
            continue
        trips.append({"route_id": str(rid), "dir": dirs[int(rid)], "vehicle_id": v, "trip_id": tid,
                      "pts": [[int(t), float(a), float(b)] for t, a, b in zip(g.t, g.lat, g.lng)]})
    return {"route_id": route_id, "date": str(d), "routes": pair, "step_s": step_s, "trips": trips}


@lru_cache(maxsize=1)
def _overview() -> dict:
    src = f"read_parquet('{(PASS_DIR / '*' / 'part.parquet').as_posix()}', hive_partitioning = false)"
    with duckdb.connect() as con:
        tot = con.execute(f"""SELECT count(*), count(DISTINCT (date, vehicle_id, trip_id)), count(DISTINCT route_id),
                                     count(DISTINCT vehicle_id) FROM {src}""").fetchone()
        per = con.execute(f"""SELECT date, count(*), count(DISTINCT (vehicle_id, trip_id)), count(DISTINCT route_id),
                                     count(DISTINCT vehicle_id) FROM {src} GROUP BY date ORDER BY date""").fetchall()
    keys = ["passages", "trips", "routes", "vehicles"]
    return {"total": dict(zip(keys, map(int, tot))),
            "days": {str(r[0]): dict(zip(keys, map(int, r[1:]))) for r in per},
            "n_routes_gtfs": int(_pat().route_id.nunique())}


@router.get("/viz/api/overview")
def overview():
    """10月の全体と日ごとに、通過を検出した路線・車両・便・通過の数。"""
    return _overview()


@router.get("/passages")
def passages_page():
    return FileResponse(ROOT / "app" / "static" / "passages.html")


app = FastAPI(title="停留所の通過の確かめ（単体）")
app.include_router(router)
