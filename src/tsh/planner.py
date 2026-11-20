"""経路検索（問題1と問題2をつなぐ部分）。

出発地・目的地の座標と出発時刻から、徒歩 → バス → (乗り換え1回まで) → 徒歩 の候補を探し、
各候補に「所要時間（観測 GPS のモデル）」と「区間ごとの混雑度（乗車券のモデル）」を付けて返す。

探索の流れ:
  1. 出発地・目的地から徒歩 800m 以内の停留所を集める（直線距離 × 1.3 を歩く距離とし、時速 4.5km）。
  2. 直通: 出発側の停留所と目的側の停留所を同じ路線（同じ向き）で結べる組み合わせ。
  3. 乗り換え1回: 1本目の路線の下流の停留所から、250m 以内で2本目の路線に乗り換えて目的側へ。
  4. まず距離ベースの概算で候補を絞り、上位をモデル（時間帯別の区間所要時間・待ち時間）で計算し直す。
  5. 混雑度は、各乗車区間で最も混む区間のレベル（座れる / 立つ / 混雑）と信頼度を付ける。
  6. 並べ方: fastest（合計時間）/ comfort（混雑で重みづけした体感時間）/ fewer_transfers（乗り換えが少ない順）。
     到着時刻を指定する検索は plan_arrive（docs 16.9）。
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
# 到着時刻を指定したとき、過去の日の何割で間に合う出発を出すか（余裕を見た到着の 85% 点と同じ。docs 16.9）
ARRIVE_Q = 0.85
# 到着時刻の指定で、q の日で間に合う出発からさらに早める分（乗り換えの回数ごと、分。docs 17章）。過去の日だけで決めた出発は、
# 較正の週（部品は 10/1〜17、測るのは 10/18〜24）で 77.9% しか間に合わなかった（過去の日で最も厳しい日に合わせても 82.4%）。
# 早める分を 0〜30 分で変えて測り、85% に届いた最小の値: 直通 2 分（85.3%）、乗り換えあり 16 分（85.0%）
ARRIVE_MARGIN_MIN = {0: 2, 1: 16}


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
    def _candidates(self, o_lat, o_lng, d_lat, d_lng):
        """候補の構造を最大 40 案、距離ベースの概算（秒）と一緒に返す: [(概算秒, 構造), ...]（概算の短い順）。"""
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
            cand.append((est, st))
            if len(cand) >= 40:
                break
        return cand, len(O), len(D)

    def plan(self, o_lat, o_lng, d_lat, d_lng, depart: datetime, sort: str = "fastest",
             max_options: int = 3, live_wait=None, live_links=None) -> dict:
        self._live_links = live_links
        cand, nO, nD = self._candidates(o_lat, o_lng, d_lat, d_lng)
        opts = [self._evaluate(st, depart, live_wait) for _, st in cand]
        if getattr(self, "plan_replay", False) and getattr(self, "plan_wait", None) is not None:
            for o in opts:
                self._replay(o, depart)
        # 「今すぐ出る」で 1 本目の待ちがリアルタイムの案は、合計時間（順位にも使う）と余裕を見た到着を、
        # 学習期間で集めた待ちの外れ方を入れた分布から出す（16.6・16.7）
        if getattr(self, "live_excess", None) is not None:
            for o in opts:
                self._live_dist(o, depart)
        # 乗り換え案のうち、2本目の路線に出発地から直接乗れて、しかも5分以上は速くならないものは捨てる。
        # 比べる直通は後ろへ回していないものだけ（16.9: 出発の停留所で通過の記録が無い直通 425UP が、
        # 425UP に乗り換える案を全部捨てさせ、243 分の案が 1 位になっていた）
        direct = {o["legs"][1]["route_id"]: o["total_min"] for o in opts
                  if o["transfers"] == 0 and not o.get("unreliable", False)}
        opts = [o for o in opts if o["transfers"] == 0
                or o["legs"][3]["route_id"] not in direct
                or o["total_min"] < direct[o["legs"][3]["route_id"]] - 5]
        key = {"fastest": lambda o: o["total_min"], "comfort": lambda o: o["perceived_min"],
               # 乗り換えが少ない順（Google の「乗り換えが少ない」に当たる）: 直通を先に、同じ回数の中は合計時間の順
               "fewer_transfers": lambda o: (o["transfers"], o["total_min"])}[sort]
        # 過去の半分以上の日でこの時刻にバスが来ていない案は後ろへ（_replay）
        opts.sort(key=lambda o: (o.get("unreliable", False), key(o)))
        if not getattr(self, "keep_tot", False):
            for o in opts:
                o.pop("_tot", None)
        return {
            "from": {"lat": o_lat, "lng": o_lng, "near_stops": nO},
            "to": {"lat": d_lat, "lng": d_lng, "near_stops": nD},
            "depart": depart.isoformat(), "day_type": C.day_type(depart.date()), "sort": sort,
            "options": opts[:max_options],
        }

    def plan_arrive(self, o_lat, o_lng, d_lat, d_lng, arrive_by: datetime, sort: str = "fastest",
                    max_options: int = 3, q: float = ARRIVE_Q) -> dict:
        """到着時刻を指定する検索（Google の「到着時刻」に当たる。docs 16.9）。前もって計画する場合だけで、リアルタイムは使わない。

        Google は時刻表で出発を決める（ヘルプ「交通機関の時刻表に基づく」）。デリーの時刻表は実際の運行と合わない（14 章）
        ので、各候補について過去の同じ平日/休日の日ごとに「arrive_by までに着ける最も遅い出発」を求め
        （PassageTimetable.latest_departures）、q（既定 85%）以上の日で間に合う最も遅い出発を「出発」にする。
        q の日で間に合わない案は、半分の日で間に合う出発を出して後ろへ回す。半分の日でも間に合わない案は最後。
        乗車時間は区間モデルの中央値。概算の出発で計算した後、上位の案は求めた出発の時刻で 2 回計算し直す。
        並べ方: fastest は出発が遅い順（＝所要時間が短い）、comfort は体感時間、fewer_transfers は乗り換えが少ない順。"""
        cand, nO, nD = self._candidates(o_lat, o_lng, d_lat, d_lng)
        res = {"from": {"lat": o_lat, "lng": o_lng, "near_stops": nO},
               "to": {"lat": d_lat, "lng": d_lng, "near_stops": nD},
               "arrive_by": arrive_by.isoformat(), "day_type": C.day_type(arrive_by.date()), "sort": sort,
               "on_time_target": q, "options": []}
        pt = getattr(self, "plan_wait", None)
        if pt is None:
            res["error"] = "実際の通過の時刻表が読み込まれていないので、到着時刻の指定は使えない"
            return res
        self._live_links = None
        scored = []
        for est, st in cand:
            o = self._evaluate(st, arrive_by - timedelta(seconds=est))
            self._arrive_fit(o, arrive_by, q, pt)
            scored.append((est, st, o))
        scored.sort(key=lambda x: self._arrive_key(x[2], "fastest"))
        opts = []
        for est, st, o in scored[:max(2 * max_options, 6)]:
            # 求めた出発の時刻で、待ち・乗車時間（時間帯で変わる）・混雑を計算し直し、出発を求め直す
            for _ in range(2):
                if o["_dep_dt"] is None:
                    break
                o = self._evaluate(st, o["_dep_dt"])
                self._arrive_fit(o, arrive_by, q, pt)
            if o["_dep_dt"] is not None:
                self._replay(o, o["_dep_dt"])
                o["arrive_safe"] = None   # 到着時刻を指定したときは、出発の側で余裕を見ている
                o.pop("unreliable", None)
                o["total_source"] = (f"過去の同じ種類の日 {o['replay_days']} 日のうち {q * 100:.0f}% で "
                                     f"{arrive_by:%H:%M} までに着けた最も遅い出発から、さらに "
                                     f"{getattr(self, 'arrive_margin_min', ARRIVE_MARGIN_MIN)[min(o['transfers'], 1)]} 分早めた出発"
                                     f"（較正の週で 85% 間に合うように決めた余裕）。所要時間と到着はその出発での中央値")
            if o["_tier"] > 0:
                o["unreliable"] = True
                o["total_source"] = (f"過去の同じ種類の日 {o['replay_days']} 日のうち、{arrive_by:%H:%M} までに着けたのは "
                                     + ("半分ほど。余裕を見た出発は出せない" if o["_tier"] == 1 else "半分未満"))
            opts.append(o)
        # 乗り換えの案のうち、2 本目の路線に出発地から直接乗れて、しかも 5 分以上は遅く出られないものは捨てる
        direct = {o["legs"][1]["route_id"]: o["_dep_s"] for o in opts if o["transfers"] == 0 and o["_tier"] == 0}
        opts = [o for o in opts if o["transfers"] == 0 or o["_tier"] > 0
                or o["legs"][3]["route_id"] not in direct or o["_dep_s"] >= direct[o["legs"][3]["route_id"]] + 300]
        opts.sort(key=lambda o: self._arrive_key(o, sort))
        for o in opts:
            for k in ("_dep_dt", "_dep_s", "_dep50_s", "_tier", "_tot"):
                o.pop(k, None)
        res["options"] = opts[:max_options]
        return res

    def _arrive_key(self, o: dict, sort: str):
        # arrive_rank="median": 順位は半分の日で間に合う出発で付ける（見せるのは 85% の出発）。85% の出発そのもので
        # 順位を付けると、候補の中で 85% の出発がたまたま遅く出た案を選びやすい（16.2 の最適化の呪いと同じ形）
        dep = o.get("_dep50_s") if getattr(self, "arrive_rank", "q") == "median" else o["_dep_s"]
        late = -dep if dep is not None else 0.0
        if sort == "comfort":
            return (o["_tier"], o["perceived_min"])
        if sort == "fewer_transfers":
            return (o["_tier"], o["transfers"], late)
        return (o["_tier"], late)

    def _arrive_fit(self, o: dict, arrive_by: datetime, q: float, pt) -> None:
        """o（_evaluate の結果）に、arrive_by までに着く出発を付ける（plan_arrive）。
        _tier: 0＝q 以上の日で間に合う出発がある、1＝半分以上の日で間に合う出発だけある、2＝それも無い。"""
        legs, walk_before = [], 0.0
        for l in o["legs"]:
            if l["mode"] == "walk":
                walk_before = l["minutes"] * 60
                continue
            legs.append((l["route_id"], l["board"]["seq"], walk_before, l["ride_min"] * 60))
        d = pt.latest_departures(legs, arrive_by, o["legs"][-1]["minutes"] * 60)
        o["_dep_dt"] = o["_dep_s"] = None
        o["_tier"] = 2
        o["depart"] = o["depart_median"] = None
        if d is None:
            o["replay_days"], o["on_time_share"] = 0, None
            return
        day0 = datetime(arrive_by.year, arrive_by.month, arrive_by.day)
        o["replay_days"] = int(len(d))

        def latest_ok(share):
            s = np.sort(d)
            v = s[len(s) - int(np.ceil(share * len(s) - 1e-9))]
            return float(np.floor(v / 60) * 60) if np.isfinite(v) else None   # 分に切り下げ（早めに出る側）

        if getattr(self, "arrive_ride_sd", False):
            # 乗車時間のばらつき: 各区間の (85% 点 − 中央値) を二乗和の平方根で合わせ、標準正規の 21 点だけ出発をずらす
            # （_live_dist と同じ）。日ごとの出発 × 21 通りを同じ重みで合わせる
            from statistics import NormalDist
            sd = np.sqrt(sum(((l["ride_min_p85"] - l["ride_min"]) * 60) ** 2
                             for l in o["legs"] if l["mode"] == "bus" and l.get("ride_min_p85"))) / 1.0364
            if sd > 0:
                z = np.array([NormalDist().inv_cdf((k + 0.5) / 21) for k in range(21)])
                d = (d[:, None] - sd * z[None, :]).ravel()
        d85, d50 = latest_ok(q), latest_ok(0.5)
        o["_dep50_s"] = d50
        if d50 is not None:
            o["depart_median"] = (day0 + timedelta(seconds=d50)).strftime("%H:%M")
        use = d85 if d85 is not None else d50
        if use is None:
            o["on_time_share"] = round(float(np.isfinite(d).mean()), 2)
            return
        o["_tier"] = 0 if d85 is not None else 1
        if d85 is not None:
            use = d85 - getattr(self, "arrive_margin_min", ARRIVE_MARGIN_MIN)[min(o["transfers"], 1)] * 60
        o["_dep_s"] = use
        o["_dep_dt"] = day0 + timedelta(seconds=use)
        o["depart"] = o["_dep_dt"].strftime("%H:%M")
        o["on_time_share"] = round(float((d >= use).mean()), 2)

    def _replay(self, o: dict, depart: datetime) -> None:
        """前もって計画するとき（最初の待ちがリアルタイムでないとき）、合計時間を「過去の同じ種類の日に同じ時刻に
        出ていたら」の再現の中央値に置き換える（tsh.waitmodel.PassageTimetable.journey、docs 16章）。
        区間ごとの予測の和は、めったに走らない路線の待ちを短く見積もり、その案が 1 位に選ばれやすかった。
        過去の半分以上の日に着けない案は unreliable として後ろへ回す。"""
        bus = [l for l in o["legs"] if l["mode"] == "bus"]
        legs, walk_before = [], 0.0
        for l in o["legs"]:
            if l["mode"] == "walk":
                walk_before = l["minutes"] * 60
                continue
            legs.append((l["route_id"], l["board"]["seq"], walk_before, l["ride_min"] * 60))
        walk_last = o["legs"][-1]["minutes"] * 60
        offset = 0.0
        # 「次のバスは始発を出る前（実際の発車の時刻表）」はバスが見えないときの過去の記録なので、過去の待ちと同じに扱う
        # （発車の無かった日を捨てた中央値なので、めったに走らない路線を選びやすかった。16.5）
        if bus[0]["wait_source"] not in ("過去の実績", "過去の実際の通過の時刻表",
                                         "次のバスは始発を出る前（実際の発車の時刻表）"):
            # 1 本目の待ちはリアルタイム（手前のバス・折り返し・経過など）。乗り換えから先だけを過去の日ごとに再現する（16.5）
            if len(legs) < 2:
                return
            w0, wait0, ride0 = legs[0][2], bus[0]["wait_min"] * 60, legs[0][3]
            offset = w0 + wait0 + ride0
            legs = legs[1:]
        r = self.plan_wait.journey(legs, depart + timedelta(seconds=offset), walk_last)
        if r is None:
            return
        med, q85 = offset + r["median_s"], offset + r["q85_s"]
        cal = getattr(self, "plan_calib", None)
        if offset == 0:
            o["_tot"] = r["tot"]       # 較正の週で外れ方を集めるとき用（tsh.validate_journeys。API には返さない）
            if cal is not None and np.isfinite(med):
                # 選ぶことによる偏りの較正（docs 17章、tsh.plan_calib）: 再現の分布のうち、較正の週に実際の所要時間の
                # 50%・85% が入った位置を、合計時間（順位にも使う）と余裕を見た到着に使う。乗り換えの回数ごと
                lv = cal["levels"].get(str(min(o["transfers"], 1)), cal["levels"]["all"])
                m2 = float(np.quantile(r["tot"], min(lv["p50"], 1.0), method="inverted_cdf"))
                med = m2 if np.isfinite(m2) else med
                q85 = float(np.quantile(r["tot"], min(lv["p85"], 1.0), method="inverted_cdf"))
        o["total_min_sum"] = o["total_min"]
        o["served_share"] = round(r["served"], 2)
        o["replay_days"] = r["days"]
        if np.isfinite(med):
            o["total_min"] = round(med / 60, 1)
            o["arrive"] = (depart + timedelta(seconds=med)).strftime("%H:%M")
            o["total_source"] = (f"{'1 本目はリアルタイム、乗り換えから先は' if offset else ''}"
                                 f"過去の同じ種類の日 {r['days']} 日の再現の中央値（着けた日 {r['served'] * 100:.0f}%）")
            if offset == 0 and cal is not None:
                o["total_source"] = (f"過去の同じ種類の日 {r['days']} 日の再現（着けた日 {r['served'] * 100:.0f}%）を、"
                                     "学習期間の中の較正の週で実際の所要時間と合うように読み替えた値")
            # 余裕を見た到着: 同じ再現の 85% 点（待ちのばらつきも含む）。15% より多い日に着けなければ出さない
            o["arrive_safe"] = ((depart + timedelta(seconds=q85)).strftime("%H:%M")
                                if np.isfinite(q85) else None)
        else:
            o["unreliable"] = True
            o["total_source"] = (f"区間の予測の和。過去の同じ種類の日 {r['days']} 日のうち、この時刻に乗って着けたのは "
                                 f"{r['served'] * 100:.0f}% だけ")

    def _live_dist(self, o: dict, depart: datetime) -> None:
        """1 本目の待ちがリアルタイムのときの合計時間（中央値）と余裕を見た到着（85% 点）（docs 16.6・16.7）。

        リアルタイムの待ちは点の予測で、実際には「見えていたバスに数十秒の差で乗り遅れる」「そのバスが手前で折り返す・
        GPS が途切れる」ことがある（学習期間の中の較正の週で、2 分以内と出た待ちの 25% が 10 分以上長かった）。
        そこで学習期間で集めた「実際 − 予測」の分位点 40 個（tsh.live_excess）で待ちを 40 通りにし、直通はそれぞれの到着、
        乗り換えの案は乗り換えの停留所に着く時刻から過去の日ごとに再現し直した到着を出して、全部を同じ重みで合わせる。
        乗車時間のばらつき（区間モデルの 85% 点を正規分布の形で）も足す。その中央値を合計時間（順位にも使う）、
        85% 点を余裕を見た到着にする。半分以上の場合に着けなければ unreliable（後ろへ）。分布が無ければ何もしない。"""
        from statistics import NormalDist

        from .live_excess import samples_for
        bus = [l for l in o["legs"] if l["mode"] == "bus"]
        E = samples_for(getattr(self, "live_excess", None), bus[0]["wait_source"], bus[0]["wait_min"] * 60)
        if E is None or (len(bus) > 1 and getattr(self, "plan_wait", None) is None):
            return
        legs, walk_before = [], 0.0
        for l in o["legs"]:
            if l["mode"] == "walk":
                walk_before = l["minutes"] * 60
                continue
            legs.append((l["route_id"], l["board"]["seq"], walk_before, l["ride_min"] * 60))
        walk_last = o["legs"][-1]["minutes"] * 60
        w0, wait0 = o["legs"][0]["minutes"] * 60, bus[0]["wait_min"] * 60
        ride0 = bus[0]["ride_min"] * 60
        waits = np.maximum(wait0 + E, 0.0)
        if len(bus) == 1:
            tot = w0 + waits + ride0 + walk_last
        else:
            m = self.plan_wait.journey_many(legs[1:], depart, w0 + waits + ride0, walk_last)
            if m is None:
                return
            tot = m.ravel()       # [待ちの 40 通り × 日]。どの通りも日数は同じなので、1 通りの重みは同じ
        # 乗車時間のばらつき: 各区間の (85% 点 − 中央値) を二乗和の平方根で合わせ、標準正規の 21 点に掛ける
        sd = np.sqrt(sum(((l["ride_min_p85"] - l["ride_min"]) * 60) ** 2 for l in bus if l.get("ride_min_p85"))) / 1.0364
        z = np.array([NormalDist().inv_cdf((k + 0.5) / 21) for k in range(21)]) if sd > 0 else np.zeros(1)
        allv = (np.asarray(tot, float)[:, None] + sd * z[None, :]).ravel()
        med = float(np.quantile(allv, 0.5, method="inverted_cdf"))
        q85 = float(np.quantile(allv, 0.85, method="higher"))
        late = float(np.mean(E > 600))
        o["total_min_point"] = o["total_min"]
        o["wait0_late10_share"] = round(late, 2)
        rest = "、乗り換えから先は過去の同じ種類の日の再現" if len(bus) > 1 else ""
        if np.isfinite(med):
            o["perceived_min"] = round(o["perceived_min"] + (med / 60 - o["total_min"]) * 1.5, 1)
            o["total_min"] = round(med / 60, 1)
            o["arrive"] = (depart + timedelta(seconds=med)).strftime("%H:%M")
            o["total_source"] = (f"1 本目はリアルタイム（同じような予測は、学習期間に {late * 100:.0f}% の場面で "
                                 f"10 分以上長く待った）{rest}。それを合わせた中央値")
        else:
            o["unreliable"] = True
            o["total_source"] = ("1 本目はリアルタイムだが、同じような予測は学習期間に半分以上の場面で、"
                                 "3 時間以内にバスが来なかったか乗り換えから先で着けなかった")
        if np.isfinite(q85):
            o["arrive_safe"] = (depart + timedelta(seconds=q85)).strftime("%H:%M")
            o["safe_source"] = "見えていたバスに乗れない場合も含めた 85% 点（学習期間のリアルタイムの外れ方から）"
        else:
            o["arrive_safe"] = None
            o["safe_source"] = ("見えていたバスに乗れない場合や、乗り換えから先で過去の日にバスが来なかった場合を合わせると、"
                                "着けない見込みが 15% を超えるので、余裕を見た到着は出さない")

    def _evaluate(self, st, depart: datetime, live_wait=None) -> dict:
        legs, t = [], depart
        dtp = C.day_type(depart.date())
        walk_ms = [x for x in st if not isinstance(x, tuple)]
        buses = [x for x in st if isinstance(x, tuple)]
        total_wait = total_ride = total_walk = perceived = buffer_s = 0.0
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
                lw = live_wait(rid, i, t)
                if isinstance(lw, tuple):
                    wait, src = lw
                elif lw is not None:
                    wait, src = lw, "リアルタイム"
            if wait is None and getattr(self, "plan_wait", None) is not None:
                wait = self.plan_wait.wait(rid, i, t)      # 実際の通過の時刻表（tsh.waitmodel.PassageTimetable）
                if wait is not None:
                    src = "過去の実際の通過の時刻表"
            if wait is None:
                wait = self.tt.wait_sec(rid, t)
            t_board = t + timedelta(seconds=wait)
            ll = getattr(self, "_live_links", None)
            now = datetime.now(IST).replace(tzinfo=None)
            # 直近の実績を使うのは、乗車が今から 30 分以内のとき（それより先は過去の実績だけ）
            near_now = -15 * 60 <= (t_board - now).total_seconds() <= 30 * 60
            seg = getattr(self, "seg", None)
            corr, corr_n = 1.0, 0
            if seg is not None:
                # 乗る区間全体の LightGBM（中央値と 85% 点）。直近の実績が使えるときは「直近あり」のモデル
                raw = ll.raw if (ll is not None and near_now) else None
                if raw is not None:
                    ll.refresh()
                    raw = ll.raw
                pr = seg.predict(rid, i, j, t_board, raw, pd.Timestamp(now, tz=C.TZ).timestamp() if near_now else None)
                ride, ride_p85, ride_model = pr["median_s"], pr["q85_s"], f"区間モデル（{pr['mode']}）"
                corr_n = pr["recent_obs"]
                quiet = seg.predict(rid, i, j, t_board.replace(hour=14, minute=0))["median_s"]
            else:
                ride = self.tt.ride_sec(rid, i, j, t_board)
                # 直前のバスによる補正（記録した GTFS-RT の直近 30 分の実績）。出発が今から 15 分以内のときだけ
                if ll is not None and near_now:
                    corr, corr_n = ll.factor(rid, i, j, pd.Timestamp(now, tz=C.TZ).timestamp())
                    ride *= corr
                ride_p85, ride_model = None, "区間ごとの中央値の合計"
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
                "ride_min_p85": round(ride_p85 / 60, 1) if ride_p85 else None,
                "ride_model": ride_model,
                "ride_live_factor": round(corr, 3), "ride_live_obs": corr_n,
                "ride_min_at_14h": round(quiet / 60, 1),
                "ride_min_timetable": round(sched / 60, 1) if sched else None,
                "board_time": t_board.strftime("%H:%M"),
                "crowding": crowd,
                "path": self.seq_xy[rid][i:j + 1].round(6).tolist(),
            })
            total_wait += wait; total_ride += ride
            buffer_s += (ride_p85 - ride) if ride_p85 else 0.0
            if "prob" in crowd:   # 混雑の確率があれば、重みの期待値（座れる 1.0 / 立つ 1.5 / 混雑 2.3）を使う
                w_crowd = sum(p * CROWD_WEIGHT[k] for k, p in crowd["prob"].items())
            else:
                w_crowd = CROWD_WEIGHT.get(crowd["level"], 1.2)
            perceived += wait * 1.5 + ride * w_crowd
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
            # 余裕を見た到着（乗車時間を 85% 点で見た場合。待ち時間のばらつきは含まない）
            "arrive_safe": (t + timedelta(seconds=buffer_s)).strftime("%H:%M") if buffer_s else None,
            "walk_min": round(total_walk / 60, 1), "wait_min": round(total_wait / 60, 1),
            "ride_min": round(total_ride / 60, 1), "transfers": len(buses) - 1,
            "crowding_worst": worst, "perceived_min": round(perceived / 60, 1),
            "legs": legs,
        }
