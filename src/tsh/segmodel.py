"""API 用: 乗る区間全体（停留所 i → j）を直接予測する LightGBM（tsh.seg_ml で学習）。

返すもの: 乗車時間の中央値、15% 点、85% 点（＝余裕を見た時間）。
- 出発が今から 15 分以内で、記録した GTFS-RT の直近の区間実績（tsh.livelinks）があれば「直近あり」のモデル、
  なければ「過去のみ」のモデルを使う。
- 過去の推定は 10 月の全 31 日の区間実績から作る（学習時は 1 日抜き、検証時は 10/1〜24）。
特徴量の定義は tsh.seg_ml と同じ（変えるときは両方そろえること）。
"""
from __future__ import annotations

from datetime import datetime

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import common as C
from .improve_p1 import OUT as IMP
from .seg_ml import FEATS, OUT as SEG

SERVE = C.PROCESSED / "serve"
NO_REC = [f for f in FEATS if not (f.startswith("rec_") or f.startswith("up_") or f.startswith("route_") or f.startswith("city_"))]
DEFAULT_MPS = 4.1667   # 15 km/h（学習時と同じ）


def build_serving_tables(folder=SERVE, train_only: bool = False) -> None:
    """過去の推定の表。API 用は 31 日分、検証（経路の再現）用は学習期間 10/1〜24 だけ（train_only）。"""
    folder.mkdir(parents=True, exist_ok=True)
    con = C.connect()
    files = [(IMP / "obs_train.parquet").as_posix()] + ([] if train_only else [(IMP / "obs_test.parquet").as_posix()])
    flist = "[" + ",".join(f"'{f}'" for f in files) + "]"
    src = (f"(SELECT route_id, day_type, from_stop, to_stop, ln(link_s) AS ls, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr "
           f"FROM read_parquet({flist}) WHERE link_s > 0)")
    for n, k in {"lk": "from_stop, to_stop, day_type, hr", "ld": "from_stop, to_stop, day_type",
                 "la": "from_stop, to_stop", "lr": "CAST(route_id AS VARCHAR) AS route_id, from_stop, to_stop, day_type, hr"}.items():
        gk = k.replace("CAST(route_id AS VARCHAR) AS route_id", "route_id")
        con.execute(f"COPY (SELECT {k}, avg(ls) AS mlog, count(*) AS n FROM {src} GROUP BY {gk}) "
                    f"TO '{(folder / f'{n}.parquet').as_posix()}' (FORMAT parquet)")


class SegModel:
    def __init__(self, train_only: bool = False):
        folder = (C.PROCESSED / "serve_train") if train_only else SERVE
        if not (folder / "lk.parquet").exists():
            build_serving_tables(folder, train_only)
        def load(n, k):
            df = pd.read_parquet(folder / f"{n}.parquet")
            return {tuple(r[:k]): (r[k], r[k + 1]) for r in df.itertuples(index=False)}
        self.lk = load("lk", 4)
        self.ld = load("ld", 3)
        self.la = load("la", 2)
        self.lr = load("lr", 5)
        self.models = {}
        for tag in ("live", "hist"):
            for q in (15, 50, 85):
                self.models[(tag, q)] = lgb.Booster(model_file=str(SEG / f"lgb_seg_{tag}_q{q}.txt"))
        p = C.patterns()
        self.ids = {rid: g.stop_id.tolist() for rid, g in p.groupby("route_id")}
        self.cum = {rid: g.cum_m.to_numpy() for rid, g in p.groupby("route_id")}

    # ---- 過去の推定 ----------------------------------------------------------
    def _h(self, d, key):
        v = d.get(key)
        return (float(np.exp(v[0])), int(v[1])) if v is not None else (None, 0)

    def _link(self, rid, a, b, m, dt, hr):
        h_hr, n_hr = self._h(self.lk, (a, b, dt, hr))
        h_hr1, _ = self._h(self.lk, (a, b, dt, (hr + 1) % 24))
        h_dt, _ = self._h(self.ld, (a, b, dt))
        h_all, _ = self._h(self.la, (a, b))
        h_rt, n_rt = self._h(self.lr, (rid, a, b, dt, hr))
        dflt = max(m / DEFAULT_MPS, 1.0)   # 同じ場所に停留所が続く（距離 0）区間でも 0 にしない
        h0 = h_hr if (h_hr is not None and n_hr >= 3) else (h_dt or h_all or dflt)
        h1 = h_hr1 or h_dt or h_all or dflt
        hd = h_dt or h_all or dflt
        return h0, h1, hd, n_hr, h_rt, n_rt

    def lr_obs(self, a, b, t_epoch, s):
        """観測 1 件の「いつもとの比」の対数（過去の推定はその時刻の平日/休日・時間帯）。"""
        ti = pd.Timestamp(t_epoch, unit="s", tz="UTC").tz_convert(C.TZ)
        v = self.lk.get((a, b, C.day_type(ti.date()), ti.hour))
        if v is None or v[1] < 3 or s <= 0:
            return None
        return float(np.log(s) - v[0])

    def _raw_with_lr(self, raw: pd.DataFrame) -> pd.DataFrame:
        """直近の区間実績に「いつもとの比」の対数を付ける。記録が更新されるまでは同じ結果を使い回す。"""
        if getattr(self, "_raw_src", None) is raw:
            return self._raw_lr
        ti = pd.to_datetime(raw.t, unit="s", utc=True).dt.tz_convert(C.TZ)
        dts = ti.dt.date.map(C.day_type)
        hrs = ti.dt.hour
        lr = []
        for a, b, dt, hr, s in zip(raw.a, raw.b, dts, hrs, raw.s):
            v = self.lk.get((a, b, dt, hr))
            lr.append(float(np.log(s) - v[0]) if (v is not None and v[1] >= 3 and s > 0) else np.nan)
        out = raw.assign(lr=lr).dropna(subset=["lr"])
        self._raw_src, self._raw_lr = raw, out
        return out

    # ---- 特徴量と予測 ---------------------------------------------------------
    def features(self, rid: str, i: int, j: int, t_board: datetime, raw: pd.DataFrame | None, t0_epoch: float | None):
        ids, cum = self.ids[rid], self.cum[rid]
        dt = C.day_type(t_board.date())
        hr = t_board.hour
        H0 = H1 = HD = HRp = H0p = 0.0
        n_cov = n_rt_cov = 0
        min_n = None
        links = []
        for k in range(i, j):
            a, b, m = ids[k], ids[k + 1], float(cum[k + 1] - cum[k])
            h0, h1, hd, n_hr, h_rt, n_rt = self._link(rid, a, b, m, dt, hr)
            H0 += h0; H1 += h1; HD += hd
            n_cov += int(n_hr >= 3)
            min_n = n_hr if min_n is None else min(min_n, n_hr)
            if h_rt is not None and n_rt >= 3:
                HRp += h_rt; H0p += h0; n_rt_cov += 1
            links.append((a, b))
        n = j - i
        f = {"lH0": np.log(H0), "r_H1": np.log(H1 / H0), "r_HD": np.log(HD / H0), "n_links": n,
             "dist": float(cum[j] - cum[i]), "v_hist": float(cum[j] - cum[i]) / H0, "cov_hr": n_cov / n,
             "min_n": min_n or 0, "r_route": np.log(HRp / H0p) if H0p > 0 else np.nan, "cov_rt": n_rt_cov / n,
             "hr_f": hr + t_board.minute / 60, "dow": (t_board.weekday() + 1) % 7, "weekend": int(dt == "weekend"),
             "rec_med": np.nan, "rec_avg": np.nan, "rec_n": 0, "rec_decay": np.nan, "up_med": np.nan, "up_n": 0,
             "route_avg": np.nan, "route_n": 0, "city_avg": np.nan, "city_n": 0}
        live = raw is not None and t0_epoch is not None and len(raw) > 0
        if live:
            allr = self._raw_with_lr(raw)
            w = allr[(allr.t >= t0_epoch - 1800) & (allr.t < t0_epoch)]
            if len(w):
                key = list(zip(w.a, w.b))
                on_seg = np.array([x in set(links) for x in key])
                x = w[on_seg]
                if len(x):
                    wt = np.exp(-(t0_epoch - x.t.to_numpy()) / 900.0)
                    f.update(rec_med=float(x.lr.median()), rec_avg=float(x.lr.mean()), rec_n=len(x),
                             rec_decay=float((x.lr * wt).sum() / wt.sum()))
                up = {(ids[k], ids[k + 1]) for k in range(max(0, i - 10), i)}
                u = w[np.array([x in up for x in key])]
                if len(u):
                    f.update(up_med=float(u.lr.median()), up_n=len(u))
                rr = w[w.route_id.astype(str) == str(rid)]
                if len(rr):
                    f.update(route_avg=float(rr.lr.mean()), route_n=len(rr))
                f.update(city_avg=float(w.lr.mean()), city_n=len(w))
        return f, H0, live

    def predict(self, rid: str, i: int, j: int, t_board: datetime, raw=None, t0_epoch=None) -> dict:
        f, H0, live = self.features(rid, i, j, t_board, raw, t0_epoch)
        tag = "live" if live and f["rec_n"] > 0 else "hist"
        feats = FEATS if tag == "live" else NO_REC
        x = np.array([[f[k] for k in feats]], dtype=float)
        out = {q: H0 * float(np.exp(self.models[(tag, q)].predict(x)[0])) for q in (15, 50, 85)}
        lo, mid, hi = sorted(out.values())   # 分位点の交差を防ぐ
        return {"median_s": mid, "q15_s": lo, "q85_s": hi, "mode": "直近の実績あり" if tag == "live" else "過去の実績のみ",
                "recent_obs": int(f["rec_n"])}
