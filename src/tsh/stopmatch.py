"""乗車券の停留所名を、その路線の GTFS の停留所（代表パターンの seq）に対応づける。

乗車券の名前は販売側（ONDC の seller）の停留所表から来ていて、GTFS とは綴り・略語・語順が違う
（reports/停留所名の照合の改善とオープンデータ.md）。（路線, 名前）ごとに次の順で決める。

  1. 完全一致: 小文字にして記号を除いた名前（GTFS の「A / B」は全体と各部分を候補にする）    how = exact
  2. 文字列の規則（名前の両側に同じ規則を当て、鍵が一致するもの）                          how = rule
       略語の展開と空白の除去（Sec→sector、Xing→crossing、Phase-Iii→phase 3 …）
       → 音写のゆれを畳んだ鍵（aa→a、ee→i、bh→b、w→v …）→ 語順をそろえた鍵
       → 子音の骨格（路線の中で1つの停留所に決まるときだけ）
  3. 近さで選ぶ（一方向の包含 → 音写を畳んだ鍵の文字の近さ → 語の並びと語の包含の平均）   how = fuzzy
     券の名前が路線の 2 つ以上の停留所の名前に含まれるときは、文字列では決めない
  4. 地理的な退避: 市内の全停留所から名前で場所を引き、その路線で 400m 以内の最寄りに寄せる   how = nearby
  5. GPS の別名: 車両番号つきの券は、買った瞬間のバスの位置が GPS で分かる。乗客の多くは乗った直後に
     買う（中央値で乗車停留所の通過の 0.8 分後）ので、（路線, 名前）ごとに、ずれの分布で重みを付けた
     多数決を取れば、名前の文字列を見ずに停留所が決まる。学ぶのは学習期間（10/1〜24）の券だけ。 how = gps
       - 1〜4 で決まらない名前を補う
       - 3〜4 で決めた停留所と GPS が 2 停留所以上食い違えば、GPS を採る
       - 起点・終点への推定は、起点での待機中の購入で偏るので、名前の裏づけがあるときだけ使う

ガード（2〜4 のすべての候補）: 数字（ローマ数字は算用数字に直す。国道の NH8 などは除く）や記号（A Block、
Pocket C、B-1 の a・c・b）が食い違う候補（片方にだけある場合も）、停留所の種類（Metro・Depot・Market …）が
重ならない候補、一般名詞（Nagar、Metro、Terminal …）を除いた固有の部分が似ていない候補は、点数によらず捨てる。
「R.K. Puram Sec-12」→「Sec 10」、「Uttam Nagar Terminal」→「Tilak Nagar Terminal」のような取り違えを防ぐ。
券の名前が「A / B」のように 2 つの呼び名をつないでいれば、全体で決まらないときに各部分でも照合する。

規則の多く（略語・音写・語順・骨格・包含）は reports/停留所名の照合と通過検出.md の実験から、
GPS の多数決は experiments/ticket_gps/alias_from_gps.py の実験から移した。閾値と段階は experiments/ticket_gps/eval_matching.py
で、GPS の多数決との一致を見て決めた（一般名詞を除いた「核」の段は一致が 65% と低かったので外した。
docs/phase1_prototype.md の 13.5）。
"""
from __future__ import annotations

import json
import re
import time
from functools import lru_cache

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from . import common as C

CORE_MIN = 60          # 固有の部分の近さ（token_set_ratio）の下限
FUZZY_MIN = 85         # あいまい一致（語の並びと語の包含の平均）の下限
NEARBY_M = 400         # 地理的な退避で寄せる距離の上限
GPS_N_MIN = 10         # GPS の別名に使う、位置の取れた券の枚数の下限
GPS_MARGIN_MIN = 0.3   # 首位と2位の点数の差（券1枚あたり）の下限。完全一致の名前を隠して当てると 97.8% 当たる
TERMINAL_CORE_MIN = 60  # 起点・終点への GPS の推定を使うのに要る、名前の固有の部分の近さ
KMIN, KMAX = -3, 6     # ずれ k（購入時の最寄りの停留所 − 乗車停留所）の範囲
MAX_LAG_S = 60         # 購入の何秒前までの GPS の点を使うか
MAX_OFF_M = 300        # バスが券の路線の停留所から何 m 以内なら使うか

# 照合の確からしさの順（券の両端のうち、低い方を券の match にする）
ORDER = ["exact", "rule", "gps", "fuzzy", "nearby"]


# ---- 正規化と鍵 ------------------------------------------------------------------------------

def norm(s) -> str:
    """完全一致の鍵: 小文字にして、"bus stop" などと記号を除く。"""
    s = str(s).lower().replace("&", " and ")
    s = re.sub(r"\b(bus stop|bus stand|busstop|stop)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


PRE = [
    (r"\(\s*t\s*\)", " terminal "),                          # Kashmere Gate (T)
    (r"\bx\s*-\s*ing\b|\bx\s+ing\b|\bxng\b", " crossing "),   # X-Ing / X Ing
    (r"\bp\s*\.?\s*s\s*\.?(?=\s)", " police station "),      # P.S. / P S
    (r"\bnational\s+highway\b", " nh "),                     # National Highway 8 → nh8
    (r"(\d+)(st|nd|rd|th)\b", r" \1 "),                      # 2nd → 2
]
TOK = {
    "sec": "sector", "sctr": "sector", "sect": "sector", "secter": "sector",
    "extn": "extension", "ext": "extension", "extention": "extension", "exten": "extension",
    "ph": "phase", "mkt": "market", "bdr": "border", "brdr": "border", "xing": "crossing", "crosing": "crossing",
    "jn": "junction", "jnc": "junction", "jct": "junction", "rd": "road", "stn": "station",
    "hosp": "hospital", "hsptl": "hospital", "vill": "village", "vil": "village", "vlg": "village",
    "gaon": "village", "goan": "village", "clny": "colony", "encl": "enclave", "enclv": "enclave",
    "ngr": "nagar", "dpt": "depot", "govt": "government", "sch": "school", "schl": "school",
    "pkt": "pocket", "blk": "block", "indl": "industrial", "inst": "institute", "rly": "railway",
    "apts": "apartment", "apt": "apartment", "apartments": "apartment", "centre": "center",
    "theatre": "theater", "morh": "mor", "mod": "mor", "mode": "mor", "more": "mor",
    "chauk": "chowk", "chok": "chowk", "chk": "chowk", "terminus": "terminal", "dist": "district",
    "takies": "talkies",
}
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9"}
ROMAN_AFTER = {"phase", "part", "sector", "stage", "block", "pocket", "gate", "no", "number", "extension", "camp", "wing"}
DROP = {"bus", "stop", "stand", "the", "of"}
# ガードで「固有の部分」を比べるときに落とす語（一般名詞と、地名に多い後ろの語）
GENERIC = {"village", "metro", "station", "terminal", "crossing", "chowk", "market", "depot", "road", "marg",
           "mor", "hospital", "school", "colony", "extension", "phase", "block", "gate", "red", "light", "flyover",
           "bridge", "junction", "border", "temple", "mandir", "park", "near", "opp", "opposite", "police"}
COMMON = GENERIC | {"nagar", "vihar", "enclave", "garden", "puri", "pur", "bagh", "ganj", "kunj", "sarai", "sector",
                    "pocket", "camp", "estate", "area", "industrial", "new", "old", "main", "office", "complex", "and",
                    "no", "number", "east", "west", "north", "south", "part", "stage", "point", "center", "institute",
                    "government", "railway", "apartment", "talkies", "district"}
SHORT = {"no", "of", "to", "in", "at", "on", "nr"}
# 停留所の種類。両方の名前に種類があって重ならない候補は捨てる（Shadipur Metro Station と Shadipur Depot など）
TYPES = {"crossing": "crossing", "mor": "crossing", "chowk": "crossing", "junction": "crossing",
         "village": "village", "metro": "metro", "terminal": "terminal", "depot": "terminal",
         "hospital": "hospital", "school": "school", "college": "school", "university": "school", "institute": "school",
         "market": "market", "mall": "market", "temple": "temple", "mandir": "temple", "gurudwara": "temple",
         "masjid": "temple", "church": "temple", "park": "park", "police": "police", "railway": "railway",
         "flyover": "bridge", "bridge": "bridge", "border": "border", "colony": "colony"}
HIGHWAY = re.compile(r"^nh\d+$")


def fold_tok(t: str) -> str:
    """ヒンディー語の音写のゆれを畳む（ee→i、oo→u、bh→b、sh→s、w→v、z→j、重ね文字→1文字 …）。"""
    if t.isdigit():
        return t
    t = t.replace("ksh", "ks").replace("x", "ks").replace("q", "k").replace("w", "v").replace("z", "j")
    t = t.replace("ee", "i").replace("ii", "i").replace("oo", "u").replace("uu", "u").replace("ou", "u").replace("au", "o")
    t = re.sub(r"([kgcjtdpbsr])h", r"\1", t)     # 有気音・sh・ch・rh
    t = re.sub(r"(.)\1+", r"\1", t)              # 重ね文字（aa→a、tt→t）
    t = re.sub(r"(?<=[^aeiou])y$", "i", t)
    return t


def skel_tok(t: str) -> str:
    """子音の骨格（最初の文字は残し、後の母音を落とす。v と b は同じに扱う）。"""
    if t.isdigit():
        return t
    f = fold_tok(t).replace("v", "b")
    return f[0] + re.sub(r"[aeiouy]", "", f[1:]) if f else f


def norm1(s) -> str:
    """略語を展開した名前（語の並びは保つ）。数字と文字の境目で分け、Phase などの後のローマ数字は算用数字に直す。"""
    s = " " + str(s).lower().replace("&", " and ") + " "
    for pat, rep in PRE:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\b(bus stop|bus stand|busstop|bus stn|stop)\b", " ", s)
    s = re.sub(r"(\d)([a-z])", r"\1 \2", s)
    s = re.sub(r"([a-z])(\d)", r"\1 \2", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\bnh (\d+)\b", r"nh\1", s)                      # 国道の番号（NH8）は地名の番号ではないので1語に
    s = re.sub(r"\b([a-z]) and ([a-z])\b", r"\1\2", s)          # J & D Block → jd block
    toks = [TOK.get(t, t) for t in s.split()]
    toks = [ROMAN[t] if (t in ROMAN and p > 0 and toks[p - 1] in ROMAN_AFTER) else t for p, t in enumerate(toks)]
    toks = [(t.lstrip("0") or "0") if t.isdigit() else t for t in toks]
    return " ".join(t for t in toks if t not in DROP)


def marks(toks: list[str]) -> tuple[frozenset, frozenset, frozenset]:
    """番号の印: 数字の集合、記号の集合（Block・Pocket に付く A Block・Pocket C・JD Block の a・c・jd と、
    番号の前の1文字 B-1・C1 の b・c）、国道の集合（nh8 など）。"""
    nums = frozenset(t for t in toks if t.isdigit())
    hw = frozenset(t for t in toks if HIGHWAY.match(t))
    des = set()
    for p, t in enumerate(toks):
        if t in ("block", "pocket"):
            for q in (p - 1, p + 1):
                if 0 <= q < len(toks) and toks[q].isalpha() and len(toks[q]) <= 2 and toks[q] not in SHORT:
                    des.add(toks[q])
        elif len(t) == 1 and t.isalpha() and p + 1 < len(toks) and toks[p + 1].isdigit():
            des.add(t)
    return nums, frozenset(des), hw


@lru_cache(maxsize=None)
def keys(s: str) -> dict:
    """照合に使う鍵の一式。"""
    n1 = norm1(s)
    toks = n1.split()
    f = [fold_tok(t) for t in toks]
    return {
        "k0": norm(s),                                     # 完全一致
        "n1": n1,                                          # あいまい一致
        "k1": n1.replace(" ", ""),                         # 略語の展開と空白の除去
        "k2": "".join(f),                                  # 音写のゆれを畳んだ鍵
        "ks": " ".join(sorted(f)),                         # 語順をそろえた鍵
        "kk": re.sub(r"(.)\1+", r"\1", "".join(skel_tok(t) for t in toks)),   # 子音の骨格
        "marks": marks(toks),
        "types": frozenset(TYPES[t] for t in toks if t in TYPES),
        "core": " ".join(ft for t, ft in zip(toks, f)
                         if t not in COMMON and not t.isdigit() and len(t) > 2 and not HIGHWAY.match(t)),
    }


def core_sim(a: dict, b: dict) -> float:
    """固有の部分の近さ（片方が空なら比べられないので 100）。片方の語がもう片方に含まれれば 100。
    語の区切りの違い（Pahar Gunj と Paharganj）も拾うように、空白を除いた文字の近さとの大きい方を取る。"""
    if not a["core"] or not b["core"]:
        return 100.0
    return max(fuzz.token_set_ratio(a["core"], b["core"]),
               fuzz.ratio(a["core"].replace(" ", ""), b["core"].replace(" ", "")))


def guard_ok(a: dict, b: dict, core_min: float = CORE_MIN) -> bool:
    """候補として残してよいか。番号・記号は片方にだけある場合も食い違いとみなす（GPS で確かめると、
    片方にだけ番号がある候補の当たりは 61〜75% で、両方同じ候補の 91〜93% より低い）。"""
    (na, da, ha), (nb, db, hb) = a["marks"], b["marks"]
    if na != nb or da != db:
        return False
    if ha and hb and ha != hb:      # 国道は、両方にあって違うときだけ（NH8 と NH24）
        return False
    if a["types"] and b["types"] and not (a["types"] & b["types"]):
        return False
    return core_sim(a, b) >= core_min


def split_parts(full: str) -> list[str]:
    """GTFS の「A / B」は全体と各部分を候補にする。"""
    full = str(full)
    return [full] + [p for p in full.split("/") if p.strip()] if "/" in full else [full]


# ---- 文字列の照合 ----------------------------------------------------------------------------

class RouteIndex:
    """1 路線の代表パターンの停留所名から作った照合の索引。"""

    def __init__(self, g: pd.DataFrame):
        self.seq = g.seq.to_numpy()
        self.lat = g.stop_lat.to_numpy()
        self.lon = g.stop_lon.to_numpy()
        self.sid = dict(zip(g.seq, g.stop_id))
        self.feat: list[dict] = []
        self.idx: dict[str, dict] = {c: {} for c in ("k0", "k1", "k2", "ks", "kk")}
        for seq, full in zip(g.seq, g.stop_name):
            for part in split_parts(full):
                k = keys(part)
                if not k["k0"]:
                    continue
                for c in self.idx:
                    if k[c]:
                        self.idx[c].setdefault(k[c], []).append(len(self.feat))
                self.feat.append(dict(k, seq=int(seq)))

    def _seqs(self, ids) -> list[int]:
        return sorted({self.feat[i]["seq"] for i in ids})

    def _unique(self, ids) -> bool:
        return len({self.sid[self.feat[i]["seq"]] for i in ids}) == 1

    def match(self, k: dict, core_min: float = CORE_MIN, fuzzy_min: float = FUZZY_MIN) -> tuple[list[int], str, str]:
        """名前の鍵 k → (seq の一覧, how, 段階)。決まらなければ ([], "none", "none" か "ambiguous")。"""
        ids = self.idx["k0"].get(k["k0"])
        if ids:
            return self._seqs(ids), "exact", "exact"
        ok = [guard_ok(k, f, core_min) for f in self.feat]
        for c, step in (("k1", "abbr"), ("k2", "phonetic"), ("ks", "sorted")):
            ids = [i for i in self.idx[c].get(k[c], ()) if ok[i]]
            if ids:
                return self._seqs(ids), "rule", step
        if len(k["kk"]) >= 4:
            ids = [i for i in self.idx["kk"].get(k["kk"], ()) if ok[i]]
            if ids and self._unique(ids):
                return self._seqs(ids), "rule", "skeleton"
        cand = [i for i in range(len(self.feat)) if ok[i]]
        if not cand:
            return [], "none", "none"
        # ここから下は近さで選ぶ（how = fuzzy）。券の名前が路線の 2 つ以上の停留所の名前に含まれるとき
        # （Shastri Park → Shastri Park Metro Depot と Shastri Park GT Road）は、文字列では決めない
        k2 = k["k2"]
        if len(k2) >= 4 and len({self.sid[self.feat[i]["seq"]] for i in cand if k2 in self.feat[i]["k2"]}) >= 2:
            return [], "none", "ambiguous"
        # 一方向の包含: 券の名前が GTFS の名前の頭か尾にある（Mahipal Pur → Mahipal Pur Village）。
        # 逆向き（券の方が長い: Kirti Ngr Rly Reser Office → Kirti Nagar）は GPS で確かめると誤りが多いので使わない
        if len(k2) >= 5:
            ids = [i for i in cand if len(self.feat[i]["k2"]) >= 5 and (
                self.feat[i]["k2"].startswith(k2) or self.feat[i]["k2"].endswith(k2))]
            if ids and self._unique(ids):
                return self._seqs(ids), "fuzzy", "contain"
        # 音写を畳んだ鍵の文字の近さ（首位が 88 点以上で、2 位の別の鍵より 4 点以上高い）
        by_k2: dict[str, list[int]] = {}
        for i in cand:
            by_k2.setdefault(self.feat[i]["k2"], []).append(i)
        ranked = sorted(((fuzz.ratio(k2, c), c) for c in by_k2), reverse=True)
        if ranked[0][0] >= 88 and (len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= 4):
            return self._seqs(by_k2[ranked[0][1]]), "fuzzy", "fuzzy_fold"
        # 語の並びの近さ（token_sort）と、片方の語がもう片方に含まれるか（token_set）の平均
        by_n1: dict[str, list[int]] = {}
        for i in cand:
            by_n1.setdefault(self.feat[i]["n1"], []).append(i)
        best, bc = max((0.5 * fuzz.token_sort_ratio(k["n1"], c) + 0.5 * fuzz.token_set_ratio(k["n1"], c), c)
                       for c in by_n1)
        if best >= fuzzy_min:
            return self._seqs(by_n1[bc]), "fuzzy", "fuzzy_tok"
        return [], "none", "none"

    def nearest(self, xy: np.ndarray, max_m: float) -> int | None:
        d = np.min(C.dist_m(self.lat[:, None], self.lon[:, None], xy[None, :, 0], xy[None, :, 1]), axis=1)
        j = int(np.argmin(d))
        return int(self.seq[j]) if d[j] <= max_m else None


class GlobalIndex:
    """市内の全停留所の名前 → 場所（路線の代表パターンに無い停留所の名前でも、場所が分かるように）。"""

    def __init__(self):
        st = C.stops()
        self.by: dict[str, dict] = {c: {} for c in ("k0", "k1", "k2")}
        names: dict[str, tuple[dict, list]] = {}
        for full, lat, lon in zip(st.stop_name, st.stop_lat, st.stop_lon):
            for part in split_parts(full):
                k = keys(part)
                if not k["k0"]:
                    continue
                for c in self.by:
                    self.by[c].setdefault(k[c], []).append((lat, lon))
                names.setdefault(k["n1"], (k, []))[1].append((lat, lon))
        self.n1 = list(names)
        self.val = [names[n] for n in self.n1]

    def locate(self, k: dict, core_min: float = CORE_MIN) -> np.ndarray | None:
        for c in self.by:
            xy = self.by[c].get(k[c])
            if xy:
                return np.asarray(xy)
        for _, _, i in process.extract(k["n1"], self.n1, scorer=fuzz.token_sort_ratio, score_cutoff=90, limit=5):
            kk, xy = self.val[i]
            if guard_ok(k, kk, core_min):
                return np.asarray(xy)
        return None


def name_pairs(tk: pd.DataFrame) -> pd.DataFrame:
    """券の（路線, 停留所名）の組と、その端の数（乗車・降車）。"""
    t = tk[tk.route_id.notna()]
    e = pd.concat([t[["route_id", "start_stop_name"]].rename(columns={"start_stop_name": "name"}).assign(end="s"),
                   t[["route_id", "end_stop_name"]].rename(columns={"end_stop_name": "name"}).assign(end="e")])
    e = e[e.name.notna()]
    return e.groupby(["route_id", "name"]).end.agg(n_s=lambda x: (x == "s").sum(), n_e=lambda x: (x == "e").sum()).reset_index()


def name_variants(name: str) -> list[str]:
    """券の名前と、「A / B」のように呼び名をつないだ名前の各部分（Sec-3/4 のように空白の無い / では分けない）。"""
    parts = [p.strip() for p in re.split(r"\s+/\s*|\s*/\s+", name)] if "/" in name else []
    return [name] + [p for p in parts if len(p) >= 3 and p != name]


def match_names(pairs: pd.DataFrame, pat: pd.DataFrame, core_min: float = CORE_MIN, fuzzy_min: float = FUZZY_MIN,
                nearby_m: float = NEARBY_M, verbose: bool = True) -> pd.DataFrame:
    """（路線, 名前）→ seq の一覧（文字列の照合と地理的な退避まで）。返り値: route_id, name, seqs, how, step"""
    t0 = time.time()
    idx = {r: RouteIndex(g) for r, g in pat.groupby("route_id")}
    glob = GlobalIndex()
    rank = {h: i for i, h in enumerate(ORDER)}
    rows = []
    for rid, name in zip(pairs.route_id, pairs.name):
        ri = idx.get(rid)
        if ri is None or not isinstance(name, str):
            continue
        vs = name_variants(name)
        seqs, how, step = ri.match(keys(name), core_min, fuzzy_min)
        if not seqs and len(vs) > 1:
            # 全体で決まらなければ各部分で。部分どうしで結果が違えば、確からしい方法で決まった部分を採る
            res = [r for r in (ri.match(keys(v), core_min, fuzzy_min) for v in vs[1:]) if r[0]]
            if res:
                seqs, how, step = min(res, key=lambda r: rank[r[1]])
                step = f"part:{step}"
        if not seqs:
            for v in vs:
                xy = glob.locate(keys(v), core_min)
                s = ri.nearest(xy, nearby_m) if xy is not None else None
                if s is not None:
                    seqs, how, step = [s], "nearby", "nearby"
                    break
        rows.append((rid, name, seqs, how, step))
    mt = pd.DataFrame(rows, columns=["route_id", "name", "seqs", "how", "step"])
    if verbose:
        print(f"停留所名の照合（文字列）: {len(mt):,} 組、{time.time() - t0:.0f} 秒", flush=True)
    return mt


# ---- GPS の別名 ------------------------------------------------------------------------------

def bus_positions(tk: pd.DataFrame, pat: pd.DataFrame) -> pd.DataFrame:
    """車両番号つきの券ごとに、購入の直前（60 秒以内）の GPS の点に最も近い、券の路線の停留所の seq（300m 以内）。
    tk: tid, vehicle_number, route_id, created_at, date"""
    con = C.connect()
    con.register("pat_df", pat[["route_id", "seq", "stop_lat", "stop_lon"]])
    con.execute("CREATE TABLE pat AS SELECT CAST(route_id AS INT) AS rid, seq, stop_lat, stop_lon FROM pat_df")
    t = tk[tk.vehicle_number.notna() & tk.route_id.notna()]
    out = []
    for d, day in t.groupby("date"):
        g = C.GPS / f"date={d}" / "part.parquet"
        if not g.exists():
            continue
        con.register("day", day[["tid", "vehicle_number", "route_id", "created_at"]])
        r = con.execute(f"""
            WITH t AS (SELECT tid, vehicle_number AS vid, CAST(route_id AS INT) AS rid, created_at FROM day),
                 g AS (SELECT vehicle_id AS vid, ts, lat, lng FROM read_parquet('{g.as_posix()}')
                       WHERE vehicle_id IN (SELECT DISTINCT vid FROM t)),
                 pos AS (SELECT t.tid, t.rid, g.lat, g.lng, epoch(t.created_at) - epoch(g.ts) AS lag
                         FROM t ASOF JOIN g ON g.vid = t.vid AND g.ts <= t.created_at),
                 c AS (SELECT pos.tid, pat.seq,
                              sqrt(pow((pos.lat - pat.stop_lat) * {C.M_PER_DEG_LAT}, 2)
                                   + pow((pos.lng - pat.stop_lon) * {C.M_PER_DEG_LNG}, 2)) AS dm
                       FROM pos JOIN pat ON pat.rid = pos.rid WHERE pos.lag <= {MAX_LAG_S})
            SELECT tid, arg_min(seq, dm) AS seq_near, min(dm) AS d_near FROM c GROUP BY tid
        """).df()
        con.unregister("day")
        out.append(r[r.d_near <= MAX_OFF_M])
    return pd.concat(out, ignore_index=True)


def gps_votes(tk: pd.DataFrame, mt: pd.DataFrame, pat: pd.DataFrame, days=None,
              use_cache: bool = True) -> tuple[pd.DataFrame, dict]:
    """（路線, 乗車名）ごとの GPS の多数決。返り値: (route_id, name, n, seq_gps, share, margin の表, ずれの分布 P(k))

    1. ずれの分布 P(k): 完全一致で路線上の1か所に決まる乗車名の券で、k = 購入時の最寄りの停留所 − 乗車停留所
    2. 各停留所 s の点数 = Σ_券 P(購入時の最寄りの停留所 − s)。首位を推定、(首位 − 2位) / 枚数 を確からしさとする
    days: 学ぶ日。既定は学習期間（10/1〜24）だけ（検証週はモデル作成に使わない決まりなので、照合にも使わない）。
    結果は data/processed/stop_alias_gps_{期間}.parquet に保存する（元データ由来の名前を含むので git には入れない）。
    """
    days = sorted(days or C.TRAIN_DAYS)
    tag = f"{days[0]:%m%d}-{days[-1]:%m%d}"
    out = C.PROCESSED / f"stop_alias_gps_{tag}.parquet"
    pk_path = C.PROCESSED / f"stop_alias_pk_{tag}.json"
    if use_cache and out.exists() and pk_path.exists():
        return pd.read_parquet(out), {int(k): v for k, v in json.loads(pk_path.read_text(encoding="utf-8")).items()}
    t0 = time.time()
    tk = tk[tk.date.isin(set(days))]
    tk = tk[["vehicle_number", "route_id", "start_stop_name", "created_at", "date"]].reset_index(drop=True)
    tk["tid"] = np.arange(len(tk))
    pos = bus_positions(tk, pat).merge(tk[["tid", "route_id", "start_stop_name"]], on="tid")
    pos = pos.rename(columns={"start_stop_name": "name"})
    ex = mt[(mt.how == "exact") & (mt.seqs.map(len) == 1)]
    truth = {(r, n): s[0] for r, n, s in zip(ex.route_id, ex.name, ex.seqs)}
    tr = np.array([truth.get((r, n), -10_000) for r, n in zip(pos.route_id, pos.name)])
    k = pos.seq_near.to_numpy()[tr > -10_000] - tr[tr > -10_000]
    pk = {int(v): float((k == v).mean()) for v in range(KMIN, KMAX + 1)}
    con = C.connect()
    con.register("pos", pos[["route_id", "name", "seq_near"]])
    con.register("pk", pd.DataFrame({"k": list(pk), "p": list(pk.values())}))
    con.register("ns", pat.groupby("route_id").seq.max().add(1).rename("nstops").reset_index())
    gv = con.execute("""
        WITH c AS (SELECT route_id, name, seq_near, count(*) AS c FROM pos GROUP BY ALL),
             n AS (SELECT route_id, name, sum(c) AS n FROM c GROUP BY ALL),
             s AS (SELECT c.route_id, c.name, c.seq_near - pk.k AS s, sum(c.c * pk.p) AS score
                   FROM c CROSS JOIN pk JOIN ns ON ns.route_id = c.route_id
                   WHERE c.seq_near - pk.k BETWEEN 0 AND ns.nstops - 1
                   GROUP BY ALL),
             r AS (SELECT *, row_number() OVER (PARTITION BY route_id, name ORDER BY score DESC, s) AS rk FROM s)
        SELECT a.route_id, a.name, CAST(n.n AS INT) AS n, CAST(a.s AS INT) AS seq_gps, a.score / n.n AS share,
               (a.score - coalesce(b.score, 0)) / n.n AS margin
        FROM r a JOIN n ON n.route_id = a.route_id AND n.name = a.name
        LEFT JOIN r b ON b.route_id = a.route_id AND b.name = a.name AND b.rk = 2
        WHERE a.rk = 1
    """).df()
    gv.to_parquet(out, index=False)
    pk_path.write_text(json.dumps(pk), encoding="utf-8")
    print(f"GPS の多数決（{tag}）: 位置が取れた券 {len(pos):,} 枚、（路線, 乗車名）{len(gv):,} 組、{time.time() - t0:.0f} 秒",
          flush=True)
    return gv, pk


def resolve(mt: pd.DataFrame, gv: pd.DataFrame, pat: pd.DataFrame, n_min: int = GPS_N_MIN,
            margin_min: float = GPS_MARGIN_MIN, override: tuple = ("fuzzy", "nearby")) -> pd.DataFrame:
    """文字列の照合（mt）と GPS の多数決（gv）を合わせて、（路線, 名前）→ seq の一覧を決める。

    GPS の推定（枚数 n_min 以上・差 margin_min 以上）は、文字列で決まらない名前を補い、override の方法で決めた
    停留所と 2 停留所以上食い違えば置き換える。起点・終点への推定は、名前の固有の部分が近いときだけ使う。
    返り値: route_id, name, seqs, how, step（gps_fill / gps_over_fuzzy … / gps_terminal_skip）
    """
    last = pat.groupby("route_id").seq.max().to_dict()
    sname = {(r, s): n for r, s, n in zip(pat.route_id, pat.seq, pat.stop_name)}
    g = gv[(gv.n >= n_min) & (gv.margin >= margin_min)]
    gmap = dict(zip(zip(g.route_id, g.name), g.seq_gps))
    seqs, how, step = [], [], []
    for rid, name, sq, h, st in zip(mt.route_id, mt.name, mt.seqs, mt.how, mt.step):
        s = gmap.get((rid, name))
        if s is None or not (h == "none" or h in override) or (sq and min(abs(x - s) for x in sq) <= 1):
            seqs.append(sq); how.append(h); step.append(st)
            continue
        s = int(s)
        if s in (0, last[rid]) and max(core_sim(keys(v), keys(p)) for v in name_variants(name)
                                        for p in split_parts(sname[(rid, s)])) < TERMINAL_CORE_MIN:
            seqs.append(sq); how.append(h); step.append(f"{st}|gps_terminal_skip")
            continue
        seqs.append([s]); how.append("gps"); step.append("gps_fill" if h == "none" else f"gps_over_{h}")
    return mt.assign(seqs=seqs, how=how, step=step)


# ---- 券への当てはめ ------------------------------------------------------------------------

def assign(tk: pd.DataFrame, fin: pd.DataFrame) -> pd.DataFrame:
    """券ごとに 乗車 seq i、降車 seq j（i より後で最初に出てくる同名停留所）、照合の方法を付ける。"""
    look = {(r, n): (s, h) for r, n, s, h in zip(fin.route_id, fin.name, fin.seqs, fin.how)}
    rank = {h: i for i, h in enumerate(ORDER)}
    i_l, j_l, m_l, hs_l, he_l = [], [], [], [], []
    for rid, s, e in zip(tk.route_id, tk.start_stop_name, tk.end_stop_name):
        a, b = look.get((rid, s)), look.get((rid, e))
        hs_l.append(a[1] if a else None)
        he_l.append(b[1] if b else None)
        if not a or not b or not a[0] or not b[0]:
            i_l.append(-1); j_l.append(-1); m_l.append(None)
            continue
        i = a[0][0]
        later = [x for x in b[0] if x > i]
        i_l.append(i); j_l.append(later[0] if later else -1)
        m_l.append(max(a[1], b[1], key=rank.get))
    return tk.assign(i=i_l, j=j_l, match=m_l, match_start=hs_l, match_end=he_l)


def metrics(tk: pd.DataFrame, mt: pd.DataFrame, fin: pd.DataFrame, gv: pd.DataFrame, pk: dict) -> dict:
    """照合の量と、GPS の多数決との一致（名前は含めない集計だけ）。results/stop_match_metrics.json に保存する。"""
    pairs = name_pairs(tk)
    pairs["ends"] = pairs.n_s + pairs.n_e
    n_ends = int(pairs.ends.sum())
    f = fin.merge(pairs, on=["route_id", "name"], how="left")
    m = mt.merge(pairs, on=["route_id", "name"], how="left")

    def share(df, col):
        return {k: round(float(v) / n_ends * 100, 2) for k, v in df.groupby(col).ends.sum().sort_values(ascending=False).items()}

    # 文字列の照合（GPS で置き換える前）と GPS の多数決の一致: 枚数 10 以上・差 0.3 以上の組で
    g = gv[(gv.n >= GPS_N_MIN) & (gv.margin >= GPS_MARGIN_MIN)][["route_id", "name", "n", "seq_gps"]]
    c = m.merge(g, on=["route_id", "name"])
    c = c[c.how != "none"]
    c["agree"] = [s in q for s, q in zip(c.seq_gps, c.seqs)]
    c["agree1"] = [min(abs(s - x) for x in q) <= 1 for s, q in zip(c.seq_gps, c.seqs)]
    agree = {}
    for key, d in list(c.groupby("step")) + [("(all)", c)]:
        agree[key] = {"pairs": int(len(d)), "agree_%": round(float(d.agree.mean() * 100), 1),
                      "agree_within1_%": round(float(d.agree1.mean() * 100), 1),
                      "agree_ticket_weighted_%": round(float(np.average(d.agree, weights=d.n) * 100), 1)}
    t_route = tk.route_id.notna()
    return {
        "tickets": int(len(tk)),
        "route_matched_%": round(float(t_route.mean() * 100), 1),
        "ends_with_route": n_ends,
        "ends_by_method_before_gps_%": share(m, "how"),
        "ends_by_method_%": share(f, "how"),
        "ends_by_step_%": share(f, "step"),
        "unmatched_ends_%": round(float(100 - f[f.how != "none"].ends.sum() / n_ends * 100), 2),
        "tickets_both_ends_matched_forward_%": round(float((tk.j > tk.i).mean() * 100), 1),
        "tickets_by_method_%": {k: round(float(v) * 100, 1) for k, v in tk[tk.j > tk.i].match.value_counts(normalize=True).items()},
        "gps_offset_distribution_P(k)": {str(k): round(v, 4) for k, v in pk.items()},
        "gps_pairs_confident": int(len(g)),
        "string_match_agreement_with_gps": agree,
    }
