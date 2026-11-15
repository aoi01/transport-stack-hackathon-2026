"""問題2: 電子乗車券から、路線 × 区間 × 時間帯ごとの車内人数と混雑度を推定する。

手順:
  1. 乗車券の route（例 8UP）を GTFS の route_short_name で route_id に対応づける（上り/下りは別 route_id）。
  2. 乗車・降車の停留所名を、その路線の代表パターンの停留所名と照合する
     （正規化した完全一致 → 表記ゆれはあいまい一致 rapidfuzz で 85 点以上）。
     乗車 seq i、降車 seq j（i より後で最初に出てくる同名停留所）。j <= i の券は捨てる。
  3. 券 1 枚の乗客（passenger_count 人）は、乗車時刻の時間帯に区間 i→i+1, …, j-1→j に乗っていたとみなす。
  4. 路線 × 区間 × 日 × 時間帯の「乗っていた人数（標本）」を、その日・時間帯にその路線を走った便の数で割り、
     1便あたりの標本人数にする。便の数は GPS で実際に走った便（GPS が無い路線は GTFS の時刻表）。
  5. 電子乗車券は全バス乗車券の 3〜4% しか捕捉していない（ハッカソンのブリーフ）。中央値 3.5% として
     拡大係数 1/0.035 ≈ 28.6 を掛け、全乗客ベースの車内人数にする（3% と 4% の場合も幅として出す）。
  6. 定員の仮定（標準 12m 車、座席 35、快適な立席を含め 60）で 3 段階に分ける:
       座れる（≤35人）/ 立つ（35〜60人）/ 混雑（>60人）
  7. 信頼度は、そのマスの推定に使った券の枚数 n で決める（ポアソン近似で相対誤差 ≈ 1/√n）:
       高: n ≥ 30（±30% 以内）/ 中: 10 ≤ n < 30 / 低: n < 10
"""
from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from . import common as C
from .traveltime import passages_glob

CAPTURE_SHARE = 0.035                  # 電子乗車券の捕捉率（3〜4% の中央）
EXPANSION = 1 / CAPTURE_SHARE          # ≈ 28.6
SEATS = 35
COMFORT = 60
CRUSH = 100   # 12m 車の詰め込み時の上限の目安
LEVELS = ["座れる", "立つ", "混雑"]


def norm(s: str) -> str:
    s = str(s).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b(bus stop|bus stand|busstop|stop)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def level(load: float) -> str:
    if load <= SEATS:
        return LEVELS[0]
    if load <= COMFORT:
        return LEVELS[1]
    return LEVELS[2]


def confidence(n: float) -> str:
    return "高" if n >= 30 else ("中" if n >= 10 else "低")


def match_stops(tk: pd.DataFrame, pat: pd.DataFrame) -> pd.DataFrame:
    """(route_id, 停留所名) → 代表パターン上の seq の一覧。"""
    pat = pat.assign(nname=pat.stop_name.map(norm))
    by_route = {r: g for r, g in pat.groupby("route_id")}
    # GTFS の停留所名は「A / B」のように複数の呼び名をつないでいるので、"/" で分けた各部分も候補にする
    parts = pat.assign(part=pat.stop_name.str.split("/")).explode("part")
    parts["pname"] = parts.part.map(norm)
    parts = parts[parts.pname != ""]
    parts_by_route = {r: g for r, g in parts.groupby("route_id")}
    pairs = pd.concat([
        tk[["route_id", "start_stop_name"]].rename(columns={"start_stop_name": "name"}),
        tk[["route_id", "end_stop_name"]].rename(columns={"end_stop_name": "name"}),
    ]).drop_duplicates()
    # 全停留所の名前 → 座標（路線の代表パターンに無い停留所 ID の名前でも場所が分かるように）
    allst = C.stops().assign(nname=lambda d: d.stop_name.map(norm))
    name_xy = {n: g[["stop_lat", "stop_lon"]].to_numpy() for n, g in allst.groupby("nname")}
    all_names = list(name_xy.keys())
    rows = []
    for r in pairs.itertuples():
        g = by_route.get(r.route_id)
        if g is None:
            continue
        nn = norm(r.name)
        pg = parts_by_route[r.route_id]
        hit = g[g.nname == nn]
        how = "exact"
        if hit.empty:
            hit = g[g.seq.isin(pg[pg.pname == nn].seq)]
        if hit.empty:
            # あいまい一致：語の並びの近さ（token_sort）と、片方の語がもう片方に含まれるか（token_set）
            cands = pg.pname.unique().tolist()
            sc = [(0.5 * fuzz.token_sort_ratio(nn, c) + 0.5 * fuzz.token_set_ratio(nn, c), c) for c in cands]
            s_best, c_best = max(sc) if sc else (0, None)
            if s_best >= 85:
                hit = g[g.seq.isin(pg[pg.pname == c_best].seq)]
                how = "fuzzy"
        if hit.empty:
            # 退避: 全停留所から名前で場所を引き、その路線で 400m 以内の最寄り停留所に寄せる
            key = nn if nn in name_xy else None
            if key is None:
                b2 = process.extractOne(nn, all_names, scorer=fuzz.token_sort_ratio)
                key = b2[0] if b2 is not None and b2[1] >= 90 else None
            if key is not None:
                xy = name_xy[key]
                d = np.min(C.dist_m(g.stop_lat.to_numpy()[:, None], g.stop_lon.to_numpy()[:, None],
                                    xy[None, :, 0], xy[None, :, 1]), axis=1)
                if d.min() <= 400:
                    hit = g.iloc[[int(np.argmin(d))]]
                    how = "nearby"
        if hit.empty:
            continue
        rows.append((r.route_id, r.name, sorted(hit.seq.tolist()), how))
    return pd.DataFrame(rows, columns=["route_id", "name", "seqs", "how"])


def build_tickets() -> pd.DataFrame:
    """乗車券を読み、路線・乗車 seq・降車 seq を付けた表を返す（data/processed/tickets_matched.parquet）。"""
    out = C.PROCESSED / "tickets_matched.parquet"
    if out.exists():
        return pd.read_parquet(out)
    con = C.connect()
    tk = con.execute(f"""
        SELECT CAST(passenger_count AS INT) AS pax, TRY_CAST(amount AS DOUBLE) AS amount,
               NULLIF(NULLIF(vehicle_number, 'NULL'), '') AS vehicle_number,
               route, start_stop_name, end_stop_name, is_ac,
               CAST(created_at AS TIMESTAMPTZ) AS created_at
        FROM read_csv('{C.TICKETS.as_posix()}', all_varchar=true)
    """).df()
    tk["created_at"] = tk.created_at.dt.tz_convert(C.TZ)
    r = C.routes()[["route_id", "route_short_name"]].rename(columns={"route_short_name": "route"})
    tk = tk.merge(r, on="route", how="left")
    n0 = len(tk)
    pat = C.patterns()
    mt = match_stops(tk.dropna(subset=["route_id"]), pat)
    look = {(a, b): s for a, b, s in zip(mt.route_id, mt.name, mt.seqs)}
    how = {(a, b): h for a, b, h in zip(mt.route_id, mt.name, mt.how)}
    i_list, j_list, h_list = [], [], []
    for rid, s, e in zip(tk.route_id, tk.start_stop_name, tk.end_stop_name):
        si, se = look.get((rid, s)), look.get((rid, e))
        if not si or not se:
            i_list.append(-1); j_list.append(-1); h_list.append(None)
            continue
        i = si[0]
        later = [x for x in se if x > i]
        j = later[0] if later else -1
        i_list.append(i); j_list.append(j)
        hs = {how[(rid, s)], how[(rid, e)]}
        h_list.append("nearby" if "nearby" in hs else ("fuzzy" if "fuzzy" in hs else "exact"))
    tk["i"], tk["j"], tk["match"] = i_list, j_list, h_list
    tk["date"] = tk.created_at.dt.date
    tk["hr"] = tk.created_at.dt.hour
    tk["day_type"] = tk.date.map(C.day_type)
    stats = {
        "tickets": n0,
        "route_matched": int(tk.route_id.notna().sum()),
        "both_stops_matched_and_forward": int((tk.j > tk.i).sum()),
    }
    print("乗車券の対応づけ:", stats)
    tk.to_parquet(out, index=False)
    return tk


def trips_per_hour(days) -> pd.DataFrame:
    """路線 × 日 × 時間帯に GPS で実際に走った便の数（GPS の無い路線は GTFS 時刻表の便数）。"""
    con = C.connect()
    g = con.execute(f"""
        SELECT CAST(route_id AS VARCHAR) AS route_id, date,
               hour(timezone('{C.TZ}', t0)) AS hr, count(*) AS trips
        FROM (SELECT date, route_id, vehicle_id, trip_id, min(ts) AS t0
              FROM read_parquet({passages_glob(days)})
              GROUP BY ALL)
        GROUP BY ALL
    """).df()
    sched = pd.read_parquet(C.PROCESSED / "schedule.parquet")
    first = sched.groupby(["route_id", "trip_id"]).t_s.min().reset_index()
    first["hr"] = (first.t_s // 3600) % 24
    sh = first.groupby(["route_id", "hr"]).size().rename("sched_trips").reset_index()
    return g, sh


def build(days=C.TRAIN_DAYS, tag: str = "train") -> pd.DataFrame:
    """路線 × 区間 × 平日/休日 × 時間帯 の混雑推定表を作る。"""
    tk = build_tickets()
    tk = tk[(tk.j > tk.i) & tk.date.isin(set(days))]
    con = C.connect()
    con.register("tk", tk[["route_id", "date", "day_type", "hr", "i", "j", "pax"]])
    seg = con.execute("""
        WITH s AS (SELECT * FROM tk, range(0, 400) r(k) WHERE k >= i AND k < j)
        SELECT route_id, k AS seq, date, day_type, hr, sum(pax) AS pax, count(*) AS n_tickets
        FROM s GROUP BY ALL
    """).df()
    trips, sched_trips = trips_per_hour(days)
    trips["date"] = pd.to_datetime(trips.date).dt.date
    # 日 × 時間帯の便数（GPS）。その路線に GPS が無い場合は時刻表の便数で代用
    day_info = pd.DataFrame({"date": days, "day_type": [C.day_type(d) for d in days]})
    ndays = day_info.groupby("day_type").size()
    gps_routes = set(trips.route_id)
    tr_dt = trips.merge(day_info, on="date").groupby(["route_id", "day_type", "hr"]).trips.sum().reset_index()
    agg = seg.groupby(["route_id", "seq", "day_type", "hr"]).agg(
        pax=("pax", "sum"), n_tickets=("n_tickets", "sum"), days_with_tickets=("date", "nunique")).reset_index()
    agg = agg.merge(tr_dt, on=["route_id", "day_type", "hr"], how="left")
    agg = agg.merge(sched_trips, on=["route_id", "hr"], how="left")
    agg["ndays"] = agg.day_type.map(ndays)
    # 路線ごとの GPS の捕捉率 = GPS で見えた便数 / 時刻表の便数。半分未満なら GPS の便数は少なすぎるので時刻表を使う
    gps_total = trips.groupby("route_id").trips.sum()
    sched_day = sched_trips.groupby("route_id").sched_trips.sum() * len(days)
    coverage = (gps_total / sched_day).reindex(sched_day.index).fillna(0)
    low_cov = set(coverage[coverage < 0.5].index) | (set(agg.route_id) - gps_routes)
    use_sched = agg.route_id.isin(low_cov) | agg.trips.isna()
    agg["trips_total"] = np.where(use_sched, agg.sched_trips * agg.ndays, agg.trips)
    # 券が出た日には少なくとも1便は走っている
    agg["trips_total"] = np.fmax(agg.trips_total.fillna(0), agg.days_with_tickets)
    agg["trips_src"] = np.where(use_sched, "時刻表", "GPS")
    agg = agg[agg.trips_total > 0].copy()
    agg["sample_per_trip"] = agg.pax / agg.trips_total
    agg["load_raw"] = agg.sample_per_trip * EXPANSION
    # 物理的な上限で頭打ちにする。上限にかかるマスは、その路線の電子乗車券の比率が平均（3.5%）より高いとみられる
    agg["capped"] = agg.load_raw > CRUSH
    agg["load"] = agg.load_raw.clip(upper=CRUSH)
    agg["load_lo"] = (agg.sample_per_trip / 0.04).clip(upper=CRUSH)   # 捕捉率 4% のとき
    agg["load_hi"] = (agg.sample_per_trip / 0.03).clip(upper=CRUSH)   # 捕捉率 3% のとき
    rel = 1.645 / np.sqrt(agg.n_tickets.clip(lower=1))   # 標本の少なさによる 90% 区間（ポアソン近似）
    agg["load_ci_lo"] = agg.load * np.clip(1 - rel, 0, None)
    agg["load_ci_hi"] = (agg.load * (1 + rel)).clip(upper=CRUSH)
    agg["level"] = agg.load.map(level)
    agg["confidence"] = agg.n_tickets.map(confidence)
    pat = C.patterns()[["route_id", "seq", "stop_id", "stop_name"]]
    agg = agg.merge(pat, on=["route_id", "seq"], how="left")
    out = C.PROCESSED / tag
    out.mkdir(parents=True, exist_ok=True)
    agg.to_parquet(out / "crowding.parquet", index=False)
    seg.to_parquet(out / "crowding_daily.parquet", index=False)
    trips.to_parquet(out / "trips_per_day_hour.parquet", index=False)
    print(f"[{tag}] 混雑推定 {len(agg):,} マス（路線 {agg.route_id.nunique():,}）→ {out}")
    return agg


class CrowdingModel:
    def __init__(self, tag: str = "train"):
        a = pd.read_parquet(C.PROCESSED / tag / "crowding.parquet")
        self.cell = {(r.route_id, r.seq, r.day_type, r.hr): (r.load, r.n_tickets, r.load_ci_lo, r.load_ci_hi)
                     for r in a.itertuples()}

    def leg(self, route_id: str, i: int, j: int, day_type: str, hr: int) -> dict:
        """乗車区間 i→j で最も混む区間の推定（乗客が体験する最悪の混雑）。"""
        best = None
        for k in range(i, j):
            v = self.cell.get((route_id, k, day_type, hr))
            if v is None:
                continue
            if best is None or v[0] > best[0]:
                best = v
        if best is None:
            return {"level": "不明", "load": None, "confidence": "データなし"}
        load, n, lo, hi = best
        return {"level": level(load), "load": round(float(load)), "load_90ci": [round(float(lo)), round(float(hi))],
                "confidence": confidence(n), "tickets_used": int(n)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    which = sys.argv[1] if len(sys.argv) > 1 else "train"
    if which == "all":
        build(C.TRAIN_DAYS + C.TEST_DAYS, "all")
    elif which == "test":
        build(C.TEST_DAYS, "test")
    else:
        build(C.TRAIN_DAYS, "train")


if __name__ == "__main__":
    main()
