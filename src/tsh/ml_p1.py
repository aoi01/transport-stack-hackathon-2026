"""問題1を機械学習（LightGBM、勾配ブースティング木）で解き、集計方式と同じ検証で比べる。

設計:
  単位    : リンク（隣り合う停留所の区間）1回の通過
  目的変数: log(実際の所要秒 / 過去の中央値)  … 「いつもより何倍遅いか」を学習する
  特徴量  :
    時刻（時 + 分/60）、曜日、休日フラグ、リンク長
    過去の中央値（リンク × 平日/休日 × 時間帯、平日/休日、全体）・その観測数・ばらつき（75% 点 / 中央値）
    路線別の過去の中央値（リンク × 路線 × 平日/休日 × 時間帯）
    直近の状況: 同じリンクを直近 30 分に通った他のバスの log 比の平均と件数、
                同じ路線の直近 30 分の log 比の平均と件数
  リーク防止:
    過去の中央値は 10/1〜10/17 から作り、10/18〜10/24 の通過で学習する（自分自身を含む集計を特徴量にしない）。
    直近の状況は「その通過の 10 分前までの 30 分間」で作る（予測時に少し古い情報しか無いことに合わせる）。
  検証: 10/25〜31 の 20,000 区間（validate_p1 と同じ）。過去の中央値は 10/1〜24 から、直近の状況は区間の出発時刻まで。
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from collections import defaultdict
from datetime import datetime

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import common as C
from .improve_p1 import OUT as IMP, Probe, Variants, build_tables
from .validate_p1 import metrics

ML = C.PROCESSED / "ml"
LAG = 600      # 直近の情報は 10 分前まで
WIN = 1800     # 30 分間
FEATS = ["hr_f", "dow", "weekend", "link_m", "lh_dt_hr", "ln_dt_hr", "lh_dt", "lh_all", "spread",
         "lh_route", "ln_route", "rec_link", "rec_link_n", "rec_route", "rec_route_n"]


def epoch_ist(y, m, d) -> int:
    return int(pd.Timestamp(year=y, month=m, day=d, tz=C.TZ).timestamp())


def hist_tables(con, t_end: int, prefix: str) -> None:
    src = (f"(SELECT *, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr FROM '{(IMP / 'obs_train.parquet').as_posix()}' "
           f"WHERE t < {t_end})")
    con.execute(f"CREATE OR REPLACE TABLE {prefix}_dt_hr AS SELECT from_stop, to_stop, day_type, hr, "
                f"median(link_s) AS h, count(*) AS n, quantile_cont(link_s, 0.75) AS q75 FROM {src} GROUP BY ALL")
    con.execute(f"CREATE OR REPLACE TABLE {prefix}_dt AS SELECT from_stop, to_stop, day_type, median(link_s) AS h FROM {src} GROUP BY ALL")
    con.execute(f"CREATE OR REPLACE TABLE {prefix}_all AS SELECT from_stop, to_stop, median(link_s) AS h FROM {src} GROUP BY ALL")
    con.execute(f"CREATE OR REPLACE TABLE {prefix}_route AS SELECT route_id, from_stop, to_stop, day_type, hr, "
                f"median(link_s) AS h, count(*) AS n FROM {src} GROUP BY ALL")


def build_training() -> pd.DataFrame:
    out = ML / "train_rows.parquet"
    if out.exists():
        return pd.read_parquet(out)
    ML.mkdir(parents=True, exist_ok=True)
    build_tables()
    con = C.connect()
    t_hist_end = epoch_ist(2026, 10, 18)
    hist_tables(con, t_hist_end, "H")
    obs = (IMP / "obs_train.parquet").as_posix()
    con.execute(f"""
        CREATE TABLE base AS
        WITH o AS (
            SELECT *, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr,
                   hour(timezone('{C.TZ}', to_timestamp(t))) + minute(timezone('{C.TZ}', to_timestamp(t))) / 60.0 AS hr_f,
                   dayofweek(timezone('{C.TZ}', to_timestamp(t))) AS dow
            FROM '{obs}'
        )
        SELECT o.*, (o.day_type = 'weekend')::INT AS weekend,
               a.h AS h_dt_hr, a.n AS ln_dt_hr, a.q75 / a.h AS spread, b.h AS h_dt, c.h AS h_all,
               r.h AS h_route, r.n AS ln_route,
               coalesce(a.h, b.h, c.h, o.link_m / (15 / 3.6)) AS h_ref
        FROM o
        LEFT JOIN H_dt_hr a USING (from_stop, to_stop, day_type, hr)
        LEFT JOIN H_dt b USING (from_stop, to_stop, day_type)
        LEFT JOIN H_all c USING (from_stop, to_stop)
        LEFT JOIN H_route r USING (route_id, from_stop, to_stop, day_type, hr)
    """)
    # 直近の状況（リンク別・路線別）: [t - LAG - WIN, t - LAG) の log 比の平均と件数
    con.execute(f"""
        CREATE TABLE rows AS
        SELECT *,
          avg(lr) OVER wl AS rec_link, count(lr) OVER wl AS rec_link_n,
          avg(lr) OVER wr AS rec_route, count(lr) OVER wr AS rec_route_n
        FROM (SELECT *, ln(link_s / h_ref) AS lr FROM base)
        WINDOW wl AS (PARTITION BY from_stop, to_stop ORDER BY t RANGE BETWEEN {LAG + WIN} PRECEDING AND {LAG} PRECEDING),
               wr AS (PARTITION BY route_id ORDER BY t RANGE BETWEEN {LAG + WIN} PRECEDING AND {LAG} PRECEDING)
    """)
    df = con.execute(f"""
        SELECT * FROM rows WHERE t >= {t_hist_end} USING SAMPLE 4000000 ROWS (reservoir, 42)
    """).df()
    df.to_parquet(out, index=False)
    return df


def to_X(df: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame({
        "hr_f": df.hr_f, "dow": df.dow, "weekend": df.weekend, "link_m": df.link_m,
        "lh_dt_hr": np.log(df.h_dt_hr), "ln_dt_hr": df.ln_dt_hr, "lh_dt": np.log(df.h_dt), "lh_all": np.log(df.h_all),
        "spread": df.spread, "lh_route": np.log(df.h_route), "ln_route": df.ln_route,
        "rec_link": df.rec_link, "rec_link_n": df.rec_link_n, "rec_route": df.rec_route, "rec_route_n": df.rec_route_n,
    })
    return X[FEATS]


def train(df: pd.DataFrame, feats: list[str], tag: str):
    df = df[np.isfinite(df.lr)]
    valid_from = epoch_ist(2026, 10, 24)
    tr, va = df[df.t < valid_from], df[df.t >= valid_from]
    X_tr, X_va = to_X(tr)[feats], to_X(va)[feats]
    params = dict(objective="l1", learning_rate=0.05, num_leaves=127, min_data_in_leaf=200,
                  feature_fraction=0.9, bagging_fraction=0.8, bagging_freq=1, verbose=-1, num_threads=16)
    t0 = time.time()
    m = lgb.train(params, lgb.Dataset(X_tr, tr.lr), 2000, valid_sets=[lgb.Dataset(X_va, va.lr)],
                  callbacks=[lgb.early_stopping(50, verbose=False)])
    print(f"[{tag}] 学習 {len(tr):,} 行・検証 {len(va):,} 行・木 {m.best_iteration} 本・{time.time() - t0:.0f}s", flush=True)
    m.save_model(str(ML / f"lgb_{tag}.txt"))
    return m


class TestFeatures:
    """検証区間の各リンクの特徴量を作る（過去の値は 10/1〜24、直近は区間の出発時刻まで）。"""

    def __init__(self):
        con = C.connect()
        hist_tables(con, epoch_ist(2026, 10, 25), "A")
        def d(sql, k):
            df = con.execute(sql).df()
            return {tuple(r[:k]): tuple(r[k:]) for r in df.itertuples(index=False)}
        self.a = d("SELECT from_stop, to_stop, day_type, hr, h, n, q75 FROM A_dt_hr", 4)
        self.b = d("SELECT from_stop, to_stop, day_type, h FROM A_dt", 3)
        self.c = d("SELECT from_stop, to_stop, h FROM A_all", 2)
        r = con.execute("SELECT CAST(route_id AS VARCHAR), from_stop, to_stop, day_type, hr, h, n FROM A_route").df()
        self.r = {tuple(x[:5]): tuple(x[5:]) for x in r.itertuples(index=False)}
        # 検証週の観測（直近の状況用）: リンク別・路線別に時刻順
        o = pd.read_parquet(IMP / "obs_test.parquet")
        o["hr"] = pd.to_datetime(o.t, unit="s", utc=True).dt.tz_convert(C.TZ).dt.hour
        href = []
        for x in o.itertuples():
            v = self.a.get((x.from_stop, x.to_stop, x.day_type, x.hr))
            h = v[0] if v else (self.b.get((x.from_stop, x.to_stop, x.day_type)) or
                                self.c.get((x.from_stop, x.to_stop)) or (x.link_m / (15 / 3.6),))
            href.append(h if isinstance(h, float) else h[0])
        o["lr"] = np.log(o.link_s / np.array(href))
        o = o[np.isfinite(o.lr)].sort_values("t")
        self.link = defaultdict(lambda: ([], []))
        self.route = defaultdict(lambda: ([], []))
        for x in o.itertuples():
            L = self.link[(x.from_stop, x.to_stop)]; L[0].append(x.t); L[1].append(x.lr)
            R = self.route[str(x.route_id)]; R[0].append(x.t); R[1].append(x.lr)
        self.link = {k: (np.array(v[0]), np.array(v[1])) for k, v in self.link.items()}
        self.route = {k: (np.array(v[0]), np.array(v[1])) for k, v in self.route.items()}

    @staticmethod
    def recent(store, key, t_now):
        v = store.get(key)
        if v is None:
            return np.nan, 0
        ts, lr = v
        lo, hi = np.searchsorted(ts, t_now - WIN), np.searchsorted(ts, t_now)
        if hi <= lo:
            return np.nan, 0
        return float(lr[lo:hi].mean()), int(hi - lo)

    def segment_rows(self, rid, ids, cum, i, j, t0: datetime, t_now: float, href_fn):
        dt = C.day_type(t0.date())
        dow = (t0.weekday() + 1) % 7   # duckdb の dayofweek（日曜=0）に合わせる
        rr, rn = self.recent(self.route, rid, t_now)
        rows = []
        for q in range(i, j):
            a, b, m = ids[q], ids[q + 1], cum[q + 1] - cum[q]
            rows.append(dict(a=a, b=b, link_m=m, dt=dt, dow=dow, weekend=int(dt == "weekend"),
                             rec_route=rr, rec_route_n=rn, rec=self.recent(self.link, (a, b), t_now)))
        return rows

    def feat(self, row, rid, hr, hr_f):
        a, b, dt = row["a"], row["b"], row["dt"]
        va = self.a.get((a, b, dt, hr))
        hb = self.b.get((a, b, dt)); hc = self.c.get((a, b))
        hr_ = self.r.get((rid, a, b, dt, hr))
        h_ref = (va[0] if va else (hb[0] if hb else (hc[0] if hc else row["link_m"] / (15 / 3.6))))
        f = {"hr_f": hr_f, "dow": row["dow"], "weekend": row["weekend"], "link_m": row["link_m"],
             "lh_dt_hr": np.log(va[0]) if va else np.nan, "ln_dt_hr": va[1] if va else np.nan,
             "lh_dt": np.log(hb[0]) if hb else np.nan, "lh_all": np.log(hc[0]) if hc else np.nan,
             "spread": (va[2] / va[0]) if va and va[2] is not None else np.nan,
             "lh_route": np.log(hr_[0]) if hr_ else np.nan, "ln_route": hr_[1] if hr_ else np.nan,
             "rec_link": row["rec"][0], "rec_link_n": row["rec"][1],
             "rec_route": row["rec_route"], "rec_route_n": row["rec_route_n"]}
        return f, h_ref


def evaluate(models: dict) -> dict:
    var = Variants()
    s = pd.read_csv(C.ROOT / "results" / "p1_ride_samples.csv", parse_dates=["t_i", "t_j"], dtype={"route_id": str})
    s = s[s.route_id.isin(var.ids.keys())].reset_index(drop=True)
    tf = TestFeatures()
    t_ep = (s.t_i.dt.tz_localize(C.TZ).dt.tz_convert("UTC").astype("int64") // 10**9).to_numpy()
    preds = {k: [] for k in models}
    for n, r in enumerate(s.itertuples()):
        ids, cum = var.ids[r.route_id], var.cum[r.route_id]
        t0 = r.t_i.to_pydatetime()
        rows = tf.segment_rows(r.route_id, ids, cum, r.i, r.j, t0, t_ep[n], None)
        for name, (m, feats) in models.items():
            tot = 0.0
            s0 = t0.hour * 3600 + t0.minute * 60 + t0.second
            for row in rows:   # 時刻を進めながら1リンクずつ予測
                t = s0 + tot
                hr = int(t // 3600) % 24
                f, h_ref = tf.feat(row, r.route_id, hr, (t / 3600) % 24)
                x = np.array([[f[k] for k in feats]], dtype=float)
                tot += h_ref * float(np.exp(m.predict(x, num_threads=1)[0]))
            preds[name].append(tot)
        if n % 5000 == 0:
            print(f"  評価 {n:,}/{len(s):,}", flush=True)
    res = {name: metrics(s.actual_s, p) for name, p in preds.items()}
    s = s.assign(**{f"pred_{k}": v for k, v in preds.items()})
    s.to_csv(C.ROOT / "results" / "p1_ml_samples.csv", index=False)
    return res


def build_training_loo() -> pd.DataFrame:
    """条件をそろえた版: 10/1〜24 の全日を学習に使う。過去の値は「その行の日を除いた残りの日」から作る（1日抜き）。
    中央値は1日抜きで計算しにくいので、対数の平均（幾何平均）を使う: (全体の和 - その日の和) / (全体の件数 - その日の件数)。"""
    out = ML / "train_rows_loo.parquet"
    if out.exists():
        return pd.read_parquet(out)
    con = C.connect()
    obs = (IMP / "obs_train.parquet").as_posix()
    con.execute(f"""
        CREATE TABLE o AS SELECT *, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr,
               hour(timezone('{C.TZ}', to_timestamp(t))) + minute(timezone('{C.TZ}', to_timestamp(t))) / 60.0 AS hr_f,
               dayofweek(timezone('{C.TZ}', to_timestamp(t))) AS dow,
               CAST(timezone('{C.TZ}', to_timestamp(t)) AS DATE) AS d, ln(link_s) AS ls
        FROM '{obs}' WHERE link_s > 0
    """)
    for name, keys in {"a": "from_stop, to_stop, day_type, hr", "b": "from_stop, to_stop, day_type",
                       "c": "from_stop, to_stop", "r": "route_id, from_stop, to_stop, day_type, hr"}.items():
        con.execute(f"CREATE TABLE {name}_tot AS SELECT {keys}, sum(ls) AS s, sum(ls*ls) AS s2, count(*) AS n FROM o GROUP BY ALL")
        con.execute(f"CREATE TABLE {name}_day AS SELECT {keys}, d, sum(ls) AS s, sum(ls*ls) AS s2, count(*) AS n FROM o GROUP BY ALL")
    def loo(name, keys):
        on = " AND ".join(f"x.{k.strip()} = T.{k.strip()}" for k in keys.split(","))
        ond = on.replace("T.", "D.") + " AND D.d = x.d"
        return (f"LEFT JOIN {name}_tot T ON {on} LEFT JOIN {name}_day D ON {ond}",
                f"(T.s - coalesce(D.s,0)) / NULLIF(T.n - coalesce(D.n,0), 0)",
                f"(T.n - coalesce(D.n,0))",
                f"(T.s2 - coalesce(D.s2,0))")
    parts = {n: loo(n, k) for n, k in {"a": "from_stop, to_stop, day_type, hr", "b": "from_stop, to_stop, day_type",
                                       "c": "from_stop, to_stop", "r": "route_id, from_stop, to_stop, day_type, hr"}.items()}
    sel = []
    joins = []
    for n, (j, mean, cnt, s2) in parts.items():
        joins.append(j.replace(" T ", f" T{n} ").replace("T.", f"T{n}.").replace(" D ", f" D{n} ").replace("D.", f"D{n}."))
        sel.append(f"{mean.replace('T.', f'T{n}.').replace('D.', f'D{n}.')} AS m_{n}")
        sel.append(f"{cnt.replace('T.', f'T{n}.').replace('D.', f'D{n}.')} AS n_{n}")
    con.execute(f"""
        CREATE TABLE rows0 AS
        SELECT x.*, {", ".join(sel)}
        FROM (SELECT * FROM o USING SAMPLE 3000000 ROWS (reservoir, 7)) x {" ".join(joins)}
    """)
    df = con.execute("SELECT * FROM rows0").df()
    df["h_dt_hr"] = np.exp(df.m_a).where(df.n_a > 0)
    df["ln_dt_hr"] = df.n_a
    df["h_dt"] = np.exp(df.m_b).where(df.n_b > 0)
    df["h_all"] = np.exp(df.m_c).where(df.n_c > 0)
    df["h_route"] = np.exp(df.m_r).where(df.n_r > 0)
    df["ln_route"] = df.n_r
    df["spread"] = np.nan
    df["weekend"] = (df.day_type == "weekend").astype(int)
    h_ref = df.h_dt_hr.fillna(df.h_dt).fillna(df.h_all).fillna(df.link_m / (15 / 3.6))
    df["lr"] = np.log(df.link_s / h_ref)
    # 直近の状況（全観測から。サンプル行の t より前の窓）
    rec = con.execute(f"""
        WITH base AS (
            SELECT o.from_stop, o.to_stop, o.route_id, o.t,
                   o.ls - coalesce(ln(exp(a.s / a.n)), o.ls) AS lr
            FROM o LEFT JOIN a_tot a USING (from_stop, to_stop, day_type, hr)
        )
        SELECT from_stop, to_stop, route_id, t,
          avg(lr) OVER wl AS rec_link, count(lr) OVER wl AS rec_link_n,
          avg(lr) OVER wr AS rec_route, count(lr) OVER wr AS rec_route_n
        FROM base
        WINDOW wl AS (PARTITION BY from_stop, to_stop ORDER BY t RANGE BETWEEN {LAG + WIN} PRECEDING AND {LAG} PRECEDING),
               wr AS (PARTITION BY route_id ORDER BY t RANGE BETWEEN {LAG + WIN} PRECEDING AND {LAG} PRECEDING)
    """).df()
    df = df.merge(rec.drop_duplicates(["from_stop", "to_stop", "route_id", "t"]),
                  on=["from_stop", "to_stop", "route_id", "t"], how="left")
    df.to_parquet(out, index=False)
    return df


class TestFeaturesGeo(TestFeatures):
    """1日抜きの版に合わせ、検証時の過去の値も幾何平均（10/1〜24 の全体）で作る。"""

    def __init__(self):
        super().__init__()
        con = C.connect()
        src = (f"(SELECT *, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr, ln(link_s) AS ls "
               f"FROM '{(IMP / 'obs_train.parquet').as_posix()}' WHERE link_s > 0)")
        def d(keys, k):
            df = con.execute(f"SELECT {keys}, exp(avg(ls)) AS h, count(*) AS n, NULL AS q FROM {src} GROUP BY ALL").df()
            return {tuple(r[:k]): tuple(r[k:]) for r in df.itertuples(index=False)}
        self.a = d("from_stop, to_stop, day_type, hr", 4)
        self.b = {k: v[:1] for k, v in d("from_stop, to_stop, day_type", 3).items()}
        self.c = {k: v[:1] for k, v in d("from_stop, to_stop", 2).items()}
        r = con.execute(f"SELECT CAST(route_id AS VARCHAR), from_stop, to_stop, day_type, hr, exp(avg(ls)), count(*) "
                        f"FROM {src} GROUP BY ALL").df()
        self.r = {tuple(x[:5]): tuple(x[5:]) for x in r.itertuples(index=False)}

    def feat(self, row, rid, hr, hr_f):
        f, h = super().feat(row, rid, hr, hr_f)
        f["spread"] = np.nan
        return f, h


def main_fair() -> None:
    """条件をそろえた比較（24日分を学習に使う）。"""
    sys.stdout.reconfigure(encoding="utf-8")
    df = build_training_loo()
    df = df[np.isfinite(df.lr)]
    print(f"学習用の行（1日抜き・24日分）: {len(df):,}")
    feats = [f for f in FEATS if f != "spread"]
    valid_from = epoch_ist(2026, 10, 23)
    tr, va = df[df.t < valid_from], df[df.t >= valid_from]
    params = dict(objective="l1", learning_rate=0.05, num_leaves=127, min_data_in_leaf=200,
                  feature_fraction=0.9, bagging_fraction=0.8, bagging_freq=1, verbose=-1, num_threads=16)
    models = {}
    for tag, fs in [("LightGBM 公平版（過去のみ）", [f for f in feats if not f.startswith("rec_")]),
                    ("LightGBM 公平版（過去＋直近）", feats)]:
        m = lgb.train(params, lgb.Dataset(to_X(tr)[fs], tr.lr), 3000,
                      valid_sets=[lgb.Dataset(to_X(va)[fs], va.lr)], callbacks=[lgb.early_stopping(50, verbose=False)])
        print(f"[{tag}] 木 {m.best_iteration} 本", flush=True)
        models[tag] = (m, fs)
    global TestFeatures
    orig = TestFeatures
    TestFeatures = TestFeaturesGeo
    try:
        res = evaluate(models)
    finally:
        TestFeatures = orig
    prev = json.loads((C.ROOT / "results" / "p1_ml_metrics.json").read_text(encoding="utf-8"))
    prev.update(res)
    (C.ROOT / "results" / "p1_ml_metrics.json").write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in res.items():
        print(k, v)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "fair":
        return main_fair()
    df = build_training()
    print(f"学習用の行: {len(df):,}")
    no_recent = [f for f in FEATS if not f.startswith("rec_")]
    m1 = train(df, no_recent, "hist_only")
    m2 = train(df, FEATS, "with_recent")
    imp = dict(zip(FEATS, m2.feature_importance("gain").round(0).tolist()))
    res = evaluate({"LightGBM（過去のみ）": (m1, no_recent), "LightGBM（過去＋直近）": (m2, FEATS)})
    base = json.loads((C.ROOT / "results" / "p1_improve_metrics.json").read_text(encoding="utf-8"))
    out = {"集計 V0（最初の版）": base["V0"], f"集計＋直前のバス補正 {base['best']}": base[base["best"]], **res,
           "feature_importance_gain": imp}
    (C.ROOT / "results" / "p1_ml_metrics.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
