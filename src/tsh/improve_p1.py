"""問題1の精度改善の実験。最初の検証（validate_p1）と同じ 20,000 区間で、手法を1つずつ足して比べる。

試す手法（先行研究の根拠つき）:
  V0  基準: リンク × 平日/休日 × 1時間帯の中央値（最初の版）
  V1  時間帯を 30 分に細かくする（ピークの立ち上がりを捉える）
  V2  縮小推定（empirical Bayes）: 観測が少ないマスの値を、上の階層（時間帯をまとめた値）に寄せる
        推定 = (n × マスの値 + k × 上の階層の値) / (n + k)
  V3  路線別のリンク時間: 同じ道路でも急行・各停で違うので、路線ごとの値を全路線の値に縮小して使う
  V4  直前のバスによる補正（Schwinger ら、Delhi の TCS 論文、Chennai の Kalman 法と同じ考え方）:
        出発前 W 分以内に、これから通るリンクを実際に走った他のバスが「いつもよりどれだけ遅かったか」の比
        （観測 ÷ 過去の推定）の中央値 r を求め、予測 = 過去の推定 × r^w（w = m/(m+c)、m は観測数）
        本番では GTFS-RT の位置から同じものが計算できる。
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import defaultdict
from datetime import datetime

import numpy as np
import pandas as pd

from . import common as C
from .traveltime import passages_glob
from .validate_p1 import metrics

OUT = C.PROCESSED / "improve"


def link_obs(days, path) -> None:
    """リンク観測（時刻つき）: route_id, from_stop, to_stop, t（区間に入った時刻・epoch 秒）, link_s, link_m, day_type"""
    con = C.connect()
    pat = C.patterns()[["route_id", "seq", "stop_id", "cum_m"]].copy()
    pat["route_id"] = pat["route_id"].astype(int)
    con.register("pat", pat)
    con.register("daytypes", pd.DataFrame({"date": days, "day_type": [C.day_type(d) for d in days]}))
    con.execute(f"""
        COPY (
        WITH p AS (
            SELECT date, vehicle_id, trip_id, route_id, seq, ts,
                   lead(seq) OVER w AS seq2, lead(ts) OVER w AS ts2
            FROM read_parquet({passages_glob(days)})
            WINDOW w AS (PARTITION BY date, vehicle_id, trip_id ORDER BY seq)
        ), g AS (
            SELECT p.*, epoch(ts2 - ts) AS dt_s, b.cum_m - a.cum_m AS d_m, a.cum_m AS c0
            FROM p JOIN pat a ON a.route_id = p.route_id AND a.seq = p.seq
                   JOIN pat b ON b.route_id = p.route_id AND b.seq = p.seq2
            WHERE seq2 IS NOT NULL AND seq2 - p.seq <= 5
        )
        SELECT g.route_id, dt.day_type, l.stop_id AS from_stop, l2.stop_id AS to_stop,
               epoch(g.ts) + g.dt_s * (l.cum_m - g.c0) / g.d_m AS t,
               g.dt_s * (l2.cum_m - l.cum_m) / g.d_m AS link_s,
               l2.cum_m - l.cum_m AS link_m
        FROM g JOIN daytypes dt USING (date)
        JOIN pat l  ON l.route_id = g.route_id AND l.seq >= g.seq AND l.seq < g.seq2
        JOIN pat l2 ON l2.route_id = g.route_id AND l2.seq = l.seq + 1
        WHERE g.d_m > 0 AND g.dt_s > 0 AND g.d_m / g.dt_s * 3.6 BETWEEN 1 AND 80 AND l2.cum_m > l.cum_m
        ) TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)


def build_tables() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tr = OUT / "obs_train.parquet"
    te = OUT / "obs_test.parquet"
    if not tr.exists():
        link_obs(C.TRAIN_DAYS, tr)
    if not te.exists():
        link_obs(C.TEST_DAYS, te)
    con = C.connect()
    src = f"(SELECT *, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr, " \
          f"hour(timezone('{C.TZ}', to_timestamp(t))) * 2 + (minute(timezone('{C.TZ}', to_timestamp(t))) >= 30)::INT AS hh " \
          f"FROM '{tr.as_posix()}')"
    specs = {
        "l_dt_hh": "from_stop, to_stop, day_type, hh",
        "l_dt_hr": "from_stop, to_stop, day_type, hr",
        "l_dt": "from_stop, to_stop, day_type",
        "l": "from_stop, to_stop",
        "r_l_dt_hr": "route_id, from_stop, to_stop, day_type, hr",
    }
    for name, keys in specs.items():
        con.execute(f"COPY (SELECT {keys}, median(link_s) AS sec, count(*) AS n, any_value(link_m) AS link_m "
                    f"FROM {src} GROUP BY ALL) TO '{(OUT / (name + '.parquet')).as_posix()}' (FORMAT parquet)")


class Variants:
    def __init__(self):
        def load(name, key):
            df = pd.read_parquet(OUT / f"{name}.parquet")
            return {tuple(r[:len(key)]): (r[len(key)], r[len(key) + 1])
                    for r in df[key + ["sec", "n"]].itertuples(index=False)}
        self.hh = load("l_dt_hh", ["from_stop", "to_stop", "day_type", "hh"])
        self.hr = load("l_dt_hr", ["from_stop", "to_stop", "day_type", "hr"])
        self.dt = load("l_dt", ["from_stop", "to_stop", "day_type"])
        self.al = load("l", ["from_stop", "to_stop"])
        rl = pd.read_parquet(OUT / "r_l_dt_hr.parquet")
        rl["route_id"] = rl.route_id.astype(str)
        self.rl = {(r.route_id, r.from_stop, r.to_stop, r.day_type, r.hr): (r.sec, r.n) for r in rl.itertuples()}
        p = C.patterns()
        self.ids = {rid: g.stop_id.tolist() for rid, g in p.groupby("route_id")}
        self.cum = {rid: g.cum_m.to_numpy() for rid, g in p.groupby("route_id")}

    @staticmethod
    def shrink(cell, parent, k):
        if cell is None:
            return parent
        if parent is None:
            return cell[0]
        return (cell[1] * cell[0] + k * parent) / (cell[1] + k)

    def link(self, rid, a, b, m, dt, hr, hh, v: str, k: float = 10.0, k_route: float = 20.0) -> float:
        base_dt = self.dt.get((a, b, dt))
        base_al = self.al.get((a, b))
        parent = base_dt[0] if base_dt and base_dt[1] >= 5 else (base_al[0] if base_al else m / (15 / 3.6))
        c_hr = self.hr.get((a, b, dt, hr))
        if v == "V0":
            if c_hr and c_hr[1] >= 5:
                return c_hr[0]
            return parent
        if v == "V1":
            c = self.hh.get((a, b, dt, hh))
            if c and c[1] >= 5:
                return c[0]
            return c_hr[0] if c_hr and c_hr[1] >= 5 else parent
        # V2 以降: 30分 → 1時間 → 平日/休日 の順に縮小
        hr_val = self.shrink(c_hr, parent, k)
        val = self.shrink(self.hh.get((a, b, dt, hh)), hr_val, k)
        if v in ("V3", "V4"):
            val = self.shrink(self.rl.get((rid, a, b, dt, hr)), val, k_route)
        return val

    def ride(self, rid, i, j, t0: datetime, v: str, **kw) -> tuple[float, list]:
        ids, cum = self.ids[rid], self.cum[rid]
        dt = C.day_type(t0.date())
        s0 = t0.hour * 3600 + t0.minute * 60 + t0.second
        tot, parts = 0.0, []
        for q in range(i, j):
            t = s0 + tot
            hr = int(t // 3600) % 24
            hh = hr * 2 + int((t % 3600) >= 1800)
            x = self.link(rid, ids[q], ids[q + 1], cum[q + 1] - cum[q], dt, hr, hh, v, **kw)
            parts.append((ids[q], ids[q + 1], x))
            tot += x
        return tot, parts


class Probe:
    """検証週のリンク観測（時刻つき）から、ある時刻より前 W 分の観測を引く。"""

    def __init__(self, var: Variants):
        df = pd.read_parquet(OUT / "obs_test.parquet")
        df["hr"] = pd.to_datetime(df.t, unit="s", utc=True).dt.tz_convert(C.TZ).dt.hour
        self.by = defaultdict(list)
        for r in df.itertuples():
            self.by[(r.from_stop, r.to_stop)].append((r.t, r.link_s, r.day_type, r.hr, r.link_m))
        for k in self.by:
            self.by[k].sort()
        self.times = {k: [x[0] for x in v] for k, v in self.by.items()}
        self.var = var

    def ratio(self, parts, t_epoch: float, window_s: float, v: str) -> tuple[float, int]:
        logs = []
        for a, b, _ in parts:
            ts = self.times.get((a, b))
            if not ts:
                continue
            lo = bisect.bisect_left(ts, t_epoch - window_s)
            hi = bisect.bisect_left(ts, t_epoch)
            for t, s, dt, hr, m in self.by[(a, b)][lo:hi]:
                hh = hr * 2   # 比の計算には 1 時間の値で十分
                h = self.var.link(None, a, b, m, dt, hr, hh, "V2")
                if h > 0 and s > 0:
                    logs.append(np.log(s / h))
        if not logs:
            return 1.0, 0
        return float(np.exp(np.median(logs))), len(logs)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    build_tables()
    var = Variants()
    s = pd.read_csv(C.RESULTS / "p1_ride_samples.csv", parse_dates=["t_i", "t_j"], dtype={"route_id": str})
    s = s[s.route_id.isin(var.ids.keys())].reset_index(drop=True)
    res, preds = {}, {}
    for v in ["V0", "V1", "V2", "V3"]:
        preds[v] = [var.ride(r.route_id, r.i, r.j, r.t_i.to_pydatetime(), v)[0] for r in s.itertuples()]
        res[v] = metrics(s.actual_s, preds[v])
        print(v, res[v], flush=True)
    # k（縮小の強さ）の感度
    for k in [3, 30]:
        p = [var.ride(r.route_id, r.i, r.j, r.t_i.to_pydatetime(), "V3", k=k)[0] for r in s.itertuples()]
        res[f"V3_k{k}"] = metrics(s.actual_s, p)
        print(f"V3 k={k}", res[f"V3_k{k}"], flush=True)
    # V4: 直前のバスの補正
    pr = Probe(var)
    t_ep = (s.t_i.dt.tz_localize(C.TZ).dt.tz_convert("UTC").astype("int64") // 10**9).to_numpy()
    for W in [15, 30, 60]:
        for c in [5, 20]:
            out, ms = [], []
            for n, r in enumerate(s.itertuples()):
                base, parts = var.ride(r.route_id, r.i, r.j, r.t_i.to_pydatetime(), "V3")
                ratio, m = pr.ratio(parts, t_ep[n], W * 60, "V3")
                w = m / (m + c)
                out.append(base * ratio ** w)
                ms.append(m)
            key = f"V4_W{W}_c{c}"
            res[key] = metrics(s.actual_s, out)
            res[key]["share_with_probe_%"] = round(float(np.mean(np.array(ms) > 0) * 100), 1)
            preds[key] = out
            print(key, res[key], flush=True)
    best = min((k for k in res if k.startswith("V4")), key=lambda k: res[k]["MedAPE_%"])
    s["V0"] = preds["V0"]; s["best"] = preds[best]
    s["hr"] = s.t_i.dt.hour
    s["period"] = np.select([s.hr.between(8, 10), s.hr.between(17, 20)], ["朝ピーク(8-10時)", "夕ピーク(17-20時)"], "その他")
    by = {p: {"V0": metrics(g.actual_s, g.V0), best: metrics(g.actual_s, g.best)} for p, g in s.groupby("period")}
    res["best"] = best
    res["by_period"] = by
    (C.RESULTS / "p1_improve_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("best:", best)
    print(json.dumps(by, ensure_ascii=False))


if __name__ == "__main__":
    main()
