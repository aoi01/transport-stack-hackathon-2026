"""問題1の精度検証。

学習: 10/1〜10/24 の GPS、検証: 10/25〜10/31 の GPS（モデルは検証期間を一切見ていない）。

検証A（乗車時間）: 検証期間の実際の便から、同じ便で停留所 i と j（5〜25 停留所先）の通過時刻を取り、
  実際の乗車時間と各手法の予測を比べる。
  - model   : 区間 × 平日/休日 × 時間帯の中央値（本モデル）
  - flat    : 区間の中央値（時間帯を区別しない）
  - schedule: GTFS 時刻表の所要時間
検証B（待ち時間込み）: ある時刻に停留所 i に着いた人が、次に来た実際のバスで j に着くまでの時間を、
  検証期間の GPS から再現し、予測（待ち時間 + 乗車時間）と比べる。比較の基準は時刻表どおりの「次の便」。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import common as C
from .traveltime import TravelTimeModel, passages_glob

RNG = np.random.default_rng(42)
OUT = C.RESULTS


def metrics(actual, pred) -> dict:
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    m = ~np.isnan(p)
    a, p = a[m], p[m]
    ape = np.abs(p - a) / a
    return {
        "n": int(m.sum()),
        "MAE_min": round(float(np.mean(np.abs(p - a)) / 60), 2),
        "MAPE_%": round(float(np.mean(ape) * 100), 1),
        "MedAPE_%": round(float(np.median(ape) * 100), 1),
        "within20%_%": round(float(np.mean(ape <= 0.2) * 100), 1),
        "bias_min": round(float(np.mean(p - a) / 60), 2),
        "median_err_min": round(float(np.median(p - a) / 60), 2),
        "actual_mean_min": round(float(np.mean(a) / 60), 1),
    }


def load_test_passages() -> pd.DataFrame:
    con = C.connect()
    df = con.execute(f"""
        SELECT date, vehicle_id, trip_id, CAST(route_id AS VARCHAR) AS route_id, seq,
               timezone('{C.TZ}', ts) AS ts
        FROM read_parquet({passages_glob(C.TEST_DAYS, truth=True)})
    """).df()
    return df


def sample_segments(ps: pd.DataFrame, n: int) -> pd.DataFrame:
    keys = ps[["date", "vehicle_id", "trip_id"]].drop_duplicates().sample(n=min(n * 3, 200_000), random_state=1)
    sub = ps.merge(keys, on=["date", "vehicle_id", "trip_id"])
    rows = []
    for (_, _, _), g in sub.groupby(["date", "vehicle_id", "trip_id"], sort=False):
        seqs = g.seq.to_numpy()
        if len(seqs) < 2:
            continue
        a = RNG.integers(0, len(seqs))
        cand = np.where((seqs - seqs[a] >= 5) & (seqs - seqs[a] <= 25))[0]
        if len(cand) == 0:
            continue
        b = RNG.choice(cand)
        r = g.iloc[a]
        rows.append((r.route_id, int(seqs[a]), int(seqs[b]), r.ts, g.iloc[b].ts))
        if len(rows) >= n:
            break
    s = pd.DataFrame(rows, columns=["route_id", "i", "j", "t_i", "t_j"])
    s["actual_s"] = (s.t_j - s.t_i).dt.total_seconds()
    return s[s.actual_s > 0]


def eval_ride(m: TravelTimeModel, ps: pd.DataFrame, n: int = 20_000) -> tuple[dict, pd.DataFrame]:
    s = sample_segments(ps, n)
    m.source_counts = {k: 0 for k in m.source_counts}
    s["model_s"] = [m.ride_sec(r.route_id, r.i, r.j, r.t_i.to_pydatetime()) for r in s.itertuples()]
    src = dict(m.source_counts)
    s["flat_s"] = [m.ride_sec(r.route_id, r.i, r.j, r.t_i.to_pydatetime(), mode="flat") for r in s.itertuples()]
    s["sched_s"] = [m.sched_ride_sec(r.route_id, r.i, r.j, r.t_i.to_pydatetime()) for r in s.itertuples()]
    s["sched_s"] = s.sched_s.astype(float)
    s["hr"] = s.t_i.dt.hour
    s["period"] = np.select([s.hr.between(8, 10), s.hr.between(17, 20)], ["朝ピーク(8-10時)", "夕ピーク(17-20時)"], "その他")
    s["day_type"] = [C.day_type(t.date()) for t in s.t_i]
    res = {"all": {k: metrics(s.actual_s, s[c]) for k, c in
                   [("model", "model_s"), ("flat", "flat_s"), ("schedule", "sched_s")]}}
    for p, g in s.groupby("period"):
        res[p] = {k: metrics(g.actual_s, g[c]) for k, c in [("model", "model_s"), ("flat", "flat_s"), ("schedule", "sched_s")]}
    for p, g in s.groupby("day_type"):
        res[p] = {k: metrics(g.actual_s, g[c]) for k, c in [("model", "model_s"), ("flat", "flat_s"), ("schedule", "sched_s")]}
    tot = sum(src.values())
    res["model_link_source_%"] = {k: round(v / tot * 100, 1) for k, v in src.items()}
    return res, s


def interp_trip(g: pd.DataFrame, cum: np.ndarray, i: int, j: int):
    """便 g の検出済み通過時刻から、seq i と j の通過時刻を距離で線形補間する。
    i が検出範囲外なら None。j が範囲外なら (t_i, None)。"""
    seqs = g.seq.to_numpy()
    if seqs.min() > i or seqs.max() < i:
        return None
    x = cum[seqs]
    y = g.ts.astype("datetime64[ns]").astype("int64").to_numpy() / 1e9
    tj = np.interp(cum[j], x, y) if seqs.max() >= j else None
    return np.interp(cum[i], x, y), tj


def eval_door(m: TravelTimeModel, ps: pd.DataFrame, n: int = 3000) -> tuple[dict, pd.DataFrame]:
    by_route_day = {k: g for k, g in ps.groupby(["route_id", "date"])}
    keys = list(by_route_day.keys())
    rows = []
    tries = 0
    while len(rows) < n and tries < n * 20:
        tries += 1
        rid, d = keys[RNG.integers(len(keys))]
        if rid not in m.cum:
            continue
        cum = m.cum[rid]
        L = len(cum)
        if L < 8:
            continue
        i = int(RNG.integers(0, L - 6))
        j = int(min(L - 1, i + RNG.integers(5, 26)))
        dep = datetime.combine(d, datetime.min.time()) + timedelta(seconds=int(RNG.integers(6 * 3600, 21 * 3600)))
        t0 = pd.Timestamp(dep).value / 1e9
        # 停留所 i を通った（i が GPS の検出範囲内にある）便のうち、t0 以降で最初の便
        best = None
        for _, g in by_route_day[(rid, d)].groupby(["vehicle_id", "trip_id"]):
            r = interp_trip(g, cum, i, j)
            if r is None or r[0] < t0:
                continue
            if best is None or r[0] < best[0]:
                best = r
        if best is None or best[0] - t0 > 2 * 3600:
            continue
        actual_wait = best[0] - t0
        # その便が j まで GPS で追えたときだけ、待ち時間込みの合計を比べる
        actual = (best[1] - t0) if best[1] is not None else np.nan
        w = m.wait_sec(rid, dep)
        pred = w + m.ride_sec(rid, i, j, dep + timedelta(seconds=w))
        # リアルタイム：時刻 t0 までの GPS だけを使い、i より手前を走っているバス（直近10分以内に検出）の
        # i 到着時刻を「最後に検出した停留所の時刻 + そこから i までの乗車時間モデル」で予測する。
        rt_wait = np.nan
        for _, g in by_route_day[(rid, d)].groupby(["vehicle_id", "trip_id"]):
            tt = g.ts.astype("datetime64[ns]").astype("int64").to_numpy() / 1e9
            past = tt <= t0
            if not past.any():
                continue
            k = int(g.seq.to_numpy()[past].max())
            t_k = float(tt[past].max())
            if k >= i or t0 - t_k > 600:
                continue
            eta = t_k + m.ride_sec(rid, k, i, datetime.fromtimestamp(t_k, tz=None) if False else
                                   pd.Timestamp(t_k, unit="s").to_pydatetime())
            if eta >= t0 - 60 and (np.isnan(rt_wait) or eta - t0 < rt_wait):
                rt_wait = max(eta - t0, 0.0)
        rt_found = not np.isnan(rt_wait)
        if not rt_found:
            rt_wait = w   # 手前にバスが見えないときは過去データの待ち時間
        pred_rt = rt_wait + m.ride_sec(rid, i, j, dep + timedelta(seconds=rt_wait))
        sn = m.sched_next(rid, i, j, dep)
        now = dep.hour * 3600 + dep.minute * 60 + dep.second
        sched = (sn[1] - now) if sn else np.nan
        sched_wait = (sn[0] - now) if sn else np.nan
        w_h = m.wait_sec(rid, dep, mode="headway")
        rows.append((rid, i, j, dep, actual, actual_wait, pred, w, w_h, sched, sched_wait, pred_rt, rt_wait, rt_found))
    s = pd.DataFrame(rows, columns=["route_id", "i", "j", "depart", "actual_s", "actual_wait_s",
                                    "model_s", "model_wait_s", "headway_wait_s", "sched_s", "sched_wait_s",
                                    "realtime_s", "realtime_wait_s", "realtime_found"])
    t = s.dropna(subset=["actual_s"])
    aw = s.actual_wait_s.clip(lower=30)
    f = s[s.realtime_found]
    tf = t[t.realtime_found]
    res = {"door_total": {"model": metrics(t.actual_s, t.model_s), "realtime": metrics(t.actual_s, t.realtime_s),
                          "schedule": metrics(t.actual_s, t.sched_s)},
           "door_total_bus_visible": {"model": metrics(tf.actual_s, tf.model_s),
                                      "realtime": metrics(tf.actual_s, tf.realtime_s),
                                      "schedule": metrics(tf.actual_s, tf.sched_s)},
           "wait_only": {"model": metrics(aw, s.model_wait_s),
                         "realtime": metrics(aw, s.realtime_wait_s),
                         "headway_half": metrics(aw, s.headway_wait_s),
                         "schedule": metrics(aw, s.sched_wait_s)},
           "wait_only_bus_visible": {"model": metrics(f.actual_wait_s.clip(lower=30), f.model_wait_s),
                                     "realtime": metrics(f.actual_wait_s.clip(lower=30), f.realtime_wait_s)},
           "share_bus_visible_%": round(float(s.realtime_found.mean() * 100), 1),
           "wait_mean_min": {"actual": round(s.actual_wait_s.mean() / 60, 1),
                             "model": round(s.model_wait_s.mean() / 60, 1),
                             "headway_half": round(s.headway_wait_s.mean() / 60, 1),
                             "schedule": round(s.sched_wait_s.mean() / 60, 1)},
           "share_tracked_to_j_%": round(float(s.actual_s.notna().mean() * 100), 1)}
    return res, s


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    m = TravelTimeModel("train")
    ps = load_test_passages()
    print(f"検証用の通過データ: {len(ps):,} 件")
    ride, s1 = eval_ride(m, ps)
    print(json.dumps(ride, ensure_ascii=False, indent=1))
    door, s2 = eval_door(m, ps)
    print(json.dumps(door, ensure_ascii=False, indent=1))
    s1.to_csv(OUT / "p1_ride_samples.csv", index=False)
    s2.to_csv(OUT / "p1_door_samples.csv", index=False)
    (OUT / "p1_metrics.json").write_text(json.dumps({"ride": ride, "door": door}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
