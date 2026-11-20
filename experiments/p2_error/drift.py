"""路線ごとの週ごとの揺れ: 同じ週の中の揺れ（曜日で半分に分ける）と、週をまたいだ揺れを比べる。
人数（分子）と便数（分母）のどちらが揺れるかも分ける。平日だけ（10/5〜9 と 10/12〜16 は異常の無い連続した平日）。"""
from agg import *  # noqa: F401,F403
d, g = daily("train")
dte, gte = daily("test")
d = pd.concat([d, dte]); g = pd.concat([g, gte])
A = [OCT(x) for x in range(5, 10)]; B = [OCT(x) for x in range(12, 17)]; D = [OCT(x) for x in range(26, 31)]
A1 = [OCT(5), OCT(7), OCT(9)]; A2 = [OCT(6), OCT(8)]
def route_level(days):
    w = {x: 1.0 for x in days}
    s = seg_sums(d[d.date.isin(set(days))], w); t = trips_rdh(g[g.date.isin(set(days))], w)
    s = s.groupby("route_id")[["pax", "n"]].sum(); t = t.groupby("route_id")["T"].sum()
    return s.join(t, how="inner").assign(load=lambda x: x.pax / x["T"], pax_d=lambda x: x.pax / len(days), T_d=lambda x: x["T"] / len(days))
def cmp(x, y, name, min_n=200):
    m = x.join(y, lsuffix="_x", rsuffix="_y", how="inner")
    m = m[(m.n_x >= min_n) & (m.n_y >= min_n)]
    out = {"routes": len(m)}
    for c in ["load", "pax_d", "T_d"]:
        out[c] = round(float(np.median(np.abs(np.log(m[f"{c}_x"] / m[f"{c}_y"])))) * 100, 1)
    print(name, out)
ra, rb, rd = route_level(A), route_level(B), route_level(D)
ra1, ra2 = route_level(A1), route_level(A2)
print("中央値 |log 比| (%)。load=1便あたり, pax_d=1日の人数, T_d=1日の便数。券（区間ごとに数えた延べ）200以上の路線")
cmp(ra1, ra2, "同じ週の中（月水金 vs 火木）")
cmp(ra, rb, "隣の週（10/5-9 vs 10/12-16）")
cmp(rb, rd, "2週あと（10/12-16 vs 10/26-30）")
for mn in [1000, 3000]:
    cmp(ra1, ra2, f"同じ週の中 n≥{mn}", mn); cmp(ra, rb, f"隣の週 n≥{mn}", mn)
