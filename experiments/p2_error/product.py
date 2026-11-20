"""経路検索が実際に使う推定（tsh.crowding2 の便ベース＋縮小、学習期間で作った data/processed/train/crowding_trip.parquet）の
週ごとの安定性を、分子・分母とも「区間を通る時間帯」で数えた検証週の値（全部の券）と比べる。
比べる相手として、集計の方式（tsh.crowding、時間帯の数え方を直したもの）も同じ正解で並べる。拡大係数は比に効かないので、
1 便あたりの標本人数（全電子乗車券に換算）で比べる。"""
from segtrips import *  # noqa: F401,F403
from tsh import improve_p2 as IP
d_tr, g_tr = daily("train"); d_te, g_te = daily("test")
gps = set(g_tr[g_tr.gps].route_id)
def consistent(days, tag, g):
    x = IP.segment_counts(days, True)
    t_old = trips_rdh(g, None)
    st = cell_T(seg_trips(days, tag), t_old, gps)
    x = x.merge(t_old, on=["route_id", "day_type", "hr"], how="left").merge(st, on=K, how="left")
    x["TT"] = np.fmax(x.T_seg.where(x.T_seg > 0, x["T"].fillna(0)), 1)
    return x.assign(y=x.pax / x.TT)
te = consistent(C.TEST_DAYS, "test", g_te)
tr = consistent(C.TRAIN_DAYS, "train", g_tr)
prod = pd.read_parquet(C.PROCESSED / "train" / "crowding_trip.parquet").rename(columns={"k": "seq"})
print("便ベースの列:", prod.columns.tolist())
m = te[K + ["y", "n_tickets"]].merge(tr[K + ["y", "n_tickets"]].rename(columns={"y": "agg_y", "n_tickets": "n_tr"}), on=K, how="left") \
      .merge(prod[K + ["sample_per_trip", "sum"]].rename(columns={"sample_per_trip": "trip"}), on=K, how="left")
m = m[(m.n_tickets >= 5) & m.agg_y.notna() & m.trip.notna() & (m.trip > 0)]
for nm in ["agg_y", "trip"]:
    r = (m[nm] - m.y).abs() / m.y
    print(nm, "cells", len(m), "誤差の中央値", round(r.median() * 100, 1), " 学習の券≥100:", round(r[m.n_tr >= 100].median() * 100, 1),
          " ≥500:", round(r[m.n_tr >= 500].median() * 100, 1), " 偏り(中央値 log)", round(float(np.median(np.log(m[nm] / m.y))), 3))
