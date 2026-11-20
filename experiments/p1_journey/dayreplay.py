"""経路全体を「過去の同じ種類の日に、同じ時刻に出ていたら」の再現で予測する（日ごとの再現の中央値）。

今の予測は、区間ごとの予測（待ちの中央値・乗車の中央値）を足し、乗り換えの待ちは「予測した到着時刻」で出す。
待ち時間はバスの来方でとびとびに変わるので、中央値の和は和の中央値と一致しない。
ここでは学習期間（10/1〜24）の同じ平日/休日の各日 k について、
  最初の停留所に歩いて着く → その日に実際に最初に通ったバスに乗る → 乗車時間（今のモデルの中央値）
  → 乗り換えの停留所まで歩く → その日に実際に次に通ったバスに乗る → … → 歩いて目的地
を辿り、日ごとの合計の中央値（や分位点）を予測にする。どの日にも 4 時間以内にバスが来なければその日は除く。

decompose.py の出力（同じ 600 組、評価した全候補と検証週の再現）を使って、
  A. 今の 1 位の案の予測を置き換えたときの誤差
  B. 新しい予測で順位を付け直したときの、選んだ案の実際の所要時間と誤差
を比べる。
使い方: python -X utf8 experiments/p1_journey/dayreplay.py [tag]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.waitmodel import PassageTimetable  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
CAP = 4 * 3600


def next_pass(pt, rid, i, dt, k, sec):
    se = pt.idx.get((str(rid), int(i), dt))
    if se is None:
        return None
    x = pt.v[se[0]:se[1]]
    p = np.searchsorted(x, k * 86400 + sec)
    if p < len(x) and x[p] < (k + 1) * 86400 and x[p] - (k * 86400 + sec) <= CAP:
        return float(x[p] - k * 86400)
    return None


def day_totals(pt, legs, dep_sec, dt, walk_last, keep_fail=False):
    """日ごとの合計。keep_fail=True なら、4 時間以内にバスが来なかった日を inf として残す。"""
    out = []
    for k in pt.days_of[dt]:
        t = dep_sec
        ok = True
        for lg in legs:
            t += lg.walk_before_s
            b = next_pass(pt, lg.route_id, lg.i, dt, k, t)
            if b is None:
                ok = False
                break
            t = b + lg.pred_ride_s
        if ok:
            out.append(t + walk_last - dep_sec)
        elif keep_fail:
            out.append(np.inf)
    return np.asarray(out, float)


def main(tag=""):
    sys.stdout.reconfigure(encoding="utf-8")
    o = pd.read_parquet(OUT / f"options{tag}.parquet")
    lg = pd.read_parquet(OUT / f"legs{tag}.parquet")
    pt = PassageTimetable(C.TRAIN_DAYS)
    lgs = {k: g.sort_values("leg") for k, g in lg.groupby(["pair", "rank"])}
    q = {"med": [], "mean": [], "q60": [], "q75": [], "ndays": [], "all_med": [], "served": [], "all_q85": []}
    for r in o.itertuples():
        legs = list(lgs[(r.pair, r.rank)].itertuples())
        dep = pd.Timestamp(r.depart)
        sec = dep.hour * 3600 + dep.minute * 60 + dep.second
        tall = day_totals(pt, legs, sec, r.day_type, r.walk_last_s, keep_fail=True)
        tot = tall[np.isfinite(tall)]
        # 着けなかった日も入れた中央値（半分以上の日に着けなければ inf）と、着けた日の割合
        q["all_med"].append(float(np.median(tall)) if len(tall) >= 3 else np.nan)
        q["served"].append(float(np.isfinite(tall).mean()) if len(tall) else np.nan)
        q["all_q85"].append(float(np.quantile(tall, 0.85, method="higher")) if len(tall) >= 3 else np.nan)
        n = len(tot)
        q["ndays"].append(n)
        for nm, f in (("med", np.median), ("mean", np.mean), ("q60", lambda x: np.quantile(x, 0.6)),
                      ("q75", lambda x: np.quantile(x, 0.75))):
            q[nm].append(float(f(tot)) if n >= 3 else np.nan)
    for nm, v in q.items():
        o[f"dr_{nm}"] = v
    o.to_parquet(OUT / f"options_dr{tag}.parquet", index=False)

    def m(pred, act):
        e = (pred - act) / act
        return {"n": int(len(act)), "medAPE_%": round(float(np.median(np.abs(e)) * 100), 1),
                "median_rel_err_%": round(float(np.median(e) * 100), 1),
                "mean_err_min": round(float(np.mean(pred - act) / 60), 1),
                "within_15min_%": round(float(np.mean(np.abs(pred - act) <= 900) * 100), 1)}
    res = {}
    top = o[(o["rank"] == 0) & o.actual_s.notna()]
    res["A 1位の案（今の順位）"] = {"今の予測": m(top.pred_s, top.actual_s)}
    for nm in ("med", "mean", "q60", "q75"):
        p = top[f"dr_{nm}"].fillna(top.pred_s)
        res["A 1位の案（今の順位）"][f"日ごとの再現 {nm}"] = m(p, top.actual_s)
    res["A 1位の案（今の順位）"]["日ごとの再現が使えた割合_%"] = round(float(top.dr_med.notna().mean() * 100), 1)
    # B: 順位の付け直し。候補のうち新しい予測が最小の案を選ぶ。選んだ案と今の 1 位が両方再現できた組で比べる
    rows = []
    for pair, g in o.groupby("pair"):
        cur = g[g["rank"] == 0].iloc[0]
        rec = {"pair": pair, "cur_act": cur.actual_s, "cur_pred": cur.pred_s}
        for nm in ("med", "q60", "q75"):
            s = g[f"dr_{nm}"].fillna(g.pred_s)
            c = g.loc[s.idxmin()]
            rec[f"{nm}_act"] = c.actual_s
            rec[f"{nm}_pred"] = s.loc[c.name]
            rec[f"{nm}_same"] = bool(c["rank"] == 0)
        ok = g[g.actual_s.notna()]
        rec["best_act"] = ok.actual_s.min() if len(ok) else np.nan
        rows.append(rec)
    R = pd.DataFrame(rows)
    res["B 付け直し"] = {}
    for nm in ("med", "q60", "q75"):
        both = R[R.cur_act.notna() & R[f"{nm}_act"].notna()]
        res["B 付け直し"][nm] = {
            "1位が変わった組_%": round(float((~R[f"{nm}_same"]).mean() * 100), 1),
            "両方再現できた組": int(len(both)),
            "実際の所要時間の平均（今 → 新, 分）": [round(float(both.cur_act.mean() / 60), 1), round(float(both[f"{nm}_act"].mean() / 60), 1)],
            "今の選び方の誤差": m(both.cur_pred, both.cur_act),
            "新しい選び方の誤差": m(both[f"{nm}_pred"], both[f"{nm}_act"]),
            "新しい選び方（再現できた全組）": m(R[R[f"{nm}_act"].notna()][f"{nm}_pred"], R[R[f"{nm}_act"].notna()][f"{nm}_act"]),
        }
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (OUT / f"dayreplay{tag}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
