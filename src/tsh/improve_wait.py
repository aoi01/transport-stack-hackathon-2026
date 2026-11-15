"""問題1の改善実験3: 待ち時間（次のバスがいつ来るか）の予測。

最初の検証（validate_p1.eval_door）と同じ 3,000 件（results/p1_door_samples.csv）で比べる。

試す方法:
  W0 過去の実績: 路線 × 平日/休日 × 時間帯の E[H²]/(2E[H])（今の API）
  W1 リアルタイム（今の API）: 乗車停留所より手前を走っているバスの到着予測。見えなければ W0
  W2 前のバスからの経過時間で条件づけ: 停留所 i を最後のバスが通ってから e 分たっているとき、
     実際の運行間隔 H の分布から E[H − e | H > e]（残りの待ち時間）を出す（再生過程の「残り寿命」の考え方）
  W3 W1 で見えなければ W2
  W4 折り返しの予測を追加: 反対方向の路線を走っていて終点に近いバスは、終点で休憩したあと自分の路線を走り始める。
     「今の位置から反対路線の終点まで」＋「終点での休憩（実績の中央値）」＋「自分の路線の始点から i まで」で到着を予測。
     どの路線の次にどの路線を走るか（折り返しの組）と休憩時間は、10/1〜24 の GPS で車両ごとの便の並びから学ぶ。
  W5 W4 で見えなければ W2

予測に使う情報は、出発時刻 t0 までに分かるものだけ（GPS の点は t0 以前のもの）。
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import common as C
from .traveltime import TravelTimeModel, passages_glob
from .validate_p1 import load_test_passages, metrics

OUT = C.PROCESSED / "wait"


def headway_samples(days) -> pd.DataFrame:
    """基準停留所での実際の到着間隔（秒）: route_id, day_type, hr, hw"""
    con = C.connect()
    pat = C.patterns()[["route_id", "seq", "cum_m"]].copy()
    pat["route_id"] = pat.route_id.astype(int)
    con.register("pat", pat)
    con.register("daytypes", pd.DataFrame({"date": days, "day_type": [C.day_type(d) for d in days]}))
    return con.execute(f"""
        WITH ps AS (
            SELECT p.date, p.vehicle_id, p.trip_id, p.route_id, p.seq, epoch(p.ts) AS t, pat.cum_m
            FROM read_parquet({passages_glob(days)}) p JOIN pat ON pat.route_id = p.route_id AND pat.seq = p.seq
        ), refseq AS (SELECT route_id, mode(seq) AS ref FROM ps GROUP BY route_id),
        rc AS (SELECT r.route_id, r.ref, pat.cum_m AS ref_cum FROM refseq r JOIN pat ON pat.route_id = r.route_id AND pat.seq = r.ref),
        br AS (
            SELECT ps.date, ps.vehicle_id, ps.trip_id, ps.route_id, any_value(rc.ref_cum) AS ref_cum,
                   arg_max(t, ps.seq) FILTER (WHERE ps.seq <= rc.ref) AS t_a, max(cum_m) FILTER (WHERE ps.seq <= rc.ref) AS c_a,
                   arg_min(t, ps.seq) FILTER (WHERE ps.seq >= rc.ref) AS t_b, min(cum_m) FILTER (WHERE ps.seq >= rc.ref) AS c_b
            FROM ps JOIN rc USING (route_id) GROUP BY ALL
        ), arr AS (
            SELECT date, route_id, CASE WHEN c_b = c_a THEN t_a ELSE t_a + (t_b - t_a) * (ref_cum - c_a) / (c_b - c_a) END AS t
            FROM br WHERE t_a IS NOT NULL AND t_b IS NOT NULL
        ), h AS (SELECT date, route_id, t, lead(t) OVER (PARTITION BY date, route_id ORDER BY t) - t AS hw FROM arr)
        SELECT CAST(route_id AS VARCHAR) AS route_id, dt.day_type, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr, hw
        FROM h JOIN daytypes dt USING (date) WHERE hw >= 120 AND hw <= 4 * 3600
    """).df()


def chaining(days, tt: TravelTimeModel) -> tuple[dict, dict]:
    """車両ごとの便の並びから「路線 A の次に走る路線 B」と終点での休憩時間（秒）を学ぶ。"""
    con = C.connect()
    trips = con.execute(f"""
        SELECT date, vehicle_id, trip_id, CAST(route_id AS VARCHAR) AS route_id,
               min(epoch(ts)) AS t_first, max(epoch(ts)) AS t_last, arg_min(seq, ts) AS seq_first, arg_max(seq, ts) AS seq_last
        FROM read_parquet({passages_glob(days)}) GROUP BY ALL
    """).df().sort_values(["date", "vehicle_id", "t_first"])
    nxt = trips.groupby(["date", "vehicle_id"]).shift(-1)
    trips["next_route"] = nxt.route_id
    trips["next_first"] = nxt.t_first
    trips["next_seq_first"] = nxt.seq_first
    trips = trips.dropna(subset=["next_route"])
    trips = trips[trips.route_id.isin(tt.cum) & trips.next_route.isin(tt.cum)]
    trips["gap"] = trips.next_first - trips.t_last
    trips = trips[(trips.gap > 0) & (trips.gap < 3 * 3600)]
    # 終点まで・始点からの未検出部分を過去の平均速度で差し引いて「休憩」を推定（概算）
    def rest(r):
        cum_a, cum_b = tt.cum[r.route_id], tt.cum[r.next_route]
        tail = (cum_a[-1] - cum_a[int(r.seq_last)]) / (17 / 3.6)
        head = (cum_b[int(r.next_seq_first)] - cum_b[0]) / (17 / 3.6)
        return r.gap - tail - head
    trips["layover"] = trips.apply(rest, axis=1)
    pair = trips.groupby(["route_id", "next_route"]).size().rename("n").reset_index()
    tot = pair.groupby("route_id").n.transform("sum")
    pair["share"] = pair.n / tot
    pair = pair[(pair.share >= 0.3) & (pair.n >= 10)]
    lay = trips.merge(pair[["route_id", "next_route"]], on=["route_id", "next_route"]).groupby(
        ["route_id", "next_route"]).layover.median().clip(lower=0)
    feeders = defaultdict(list)    # 自分の路線 B → [(反対の路線 A, 休憩秒, 割合)]
    for (a, b), v in lay.items():
        sh = float(pair[(pair.route_id == a) & (pair.next_route == b)].share.iloc[0])
        feeders[b].append((a, float(v), sh))
    stats = {"pairs": int(len(pair)), "routes_with_feeder": len(feeders),
             "layover_median_min": round(float(lay.median() / 60), 1),
             "share_next_is_paired_%": round(float((trips.merge(pair, on=["route_id", "next_route"]).shape[0]) / len(trips) * 100), 1)}
    return feeders, stats


class Residual:
    """運行間隔 H の分布から、経過時間 e のときの残りの待ち時間 E[H − e | H > e]。"""

    def __init__(self, hw: pd.DataFrame):
        self.h = {k: np.sort(g.hw.to_numpy()) for k, g in hw.groupby(["route_id", "day_type", "hr"])}
        self.h2 = {k: np.sort(g.hw.to_numpy()) for k, g in hw.groupby(["route_id", "day_type"])}

    def __call__(self, rid, dtp, hr, e):
        for H in (self.h.get((rid, dtp, hr)), self.h2.get((rid, dtp))):
            if H is None or len(H) < 5:
                continue
            tail = H[H > e]
            if len(tail) >= 3:
                return float((tail - e).mean())
        return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    tt = TravelTimeModel("train")
    hw = headway_samples(C.TRAIN_DAYS)
    res_fn = Residual(hw)
    feeders, ch_stats = chaining(C.TRAIN_DAYS, tt)
    print("折り返しの組:", ch_stats, flush=True)
    s = pd.read_csv(C.ROOT / "results" / "p1_door_samples.csv", parse_dates=["depart"], dtype={"route_id": str})
    ps = load_test_passages()
    ps["date"] = pd.to_datetime(ps.date).dt.date      # 検索のキー（Python の date）にそろえる
    by_rd = {k: g for k, g in ps.groupby(["route_id", "date"])}
    rows = []
    for r in s.itertuples():
        rid, d = r.route_id, r.depart.date()
        dep = r.depart.to_pydatetime()
        t0 = pd.Timestamp(dep).value / 1e9
        dtp, hr = C.day_type(d), dep.hour
        cum = tt.cum[rid]
        g_r = by_rd.get((rid, d))
        # --- W2: 停留所 i を最後のバスが通った時刻（t0 より前）
        last_pass = None
        if g_r is not None:
            for _, g in g_r.groupby(["vehicle_id", "trip_id"]):
                seqs = g.seq.to_numpy()
                tt_ = g.ts.astype("datetime64[ns]").astype("int64").to_numpy() / 1e9
                if seqs.min() > r.i or seqs.max() < r.i:
                    continue
                ti = float(np.interp(cum[r.i], cum[seqs], tt_))
                if ti < t0 and (last_pass is None or ti > last_pass):
                    last_pass = ti
        e = (t0 - last_pass) if last_pass is not None else None
        w_res = res_fn(rid, dtp, hr, e) if e is not None and e < 4 * 3600 else None
        # --- W4: 反対方向から折り返してくるバス（t0 時点で直近 10 分以内に検出されたもの）
        chain_eta = None
        chain_list = []   # (到着予測の時刻, その組の折り返しの割合)
        for a, lay, sh in feeders.get(rid, []):
            g_a = by_rd.get((a, d))
            if g_a is None:
                continue
            cum_a = tt.cum[a]
            for _, g in g_a.groupby(["vehicle_id", "trip_id"]):
                tt_ = g.ts.astype("datetime64[ns]").astype("int64").to_numpy() / 1e9
                past = tt_ <= t0
                if not past.any():
                    continue
                k = int(g.seq.to_numpy()[past].max())
                t_k = float(tt_[past].max())
                if t0 - t_k > 600:
                    continue
                ts_k = pd.Timestamp(t_k, unit="s").to_pydatetime()
                t_end = t_k + tt.ride_sec(a, k, len(cum_a) - 1, ts_k)
                t_start = t_end + lay
                t_i = t_start + tt.ride_sec(rid, 0, r.i, pd.Timestamp(t_start, unit="s").to_pydatetime())
                if t_i >= t0 - 60:
                    chain_list.append((t_i, sh))
                if t_i >= t0 - 60 and (chain_eta is None or t_i < chain_eta):
                    chain_eta = t_i
        w0 = r.model_wait_s
        w1 = r.realtime_wait_s
        up_found = bool(r.realtime_found)
        w2 = w_res if w_res is not None else w0
        w3 = w1 if up_found else w2
        cands = []
        if up_found:
            cands.append(w1)
        if chain_eta is not None:
            cands.append(max(chain_eta - t0, 0.0))
        w4 = min(cands) if cands else w0
        w5 = min(cands) if cands else w2
        # --- W6: 確率的な組み合わせ。候補ごとに「本当に来る確率」π を付け、見えていないバスは平均 w2 の指数分布とする。
        #     P(W > w) = exp(−w / w2) × Π_{候補 c: 到着 ≤ w} (1 − π_c)。この値が 0.5 を切る最初の w を予測とする（中央値）。
        #     π は事前に決めた値: 手前に見えるバス 0.95、折り返しのバス 0.8 × その組の折り返し割合（検証データでは調整していない）
        cand_p = []
        if up_found:
            cand_p.append((w1, 0.95))
        for t_i, sh in chain_list:
            cand_p.append((max(t_i - t0, 0.0), 0.8 * sh))
        grid = np.arange(0, 4 * 3600, 15.0)
        surv = np.exp(-grid / max(w2, 60.0))
        for w_c, p_c in cand_p:
            surv = surv * np.where(grid >= w_c, 1 - p_c, 1.0)
        w6 = float(grid[np.argmax(surv <= 0.5)]) if (surv <= 0.5).any() else float(grid[-1])
        rows.append(dict(route_id=rid, i=r.i, j=r.j, depart=r.depart, actual_wait=r.actual_wait_s, actual_s=r.actual_s,
                         W0=w0, W1=w1, W2=w2, W3=w3, W4=w4, W5=w5, W6=w6, up=up_found, chain=chain_eta is not None,
                         has_last=e is not None))
    x = pd.DataFrame(rows)
    aw = x.actual_wait.clip(lower=30)
    res = {"chaining": ch_stats,
           "share_upstream_visible_%": round(float(x.up.mean() * 100), 1),
           "share_upstream_or_chain_%": round(float((x.up | x.chain).mean() * 100), 1),
           "share_last_bus_known_%": round(float(x.has_last.mean() * 100), 1)}
    names = {"W0": "過去の実績", "W1": "リアルタイム（今）", "W2": "前のバスからの経過で条件づけ",
             "W3": "リアルタイム→経過で条件づけ", "W4": "リアルタイム＋折り返し", "W5": "リアルタイム＋折り返し→経過で条件づけ",
             "W6": "確率的な組み合わせ"}
    res["wait"] = {names[k]: metrics(aw, x[k]) for k in names}
    # 待ち時間込みの合計（乗車時間は今のモデル）
    t = x.dropna(subset=["actual_s"]).copy()
    for k in names:
        t[f"tot_{k}"] = [w + tt.ride_sec(r.route_id, r.i, r.j, r.depart.to_pydatetime() + timedelta(seconds=w))
                         for w, r in zip(t[k], t.itertuples())]
    res["door_total"] = {names[k]: metrics(t.actual_s, t[f"tot_{k}"]) for k in names}
    # 見え方別
    nv = x[~x.up]
    res["wait_when_no_upstream_bus"] = {names[k]: metrics(nv.actual_wait.clip(lower=30), nv[k]) for k in ["W0", "W2", "W4", "W5", "W6"]}
    (C.ROOT / "results" / "p1_wait_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    x.to_csv(C.ROOT / "results" / "p1_wait_samples.csv", index=False)
    print(json.dumps({k: v for k, v in res.items() if not isinstance(v, dict) or k == "chaining"}, ensure_ascii=False))
    for sec in ["wait", "door_total", "wait_when_no_upstream_bus"]:
        for k, v in res[sec].items():
            print(sec, k, {a: v[a] for a in ["n", "MAE_min", "MedAPE_%", "within20%_%", "median_err_min", "actual_mean_min"]})


if __name__ == "__main__":
    main()
