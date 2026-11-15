"""経路検索（問題1と問題2をつなぐ部分）。

出発地・目的地の座標と出発時刻から、徒歩 → バス → (乗り換え1回まで) → 徒歩 の候補を探し、
各候補に「所要時間（観測 GPS のモデル）」と「区間ごとの混雑度（乗車券のモデル）」を付けて返す。

探索の流れ:
  1. 出発地・目的地から徒歩 800m 以内の停留所を集める（直線距離 × 1.3 を歩く距離とし、時速 4.5km）。
  2. 直通: 出発側の停留所と目的側の停留所を同じ路線（同じ向き）で結べる組み合わせ。
  3. 乗り換え1回: 1本目の路線の下流の停留所から、250m 以内で2本目の路線に乗り換えて目的側へ。
  4. まず距離ベースの概算で候補を絞り、上位をモデル（時間帯別の区間所要時間・待ち時間）で計算し直す。
  5. 混雑度は、各乗車区間で最も混む区間のレベル（座れる / 立つ / 混雑）と信頼度を付ける。
  6. 並べ方: fastest（合計時間）/ comfort（混雑で重みづけした体感時間）。
     体感時間の重み（乗車時間に掛ける）: 座れる 1.0 / 立つ 1.5 / 混雑 2.3
     （英国の研究のメタ分析で、立って乗る時間は座る時間の約2倍に感じるとされる値を参考にした）
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import common as C
from .crowding import CrowdingModel
from .traveltime import TravelTimeModel

IST = timezone(timedelta(hours=5, minutes=30))
WALK_MPS = 4.5 / 3.6
DETOUR = 1.3
ACCESS_M = 800
TRANSFER_M = 250
TRANSFER_PENALTY_S = 120   # 乗り換え1回の負担（乗り継ぎの不確実さ）
CROWD_WEIGHT = {"座れる": 1.0, "立つ": 1.5, "混雑": 2.3, "不明": 1.2}


@dataclass
class Option:
    legs: list = field(default_factory=list)
    total_s: float = 0.0
    perceived_s: float = 0.0


class Planner:
    def __init__(self, tag: str = "all"):
        self.tt = TravelTimeModel(tag)
        self.cr = CrowdingModel(tag)
        p = C.patterns()
        self.pat = p
        self.route_name = dict(zip(p.route_id, p.route_short_name))
        self.route_desc = dict(zip(p.route_id, p.route_desc))
        st = C.stops()
        self.stop_ids = st.stop_id.to_numpy()
        self.stop_xy = st[["stop_lat", "stop_lon"]].to_numpy()
        self.stop_name = dict(zip(st.stop_id, st.stop_name))
        self.stop_pos = {s: i for i, s in enumerate(self.stop_ids)}
        self.serving = defaultdict(list)            # stop_id -> [(route_id, seq)]
        for r in p.itertuples():
            self.serving[r.stop_id].append((r.route_id, r.seq))
        self.seq_stop = {rid: g.stop_id.tolist() for rid, g in p.groupby("route_id")}
        self.seq_xy = {rid: g[["stop_lat", "stop_lon"]].to_numpy() for rid, g in p.groupby("route_id")}
        self._neighbors()

    def _neighbors(self) -> None:
        xy = self.stop_xy
        self.nbr = {}
        for k in range(len(xy)):
            d = C.dist_m(xy[k, 0], xy[k, 1], xy[:, 0], xy[:, 1])
            idx = np.where(d <= TRANSFER_M)[0]
            self.nbr[self.stop_ids[k]] = [(self.stop_ids[i], float(d[i])) for i in idx]

    def near_stops(self, lat: float, lng: float, radius: float = ACCESS_M):
        d = C.dist_m(lat, lng, self.stop_xy[:, 0], self.stop_xy[:, 1])
        idx = np.argsort(d)
        out = [(self.stop_ids[i], float(d[i])) for i in idx if d[i] <= radius][:25]
        if not out:   # 近くに無ければ最寄り3つ
            out = [(self.stop_ids[i], float(d[i])) for i in idx[:3]]
        return out

    @staticmethod
    def walk_s(m: float) -> float:
        return m * DETOUR / WALK_MPS

    # ------------------------------------------------------------------
    def plan(self, o_lat, o_lng, d_lat, d_lng, depart: datetime, sort: str = "fastest",
             max_options: int = 3, live_wait=None, live_links=None) -> dict:
        self._live_links = live_links
        O = self.near_stops(o_lat, o_lng)
        D = self.near_stops(d_lat, d_lng)
        Dmap = defaultdict(list)          # route_id -> [(j, stop, walk_m)]
        for s, wm in D:
            for rid, j in self.serving[s]:
                Dmap[rid].append((j, s, wm))
        rough = []                        # (概算秒, 構造)

        def cum(rid, a, b):
            c = self.tt.cum[rid]
            return c[b] - c[a]

        # 直通
        for s, wm in O:
            for rid, i in self.serving[s]:
                for j, ds, dm in Dmap.get(rid, []):
                    if j > i:
                        est = self.walk_s(wm) + cum(rid, i, j) / 4.5 + self.walk_s(dm) + 600
                        rough.append((est, (("bus", rid, i, j, s, ds), wm, dm)))
        # 乗り換え1回: 目的地へ行ける (路線2, 乗車 seq m) を停留所ごとに索引
        reach = defaultdict(list)          # stop -> [(rid2, m, j, ds, dm)]
        for rid2, lst in Dmap.items():
            stops2 = self.seq_stop[rid2]
            for j, ds, dm in lst:
                for m in range(max(0, j - 60), j):
                    reach[stops2[m]].append((rid2, m, j, ds, dm))
        best_pair = {}
        for s, wm in O:
            for rid1, i in self.serving[s]:
                stops1 = self.seq_stop[rid1]
                for k in range(i + 1, min(len(stops1), i + 61)):
                    s1 = stops1[k]
                    for s2, tm in self.nbr.get(s1, []):
                        for rid2, m, j, ds, dm in reach.get(s2, []):
                            if rid2 == rid1:
                                continue
                            est = (self.walk_s(wm) + cum(rid1, i, k) / 4.5 + self.walk_s(tm)
                                   + cum(rid2, m, j) / 4.5 + self.walk_s(dm) + 1200 + TRANSFER_PENALTY_S)
                            key = (rid1, rid2)
                            if key not in best_pair or est < best_pair[key][0]:
                                best_pair[key] = (est, (("bus", rid1, i, k, s, s1), ("bus", rid2, m, j, s2, ds), wm, tm, dm))
        rough += list(best_pair.values())
        rough.sort(key=lambda x: x[0])
        # 同じ路線の組み合わせは1つに（直通は路線ごとに最良）
        seen, cand = set(), []
        for est, st in rough:
            routes = tuple(x[1] for x in st if isinstance(x, tuple))
            if routes in seen:
                continue
            seen.add(routes)
            cand.append(st)
            if len(cand) >= 40:
                break
        opts = [self._evaluate(st, depart, live_wait) for st in cand]
        # 乗り換え案のうち、2本目の路線に出発地から直接乗れて、しかも5分以上は速くならないものは捨てる
        direct = {o["legs"][1]["route_id"]: o["total_min"] for o in opts if o["transfers"] == 0}
        opts = [o for o in opts if o["transfers"] == 0
                or o["legs"][3]["route_id"] not in direct
                or o["total_min"] < direct[o["legs"][3]["route_id"]] - 5]
        key = (lambda o: o["total_min"]) if sort == "fastest" else (lambda o: o["perceived_min"])
        opts.sort(key=key)
        return {
            "from": {"lat": o_lat, "lng": o_lng, "near_stops": len(O)},
            "to": {"lat": d_lat, "lng": d_lng, "near_stops": len(D)},
            "depart": depart.isoformat(), "day_type": C.day_type(depart.date()), "sort": sort,
            "options": opts[:max_options],
        }

    def _evaluate(self, st, depart: datetime, live_wait=None) -> dict:
        legs, t = [], depart
        dtp = C.day_type(depart.date())
        walk_ms = [x for x in st if not isinstance(x, tuple)]
        buses = [x for x in st if isinstance(x, tuple)]
        total_wait = total_ride = total_walk = perceived = 0.0
        # 最初の徒歩
        w0 = self.walk_s(walk_ms[0])
        legs.append({"mode": "walk", "to_stop": self.stop_name.get(buses[0][4]), "minutes": round(w0 / 60, 1),
                     "meters": round(walk_ms[0])})
        t += timedelta(seconds=w0); total_walk += w0
        for n, (_, rid, i, j, s_on, s_off) in enumerate(buses):
            if n == 1:   # 乗り換えの徒歩
                tw = self.walk_s(walk_ms[1])
                legs.append({"mode": "walk", "to_stop": self.stop_name.get(s_on), "minutes": round(tw / 60, 1),
                             "meters": round(walk_ms[1]), "transfer": True})
                t += timedelta(seconds=tw); total_walk += tw
            wait = None
            src = "過去の実績"
            if n == 0 and live_wait is not None:
                wait = live_wait(rid, i, t)
                if wait is not None:
                    src = "リアルタイム"
            if wait is None:
                wait = self.tt.wait_sec(rid, t)
            t_board = t + timedelta(seconds=wait)
            ride = self.tt.ride_sec(rid, i, j, t_board)
            # 直前のバスによる補正（記録した GTFS-RT の直近 30 分の実績）。出発が今から 15 分以内のときだけ
            corr, corr_n = 1.0, 0
            ll = getattr(self, "_live_links", None)
            if ll is not None:
                now = datetime.now(IST).replace(tzinfo=None)
                if abs((t_board - now).total_seconds()) <= 15 * 60:
                    corr, corr_n = ll.factor(rid, i, j, pd.Timestamp(now, tz=C.TZ).timestamp())
                    ride *= corr
            quiet = self.tt.ride_sec(rid, i, j, t_board.replace(hour=14, minute=0))
            sched = self.tt.sched_ride_sec(rid, i, j, t_board)
            crowd = self.cr.leg(rid, i, j, dtp, t_board.hour)
            legs.append({
                "mode": "bus", "route": self.route_name.get(rid), "route_id": rid,
                "headsign": self.route_desc.get(rid),
                "board": {"stop": self.stop_name.get(s_on), "seq": i},
                "alight": {"stop": self.stop_name.get(s_off), "seq": j},
                "stops": j - i,
                "wait_min": round(wait / 60, 1), "wait_source": src,
                "ride_min": round(ride / 60, 1),
                "ride_live_factor": round(corr, 3), "ride_live_obs": corr_n,
                "ride_min_at_14h": round(quiet / 60, 1),
                "ride_min_timetable": round(sched / 60, 1) if sched else None,
                "board_time": t_board.strftime("%H:%M"),
                "crowding": crowd,
                "path": self.seq_xy[rid][i:j + 1].round(6).tolist(),
            })
            total_wait += wait; total_ride += ride
            perceived += wait * 1.5 + ride * CROWD_WEIGHT.get(crowd["level"], 1.2)
            t = t_board + timedelta(seconds=ride)
        wl = self.walk_s(walk_ms[-1])
        legs.append({"mode": "walk", "to": "目的地", "minutes": round(wl / 60, 1), "meters": round(walk_ms[-1])})
        t += timedelta(seconds=wl); total_walk += wl
        total = (t - depart).total_seconds() + (TRANSFER_PENALTY_S if len(buses) > 1 else 0) * 0
        perceived += total_walk * 1.5 + (TRANSFER_PENALTY_S if len(buses) > 1 else 0)
        worst = max((l["crowding"]["level"] for l in legs if l["mode"] == "bus"),
                    key=lambda x: ["座れる", "立つ", "混雑", "不明"].index(x) if x in ["座れる", "立つ", "混雑"] else -1)
        return {
            "total_min": round(total / 60, 1), "arrive": t.strftime("%H:%M"),
            "walk_min": round(total_walk / 60, 1), "wait_min": round(total_wait / 60, 1),
            "ride_min": round(total_ride / 60, 1), "transfers": len(buses) - 1,
            "crowding_worst": worst, "perceived_min": round(perceived / 60, 1),
            "legs": legs,
        }
