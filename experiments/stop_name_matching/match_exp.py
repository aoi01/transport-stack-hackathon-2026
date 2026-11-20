"""Quick offline experiment: how much do Indic-aware normalization steps raise route-restricted
ticket-stop-name -> GTFS stop matches, compared with the project's baseline (norm exact -> rapidfuzz 85)?
Read-only on project data. Prints a report to stdout."""
import json
import re
import sys
import time
from collections import Counter, defaultdict

import pandas as pd
from rapidfuzz import fuzz

ROOT = "C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data"
GT = ROOT + "/raw/gtfs_static"
OSM = sys.argv[1] if len(sys.argv) > 1 else None
t0 = time.time()

# ---------------------------------------------------------------- normalisers
def norm0(s):  # project baseline (src/tsh/crowding.py norm)
    s = str(s).lower().replace("&", " and ")
    s = re.sub(r"\b(bus stop|bus stand|busstop|stop)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

ABBR = [
    (r"\(\s*t\s*\)", " terminal "),
    (r"\bx\s*-?\s*ing\b|\bxng\b|\bx\s*ings\b", " crossing "),
]
TOK = {
    "sec": "sector", "sect": "sector", "sctr": "sector",
    "extn": "extension", "ext": "extension", "extention": "extension", "exten": "extension",
    "ph": "phase", "mkt": "market", "bdr": "border", "brdr": "border",
    "jn": "junction", "jnc": "junction", "jct": "junction",
    "rd": "road", "stn": "station", "hosp": "hospital", "hsptl": "hospital",
    "vill": "village", "vil": "village", "vlg": "village", "gaon": "village", "goan": "village",
    "clny": "colony", "encl": "enclave", "enclv": "enclave", "ngr": "nagar",
    "dpt": "depot", "govt": "government", "sch": "school", "schl": "school",
    "pkt": "pocket", "blk": "block", "indl": "industrial", "inst": "institute",
    "apts": "apartment", "apt": "apartment", "apartments": "apartment",
    "centre": "center", "theatre": "theater",
    "morh": "mor", "mod": "mor", "mode": "mor", "more": "mor",
    "chauk": "chowk", "chok": "chowk", "chk": "chowk",
    "terminus": "terminal", "termnal": "terminal",
    "xing": "crossing",
}
STOPWORDS = {"bus", "stop", "stand", "the", "of"}
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}

def norm1(s):
    s = str(s).lower().replace("&", " and ")
    for pat, rep in ABBR:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\b(bus stop|bus stand|busstop|bus stn|stop)\b", " ", s)
    s = re.sub(r"\bnh\s*-?\s*(\d+)\b", r"nh\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [ROMAN.get(t, TOK.get(t, t)) for t in s.split()]
    toks = [t for t in toks if t not in STOPWORDS]
    return " ".join(toks)

def fold_tok(t):
    if t.isdigit():
        return t
    t = t.replace("ksh", "ks").replace("x", "ks").replace("q", "k").replace("w", "v").replace("z", "j")
    t = re.sub(r"([kgcjtdpbsr])h", r"\1", t)     # aspirates / sh / ch / rh
    t = re.sub(r"(.)\1+", r"\1", t)              # doubled letters (also aa, ee, oo)
    t = t.replace("ee", "i").replace("oo", "u").replace("ou", "u").replace("au", "o")
    t = re.sub(r"(?<=[^aeiou])y$", "i", t)
    t = re.sub(r"(.)\1+", r"\1", t)
    return t

def key_nospace(s):
    return norm1(s).replace(" ", "")

def key_fold(s):
    return "".join(fold_tok(t) for t in norm1(s).split())

GENERIC = {"village", "metro", "station", "terminal", "crossing", "chowk", "market", "depot", "road",
           "marg", "mor", "hospital", "school", "colony", "extension", "phase", "block", "gate", "red", "light",
           "flyover", "bridge", "junction", "border", "temple", "mandir", "park", "near", "opp", "opposite"}

def key_core(s):  # folded key without generic words (used only with uniqueness checks)
    toks = [t for t in norm1(s).split() if t not in GENERIC]
    return "".join(fold_tok(t) for t in toks)

# ---------------------------------------------------------------- data
stops = pd.read_csv(GT + "/stops.txt", dtype=str)
routes = pd.read_csv(GT + "/routes.txt", dtype=str)
pat = pd.read_parquet(ROOT + "/processed/patterns.parquet")
pat = pat if "stop_name" in pat.columns else pat.merge(stops[["stop_id", "stop_name"]], on="stop_id", how="left")
trips = pd.read_csv(GT + "/trips.txt", dtype=str, usecols=["route_id", "trip_id"])
st = pd.read_csv(GT + "/stop_times.txt", dtype=str, usecols=["trip_id", "stop_id"])
st = st.merge(trips, on="trip_id")
union = st[["route_id", "stop_id"]].drop_duplicates().merge(stops[["stop_id", "stop_name"]], on="stop_id")
print(f"[load gtfs] {time.time()-t0:.1f}s  stops={len(stops)} routes={len(routes)} pattern_rows={len(pat)}")

# GTFS name facts
nm = stops.stop_name.astype(str)
print("\n=== GTFS stop_name facts ===")
print("distinct stop_name:", nm.nunique(), " with '/':", nm.str.contains("/").sum(),
      " with '(':", nm.str.contains(r"\(").sum())
tokc = Counter(t for n in nm for t in re.sub(r"[^a-z0-9()]+", " ", n.lower()).split())
probe = ["sec", "sector", "extn", "extension", "ext", "ph", "phase", "mkt", "market", "bdr", "border", "xing",
         "x-ing", "crossing", "jn", "junction", "isbt", "(t)", "terminal", "nh8", "nh", "rd", "road", "village",
         "vill", "gaon", "metro", "station", "stn", "hospital", "hosp", "opp", "near", "nagar", "puri", "pur",
         "vihar", "enclave", "ganj", "bagh", "chowk", "kunj", "marg", "mor", "more", "depot", "colony", "camp",
         "kalan", "khurd", "centre", "center", "gate", "block", "pocket", "dda", "flats", "apartment", "school"]
print("token counts in GTFS stop names:", {p: tokc.get(p, 0) for p in probe})
sfx = Counter()
for n in nm:
    for t in re.sub(r"[^a-z]+", " ", n.lower()).split():
        for s in ["puri", "pur", "nagar", "vihar", "ganj", "bagh", "garh", "abad", "kunj", "wala", "sarai", "khera", "pura"]:
            if t.endswith(s) and len(t) > len(s) + 2:
                sfx[s + "(joined)"] += 1
                break
print("joined-suffix tokens in GTFS:", dict(sfx.most_common()))
# within-GTFS variants: different raw names, same folded key
by_fold = defaultdict(set)
for n in nm.unique():
    by_fold[key_fold(n)].add(n)
multi = [v for v in by_fold.values() if len(v) > 1]
print("GTFS name groups that differ in raw form but share a folded key:", len(multi))
for v in multi[:25]:
    print("   ", sorted(v))

# ---------------------------------------------------------------- tickets
tk = pd.read_csv(ROOT + "/raw/ticketing/October-Delhi.csv", dtype=str,
                 usecols=["route", "start_stop_name", "end_stop_name"])
print(f"\n[load tickets] {time.time()-t0:.1f}s rows={len(tk)}")
ends = pd.concat([tk[["route", "start_stop_name"]].rename(columns={"start_stop_name": "name"}),
                  tk[["route", "end_stop_name"]].rename(columns={"end_stop_name": "name"})])
pairs = ends.groupby(["route", "name"]).size().reset_index(name="n")
rid = routes.set_index("route_short_name").route_id.to_dict()
pairs["route_id"] = pairs.route.map(rid)
tot = pairs.n.sum()
print("ticket ends:", tot, " distinct names:", pairs.name.nunique(), " distinct (route,name):", len(pairs),
      " ends with route not in GTFS:", pairs[pairs.route_id.isna()].n.sum())
tn = Counter()
for n, c in zip(pairs.name, pairs.n):
    for t in re.sub(r"[^a-z0-9()\-]+", " ", str(n).lower()).split():
        tn[t] += c
print("ticket-end weighted token counts:", {p: tn.get(p, 0) for p in probe + ["x-ing", "sabha", "gtb", "nd"]})
pairs = pairs[pairs.route_id.notna()].copy()

# ---------------------------------------------------------------- candidate tables per route
def build(df):
    rows = []
    for r in df.itertuples():
        full = str(r.stop_name)
        for part in [full] + ([p for p in full.split("/")] if "/" in full else []):
            rows.append((r.route_id, r.stop_id, full, part))
    c = pd.DataFrame(rows, columns=["route_id", "stop_id", "full", "part"])
    c["k0"] = c.part.map(norm0)
    c["k1"] = c.part.map(key_nospace)
    c["k2"] = c.part.map(key_fold)
    c["k3"] = c.part.map(key_core)
    return {r: g for r, g in c.groupby("route_id")}

cand_pat = build(pat)
cand_uni = build(union)
glob = build(stops.assign(route_id="ALL"))["ALL"]
glob_k2 = set(glob.k2)
print(f"[cands] {time.time()-t0:.1f}s")

def baseline(name, g):
    nn = norm0(name)
    h = g[g.k0 == nn]
    if len(h):
        return "exact", set(h.stop_id)
    best, bc = -1, None
    for c in g.k0.unique():
        s = 0.5 * fuzz.token_sort_ratio(nn, c) + 0.5 * fuzz.token_set_ratio(nn, c)
        if s > best:
            best, bc = s, c
    if best >= 85:
        return "fuzzy", set(g[g.k0 == bc].stop_id)
    return "none", set()

def improved(name, g):
    nn = norm0(name)
    h = g[g.k0 == nn]
    if len(h):
        return "exact", set(h.stop_id)
    k1, k2, k3 = key_nospace(name), key_fold(name), key_core(name)
    h = g[g.k1 == k1]
    if len(h):
        return "abbr+space", set(h.stop_id)
    h = g[g.k2 == k2]
    if len(h):
        return "phonetic", set(h.stop_id)
    # containment of folded keys (one is prefix/suffix of other), unique stop on route
    if len(k2) >= 5:
        h = g[g.k2.map(lambda c: len(c) >= 5 and (c.startswith(k2) or k2.startswith(c) or c.endswith(k2) or k2.endswith(c)))]
        if h.stop_id.nunique() == 1:
            return "contain", set(h.stop_id)
    if len(k3) >= 5:
        h = g[g.k3 == k3]
        if h.stop_id.nunique() == 1:
            return "core", set(h.stop_id)
    # fuzzy on folded keys with margin
    sc = sorted(((fuzz.ratio(k2, c), c) for c in g.k2.unique()), reverse=True)
    if sc and sc[0][0] >= 88 and (len(sc) == 1 or sc[0][0] - sc[1][0] >= 4):
        return "fuzzy_fold", set(g[g.k2 == sc[0][1]].stop_id)
    nn1 = norm1(name)
    best, bc = -1, None
    for c in g.part.map(norm1).unique():
        s = 0.5 * fuzz.token_sort_ratio(nn1, c) + 0.5 * fuzz.token_set_ratio(nn1, c)
        if s > best:
            best, bc = s, c
    if best >= 90:
        return "fuzzy_tok90", set(g[g.part.map(norm1) == bc].stop_id)
    return "none", set()

res = []
for r in pairs.itertuples():
    g = cand_pat.get(r.route_id)
    if g is None:
        res.append((r.route, r.name, r.n, "noroute", "noroute", False, ""))
        continue
    b, bs = baseline(r.name, g)
    m, ms = improved(r.name, g)
    disagree = (b != "none" and m != "none" and not (bs & ms))
    cause = ""
    if m == "none":
        gu = cand_uni.get(r.route_id)
        k2 = key_fold(r.name)
        if gu is not None and (gu.k2 == k2).any():
            cause = "on_route_other_pattern"
        elif k2 in glob_k2:
            cause = "in_gtfs_not_on_route"
        else:
            cause = "not_in_gtfs_by_key"
    res.append((r.route, r.name, r.n, b, m, disagree, cause))
R = pd.DataFrame(res, columns=["route", "name", "n", "base", "imp", "disagree", "cause"])
print(f"[match] {time.time()-t0:.1f}s")
T = R.n.sum()
print("\n=== route-restricted (representative pattern) shares of ticket ENDS, no 'nearby' step ===")
print("baseline:", (R.groupby("base").n.sum() / T * 100).round(2).to_dict())
print("improved:", (R.groupby("imp").n.sum() / T * 100).round(2).to_dict())
print("baseline 'none' -> improved method:", (R[R.base == "none"].groupby("imp").n.sum() / T * 100).round(2).to_dict())
print("baseline 'fuzzy' -> improved method:", (R[R.base == "fuzzy"].groupby("imp").n.sum() / T * 100).round(2).to_dict())
print("disagreements (both matched, different stop) share of ends:", round(R[R.disagree].n.sum() / T * 100, 2))
print("residual unmatched (improved) by cause:", (R[R.imp == "none"].groupby("cause").n.sum() / T * 100).round(2).to_dict())

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 60)
print("\n--- top disagreements ---")
print(R[R.disagree].sort_values("n", ascending=False).head(25).to_string())
for meth in ["abbr+space", "phonetic", "contain", "core", "fuzzy_fold", "fuzzy_tok90"]:
    sub = R[(R.base == "none") & (R.imp == meth)].sort_values("n", ascending=False)
    print(f"\n--- newly matched by {meth} (top 12 of {len(sub)}) ---")
    print(sub.head(12)[["route", "name", "n"]].to_string())
for cause in ["on_route_other_pattern", "in_gtfs_not_on_route", "not_in_gtfs_by_key"]:
    sub = R[(R.imp == "none") & (R.cause == cause)].groupby("name").n.sum().sort_values(ascending=False)
    print(f"\n--- residual unmatched, cause={cause}: {len(sub)} names; top 30 ---")
    print(sub.head(30).to_string())
R.to_csv(sys.argv[2] if len(sys.argv) > 2 else "match_exp_out.csv", index=False)

# store the new-match details for later inspection
def show(name, g):
    return improved(name, g)

# ---------------------------------------------------------------- failure examples (pairwise)
ex = [("S.J. Hospital", "T.B. Hospital"), ("Badarpur", "Badarpur Village"), ("Aerocity", "Aero City Metro Station"),
      ("Said Ul Zeb Village", "Said ul zeb Village"), ("Jahangir Puri Metro Station", "Jahangirpuri Metro Station GT Road"),
      ("Sagar Pur Vashishth Park", "SagarPur Vashisht Park"), ("Health Center", "Najafghar Health Centre"),
      ("Pul Prehladpur ( Badarpur)", "Pul Pehladpur ( BadarPur)"),
      ("Reddison Hotel Mahipal Pur / Rang Puri (Nh8 Circle)", "Rang Puri (Airport Road) / Mahipal Pur Crossing")]
print("\n=== failure examples: keys and scores ===")
for a, b in ex:
    print(f"{a!r:55} | {b!r:50} | base={0.5*fuzz.token_sort_ratio(norm0(a), norm0(b))+0.5*fuzz.token_set_ratio(norm0(a), norm0(b)):.0f}"
          f" | k1 {key_nospace(a)} vs {key_nospace(b)} | k2 {key_fold(a)} vs {key_fold(b)} ratio={fuzz.ratio(key_fold(a), key_fold(b)):.0f}"
          f" | core {key_core(a)} vs {key_core(b)}")

# ---------------------------------------------------------------- OSM stats
if OSM:
    d = json.load(open(OSM, encoding="utf-8"))
    el = d["elements"]
    keys = Counter(k for e in el for k in e.get("tags", {}))
    print("\n=== OSM Delhi bus stops (highway=bus_stop or PT platform bus=yes) ===")
    print("nodes:", len(el), {k: keys.get(k, 0) for k in ["name", "name:en", "name:hi", "name:ur", "name:pa", "alt_name",
                                                         "old_name", "short_name", "official_name", "ref", "operator", "network"]})
    alts = [(e["tags"].get("name"), e["tags"].get("alt_name")) for e in el if "alt_name" in e.get("tags", {})]
    print("alt_name examples:", alts[:40])
    hi = [(e["tags"].get("name"), e["tags"].get("name:hi")) for e in el if "name:hi" in e.get("tags", {})]
    print("name:hi examples:", hi[:15])
    # OSM names that hit ticket names missing from GTFS
    osm_keys = defaultdict(set)
    for e in el:
        tg = e.get("tags", {})
        for k in ["name", "alt_name", "old_name", "short_name", "official_name", "name:en"]:
            if k in tg:
                for v in str(tg[k]).split(";"):
                    osm_keys[key_fold(v)].add(tg.get("name", ""))
    miss = R[(R.imp == "none") & (R.cause == "not_in_gtfs_by_key")]
    w = miss.groupby("name").n.sum()
    hit = [(n, c, sorted(osm_keys[key_fold(n)])[:3]) for n, c in w.items() if key_fold(n) in osm_keys]
    print("residual 'not_in_gtfs' names found in OSM by folded key:", len(hit), "of", len(w),
          "; ticket-end share:", round(sum(c for _, c, _ in hit) / T * 100, 2))
    print(sorted(hit, key=lambda x: -x[1])[:20])
print(f"\n[done] {time.time()-t0:.1f}s")
