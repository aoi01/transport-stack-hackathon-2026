"""需要÷便数の「便数」を、検証週より前に分かるものだけで作っても効くか。
  A  今の方式（学習期間の 人数/便数）
  B* 便数＝検証週に実際に走った数（運行計画が正確か、リアルタイムで数えられる場合の上限）
  B1 便数＝直前の 1 週（10/18〜24）の 1 日あたりの便数 × 検証週の日数
  B2 便数＝直前の 1 週の 1 日あたり × 日数。ただし直前の週にその時間帯の便が無ければ学習期間全体の 1 日あたり
需要（1 日あたりの人数）は学習期間全体（異常日 10/17〜20 を外す版も）から。"""
from tiers import *  # noqa: F401,F403
d, g = daily("train"); dte, gte = daily("test")
sh = pd.read_parquet(OUT / "test_split_half.parquet")
s_te = seg_sums(dte, None).merge(sh, on=K, how="left"); t_te = trips_rdh(gte, None)
last = [OCT(x) for x in range(18, 25)]
ndt = lambda days: pd.Series([C.day_type(x) for x in days]).value_counts()  # noqa: E731
n_te, n_last = ndt(C.TEST_DAYS), ndt(last)
t_last = trips_rdh(g[g.date.isin(set(last))], None).rename(columns={"T": "T_last"})
t_all = trips_rdh(g, None).rename(columns={"T": "T_all"})
rows = []
for cal in [False, True]:
    w = day_weights(C.TRAIN_DAYS, C.TEST_DAYS, calendar=cal, compose=False)
    wdt = pd.Series({dt: sum(v for x, v in w.items() if C.day_type(x) == dt) for dt in ["weekday", "weekend"]})
    nall = pd.Series({dt: sum(1 for x in C.TRAIN_DAYS if C.day_type(x) == dt) for dt in ["weekday", "weekend"]})
    a = cells_from_daily(d, g, w); a = a[a["T"] > 0]
    m = s_te.merge(t_te, on=["route_id", "day_type", "hr"]).merge(a[K + ["pax", "n", "T"]].rename(columns={"pax": "pax_tr", "n": "n_fit", "T": "T_tr"}), on=K)
    m = m.merge(t_last, on=["route_id", "day_type", "hr"], how="left").merge(t_all, on=["route_id", "day_type", "hr"], how="left")
    m = m[m["T"] > 0]; m["y"] = m.pax / m["T"]
    dem = m.pax_tr / m.day_type.map(wdt)                       # 1 日あたりの需要
    sup_last = m.T_last / m.day_type.map(n_last)
    sup_all = m.T_all / m.day_type.map(nall)
    sup_b2 = sup_last.where(sup_last > 0, sup_all)
    preds = {"A": m.pax_tr / m.T_tr, "B*": dem * m.day_type.map(n_te) / m["T"],
             "B1": dem / sup_last.where(sup_last > 0), "B2": dem / sup_b2}
    for nm, p in preds.items():
        for lo, hi, lab in [(0, 10**9, "全体"), (100, 10**9, "学習の券≥100"), (500, 10**9, "学習の券≥500")]:
            x = m[(m.n >= 5) & (m.n_fit >= lo) & (m.n_fit < hi)].assign(p=p)
            x = x[np.isfinite(x.p) & (x.p > 0)]
            rows.append({"異常日を外す": cal, "予測": nm, "マス": lab, "cells": len(x),
                         "median_rel_%": round(float(((x.p - x.y).abs() / x.y).median() * 100), 1),
                         "bias_med_log": round(float(np.median(np.log(x.p / x.y))), 3)})
r = pd.DataFrame(rows)
print(r.pivot_table(index=["異常日を外す", "予測"], columns="マス", values="median_rel_%").to_string())
print(r[r.マス == "全体"].to_string(index=False))
r.to_csv(OUT / "supply.csv", index=False)
