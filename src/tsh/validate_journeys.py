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
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import common as C
from .planner import Planner
from .segmodel import SegModel
from .validate_p1 import load_test_passages, metrics

RNG = np.random.default_rng(2026)


class Replay:
    def __init__(self, ps: pd.DataFrame, cum: dict):
        ps = ps.copy()
        ps["date"] = pd.to_datetime(ps.date).dt.date
        ps["t"] = ps.ts.astype("datetime64[ns]").astype("int64") / 1e9
        self.trips = {}
        for (rid, d), g in ps.groupby(["route_id", "date"]):
            lst = []
            for _, tg in g.groupby(["vehicle_id", "trip_id"]):
                tg = tg.sort_values("seq")
                lst.append((tg.seq.to_numpy(), tg.t.to_numpy()))
            self.trips[(rid, d)] = lst
        self.cum = cum

    def ride(self, rid, d, i, j, t_arrive_stop: float):
        """t 以降に停留所 i を通った最初のバスの (乗車時刻, 降車時刻)。降車まで追えなければ None。"""
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
        if best is None or best[1] is None:
            return None
        return best


def replay_option(rp: Replay, opt: dict, d, t0: float):
    t = t0
    for leg in opt["legs"]:
        if leg["mode"] == "walk":
            t += leg["minutes"] * 60
        else:
            r = rp.ride(leg["route_id"], d, leg["board"]["seq"], leg["alight"]["seq"], t)
            if r is None:
                return None
            t = r[1]
    return t - t0


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


def main(n_pairs: int = 600) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    t_start = time.time()
    P = Planner("train")
    P.seg = SegModel(train_only=True)
    ps = load_test_passages()
    rp = Replay(ps, P.tt.cum)
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
        d = C.TEST_DAYS[int(RNG.integers(len(C.TEST_DAYS)))]
        dep = datetime(d.year, d.month, d.day) + timedelta(seconds=int(RNG.integers(7 * 3600, 21 * 3600)))
        res = P.plan(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], dep, max_options=3)
        if not res["options"]:
            continue
        t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
        opts = []
        for k, o in enumerate(res["options"]):
            act = replay_option(rp, o, d, t0)
            sch = schedule_option(P, o, dep)
            opts.append({"rank": k, "pred_s": o["total_min"] * 60, "actual_s": act, "sched_s": sch,
                         "transfers": o["transfers"]})
        rows.append({"pair": len(rows), "km": km, "depart": dep, "day_type": C.day_type(d), "opts": opts})
        if len(rows) % 100 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)
    # 1位の案の精度
    top = [(r, r["opts"][0]) for r in rows if r["opts"][0]["actual_s"] is not None]
    act = np.array([o["actual_s"] for _, o in top]); pred = np.array([o["pred_s"] for _, o in top])
    sch = np.array([o["sched_s"] if o["sched_s"] is not None else np.nan for _, o in top])
    within = lambda p: {f"within_{m}min_%": round(float(np.nanmean(np.abs(p - act) <= m * 60) * 100), 1) for m in (5, 10, 15)}
    res = {"pairs": len(rows), "top_option_replayable": len(top),
           "top_option_accuracy": {"model": {**metrics(act, pred), **within(pred)},
                                   "timetable": {**metrics(act, sch), **within(sch)}},
           "by_transfers": {}}
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
    out = C.ROOT / "results"
    (out / "journey_replay_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    flat = [{"pair": r["pair"], "km": r["km"], "depart": r["depart"], **o} for r in rows for o in r["opts"]]
    pd.DataFrame(flat).to_csv(out / "journey_replay_samples.csv", index=False)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
