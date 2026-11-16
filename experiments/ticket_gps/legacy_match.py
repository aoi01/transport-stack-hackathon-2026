"""改良前の停留所名の照合（2026-11-16 まで src/tsh/crowding.py にあった match_stops をそのまま残したもの）。

実験の再現（alias_from_gps.py）と、改良前後の比較（eval_matching.py）に使う。本体は src/tsh/stopmatch.py。
  完全一致（GTFS の "/" で分けた各部分も）→ あいまい一致（rapidfuzz、語の並びと語の包含の平均が 85 点以上）
  → 全停留所から名前で場所を引き、その路線で 400m 以内の最寄りに寄せる
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402


def norm(s: str) -> str:
    s = str(s).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\b(bus stop|bus stand|busstop|stop)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def match_stops(tk: pd.DataFrame, pat: pd.DataFrame) -> pd.DataFrame:
    """(route_id, 停留所名) → 代表パターン上の seq の一覧。"""
    pat = pat.assign(nname=pat.stop_name.map(norm))
    by_route = {r: g for r, g in pat.groupby("route_id")}
    parts = pat.assign(part=pat.stop_name.str.split("/")).explode("part")
    parts["pname"] = parts.part.map(norm)
    parts = parts[parts.pname != ""]
    parts_by_route = {r: g for r, g in parts.groupby("route_id")}
    pairs = pd.concat([
        tk[["route_id", "start_stop_name"]].rename(columns={"start_stop_name": "name"}),
        tk[["route_id", "end_stop_name"]].rename(columns={"end_stop_name": "name"}),
    ]).drop_duplicates()
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
            cands = pg.pname.unique().tolist()
            sc = [(0.5 * fuzz.token_sort_ratio(nn, c) + 0.5 * fuzz.token_set_ratio(nn, c), c) for c in cands]
            s_best, c_best = max(sc) if sc else (0, None)
            if s_best >= 85:
                hit = g[g.seq.isin(pg[pg.pname == c_best].seq)]
                how = "fuzzy"
        if hit.empty:
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
