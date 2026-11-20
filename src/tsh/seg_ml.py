"""問題1の改善実験2: 「乗る区間全体（停留所 i → j）」を直接学習する LightGBM と、余裕を見た時間（分位点）。

それまでの方式は、隣り合う停留所の区間（リンク）ごとに予測して足していた。評価しているのは i→j 全体なので、
リンクごとの誤差（互いに相関している）が積み上がる。ここでは i→j 全体を1つの学習例にする。

学習例: 10/1〜24 の実際の便から、検出された停留所 i と 5〜25 停留所先の j を1便につき1組選ぶ（検証と同じ作り方）。
目的変数: log(実際の所要時間 / 過去の推定の合計)
過去の推定: リンク × 平日/休日 × 時間帯 の対数平均（＝幾何平均）。学習例の日を除いた残りの日から作る（1日抜き）。
            検証（10/25〜31）では 10/1〜24 の全日から作る。
特徴量:
  過去の推定の合計（出発時の時間帯 / 次の時間帯 / 平日・休日全体）、リンク数、距離、過去の推定の平均速度、
  過去の推定が細かいマスで取れたリンクの割合、路線別の過去の推定との比、出発時刻・曜日・休日、
  直近の状況: これから通るリンクを直近 30 分に走った他のバスの「いつもとの比」（中央値・平均・件数・時間で重みづけ）、
             乗車停留所より手前 10 リンクの直近の比、同じ路線の直近の比、市内全体の直近の比
モデル: 中央値（L1）、15% 点、85% 点（分位点回帰）
"""
from __future__ import annotations

import json
import sys
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import common as C
from .improve_p1 import OUT as IMP, build_tables
from .traveltime import passages_glob
from .validate_p1 import metrics

OUT = C.PROCESSED / "seg_ml"
TZ = C.TZ
N_TRAIN_SEG = 300_000
FEATS = ["lH0", "r_H1", "r_HD", "n_links", "dist", "v_hist", "cov_hr", "min_n", "r_route", "cov_rt",
         "hr_f", "dow", "weekend",
         "rec_med", "rec_avg", "rec_n", "rec_decay", "up_med", "up_n", "route_avg", "route_n", "city_avg", "city_n"]


def con_with_base(con) -> None:
    pat = C.patterns()[["route_id", "seq", "stop_id", "cum_m"]].copy()
    pat["route_id"] = pat.route_id.astype(int)
    con.register("pat_df", pat)
    con.execute("CREATE OR REPLACE TABLE pat AS SELECT * FROM pat_df")
    for name, path in [("o", IMP / "obs_train.parquet"), ("ot", IMP / "obs_test.parquet")]:
        con.execute(f"""
            CREATE OR REPLACE TABLE {name} AS
            SELECT route_id, day_type, from_stop, to_stop, t, link_s, link_m, ln(link_s) AS ls,
                   hour(timezone('{TZ}', to_timestamp(t))) AS hr,
                   CAST(timezone('{TZ}', to_timestamp(t)) AS DATE) AS d,
                   CAST(floor(t / 1800) AS BIGINT) AS b30,
                   CAST(floor(t / 300) AS BIGINT) AS b5
            FROM '{path.as_posix()}' WHERE link_s > 0
        """)
    # 過去の推定の材料: 全体の和と日ごとの和（1日抜きに使う）
    keys = {"lk": "from_stop, to_stop, day_type, hr", "ld": "from_stop, to_stop, day_type",
            "la": "from_stop, to_stop", "lr": "route_id, from_stop, to_stop, day_type, hr"}
    for n, k in keys.items():
        con.execute(f"CREATE OR REPLACE TABLE {n}_tot AS SELECT {k}, sum(ls) AS S, count(*) AS N FROM o GROUP BY ALL")
        con.execute(f"CREATE OR REPLACE TABLE {n}_day AS SELECT {k}, d, sum(ls) AS S, count(*) AS N FROM o GROUP BY ALL")


def loo(t: str, d: str) -> tuple[str, str]:
    """1日抜きの対数平均と件数（d 側が無ければ全体）"""
    return (f"(({t}.S - coalesce({d}.S, 0)) / NULLIF({t}.N - coalesce({d}.N, 0), 0))",
            f"({t}.N - coalesce({d}.N, 0))")


def build_features(con, seg_table: str, obs_table: str, out_name: str) -> pd.DataFrame:
    """seg_table: sid, route_id, i, j, t0（epoch）, d（IST 日付）, day_type, hr0, hr_f, dow, actual_s"""
    con.execute(f"""
        CREATE OR REPLACE TABLE sl AS
        SELECT s.sid, s.d, s.day_type, s.hr0, s.route_id, p.seq AS k, p.stop_id AS a, p2.stop_id AS b,
               p2.cum_m - p.cum_m AS m
        FROM {seg_table} s JOIN pat p ON p.route_id = s.route_id AND p.seq >= s.i AND p.seq < s.j
        JOIN pat p2 ON p2.route_id = s.route_id AND p2.seq = p.seq + 1
    """)
    m1, n1 = loo("t1", "d1"); m2, _ = loo("t2", "d2"); m3, _ = loo("t3", "d3"); m4, _ = loo("t4", "d4"); m5, n5 = loo("t5", "d5")
    con.execute(f"""
        CREATE OR REPLACE TABLE slh AS
        SELECT sl.*, exp({m1}) AS h_hr, {n1} AS n_hr, exp({m2}) AS h_hr1, exp({m3}) AS h_dt, exp({m4}) AS h_all,
               exp({m5}) AS h_rt, {n5} AS n_rt
        FROM sl
        LEFT JOIN lk_tot t1 ON t1.from_stop = sl.a AND t1.to_stop = sl.b AND t1.day_type = sl.day_type AND t1.hr = sl.hr0
        LEFT JOIN lk_day d1 ON d1.from_stop = sl.a AND d1.to_stop = sl.b AND d1.day_type = sl.day_type AND d1.hr = sl.hr0 AND d1.d = sl.d
        LEFT JOIN lk_tot t2 ON t2.from_stop = sl.a AND t2.to_stop = sl.b AND t2.day_type = sl.day_type AND t2.hr = (sl.hr0 + 1) % 24
        LEFT JOIN lk_day d2 ON d2.from_stop = sl.a AND d2.to_stop = sl.b AND d2.day_type = sl.day_type AND d2.hr = (sl.hr0 + 1) % 24 AND d2.d = sl.d
        LEFT JOIN ld_tot t3 ON t3.from_stop = sl.a AND t3.to_stop = sl.b AND t3.day_type = sl.day_type
        LEFT JOIN ld_day d3 ON d3.from_stop = sl.a AND d3.to_stop = sl.b AND d3.day_type = sl.day_type AND d3.d = sl.d
        LEFT JOIN la_tot t4 ON t4.from_stop = sl.a AND t4.to_stop = sl.b
        LEFT JOIN la_day d4 ON d4.from_stop = sl.a AND d4.to_stop = sl.b AND d4.d = sl.d
        LEFT JOIN lr_tot t5 ON t5.route_id = sl.route_id AND t5.from_stop = sl.a AND t5.to_stop = sl.b AND t5.day_type = sl.day_type AND t5.hr = sl.hr0
        LEFT JOIN lr_day d5 ON d5.route_id = sl.route_id AND d5.from_stop = sl.a AND d5.to_stop = sl.b AND d5.day_type = sl.day_type AND d5.hr = sl.hr0 AND d5.d = sl.d
    """)
    con.execute("""
        CREATE OR REPLACE TABLE segh AS
        WITH x AS (
            SELECT *, coalesce(CASE WHEN n_hr >= 3 THEN h_hr END, h_dt, h_all, m / 4.1667) AS h0,
                      coalesce(h_hr1, h_dt, h_all, m / 4.1667) AS h1,
                      coalesce(h_dt, h_all, m / 4.1667) AS hd
            FROM slh)
        SELECT sid, count(*) AS n_links, sum(m) AS dist, sum(h0) AS H0, sum(h1) AS H1, sum(hd) AS HD,
               avg((coalesce(n_hr, 0) >= 3)::INT) AS cov_hr, min(coalesce(n_hr, 0)) AS min_n,
               sum(CASE WHEN n_rt >= 3 THEN h_rt END) AS HRp, sum(CASE WHEN n_rt >= 3 THEN h0 END) AS H0p,
               avg((coalesce(n_rt, 0) >= 3)::INT) AS cov_rt
        FROM x GROUP BY sid
    """)
    # 観測ごとの「いつもとの比」（観測した日を除いた過去の推定に対して）
    ml, nl = loo("T", "D")
    con.execute(f"""
        CREATE OR REPLACE TABLE olr AS
        SELECT o.route_id, o.from_stop, o.to_stop, o.t, o.b30, o.b5, o.ls - {ml} AS lr
        FROM {obs_table} o JOIN lk_tot T ON T.from_stop = o.from_stop AND T.to_stop = o.to_stop AND T.day_type = o.day_type AND T.hr = o.hr
        LEFT JOIN lk_day D ON D.from_stop = o.from_stop AND D.to_stop = o.to_stop AND D.day_type = o.day_type AND D.hr = o.hr AND D.d = o.d
        WHERE {nl} >= 3
    """)
    con.execute(f"CREATE OR REPLACE TABLE segt AS SELECT sid, route_id, i, t0, CAST(floor(t0 / 1800) AS BIGINT) AS b30, "
                f"CAST(floor(t0 / 300) AS BIGINT) AS b5 FROM {seg_table}")
    # 直近 30 分（30 分ごとの区切りの今と1つ前だけを結合して、時刻で絞る）
    con.execute("""
        CREATE OR REPLACE TABLE rec1 AS
        WITH c AS (
            SELECT sl.sid, x.lr, s.t0 - x.t AS age
            FROM sl JOIN segt s USING (sid)
            JOIN olr x ON x.from_stop = sl.a AND x.to_stop = sl.b AND x.b30 IN (s.b30, s.b30 - 1)
            WHERE x.t >= s.t0 - 1800 AND x.t < s.t0)
        SELECT sid, median(lr) AS rec_med, avg(lr) AS rec_avg, count(*) AS rec_n,
               sum(lr * exp(-age / 900.0)) / sum(exp(-age / 900.0)) AS rec_decay
        FROM c GROUP BY sid
    """)
    con.execute("""
        CREATE OR REPLACE TABLE upl AS
        SELECT s.sid, p.stop_id AS a, p2.stop_id AS b FROM segt s
        JOIN pat p ON p.route_id = s.route_id AND p.seq >= s.i - 10 AND p.seq < s.i
        JOIN pat p2 ON p2.route_id = s.route_id AND p2.seq = p.seq + 1
    """)
    con.execute("""
        CREATE OR REPLACE TABLE rec2 AS
        SELECT u.sid, median(x.lr) AS up_med, count(*) AS up_n
        FROM upl u JOIN segt s USING (sid)
        JOIN olr x ON x.from_stop = u.a AND x.to_stop = u.b AND x.b30 IN (s.b30, s.b30 - 1)
        WHERE x.t >= s.t0 - 1800 AND x.t < s.t0 GROUP BY u.sid
    """)
    con.execute("""
        CREATE OR REPLACE TABLE rec3 AS
        SELECT s.sid, avg(x.lr) AS route_avg, count(*) AS route_n
        FROM segt s JOIN olr x ON x.route_id = s.route_id AND x.b30 IN (s.b30, s.b30 - 1)
        WHERE x.t >= s.t0 - 1800 AND x.t < s.t0 GROUP BY s.sid
    """)
    con.execute("CREATE OR REPLACE TABLE city AS SELECT b5, sum(lr) AS s, count(*) AS n FROM olr GROUP BY b5")
    con.execute("""
        CREATE OR REPLACE TABLE rec4 AS
        SELECT s.sid, sum(c.s) / sum(c.n) AS city_avg, sum(c.n) AS city_n
        FROM segt s, range(1, 7) r(q) JOIN city c ON c.b5 = s.b5 - r.q GROUP BY s.sid
    """)
    df = con.execute(f"""
        SELECT s.*, h.* EXCLUDE (sid), r1.* EXCLUDE (sid), r2.* EXCLUDE (sid), r3.* EXCLUDE (sid), r4.* EXCLUDE (sid)
        FROM {seg_table} s JOIN segh h USING (sid)
        LEFT JOIN rec1 r1 USING (sid) LEFT JOIN rec2 r2 USING (sid) LEFT JOIN rec3 r3 USING (sid) LEFT JOIN rec4 r4 USING (sid)
    """).df()
    df["lH0"] = np.log(df.H0)
    df["r_H1"] = np.log(df.H1 / df.H0)
    df["r_HD"] = np.log(df.HD / df.H0)
    df["v_hist"] = df.dist / df.H0
    df["r_route"] = np.log(df.HRp / df.H0p)
    df["weekend"] = (df.day_type == "weekend").astype(int)
    for c in ["rec_n", "up_n", "route_n", "city_n"]:
        df[c] = df[c].fillna(0)
    df["y"] = np.log(df.actual_s / df.H0)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT / f"{out_name}.parquet", index=False)
    return df


def train_segments(con) -> None:
    """学習用の区間（1便につき1組）を作る。"""
    con.execute(f"""
        CREATE OR REPLACE TABLE ps AS
        SELECT date, vehicle_id, trip_id, route_id, seq, epoch(ts) AS t
        FROM read_parquet({passages_glob(C.TRAIN_DAYS)})
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE seg_tr AS
        WITH tg AS (
            SELECT date, vehicle_id, trip_id FROM ps GROUP BY date, vehicle_id, trip_id HAVING max(seq) - min(seq) >= 5
        ), trips AS (
            SELECT * FROM tg ORDER BY hash(date, vehicle_id, trip_id) LIMIT {N_TRAIN_SEG}
        ), a AS (
            SELECT p.* FROM ps p JOIN trips USING (date, vehicle_id, trip_id)
            QUALIFY row_number() OVER (PARTITION BY date, vehicle_id, trip_id ORDER BY hash(seq, vehicle_id, 17)) = 1
        ), ab AS (
            SELECT a.date, a.vehicle_id, a.trip_id, a.route_id, a.seq AS i, b.seq AS j, a.t AS t0, b.t - a.t AS actual_s
            FROM a JOIN ps b USING (date, vehicle_id, trip_id)
            WHERE b.seq - a.seq BETWEEN 5 AND 25
            QUALIFY row_number() OVER (PARTITION BY a.date, a.vehicle_id, a.trip_id ORDER BY hash(b.seq, 29)) = 1
        )
        SELECT row_number() OVER () AS sid, route_id, i, j, t0, actual_s,
               CAST(timezone('{TZ}', to_timestamp(t0)) AS DATE) AS d,
               hour(timezone('{TZ}', to_timestamp(t0))) AS hr0,
               hour(timezone('{TZ}', to_timestamp(t0))) + minute(timezone('{TZ}', to_timestamp(t0))) / 60.0 AS hr_f,
               dayofweek(timezone('{TZ}', to_timestamp(t0))) AS dow
        FROM ab WHERE actual_s > 0
    """)
    dt = pd.DataFrame({"d": C.TRAIN_DAYS, "day_type": [C.day_type(x) for x in C.TRAIN_DAYS]})
    con.register("dt_df", dt)
    con.execute("CREATE OR REPLACE TABLE seg_train AS SELECT s.*, dt.day_type FROM seg_tr s JOIN dt_df dt USING (d)")


def test_segments(con) -> None:
    s = pd.read_csv(C.RESULTS / "p1_ride_samples.csv", parse_dates=["t_i", "t_j"], dtype={"route_id": str})
    t0 = s.t_i.dt.tz_localize(TZ)
    df = pd.DataFrame({
        "sid": np.arange(len(s)), "route_id": s.route_id.astype(int), "i": s.i, "j": s.j,
        "t0": (t0.dt.tz_convert("UTC").astype("int64") // 10**9).astype(float),
        "actual_s": s.actual_s, "d": s.t_i.dt.date.map(lambda x: pd.Timestamp("1900-01-01").date()),   # 1日抜きを無効に
        "hr0": s.t_i.dt.hour, "hr_f": s.t_i.dt.hour + s.t_i.dt.minute / 60, "dow": (s.t_i.dt.weekday + 1) % 7,
        "day_type": [C.day_type(x.date()) for x in s.t_i],
    })
    con.register("seg_test_df", df)
    con.execute("CREATE OR REPLACE TABLE seg_test AS SELECT * FROM seg_test_df")


def fit(tr: pd.DataFrame, va: pd.DataFrame, obj: dict, feats=FEATS) -> lgb.Booster:
    params = dict(learning_rate=0.03, num_leaves=63, min_data_in_leaf=100, feature_fraction=0.9,
                  bagging_fraction=0.8, bagging_freq=1, lambda_l2=1.0, verbose=-1, num_threads=16, **obj)
    return lgb.train(params, lgb.Dataset(tr[feats], tr.y), 5000, valid_sets=[lgb.Dataset(va[feats], va.y)],
                     callbacks=[lgb.early_stopping(100, verbose=False)])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    build_tables()
    OUT.mkdir(parents=True, exist_ok=True)
    t = time.time()
    con = C.connect()
    con_with_base(con)
    print(f"準備 {time.time() - t:.0f}s", flush=True)
    if (OUT / "train_feats.parquet").exists():
        tr_all = pd.read_parquet(OUT / "train_feats.parquet")
    else:
        train_segments(con)
        tr_all = build_features(con, "seg_train", "o", "train_feats")
    print(f"学習用の区間: {len(tr_all):,}（{time.time() - t:.0f}s）", flush=True)
    test_segments(con)
    te = build_features(con, "seg_test", "ot", "test_feats")
    print(f"検証用の区間: {len(te):,}（{time.time() - t:.0f}s）", flush=True)

    tr_all = tr_all[np.isfinite(tr_all.y)].copy()
    tr_all["d"] = pd.to_datetime(tr_all.d)
    cut = pd.Timestamp("2026-10-23")
    tr, va = tr_all[tr_all.d < cut], tr_all[tr_all.d >= cut]
    res = {}
    preds = {}
    # 過去の推定の合計そのまま（学習なし）
    preds["過去の推定の合計（学習なし）"] = te.H0.to_numpy()
    no_rec = [f for f in FEATS if not (f.startswith("rec_") or f.startswith("up_") or f.startswith("route_") or f.startswith("city_"))]
    models = {}
    for name, feats in [("区間LightGBM（過去のみ）", no_rec), ("区間LightGBM（過去＋直近）", FEATS)]:
        m = fit(tr, va, {"objective": "l1"}, feats)
        models[name] = (m, feats)
        preds[name] = te.H0.to_numpy() * np.exp(m.predict(te[feats]))
        print(f"[{name}] 木 {m.best_iteration} 本", flush=True)
    for name, p in preds.items():
        res[name] = metrics(te.actual_s, p)
        print(name, res[name], flush=True)
    # 分位点（余裕を見た時間）。API で使うので、直近の情報あり（live）・なし（hist）の両方を保存
    q = {}
    for tag, feats in [("live", FEATS), ("hist", no_rec)]:
        for a in (0.15, 0.85):
            m = fit(tr, va, {"objective": "quantile", "alpha": a}, feats)
            q[(tag, a)] = te.H0.to_numpy() * np.exp(m.predict(te[feats]))
            m.save_model(str(OUT / f"lgb_seg_{tag}_q{int(a * 100)}.txt"))
        med = preds["区間LightGBM（過去＋直近）" if tag == "live" else "区間LightGBM（過去のみ）"]
        inside = (te.actual_s >= q[(tag, 0.15)]) & (te.actual_s <= q[(tag, 0.85)])
        res[f"[{tag}] 区間（15%〜85%点）に入った割合_%"] = round(float(inside.mean() * 100), 1)
        res[f"[{tag}] 85%点以内に着いた割合_%"] = round(float((te.actual_s <= q[(tag, 0.85)]).mean() * 100), 1)
        res[f"[{tag}] 85%点 − 中央値（平均, 分）"] = round(float((q[(tag, 0.85)] - med).mean() / 60), 2)
    imp = models["区間LightGBM（過去＋直近）"][0]
    res["feature_importance_gain"] = dict(zip(FEATS, imp.feature_importance("gain").round(0).tolist()))
    models["区間LightGBM（過去＋直近）"][0].save_model(str(OUT / "lgb_seg_live_q50.txt"))
    models["区間LightGBM（過去のみ）"][0].save_model(str(OUT / "lgb_seg_hist_q50.txt"))
    q = {0.15: q[("live", 0.15)], 0.85: q[("live", 0.85)]}
    out = te[["sid", "route_id", "i", "j", "t0", "actual_s", "hr0", "day_type"]].assign(
        **{f"pred_{k}": v for k, v in preds.items()}, q15=q[0.15], q85=q[0.85])
    out.to_csv(C.RESULTS / "p1_segml_samples.csv", index=False)
    (C.RESULTS / "p1_segml_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in res.items():
        if k.startswith("["):
            print(k, v)


if __name__ == "__main__":
    main()
