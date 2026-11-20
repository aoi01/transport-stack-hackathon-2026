"""v2: route-restricted cascade with fixed vowel folding, consonant-skeleton key, sorted-token key,
more abbreviations; prints random samples of each new-match type with the GTFS stop chosen, so precision
can be eyeballed. Read-only on project data."""
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict

import pandas as pd
from rapidfuzz import fuzz

ROOT = "C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data"
GT = ROOT + "/raw/gtfs_static"
OSM = sys.argv[1]
t0 = time.time()
random.seed(7)

def norm0(s):  # project baseline (src/tsh/crowding.py norm)
    s = str(s).lower().replace("&", " and ")
    s = re.sub(r"\b(bus stop|bus stand|busstop|stop)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

PRE = [
    (r"\(\s*t\s*\)", " terminal "),
    (r"\bx\s*-\s*ing\b|\bx\s+ing\b|\bxng\b", " crossing "),
    (r"\bp\s*\.?\s*s\s*\.?(?=\s)", " police station "),       # P.S. / P S
    (r"\bnh\s*-?\s*(\d+)\b", r" nh\1 "),
]
TOK = {
    "sec": "sector", "sctr": "sector", "sect": "sector",
    "extn": "extension", "ext": "extension", "extention": "extension", "exten": "extension",
    "ph": "phase", "mkt": "market", "bdr": "border", "brdr": "border", "xing": "crossing",
    "jn": "junction", "jnc": "junction", "jct": "junction", "rd": "road", "stn": "station",
    "hosp": "hospital", "hsptl": "hospital", "vill": "village", "vil": "village", "vlg": "village",
    "gaon": "village", "goan": "village", "clny": "colony", "encl": "enclave", "enclv": "enclave",
    "ngr": "nagar", "dpt": "depot", "govt": "government", "sch": "school", "schl": "school",
    "pkt": "pocket", "blk": "block", "indl": "industrial", "inst": "institute", "rly": "railway",
    "apts": "apartment", "apt": "apartment", "apartments": "apartment", "centre": "center",
    "theatre": "theater", "morh": "mor", "mod": "mor", "mode": "mor", "more": "mor",
    "chauk": "chowk", "chok": "chowk", "chk": "chowk", "terminus": "terminal", "dist": "district",
    "takies": "talkies", "cinema": "cinema",
}
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}
STOPWORDS = {"bus", "stop", "stand", "the", "of"}

def norm1(s):
    s = " " + str(s).lower().replace("&", " and ") + " "
    for pat, rep in PRE:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\b(bus stop|bus stand|busstop|bus stn|stop)\b", " ", s)
    s = re.sub(r"(\d)([a-z])", r"\1 \2", s)
    s = re.sub(r"([a-z])(\d)", r"\1 \2", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [ROMAN.get(t, TOK.get(t, t)) for t in s.split()]
    return " ".join(t for t in toks if t not in STOPWORDS)

def fold_tok(t):
    if t.isdigit():
        return t
    t = t.replace("ksh", "ks").replace("x", "ks").replace("q", "k").replace("w", "v").replace("z", "j")
    t = t.replace("ee", "i").replace("ii", "i").replace("oo", "u").replace("uu", "u").replace("ou", "u").replace("au", "o")
    t = re.sub(r"([kgcjtdpbsr])h", r"\1", t)     # aspirates / sh / ch / rh
    t = re.sub(r"(.)\1+", r"\1", t)              # doubled letters (aa -> a, tt -> t)
    t = re.sub(r"(?<=[^aeiou])y$", "i", t)
    return t

def skel_tok(t):  # consonant skeleton: first letter kept, later vowels dropped, v~b
    if t.isdigit():
        return t
    f = fold_tok(t).replace("v", "b")
    return f[0] + re.sub(r"[aeiouy]", "", f[1:]) if f else f

def key_nospace(s): return norm1(s).replace(" ", "")
def key_fold(s): return "".join(fold_tok(t) for t in norm1(s).split())
def key_sorted(s): return " ".join(sorted(fold_tok(t) for t in norm1(s).split()))
def key_skel(s): return re.sub(r"(.)\1+", r"\1", "".join(skel_tok(t) for t in norm1(s).split()))

GENERIC = {"village", "metro", "station", "terminal", "crossing", "chowk", "market", "depot", "road", "marg",
           "mor", "hospital", "school", "colony", "extension", "phase", "block", "gate", "red", "light", "flyover",
           "bridge", "junction", "border", "temple", "mandir", "park", "near", "opp", "opposite", "police"}
def key_core(s):
    return "".join(fold_tok(t) for t in norm1(s).split() if t not in GENERIC)

stops = pd.read_csv(GT + "/stops.txt", dtype=str)
sname = dict(zip(stops.stop_id, stops.stop_name))
routes = pd.read_csv(GT + "/routes.txt", dtype=str)
pat = pd.read_parquet(ROOT + "/processed/patterns.parquet")
if "stop_name" not in pat.columns:
    pat = pat.merge(stops[["stop_id", "stop_name"]], on="stop_id", how="left")
trips = pd.read_csv(GT + "/trips.txt", dtype=str, usecols=["route_id", "trip_id"])
st = pd.read_csv(GT + "/stop_times.txt", dtype=str, usecols=["trip_id", "stop_id", "stop_sequence"])
sig = st.sort_values(["trip_id"]).groupby("trip_id").stop_id.agg(lambda x: ",".join(x)).reset_index().merge(trips, on="trip_id")
npat = sig.groupby("route_id").stop_id.nunique()
print("stop patterns per route_id:", npat.describe().round(2).to_dict(), " routes with >1 pattern:", int((npat > 1).sum()))

def build(df):
    rows = []
    for r in df.itertuples():
        full = str(r.stop_name)
        for part in [full] + (full.split("/") if "/" in full else []):
            rows.append((r.route_id, r.stop_id, full, part))
    c = pd.DataFrame(rows, columns=["route_id", "stop_id", "full", "part"])
    for k, f in [("k0", norm0), ("k1", key_nospace), ("k2", key_fold), ("ks", key_sorted), ("k3", key_core),
                 ("kk", key_skel), ("n1", norm1)]:
        c[k] = c.part.map(f)
    return {r: g for r, g in c.groupby("route_id")}

cand = build(pat)
glob = build(stops.assign(route_id="ALL"))["ALL"]
glob_keys = set(glob.k2) | set(glob.kk)

tk = pd.read_csv(ROOT + "/raw/ticketing/October-Delhi.csv", dtype=str, usecols=["route", "start_stop_name", "end_stop_name"])
ends = pd.concat([tk[["route", "start_stop_name"]].rename(columns={"start_stop_name": "name"}),
                  tk[["route", "end_stop_name"]].rename(columns={"end_stop_name": "name"})])
pairs = ends.groupby(["route", "name"]).size().reset_index(name="n")
pairs["route_id"] = pairs.route.map(routes.set_index("route_short_name").route_id.to_dict())
pairs = pairs[pairs.route_id.notna()]
print(f"[load] {time.time()-t0:.1f}s pairs={len(pairs)}")

def uniq(h):
    return set(h.stop_id) if h.stop_id.nunique() == 1 else None

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
    k1, k2, ks, k3, kk = key_nospace(name), key_fold(name), key_sorted(name), key_core(name), key_skel(name)
    for meth, col, k in [("abbr+space", "k1", k1), ("phonetic", "k2", k2), ("phonetic_sorted", "ks", ks)]:
        h = g[g[col] == k]
        if len(h):
            return meth, set(h.stop_id)
    h = g[g.kk == kk]
    if len(kk) >= 4 and uniq(h):
        return "skeleton", set(h.stop_id)
    if len(k2) >= 5:
        h = g[g.k2.map(lambda c: len(c) >= 5 and (c.startswith(k2) or k2.startswith(c) or c.endswith(k2) or k2.endswith(c)))]
        if uniq(h):
            return "contain", set(h.stop_id)
    if len(k3) >= 5:
        h = g[g.k3 == k3]
        if uniq(h):
            return "core", set(h.stop_id)
    sc = sorted(((fuzz.ratio(k2, c), c) for c in g.k2.unique()), reverse=True)
    if sc and sc[0][0] >= 88 and (len(sc) == 1 or sc[0][0] - sc[1][0] >= 4):
        return "fuzzy_fold", set(g[g.k2 == sc[0][1]].stop_id)
    nn1 = norm1(name)
    best, bc = -1, None
    for c in g.n1.unique():
        s = 0.5 * fuzz.token_sort_ratio(nn1, c) + 0.5 * fuzz.token_set_ratio(nn1, c)
        if s > best:
            best, bc = s, c
    if best >= 90:
        return "fuzzy_tok90", set(g[g.n1 == bc].stop_id)
    return "none", set()

res = []
for r in pairs.itertuples():
    g = cand.get(r.route_id)
    if g is None:
        continue
    b, bs = baseline(r.name, g)
    m, ms = improved(r.name, g)
    cause = ""
    if m == "none":
        cause = "in_gtfs_not_on_route" if (key_fold(r.name) in glob_keys or key_skel(r.name) in glob_keys) else "not_in_gtfs_by_key"
    res.append((r.route, r.name, r.n, b, " | ".join(sorted({sname[s] for s in bs})), m,
                " | ".join(sorted({sname[s] for s in ms})), bool(b != "none" and m != "none" and not (bs & ms)), cause))
R = pd.DataFrame(res, columns=["route", "name", "n", "base", "base_stop", "imp", "imp_stop", "disagree", "cause"])
R.to_csv("match_exp2_out.csv", index=False)
T = R.n.sum()
print(f"[match] {time.time()-t0:.1f}s ends_with_pattern={T}")
print("baseline %:", (R.groupby("base").n.sum() / T * 100).round(2).to_dict())
print("improved %:", (R.groupby("imp").n.sum() / T * 100).round(2).to_dict())
print("baseline none -> improved %:", (R[R.base == "none"].groupby("imp").n.sum() / T * 100).round(2).to_dict())
print("baseline fuzzy -> improved %:", (R[R.base == "fuzzy"].groupby("imp").n.sum() / T * 100).round(2).to_dict())
print("disagree % of ends:", round(R[R.disagree].n.sum() / T * 100, 2))
print("residual by cause %:", (R[R.imp == "none"].groupby("cause").n.sum() / T * 100).round(2).to_dict())

pd.set_option("display.width", 260)
pd.set_option("display.max_colwidth", 55)
print("\n--- top 20 disagreements (baseline stop vs improved stop) ---")
print(R[R.disagree].sort_values("n", ascending=False).head(20)[["route", "name", "n", "base_stop", "imp", "imp_stop"]].to_string())
for meth in ["abbr+space", "phonetic", "phonetic_sorted", "skeleton", "contain", "core", "fuzzy_fold", "fuzzy_tok90"]:
    sub = R[(R.base == "none") & (R.imp == meth)]
    if len(sub) == 0:
        continue
    smp = sub.sample(min(15, len(sub)), weights=sub.n, random_state=3)
    print(f"\n--- random (ticket-weighted) sample of NEW matches by {meth} ({len(sub)} pairs, {sub.n.sum()/T*100:.2f}% ends) ---")
    print(smp[["route", "name", "n", "imp_stop"]].to_string())
sub = R[(R.base == "fuzzy") & (R.imp == "none")]
smp = sub.sample(min(20, len(sub)), weights=sub.n, random_state=5)
print(f"\n--- baseline FUZZY matches that the stricter cascade rejects ({sub.n.sum()/T*100:.2f}% ends), sample ---")
print(smp[["route", "name", "n", "base_stop"]].to_string())

# failure examples, skeleton keys
for a, b in [("Begam Pur", "Begumpur"), ("Mahvir Enclave", "Mahavir Enclave"), ("Rajindera Place", "Rajendra Place"),
             ("Sarai Rohella", "Sarai Rohilla"), ("Anand Pravat", "Anand Parbat"), ("Madhuvan Chowk", "Madhuban Chowk"),
             ("P.S. Pahar Gunj", "Paharganj Police Station"), ("Inder Puri", "Indrapuri"), ("Kirshi Kunj", "Krishi Kunj"),
             ("Swaroop Nagar", "Swarup Nagar"), ("Peera Garhi", "Peeragarhi"), ("Badarpur", "Badarpur Village")]:
    print(f"skeleton {a!r:22} -> {key_skel(a):14} | {b!r:28} -> {key_skel(b):14} | sorted {key_sorted(a)!r} vs {key_sorted(b)!r}")

d = json.load(open(OSM, encoding="utf-8"))
el = d["elements"]
hi = [(e["tags"].get("name"), e["tags"].get("name:hi")) for e in el if "name:hi" in e.get("tags", {})]
print("\nOSM name:hi examples:", hi[:12])
sn = [(e["tags"].get("name"), e["tags"].get("short_name")) for e in el if "short_name" in e.get("tags", {})]
print("OSM short_name examples:", sn[:25])
osm_k = defaultdict(set)
for e in el:
    tg = e.get("tags", {})
    for k in ["name", "alt_name", "short_name", "official_name", "name:en"]:
        for v in str(tg.get(k, "")).split(";"):
            if v:
                osm_k[key_skel(v)].add(tg.get("name", ""))
miss = R[(R.imp == "none") & (R.cause == "not_in_gtfs_by_key")].groupby("name").n.sum()
hit = [(n, c, sorted(osm_k[key_skel(n)])[:2]) for n, c in miss.items() if key_skel(n) in osm_k]
print("residual not-in-GTFS names found in OSM (skeleton key):", len(hit), "of", len(miss), "names;",
      round(sum(c for _, c, _ in hit) / T * 100, 2), "% of ends")
print(sorted(hit, key=lambda x: -x[1])[:25])
print("\nresidual not_in_gtfs top 40:")
print(miss.sort_values(ascending=False).head(40).to_string())
print(f"[done] {time.time()-t0:.1f}s")
