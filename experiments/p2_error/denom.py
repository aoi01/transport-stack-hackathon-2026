"""診断: 分母（便数）の時間の区切りのずれがどれだけ誤差を生むか。
券は「買った時刻」の時間帯、便は「始発を出た時刻」の時間帯で数えているので、8:55 に出た便の客は 9 時台の券になる。
両方の期間で、便数を前後 1 時間と均した値（(T[h-1] + 2T[h] + T[h+1]) / 4 の 4/4 倍、合計は保たれる）に替えて、週ごとの安定性を比べる。
※ 正解の定義も変わるので「予測の改善」ではなく、誤差の出どころの診断。"""
from tiers import *  # noqa: F401,F403
d, g = daily("train"); dte, gte = daily("test")
def smooth_T(t):
    t = t.set_index(["route_id", "day_type", "hr"])["T"]
    out = t * 0.5
    for dh in (-1, 1):
        sh = t.rename(lambda h: h - dh, level="hr")
        out = out.add(0.25 * sh.reindex(t.index).fillna(0), fill_value=0)
    return out.rename("T").reset_index()
s_tr, t_tr = seg_sums(d, None), trips_rdh(g, None)
s_te, t_te = seg_sums(dte, None), trips_rdh(gte, None)
for nm, (a, b) in {"今の分母": (t_tr, t_te), "前後1時間で均した分母": (smooth_T(t_tr), smooth_T(t_te))}.items():
    m = s_te.merge(b, on=["route_id", "day_type", "hr"]).merge(
        s_tr.merge(a, on=["route_id", "day_type", "hr"]).rename(columns={"pax": "pax_tr", "n": "n_tr", "T": "T_tr"}), on=K)
    m = m[(m["T"] > 0) & (m.T_tr > 0) & (m.n >= 5)]
    r = ((m.pax_tr / m.T_tr) - (m.pax / m["T"])).abs() / (m.pax / m["T"])
    print(nm, "cells", len(m), "誤差の中央値", round(r.median() * 100, 1),
          " 学習の券≥100:", round(r[m.n_tr >= 100].median() * 100, 1), " ≥500:", round(r[m.n_tr >= 500].median() * 100, 1))
