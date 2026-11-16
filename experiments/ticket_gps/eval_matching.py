"""停留所名の照合の改良前後を比べ、ガードとあいまい一致の閾値を決める実験。

正しさの物差しは、GPS の多数決（名前の文字列を見ずに、買った瞬間のバスの位置から停留所を推定する）。
完全一致の名前を隠して当てると、枚数 10 以上・首位と 2 位の差 0.3 以上の組で 97.8% 当たる
（experiments/ticket_gps/alias_from_gps.py）。その組で、各方法が決めた停留所が GPS と同じかを数える。

  - 改良前（legacy_match.py）と、改良後（src/tsh/stopmatch.py）の設定違い
  - 方法・段階ごとの量（券の端の割合）と、GPS との一致（組の数、一致、±1停留所、券の枚数で重み）

使い方: python -X utf8 experiments/ticket_gps/eval_matching.py
出力:   標準出力と experiments/ticket_gps/out/eval_*.csv（元データ由来の名前を含むので git には入れない）
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tsh import common as C  # noqa: E402
from tsh import stopmatch as SM  # noqa: E402
from tsh.crowding import load_tickets  # noqa: E402
from legacy_match import match_stops  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def summarize(label: str, mt: pd.DataFrame, pairs: pd.DataFrame, gv: pd.DataFrame, n_ends: int) -> pd.DataFrame:
    m = pairs.merge(mt, on=["route_id", "name"], how="left")
    m["how"] = m.how.fillna("none")
    m["step"] = m.step.fillna(m.how) if "step" in m else m.how
    m["seqs"] = [s if isinstance(s, list) else [] for s in m.seqs]
    print(f"\n=== {label} ===")
    cov = (m.groupby("how").ends.sum() / n_ends * 100).round(2).sort_values(ascending=False)
    print("  券の端の割合（%）:", cov.to_dict())
    g = gv[(gv.n >= SM.GPS_N_MIN) & (gv.margin >= SM.GPS_MARGIN_MIN)][["route_id", "name", "n", "seq_gps"]]
    c = m.merge(g, on=["route_id", "name"])
    c = c[c.how != "none"].copy()
    c["agree"] = [s in q for s, q in zip(c.seq_gps, c.seqs)]
    c["agree1"] = [min(abs(s - x) for x in q) <= 1 for s, q in zip(c.seq_gps, c.seqs)]
    print("  GPS との一致（枚数10以上・差0.3以上の組）")
    print("    段階            組の数   一致    ±1   券の重み   端の割合%")
    for step, d in c.groupby("step"):
        ends = m[m.step == step].ends.sum() / n_ends * 100
        print(f"    {step:<14} {len(d):>6,}  {d.agree.mean():6.1%} {d.agree1.mean():6.1%}  {np.average(d.agree, weights=d.n):6.1%}   {ends:6.2f}")
    print(f"    {'(全体)':<13} {len(c):>6,}  {c.agree.mean():6.1%} {c.agree1.mean():6.1%}  {np.average(c.agree, weights=c.n):6.1%}")
    # 段階ごとの端の割合 × その段階の GPS との一致（券の枚数で重み）で、正しく対応した端・誤った端の割合を見積もる
    # （一致は、枚数の多い名前で測った値。枚数の少ない名前でも同じとは限らない）
    acc = {s: np.average(d.agree, weights=d.n) for s, d in c.groupby("step")}
    sh = m[m.how != "none"].groupby("step").ends.sum() / n_ends
    ok = sum(v * acc.get(s, np.nan) for s, v in sh.items() if s in acc)
    bad = sum(v * (1 - acc[s]) for s, v in sh.items() if s in acc)
    rest = sum(v for s, v in sh.items() if s not in acc)
    print(f"  見積もり: 正しく対応した端 {ok:.1%}、誤って対応した端 {bad:.1%}、一致を測れない段階 {rest:.1%}、"
          f"照合できない端 {1 - sh.sum():.1%}")
    return m.merge(g, on=["route_id", "name"], how="left")


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    tk = load_tickets()
    pat = C.patterns()
    pairs = SM.name_pairs(tk)
    pairs["ends"] = pairs.n_s + pairs.n_e
    n_ends = int(pairs.ends.sum())
    print(f"券 {len(tk):,} 枚、（路線, 名前）{len(pairs):,} 組、端 {n_ends:,}（GTFS に路線がある端）  {time.time() - t0:.0f} 秒")

    old = match_stops(tk[tk.route_id.notna()], pat).assign(step=lambda d: d.how)
    new = SM.match_names(pairs, pat)
    gv, pk = SM.gps_votes(tk[tk.route_id.notna()], new, pat, C.TRAIN_DAYS)   # 閾値も学習期間だけで決める
    print("ずれの分布 P(k):", {k: round(v, 3) for k, v in pk.items()})

    m_old = summarize("改良前（完全一致 → あいまい一致85 → 400m の退避）", old, pairs, gv, n_ends)
    m_new = summarize(f"改良後の文字列の照合（ガード: 固有の部分 {SM.CORE_MIN}、あいまい一致 {SM.FUZZY_MIN}）", new, pairs, gv, n_ends)
    # 1 回目の評価（2026-11-16）で、固有の部分の閾値 0/50/60/70 とあいまい一致 85/90 は、GPS との一致を
    # ほとんど変えなかった（60・85 を採用）。設定違いを見るときは、ここで match_names の引数を変えて summarize する

    # 番号が片方の名前にだけある候補（ガードは通す）の正しさ
    pn = {}
    for (rid, s), name in zip(zip(pat.route_id, pat.seq), pat.stop_name):
        pn[(rid, s)] = name
    x = m_new[(m_new.how.isin(["rule", "fuzzy", "nearby"])) & m_new.seq_gps.notna()].copy()
    x["one_sided_num"] = [bool(SM.keys(n)["marks"][0]) != bool(SM.keys(str(pn[(r, q[0])]))["marks"][0])
                          for r, n, q in zip(x.route_id, x.name, x.seqs)]
    x["agree"] = [int(s) in q for s, q in zip(x.seq_gps, x.seqs)]
    print("\n番号が片方にだけある候補と、両方とも同じ（または無い）候補の GPS との一致")
    print(x.groupby(["how", "one_sided_num"]).agree.agg(["size", "mean"]).round(3).to_string())

    # GPS で決める名前（補う・置き換える）と、起点・終点への推定
    for override in [("fuzzy", "nearby"), ("rule", "fuzzy", "nearby")]:
        fin = SM.resolve(new, gv, pat, override=override)
        f = pairs.merge(fin, on=["route_id", "name"], how="left")
        f["step"] = f.step.fillna("none")
        print(f"\nGPS で置き換える方法 {override}:")
        print("  段階ごとの端の割合（%）:", (f.groupby("step").ends.sum() / n_ends * 100).round(2).sort_values(ascending=False).to_dict())
        print(f"  照合できない端: {f[f.how.fillna('none') == 'none'].ends.sum() / n_ends:.2%}")

    # 起点・終点への GPS の推定（確かめる用）
    last = pat.groupby("route_id").seq.max().to_dict()
    g = gv[(gv.n >= SM.GPS_N_MIN) & (gv.margin >= SM.GPS_MARGIN_MIN)]
    t = g.merge(new, on=["route_id", "name"])
    t = t[(t.how == "none").to_numpy() & np.array([s in (0, last[r]) for r, s in zip(t.route_id, t.seq_gps)])].copy()
    t["gtfs"] = [pn[(r, s)] for r, s in zip(t.route_id, t.seq_gps)]
    t["core_sim"] = [max(SM.core_sim(SM.keys(v), SM.keys(p)) for v in SM.name_variants(a) for p in SM.split_parts(b))
                     for a, b in zip(t.name, t.gtfs)]
    t["end"] = ["起点" if s == 0 else "終点" for s in t.seq_gps]
    t.sort_values("n", ascending=False)[["route_id", "name", "n", "margin", "end", "gtfs", "core_sim"]] \
     .to_csv(OUT / "eval_terminal_gps.csv", index=False)
    print(f"\n照合できず GPS が起点・終点を指す組: {len(t)}（core_sim >= {SM.TERMINAL_CORE_MIN}: {(t.core_sim >= SM.TERMINAL_CORE_MIN).sum()}）"
          f" → out/eval_terminal_gps.csv")
    m_old.to_csv(OUT / "eval_old.csv", index=False)
    m_new.to_csv(OUT / "eval_new.csv", index=False)
    print(f"\n完了 {time.time() - t0:.0f} 秒")


if __name__ == "__main__":
    main()
