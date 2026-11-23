"""Google Maps (Routes API, transit, bus only) と、この試作と、実際のバスの所要時間を同じ組で比べる。

検証（tsh.validate_journeys）と同じ 600 組の出発地・目的地・出発時刻を使う。
- この試作の予測と実際の所要時間: results/journey_replay_samples.csv（前もって計画）と _live.csv（今すぐ出る）。
  実際の所要時間 = 1 位の案に検証週（10/25〜31）の GPS どおりに乗ったときの戸口から戸口まで。
- Google: Routes API の computeRoutes（travelMode=TRANSIT, allowedTravelModes=[BUS]）。
  Routes API の公共交通は過去の日時を受け付けないので、検証週と同じ曜日・同じ時刻の、これから先の日（既定は
  2026-11-30 の週）で問い合わせる。Google の所要時間 = 到着時刻 − 頼んだ出発時刻（最初の待ちを含む）。

使い方（リポジトリの根元で。キーは .env の GOOGLE_MAPS_API_KEY）:
  python experiments/p1_google/compare.py pairs     # 600 組を作り直す（data/processed_v2/google/pairs.csv）
  python experiments/p1_google/compare.py fetch     # Google に問い合わせる（返事は data/ の下に保存、途中から再開できる）
  python experiments/p1_google/compare.py score     # results/google_compare_metrics.json と _samples.csv
Google の返事（経路そのもの）はリポジトリに入れない（data/ の下、.gitignore 済み）。
"""
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402

OUT = C.PROCESSED / "google"
RAW = OUT / "raw"
WEEK0 = date(2026, 11, 30)   # 問い合わせる週の月曜（未来でなければならない）
URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
FIELDS = ",".join([
    "routes.duration", "routes.distanceMeters",
    "routes.legs.steps.travelMode", "routes.legs.steps.staticDuration",
    "routes.legs.steps.transitDetails.stopDetails.departureTime",
    "routes.legs.steps.transitDetails.stopDetails.arrivalTime",
    "routes.legs.steps.transitDetails.stopDetails.departureStop.name",
    "routes.legs.steps.transitDetails.stopDetails.arrivalStop.name",
    "routes.legs.steps.transitDetails.transitLine.nameShort",
    "routes.legs.steps.transitDetails.transitLine.vehicle.type",
])


def rebuild_pairs() -> pd.DataFrame:
    """validate_journeys.main と同じ乱数の引き方で候補を並べ、検証の記録（距離と出発時刻）と突き合わせる。"""
    rng = np.random.default_rng(2026)
    xy = C.stops()[["stop_lat", "stop_lon"]].to_numpy()
    days = C.TEST_DAYS
    cand = {}
    for _ in range(600 * 5):
        a, b = rng.integers(len(xy), size=2)
        km = float(C.dist_m(xy[a, 0], xy[a, 1], xy[b, 0], xy[b, 1])) / 1000
        if not 3 <= km <= 15:
            continue
        d = days[int(rng.integers(len(days)))]
        dep = datetime(d.year, d.month, d.day) + timedelta(seconds=int(rng.integers(7 * 3600, 21 * 3600)))
        cand.setdefault((dep.strftime("%Y-%m-%d %H:%M:%S"), round(km, 6)), (xy[a], xy[b]))
    s = pd.read_csv(C.RESULTS / "journey_replay_samples.csv").query("rank == 0")
    rows = []
    for r in s.itertuples():
        k = (r.depart, round(r.km, 6))
        if k not in cand:
            raise SystemExit(f"組 {r.pair} が作り直せない: {k}")
        (la, lo), (lb, lob) = cand[k]
        dep = datetime.strptime(r.depart, "%Y-%m-%d %H:%M:%S")
        q = datetime.combine(WEEK0 + timedelta(days=dep.weekday()), dep.time())
        rows.append({"pair": r.pair, "km": r.km, "depart": r.depart, "query_depart": q.strftime("%Y-%m-%dT%H:%M:%S"),
                     "o_lat": la, "o_lng": lo, "d_lat": lb, "d_lng": lob})
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "pairs.csv", index=False)
    print(f"{len(df)} 組を作り直した → {OUT / 'pairs.csv'}")
    return df


def api_key() -> str:
    k = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not k and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GOOGLE_MAPS_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        raise SystemExit(".env に GOOGLE_MAPS_API_KEY=... を書いてください")
    return k


# 無料枠を超えないための上限。送ったリクエストは失敗も含めて全部 calls.json に数え、これを超えたら止める。
# Routes API の毎月の無料枠は最も高い区分（Enterprise）でも 1,000 件。600 組 + 試し・やり直しの余裕で 700。
MAX_CALLS = 700
CALLS = OUT / "calls.json"


def count_call() -> int:
    n = json.loads(CALLS.read_text())["calls"] if CALLS.exists() else 0
    if n >= MAX_CALLS:
        raise SystemExit(f"上限 {MAX_CALLS} 件に達したので止めた（無料枠を超えないため）")
    CALLS.write_text(json.dumps({"calls": n + 1, "updated": datetime.now().isoformat()}))
    return n + 1


def fetch(limit: int | None = None) -> None:
    key = api_key()
    pairs = pd.read_csv(OUT / "pairs.csv")
    RAW.mkdir(parents=True, exist_ok=True)
    n_new = 0
    for r in pairs.itertuples():
        f = RAW / f"{r.pair}.json"
        if f.exists():
            continue
        if limit is not None and n_new >= limit:
            break
        body = {
            "origin": {"location": {"latLng": {"latitude": r.o_lat, "longitude": r.o_lng}}},
            "destination": {"location": {"latLng": {"latitude": r.d_lat, "longitude": r.d_lng}}},
            "travelMode": "TRANSIT",
            "departureTime": pd.Timestamp(r.query_depart, tz=C.TZ).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "transitPreferences": {"allowedTravelModes": ["BUS"]},
            "computeAlternativeRoutes": False,
            "languageCode": "en",
        }
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
            "Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS})
        for attempt in range(3):
            count_call()
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")
                if e.code in (429, 500, 503) and attempt < 2:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise SystemExit(f"組 {r.pair}: HTTP {e.code} {msg[:500]}")
        f.write_text(json.dumps({"query": body, "response": data}, ensure_ascii=False), encoding="utf-8")
        n_new += 1
        if n_new % 50 == 0:
            print(f"  {n_new} 件", flush=True)
        time.sleep(0.05)
    print(f"新しく {n_new} 件、保存済み {len(list(RAW.glob('*.json')))} 件")


def parse(path: Path) -> dict:
    j = json.loads(path.read_text(encoding="utf-8"))
    q0 = pd.Timestamp(j["query"]["departureTime"])
    routes = j["response"].get("routes") or []
    if not routes:
        return {"g_status": "no_route"}
    steps = [s for leg in routes[0].get("legs", []) for s in leg.get("steps", [])]
    transit = [i for i, s in enumerate(steps) if s.get("travelMode") == "TRANSIT"]
    if not transit:
        return {"g_status": "walk_only", "g_total_s": float(routes[0]["duration"].rstrip("s"))}
    dur = lambda s: float((s.get("staticDuration") or "0s").rstrip("s"))
    first, last = steps[transit[0]], steps[transit[-1]]
    t_board = pd.Timestamp(first["transitDetails"]["stopDetails"]["departureTime"])
    t_alight = pd.Timestamp(last["transitDetails"]["stopDetails"]["arrivalTime"])
    walk_after = sum(dur(s) for s in steps[transit[-1] + 1:])
    arrive = t_alight + pd.Timedelta(seconds=walk_after)
    walk_before = sum(dur(s) for s in steps[:transit[0]])
    kinds = {(steps[i]["transitDetails"].get("transitLine", {}).get("vehicle", {}) or {}).get("type") for i in transit}
    return {"g_status": "ok", "g_total_s": (arrive - q0).total_seconds(),
            "g_wait0_s": (t_board - q0).total_seconds() - walk_before,
            "g_transfers": len(transit) - 1, "g_lines": " ".join(
                steps[i]["transitDetails"].get("transitLine", {}).get("nameShort", "?") for i in transit),
            "g_vehicle": ",".join(sorted(k for k in kinds if k))}


def score() -> None:
    pairs = pd.read_csv(OUT / "pairs.csv")
    g = pd.DataFrame([{"pair": int(p.stem), **parse(p)} for p in RAW.glob("*.json")])
    plan = pd.read_csv(C.RESULTS / "journey_replay_samples.csv").query("rank == 0")
    live = pd.read_csv(C.RESULTS / "journey_replay_samples_live.csv").query("rank == 0")
    df = (pairs[["pair", "km", "depart", "query_depart"]]
          .merge(plan[["pair", "pred_s", "actual_s", "sched_s", "status"]], on="pair")
          .merge(live[["pair", "pred_s", "actual_s"]].rename(columns={"pred_s": "live_pred_s", "actual_s": "live_actual_s"}),
                 on="pair", how="left")
          .merge(g, on="pair", how="left"))
    df.to_csv(C.RESULTS / "google_compare_samples.csv", index=False)

    def errs(pred, act):
        e = np.abs(pred - act) / act * 100
        m = np.abs(pred - act) / 60
        return {"n": int(len(act)), "median_abs_pct_err": round(float(np.median(e)), 1),
                "median_abs_err_min": round(float(np.median(m)), 1),
                "within_10min_%": round(float(np.mean(m <= 10) * 100), 1),
                "median_signed_err_min": round(float(np.median((pred - act) / 60)), 1)}

    out = {"note": "Same 600 OD pairs and departure times as the journey test (held-out week 25-31 Oct 2026). "
                   "Actual = door-to-door time when the planner's top option is followed on that week's GPS. "
                   "Google = Routes API transit (bus only), queried for the same weekday and time in the week of "
                   f"{WEEK0} (the API does not accept past departure times); arrival minus requested departure.",
           "pairs": int(len(df)), "google_status": df["g_status"].value_counts(dropna=False).to_dict()}
    ok = df[df.g_status.eq("ok") & df.actual_s.notna()]
    out["planning_ahead"] = {
        "pairs_scored": int(len(ok)),
        "ours": errs(ok.pred_s.to_numpy(), ok.actual_s.to_numpy()),
        "google": errs(ok.g_total_s.to_numpy(), ok.actual_s.to_numpy()),
        "gtfs_timetable": errs(ok.sched_s.dropna().to_numpy(), ok.loc[ok.sched_s.notna(), "actual_s"].to_numpy()),
    }
    # 中央値の相対誤差の差（この試作 − Google）の 95% ブートストラップ区間（組を引き直す）
    rng = np.random.default_rng(0)
    a = (np.abs(ok.pred_s - ok.actual_s) / ok.actual_s).to_numpy()
    g = (np.abs(ok.g_total_s - ok.actual_s) / ok.actual_s).to_numpy()
    bs = [np.median(a[i]) - np.median(g[i]) for i in rng.integers(len(a), size=(2000, len(a)))]
    out["planning_ahead"]["ours_minus_google_pct_points_95ci"] = [round(float(np.percentile(bs, q)) * 100, 1) for q in (2.5, 97.5)]
    okl = df[df.g_status.eq("ok") & df.live_actual_s.notna()]
    out["leaving_now"] = {
        "pairs_scored": int(len(okl)),
        "ours": errs(okl.live_pred_s.to_numpy(), okl.live_actual_s.to_numpy()),
        "google": errs(okl.g_total_s.to_numpy(), okl.live_actual_s.to_numpy()),
    }
    # Google が選んだ経路そのものを検証週の GPS で再現できた組（google_replay.csv、replay で作る）。
    # 置き換えは路線名と停留所名と位置で行うので、全部の組ではできない
    rp_path = OUT / "google_replay.csv"
    if rp_path.exists():
        gr = pd.read_csv(rp_path)
        df2 = df.merge(gr, on="pair", how="left")
        mapped = df2[df2.g_map.isin(["ok", "nobus", "untracked"])]
        own = df2[df2.g_map.eq("ok") & df2.actual_s.notna()]
        out["google_own_route"] = {
            "pairs_mapped_to_gtfs": int(len(mapped)),
            "mapped_google_bus_never_came_%": round(float(mapped.g_map.eq("nobus").mean() * 100), 1),
            "pairs_scored": int(len(own)),
            "google_estimate_vs_google_route_actual": errs(own.g_total_s.to_numpy(), own.g_actual_s.to_numpy()),
            "ours_estimate_vs_our_route_actual": errs(own.pred_s.to_numpy(), own.actual_s.to_numpy()),
            "actual_minutes_google_route_minus_ours_median": round(float(np.median((own.g_actual_s - own.actual_s) / 60)), 1),
            "our_route_actually_faster_%": round(float(np.mean(own.actual_s < own.g_actual_s) * 100), 1),
        }
        df2.to_csv(C.RESULTS / "google_compare_samples.csv", index=False)
    # Google の推定は Google の経路のもの。実際の時間はこの試作の 1 位の案のもの。経路の差を見るため、
    # 実際の時間と比べずに「Google とこの試作の予測の差」も出しておく
    both = df[df.g_status.eq("ok")]
    out["google_minus_ours_planning_min_median"] = round(float(np.median((both.g_total_s - both.pred_s) / 60)), 1)
    out["google_transfers_share"] = both.g_transfers.value_counts(normalize=True).round(3).to_dict()
    (C.RESULTS / "google_compare_metrics.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


def _base(name: str) -> tuple[str, str]:
    import re
    m = re.match(r"^(.*?)(UP|DOWN)$", name)
    return (m.group(1), m.group(2)) if m else (name, "")


def map_google_route(j: dict, pat: dict, by_base: dict, o: tuple, dst: tuple):
    """Google の経路を、GTFS の route_id と停留所の順番（seq）に置き換える。置き換えられなければ (None, 理由)。

    Google の路線名（例 970）と GTFS の路線名（970UP / 970DOWN）の頭を合わせ、乗る・降りる停留所の名前を
    その路線の停留所の並びの中で探す（あいまい一致、乗る停留所が降りる停留所より前）。Google と GTFS は停留所名の
    表記がよく違うので、名前の一致はゆるめにして、位置で確かめる: 最初に乗る停留所は出発地から、最後に降りる停留所は
    目的地から、乗り換えの停留所どうしは互いに、Google の歩く時間（秒 × 1.4 m）+ 400 m 以内。"""
    from rapidfuzz import fuzz, process
    routes = j["response"].get("routes") or []
    if not routes:
        return None, "no_route"
    steps = [s for leg in routes[0].get("legs", []) for s in leg.get("steps", [])]
    walks, rides, walk = [], [], 0.0
    for s in steps:
        if s.get("travelMode") != "TRANSIT":
            walk += float((s.get("staticDuration") or "0s").rstrip("s"))
            continue
        walks.append(walk); walk = 0.0
        td = s["transitDetails"]
        rides.append((str((td.get("transitLine") or {}).get("nameShort")),
                      td["stopDetails"]["departureStop"]["name"], td["stopDetails"]["arrivalStop"]["name"]))
    walks.append(walk)
    if not rides:
        return None, "walk_only"
    cands = []
    for name, a, b in rides:
        lst = []
        for rid in by_base.get(name, []):
            g = pat[rid]
            names = g["stop_name"].tolist()
            ma = process.extract(a, names, scorer=fuzz.token_set_ratio, limit=6)
            mb = process.extract(b, names, scorer=fuzz.token_set_ratio, limit=6)
            for _, sa, ia in ma:
                for _, sb, ib in mb:
                    if sa >= 55 and sb >= 55 and ia < ib:
                        lst.append((sa + sb, rid, ia, ib))
        if not lst:
            return None, "unmatched_line" if not by_base.get(name) else "unmatched_stops"
        cands.append(sorted(lst, reverse=True)[:30])
    near = lambda p, q, w: float(C.dist_m(p[0], p[1], q[0], q[1])) <= w * 1.4 + 400
    xy = lambda rid, i: (pat[rid]["stop_lat"].iloc[i], pat[rid]["stop_lon"].iloc[i])
    best = None

    def dfs(k, prev, chosen, sc):
        nonlocal best
        if k == len(cands):
            if near(prev, dst, walks[-1]) and (best is None or sc > best[0]):
                best = (sc, list(chosen))
            return
        for c in cands[k]:
            _, rid, ia, ib = c
            if near(prev, xy(rid, ia), walks[k]):
                chosen.append(c); dfs(k + 1, xy(rid, ib), chosen, sc + c[0]); chosen.pop()

    dfs(0, o, [], 0)
    if best is None:
        return None, "unmatched_place"
    legs = []
    for k, (_, rid, ia, ib) in enumerate(best[1]):
        legs.append({"mode": "walk", "minutes": walks[k] / 60})
        legs.append({"mode": "bus", "route_id": rid, "board": {"seq": int(pat[rid]["seq"].iloc[ia])},
                     "alight": {"seq": int(pat[rid]["seq"].iloc[ib])}})
    legs.append({"mode": "walk", "minutes": walks[-1] / 60})
    return {"legs": legs}, "ok"


def replay_google() -> None:
    """Google が選んだ経路に、検証週の同じ日・同じ時刻に GPS どおりに乗ったら何分かかったか。"""
    from tsh.planner import Planner
    from tsh.validate_journeys import Replay, load_passages, replay_option_status
    pairs = pd.read_csv(OUT / "pairs.csv")
    pat_df = C.patterns()
    pat = {rid: g.reset_index(drop=True) for rid, g in pat_df.groupby("route_id")}
    by_base: dict = {}
    for rid, nm in pat_df.groupby("route_id")["route_short_name"].first().items():
        by_base.setdefault(_base(str(nm))[0], []).append(rid)
    P = Planner("train")
    rp = Replay(load_passages(C.TEST_DAYS), P.tt.cum, tt=P.tt)
    rows = []
    for r in pairs.itertuples():
        f = RAW / f"{r.pair}.json"
        opt, why = map_google_route(json.loads(f.read_text(encoding="utf-8")), pat, by_base,
                                    (r.o_lat, r.o_lng), (r.d_lat, r.d_lng))
        act = None
        if opt is not None:
            dep = datetime.strptime(r.depart, "%Y-%m-%d %H:%M:%S")
            t0 = pd.Timestamp(dep, tz=C.TZ).timestamp()
            act, why = replay_option_status(rp, opt, dep.date(), t0)
        rows.append({"pair": r.pair, "g_map": why, "g_actual_s": act})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "google_replay.csv", index=False)
    print(out.g_map.value_counts().to_dict())


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pairs":
        rebuild_pairs()
    elif cmd == "fetch":
        fetch(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "replay":
        replay_google()
    elif cmd == "score":
        score()
    else:
        print(__doc__)
