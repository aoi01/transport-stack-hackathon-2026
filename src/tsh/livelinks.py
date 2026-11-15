"""記録した GTFS-RT から「直近 30 分に、どのリンク（隣り合う停留所の区間）を何秒で走ったか」を作り、
経路検索の乗車時間を補正する（直前のバスによる補正。docs/phase1_prototype.md 10章の V4）。

手順（検証で使った方法と同じ）:
  1. data/raw/gtfs_rt/ の直近 75 分の点を読む。
  2. 点を路線の停留所の並びに重ね、60m 以内で最も近づいた時刻を停留所の通過時刻とする（tsh.passages と同じ）。
  3. 続けて検出された2つの停留所の時刻差を、間のリンクに距離で按分する（tsh.traveltime と同じ）。
  4. 各観測について log(実際の秒 / 過去の推定) を求めておく。
  補正: これから乗るリンクの、直近 30 分の log 比の中央値 r と件数 m から、乗車時間 × exp(r)^(m/(m+20))。
"""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import common as C

RT = C.ROOT / "data/raw/gtfs_rt"
IST = timezone(timedelta(hours=5, minutes=30))
LOOKBACK_S = 75 * 60
WINDOW_S = 30 * 60
SHRINK_C = 20.0
RADIUS_M = 60.0


class LiveLinks:
    def __init__(self, tt, refresh_s: int = 60):
        self.tt = tt
        self.refresh_s = refresh_s
        self._t = 0.0
        self.obs: dict = {}
        self.stats = {"points": 0, "link_obs": 0, "links": 0, "updated": None, "error": None}
        pat = C.patterns()[["route_id", "seq", "stop_id", "stop_lat", "stop_lon", "cum_m"]].copy()
        self.pat = pat

    def refresh(self, force: bool = False) -> None:
        if not force and time.time() - self._t < self.refresh_s:
            return
        self._t = time.time()
        files = sorted(RT.glob("date=*/part-*.parquet"))
        if not files:
            self.stats["error"] = "記録がまだありません（tsh.recorder を起動してください）"
            return
        # 直近の日付フォルダだけ読む（日付またぎに備えて最後の2日）
        days = sorted({f.parent for f in files})[-2:]
        globs = "[" + ",".join(f"'{(d / 'part-*.parquet').as_posix()}'" for d in days) + "]"
        since = int(time.time()) - LOOKBACK_S
        con = C.connect()
        con.register("pat", self.pat)
        dlat, dlng = RADIUS_M / C.M_PER_DEG_LAT, RADIUS_M / C.M_PER_DEG_LNG
        try:
            df = con.execute(f"""
                WITH g AS (
                    SELECT DISTINCT vehicle_id, trip_id, route_id, ts, lat, lng
                    FROM read_parquet({globs}) WHERE ts >= {since}
                ), cand AS (
                    SELECT g.vehicle_id, g.trip_id, g.route_id, g.ts, p.seq,
                           sqrt(pow((g.lat - p.stop_lat) * {C.M_PER_DEG_LAT}, 2) + pow((g.lng - p.stop_lon) * {C.M_PER_DEG_LNG}, 2)) AS d
                    FROM g JOIN pat p ON g.route_id = p.route_id
                     AND g.lat BETWEEN p.stop_lat - {dlat} AND p.stop_lat + {dlat}
                     AND g.lng BETWEEN p.stop_lon - {dlng} AND p.stop_lon + {dlng}
                ), best AS (
                    SELECT vehicle_id, trip_id, route_id, seq, arg_min(ts, d) AS ts
                    FROM cand WHERE d <= {RADIUS_M} GROUP BY ALL
                ), mono AS (
                    SELECT *, max(ts) OVER (PARTITION BY vehicle_id, trip_id ORDER BY seq
                                            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS pm FROM best
                ), ok AS (SELECT * FROM mono WHERE pm IS NULL OR ts > pm),
                pr AS (
                    SELECT route_id, seq, ts, lead(seq) OVER w AS seq2, lead(ts) OVER w AS ts2
                    FROM ok WINDOW w AS (PARTITION BY vehicle_id, trip_id ORDER BY seq)
                ), gg AS (
                    SELECT pr.*, ts2 - ts AS dt_s, b.cum_m - a.cum_m AS d_m, a.cum_m AS c0
                    FROM pr JOIN pat a ON a.route_id = pr.route_id AND a.seq = pr.seq
                            JOIN pat b ON b.route_id = pr.route_id AND b.seq = pr.seq2
                    WHERE seq2 IS NOT NULL AND seq2 - pr.seq <= 5
                )
                SELECT l.stop_id AS a, l2.stop_id AS b,
                       gg.ts + gg.dt_s * (l.cum_m - gg.c0) / gg.d_m AS t,
                       gg.dt_s * (l2.cum_m - l.cum_m) / gg.d_m AS s,
                       l2.cum_m - l.cum_m AS m
                FROM gg JOIN pat l ON l.route_id = gg.route_id AND l.seq >= gg.seq AND l.seq < gg.seq2
                        JOIN pat l2 ON l2.route_id = gg.route_id AND l2.seq = l.seq + 1
                WHERE gg.d_m > 0 AND gg.dt_s > 0 AND gg.d_m / gg.dt_s * 3.6 BETWEEN 1 AND 80 AND l2.cum_m > l.cum_m
            """).df()
            pts = con.execute(f"SELECT count(*) FROM read_parquet({globs}) WHERE ts >= {since}").fetchone()[0]
        except Exception as e:  # noqa: BLE001
            self.stats["error"] = f"読み込み失敗: {e}"
            return
        obs = defaultdict(lambda: ([], []))
        for r in df.itertuples():
            ti = pd.Timestamp(r.t, unit="s", tz="UTC").tz_convert(C.TZ)
            h = self.tt.link_sec(r.a, r.b, r.m, C.day_type(ti.date()), ti.hour)
            if h > 0 and r.s > 0:
                o = obs[(r.a, r.b)]
                o[0].append(r.t); o[1].append(np.log(r.s / h))
        self.obs = {k: (np.array(v[0]), np.array(v[1])) for k, v in obs.items()}
        self.stats.update(points=int(pts), link_obs=int(len(df)), links=len(self.obs),
                          updated=datetime.now(IST).isoformat(timespec="seconds"), error=None)

    def factor(self, route_id: str, i: int, j: int, now_epoch: float) -> tuple[float, int]:
        """路線の seq i→j のリンクについて、直近 30 分の補正係数と観測数。"""
        self.refresh()
        ids = self.tt.stop_ids[route_id]
        logs = []
        for k in range(i, j):
            v = self.obs.get((ids[k], ids[k + 1]))
            if v is None:
                continue
            t, lr = v
            m = (t >= now_epoch - WINDOW_S) & (t < now_epoch)
            logs.extend(lr[m].tolist())
        if not logs:
            return 1.0, 0
        w = len(logs) / (len(logs) + SHRINK_C)
        return float(np.exp(np.median(logs) * w)), len(logs)
