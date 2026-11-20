"""便数の変化を路線単位（区分ごと）の比だけで入れる: 予測 = 今の方式 × (学習期間の 1 日あたりの便数 / 当てる先の 1 日あたりの便数)。
当てる先の便数として、直前の 1 週（事前に分かる）と、検証週の実際（リアルタイムで分かる場合）を比べる。"""
from tiers import *  # noqa: F401,F403
d, g = daily("train"); dte, gte = daily("test")
s_te = seg_sums(dte, None); t_te = trips_rdh(gte, None)
last = [OCT(x) for x in range(18, 25)]
ndt = lambda days: pd.Series([C.day_type(x) for x in days]).value_counts()  # noqa: E731
def route_daily(t, days):
    r = t.groupby(["route_id", "day_type"])["T"].sum().reset_index()
    return r.assign(Td=r["T"] / r.day_type.map(ndt(days)))[["route_id", "day_type", "Td"]]
rt_tr = route_daily(trips_rdh(g, None), C.TRAIN_DAYS).rename(columns={"Td": "Td_tr"})
rt_last = route_daily(trips_rdh(g[g.date.isin(set(last))], None), last).rename(columns={"Td": "Td_last"})
rt_te = route_daily(t_te, C.TEST_DAYS).rename(columns={"Td": "Td_te"})
for cal in [False, True]:
    w = day_weights(C.TRAIN_DAYS, C.TEST_DAYS, calendar=cal, compose=False)
    a = cells_from_daily(d, g, w); a = a[a["T"] > 0]
    m = s_te.merge(t_te, on=["route_id", "day_type", "hr"]).merge(a[K + ["pax", "n", "T"]].rename(columns={"pax": "pax_tr", "n": "n_fit", "T": "T_tr"}), on=K)
    m = m.merge(rt_tr, on=["route_id", "day_type"]).merge(rt_last, on=["route_id", "day_type"], how="left").merge(rt_te, on=["route_id", "day_type"], how="left")
    m = m[(m["T"] > 0) & (m.n >= 5)]; m["y"] = m.pax / m["T"]
    A = m.pax_tr / m.T_tr
    for nm, p in {"A": A, "A×路線の便数比（直前の週）": A * m.Td_tr / m.Td_last, "A×路線の便数比（検証週の実際）": A * m.Td_tr / m.Td_te}.items():
        x = m.assign(p=p); x = x[np.isfinite(x.p) & (x.p > 0)]
        r = (x.p - x.y).abs() / x.y
        print(f"異常日を外す={cal}", nm, "cells", len(x), "median", round(r.median() * 100, 1), " 学習の券≥500:", round(r[x.n_fit >= 500].median() * 100, 1))
