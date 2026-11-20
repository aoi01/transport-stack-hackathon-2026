"""分子（人数）と分母（便数）の時間帯の数え方を 2×2 で比べる。
  分子: 買った時刻の時間帯（今）/ 区間を通る時刻の時間帯（問題1の所要時間で乗車からの経過を足す。tsh.improve_p2 の B1）
  分母: 始発を出た時間帯（今）/ 区間を通った時間帯（segtrips.py）
週ごとの安定性（学習期間 → 検証週、検証週の券が 5 枚以上のマス）。所要時間は学習期間のモデルだけを使う。"""
from segtrips import *  # noqa: F401,F403
from tsh import improve_p2 as IP
num = {}
for shift in [False, True]:
    num[shift] = {tag: IP.segment_counts(days, shift) for tag, days in [("tr", C.TRAIN_DAYS), ("te", C.TEST_DAYS)]}
d_tr, g_tr = daily("train"); d_te, g_te = daily("test")
gps = set(g_tr[g_tr.gps].route_id)
den = {}
for tag, g, days in [("tr", g_tr, C.TRAIN_DAYS), ("te", g_te, C.TEST_DAYS)]:
    t_old = trips_rdh(g, None)
    st = cell_T(seg_trips(days, "train" if tag == "tr" else "test"), t_old, gps)
    den[tag] = (t_old, st)
rows = []
for shift in [False, True]:
    for seg_den in [False, True]:
        parts = {}
        for tag in ["tr", "te"]:
            x = num[shift][tag].merge(den[tag][0], on=["route_id", "day_type", "hr"], how="left").merge(den[tag][1], on=K, how="left")
            x["T"] = x["T"].fillna(0)
            x["TT"] = x.T_seg.where(x.T_seg > 0, x["T"]) if seg_den else x["T"]
            x["TT"] = np.fmax(x.TT, 1)
            parts[tag] = x.assign(y=x.pax / x.TT)[K + ["y", "n_tickets"]]
        m = parts["te"].merge(parts["tr"], on=K, suffixes=("_te", "_tr"))
        m = m[m.n_tickets_te >= 5]
        r = (m.y_tr - m.y_te).abs() / m.y_te
        row = {"分子": "区間を通る時刻" if shift else "買った時刻", "分母": "区間を通った便" if seg_den else "始発の時間帯", "cells": len(m),
               "全体": round(r.median() * 100, 1)}
        for lo in [30, 100, 500]:
            row[f"学習の券≥{lo}"] = round(r[m.n_tickets_tr >= lo].median() * 100, 1)
        rows.append(row); print(row, flush=True)
pd.DataFrame(rows).to_csv(OUT / "segtrips2_result.csv", index=False)
