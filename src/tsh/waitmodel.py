"""API 用の待ち時間モデル（docs/phase1_prototype.md 12章の「W8」と 14章の「W9」）。

最初のバスの待ち時間を、次の順で決める（出発が今から 15 分以内のとき）:
  1. 乗車停留所より手前を走っている同じ路線のバスが見えれば、その到着予測（tsh.realtime と同じ）
  2. 見えなければ、反対方向の路線を走っていて折り返してくるバスの到着予測（折り返しの組と終点での休憩は 10 月の実績から）、
     「停留所を最後のバスが通ってからの経過時間」で条件づけた残りの待ち時間 E[H − e | H > e]、
     「実際の発車の時刻表」による待ち時間（下の 3）の 3 つの平均（事前に決めた等しい重み）
  3. 折り返しのバスも無ければ、次のバスはまだ始発を出ていないとみなし、「実際の発車の時刻表」で出す:
     10 月の同じ平日/休日の各日に GPS で始発付近を出た時刻から、今以降の最初の発車までの時間の中央値
     ＋ 始発から乗車停留所までの所要時間（3 日分以上なければ、経過時間で条件づけた残りの待ち時間）。
     GTFS の時刻表は実際の発車と合わない（時刻表の時間帯の 24% では便がほとんど走っていない）ので使わない。
検証（10/25〜31、3,000 件）で待ち時間の誤差中央値 36.6% → 33.3%（W8）→ 28.9%（W9、−4.3 ポイント、95% 区間 −5.6〜−3.1）、
待ち時間込みの合計 24.9% → 23.5%（W8）→ 20.4%（W9）。実験は experiments/p1_external/missing_trips.py。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import common as C
from .improve_wait import Residual, chaining, headway_samples
from .traveltime import passages_glob

SERVE = C.PROCESSED / "serve"
IST = timezone(timedelta(hours=5, minutes=30))


def actual_departures(days) -> pd.DataFrame:
    """GPS で始発付近（seq ≤ 3）を出た時刻: route_id, date, sec（その日の 0 時からの秒、IST）。5 停留所以上走った便だけ。"""
    con = C.connect()
    return con.execute(f"""
        WITH t AS (SELECT date, vehicle_id, trip_id, route_id, min(ts) AS t0, min(seq) AS s0
                   FROM read_parquet({passages_glob(days)}) GROUP BY ALL HAVING max(seq) - min(seq) >= 5)
        SELECT CAST(route_id AS VARCHAR) AS route_id, date,
               hour(timezone('{C.TZ}', t0)) * 3600 + minute(timezone('{C.TZ}', t0)) * 60 + second(timezone('{C.TZ}', t0)) AS sec
        FROM t WHERE s0 <= 3""").df()


class WaitModel:
    def __init__(self, tt):
        self.tt = tt
        SERVE.mkdir(parents=True, exist_ok=True)
        hw_path, fd_path, dp_path = SERVE / "headways.parquet", SERVE / "feeders.json", SERVE / "departures.parquet"
        days = C.TRAIN_DAYS + C.TEST_DAYS
        if not hw_path.exists():
            headway_samples(days).to_parquet(hw_path, index=False)
        if not fd_path.exists():
            fd, stats = chaining(days, tt)
            fd_path.write_text(json.dumps({"feeders": fd, "stats": stats}, ensure_ascii=False), encoding="utf-8")
        if not dp_path.exists():
            actual_departures(days).to_parquet(dp_path, index=False)
        self.deps: dict = {}
        for (r, d), x in pd.read_parquet(dp_path).groupby(["route_id", "date"]):
            dd = pd.Timestamp(d).date()
            self.deps.setdefault((r, C.day_type(dd)), []).append(np.sort(x.sec.to_numpy()))
        self.res = Residual(pd.read_parquet(hw_path))
        self.feeders = json.loads(fd_path.read_text(encoding="utf-8"))["feeders"]

    def chain_wait(self, rid: str, i: int, now: datetime, by_route: dict):
        """折り返してくるバスの到着までの秒数（最も早いもの）。無ければ None。"""
        best = None
        for a, lay, _share in self.feeders.get(rid, []):
            veh = by_route.get(str(a))
            if not veh or a not in self.tt.cum:
                continue
            xy_a = self.tt.pat[a][["stop_lat", "stop_lon"]].to_numpy()
            end = len(xy_a) - 1
            for lat, lng, ts in veh:
                d = C.dist_m(lat, lng, xy_a[:, 0], xy_a[:, 1])
                k = int(np.argmin(d))
                if d[k] > 300:
                    continue
                t_k = datetime.fromtimestamp(ts, IST).replace(tzinfo=None)
                if (now - t_k).total_seconds() > 600:
                    continue
                t_end = t_k + timedelta(seconds=self.tt.ride_sec(a, k, end, t_k))
                t_start = t_end + timedelta(seconds=lay)
                t_i = t_start + timedelta(seconds=self.tt.ride_sec(rid, 0, i, t_start))
                w = (t_i - now).total_seconds()
                if w >= -60 and (best is None or w < best):
                    best = max(w, 0.0)
        return best

    def conditional_wait(self, rid: str, i: int, now: datetime, live_links):
        """最後のバスが停留所 i を通ってからの経過時間で条件づけた残りの待ち時間。分からなければ None。"""
        if live_links is None:
            return None, None
        now_ep = pd.Timestamp(now, tz=C.TZ).timestamp()
        lp = live_links.last_pass(rid, i, self.tt.cum[rid], now_ep)
        if lp is None:
            return None, None
        e = now_ep - lp
        if e >= 4 * 3600:
            return None, e
        return self.res(rid, C.day_type(now.date()), now.hour, e), e

    def departure_wait(self, rid: str, i: int, now: datetime):
        """実際の発車の時刻表による待ち時間（秒）: 次の発車までの時間の中央値（日ごと）＋ 始発から停留所 i まで。無ければ None。"""
        sec = now.hour * 3600 + now.minute * 60 + now.second
        gaps = []
        for x in self.deps.get((rid, C.day_type(now.date())), []):
            nxt = x[x >= sec]
            if len(nxt) and nxt[0] - sec <= 4 * 3600:
                gaps.append(nxt[0] - sec)
        if len(gaps) < 3 or rid not in self.tt.cum:
            return None
        g = float(np.median(gaps))
        return g + self.tt.ride_sec(rid, 0, i, now + timedelta(seconds=g))

    def wait(self, rid: str, i: int, now: datetime, upstream_wait, by_route: dict, live_links):
        """(待ち秒, 出どころの説明)"""
        if upstream_wait is not None:
            return upstream_wait, "リアルタイム（手前を走るバス）"
        cond, e = self.conditional_wait(rid, i, now, live_links)
        chain = self.chain_wait(rid, i, now, by_route)
        dep = self.departure_wait(rid, i, now)
        base = cond if cond is not None else self.tt.wait_sec(rid, now)
        if chain is not None:
            if dep is not None:
                return (chain + base + dep) / 3, "折り返してくるバス＋前のバスからの経過＋実際の発車の時刻表"
            return 0.5 * chain + 0.5 * base, "折り返してくるバス＋前のバスからの経過"
        if dep is not None:
            return dep, "次のバスは始発を出る前（実際の発車の時刻表）"
        if cond is not None:
            return cond, f"前のバスが {e / 60:.0f} 分前に通過"
        return None, None
