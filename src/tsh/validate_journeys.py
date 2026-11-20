"""経路検索全体の検証（経路の再現）。ハッカソンの評価「代表的な出発地・目的地の組で、実際の所要時間と比べる」に合わせる。

方法（Berkeley の SF 研究 Jariyasunant ら 2011 と同じ考え方）:
  1. 3〜15km 離れた停留所の組を 600 組選び、検証週（10/25〜31）の 7〜21 時の出発時刻をランダムに付ける。
  2. 学習期間（10/1〜24）だけで作ったモデルで経路検索する（直近の実績は使わない＝前もって計画する場合）。
  3. 候補の上位 3 案それぞれを、検証週の GPS で「実際に来たバスに乗ったら何時に着いたか」再現する:
     歩いて停留所に着いた時刻以降に、その停留所を通った最初のバスに乗り、同じバスが降車停留所を通った時刻に降りる。
     乗り換えも同様。最初のバスが降車停留所まで GPS で追えないときは、その案は「再現できない」として除く。
  4. 比べるもの:
     - 予測した合計時間（本モデル） vs 再現した実際の合計時間
     - 時刻表で予測した合計時間（同じ案を GTFS の時刻表どおりに走ると仮定） vs 実際
     - 1位に選んだ案が、再現できた案の中で実際に最も速かったか（本モデルの順位 / 時刻表の順位）
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import common as C
from .planner import Planner
from .segmodel import SegModel
from .traveltime import passages_glob
from .validate_p1 import metrics

RNG = np.random.default_rng(2026)
# 「今すぐ出る」の余裕の較正（16.6）: 学習期間の中で、前の 17 日で部品を作り、最後の 7 日（10/18 日〜24 土、検証週と同じ曜日の並び）で測る
FIT_DAYS = C.TRAIN_DAYS[:17]
CAL_DAYS = C.TRAIN_DAYS[17:]


def load_passages(days) -> pd.DataFrame:
    con = C.connect()
    return con.execute(f"""
        SELECT date, vehicle_id, trip_id, CAST(route_id AS VARCHAR) AS route_id, seq,
               timezone('{C.TZ}', ts) AS ts
        FROM read_parquet({passages_glob(days, truth=True)})
    """).df()


# 同じ車両の 1 本の走りが 2 つの便（trip_id）に分かれて記録されたものをつなぐとき、間の時間が
# 「その区間を普通に走る時間（モデルの中央値）」より何秒長くてもよいか（docs 16.8。検証週で 92% の組がこの内）
BRIDGE_MAX_EXTRA_S = 900


def bridge_split_runs(ps: pd.DataFrame, tt, max_extra_s: float = BRIDGE_MAX_EXTRA_S) -> pd.DataFrame:
    """ps（date, vehicle_id, trip_id, route_id, seq, t）に、分かれて記録された便をつないだ走りの番号 run を付ける（docs 16.8）。

    車両ごとに便を時刻順に並べ、隣り合う 2 便 A→B が同じ路線で、B の最初の停留所が A の最後の停留所以降、
    B の最初の通過が A の最後の通過より後、間の時間が普通に走る時間 + max_extra_s 以内なら、同じ走りとみなす。
    GTFS-RT の trip_id が走っている途中で次の便の名前に変わり、その前後の数停留所で通過が検出されないことがある
    （検証週の便の 9%）。つながないと、間の停留所をそのバスが通ったことも、B の区間まで乗れたことも正解に入らない。
    同じ停留所が両方にあるとき（間 0 停留所）は A の通過を残す。"""
    pc = ps.groupby(["date", "vehicle_id", "trip_id"], sort=False).agg(
        route_id=("route_id", "first"), s0=("seq", "min"), s1=("seq", "max"), t0=("t", "min"), t1=("t", "max")).reset_index()
    pc = pc.sort_values(["date", "vehicle_id", "t0"]).reset_index(drop=True)
    prev = pc.groupby(["date", "vehicle_id"]).shift(1)
    cand = (prev.route_id == pc.route_id) & (pc.s0 >= prev.s1) & (pc.t0 > prev.t1)
    link = np.zeros(len(pc), bool)
    ist = timezone(timedelta(hours=5, minutes=30))
    for k in np.flatnonzero(cand.to_numpy()):
        a1, b0 = int(prev.s1.iat[k]), int(pc.s0.iat[k])
        exp = tt.ride_sec(str(pc.route_id.iat[k]), a1, b0,
                          datetime.fromtimestamp(float(prev.t1.iat[k]), ist).replace(tzinfo=None)) if b0 > a1 else 0.0
        link[k] = pc.t0.iat[k] - prev.t1.iat[k] <= exp + max_extra_s
    pc["run"] = np.cumsum(~link)
    out = ps.merge(pc[["date", "vehicle_id", "trip_id", "run"]], on=["date", "vehicle_id", "trip_id"])
    return out.sort_values(["run", "seq", "t"]).drop_duplicates(["run", "seq"], keep="first")


class Replay:
    def __init__(self, ps: pd.DataFrame, cum: dict, tt=None):
        """tt（TravelTimeModel）を渡すと、分かれて記録された便をつないでから正解を作る（docs 16.8）。"""
        ps = ps.copy()
        ps["date"] = pd.to_datetime(ps.date).dt.date
        # ts は IST の時刻（タイムゾーンなし）。出発時刻 t0 は pd.Timestamp(dep, tz=C.TZ).timestamp()（本当の epoch）で
        # 比べるので、こちらも IST として本当の epoch にする（2026-11-18 まではここを UTC とみなしており、
        # 再現が出発の 5.5 時間前の時間帯で行われていた。docs 16章）
        ts = pd.to_datetime(ps.ts)
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize(C.TZ)
        ps["t"] = ts.dt.tz_convert("UTC").dt.tz_localize(None).astype("datetime64[ns]").astype("int64") / 1e9
        if tt is not None:
            n0 = ps.groupby(["date", "vehicle_id", "trip_id"]).ngroups
            ps = bridge_split_runs(ps, tt)
            key = "run"
            print(f"分かれて記録された便をつないだ: 便 {n0:,} → 走り {ps.run.nunique():,}", flush=True)
        else:
            key = "trip_id"
        self.trips = {}
        for (rid, d), g in ps.groupby(["route_id", "date"]):
            lst = []
            for _, tg in g.groupby(["vehicle_id", key]):
                tg = tg.sort_values("seq")
                lst.append((tg.seq.to_numpy(), tg.t.to_numpy()))
            self.trips[(rid, d)] = lst
        self.cum = cum

    def ride_detail(self, rid, d, i, j, t_arrive_stop: float):
        """t 以降 3 時間以内に停留所 i を通った最初のバスの (乗車時刻, 降車時刻 or None)。来なければ None。"""
        cum = self.cum.get(rid)
        best = None
        for seqs, ts in self.trips.get((rid, d), []):
            if seqs.min() > i or seqs.max() < i:
                continue
            ti = float(np.interp(cum[i], cum[seqs], ts))
            if ti < t_arrive_stop or ti - t_arrive_stop > 3 * 3600:
                continue
            if best is None or ti < best[0]:
                tj = float(np.interp(cum[j], cum[seqs], ts)) if seqs.max() >= j else None
                best = (ti, tj)
        return best

    def ride(self, rid, d, i, j, t_arrive_stop: float):
        """t 以降に停留所 i を通った最初のバスの (乗車時刻, 降車時刻)。降車まで追えなければ None。"""
        best = self.ride_detail(rid, d, i, j, t_arrive_stop)
        if best is None or best[1] is None:
            return None
        return best


class _Routes:
    """出発時刻の時点で見えていたバスの位置 {route_id: [(lat, lng, epoch)]}（GTFS-RT の代わり、必要な路線だけ作る）。"""

    def __init__(self, sim, d, now_ep):
        self.sim, self.d, self.now_ep, self.cache = sim, d, now_ep, {}

    def get(self, rid, default=None):
        if rid not in self.cache:
            self.cache[rid] = self.sim.vehicles(rid, self.d, self.now_ep)
        return self.cache[rid] or default


class _Links:
    """LiveLinks.last_pass の代わり: 出発時刻までに検出された通過だけで、停留所 i を最後のバスが通った時刻。"""

    def __init__(self, sim, d, now_ep):
        self.sim, self.d, self.now_ep = sim, d, now_ep

    def last_pass(self, route_id, i, cum, now_epoch):
        cap = min(now_epoch, self.now_ep)
        best = None
        for seqs, ts in self.sim.rp.trips.get((str(route_id), self.d), []):
            m = ts <= cap
            if m.sum() < 1:
                continue
            s, t = seqs[m], ts[m]
            if s.min() > i or s.max() < i:
                continue
            ti = float(np.interp(cum[i], cum[s], t))
            if ti < cap and (best is None or ti > best):
                best = ti
        return best


class SimLive:
    """検証週の GPS の通過から、出発時刻の時点で見えていたものだけを作り、planner.plan(live_wait=...) に渡す関数を返す。

    本番の tsh.realtime.LiveFeed.wait_fn と同じ規則（手前を走るバスの到着予測 → 無ければ WaitModel の折り返し・
    前のバスからの経過・実際の発車の時刻表）。バスの位置は「出発時刻までの 10 分以内に最後に検出された停留所」とする。
    WaitModel の部品（運行間隔・折り返しの組・実際の発車）は学習期間だけで作り直す（検証週を使わない）。
    """

    def __init__(self, P: Planner, rp: Replay, fit_days=None):
        from .improve_wait import Residual, chaining, headway_samples
        fit_days = fit_days or C.TRAIN_DAYS
        from .waitmodel import WaitModel, actual_departures
        self.P, self.rp = P, rp
        wm = WaitModel(P.tt)
        wm.res = Residual(headway_samples(fit_days))
        wm.feeders = {str(k): v for k, v in chaining(fit_days, P.tt)[0].items()}
        wm.deps = {}
        for (r, d), x in actual_departures(fit_days).groupby(["route_id", "date"]):
            wm.deps.setdefault((r, C.day_type(pd.Timestamp(d).date())), []).append(np.sort(x.sec.to_numpy()))
        self.wm = wm

    def vehicles(self, rid, d, now_ep):
        xy = self.P.seq_xy.get(rid)
        if xy is None:
            return []
        out = []
        for seqs, ts in self.rp.trips.get((str(rid), d), []):
            m = ts <= now_ep
            if not m.any():
                continue
            k = int(np.argmax(np.where(m, ts, -np.inf)))
            if now_ep - ts[k] > 600 or seqs[k] >= len(xy):
                continue
            out.append((float(xy[seqs[k], 0]), float(xy[seqs[k], 1]), float(ts[k])))
        return out

    def wait_fn(self, d, now: datetime):
        now_ep = pd.Timestamp(now, tz=C.TZ).timestamp()
        routes, links = _Routes(self, d, now_ep), _Links(self, d, now_ep)
        P, wm = self.P, self.wm

        def f(route_id: str, i: int, t: datetime):
            veh = routes.get(str(route_id)) or []
            xy = P.seq_xy[route_id]
            best = None
            for lat, lng, ts in veh:
                dd = C.dist_m(lat, lng, xy[:, 0], xy[:, 1])
                k = int(np.argmin(dd))
                if dd[k] > 300 or k >= i:
                    continue
                t_k = datetime.fromtimestamp(ts, timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)
                eta = t_k + timedelta(seconds=P.tt.ride_sec(route_id, k, i, t_k))
                w = (eta - t).total_seconds()
                if w >= C.CATCH_MIN_S and (best is None or w < best):
                    best = max(w, 0.0)
            w, src = wm.wait(route_id, i, t, best, routes, links)
            return (w, src) if w is not None else None
        return f


def replay_option(rp: Replay, opt: dict, d, t0: float):
    return replay_option_status(rp, opt, d, t0)[0]


def replay_option_status(rp: Replay, opt: dict, d, t0: float):
    """(合計の秒 or None, 状態)。状態: ok / nobus（乗る停留所に 3 時間以内に GPS のバスが来ない）/
    untracked（乗ったバスが降りる停留所まで GPS で追えない＝正解が作れない）。"""
    t = t0
    for leg in opt["legs"]:
        if leg["mode"] == "walk":
            t += leg["minutes"] * 60
        else:
            r = rp.ride_detail(leg["route_id"], d, leg["board"]["seq"], leg["alight"]["seq"], t)
            if r is None:
                return None, "nobus"
            if r[1] is None:
                return None, "untracked"
            t = r[1]
    return t - t0, "ok"


def schedule_option(P: Planner, opt: dict, depart: datetime):
    """同じ案を時刻表どおりに走ると仮定した合計（秒）。時刻表に便が無ければ None。"""
    t = depart
    for leg in opt["legs"]:
        if leg["mode"] == "walk":
            t += timedelta(minutes=leg["minutes"])
        else:
            sn = P.tt.sched_next(leg["route_id"], leg["board"]["seq"], leg["alight"]["seq"], t)
            if sn is None:
                return None
            day0 = datetime(t.year, t.month, t.day)
            t = day0 + timedelta(seconds=sn[1])
    return (t - depart).total_seconds()


def main(n_pairs: int = 600, plan_wait: bool = True, replay: bool = True, live: bool = False, tag: str = "",
         eval_days=None, fit_days=None, excess=None, bridge: bool = True) -> None:
    """plan_wait=True: リアルタイムが無いときの待ち時間に「実際の通過の時刻表」（学習期間だけ）を使う（docs 14章）。
    replay=True: 合計時間と順位を「過去の同じ種類の日の再現の中央値」にする（docs 16章、plan_wait が要る）。
    live=True: 「今すぐ出る」検索。出発時刻の時点で見えていたバス（検証週の GPS）で 1 本目の待ちを出す（docs 16.5）。
    eval_days / fit_days: 測る日と部品を作る日（既定は検証週と学習期間。較正は CAL_DAYS と FIT_DAYS、16.6）。
    excess: 「今すぐ出る」の 1 本目の待ちの外れ方の分布（tsh.live_excess、16.6）。None なら使わない。
    bridge: 正解（実際に来たバス）を作る前に、分かれて記録された便をつなぐ（16.8。False は 16.7 までの正解）。"""
    eval_days = eval_days or C.TEST_DAYS
    fit_days = fit_days or C.TRAIN_DAYS
    sys.stdout.reconfigure(encoding="utf-8")
    t_start = time.time()
    P = Planner("train")
    P.seg = SegModel(train_only=True)
    if plan_wait:
        from .waitmodel import PassageTimetable
        P.plan_wait = PassageTimetable(fit_days)
        P.plan_wait.jitter_s = float(os.environ.get("TSH_PT_JITTER_S", str(P.plan_wait.jitter_s)))   # docs 17章の実験用
        P.plan_replay = replay
    P.keep_tot = True
    if os.environ.get("TSH_PLAN_CALIB") == "1":
        # 前もって計画の、選ぶことによる偏りの較正（docs 17章、python -m tsh.plan_calib で作る）
        from .plan_calib import load as load_calib
        P.plan_calib = load_calib()
        print("前もって計画の較正:", P.plan_calib, flush=True)
    P.live_excess = excess
    ps = load_passages(eval_days)
    rp = Replay(ps, P.tt.cum, tt=P.tt if bridge else None)
    sim = SimLive(P, rp, fit_days) if live else None
    st = C.stops()
    xy = st[["stop_lat", "stop_lon"]].to_numpy()
    rows = []
    tries = 0
    while len(rows) < n_pairs and tries < n_pairs * 5:
        tries += 1
        a, b = RNG.integers(len(xy), size=2)
        km = float(C.dist_m(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1])) / 1000
        if not 3 <= km <= 15:
            continue
        d = eval_days[int(RNG.integers(len(eval_days)))]
        dep = datetime(d.year, d.month, d.day) + timedelta(seconds=int(RNG.integers(7 * 3600, 21 * 3600)))
        res = P.plan(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], dep, max_options=3,
                     live_wait=sim.wait_fn(d, dep) if sim else None)
        if not res["options"]:
            continue
        t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
        opts = []
        for k, o in enumerate(res["options"]):
            act, stt = replay_option_status(rp, o, d, t0)
            sch = schedule_option(P, o, dep)
            safe = None
            if o.get("arrive_safe"):
                hh, mm = map(int, o["arrive_safe"].split(":"))
                safe = (datetime(dep.year, dep.month, dep.day, hh, mm) - dep).total_seconds()
                safe = safe + 86400 if safe < 0 else safe
            # 1 本目の待ち（予測と、検証週の GPS で実際に最初に来たバスまで）
            l0, w_walk = o["legs"][1], o["legs"][0]["minutes"] * 60
            r0 = rp.ride_detail(l0["route_id"], d, l0["board"]["seq"], l0["alight"]["seq"], t0 + w_walk)
            # 実際の所要時間が、過去の日ごとの再現の分布のどの位置に来たか（tsh.plan_calib。降りるまで追えた案だけ）
            tot = o.pop("_tot", None)
            pit = None
            if tot is not None and act is not None:
                tot = np.asarray(tot, float)
                pit = float(np.mean(tot < act) + 0.5 * np.mean(tot == act))
            opts.append({"rank": k, "pred_s": o["total_min"] * 60, "actual_s": act, "sched_s": sch, "safe_s": safe, "pit": pit,
                         "wait0_pred_s": l0["wait_min"] * 60, "wait0_act_s": (r0[0] - t0 - w_walk) if r0 else None,
                         "transfers": o["transfers"], "status": stt, "unreliable": o.get("unreliable", False),
                         "src0": o["legs"][1]["wait_source"]})
        rows.append({"pair": len(rows), "km": km, "depart": dep, "day_type": C.day_type(d), "opts": opts})
        if len(rows) % 100 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)
    # 1位の案の精度
    top = [(r, r["opts"][0]) for r in rows if r["opts"][0]["actual_s"] is not None]
    act = np.array([o["actual_s"] for _, o in top]); pred = np.array([o["pred_s"] for _, o in top])
    sch = np.array([o["sched_s"] if o["sched_s"] is not None else np.nan for _, o in top])
    within = lambda p: {f"within_{m}min_%": round(float(np.nanmean(np.abs(p - act) <= m * 60) * 100), 1) for m in (5, 10, 15)}
    st0 = [r["opts"][0]["status"] for r in rows]
    res = {"pairs": len(rows), "top_option_replayable": len(top),
           # 1 位の案の状態: nobus＝乗る停留所に 3 時間以内に GPS のバスが来なかった（利用者には「来ない」案）
           "top_option_status_%": {s: round(st0.count(s) / max(len(st0), 1) * 100, 1) for s in ("ok", "nobus", "untracked")},
           "top_option_accuracy": {"model": {**metrics(act, pred), **within(pred)},
                                   "timetable": {**metrics(act, sch), **within(sch)}},
           "by_transfers": {}}
    sf = [(o["actual_s"], o["safe_s"]) for _, o in top if o.get("safe_s") is not None]
    if sf:
        # 余裕を見た到着（arrive_safe）の内に実際に着いた割合（分は arrive_safe が分単位なので +59 秒まで同じ分とみなす）
        res["top_option_safe"] = {"n": len(sf), "share_of_replayable_%": round(len(sf) / max(len(top), 1) * 100, 1),
                                  "arrived_by_safe_%": round(float(np.mean([a <= s + 59 for a, s in sf])) * 100, 1),
                                  "mean_safe_minus_pred_min": round(float(np.mean([s for _, s in sf]) - np.mean(
                                      [o["pred_s"] for _, o in top if o.get("safe_s") is not None])) / 60, 1)}
    # 1 本目の待ちの出どころ別（再現できた 1 位の案）
    srcs = sorted({o["src0"] for _, o in top})
    res["by_first_wait_source"] = {}
    for s_ in srcs:
        idx = [k for k, (_, o) in enumerate(top) if o["src0"] == s_]
        res["by_first_wait_source"][s_] = metrics(act[idx], pred[idx])
    for tr in (0, 1):
        idx = [k for k, (_, o) in enumerate(top) if o["transfers"] == tr]
        if idx:
            res["by_transfers"][f"乗換{tr}回"] = {"model": metrics(act[idx], pred[idx]), "timetable": metrics(act[idx], sch[idx])}
    # 1位の案が実際に最速だったか（再現できた案が 2 つ以上ある組）
    hit_m = hit_s = n_cmp = 0
    regret_m, regret_s = [], []
    for r in rows:
        ok = [o for o in r["opts"] if o["actual_s"] is not None and o["sched_s"] is not None]
        if len(ok) < 2:
            continue
        n_cmp += 1
        best_act = min(o["actual_s"] for o in ok)
        pm = min(ok, key=lambda o: o["pred_s"]); psch = min(ok, key=lambda o: o["sched_s"])
        hit_m += pm["actual_s"] == best_act; hit_s += psch["actual_s"] == best_act
        regret_m.append(pm["actual_s"] - best_act); regret_s.append(psch["actual_s"] - best_act)
    res["route_choice"] = {"pairs_with_2plus_replayable": n_cmp,
                           "model_picked_actual_fastest_%": round(hit_m / max(n_cmp, 1) * 100, 1),
                           "timetable_picked_actual_fastest_%": round(hit_s / max(n_cmp, 1) * 100, 1),
                           "model_mean_regret_min": round(float(np.mean(regret_m)) / 60, 2) if regret_m else None,
                           "timetable_mean_regret_min": round(float(np.mean(regret_s)) / 60, 2) if regret_s else None}
    out = C.RESULTS
    (out / f"journey_replay_metrics{tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    flat = [{"pair": r["pair"], "km": r["km"], "depart": r["depart"], **o} for r in rows for o in r["opts"]]
    pd.DataFrame(flat).to_csv(out / f"journey_replay_samples{tag}.csv", index=False)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


def schedule_latest_departure(P: Planner, opt: dict, target: datetime, max_min: int = 240):
    """時刻表どおりに走ると仮定して、target までに着く最も遅い出発（分単位）。Google の「到着時刻」に近い決め方
    （ヘルプ: 交通機関の時刻表に基づく）。max_min 分前に出ても間に合わなければ None。遅く出るほど遅く着くので二分探索。"""
    def ok(m):
        dep = target - timedelta(minutes=m)
        s = schedule_option(P, opt, dep)
        return s is not None and dep + timedelta(seconds=s) <= target
    if not ok(max_min):
        return None
    lo, hi = 0, max_min           # ok(hi) は真
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    return target - timedelta(minutes=lo)


def main_arrive(n_pairs: int = 600, tag: str = "", bridge: bool = True, eval_days=None, fit_days=None,
                ride_sd: bool = False, rank: str = "q") -> None:
    """到着時刻を指定する検索の検証（docs 16.9）。600 組に検証週の 8〜22 時の到着時刻をランダムに付け、学習期間だけの
    「実際の通過の時刻表」で plan_arrive を検索する。1 位の案について、次の出発で出たら検証週の GPS で何時に着いたかを再現する:
      ours85: 過去の日の 85% で間に合う最も遅い出発（今の方式）
      ours50: 過去の日の半分で間に合う最も遅い出発（中央値の所要時間で逆算するのに近い）
      timetable: 同じ案を GTFS の時刻表どおりに走ると仮定して間に合う最も遅い出発（Google の決め方に近い）
    間に合った割合（バスが来なかった日は間に合わなかったに数える）、早く着きすぎた分、遅れた分を比べる。
    eval_days / fit_days: 測る日と通過の時刻表を作る日（既定は検証週と学習期間。決め方の比較は CAL_DAYS と FIT_DAYS）。
    ride_sd: 乗車時間のばらつきを出発に入れる。rank: "q"＝85% の出発で順位、"median"＝半分の日の出発で順位。"""
    sys.stdout.reconfigure(encoding="utf-8")
    eval_days = eval_days or C.TEST_DAYS
    fit_days = fit_days or C.TRAIN_DAYS
    t_start = time.time()
    P = Planner("train")
    P.seg = SegModel(train_only=True)
    from .waitmodel import PassageTimetable
    from .planner import ARRIVE_Q
    # 何 % の日で間に合う出発にするか（docs 17章。較正の週で実際に 85% 間に合う値を選ぶときに変える）
    arrive_q = float(os.environ.get("TSH_ARRIVE_Q", str(ARRIVE_Q)))
    P.plan_wait = PassageTimetable(fit_days)
    P.plan_replay = True
    P.arrive_ride_sd, P.arrive_rank = ride_sd, rank
    print(f"到着時刻の検証: 測る日 {eval_days[0]}〜{eval_days[-1]}、時刻表 {fit_days[0]}〜{fit_days[-1]}、"
          f"乗車時間のばらつき {ride_sd}、順位 {rank}", flush=True)
    rp = Replay(load_passages(eval_days), P.tt.cum, tt=P.tt if bridge else None)
    st = C.stops()
    xy = st[["stop_lat", "stop_lon"]].to_numpy()
    rng = np.random.default_rng(2027)
    rows, tries = [], 0
    while len(rows) < n_pairs and tries < n_pairs * 5:
        tries += 1
        a, b = rng.integers(len(xy), size=2)
        km = float(C.dist_m(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1])) / 1000
        if not 3 <= km <= 15:
            continue
        d = eval_days[int(rng.integers(len(eval_days)))]
        target = datetime(d.year, d.month, d.day) + timedelta(seconds=int(rng.integers(8 * 3600, 22 * 3600)))
        res = P.plan_arrive(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], target, max_options=3, q=arrive_q)
        if not res["options"]:
            continue
        o = res["options"][0]
        day0 = datetime(d.year, d.month, d.day)
        hm = lambda s: day0 + timedelta(hours=int(s[:2]), minutes=int(s[3:])) if s else None
        deps = {"ours85": hm(o["depart"]) if not o.get("unreliable") else None,
                "ours50": hm(o["depart_median"]),
                "timetable": schedule_latest_departure(P, o, target)}
        row = {"pair": len(rows), "km": km, "target": target, "transfers": o["transfers"],
               "unreliable": bool(o.get("unreliable")), "on_time_share_train": o.get("on_time_share")}
        for k, dep in deps.items():
            if dep is None:
                row[f"{k}_status"] = "none"
                continue
            t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
            act, stt = replay_option_status(rp, o, d, t0)
            row[f"{k}_budget_min"] = (target - dep).total_seconds() / 60
            row[f"{k}_status"] = stt
            # 着いた時刻 − 到着時刻（分、− は早く着いた）
            row[f"{k}_late_min"] = (act - (target - dep).total_seconds()) / 60 if act is not None else None
            if k == "ours85":
                # 出発をさらに B 分早めたら間に合ったか（docs 17章。較正の週で 85% 間に合う余裕を決める）。
                # 1 = 間に合った、0 = 遅れた・バスが来なかった、NaN = 追えない
                for B in range(0, 31, 2):
                    tb = t0 - B * 60
                    a2, s2 = replay_option_status(rp, o, d, tb)
                    row[f"early{B}"] = (np.nan if s2 == "untracked" else
                                        float(s2 == "ok" and a2 <= (target - dep).total_seconds() + B * 60))
        rows.append(row)
        if len(rows) % 100 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)
    df = pd.DataFrame(rows)
    out = {"pairs": len(df), "top_option_unreliable_%": round(float(df.unreliable.mean() * 100), 1), "methods": {}}
    for k in ("ours85", "ours50", "timetable"):
        s = df[f"{k}_status"]
        late = df.get(f"{k}_late_min")
        ok = s == "ok"
        judged = ok | (s == "nobus")        # バスが来なかったものは間に合わなかったに数える（追えないものは除く）
        on = ok & (late <= 0)
        out["methods"][k] = {
            "departure_given": int((s != "none").sum()),
            "replayable": int(ok.sum()), "nobus": int((s == "nobus").sum()), "untracked": int((s == "untracked").sum()),
            "on_time_%_of_replayable": round(float(on[ok].mean() * 100), 1) if ok.any() else None,
            "on_time_%_incl_nobus": round(float(on[judged].mean() * 100), 1) if judged.any() else None,
            "median_budget_min": round(float(df.loc[s != "none", f"{k}_budget_min"].median()), 1),
            "median_early_min_when_on_time": round(float(-late[on].median()), 1) if on.any() else None,
            "median_late_min_when_late": round(float(late[ok & (late > 0)].median()), 1) if (ok & (late > 0)).any() else None,
            "late_over_10min_%_of_replayable": round(float((late[ok] > 10).mean() * 100), 1) if ok.any() else None,
        }
    # 3 つとも出発が出せて再現できた同じ組で比べる
    same = df[(df.ours85_status == "ok") & (df.ours50_status == "ok") & (df.timetable_status == "ok")]
    out["same_pairs"] = {"n": len(same), **{k: {
        "on_time_%": round(float((same[f"{k}_late_min"] <= 0).mean() * 100), 1),
        "median_budget_min": round(float(same[f"{k}_budget_min"].median()), 1),
        "median_arrival_minus_target_min": round(float(same[f"{k}_late_min"].median()), 1)}
        for k in ("ours85", "ours50", "timetable")}}
    path = C.RESULTS
    (path / f"journey_arrive_metrics{tag}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str),
                                                            encoding="utf-8")
    df.to_csv(path / f"journey_arrive_samples{tag}.csv", index=False)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(f"（{time.time() - t_start:.0f}s）")


if __name__ == "__main__":
    # python -m tsh.validate_journeys [live|old|sum]
    #   live   : 今の方式で「今すぐ出る」検索（1 本目の待ちにリアルタイム、16.5）
    #   （なし）: 合計時間と順位を過去の日ごとの再現の中央値で（16章、今の方式）
    #   sum    : 区間ごとの予測の和（待ちは実際の通過の時刻表、14章）
    #   old    : 区間ごとの予測の和（待ちは過去の到着間隔、14章より前）
    #   livecal: 較正用。学習期間の中で FIT_DAYS（10/1〜17）で部品を作り、CAL_DAYS（10/18〜24）で「今すぐ出る」を測る（16.6）
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "live":
        # 余裕を見た到着に、較正の週（livecal → python -m tsh.live_excess）で集めた 1 本目の待ちの外れ方を入れる（16.6）
        from .live_excess import load as load_excess
        ex = load_excess()
        if ex is None:
            print("live_wait_excess.json が無いので、余裕を見た到着は点の予測のまま（16.5 の方式）")
        main(live=True, tag="_live", excess=ex)
    elif mode == "livecal":
        main(live=True, tag="_live_cal", eval_days=CAL_DAYS, fit_days=FIT_DAYS)
    elif mode == "livecalcheck":
        # 較正の週に、そこで集めた外れ方を入れて余裕を見た到着を測る（同じ週なので内側の確認。外側の確認は live）
        from .live_excess import load as load_excess
        main(live=True, tag="_live_cal_check", eval_days=CAL_DAYS, fit_days=FIT_DAYS, excess=load_excess())
    elif mode == "arrive":
        # 到着時刻を指定する検索（16.9）: 85% の日で間に合う出発 vs 半分の日 vs 時刻表どおり
        main_arrive()
    elif mode == "arrivecal":
        # 到着時刻の決め方を学習期間の中で比べる（10/1〜17 で時刻表、10/18〜24 で測る）。
        # 引数: 乗車時間のばらつき（sd）と順位（median）。例: arrivecal sd median
        opt = sys.argv[2:]
        main_arrive(tag="_cal" + "".join("_" + x for x in opt) + os.environ.get("TSH_TAG", ""), eval_days=CAL_DAYS, fit_days=FIT_DAYS,
                    ride_sd="sd" in opt, rank="median" if "median" in opt else "q")
    elif mode == "plancal":
        # 前もって計画を較正の週で測る（docs 17章。TSH_PT_JITTER_S で再現のずらし幅を変えて比べる）
        main(tag="_plan_cal" + os.environ.get("TSH_TAG", ""), eval_days=CAL_DAYS, fit_days=FIT_DAYS)
    elif mode == "old":
        main(plan_wait=False, replay=False, tag="_old")
    elif mode == "sum":
        main(plan_wait=True, replay=False, tag="_sum")
    else:
        main()
