"""問題2の改善実験2: 便ごとの検証と、便ごとのばらつき（混雑の確率表示の材料）。

車両番号つきの乗車券（約 51%、路線・時間帯によらずほぼ一定 → ほぼ無作為な半分とみなせる）を、
同じ車両・同じ路線で、発券時刻に走っていた GPS の便に結びつける。便ごと・区間ごとの「乗っていた券の人数 y」を作る
（券の無い便も y=0 として数える。便は GPS で検出された範囲の区間だけを使う）。

検証: 10/1〜24 の便から作った推定で、10/25〜31 の各便・各区間の y を予測し、ポアソン逸脱度と平均絶対誤差で比べる。
  M0 今の方式: 全券の人数 / 便数（crowding.parquet）× 路線の車両番号つきの割合 q
  M1 便ベースのマス平均: マス（路線 × 区間 × 平日/休日 × 時間帯）の y の平均
  M2 M1 を縮小推定: (Σy + α × 親の平均) / (便数 + α)
     親の平均 = 路線 × 区間 × 平日/休日（全時間帯）の平均 × 路線 × 平日/休日の時間帯の形
  M3 M2 の親に、前後 2 区間の平均を混ぜる
  α と組み合わせは 10/1〜17 → 10/18〜24 で選ぶ。
便ごとのばらつき: y はポアソンの「間引き」なので Var(y) = E[y] + p² Var(L)。
  ここから本当の車内人数 L の便ごとのばらつき（変動係数）を推定する → 「座れる確率」などの表示に使える。
"""
from __future__ import annotations

import json
import sys
from datetime import date

import numpy as np
import pandas as pd

from . import common as C
from . import crowding as K
from .traveltime import passages_glob

OUT = C.PROCESSED / "p2_trip"
DAYS_A = [date(2026, 10, d) for d in range(1, 18)]
DAYS_B = [date(2026, 10, d) for d in range(18, 25)]


def trip_segments() -> pd.DataFrame:
    """便 × 区間ごとの y（車両番号つきの券で乗っていた人数）。全期間ぶん作って保存。"""
    out = OUT / "trip_seg.parquet"
    if out.exists():
        return pd.read_parquet(out)
    OUT.mkdir(parents=True, exist_ok=True)
    tk = K.build_tickets()
    tk = tk[(tk.j > tk.i) & tk.vehicle_number.notna()].copy()
    # 発券時刻 → epoch 秒（datetime64 の単位に左右されないように差分で計算）
    tk["ce"] = (tk.created_at - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds()
    con = C.connect()
    con.register("tk", tk[["vehicle_number", "route_id", "ce", "i", "j", "pax"]])
    days = C.TRAIN_DAYS + C.TEST_DAYS
    con.execute(f"""
        CREATE TABLE ps AS SELECT date, vehicle_id, trip_id, CAST(route_id AS VARCHAR) AS route_id, seq, epoch(ts) AS t
        FROM read_parquet({passages_glob(days)})
    """)
    con.execute("""
        CREATE TABLE trips AS
        SELECT date, vehicle_id, trip_id, route_id, min(t) AS t_first, max(t) AS t_last, min(seq) AS smin, max(seq) AS smax,
               min(t) - 600 AS t_key
        FROM ps GROUP BY ALL HAVING max(seq) - min(seq) >= 3
    """)
    # 券 → 便（同じ車両・同じ路線で、発券時刻の直前に始まった便。便の終わり +5 分まで）
    con.execute("""
        CREATE TABLE tk_trip AS
        SELECT tr.date, tr.vehicle_id, tr.trip_id, tk.route_id, tk.i, tk.j, tk.pax
        FROM tk ASOF JOIN trips tr
          ON tk.vehicle_number = tr.vehicle_id AND tk.route_id = tr.route_id AND tk.ce >= tr.t_key
        WHERE tk.ce <= tr.t_last + 300
    """)
    n_tk, n_as = len(tk), con.execute("SELECT count(*) FROM tk_trip").fetchone()[0]
    print(f"車両番号つきの券 {n_tk:,} 枚のうち、GPS の便に結びついた券 {n_as:,} 枚（{n_as / n_tk * 100:.1f}%）", flush=True)
    # 便 × 区間（検出された範囲）と、その区間を通った時刻の時間帯（直前に検出した停留所の時刻）
    con.execute(f"""
        CREATE TABLE ts_ AS
        WITH g AS (
            SELECT tr.date, tr.vehicle_id, tr.trip_id, tr.route_id, k
            FROM trips tr, range(0, 400) r(k) WHERE k >= tr.smin AND k < tr.smax
        ), h AS (
            SELECT g.*, p.t FROM g LEFT JOIN ps p
              ON p.date = g.date AND p.vehicle_id = g.vehicle_id AND p.trip_id = g.trip_id AND p.seq = g.k
        )
        SELECT date, vehicle_id, trip_id, route_id, k,
               hour(timezone('{C.TZ}', to_timestamp(last_value(t IGNORE NULLS) OVER (
                    PARTITION BY date, vehicle_id, trip_id ORDER BY k ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)))) AS hr
        FROM h
    """)
    df = con.execute("""
        WITH y AS (
            SELECT t.date, t.vehicle_id, t.trip_id, k, sum(pax) AS y
            FROM tk_trip t, range(0, 400) r(k) WHERE k >= t.i AND k < t.j GROUP BY ALL
        )
        SELECT s.date, s.vehicle_id, s.trip_id, s.route_id, s.k, s.hr, coalesce(y.y, 0) AS y
        FROM ts_ s LEFT JOIN y USING (date, vehicle_id, trip_id, k)
    """).df()
    df["date"] = pd.to_datetime(df.date).dt.date
    df["day_type"] = df.date.map(C.day_type)
    df.to_parquet(out, index=False)
    return df


def poisson_dev(y, mu) -> float:
    mu = np.clip(mu, 1e-6, None)
    t = np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0.0)
    return float(np.mean(2 * (t - (y - mu))))


def estimates(tr: pd.DataFrame, alpha: float | None, neighbor: bool) -> pd.DataFrame:
    """マスごとの予測値 λ。"""
    key = ["route_id", "k", "day_type", "hr"]
    g = tr.groupby(key).y.agg(["sum", "count"]).reset_index()
    if alpha is None:
        g["lam"] = g["sum"] / g["count"]
        return g
    rk = tr.groupby(["route_id", "k", "day_type"]).y.mean().rename("m_rk")
    rh = tr.groupby(["route_id", "day_type", "hr"]).y.mean().rename("m_rh")
    r = tr.groupby(["route_id", "day_type"]).y.mean().rename("m_r")
    g = g.join(rk, on=["route_id", "k", "day_type"]).join(rh, on=["route_id", "day_type", "hr"]).join(r, on=["route_id", "day_type"])
    parent = g.m_rk * (g.m_rh / g.m_r.where(g.m_r > 0)).fillna(1.0)
    if neighbor:
        g = g.sort_values(key).reset_index(drop=True)
        parent = parent.loc[g.index] if len(parent) == len(g) else parent
        g["raw"] = g["sum"] / g["count"]
        nb = (g.groupby(["route_id", "day_type", "hr"])["raw"]
                .rolling(5, center=True, min_periods=1).mean().reset_index(level=[0, 1, 2], drop=True))
        parent = 0.5 * (g.m_rk * (g.m_rh / g.m_r.where(g.m_r > 0)).fillna(1.0)) + 0.5 * nb.sort_index()
    g["parent"] = parent.fillna(g["sum"] / g["count"])
    g["lam"] = (g["sum"] + alpha * g.parent) / (g["count"] + alpha)
    return g


def predict(est: pd.DataFrame, te: pd.DataFrame, fallback: pd.DataFrame) -> np.ndarray:
    key = ["route_id", "k", "day_type", "hr"]
    m = te[key].merge(est[key + ["lam"]], on=key, how="left")
    fb = te[["route_id", "day_type", "hr"]].merge(fallback, on=["route_id", "day_type", "hr"], how="left").fb
    return m.lam.fillna(fb).fillna(0.0).to_numpy()


def evaluate(tr, te, label) -> dict:
    fallback = tr.groupby(["route_id", "day_type", "hr"]).y.mean().rename("fb").reset_index()
    res = {}
    for name, a, nb in [("M1 便ベースのマス平均", None, False)] + \
                       [(f"M2 縮小 α={a}", a, False) for a in (1, 3, 10, 30)] + \
                       [(f"M3 縮小＋前後区間 α={a}", a, True) for a in (1, 3, 10, 30)]:
        mu = predict(estimates(tr, a, nb), te, fallback)
        res[name] = {"poisson_dev": round(poisson_dev(te.y.to_numpy(), mu), 4),
                     "MAE": round(float(np.abs(te.y - mu).mean()), 4),
                     "corr_trip_seg": round(float(np.corrcoef(te.y, mu)[0, 1]), 4)}
        print(label, name, res[name], flush=True)
    return res


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    df = trip_segments()
    print(f"便 × 区間: {len(df):,}（y の平均 {df.y.mean():.3f}、y>0 の割合 {(df.y > 0).mean() * 100:.1f}%）", flush=True)
    A, B = df[df.date.isin(set(DAYS_A))], df[df.date.isin(set(DAYS_B))]
    tune = evaluate(A, B, "[調整 10/1-17→10/18-24]")
    best = min(tune, key=lambda k: tune[k]["poisson_dev"])
    print("調整で選んだ方法:", best, flush=True)
    TR, TE = df[df.date.isin(set(C.TRAIN_DAYS))], df[df.date.isin(set(C.TEST_DAYS))]
    report = evaluate(TR, TE, "[報告 10/1-24→10/25-31]")
    # M0: 今の方式（全券の人数/便数）× 車両番号つきの割合
    q = K.build_tickets()
    q = q[q.j > q.i].groupby("route_id").vehicle_number.apply(lambda s: s.notna().mean()).rename("q")
    cur = pd.read_parquet(C.PROCESSED / "train" / "crowding.parquet")[["route_id", "seq", "day_type", "hr", "sample_per_trip"]]
    cur = cur.rename(columns={"seq": "k"}).merge(q, left_on="route_id", right_index=True, how="left")
    cur["lam"] = cur.sample_per_trip * cur.q.fillna(0.5)
    fb = TR.groupby(["route_id", "day_type", "hr"]).y.mean().rename("fb").reset_index()
    mu0 = predict(cur, TE, fb)
    report["M0 今の方式"] = {"poisson_dev": round(poisson_dev(TE.y.to_numpy(), mu0), 4),
                          "MAE": round(float(np.abs(TE.y - mu0).mean()), 4),
                          "corr_trip_seg": round(float(np.corrcoef(TE.y, mu0)[0, 1]), 4)}
    print("[報告] M0 今の方式", report["M0 今の方式"], flush=True)
    # 便ごとのばらつき: Var(y) = E[y] + p²Var(L) → 本当の人数 L の変動係数 CV = sqrt(Var(y) − E[y]) / E[y]
    # マスの平均を引いた残りで、平均の大きさ別にまとめる
    key = ["route_id", "k", "day_type", "hr"]
    st = TR.groupby(key).y.agg(["mean", "var", "count"]).reset_index()
    st = st[(st["count"] >= 20) & (st["mean"] > 0)]
    st["bin"] = pd.qcut(st["mean"], 5, duplicates="drop")
    disp = st.groupby("bin", observed=True).apply(
        lambda g: pd.Series({"cells": len(g), "mean_y": g["mean"].mean(),
                             "cv_true_load": float(np.sqrt(max((g["var"] - g["mean"]).mean(), 0)) / g["mean"].mean())}),
        include_groups=False)
    cv_all = float(np.sqrt(max((st["var"] - st["mean"]).mean(), 0)) / st["mean"].mean())
    out = {"trip_segments": int(len(df)), "share_y_pos_%": round(float((df.y > 0).mean() * 100), 1),
           "tuning": tune, "chosen_on_tuning": best, "report": report,
           "between_trip_cv_of_true_load_overall": round(cv_all, 3),
           "between_trip_cv_by_mean_bin": {str(k): {kk: round(float(vv), 3) for kk, vv in v.items()} for k, v in disp.iterrows()}}
    (C.ROOT / "results" / "p2_trip_metrics.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("便ごとの本当の人数のばらつき（変動係数）:", round(cv_all, 3))
    print(disp.round(3).to_string())


if __name__ == "__main__":
    main()
