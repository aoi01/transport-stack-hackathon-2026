"""問題2 改良版: 公表値にもとづく拡大、車両の種類ごとの定員、便ごとのばらつきを入れた「混雑の確率」。

(1) 拡大係数を分解して決める（docs 12章、reports/所要時間と混雑推定の精度改善策.md）:
      全乗客 = 照合できた電子乗車券の人数 × 1/照合率 × 1/(有料乗客に占める電子乗車券の割合) × 1/(1 − 無料乗車の割合)
    中央値は、公表の1日利用者数（FY2024-25: DTC 25.58 lakh + クラスター 15.25 lakh = 約 408 万人）に合わせる。
    幅: 電子乗車券の割合 3〜4%、女性の無料乗車の割合 33〜51%（2020-21〜2025 の公表値・報道の幅）。
(2) 定員は車両の種類ごと（デリー経済調査・車両メーカーの値）:
      CNG 12m（DL1PD4/5…、冷房なし・一部冷房）: 座席 40、定員 64（立席は電気 12m と同じと仮定）
      電気 12m: 座席 39、定員 63 / 電気 9m（DEVI）: 座席 23、定員 36
    車両番号から 12m と 9m は区別できないので、電気バスは 2026年3月の台数比（12m 2,750 : 9m 1,588）で混ぜる。
    路線ごとの CNG と電気の割合は、10 月の GPS で実際に走った便から求める。
(3) 便ごとのばらつき: 本当の車内人数 L は便ごとにばらつく（tsh.p2_trip で変動係数 CV を推定）。
    L ~ ガンマ分布（平均 μ、形 k）。推定の不確かさ（券の枚数 n）も足して 1/k = CV² + 1/n とする。
    P(座れる) = Σ_種類 w × P(L ≤ 座席)、P(混雑) = Σ w × P(L > 定員)、P(立つ) = 残り。
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import gamma

from . import common as C
from . import crowding as K

OFFICIAL_DAILY = 4_083_000          # FY2024-25 DTC 25.58 lakh + クラスター 15.25 lakh
FREE_SHARE = (0.33, 0.42, 0.51)     # 女性の無料乗車の割合（低・中・高）
ETICKET_SHARE = (0.04, 0.0375, 0.03)  # 有料乗客に占める電子乗車券の割合（係数が小さくなる順）
CAP = {"cng12": (40, 64), "e12": (39, 63), "e9": (23, 36)}
E9_SHARE = 1588 / (2750 + 1588)


def route_fleet_mix() -> pd.DataFrame:
    out = C.PROCESSED / "route_fleet.parquet"
    if out.exists():
        return pd.read_parquet(out)
    from .traveltime import passages_glob
    con = C.connect()
    df = con.execute(f"""
        WITH t AS (SELECT DISTINCT date, vehicle_id, trip_id, CAST(route_id AS VARCHAR) AS route_id
                   FROM read_parquet({passages_glob(C.TRAIN_DAYS + C.TEST_DAYS)}))
        SELECT route_id, avg((vehicle_id LIKE 'DL1PD4%' OR vehicle_id LIKE 'DL1PD5%')::INT) AS cng_share, count(*) AS trips
        FROM t GROUP BY route_id
    """).df()
    df.to_parquet(out, index=False)
    return df


def factors(tk: pd.DataFrame) -> dict:
    days = tk.date.nunique()
    all_pax = tk.pax.sum() / days
    matched = tk[tk.j > tk.i].pax.sum() / days
    match_rate = matched / all_pax
    central = OFFICIAL_DAILY / matched
    lo = 1 / match_rate / ETICKET_SHARE[0] / (1 - FREE_SHARE[0])
    hi = 1 / match_rate / ETICKET_SHARE[2] / (1 - FREE_SHARE[2])
    return {"e_ticket_pax_per_day": round(all_pax), "matched_pax_per_day": round(matched),
            "match_rate": round(match_rate, 3), "expansion_central": round(central, 1),
            "expansion_low": round(lo, 1), "expansion_high": round(hi, 1),
            "implied_paid_eticket_share_at_42pct_free_%": round(all_pax / (OFFICIAL_DAILY * (1 - 0.42)) * 100, 2),
            "old_expansion": round(K.EXPANSION, 1)}


ALPHA = 30.0   # 縮小の強さ（tsh.p2_trip で 10/1〜17 → 10/18〜24 の便ごとの予測が最も良かった値）


def trip_based_cells(days) -> pd.DataFrame:
    """便ベース＋縮小推定のマス（tsh.p2_trip の M2）。λ は車両番号つきの券で 1 便あたり乗っていた人数。"""
    from .p2_trip import estimates, trip_segments
    ts = trip_segments()
    ts = ts[ts.date.isin(set(days))]
    e = estimates(ts, ALPHA, False)
    q = K.build_tickets()
    q = q[q.j > q.i].groupby("route_id").vehicle_number.apply(lambda s: s.notna().mean()).rename("q")
    e = e.merge(q, left_on="route_id", right_index=True, how="left")
    e["q"] = e.q.fillna(0.515).clip(lower=0.2)
    e["sample_per_trip"] = e.lam / e.q            # 全電子乗車券に換算した 1 便あたりの人数
    return e


class CrowdingModel2:
    def __init__(self, tag: str = "all", cv: float | None = None):
        days = C.TRAIN_DAYS + C.TEST_DAYS if tag == "all" else C.TRAIN_DAYS
        cache = C.PROCESSED / tag / "crowding_trip.parquet"
        if cache.exists():
            a = pd.read_parquet(cache)
        else:
            a = trip_based_cells(days)
            a.to_parquet(cache, index=False)
        tk = K.build_tickets()
        self.f = factors(tk)
        mix = route_fleet_mix().set_index("route_id").cng_share
        self.mix = mix.to_dict()
        # 便ごとのばらつき（変動係数）を平均の大きさ別に（tsh.p2_trip）
        p = C.RESULTS / "p2_trip_metrics.json"
        self.cv_table = None
        if cv is None and p.exists():
            m = json.loads(p.read_text(encoding="utf-8"))
            bins = m["between_trip_cv_by_mean_bin"]
            self.cv_table = sorted((v["mean_y"], v["cv_true_load"]) for v in bins.values())
            cv = m["between_trip_cv_of_true_load_overall"]
        self.cv = float(cv if cv is not None else 1.0)
        self.route_E, self.E_star, self.capped_routes = self.route_expansion(a, tk)
        self.cell = {(r.route_id, r.k, r.day_type, r.hr):
                     (r.sample_per_trip * self.route_E.get(r.route_id, self.E_star), r["sum"], r.sample_per_trip, r.lam)
                     for _, r in a.iterrows()}

    def crush(self, route_id: str) -> float:
        """その路線の車両構成で、平均として起こりうる車内人数の上限（定員 × 1.4）。"""
        return 1.4 * sum(w * c[1] for w, c in self.weights(route_id))

    def route_expansion(self, a: pd.DataFrame, tk: pd.DataFrame):
        """路線ごとの拡大係数 E_r = min(E*, U_r)。U_r は「混む区間（券 5 人以上のマスの 95% 点）が上限を超えない」最大の係数。
        E* は、全路線の拡大後の乗客数の合計が公表値（約 408 万人/日）になるように二分法で決める。"""
        busy = a[a["sum"] >= 3]
        q95 = busy.groupby("route_id").sample_per_trip.quantile(0.95)
        q95_all = a.groupby("route_id").sample_per_trip.quantile(0.95)
        q95 = q95.combine_first(q95_all)
        U = {r: self.crush(r) / v for r, v in q95.items() if v > 0}
        days = tk.date.nunique()
        pax_r = tk[tk.j > tk.i].groupby("route_id").pax.sum() / days
        def total(E):
            return sum(min(E, U.get(r, E)) * p for r, p in pax_r.items())
        # E* は前提の幅（低〜高）の中で、合計が公表値に最も近くなる値
        lo, hi = self.f["expansion_low"], self.f["expansion_high"]
        if total(hi) < OFFICIAL_DAILY:
            E_star = hi
        else:
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if total(mid) < OFFICIAL_DAILY else (lo, mid)
            E_star = (lo + hi) / 2
        route_E = {r: min(E_star, U.get(r, E_star)) for r in pax_r.index}
        capped = sum(1 for r in pax_r.index if U.get(r, np.inf) < E_star)
        self.total_vs_official = total(E_star) / OFFICIAL_DAILY
        return route_E, E_star, capped

    def cv_for(self, lam_v: float) -> float:
        if not self.cv_table:
            return self.cv
        xs = [x for x, _ in self.cv_table]
        ys = [y for _, y in self.cv_table]
        return float(np.interp(lam_v, xs, ys))

    def weights(self, route_id: str) -> list:
        c = float(self.mix.get(route_id, 0.3))
        return [(c, CAP["cng12"]), ((1 - c) * (1 - E9_SHARE), CAP["e12"]), ((1 - c) * E9_SHARE, CAP["e9"])]

    def probs(self, route_id: str, mu: float, n: float, lam_v: float | None = None) -> dict:
        if not np.isfinite(mu) or mu <= 0:      # 券が 1 枚も無い区間など
            return {"座れる": 1.0, "立つ": 0.0, "混雑": 0.0}
        cv = self.cv_for(lam_v) if lam_v is not None else self.cv
        inv_k = cv ** 2 + 1.0 / max(n, 1.0)
        k = 1.0 / inv_k
        dist = gamma(a=k, scale=mu / k)
        ps = pc = 0.0
        for w, (seats, cap) in self.weights(route_id):
            ps += w * dist.cdf(seats)
            pc += w * dist.sf(cap)
        return {"座れる": ps, "立つ": max(0.0, 1 - ps - pc), "混雑": pc}

    def leg(self, route_id: str, i: int, j: int, day_type: str, hr: int) -> dict:
        """乗車区間 i→j で最も混む区間（平均が最大）の推定と、そこでの各レベルの確率。"""
        best = None
        for k in range(i, j):
            v = self.cell.get((route_id, k, day_type, hr))
            if v is not None and np.isfinite(v[0]) and (best is None or v[0] > best[0]):
                best = v
        if best is None:
            return {"level": "不明", "load": None, "confidence": "データなし"}
        mu, n, s, lam_v = best
        if n < 1:   # その区間・時間帯に車両番号つきの券が 1 枚も無い → 推定できない
            return {"level": "不明", "load": None, "confidence": "データなし", "tickets_used": 0}
        p = self.probs(route_id, mu, n, lam_v)
        lvl = self.level_of_mean(route_id, mu)
        f = self.f
        E_r = self.route_E.get(route_id, self.E_star)
        conf = "高" if n >= 15 else ("中" if n >= 5 else "低")   # 車両番号つきの券（全体の約半分）で数えた人数
        return {"level": lvl, "load": round(float(mu)),
                "load_range_assumptions": [round(float(s * min(f["expansion_low"], E_r))), round(float(s * min(f["expansion_high"], E_r * f["expansion_high"] / max(self.E_star, 1))))],
                "prob": {k2: round(float(v), 2) for k2, v in p.items()},
                "confidence": conf, "tickets_used": int(n)}

    def level_of_mean(self, route_id: str, mu: float) -> str:
        """平均の車内人数を、その路線の車両構成で重みづけした座席数・定員と比べたレベル（表示の見出し用）。"""
        seats = sum(w * c[0] for w, c in self.weights(route_id))
        cap = sum(w * c[1] for w, c in self.weights(route_id))
        return "座れる" if mu <= seats else ("立つ" if mu <= cap else "混雑")


def summary(tag: str = "train") -> dict:
    """改良前後で混雑レベルの分布がどう変わるか、定員の 1.5 倍を超えるマスの割合、時間帯別の平均（検証の材料）。"""
    m = CrowdingModel2(tag)
    old = pd.read_parquet(C.PROCESSED / tag / "crowding.parquet")
    cells = pd.DataFrame([(k[0], k[1], k[2], k[3], v[0], v[1], v[3]) for k, v in m.cell.items()],
                         columns=["route_id", "k", "day_type", "hr", "mu", "n", "lam"])
    s = cells[cells.n >= 5].sample(n=min(100_000, (cells.n >= 5).sum()), random_state=0)
    lv, over, pc = [], [], []
    for r in s.itertuples():
        p = m.probs(r.route_id, r.mu, r.n, r.lam)
        lv.append(m.level_of_mean(r.route_id, r.mu)); pc.append(p["混雑"])
        cap = sum(w * c[1] for w, c in m.weights(r.route_id))
        over.append(r.mu > 1.5 * cap)
    prof = cells.groupby(["day_type", "hr"]).mu.mean().unstack(0).round(1)
    Es = pd.Series(m.route_E)
    return {"factors": m.f, "E_star": round(m.E_star, 1), "routes_capped": m.capped_routes, "routes": len(Es),
            "expanded_total_vs_official": round(float(m.total_vs_official), 3),
            "route_E_quantiles": {k: round(float(v), 1) for k, v in Es.quantile([0.05, 0.25, 0.5, 0.75, 0.95]).items()},
            "cv_overall": m.cv, "cv_table(mean_y, cv)": m.cv_table,
            "old_level_%": {k: round(v * 100, 1) for k, v in old[old.n_tickets >= 10].level.value_counts(normalize=True).items()},
            "new_level_of_mean_%": {k: round(v * 100, 1) for k, v in pd.Series(lv).value_counts(normalize=True).items()},
            "new_mean_P_crowded_%": round(float(np.mean(pc) * 100), 1),
            "cells_mean_over_1.5x_capacity_%": round(float(np.mean(over) * 100), 2),
            "weekday_am_peak_mean_load": float(prof.loc[8:10, "weekday"].mean().round(1)),
            "weekday_midday_mean_load": float(prof.loc[12:15, "weekday"].mean().round(1)),
            "weekday_pm_peak_mean_load": float(prof.loc[17:20, "weekday"].mean().round(1))}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(summary(), ensure_ascii=False, indent=1))
