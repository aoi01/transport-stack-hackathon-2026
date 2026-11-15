"""API 用の待ち時間モデル（docs/phase1_prototype.md 12章の「W8」）。

最初のバスの待ち時間を、次の順で決める（出発が今から 15 分以内のとき）:
  1. 乗車停留所より手前を走っている同じ路線のバスが見えれば、その到着予測（tsh.realtime と同じ）
  2. 見えなければ、反対方向の路線を走っていて折り返してくるバスの到着予測（折り返しの組と終点での休憩は 10 月の実績から）と、
     「停留所を最後のバスが通ってからの経過時間」で条件づけた残りの待ち時間 E[H − e | H > e] の平均（半々、事前に決めた重み）
  3. 折り返しのバスも無ければ、経過時間で条件づけた残りの待ち時間。経過時間が分からなければ過去の実績 E[H²]/(2E[H])
検証（10/25〜31、3,000 件）で待ち時間の誤差中央値 36.6% → 33.3%、待ち時間込みの合計 24.9% → 23.5%。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from . import common as C
from .improve_wait import Residual, chaining, headway_samples

SERVE = C.PROCESSED / "serve"
IST = timezone(timedelta(hours=5, minutes=30))


class WaitModel:
    def __init__(self, tt):
        self.tt = tt
        SERVE.mkdir(parents=True, exist_ok=True)
        hw_path, fd_path = SERVE / "headways.parquet", SERVE / "feeders.json"
        days = C.TRAIN_DAYS + C.TEST_DAYS
        if not hw_path.exists():
            headway_samples(days).to_parquet(hw_path, index=False)
        if not fd_path.exists():
            fd, stats = chaining(days, tt)
            fd_path.write_text(json.dumps({"feeders": fd, "stats": stats}, ensure_ascii=False), encoding="utf-8")
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

    def wait(self, rid: str, i: int, now: datetime, upstream_wait, by_route: dict, live_links):
        """(待ち秒, 出どころの説明)"""
        if upstream_wait is not None:
            return upstream_wait, "リアルタイム（手前を走るバス）"
        cond, e = self.conditional_wait(rid, i, now, live_links)
        chain = self.chain_wait(rid, i, now, by_route)
        base = cond if cond is not None else self.tt.wait_sec(rid, now)
        if chain is not None:
            return 0.5 * chain + 0.5 * base, "折り返してくるバス＋前のバスからの経過"
        if cond is not None:
            return cond, f"前のバスが {e / 60:.0f} 分前に通過"
        return None, None
