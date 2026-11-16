"""GPS で乗車停留所を推定して、停留所名の照合を「確かめる」「補う」実験。

車両番号つきの券は、買った瞬間のバスの位置が GPS でわかる（券の vehicle_number = GPS の vehicle_id）。
乗客はたいてい乗った直後に買うので、その位置の最寄りの停留所は乗車停留所か、その1つ先になる。
同じ（路線, 乗車停留所名）の券を何枚も集めて多数決（ずれの分布で重みを付けた投票）を取れば、
名前の文字列を見ずに、その名前がどの停留所かを推定できる。

  1. ずれの分布 P(k)：名前が完全一致で1か所に決まる券で、k = 購入時の最寄りの停留所の seq − 乗車停留所の seq を数える
  2. 投票：（路線, 名前）ごとに、各停留所 s の点数 = Σ_券 P(最寄りの seq − s)。首位を推定とする
  3. 確かめ：完全一致の名前を隠して当てさせ、正解率を測る（件数ごと）
  4. 今の照合の点検：あいまい一致・距離での退避で決めた停留所と、GPS の推定が合うか
  5. 補う：今は照合できない名前のうち、GPS で決まるものの量と例

使い方: python -X utf8 experiments/ticket_gps/alias_from_gps.py [開始日 終了日]
出力:   標準出力と experiments/ticket_gps/out/ （data/ 由来の名前を含むので git には入れない）
"""
from __future__ import annotations

import sys
import time
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402
from tsh.crowding import match_stops, norm  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
KMIN, KMAX = -3, 6          # ずれ k の範囲（これより外は投票に使わない）
MAX_LAG_S = 60              # 購入の何秒前までの GPS の点を使うか
MAX_OFF_M = 300             # バスが券の路線の停留所から何 m 以内なら使うか


def days_between(a: str, b: str):
    d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
    return [d0 + timedelta(n) for n in range((d1 - d0).days + 1)]


def load_tickets(con) -> pd.DataFrame:
    tk = pd.read_parquet(C.PROCESSED / "tickets_matched.parquet",
                         columns=["vehicle_number", "route_id", "start_stop_name", "end_stop_name", "created_at", "date", "pax"])
    tk = tk[tk.route_id.notna()].reset_index(drop=True)
    tk["tid"] = np.arange(len(tk))
    return tk


def per_end_match(tk: pd.DataFrame) -> pd.DataFrame:
    """（路線, 名前）ごとの今の照合の結果（端ごと）。"""
    pat = C.patterns()
    t0 = time.time()
    mt = match_stops(tk[["route_id", "start_stop_name", "end_stop_name"]], pat)
    print(f"今の照合を端ごとに再現: {len(mt):,} 組（{time.time() - t0:.0f} 秒）")
    return mt


def bus_position_seq(con, tk: pd.DataFrame, days) -> pd.DataFrame:
    """車両番号つきの券ごとに、購入時のバスの位置に最も近い、券の路線の停留所の seq。"""
    con.execute("CREATE OR REPLACE TABLE pat AS SELECT CAST(route_id AS INT) AS rid, seq, stop_lat, stop_lon FROM pat_df")
    out = []
    for d in days:
        g = C.GPS / f"date={d}" / "part.parquet"
        if not g.exists():
            continue
        day = tk[(tk.date == d) & tk.vehicle_number.notna()][["tid", "vehicle_number", "route_id", "created_at"]]
        if day.empty:
            continue
        con.register("day", day)
        r = con.execute(f"""
            WITH t AS (SELECT tid, vehicle_number AS vid, CAST(route_id AS INT) AS rid, created_at FROM day),
                 g AS (SELECT vehicle_id AS vid, ts, lat, lng FROM read_parquet('{g.as_posix()}')
                       WHERE vehicle_id IN (SELECT DISTINCT vid FROM t)),
                 pos AS (SELECT t.tid, t.rid, g.lat, g.lng, epoch(t.created_at) - epoch(g.ts) AS lag
                         FROM t ASOF JOIN g ON g.vid = t.vid AND g.ts <= t.created_at),
                 c AS (SELECT pos.tid, pat.seq,
                              sqrt(pow((pos.lat - pat.stop_lat) * {C.M_PER_DEG_LAT}, 2) + pow((pos.lng - pat.stop_lon) * {C.M_PER_DEG_LNG}, 2)) AS dm
                       FROM pos JOIN pat ON pat.rid = pos.rid WHERE pos.lag <= {MAX_LAG_S})
            SELECT tid, arg_min(seq, dm) AS seq_near, min(dm) AS d_near FROM c GROUP BY tid
        """).df()
        con.unregister("day")
        out.append(r[r.d_near <= MAX_OFF_M])
        print(f"  {d}: 位置が取れた券 {len(out[-1]):,} / {len(day):,}", flush=True)
    return pd.concat(out, ignore_index=True)


def vote(df: pd.DataFrame, pk: dict, nstops: dict) -> pd.DataFrame:
    """（路線, 名前）ごとに、ずれの分布で重みを付けた投票。df: route_id, name, seq_near"""
    rows = []
    for (rid, name), g in df.groupby(["route_id", "name"], sort=False):
        n = len(g)
        ns = nstops[rid]
        sc = np.zeros(ns)
        for s_near, c in g.seq_near.value_counts().items():
            for k in range(KMIN, KMAX + 1):
                s = s_near - k
                if 0 <= s < ns:
                    sc[s] += c * pk.get(k, 0.0)
        o = np.argsort(-sc)
        best, second = int(o[0]), int(o[1]) if ns > 1 else -1
        rows.append((rid, name, n, best, sc[best] / n, (sc[best] - (sc[second] if second >= 0 else 0)) / n))
    return pd.DataFrame(rows, columns=["route_id", "name", "n", "seq_gps", "share", "margin"])


def main(a="2026-10-01", b="2026-10-31"):
    OUT.mkdir(exist_ok=True)
    days = days_between(a, b)
    con = duckdb.connect()
    con.execute("SET timezone='Asia/Kolkata'; SET threads TO 16; SET memory_limit='20GB';")
    tk = load_tickets(con)
    tk = tk[tk.date.isin(set(days))].reset_index(drop=True)
    pat = C.patterns()
    con.register("pat_df", pat)
    nstops = pat.groupby("route_id").seq.max().add(1).to_dict()
    names = {(r, s): n for r, s, n in zip(pat.route_id, pat.seq, pat.stop_name)}

    mt = per_end_match(tk)
    look = {(r, n): (s, h) for r, n, s, h in zip(mt.route_id, mt.name, mt.seqs, mt.how)}

    print("購入時のバスの位置を GPS から取る…")
    pos = bus_position_seq(con, tk, days)
    v = tk.merge(pos, on="tid")
    v = v.rename(columns={"start_stop_name": "name"})
    m = [look.get((r, n)) for r, n in zip(v.route_id, v.name)]
    v["how"] = [x[1] if x else "none" for x in m]
    v["seqs"] = [x[0] if x else [] for x in m]
    print(f"位置が取れた車両番号つきの券 {len(v):,} 枚（期間 {a}〜{b}）")
    print("  乗車名の今の照合:", v.how.value_counts(normalize=True).round(3).to_dict())

    # 1. ずれの分布（完全一致で1か所に決まる乗車名）
    ex = v[(v.how == "exact") & (v.seqs.map(len) == 1)].copy()
    ex["truth"] = ex.seqs.map(lambda s: s[0])
    k = (ex.seq_near - ex.truth).clip(KMIN - 1, KMAX + 1)
    pk_all = k.value_counts(normalize=True).sort_index()
    pk = {int(i): float(p) for i, p in pk_all.items() if KMIN <= i <= KMAX}
    print("\n1. ずれ k = 購入時の最寄りの停留所 − 乗車停留所 の分布（完全一致の乗車名）")
    print("   " + "  ".join(f"k={i:+d}: {p:.1%}" for i, p in pk_all.items()))

    # 2〜3. 完全一致の名前を隠して当てる（投票は名前を見ない）。日の前半で学んだ分布で後半を当てるのが本来だが、
    #       分布は形だけを使い、名前ごとの正解は使わないので、ここでは同じ期間で測る
    tv = vote(ex[["route_id", "name", "seq_near"]], pk, nstops)
    truth = ex.groupby(["route_id", "name"]).truth.first()
    tv["truth"] = [truth[(r, n)] for r, n in zip(tv.route_id, tv.name)]
    tv["ok"] = tv.seq_gps == tv.truth
    tv["ok1"] = (tv.seq_gps - tv.truth).abs() <= 1
    print("\n2. 完全一致の名前を隠して、GPS の投票だけで停留所を当てる（（路線, 名前）の組ごと）")
    print("   券の枚数     組の数   当たり   ±1停留所   （券の枚数で重みを付けた当たり）")
    for lo in [1, 3, 5, 10, 20, 50]:
        s = tv[tv.n >= lo]
        print(f"   {lo:>3} 枚以上  {len(s):>6,}   {s.ok.mean():6.1%}   {s.ok1.mean():6.1%}     {np.average(s.ok, weights=s.n):6.1%}")
    s = tv[tv.n >= 10]
    for th in [0.3, 0.4, 0.5]:
        q = s[s.margin >= th]
        print(f"   10枚以上・首位と2位の差 {th:.1f} 以上: {len(q):,} 組（10枚以上の {len(q) / len(s):.0%}）で当たり {q.ok.mean():.1%}")

    # 4. 今の照合（あいまい一致・退避）の点検
    print("\n3. 今の照合が決めた停留所と、GPS の投票の一致（10枚以上・差0.3以上の組）")
    rows = []
    for how in ["exact", "fuzzy", "nearby"]:
        sub = v[(v.how == how)]
        if sub.empty:
            continue
        vv = vote(sub[["route_id", "name", "seq_near"]], pk, nstops)
        first = sub.groupby(["route_id", "name"]).seqs.first()
        vv["cand"] = [first[(r, n)] for r, n in zip(vv.route_id, vv.name)]
        vv = vv[(vv.n >= 10) & (vv.margin >= 0.3)]
        vv["agree"] = [g in c for g, c in zip(vv.seq_gps, vv.cand)]
        vv["agree1"] = [min(abs(g - x) for x in c) <= 1 for g, c in zip(vv.seq_gps, vv.cand)]
        print(f"   {how:>6}: {len(vv):,} 組  一致 {vv.agree.mean():.1%}  ±1停留所 {vv.agree1.mean():.1%}"
              f"  （券の枚数で重み {np.average(vv.agree, weights=vv.n):.1%}）")
        vv["how"] = how
        rows.append(vv)
    chk = pd.concat(rows)
    bad = chk[(chk.how != "exact") & ~chk.agree1].sort_values("n", ascending=False).head(25)
    print("   GPS と食い違う、あいまい一致・退避の例（多い順）")
    for r in bad.itertuples():
        cand = " / ".join(names[(r.route_id, c)] for c in r.cand[:2])
        print(f"     [{r.how}] {r.name}（路線 {r.route_id}, {r.n}枚）→ 今: {cand} ／ GPS: {names[(r.route_id, r.seq_gps)]}（差 {r.margin:.2f}）")

    # 5. 補う：今は照合できない乗車名
    un = v[v.how == "none"]
    uv = vote(un[["route_id", "name", "seq_near"]], pk, nstops)
    uv["stop_name"] = [names[(r, s)] for r, s in zip(uv.route_id, uv.seq_gps)]
    uv.sort_values("n", ascending=False).to_csv(OUT / "unmatched_gps_vote.csv", index=False)
    acc = uv[(uv.n >= 10) & (uv.margin >= 0.3)]
    print(f"\n4. 今は照合できない乗車名: {len(uv):,} 組（車両番号つき・位置が取れた券 {len(un):,} 枚）")
    print(f"   10枚以上・差0.3以上で決まる組 {len(acc):,}（券 {acc.n.sum():,} 枚 ＝ 未照合の乗車名の券の {acc.n.sum() / max(len(un), 1):.0%}）")
    # 車両番号のない券も、同じ（路線, 名前）なら覆える。降車名も同じ一覧から選ばれるので、同じ鍵で覆える
    key = set(zip(acc.route_id, acc.name))
    allk = tk.copy()
    sm = [look.get((r, n)) for r, n in zip(allk.route_id, allk.start_stop_name)]
    em = [look.get((r, n)) for r, n in zip(allk.route_id, allk.end_stop_name)]
    s_un = np.array([x is None for x in sm])
    e_un = np.array([x is None for x in em])
    s_fix = s_un & np.array([(r, n) in key for r, n in zip(allk.route_id, allk.start_stop_name)])
    e_fix = e_un & np.array([(r, n) in key for r, n in zip(allk.route_id, allk.end_stop_name)])
    n_end = 2 * len(allk)
    print(f"   全券（車両番号の有無を問わず {len(allk):,} 枚、端 {n_end:,}）で: 未照合の端 {(s_un.sum() + e_un.sum()) / n_end:.2%}"
          f" → GPS の別名で埋まる端 {(s_fix.sum() + e_fix.sum()) / n_end:.2%}（乗車 {s_fix.sum():,}・降車 {e_fix.sum():,}）")
    both_ok_now = (~s_un) & (~e_un)
    both_ok_new = (~s_un | s_fix) & (~e_un | e_fix)
    print(f"   両端が対応する券（順番は問わない）: {both_ok_now.mean():.1%} → {both_ok_new.mean():.1%}")
    print("   例（多い順）")
    for r in acc.sort_values("n", ascending=False).head(25).itertuples():
        print(f"     {r.name}（路線 {r.route_id}, {r.n}枚, 差 {r.margin:.2f}）→ {r.stop_name}")
    tv.to_csv(OUT / "exact_holdout.csv", index=False)
    chk.to_csv(OUT / "current_match_check.csv", index=False)


if __name__ == "__main__":
    main(*sys.argv[1:3])
