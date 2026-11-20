"""分母の定義を直す: 便を「始発を出た時間帯」ではなく「その区間を通った時間帯」で数える。

今の推定は、券の人数を「買った時刻の時間帯」で数え、便数を「始発を出た時刻の時間帯」で数えている。
長い路線では、8:40 に始発を出た便が 9 時台に途中の区間を通り、そこで買われた券は 9 時台に入るので、
分子と分母の時間帯がずれる（区間 k の 9 時台の人数を、8 時台に始発を出た便の数で割ることがある）。

ここでは各便について、GPS で検出できた停留所のうち最初と最後の通過時刻から、停留所あたりの所要時間を出し、
路線の全区間の通過時刻を直線で補って、(路線, 区間, 日, 時間帯) ごとに通った便を数える。
GPS の便が 1 つも無い（路線, 区分, 時間帯）や、今の推定で時刻表の便数を使う路線は、今の便数のまま。

結果: data/processed は触らず、experiments/p2_error/out/seg_trips_{train,test}.parquet に保存し、
週ごとの安定性（学習期間 → 検証週、検証週の券が 5 枚以上のマス）を今の分母と比べる。
"""
from __future__ import annotations

from agg import *  # noqa: F401,F403
from tsh.traveltime import passages_glob

sys.stdout.reconfigure(encoding="utf-8")


def seg_trips(days, tag: str) -> pd.DataFrame:
    out = OUT / f"seg_trips_{tag}.parquet"
    if out.exists():
        return pd.read_parquet(out)
    pat = C.patterns().groupby("route_id").seq.max().rename("nstop").reset_index()   # 区間は 0..nstop-1
    con = C.connect()
    con.register("pat", pat)
    df = con.execute(f"""
        WITH p AS (SELECT CAST(route_id AS VARCHAR) AS route_id, date, vehicle_id, trip_id, seq, epoch(ts) AS t
                   FROM read_parquet({passages_glob(days)})),
             tr AS (SELECT route_id, date, vehicle_id, trip_id,
                           arg_min(seq, t) AS s0, min(t) AS t0, arg_max(seq, t) AS s1, max(t) AS t1
                    FROM p GROUP BY ALL),
             ok AS (SELECT tr.*, pat.nstop, (t1 - t0) / (s1 - s0) AS r FROM tr JOIN pat USING (route_id)
                    WHERE s1 > s0 AND (t1 - t0) / (s1 - s0) BETWEEN 10 AND 900),
             s AS (SELECT route_id, date, k AS seq, t0 + (k - s0) * r AS tk
                   FROM ok, range(0, 400) rr(k) WHERE k < nstop)
        SELECT route_id, seq, date, hour(timezone('{C.TZ}', to_timestamp(tk))) AS hr, count(*) AS trips
        FROM s GROUP BY ALL""").df()
    df["date"] = pd.to_datetime(df.date).dt.date
    df["day_type"] = df.date.map(C.day_type)
    df.to_parquet(out, index=False)
    return df


def cell_T(st: pd.DataFrame, t_old: pd.DataFrame, gps_routes: set) -> pd.DataFrame:
    """(路線, 区間, 区分, 時間帯) の便数。GPS の路線は区間を通った便、それ以外と GPS の便の無い所は今の便数。"""
    a = st.groupby(K).trips.sum().rename("T_seg").reset_index()
    return a[a.route_id.isin(gps_routes)]


def main():
    d_tr, g_tr = daily("train"); d_te, g_te = daily("test")
    gps = set(g_tr[g_tr.gps].route_id)
    st_tr = seg_trips(C.TRAIN_DAYS, "train"); st_te = seg_trips(C.TEST_DAYS, "test")
    s_tr, t_tr = seg_sums(d_tr, None), trips_rdh(g_tr, None)
    s_te, t_te = seg_sums(d_te, None), trips_rdh(g_te, None)
    sh = pd.read_parquet(OUT / "test_split_half.parquet")
    a = s_tr.merge(t_tr, on=["route_id", "day_type", "hr"]).merge(cell_T(st_tr, t_tr, gps), on=K, how="left")
    b = s_te.merge(t_te, on=["route_id", "day_type", "hr"]).merge(cell_T(st_te, t_te, gps), on=K, how="left").merge(sh, on=K, how="left")
    for x in (a, b):
        x["T_new"] = x.T_seg.where(x.T_seg > 0, x["T"])
    m = b.merge(a[K + ["pax", "n", "T", "T_new"]].rename(columns={"pax": "pax_tr", "n": "n_tr", "T": "T_tr", "T_new": "T_new_tr"}), on=K)
    m = m[(m.n >= 5) & (m["T"] > 0) & (m.T_tr > 0)]
    rows = []
    for nm, (pt, pe) in {"今の分母（始発の時間帯）": (m.pax_tr / m.T_tr, m.pax / m["T"]),
                         "区間を通った時間帯の便数": (m.pax_tr / m.T_new_tr, m.pax / m.T_new)}.items():
        r = (pt - pe).abs() / pe
        fl = (m.pa - m.pb).abs() / (m.pa + m.pb)
        row = {"分母": nm, "cells": int(len(m)), "全体": round(float(r.median() * 100), 1), "床": round(float(fl.median() * 100), 1)}
        for lo in [30, 100, 500]:
            row[f"学習の券≥{lo}"] = round(float(r[m.n_tr >= lo].median() * 100), 1)
            row[f"床≥{lo}"] = round(float(fl[m.n_tr >= lo].median() * 100), 1)
        rows.append(row)
    r = pd.DataFrame(rows)
    print(r.to_string(index=False))
    r.to_csv(OUT / "segtrips_result.csv", index=False)
    # 同じ週の中の安定性（曜日で半分）も、分母で比べる（正解の側に検証週を使わない確かめ）
    print("区間を通った便で数えたマスの割合（学習期間、GPS の路線）:", round(float(a.T_seg.notna().mean() * 100), 1), "%")


if __name__ == "__main__":
    main()
