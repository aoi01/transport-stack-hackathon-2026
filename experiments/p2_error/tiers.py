"""マス（路線 × 区間 × 平日/休日 × 1 時間）の誤差を、学習期間の券の枚数（予測の前に分かる量）の段ごとに見る。

予測の候補:
  A 今の方式            学習期間の 人数 / 便数
  B 需要÷その週の便数    1 日あたりの人数（学習期間）× 検証週の日数 / 検証週に走った便数
  C B ＋ 隣の時間帯の平滑化（β=0.25、調整は run.py）
  D C ＋ 縮小（κ=10）
各段で: 誤差の中央値（検証週の券が 5 枚以上のマス）・ノイズの床・マスの数・人数の割合。
段の境目は調整（10/1〜16 → 10/21〜24）で「誤差の中央値が 10% 以下になる最小の枚数」を探して決め、検証週で確かめる。
"""
from __future__ import annotations

import json

from agg import *  # noqa: F401,F403

EDGES = [0, 10, 30, 100, 200, 300, 500, 1000, 10**9]


def cell_preds(d_fit, g_fit, fit_days, tgt_days, s_tgt, t_tgt):
    """当てる先の各マスに、A〜D の予測を付ける。s_tgt/t_tgt は当てる先の人数と便数（便数は需要÷便数で使う）。"""
    w = day_weights(fit_days, tgt_days, calendar=False, compose=False)
    a = cells_from_daily(d_fit, g_fit, w)
    a = a[a["T"] > 0].copy()
    ndt_fit = pd.Series([C.day_type(x) for x in fit_days]).value_counts()
    ndt_tgt = pd.Series([C.day_type(x) for x in tgt_days]).value_counts()
    a["A"] = a.pax / a["T"]
    sm = apply(a, kappa=0, beta=0.25, dseq=0, dhr=1)["pred"]
    sk = apply(a, kappa=10, beta=0.25, dseq=0, dhr=1)["pred"]
    m = s_tgt.merge(t_tgt, on=["route_id", "day_type", "hr"], how="left")
    m = m.merge(a[K + ["A", "pax", "n", "T"]].rename(columns={"pax": "pax_fit", "n": "n_fit", "T": "T_fit"})
                .assign(sm=sm.values, sk=sk.values), on=K, how="inner")
    m = m[m["T"] > 0]
    m["y"] = m.pax / m["T"]
    per_day = lambda rate: rate * m.T_fit / m.day_type.map(ndt_fit) * m.day_type.map(ndt_tgt) / m["T"]  # noqa: E731
    m["B"] = per_day(m.A); m["C"] = per_day(m.sm); m["D"] = per_day(m.sk)
    return m


def tier_table(m, edges=EDGES, min_n=5):
    rows = []
    m = m.assign(tier=pd.cut(m.n_fit, edges, right=False))
    tot_pax = m.pax.sum()
    for t, x in m.groupby("tier", observed=True):
        x5 = x[x.n >= min_n]
        r = {"学習期間の券（延べ）": str(t), "cells": int(len(x5)), "pax_share_%": round(float(x.pax.sum() / tot_pax * 100), 1)}
        for p in "ABCD":
            r[p] = round(float(((x5[p] - x5.y).abs() / x5.y).median() * 100), 1)
        if "pa" in x5:
            r["floor"] = round(float(((x5.pa - x5.pb).abs() / (x5.pa + x5.pb)).median() * 100), 1)
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    d, g = daily("train")
    # 調整: 10/1〜16 → 10/21〜24
    fit, tgt = [OCT(x) for x in range(1, 17)], [OCT(x) for x in range(21, 25)]
    s_t = seg_sums(d[d.date.isin(set(tgt))], None); t_t = trips_rdh(g[g.date.isin(set(tgt))], None)
    mt = cell_preds(d[d.date.isin(set(fit))], g[g.date.isin(set(fit))], fit, tgt, s_t, t_t)
    tt = tier_table(mt)
    print("調整（10/1〜16 → 10/21〜24）\n", tt.to_string(index=False))
    # 検証: 10/1〜24 → 10/25〜31
    dte, gte = daily("test")
    sh = pd.read_parquet(OUT / "test_split_half.parquet")
    s_te = seg_sums(dte, None).merge(sh, on=K, how="left"); t_te = trips_rdh(gte, None)
    m = cell_preds(d, g, C.TRAIN_DAYS, C.TEST_DAYS, s_te, t_te)
    te = tier_table(m)
    print("検証（10/1〜24 → 10/25〜31）\n", te.to_string(index=False))
    x = m[m.n >= 5]
    overall = {p: round(float(((x[p] - x.y).abs() / x.y).median() * 100), 1) for p in "ABCD"}
    overall["floor"] = round(float(((x.pa - x.pb).abs() / (x.pa + x.pb)).median() * 100), 1)
    overall["cells"] = int(len(x))
    print("全体（検証週の券≥5）:", overall)
    m[K + ["n_fit", "n", "pax", "y", "A", "B", "C", "D", "pa", "pb"]].to_parquet(OUT / "cell_preds_test.parquet", index=False)
    (OUT / "tiers.json").write_text(json.dumps({"tune": tt.to_dict("records"), "test": te.to_dict("records"), "overall": overall},
                                               ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
