"""走りの途中で便の番号が変わる・別の路線に変わる現象を、検証週の GPS と時刻表で調べる。

1. 車両ごとに便（GPS の trip_id = 路線_時_分[_番号]）を時刻順に並べ、前の便が終点の手前で終わった組を分類する。
   - 同じ路線で、後ろの便が前の便の続きの停留所から始まる（番号だけの付け替え）
   - 同じ系統の逆向き（折り返し）／別の系統
   - 前の便の名前（時_分）が時刻表の SHORT 便（途中止まりの予定の便）と一致するか
2. 番号の付け替えの時刻を、時刻表と比べる:
   - 付け替えの時刻 − 新しい便の名前の時刻（始発の予定の発車）
   - その場所での、前の便と新しい便それぞれの時刻表からの遅れ
使い方: PYTHONPATH=src python experiments/p1_passages/trip_switch.py
"""
from __future__ import annotations

import json
import re
import sys

import numpy as np
import pandas as pd

from tsh import common as C

DAYS = C.TEST_DAYS


def load_day(con, d):
    g = con.execute(f"""
        select vehicle_id, trip_id, any_value(route_id) route_id,
               min(epoch(ts)) g0, max(epoch(ts)) g1, count(*) n_gps
        from '{C.ROOT / "data/interim/bus_gps"}/date={d}/*.parquet'
        group by vehicle_id, trip_id""").df()
    p = con.execute(f"""
        select vehicle_id, trip_id, arg_min(seq, ts) s0, min(epoch(ts)) p0, arg_min(stop_id, ts) stop0,
               arg_max(seq, ts) s1, max(epoch(ts)) p1, arg_max(stop_id, ts) stop1, count(*) n_pass,
               list(stop_id order by ts) stops
        from '{C.INTERIM / "stop_passages_v2"}/date={d}/*.parquet'
        group by vehicle_id, trip_id""").df()
    t = g.merge(p, on=["vehicle_id", "trip_id"], how="inner")
    t["date"] = d
    return t


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    con = C.connect()
    pat = pd.read_parquet(C.PROCESSED / "patterns.parquet")
    plen = pat.groupby("route_id").seq.max().to_dict()
    route_stops = pat.groupby("route_id").stop_id.apply(list).to_dict()
    routes = pd.read_csv(C.GTFS / "routes.txt", dtype=str)
    rname = dict(zip(routes.route_id, routes.route_short_name))
    line = {r: re.sub(r"(UP|DOWN|DN)$", "", (n or "").upper().strip()) for r, n in rname.items()}
    trips = pd.read_csv(C.GTFS / "trips.txt", dtype=str)
    st = pd.read_csv(C.GTFS / "stop_times.txt", dtype=str, usecols=["trip_id", "arrival_time", "stop_id"])
    hms = st.arrival_time.str.split(":", expand=True).astype(int)
    st["sec"] = hms[0] * 3600 + hms[1] * 60 + hms[2]
    sched = st.set_index(["trip_id", "stop_id"]).sec.to_dict()
    short_last = st.groupby("trip_id").stop_id.last()
    gtfs_ids = set(trips.trip_id)

    t = pd.concat([load_day(con, d) for d in DAYS], ignore_index=True)
    t["route_id"] = t.route_id.astype(str)
    m = t.trip_id.str.extract(r"^(\d+)_(\d+)_(\d+)")
    t["hh"], t["mm"] = m[1].astype(float), m[2].astype(float)
    t["L"] = t.route_id.map(plen)
    t = t.dropna(subset=["L", "hh"]).sort_values(["date", "vehicle_id", "p0"]).reset_index(drop=True)
    print("便（GPS の trip_id × 車両、通過のあるもの）:", len(t), flush=True)

    # 時刻表の便の名前: 路線_FULL_時_分 / 路線_SHORT_時_分
    key = t.route_id + "_" + t.hh.astype(int).map("{:02d}".format) + "_" + t.mm.astype(int).map("{:02d}".format)
    t["full_id"] = key.str.replace(r"^(\d+)_", r"\1_FULL_", regex=True)
    t["short_id"] = key.str.replace(r"^(\d+)_", r"\1_SHORT_", regex=True)
    t["is_full"] = t.full_id.isin(gtfs_ids)
    t["is_short"] = t.short_id.isin(gtfs_ids)

    nxt = t.groupby(["date", "vehicle_id"]).shift(-1)
    pair = t.join(nxt, rsuffix="_b")
    pair = pair[pair.trip_id_b.notna()].copy()
    pair["mid"] = pair.s1 < pair.L - 2            # 前の便が終点の 3 停留所より手前で終わった
    pair["gap_label_s"] = pair.g0_b - pair.g1     # 番号が途切れていた時間（GPS）
    same = pair.route_id == pair.route_id_b
    cont = same & (pair.s0_b >= pair.s1)
    rev = (~same) & (pair.route_id.map(line) == pair.route_id_b.map(line))

    res = {"便": int(len(t)), "時刻表の名前と一致": {"FULL": round(t.is_full.mean() * 100, 1),
                                                   "SHORT": round(t.is_short.mean() * 100, 1),
                                                   "どちらも無い": round((~t.is_full & ~t.is_short).mean() * 100, 1)}}
    mid = pair[pair.mid]
    res["次の便がある組"] = int(len(pair))
    res["前の便が終点の手前で終わった組"] = int(len(mid))
    cats = {
        "同じ路線の続き（番号だけ付け替え）": cont[pair.mid],
        "同じ路線で戻って始まる": (same & ~cont)[pair.mid],
        "同じ系統の逆向き（折り返し）": rev[pair.mid],
        "別の系統": ((~same) & (~rev))[pair.mid],
    }
    res["終点の手前で終わった後の行き先_%"] = {k: round(v.mean() * 100, 1) for k, v in cats.items()}

    # 予定の途中止まり（SHORT）で説明できるか: 前の便の名前が SHORT 便と一致し、その終点の近くで終わった
    def short_ok(r):
        if not r.is_short or r.is_full:
            return False
        last = short_last.get(r.short_id)
        if last is None:
            return False
        rs = route_stops.get(r.route_id, [])
        if last not in rs:
            return False
        return abs(rs.index(last) - r.s1) <= 3
    mid = mid.assign(planned_short=[short_ok(r) for r in mid.itertuples()])
    res["終点の手前で終わった組のうち、予定の SHORT 便の終点で終わった_%"] = round(mid.planned_short.mean() * 100, 1)
    for k, v in cats.items():
        sub = mid[v.loc[mid.index]]
        res.setdefault("行き先ごと", {})[k] = {
            "組": int(len(sub)), "SHORT 便の終点で終わった_%": round(sub.planned_short.mean() * 100, 1) if len(sub) else None,
            "番号が途切れた時間_中央値_秒": round(float(sub.gap_label_s.median()), 0) if len(sub) else None,
            "1 分以内に次の番号_%": round(float((sub.gap_label_s <= 60).mean()) * 100, 1) if len(sub) else None}

    # 番号の付け替え（同じ路線の続き）の時刻と時刻表
    c = pair[pair.mid & cont].copy()
    day0 = pd.to_datetime(c.date.astype(str)).map(lambda x: pd.Timestamp(x, tz=C.TZ).timestamp())
    c["sw"] = c.g0_b - day0                                  # 付け替えた時刻（その日の IST の秒）
    c["name_b"] = c.hh_b * 3600 + c.mm_b * 60                # 新しい便の名前の時刻
    c["name_a"] = c.hh * 3600 + c.mm * 60
    c["sw_minus_name_b_min"] = (c.sw - c.name_b) / 60
    # その場所（新しい便の最初の通過）での遅れ: 前の便の時刻表 / 新しい便の時刻表
    def delay(r, tid):
        s = sched.get((tid, r.stop0_b))
        return None if s is None else (r.p0_b - r.d0) - s
    c["d0"] = day0
    c["delay_old_min"] = [None if (x := delay(r, r.full_id)) is None else x / 60 for r in c.itertuples()]
    c["delay_new_min"] = [None if (x := delay(r, r.full_id_b)) is None else x / 60 for r in c.itertuples()]
    q = lambda s: [round(float(x), 1) for x in np.nanpercentile(s.astype(float), [10, 25, 50, 75, 90])]
    res["番号の付け替え"] = {
        "組": int(len(c)),
        "付け替えの時刻 − 新しい便の名前の時刻（分、10/25/50/75/90%点）": q(c.sw_minus_name_b_min),
        "付け替えが新しい便の名前の時刻の ±2 分以内_%": round(float((c.sw_minus_name_b_min.abs() <= 2).mean()) * 100, 1),
        "新しい便の名前 − 前の便の名前（分、10/25/50/75/90%点）": q((c.name_b - c.name_a) / 60),
        "その場所での遅れ: 前の便の時刻表（分、10/25/50/75/90%点）": q(c.delay_old_min.dropna()),
        "その場所での遅れ: 新しい便の時刻表（分、10/25/50/75/90%点）": q(c.delay_new_min.dropna()),
        "新しい便の時刻表のほうが近い_%": round(float((c.delay_new_min.abs() < c.delay_old_min.abs())[
            c.delay_new_min.notna() & c.delay_old_min.notna()].mean()) * 100, 1),
    }
    # 比べる相手: 付け替えの無い便の、途中の停留所での遅れ（前の便の最後の通過の時点）
    ok = pair[~pair.mid].copy()
    ok["d0"] = pd.to_datetime(ok.date.astype(str)).map(lambda x: pd.Timestamp(x, tz=C.TZ).timestamp())
    s = [(r.p1 - r.d0) - sched[(r.full_id, r.stop1)] for r in ok.itertuples() if (r.full_id, r.stop1) in sched]
    res["参考: 終点まで走った便の、終点での遅れ（分、10/25/50/75/90%点）"] = q(pd.Series(s) / 60)

    # 別の系統・折り返しのとき: 後ろの便の最初の 5 停留所が、前の便の路線の先の停留所か
    def downstream(r):
        rs = route_stops.get(r.route_id, [])
        ahead = set(rs[int(r.s1) + 1:]) if rs else set()
        first = list(r.stops_b)[:5]
        return np.mean([s in ahead for s in first]) if first else np.nan
    o = mid[cats["別の系統"].loc[mid.index] | cats["同じ系統の逆向き（折り返し）"].loc[mid.index]]
    o = o.assign(ahead=[downstream(r) for r in o.itertuples()])
    res["路線が変わった組: 後ろの便の最初の 5 停留所が前の路線の先の停留所だった割合"] = {
        "半分以上が先の停留所（同じ道を進み続けた）_%": round(float((o.ahead >= 0.5).mean()) * 100, 1),
        "1 つも無い（別の道へ）_%": round(float((o.ahead == 0).mean()) * 100, 1)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    (C.RESULTS / "trip_switch.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    c.drop(columns=["stops", "stops_b"]).to_csv(C.RESULTS / "trip_switch_samples.csv", index=False)


if __name__ == "__main__":
    main()
