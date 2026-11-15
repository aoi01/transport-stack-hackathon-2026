"""問題1: 観測 GPS にもとづく区間所要時間モデルと、待ち時間（運行間隔）モデル。

区間所要時間:
  同じ便で続けて検出された2つの停留所（間に未検出の停留所が最大4つ）の通過時刻の差を、
  間にある「隣り合う停留所どうしの区間（リンク）」に距離で按分する。
  リンクは停留所 ID の組で表すので、同じ道路を走る別の路線のデータもまとめて使える。
  （from_stop, to_stop）× 平日/休日 × 1時間帯 の中央値を推定値とする。
  データが少ないときは、時間帯をまとめた値 → リンク全体の値 → 路線の平均速度 → 15 km/h と順に退避する。

待ち時間:
  路線 × 平日/休日 × 時間帯ごとに、GPS で実際に走った便の数から運行間隔を出し、
  待ち時間の期待値 = 運行間隔 / 2（上限 30 分）とする。GPS が無い路線は GTFS の時刻表の便数を使う。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime

import numpy as np
import pandas as pd

from . import common as C

MIN_N = 5            # 中央値を使うのに必要な観測数
DEFAULT_KMH = 15.0   # どの退避先も無いときの速度
MAX_WAIT_MIN = 30.0


def passages_glob(days) -> str:
    files = [(C.INTERIM / "stop_passages" / f"date={d:%Y-%m-%d}" / "part.parquet").as_posix() for d in days]
    return "[" + ",".join(f"'{f}'" for f in files) + "]"


def build(days=C.TRAIN_DAYS, tag: str = "train") -> None:
    con = C.connect()
    pat = C.patterns()[["route_id", "seq", "stop_id", "cum_m"]].copy()
    pat["route_id"] = pat["route_id"].astype(int)
    con.register("pat", pat)
    dt = pd.DataFrame({"date": days, "day_type": [C.day_type(d) for d in days]})
    con.register("daytypes", dt)
    out = C.PROCESSED / tag
    out.mkdir(parents=True, exist_ok=True)

    # 1) 連続して検出された停留所の組 → リンクへの按分
    con.execute(f"""
        CREATE TABLE obs AS
        WITH p AS (
            SELECT ps.date, ps.vehicle_id, ps.trip_id, ps.route_id, ps.seq, ps.ts,
                   lead(ps.seq) OVER w AS seq2, lead(ps.ts) OVER w AS ts2
            FROM read_parquet({passages_glob(days)}) ps
            WINDOW w AS (PARTITION BY ps.date, ps.vehicle_id, ps.trip_id ORDER BY ps.seq)
        ), pairs AS (
            SELECT p.*, epoch(ts2 - ts) AS dt_s,
                   b.cum_m - a.cum_m AS d_m,
                   hour(timezone('{C.TZ}', ts)) AS hr
            FROM p JOIN pat a ON a.route_id = p.route_id AND a.seq = p.seq
                   JOIN pat b ON b.route_id = p.route_id AND b.seq = p.seq2
            WHERE seq2 IS NOT NULL AND seq2 - p.seq <= 5
        ), good AS (
            SELECT * FROM pairs
            WHERE d_m > 0 AND dt_s > 0
              AND d_m / dt_s * 3.6 BETWEEN 1 AND 80     -- 時速 1〜80 km の範囲だけ使う
        )
        SELECT g.date, dt.day_type, g.hr, l.stop_id AS from_stop, l2.stop_id AS to_stop,
               (l2.cum_m - l.cum_m) AS link_m,
               g.dt_s * (l2.cum_m - l.cum_m) / g.d_m AS link_s
        FROM good g
        JOIN daytypes dt USING (date)
        JOIN pat l  ON l.route_id = g.route_id AND l.seq >= g.seq AND l.seq < g.seq2
        JOIN pat l2 ON l2.route_id = g.route_id AND l2.seq = l.seq + 1
        WHERE l2.cum_m > l.cum_m
    """)
    con.execute(f"""
        COPY (SELECT from_stop, to_stop, day_type, hr, median(link_s) AS sec, count(*) AS n,
                     any_value(link_m) AS link_m
              FROM obs GROUP BY ALL) TO '{(out / 'link_hour.parquet').as_posix()}' (FORMAT parquet)
    """)
    con.execute(f"""
        COPY (SELECT from_stop, to_stop, day_type, median(link_s) AS sec, count(*) AS n
              FROM obs GROUP BY ALL) TO '{(out / 'link_daytype.parquet').as_posix()}' (FORMAT parquet)
    """)
    con.execute(f"""
        COPY (SELECT from_stop, to_stop, median(link_s) AS sec, count(*) AS n
              FROM obs GROUP BY ALL) TO '{(out / 'link_all.parquet').as_posix()}' (FORMAT parquet)
    """)
    n_obs = con.execute("SELECT count(*) FROM obs").fetchone()[0]

    # 2) 運行間隔：路線 × 日 × 時間帯で走った便の数 → 平日/休日の平均
    con.execute(f"""
        COPY (
            WITH t AS (
                SELECT ps.date, ps.route_id, ps.vehicle_id, ps.trip_id, min(ps.ts) AS t0
                FROM read_parquet({passages_glob(days)}) ps GROUP BY ALL
            ), c AS (
                SELECT t.route_id, dt.day_type, t.date, hour(timezone('{C.TZ}', t0)) AS hr, count(*) AS trips
                FROM t JOIN daytypes dt USING (date) GROUP BY ALL
            ), nd AS (SELECT day_type, count(*) AS ndays FROM daytypes GROUP BY 1)
            SELECT route_id, day_type, hr, sum(trips) / any_value(ndays) AS trips_per_hour
            FROM c JOIN nd USING (day_type) GROUP BY route_id, day_type, hr
        ) TO '{(out / 'route_freq.parquet').as_posix()}' (FORMAT parquet)
    """)
    # 3) 待ち時間：各路線の「基準停留所」（最も多く検出された停留所）での実際の到着間隔から、
    #    ランダムな時刻に来た人の平均待ち時間 E[H^2] / (2 E[H]) を求める（間隔のばらつきを反映）。
    #    基準停留所を検出できなかった便は、前後の検出から距離で補間する。2分以内の到着は同じバスとみなす。
    con.execute(f"""
        COPY (
        WITH ps AS (
            SELECT p.date, p.vehicle_id, p.trip_id, p.route_id, p.seq, p.ts, pat.cum_m
            FROM read_parquet({passages_glob(days)}) p
            JOIN pat ON pat.route_id = p.route_id AND pat.seq = p.seq
        ), refseq AS (
            SELECT route_id, mode(seq) AS ref FROM ps GROUP BY route_id
        ), refcum AS (
            SELECT r.route_id, r.ref, pat.cum_m AS ref_cum FROM refseq r JOIN pat ON pat.route_id = r.route_id AND pat.seq = r.ref
        ), bracket AS (
            SELECT ps.date, ps.vehicle_id, ps.trip_id, ps.route_id, any_value(rc.ref_cum) AS ref_cum,
                   arg_max(epoch(ps.ts), ps.seq) FILTER (WHERE ps.seq <= rc.ref) AS t_a,
                   max(ps.cum_m) FILTER (WHERE ps.seq <= rc.ref) AS c_a,
                   arg_min(epoch(ps.ts), ps.seq) FILTER (WHERE ps.seq >= rc.ref) AS t_b,
                   min(ps.cum_m) FILTER (WHERE ps.seq >= rc.ref) AS c_b
            FROM ps JOIN refcum rc USING (route_id) GROUP BY ALL
        ), arr AS (
            SELECT date, route_id,
                   CASE WHEN c_b = c_a THEN t_a ELSE t_a + (t_b - t_a) * (ref_cum - c_a) / (c_b - c_a) END AS t
            FROM bracket WHERE t_a IS NOT NULL AND t_b IS NOT NULL
        ), h AS (
            SELECT date, route_id, t, lead(t) OVER (PARTITION BY date, route_id ORDER BY t) - t AS hw
            FROM arr
        ), hh AS (
            SELECT h.route_id, dt.day_type, hour(timezone('{C.TZ}', to_timestamp(t))) AS hr, hw
            FROM h JOIN daytypes dt USING (date)
            WHERE hw >= 120 AND hw <= 4 * 3600
        )
        SELECT route_id, day_type, hr, sum(hw * hw) / (2 * sum(hw)) AS wait_s, count(*) AS n,
               median(hw) AS median_headway_s
        FROM hh GROUP BY ALL
        ) TO '{(out / 'route_wait.parquet').as_posix()}' (FORMAT parquet)
    """)
    print(f"[{tag}] リンク観測 {n_obs:,} 件から所要時間表を作成 → {out}")


def build_schedule() -> None:
    """GTFS の時刻表（比較の基準）を、代表パターンの停留所順にそろえて保存する。"""
    out = C.PROCESSED / "schedule.parquet"
    con = C.connect()
    pat = C.patterns()[["route_id", "seq", "stop_id"]]
    con.register("pat", pat)
    con.execute(f"""
        COPY (
        WITH st AS (
            SELECT trip_id, stop_id, CAST(stop_sequence AS INT) AS gseq,
                   CAST(split_part(arrival_time, ':', 1) AS INT) * 3600
                 + CAST(split_part(arrival_time, ':', 2) AS INT) * 60
                 + CAST(split_part(arrival_time, ':', 3) AS INT) AS t_s
            FROM read_csv('{(C.GTFS / 'stop_times.txt').as_posix()}', all_varchar=true)
        ), tr AS (
            SELECT trip_id, route_id FROM read_csv('{(C.GTFS / 'trips.txt').as_posix()}', all_varchar=true)
        )
        SELECT tr.route_id, st.trip_id, pat.seq, st.t_s
        FROM st JOIN tr USING (trip_id) JOIN pat ON pat.route_id = tr.route_id AND pat.stop_id = st.stop_id
        ) TO '{out.as_posix()}' (FORMAT parquet)
    """)
    print(f"時刻表 → {out}")


@dataclass
class Leg:
    route_id: str
    i: int
    j: int


class TravelTimeModel:
    """学習済みの表を辞書に読み込み、区間の所要時間・待ち時間を返す。"""

    def __init__(self, tag: str = "train"):
        d = C.PROCESSED / tag
        lh = pd.read_parquet(d / "link_hour.parquet")
        lh = lh[lh.n >= MIN_N]
        self.lh = {(r.from_stop, r.to_stop, r.day_type, r.hr): r.sec for r in lh.itertuples()}
        ld = pd.read_parquet(d / "link_daytype.parquet")
        ld = ld[ld.n >= MIN_N]
        self.ld = {(r.from_stop, r.to_stop, r.day_type): r.sec for r in ld.itertuples()}
        la = pd.read_parquet(d / "link_all.parquet")
        self.la = {(r.from_stop, r.to_stop): r.sec for r in la[la.n >= 2].itertuples()}
        self.la_n = {(r.from_stop, r.to_stop): r.n for r in la.itertuples()}
        rf = pd.read_parquet(d / "route_freq.parquet")
        self.freq = {(str(r.route_id), r.day_type, r.hr): r.trips_per_hour for r in rf.itertuples()}
        self.has_gps = {str(x) for x in rf.route_id.unique()}
        rw = pd.read_parquet(d / "route_wait.parquet")
        rw = rw[rw.n >= 3]
        self.wait_tbl = {(str(r.route_id), r.day_type, r.hr): r.wait_s for r in rw.itertuples()}
        rwd = rw.groupby(["route_id", "day_type"]).apply(
            lambda g: (g.wait_s * g.n).sum() / g.n.sum(), include_groups=False)
        self.wait_dt = {(str(k[0]), k[1]): v for k, v in rwd.items()}
        p = C.patterns()
        self.pat = {rid: g.reset_index(drop=True) for rid, g in p.groupby("route_id")}
        self.stop_ids = {rid: g.stop_id.tolist() for rid, g in self.pat.items()}
        self.cum = {rid: g.cum_m.to_numpy() for rid, g in self.pat.items()}
        self._sched = None
        self.source_counts = {"hour": 0, "daytype": 0, "all": 0, "default": 0}

    # --- 区間の所要時間 -------------------------------------------------------
    def link_sec(self, a: str, b: str, link_m: float, day_type: str, hr: int, mode: str = "model") -> float:
        if mode == "flat":
            v = self.la.get((a, b))
            if v is not None:
                return v
            return link_m / (DEFAULT_KMH / 3.6)
        v = self.lh.get((a, b, day_type, hr))
        if v is not None:
            self.source_counts["hour"] += 1
            return v
        v = self.ld.get((a, b, day_type))
        if v is not None:
            self.source_counts["daytype"] += 1
            return v
        v = self.la.get((a, b))
        if v is not None:
            self.source_counts["all"] += 1
            return v
        self.source_counts["default"] += 1
        return link_m / (DEFAULT_KMH / 3.6)

    def ride_sec(self, route_id: str, i: int, j: int, depart: datetime, mode: str = "model") -> float:
        """路線 route_id の seq i から j までの乗車時間（秒）。時刻を進めながら時間帯を切り替える。"""
        ids, cum = self.stop_ids[route_id], self.cum[route_id]
        dtp = C.day_type(depart.date())
        t = depart.hour * 3600 + depart.minute * 60 + depart.second
        total = 0.0
        for k in range(i, j):
            hr = int(((t + total) // 3600) % 24)
            total += self.link_sec(ids[k], ids[k + 1], cum[k + 1] - cum[k], dtp, hr, mode)
        return total

    # --- 待ち時間 -------------------------------------------------------------
    def wait_sec(self, route_id: str, depart: datetime, mode: str = "model") -> float:
        """待ち時間の期待値（秒）。mode="model": 実測の到着間隔から。"headway": 便数から運行間隔/2。"""
        dtp = C.day_type(depart.date())
        if mode == "model":
            v = self.wait_tbl.get((route_id, dtp, depart.hour))
            if v is None:
                v = self.wait_dt.get((route_id, dtp))
            if v is not None:
                return float(v)
        f = self.freq.get((route_id, dtp, depart.hour))
        if f is None or f <= 0:
            f = self.sched_freq(route_id, depart.hour)
        if f is None or f <= 0:
            return MAX_WAIT_MIN * 60
        return min(60.0 / f / 2.0, MAX_WAIT_MIN) * 60

    # --- 時刻表（比較の基準） ---------------------------------------------------
    @property
    def sched(self) -> pd.DataFrame:
        if self._sched is None:
            s = pd.read_parquet(C.PROCESSED / "schedule.parquet")
            # 環状路線では同じ停留所が2回出るので、便 × seq で最も早い時刻を使う
            s = s.groupby(["route_id", "trip_id", "seq"], as_index=False).t_s.min()
            self._sched = s
            self._sched_pv = {r: g.pivot(index="trip_id", columns="seq", values="t_s")
                              for r, g in s.groupby("route_id")}
            self._sched_first = {r: pv.min(axis=1) for r, pv in self._sched_pv.items()}
        return self._sched

    def sched_freq(self, route_id: str, hr: int):
        self.sched
        first = self._sched_first.get(route_id)
        if first is None:
            return None
        return float(((first // 3600) % 24 == hr).sum())

    def _sched_pair(self, route_id: str, i: int, j: int):
        self.sched
        pv = self._sched_pv.get(route_id)
        if pv is None or i not in pv.columns or j not in pv.columns:
            return None
        d = pd.DataFrame({"a": pv[i], "b": pv[j]}).dropna()
        return d[d.b > d.a]

    def sched_ride_sec(self, route_id: str, i: int, j: int, depart: datetime):
        """時刻表上の所要時間：その時間帯に seq i を出る便の (j の時刻 - i の時刻) の中央値。"""
        d = self._sched_pair(route_id, i, j)
        if d is None:
            return None
        if d.empty:
            return None
        t = depart.hour * 3600 + depart.minute * 60
        near = d[(d.a - t).abs() <= 3600]
        return float((near if len(near) else d).eval("b - a").median())

    def sched_next(self, route_id: str, i: int, j: int, depart: datetime):
        """時刻表上で、時刻 depart 以降に seq i を出る最初の便の (i 発, j 着) 秒。"""
        d = self._sched_pair(route_id, i, j)
        if d is None:
            return None
        t = depart.hour * 3600 + depart.minute * 60 + depart.second
        d = d[d.a >= t].sort_values("a")
        if d.empty:
            return None
        return float(d.a.iloc[0]), float(d.b.iloc[0])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    which = sys.argv[1] if len(sys.argv) > 1 else "train"
    if which == "schedule":
        build_schedule()
    elif which == "all":
        build(C.TRAIN_DAYS + C.TEST_DAYS, "all")
    else:
        build(C.TRAIN_DAYS, "train")


if __name__ == "__main__":
    main()
