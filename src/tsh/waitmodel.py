"""API 用の待ち時間モデル（docs/phase1_prototype.md 12章の「W8」と 14章の「W9」）。

最初のバスの待ち時間を、次の順で決める（出発が今から 15 分以内のとき）:
  1. 乗車停留所より手前を走っている同じ路線のバスが見えれば、その到着予測（tsh.realtime と同じ）
  2. 見えなければ、反対方向の路線を走っていて折り返してくるバスの到着予測（折り返しの組と終点での休憩は 10 月の実績から）、
     「停留所を最後のバスが通ってからの経過時間」で条件づけた残りの待ち時間 E[H − e | H > e]、
     「実際の発車の時刻表」による待ち時間（下の 3）の 3 つの平均（事前に決めた等しい重み）
  3. 折り返しのバスも無ければ、次のバスはまだ始発を出ていないとみなし、「実際の発車の時刻表」で出す:
     10 月の同じ平日/休日の各日に GPS で始発付近を出た時刻から、今以降の最初の発車までの時間の中央値
     ＋ 始発から乗車停留所までの所要時間（3 日分以上なければ、経過時間で条件づけた残りの待ち時間）。
     GTFS の時刻表は実際の発車と合わない（時刻表の時間帯の 24% では便がほとんど走っていない）ので使わない。
検証（10/25〜31、3,000 件）で待ち時間の誤差中央値 36.6% → 33.3%（W8）→ 28.9%（W9、−4.3 ポイント、95% 区間 −5.6〜−3.1）、
待ち時間込みの合計 24.9% → 23.5%（W8）→ 20.4%（W9）。実験は experiments/p1_external/missing_trips.py。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import common as C
from .improve_wait import Residual, chaining, headway_samples
from .traveltime import passages_glob

SERVE = C.PROCESSED / "serve"
IST = timezone(timedelta(hours=5, minutes=30))


def actual_departures(days) -> pd.DataFrame:
    """GPS で始発付近（seq ≤ 3）を出た時刻: route_id, date, sec（その日の 0 時からの秒、IST）。5 停留所以上走った便だけ。"""
    con = C.connect()
    return con.execute(f"""
        WITH t AS (SELECT date, vehicle_id, trip_id, route_id, min(ts) AS t0, min(seq) AS s0
                   FROM read_parquet({passages_glob(days)}) GROUP BY ALL HAVING max(seq) - min(seq) >= 5)
        SELECT CAST(route_id AS VARCHAR) AS route_id, date,
               hour(timezone('{C.TZ}', t0)) * 3600 + minute(timezone('{C.TZ}', t0)) * 60 + second(timezone('{C.TZ}', t0)) AS sec
        FROM t WHERE s0 <= 3""").df()


class WaitModel:
    def __init__(self, tt):
        self.tt = tt
        SERVE.mkdir(parents=True, exist_ok=True)
        hw_path, fd_path, dp_path = SERVE / "headways.parquet", SERVE / "feeders.json", SERVE / "departures.parquet"
        days = C.TRAIN_DAYS + C.TEST_DAYS
        if not hw_path.exists():
            headway_samples(days).to_parquet(hw_path, index=False)
        if not fd_path.exists():
            fd, stats = chaining(days, tt)
            fd_path.write_text(json.dumps({"feeders": fd, "stats": stats}, ensure_ascii=False), encoding="utf-8")
        if not dp_path.exists():
            actual_departures(days).to_parquet(dp_path, index=False)
        self.deps: dict = {}
        for (r, d), x in pd.read_parquet(dp_path).groupby(["route_id", "date"]):
            dd = pd.Timestamp(d).date()
            self.deps.setdefault((r, C.day_type(dd)), []).append(np.sort(x.sec.to_numpy()))
        self.res = Residual(pd.read_parquet(hw_path))
        self.feeders = json.loads(fd_path.read_text(encoding="utf-8"))["feeders"]

    def chain_wait(self, rid: str, i: int, now: datetime, by_route: dict):
        """折り返してくるバスの到着までの秒数（最も早いもの）。無ければ None。"""
        best = None
        for a, lay, _share in self.feeders.get(rid, []):
            veh = by_route.get(str(a))
            if not veh or a not in self.tt.cum:
                continue
            xy_a = self.tt.pat[a][["stop_lat", "stop_lon"]].to_numpy()
            end = len(xy_a) - 1
            for lat, lng, ts in veh:
                d = C.dist_m(lat, lng, xy_a[:, 0], xy_a[:, 1])
                k = int(np.argmin(d))
                if d[k] > 300:
                    continue
                t_k = datetime.fromtimestamp(ts, IST).replace(tzinfo=None)
                if (now - t_k).total_seconds() > 600:
                    continue
                t_end = t_k + timedelta(seconds=self.tt.ride_sec(a, k, end, t_k))
                t_start = t_end + timedelta(seconds=lay)
                t_i = t_start + timedelta(seconds=self.tt.ride_sec(rid, 0, i, t_start))
                w = (t_i - now).total_seconds()
                if w >= -60 and (best is None or w < best):
                    best = max(w, 0.0)
        return best

    def conditional_wait(self, rid: str, i: int, now: datetime, live_links):
        """最後のバスが停留所 i を通ってからの経過時間で条件づけた残りの待ち時間。分からなければ None。"""
        if live_links is None:
            return None, None
        now_ep = pd.Timestamp(now, tz=C.TZ).timestamp()
        lp = live_links.last_pass(rid, i, self.tt.cum[rid], now_ep)
        if lp is None:
            return None, None
        e = now_ep - lp
        if e >= 4 * 3600:
            return None, e
        return self.res(rid, C.day_type(now.date()), now.hour, e), e

    def departure_wait(self, rid: str, i: int, now: datetime):
        """実際の発車の時刻表による待ち時間（秒）: 次の発車までの時間の中央値（日ごと）＋ 始発から停留所 i まで。無ければ None。"""
        sec = now.hour * 3600 + now.minute * 60 + now.second
        gaps = []
        for x in self.deps.get((rid, C.day_type(now.date())), []):
            nxt = x[x >= sec]
            if len(nxt) and nxt[0] - sec <= 4 * 3600:
                gaps.append(nxt[0] - sec)
        if len(gaps) < 3 or rid not in self.tt.cum:
            return None
        g = float(np.median(gaps))
        return g + self.tt.ride_sec(rid, 0, i, now + timedelta(seconds=g))

    def wait(self, rid: str, i: int, now: datetime, upstream_wait, by_route: dict, live_links):
        """(待ち秒, 出どころの説明)"""
        if upstream_wait is not None:
            return upstream_wait, "リアルタイム（手前を走るバス）"
        cond, e = self.conditional_wait(rid, i, now, live_links)
        chain = self.chain_wait(rid, i, now, by_route)
        dep = self.departure_wait(rid, i, now)
        base = cond if cond is not None else self.tt.wait_sec(rid, now)
        if chain is not None:
            if dep is not None:
                return (chain + base + dep) / 3, "折り返してくるバス＋前のバスからの経過＋実際の発車の時刻表"
            return 0.5 * chain + 0.5 * base, "折り返してくるバス＋前のバスからの経過"
        if dep is not None:
            return dep, "次のバスは始発を出る前（実際の発車の時刻表）"
        if cond is not None:
            return cond, f"前のバスが {e / 60:.0f} 分前に通過"
        return None, None


class PassageTimetable:
    """事前計画（リアルタイムを使わない）の待ち時間: 「実際の通過の時刻表」（docs 14章の W11）。

    指定した日の GPS で、各停留所をバスが実際に通った時刻を、路線 × 停留所 × 平日/休日 ごとに並べておく。
    出発時刻 t の待ち時間 = 同じ平日/休日の各日について「t 以降に次のバスが通るまでの時間」（4 時間以内）の中央値。
    3 日分以上なければ None（呼び出し側は過去の到着間隔の E[H²]/(2E[H]) を使う）。
    検証（10/25〜31、3,000 件、学習は 10/1〜24）で事前計画の待ち時間の誤差中央値 58.7% → 49.5%（−9.2 ポイント）。
    土曜を日曜と分けると悪化した（土曜が 4 日しかない）。
    """

    # 再現の出発を ±この秒数だけ 2 分おきにずらしてまとめる（docs 17章。較正の週で 0・5・10 分を比べて決めた）
    jitter_s = 600.0

    def __init__(self, days):
        con = C.connect()
        con.register("dd", pd.DataFrame({"date": days, "k": range(len(days)), "dt": [C.day_type(d) for d in days]}))
        df = con.execute(f"""
            SELECT CAST(p.route_id AS VARCHAR) AS route_id, p.seq, dd.dt,
                   CAST(dd.k * 86400 + hour(timezone('{C.TZ}', p.ts)) * 3600 + minute(timezone('{C.TZ}', p.ts)) * 60
                        + second(timezone('{C.TZ}', p.ts)) AS INTEGER) AS v
            FROM read_parquet({passages_glob(days)}) p JOIN dd ON dd.date = p.date
            ORDER BY 1, 2, 3, 4""").df()
        self.v = df.v.to_numpy()
        g = df.groupby(["route_id", "seq", "dt"], sort=False).size()
        ends = np.cumsum(g.to_numpy())
        self.idx = {k: (int(e - n), int(e)) for k, n, e in zip(g.index, g.to_numpy(), ends)}
        self.days_of = {dt: [k for k, d in enumerate(days) if C.day_type(d) == dt] for dt in ("weekday", "weekend")}

    def wait(self, rid: str, i: int, t: datetime):
        dt = C.day_type(t.date())
        se = self.idx.get((str(rid), int(i), dt))
        if se is None:
            return None
        x = self.v[se[0]:se[1]]
        sec = t.hour * 3600 + t.minute * 60 + t.second
        gaps = []
        for k in self.days_of[dt]:
            p = np.searchsorted(x, k * 86400 + sec)
            if p < len(x) and x[p] < (k + 1) * 86400 and x[p] - (k * 86400 + sec) <= 4 * 3600:
                gaps.append(x[p] - (k * 86400 + sec))
        return float(np.median(gaps)) if len(gaps) >= 3 else None

    def _next(self, rid, i, dt, k, sec):
        se = self.idx.get((str(rid), int(i), dt))
        if se is None:
            return None
        x = self.v[se[0]:se[1]]
        p = np.searchsorted(x, k * 86400 + sec)
        if p < len(x) and x[p] < (k + 1) * 86400 and x[p] - (k * 86400 + sec) <= 4 * 3600:
            return float(x[p] - k * 86400)
        return None

    def _prev(self, rid, i, dt, k, sec):
        """日 k に停留所 i を sec 以前に最後に通ったバスの時刻（その日の 0 時からの秒）。無ければ None。"""
        se = self.idx.get((str(rid), int(i), dt))
        if se is None:
            return None
        x = self.v[se[0]:se[1]]
        p = np.searchsorted(x, k * 86400 + sec, side="right") - 1
        if p >= 0 and x[p] >= k * 86400:
            return float(x[p] - k * 86400)
        return None

    def latest_departures(self, legs, target: datetime, walk_last_s: float, max_total_s: float = 4 * 3600):
        """到着時刻を指定する検索（docs 16.9）: 同じ平日/休日の過去の各日について、target までに着ける最も遅い出発
        （その日の 0 時からの秒）。journey を後ろからたどる: 最後の乗車は「target − 最後の徒歩 − 乗車時間」以前に
        その停留所を最後に通ったバスに乗ったことにし、乗り換えも同じようにさかのぼる。乗車時間を固定すると、遅く出るほど
        遅く着く（先に出たバスを後のバスが追い越さない）ので、その日はこの出発までに出れば target までに着く。
        max_total_s より前に出ないと着けない日と、バスが無い日は -inf。同じ平日/休日の日が 3 日未満なら None。
        legs は journey と同じ [(route_id, 乗車 seq, 乗る前の徒歩の秒, 乗車時間の秒), ...]。"""
        dt = C.day_type(target.date())
        sec_t = target.hour * 3600 + target.minute * 60 + target.second
        out = []
        for k in self.days_of[dt]:
            s = sec_t - walk_last_s
            for rid, i, walk_s, ride_s in reversed(legs):
                b = self._prev(rid, i, dt, k, s - ride_s)
                if b is None:
                    s = -np.inf
                    break
                s = b - walk_s
            out.append(s if sec_t - s <= max_total_s else -np.inf)
        if len(out) < 3:
            return None
        return np.asarray(out, float)

    def journey(self, legs, t: datetime, walk_last_s: float):
        """経路全体を、同じ平日/休日の過去の各日に「同じ時刻に出ていたら」で辿った合計の中央値（docs 16章）。

        legs: [(route_id, 乗車 seq, 乗る前の徒歩の秒, 乗車時間の秒), ...]。各日 k について、歩いて停留所に着いた時刻以降に
        その日実際に最初に通ったバスに乗り、乗車時間（モデルの中央値）を足し、乗り換えも同じように辿る。
        4 時間以内にバスが来なかった日は「着けなかった日」として inf で中央値に入れる（半分以上の日に着けなければ inf）。
        今の待ちの予測（wait）は来なかった日を捨てるので、めったに走らない路線の待ちを短く見積もり、
        経路検索でそれが 1 位に選ばれていた（検証週に 1 位の案の 38% でバスが来なかった）。
        その停留所でバスの通過が一度も記録されていない（路線・停留所・平日/休日）は、どの日も着けなかったとみなす。
        返り値: {"median_s", "q85_s", "served"（着けた日の割合）, "days", "tot"（日ごとの合計の秒、着けない日は inf）}。
        同じ平日/休日の日が 3 日未満なら None。
        """
        if getattr(self, "jitter_s", 0) > 0:
            # 出発を ±jitter_s の範囲で 2 分おきにずらした再現もまとめる（docs 17章）。ちょうどその分に過去の日のバスが
            # 来ていた案が「待ちが短い」と選ばれ、検証の日には外れる（選んだことによる偏り）のを和らげる
            off = np.arange(-self.jitter_s, self.jitter_s + 1, 120, dtype=float)
            m = self.journey_many(legs, t, off, walk_last_s)
            if m is None:
                return None
            tot = (m - off[:, None]).ravel()
            return {"median_s": float(np.median(tot)), "q85_s": float(np.quantile(tot, 0.85, method="higher")),
                    "served": float(np.isfinite(tot).mean()), "days": int(m.shape[1]), "tot": tot}
        dt = C.day_type(t.date())
        sec0 = t.hour * 3600 + t.minute * 60 + t.second
        tot = []
        for k in self.days_of[dt]:
            s = sec0
            for rid, i, walk_s, ride_s in legs:
                s += walk_s
                b = self._next(rid, i, dt, k, s)
                if b is None:
                    s = np.inf
                    break
                s = b + ride_s
            tot.append(s + walk_last_s - sec0)
        if len(tot) < 3:
            return None
        tot = np.asarray(tot, float)
        # 85% 点（余裕を見た時間）。検証週の 1 位の案で、実際にこの内に着いたのは 85.1%（docs 16章）
        return {"median_s": float(np.median(tot)), "q85_s": float(np.quantile(tot, 0.85, method="higher")),
                "served": float(np.isfinite(tot).mean()), "days": int(len(tot)), "tot": tot}

    def journey_many(self, legs, t: datetime, offsets_s, walk_last_s: float):
        """journey と同じ再現を、出発を offsets_s（秒の配列、inf も可）だけずらした何通りかでまとめて行う（docs 16.6・16.7）。
        返り値: [ずらし方, 日] の合計の秒（t から測る。着けない日は inf）。同じ平日/休日の日が 3 日未満なら None。"""
        dt = C.day_type(t.date())
        days = self.days_of[dt]
        if len(days) < 3:
            return None
        off = np.asarray(offsets_s, float)
        sec0 = t.hour * 3600 + t.minute * 60 + t.second
        out = np.full((len(off), len(days)), np.inf)
        fin = np.isfinite(off)
        for c, k in enumerate(days):
            s = sec0 + off[fin]
            for rid, i, walk_s, ride_s in legs:
                s = s + walk_s
                se = self.idx.get((str(rid), int(i), dt))
                if se is None:
                    s = np.full_like(s, np.inf)
                    break
                x = self.v[se[0]:se[1]]
                q = k * 86400 + s
                ok = np.isfinite(q)
                p = np.searchsorted(x, np.where(ok, q, 0))
                nxt = np.where(p < len(x), x[np.minimum(p, len(x) - 1)], np.inf)
                good = ok & (p < len(x)) & (nxt < (k + 1) * 86400) & (nxt - q <= 4 * 3600)
                s = np.where(good, nxt - k * 86400 + ride_s, np.inf)
            out[fin, c] = s + walk_last_s - sec0
        return out
