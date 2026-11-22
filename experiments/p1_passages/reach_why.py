"""見えているバスが乗る停留所まで来なかったとき、その走りがなぜ終わったか（検証週）。

終点（最後の停留所）まで行かずに終わった走りを、その後の 30 分で分ける（上から順に当てはめる）:
  A 終点まで行っていた（通過の検出漏れ）: 走りの終わりから 30 分以内（次の走りの前まで）に GPS が終点の 500 m 以内に来た
  B 折り返し: 次の走りが 30 分以内に、同じ系統の逆向きで始まった
  C 別の路線へ: 次の走りが 30 分以内に、別の系統で始まった
  D 同じ路線の続き（つなぎ漏れ）: 次の走りが 30 分以内に、同じ路線のもっと先から始まった
  E GPS は出ているが通過が無い: 30 分に GPS が 20 点以上あり、次の走りが無い。終わった場所から 1 km 以上離れた（路線の外へ）/ 離れていない（止まっている）
  F GPS が途切れた: 30 分の GPS が 20 点未満で、次の走りが無い
利用者に効く重みにするため、「ランダムな時点で停留所 k にいる走り、その 1〜40 停留所先の停留所 i」を引き、
i まで来なかったものの理由を数える（時刻は 7〜21 時）。
使い方: PYTHONPATH=src python experiments/p1_passages/reach_why.py
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from tsh import common as C
from tsh.traveltime import TravelTimeModel

from runs_lib import IST, build_day, route_meta

WIN = 1800
RNG = np.random.default_rng(11)


def classify_day(con, d, runs, cum, xy, line):
    L = runs.route_id.map(lambda r: len(cum[r]) if r in cum else np.nan)
    runs = runs[L.notna()].copy()
    runs["L"] = L[L.notna()].astype(int)
    nx = runs.groupby("vehicle_id")[["route_id", "smin", "t0"]].shift(-1)
    runs["n_route"], runs["n_smin"], runs["n_t0"] = nx.route_id, nx.smin, nx.t0
    end = runs[runs.smax < runs.L - 1].copy()
    end["left_m"] = [cum[r][-1] - cum[r][s] for r, s in zip(end.route_id, end.smax)]
    end["k"] = np.arange(len(end))
    end["elat"] = [xy[r][s, 0] for r, s in zip(end.route_id, end.smax)]
    end["elng"] = [xy[r][s, 1] for r, s in zip(end.route_id, end.smax)]
    end["tlat"] = [xy[r][-1, 0] for r in end.route_id]
    end["tlng"] = [xy[r][-1, 1] for r in end.route_id]
    end["w1"] = np.minimum(end.t1 + WIN, end.n_t0.fillna(np.inf))
    con.register("ends", end[["k", "vehicle_id", "t1", "w1", "elat", "elng", "tlat", "tlng"]])
    g = con.execute(f"""
        select e.k, count(*) n_pts,
               min(sqrt(pow((g.lat-e.tlat)*110540,2)+pow((g.lng-e.tlng)*97800,2))) to_term_m,
               max(sqrt(pow((g.lat-e.elat)*110540,2)+pow((g.lng-e.elng)*97800,2))) from_end_m
        from ends e join '{C.ROOT / "data/interim/bus_gps"}/date={d}/*.parquet' g
          on g.vehicle_id = e.vehicle_id and epoch(g.ts) > e.t1 and epoch(g.ts) < e.w1
        group by e.k""").df()
    end = end.merge(g, on="k", how="left")
    end["n_pts"] = end.n_pts.fillna(0)
    gap = end.n_t0 - end.t1
    soon = gap.notna() & (gap <= WIN)
    same_line = end.n_route.map(lambda r: line.get(r) if isinstance(r, str) else None) == end.route_id.map(line)
    reason = np.select(
        [end.to_term_m <= 500,
         soon & same_line & (end.n_route != end.route_id),
         soon & ~same_line,
         soon & (end.n_route == end.route_id) & (end.n_smin >= end.smax),
         soon,
         (end.n_pts >= 20) & (end.from_end_m >= 1000),
         end.n_pts >= 20],
        ["A 終点まで行っていた（検出漏れ）", "B 折り返し", "C 別の路線へ", "D 同じ路線の続き（つなぎ漏れ）",
         "D' 同じ路線で戻って始まる", "E1 GPS あり・路線の外へ", "E2 GPS あり・止まっている"],
        "F GPS が途切れた")
    end["reason"] = reason
    return runs, end


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con = C.connect()
    cum, xy, line = route_meta()
    tt = TravelTimeModel("train")
    samples, ends_all = [], []
    for d in C.TEST_DAYS:
        runs = build_day(d, tt)
        runs, end = classify_day(con, d, runs, cum, xy, line)
        ends_all.append(end.drop(columns=["seqs", "ts"]))
        rmap = dict(zip(zip(end.vehicle_id, end.run), zip(end.reason, end.left_m)))
        arr = runs.reset_index(drop=True)
        n = 0
        while n < 6000:
            r = arr.iloc[int(RNG.integers(len(arr)))]
            q = int(RNG.integers(len(r.seqs)))
            k, now = int(r.seqs[q]), float(r.ts[q])
            h = ((now + IST) % 86400) / 3600
            if not 7 <= h < 21 or k >= r.L - 2:
                continue
            i = int(min(r.L - 1, k + int(RNG.integers(1, 41))))
            reached = r.smax >= i
            why, left = rmap.get((r.vehicle_id, r.run), (None, None))
            # i が終点の手前の検出漏れ区間（走りの終わりより先）にあるか
            samples.append({"date": d, "route_id": r.route_id, "k": k, "i": i, "L": r.L, "hour": int(h),
                            "reached": bool(reached), "reason": None if reached else why,
                            "i_left_m": cum[r.route_id][-1] - cum[r.route_id][i]})
            n += 1
        print(d, len(runs), "走り", len(end), "途中で終わり", flush=True)
    s = pd.DataFrame(samples)
    e = pd.concat(ends_all)
    s.to_pickle(C.RESULTS / "reach_why_samples.pkl"); e.to_pickle(C.RESULTS / "reach_why_ends_samples.pkl")
    nr = s[~s.reached]
    res = {"引いた組": len(s), "来なかった_%": round(float((~s.reached).mean()) * 100, 1),
           "来なかった理由_%": (nr.reason.value_counts(normalize=True) * 100).round(1).to_dict(),
           "来なかった理由_乗る停留所が終点から 2 km 以内か_%": {
               "2 km 以内": (nr[nr.i_left_m <= 2000].reason.value_counts(normalize=True) * 100).round(1).to_dict(),
               "2 km より先": (nr[nr.i_left_m > 2000].reason.value_counts(normalize=True) * 100).round(1).to_dict(),
               "2 km 以内の割合_%": round(float((nr.i_left_m <= 2000).mean()) * 100, 1)},
           "時間帯ごとの来なかった_%": (s.groupby(pd.cut(s.hour, [7, 10, 16, 20, 21], right=False), observed=True).reached
                                    .apply(lambda x: round(float((~x).mean()) * 100, 1))).rename(index=str).to_dict(),
           "途中で終わった走りの理由_%（走りの数で）": (e.reason.value_counts(normalize=True) * 100).round(1).to_dict(),
           "途中で終わった走り_終点までの残り_中央値_km": (e.groupby("reason").left_m.median() / 1000).round(2).to_dict()}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (C.RESULTS / "reach_why.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
