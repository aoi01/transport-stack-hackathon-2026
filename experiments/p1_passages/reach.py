"""「今すぐ出る」の誤差の内訳と、見えているバスが「本当に乗る停留所まで来るか」の確率（検証週 10/25〜31）。

1. 来る確率: 学習期間（10/1〜24）の走り（分かれて記録された便をつないだもの）から、路線ごとに
   「停留所 k を通った走りのうち、停留所 i まで走った割合」を、時間帯（5 区分）と「始発から走り始めたか」で分けて数える。
   検証週の走りで、ランダムな時点の位置 k と先の停留所 i について当たり方（Brier・AUC・確率の帯ごとの実際の割合）を測る。
2. 誤差の内訳: 今の版で 1 位の案を検証週の GPS で再現し、区間ごとに「実際 − 予測」を出す
   （1 本目の待ち・1 本目の乗車・乗り換えの待ち・2 本目の乗車・合計の調整＝合計の予測と区間の予測の和の差）。
3. 確率入りの待ち: 見えているバスのうち、来る確率が θ 未満のものを待ちの計算から外す（θ = 0.5, 0.8）。
   同じ組で今の版と比べる。待ちの外れ方の分布（live_excess）は今の版で作ったものをそのまま使う。
使い方: PYTHONPATH=src python experiments/p1_passages/reach.py [組の数]
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from tsh import common as C
from tsh.live_excess import load as load_excess
from tsh.plan_calib import load as load_calib
from tsh.planner import Planner
from tsh.segmodel import SegModel
from tsh.validate_journeys import Replay, SimLive, _Links, _Routes, load_passages
from tsh.waitmodel import PassageTimetable

from intercept import record, summary

RNG = np.random.default_rng(2027)
THETAS = (0.5, 0.8)
MIN_N = 20
IST = 19800


def band(h):
    return int(np.searchsorted([7, 10, 16, 20], h, side="right"))   # 0:〜7 1:7〜10 2:10〜16 3:16〜20 4:20〜


class Survival:
    def __init__(self, rp: Replay):
        acc = {}
        for (rid, d), lst in rp.trips.items():
            for seqs, ts in lst:
                h = int(((ts[0] + IST) % 86400) // 3600)
                acc.setdefault(str(rid), []).append((seqs.min(), seqs.max(), band(h), seqs.min() > 3))
        self.R = {r: tuple(np.array(c) for c in zip(*v)) for r, v in acc.items()}
        self.cache = {}

    def p(self, rid, k, i, h, mid):
        key = (str(rid), int(k), int(i), band(h), bool(mid))
        if key in self.cache:
            return self.cache[key]
        a = self.R.get(str(rid))
        out = None
        if a is not None:
            smin, smax, b, m = a
            base = (smin <= k) & (smax >= k)
            for cond in (base & (b == key[3]) & (m == key[4]), base & (m == key[4]), base):
                n = int(cond.sum())
                if n >= MIN_N:
                    out = float(((smax >= i) & cond).sum() / n)
                    break
        self.cache[key] = out
        return out


def auc(y, p):
    order = np.argsort(p)
    r = np.empty(len(p)); r[order] = np.arange(1, len(p) + 1)
    # 同じ値は平均の順位に
    s = pd.Series(p); r = s.rank().to_numpy()
    n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def check_survival(surv, rp_test, P, n=30000):
    keys = [k for k in rp_test.trips if str(k[0]) in P.tt.cum]
    ys, ps, pr = [], [], []
    route_only = {}
    for r, (smin, smax, b, m) in surv.R.items():
        route_only[r] = (smin, smax)
    tries = 0
    while len(ys) < n and tries < n * 5:
        tries += 1
        rid, d = keys[int(RNG.integers(len(keys)))]
        lst = rp_test.trips[(rid, d)]
        seqs, ts = lst[int(RNG.integers(len(lst)))]
        L = len(P.tt.cum[str(rid)])
        q = int(RNG.integers(len(seqs)))
        k = int(seqs[q])
        if k >= L - 2:
            continue
        i = int(min(L - 1, k + int(RNG.integers(1, 41))))
        h = int(((ts[q] + IST) % 86400) // 3600)
        p = surv.p(rid, k, i, h, seqs[0] > 3)
        if p is None:
            continue
        smin, smax = route_only[str(rid)]
        base = (smin <= k) & (smax >= k)
        ys.append(int(seqs.max() >= i)); ps.append(p); pr.append(float(((smax >= i) & base).sum() / max(base.sum(), 1)))
    y, p, pr = np.array(ys), np.array(ps), np.array(pr)
    bins = [0, .5, .7, .8, .9, .95, 1.01]
    rel = {}
    for lo, hi in zip(bins[:-1], bins[1:]):
        mm = (p >= lo) & (p < hi)
        if mm.any():
            rel[f"{lo:.2f}〜{min(hi, 1):.2f}"] = {"n": int(mm.sum()), "予測の平均": round(float(p[mm].mean()), 3),
                                                 "実際に来た割合": round(float(y[mm].mean()), 3)}
    return {"n": int(len(y)), "実際に来た割合": round(float(y.mean()), 3),
            "Brier": {"いつも来る（今の版）": round(float(np.mean((1 - y) ** 2)), 4),
                      "路線と位置だけ": round(float(np.mean((pr - y) ** 2)), 4),
                      "時間帯と始発からかも": round(float(np.mean((p - y) ** 2)), 4)},
            "AUC": {"路線と位置だけ": round(auc(y, pr), 3), "時間帯と始発からかも": round(auc(y, p), 3)},
            "確率の帯ごと": rel}


class SimReach(SimLive):
    def __init__(self, base: SimLive, surv: Survival, theta: float):
        self.P, self.rp, self.wm, self.surv, self.theta = base.P, base.rp, base.wm, surv, theta

    def wait_fn(self, d, now: datetime):
        now_ep = pd.Timestamp(now, tz=C.TZ).timestamp()
        routes, links = _Routes(self, d, now_ep), _Links(self, d, now_ep)
        P, wm, surv, theta = self.P, self.wm, self.surv, self.theta
        cache = {}

        def vehx(rid):
            if rid not in cache:
                out = []
                for seqs, ts in self.rp.trips.get((str(rid), d), []):
                    m = ts <= now_ep
                    if not m.any():
                        continue
                    k = int(np.argmax(np.where(m, ts, -np.inf)))
                    if now_ep - ts[k] > 600 or seqs[k] >= len(P.seq_xy[rid]):
                        continue
                    xy = P.seq_xy[rid]
                    out.append((float(xy[seqs[k], 0]), float(xy[seqs[k], 1]), float(ts[k]), bool(seqs[0] > 3)))
                cache[rid] = out
            return cache[rid]

        def f(route_id: str, i: int, t: datetime):
            if P.seq_xy.get(route_id) is None:
                return None
            xy = P.seq_xy[route_id]
            best = None
            for lat, lng, ts, mid in vehx(route_id):
                dd = C.dist_m(lat, lng, xy[:, 0], xy[:, 1])
                k = int(np.argmin(dd))
                if dd[k] > 300 or k >= i:
                    continue
                t_k = datetime.fromtimestamp(ts, timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)
                eta = t_k + timedelta(seconds=P.tt.ride_sec(route_id, k, i, t_k))
                w = (eta - t).total_seconds()
                if w < C.CATCH_MIN_S:
                    continue
                p = surv.p(route_id, k, i, now.hour, mid)
                if p is not None and p < theta:
                    continue
                if best is None or w < best:
                    best = max(w, 0.0)
            w, src = wm.wait(route_id, i, t, best, routes, links)
            return (w, src) if w is not None else None
        return f


def legs_actual(rp, o, d, t0):
    """区間ごとの (予測, 実際) と、止まった区間。"""
    t, out, n = t0, [], 0
    for leg in o["legs"]:
        if leg["mode"] == "walk":
            t += leg["minutes"] * 60
            continue
        r = rp.ride_detail(leg["route_id"], d, leg["board"]["seq"], leg["alight"]["seq"], t)
        if r is None:
            return out, f"nobus{n}"
        out.append((f"wait{n}", leg["wait_min"] * 60, r[0] - t))
        if r[1] is None:
            return out, f"untracked{n}"
        out.append((f"ride{n}", leg["ride_min"] * 60, r[1] - r[0]))
        t, n = r[1], n + 1
    return out, "ok"


def decompose(recs):
    ok = [r for r in recs if r["status"] == "ok"]
    res = {"n": len(recs), "止まった区間_%": {}}
    st = pd.Series([r["status"] for r in recs]).value_counts(normalize=True) * 100
    res["止まった区間_%"] = {k: round(float(v), 1) for k, v in st.items()}
    for name in ("wait0", "ride0", "wait1", "ride1"):
        e = np.array([x[2] - x[1] for r in ok for x in r["legs"] if x[0] == name]) / 60
        if len(e):
            res[name] = {"n": int(len(e)), "誤差の絶対値_中央値_分": round(float(np.median(np.abs(e))), 1),
                         "実際−予測_中央値_分": round(float(np.median(e)), 1),
                         "10分以上ずれた_%": round(float(np.mean(np.abs(e) >= 10)) * 100, 1),
                         "誤差の2乗の合計の割合_%": None, "_sq": float(np.sum(e ** 2))}
    adj = np.array([(r["pred_s"] - r["leg_pred_sum_s"]) for r in ok]) / 60
    res["合計の調整（合計の予測−区間の予測の和）_中央値_分"] = round(float(np.median(adj)), 1)
    tot = np.array([r["actual_s"] - r["pred_s"] for r in ok]) / 60
    res["合計の誤差の絶対値_中央値_分"] = round(float(np.median(np.abs(tot))), 1)
    sq = sum(v["_sq"] for k, v in res.items() if isinstance(v, dict) and "_sq" in v)
    for k, v in list(res.items()):
        if isinstance(v, dict) and "_sq" in v:
            v["誤差の2乗の合計の割合_%"] = round(v.pop("_sq") / sq * 100, 1)
    # 組ごとに一番大きくずれた区間
    big = pd.Series([max(r["legs"], key=lambda x: abs(x[2] - x[1]))[0] for r in ok if r["legs"]])
    res["一番大きくずれた区間_%"] = {k: round(float(v), 1) for k, v in (big.value_counts(normalize=True) * 100).items()}
    return res


def main(n: int = 600) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    t_start = time.time()
    P = Planner("train")
    P.seg = SegModel(train_only=True)
    P.plan_wait = PassageTimetable(C.TRAIN_DAYS)
    P.plan_replay = True
    P.keep_tot = False
    P.plan_calib = load_calib()
    P.live_excess = load_excess()
    rp_train = Replay(load_passages(C.TRAIN_DAYS), P.tt.cum, tt=P.tt)
    surv = Survival(rp_train)
    del rp_train
    print(f"来る確率の表: {len(surv.R)} 路線（{time.time() - t_start:.0f}s）", flush=True)
    rp = Replay(load_passages(C.TEST_DAYS), P.tt.cum, tt=P.tt)
    res = {"来る確率の当たり方（検証週）": check_survival(surv, rp, P)}
    print(json.dumps(res, ensure_ascii=False, indent=1), flush=True)

    sim = SimLive(P, rp, C.TRAIN_DAYS)
    sims = {"base": sim, **{f"th{th}": SimReach(sim, surv, th) for th in THETAS}}
    xy = C.stops()[["stop_lat", "stop_lon"]].to_numpy()
    rows, tries = [], 0
    while len(rows) < n and tries < n * 5:
        tries += 1
        a, b = RNG.integers(len(xy), size=2)
        km = float(C.dist_m(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1])) / 1000
        if not 3 <= km <= 15:
            continue
        d = C.TEST_DAYS[int(RNG.integers(len(C.TEST_DAYS)))]
        dep = datetime(d.year, d.month, d.day) + timedelta(seconds=int(RNG.integers(7 * 3600, 21 * 3600)))
        t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
        args = (xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1], dep)
        row = {"pair": len(rows), "km": km, "depart": dep}
        for name, s in sims.items():
            r = P.plan(*args, max_options=3, live_wait=s.wait_fn(d, dep))
            if not r["options"]:
                row = None
                break
            o = r["options"][0]
            rec = record(rp, o, d, dep, t0)
            if name == "base":
                rec["legs"], rec["leg_status"] = legs_actual(rp, o, d, t0)
                rec["leg_pred_sum_s"] = sum(l["minutes"] * 60 if l["mode"] == "walk" else (l["wait_min"] + l["ride_min"]) * 60
                                            for l in o["legs"])
            row[name] = rec
        if row is None:
            continue
        rows.append(row)
        if len(rows) % 50 == 0:
            print(f"  {len(rows)} 組（{time.time() - t_start:.0f}s）", flush=True)

    base = [r["base"] for r in rows]
    for x in base:
        x["status"] = x["leg_status"]
    res["誤差の内訳（今の版の1位の案）"] = decompose(base)
    for x in base:
        x["status"] = "ok" if x["leg_status"] == "ok" else ("nobus" if x["leg_status"].startswith("nobus") else "untracked")
    for name in sims:
        res[name] = summary(rows, name)
    for th in THETAS:
        k = f"th{th}"
        both = [r for r in rows if r["base"]["actual_s"] is not None and r[k]["actual_s"] is not None]
        ch = [r for r in rows if r["base"]["wait0_pred_s"] != r[k]["wait0_pred_s"] or r["base"]["routes"] != r[k]["routes"]]
        e_b = np.array([abs(r["base"]["pred_s"] - r["base"]["actual_s"]) for r in both]) / 60
        e_k = np.array([abs(r[k]["pred_s"] - r[k]["actual_s"]) for r in both]) / 60
        dl = np.array([r[k]["actual_s"] - r["base"]["actual_s"] for r in both]) / 60
        res[f"同じ組で比べる θ={th}"] = {
            "予測が変わった組_%": round(len(ch) / len(rows) * 100, 1), "両方再現できた組": len(both),
            "誤差の絶対値_中央値_分（今 / θ）": [round(float(np.median(e_b)), 1), round(float(np.median(e_k)), 1)],
            "誤差の絶対値_平均_分（今 / θ）": [round(float(np.mean(e_b)), 1), round(float(np.mean(e_k)), 1)],
            "実際の所要時間の差_平均_分（θ − 今）": round(float(np.mean(dl)), 2),
            "実際に1分以上速い/遅い_%": [round(float(np.mean(dl <= -1)) * 100, 1), round(float(np.mean(dl >= 1)) * 100, 1)]}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (C.RESULTS / "reach_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    flat = [{"pair": r["pair"], "km": r["km"], "depart": r["depart"], "variant": k,
             **{kk: vv for kk, vv in r[k].items() if kk != "legs"}} for r in rows for k in sims]
    pd.DataFrame(flat).to_csv(C.RESULTS / "reach_samples.csv", index=False)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 600)
