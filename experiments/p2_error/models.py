"""問2: 前の期間の推定で後の期間のマス（路線 × 区間 × 平日/休日 × 時間帯）の 1 便あたりの人数を当てる、予測の作り方の候補。

どれも学習期間の日別の集計（train/crowding_daily.parquet）と便数だけから作り、検証週のデータは使わない。
  base       今の方式: 期間内の 人数 / 便数
  calendar   券の量が異常な日を外す（10/17〜19: 車両番号の無い券だけが約 1/4 に減った、10/20: ダシャラー）
  compose    曜日の構成を当てる先の期間に合わせる（各曜日の重みの合計を、当てる先の期間のその曜日の日数に比例させる。
             休日の区分では土曜と日曜・祝日で人数が大きく違う。当てる先の暦は前もって分かっている）
  recent     最近の日ほど重くする（半減期 h 日）
  shrink     ポアソン・ガンマの経験ベイズ（Clayton & Kaldor 1987 の (O+ν)/(E+α) の形）で、
             路線ごとの「区間の形 × 時間帯の量」の独立モデル（事前の平均 m）に縮める:
             予測 = (S + κ) / (T + κ/m)。κ は事前の強さ（人数の単位）
  smooth     隣の区間・隣の時間帯の人数と便数を重み β で足す（局所の平滑化）
"""
from __future__ import annotations

from datetime import date

from base import *  # noqa: F401,F403

OCT = lambda d: date(2026, 10, d)  # noqa: E731
BAD_DAYS = {OCT(17), OCT(18), OCT(19), OCT(20)}


def dow_group(d: date) -> str:
    """曜日の区分。休日は土曜と、日曜・祝日に分ける。"""
    if d in C.HOLIDAYS or d.weekday() == 6:
        return "sun"
    if d.weekday() == 5:
        return "sat"
    return ["mon", "tue", "wed", "thu", "fri"][d.weekday()]


def day_weights(fit_days, target_days, calendar=True, compose=True, half_life=None) -> dict:
    days = [x for x in fit_days if not (calendar and x in BAD_DAYS)]
    w = {x: 1.0 for x in days}
    if compose:
        tgt = pd.Series([dow_group(x) for x in target_days]).value_counts()
        have = pd.Series([dow_group(x) for x in days]).value_counts()
        for x in days:
            g = dow_group(x)
            # 当てる先に無い曜日（例: 当てる先の休日が土曜だけ）は重み 0 にせず、小さく残す（そのマスの標本が消えないように）
            w[x] = (tgt.get(g, 0.0) + 0.05) / have[g]
    if half_life:
        last = max(days)
        for x in days:
            w[x] *= 0.5 ** ((last - x).days / half_life)
    return w


def independence_prior(a: pd.DataFrame, pool_daytype: bool = True) -> pd.Series:
    """路線ごとの「区間の形 × 時間帯の量」。m = S(区間,·) S(·,時間帯) / S(·,·) / T(時間帯)。"""
    seg_keys = ["route_id", "seq"] if pool_daytype else ["route_id", "seq", "day_type"]
    tot_keys = ["route_id"] if pool_daytype else ["route_id", "day_type"]
    s_seg = a.groupby(seg_keys).pax.transform("sum")
    s_tot = a.groupby(tot_keys).pax.transform("sum")
    s_hr = a.groupby(["route_id", "day_type", "hr"]).pax.transform("sum")
    if pool_daytype:
        # 区間の形は平日・休日をまとめて作り、時間帯の量（S(·,時間帯)）は区分ごと。S(·,·) は区分をまとめた合計なので、
        # 形の合計が 1 になるように S(区間,·)/S(·,·) を使う
        return s_seg / s_tot * s_hr / a["T"]
    return s_seg * s_hr / s_tot / a["T"]


def shrink(a: pd.DataFrame, kappa: float, pool_daytype: bool = True) -> pd.Series:
    if kappa <= 0:
        return a.pax / a["T"]
    m = independence_prior(a, pool_daytype)
    pred = (a.pax + kappa) / (a["T"] + kappa / m)
    return pred.where(m > 0, a.pax / a["T"])


def smooth(a: pd.DataFrame, beta: float, dseq: int = 1, dhr: int = 1) -> pd.Series:
    """隣の区間（±dseq）・隣の時間帯（±dhr）の人数と便数を重み beta で足した比。"""
    if beta <= 0:
        return a.pax / a["T"]
    idx = a.set_index(K)[["pax", "T"]]
    S = a.pax.to_numpy(dtype=float).copy()
    T = a["T"].to_numpy(dtype=float).copy()
    base = a[K].copy()
    for ds in range(-dseq, dseq + 1):
        for dh in range(-dhr, dhr + 1):
            if ds == 0 and dh == 0:
                continue
            nb = base.assign(seq=base.seq + ds, hr=base.hr + dh)
            v = idx.reindex(pd.MultiIndex.from_frame(nb[K]))
            S += beta * np.nan_to_num(v.pax.to_numpy())
            T += beta * np.nan_to_num(v["T"].to_numpy())
    return pd.Series(S / T, index=a.index)


def build_cells(d, grid, fit_days, target_days, calendar=True, compose=True, half_life=None) -> pd.DataFrame:
    w = day_weights(fit_days, target_days, calendar, compose, half_life)
    a = cells_from_daily(d[d.date.isin(set(fit_days))], grid[grid.date.isin(set(fit_days))], w)
    return a[a["T"] > 0].copy()


def apply(a, kappa=0.0, pool_daytype=True, beta=0.0, dseq=1, dhr=1) -> pd.DataFrame:
    a = a.copy()
    if beta > 0:
        sm = smooth(a, beta, dseq, dhr)
        if kappa > 0:   # 平滑化した比を「観測」とみなして縮める
            a["pred"] = shrink(a.assign(pax=sm * a["T"]), kappa, pool_daytype)
        else:
            a["pred"] = sm
    else:
        a["pred"] = shrink(a, kappa, pool_daytype)
    return a


def predict(d, grid, fit_days, target_days, calendar=True, compose=True, half_life=None,
            kappa=0.0, pool_daytype=True, beta=0.0, dseq=1, dhr=1) -> pd.DataFrame:
    a = build_cells(d, grid, fit_days, target_days, calendar, compose, half_life)
    return apply(a, kappa, pool_daytype, beta, dseq, dhr)
