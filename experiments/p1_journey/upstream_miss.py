"""「手前を走るバス」の到着予測が 2 分以内なのに 10 分以上待った場面は、何が起きていたか（docs 16.7）。

学習期間の中の較正の週（10/18〜24）だけを使う（検証週は見ない）。
ランダムな（路線, 停留所, 出発時刻, 停留所までの徒歩）で、SimLive と同じ規則で「見えていたバス」を選び、
そのバス自身がその後どうなったかを GPS で追う:
  - 停留所 i を、利用者が着く前に通っていた（乗り遅れ）
  - 停留所 i を、着いた後に通った（乗れた）
  - 停留所 i まで GPS で追えない（その便の検出が i より手前で終わった。終点の手前で切れたか、終点まで行ったか）
あわせて、実際に最初に来たバスまでの待ち（Replay と同じ正解）を出す。

python experiments/p1_journey/upstream_miss.py [bridge]
  bridge: 実際に最初に来たバス（正解）を、分かれて記録された便をつないでから作る（docs 16.8）。出力は upstream_miss_bridge.csv
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.planner import Planner  # noqa: E402
from tsh.validate_journeys import CAL_DAYS, Replay, load_passages  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
RNG = np.random.default_rng(7)
N = 6000
OUT = ROOT / "experiments/p1_journey/out"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    pd.set_option("display.width", 220)
    P = Planner("train")
    ps = load_passages(CAL_DAYS)
    bridge = "bridge" in sys.argv[1:]
    rp = Replay(ps, P.tt.cum, tt=P.tt if bridge else None)
    # Replay と同じ時刻の換算で、便ごとに (車両, 便) の名前も持つ。車両ごとの検出の並び（その後どこに現れたか）も作る
    ps["date"] = pd.to_datetime(ps.date).dt.date
    ts_ = pd.to_datetime(ps.ts)
    ts_ = ts_.dt.tz_localize(C.TZ) if ts_.dt.tz is None else ts_
    ps["t"] = ts_.dt.tz_convert("UTC").dt.tz_localize(None).astype("datetime64[ns]").astype("int64") / 1e9
    trips = {}
    for (rid, d), g in ps.groupby(["route_id", "date"]):
        trips[(rid, d)] = [(v, tr, tg.seq.to_numpy(), tg.t.to_numpy())
                           for (v, tr), tg in ((k, x.sort_values("seq")) for k, x in g.groupby(["vehicle_id", "trip_id"]))]
    veh_tl = {k: (g.t.to_numpy(), g.route_id.to_numpy(), g.seq.to_numpy())
              for k, g in ps.sort_values("t").groupby(["date", "vehicle_id"])}
    keys = [k for k in trips if k[0] in P.seq_xy and k[0] in P.tt.cum]
    rows = []
    while len(rows) < N:
        rid, d = keys[int(RNG.integers(len(keys)))]
        n_st = len(P.seq_xy[rid])
        if n_st < 8:
            continue
        i = int(RNG.integers(3, n_st - 2))
        now = datetime(d.year, d.month, d.day) + timedelta(seconds=int(RNG.integers(7 * 3600, 21 * 3600)))
        walk = float(RNG.integers(0, 600))
        now_ep = pd.Timestamp(now, tz=C.TZ).timestamp()
        t_ep = now_ep + walk
        t = now + timedelta(seconds=walk)
        cum = P.tt.cum[rid]
        best = None
        for veh, _trip, seqs, ts in trips[(rid, d)]:
            m = ts <= now_ep
            if not m.any():
                continue
            kk = int(np.argmax(np.where(m, ts, -np.inf)))
            k, tk = int(seqs[kk]), float(ts[kk])
            if now_ep - tk > 600 or k >= i:
                continue
            t_k = datetime.fromtimestamp(tk, IST).replace(tzinfo=None)   # SimLive と同じ
            eta = tk + P.tt.ride_sec(rid, k, i, t_k)
            w = eta - t_ep
            if w >= -60 and (best is None or w < best[0]):
                # このバス自身が停留所 i を通った時刻（検出が i まで届いていれば）
                if seqs.max() >= i:
                    ti = float(np.interp(cum[i], cum[seqs], ts))
                    fate = "passed_before" if ti < t_ep else "passed_after"
                else:
                    ti = None
                    fate = "lost_before_end" if seqs.max() < n_st - 3 else "ended_at_terminus"
                after = None
                if ti is None:
                    # 検出が i より手前で終わった: その車両が次にどこで検出されたか
                    tl_t, tl_r, tl_s = veh_tl[(d, veh)]
                    t_last = float(ts.max())
                    p_ = np.searchsorted(tl_t, t_last, side="right")
                    t_end = t_last + P.tt.ride_sec(rid, int(seqs.max()), n_st - 1, t_k)   # 終点まで走ったら着く時刻
                    if p_ >= len(tl_t) or tl_t[p_] - t_last > 2 * 3600:
                        after = "2時間検出なし"
                    elif tl_r[p_] == rid and tl_s[p_] > seqs.max():
                        # 同じ路線のもっと先で、また検出された（便の名前が分かれただけで、同じ便の続きと見られる）
                        after = "同じ路線の先で続きが検出（i より先）" if tl_s[p_] > i else "同じ路線の先で続きが検出（i より手前）"
                    elif tl_r[p_] == rid:
                        after = "同じ路線の始めのほうにまた現れた"
                    elif tl_t[p_] < t_last + 0.7 * (t_end - t_last):
                        after = "終点に着けない早さで別の路線に現れた"
                    else:
                        after = "終点まで走れる時間の後に別の路線に現れた"
                best = (w, k, now_ep - tk, fate, ti, int(seqs.max()), after)
        if best is None:
            continue
        w, k, age, fate, ti, smax, after = best
        first = rp.ride_detail(rid, d, i, i, t_ep)
        act = (first[0] - t_ep) if first is not None else np.inf
        rows.append({"route_id": rid, "date": d, "i": i, "n_stops": n_st, "k": k, "stops_ahead": i - k,
                     "age_s": age, "w_raw_s": w, "pred_s": max(w, 0.0), "act_s": act,
                     "fate": fate, "bus_at_i_minus_arrival_s": (ti - t_ep) if ti is not None else np.nan,
                     "trip_max_seq": smax, "ride_pred_s": w + walk + age, "after": after})
    df = pd.DataFrame(rows)
    df["late10"] = (df.act_s - df.pred_s) > 600
    df["pb"] = pd.cut(df.pred_s / 60, [-1, 2, 15, 30, 999], labels=["≤2", "2–15", "15–30", ">30"])
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / ("upstream_miss_bridge.csv" if bridge else "upstream_miss.csv"), index=False)
    print(f"見えていたバスがあった場面 {len(df)} 件（較正の週、ランダム）")
    g = df.groupby("pb", observed=True)
    print(pd.DataFrame({"n": g.size(), "10分以上長い_%": (g.late10.mean() * 100).round(1)}))
    print("\n== 予測した待ち × そのバスがどうなったか（行ごとの割合 %）")
    print((pd.crosstab(df.pb, df.fate, normalize="index") * 100).round(1))
    print("\n== 10 分以上長かった場面だけ: そのバスがどうなったか（%）")
    print((pd.crosstab(df[df.late10].pb, df[df.late10].fate, normalize="index") * 100).round(1))
    print("\n== 予測が 2 分以内: 生の到着予測（停留所に着く時刻との差、秒）ごとの、乗り遅れと 10 分以上長い割合")
    s = df[df.pb == "≤2"].copy()
    s["wb"] = pd.cut(s.w_raw_s, [-61, -30, 0, 30, 60, 120])
    gs = s.groupby("wb", observed=True)
    print(pd.DataFrame({"n": gs.size(), "乗り遅れ_%": (gs.fate.apply(lambda x: (x == "passed_before").mean()) * 100).round(1),
                        "追えない_%": (gs.fate.apply(lambda x: x.str.startswith(("lost", "ended")).mean()) * 100).round(1),
                        "10分以上長い_%": (gs.late10.mean() * 100).round(1)}))
    print("\n== そのバスが停留所 i を実際に通った時刻 − 予測した到着（秒）: 通ったバスだけ")
    df["eta_err_s"] = df.bus_at_i_minus_arrival_s - df.w_raw_s
    for pb, x in df[df.fate.str.startswith("passed")].groupby("pb", observed=True):
        q = x.eta_err_s.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(0).tolist()
        print(f"  {pb}: n={len(x)} 分位点(10/25/50/75/90%) {q}")
    print("\n== 位置の古さ（秒）・手前の停留所数ごとの、10 分以上長い割合（予測 2〜15 分）")
    m = df[df.pb == "2–15"].copy()
    print("\n== 検出が i より手前で終わったバス: その車両は次にどこに現れたか（%）。全部 / 10 分以上長かった場面")
    lo = df[df.fate == "lost_before_end"]
    print(pd.concat({"全部": lo.after.value_counts(normalize=True), "10分以上長い": lo[lo.late10].after.value_counts(normalize=True)},
                    axis=1).mul(100).round(1))
    m["ab"] = pd.cut(m.age_s, [-1, 60, 180, 300, 600])
    print((m.groupby("ab", observed=True).late10.agg(["size", "mean"])).round(3))


if __name__ == "__main__":
    main()
