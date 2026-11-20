"""集計の単位を変えると、誤差とノイズの床がどう変わるか。

単位（どれも 1 便あたりの人数。区間をまとめる単位では「区間ごとの人数の合計 / 便数」= 路線に沿った平均の混み具合に比例）:
  マス           路線 × 区間 × 平日/休日 × 1 時間     … 今の検証
  区間×時間帯    路線 × 区間 × 平日/休日 × 時間帯（6 つ）
  路線×1時間     路線 × 平日/休日 × 1 時間（区間をまとめる）
  路線×時間帯    路線 × 平日/休日 × 時間帯
  路線×1日       路線 × 平日/休日
時間帯: 深夜早朝 0–5 / 朝 6–7 / 朝ピーク 8–10 / 昼 11–16 / 夕ピーク 17–20 / 夜 21–23（ピークは docs 7.1 と同じ区切り）

予測: 今の方式（全日の 人数/便数）、異常日を外す、異常日＋曜日の構成、最近の重み（半減期 7 日）。
正解: 検証週の 人数/便数。ノイズの床: 検証週の券を半分に分けた A・B の |A−B|/(A+B) の中央値。
比べる単位の集合: 学習期間に券があり、検証週の券が 5 枚以上（今の検証と同じ選び方）。20 枚以上も出す。
"""
from __future__ import annotations

import json

from models import *  # noqa: F401,F403

sys.stdout.reconfigure(encoding="utf-8")
BANDS = {**{h: "0深夜早朝" for h in range(0, 6)}, 6: "1朝", 7: "1朝", 8: "2朝ピーク", 9: "2朝ピーク", 10: "2朝ピーク",
         **{h: "3昼" for h in range(11, 17)}, **{h: "4夕ピーク" for h in range(17, 21)}, **{h: "5夜" for h in range(21, 24)}}
LEVELS = {
    "マス": ["route_id", "seq", "day_type", "hr"],
    "区間×時間帯": ["route_id", "seq", "day_type", "band"],
    "路線×1時間": ["route_id", "day_type", "hr"],
    "路線×時間帯": ["route_id", "day_type", "band"],
    "路線×1日": ["route_id", "day_type"],
}


def trips_rdh(grid: pd.DataFrame, w: dict | None) -> pd.DataFrame:
    """(路線, 区分, 時間帯) の便数（重みつき）。GPS の路線でも GPS の便が 0 なら時刻表。"""
    g = grid.copy()
    g["w"] = 1.0 if w is None else g.date.map(w).fillna(0.0)
    g = g[g.w > 0]
    g["wg"] = g.trips * g.w; g["ws"] = g.sched_trips * g.w
    t = g.groupby(["route_id", "day_type", "hr"]).agg(Tg=("wg", "sum"), Ts=("ws", "sum"), gps=("gps", "first")).reset_index()
    t["T"] = np.where(t.gps & (t.Tg > 0), t.Tg, t.Ts)
    return t[["route_id", "day_type", "hr", "T"]]


def seg_sums(d: pd.DataFrame, w: dict | None) -> pd.DataFrame:
    d = d.copy()
    d["w"] = 1.0 if w is None else d.date.map(w).fillna(0.0)
    d = d[d.w > 0]
    d["wp"] = d.pax * d.w; d["wn"] = d.n_tickets * d.w
    return d.groupby(K).agg(pax=("wp", "sum"), n=("wn", "sum")).reset_index()


def level_table(s: pd.DataFrame, t: pd.DataFrame, keys: list[str], extra: list[str] = ()) -> pd.DataFrame:
    """単位ごとに Σ人数 / Σ便数。便数は単位に含まれる (路線, 区分, 時間) について 1 回ずつ足す。"""
    s = s.assign(band=s.hr.map(BANDS)); t = t.assign(band=t.hr.map(BANDS))
    num = s.groupby(keys)[["pax", "n", *extra]].sum().reset_index()
    tk = [k for k in keys if k != "seq"]
    den = t.groupby(tk)["T"].sum().reset_index()
    out = num.merge(den, on=tk, how="left")
    return out[out["T"] > 0]


def main():
    d_tr, g_tr = daily("train")
    d_te, g_te = daily("test")
    sh = pd.read_parquet(OUT / "test_split_half.parquet")
    s_te = seg_sums(d_te, None).merge(sh, on=K, how="left")
    t_te = trips_rdh(g_te, None)
    preds = {
        "今の方式": dict(calendar=False, compose=False, half_life=None),
        "異常日を外す": dict(calendar=True, compose=False, half_life=None),
        "異常日＋曜日の構成": dict(calendar=True, compose=True, half_life=None),
        "異常日＋曜日の構成＋最近の重み7日": dict(calendar=True, compose=True, half_life=7),
    }
    res = {}
    ndays_te = pd.Series([C.day_type(x) for x in C.TEST_DAYS]).value_counts()
    for supply in [False, True]:
        for pn, kw in preds.items():
            w = day_weights(C.TRAIN_DAYS, C.TEST_DAYS, **kw)
            wdt = pd.Series({dt: sum(v for x, v in w.items() if C.day_type(x) == dt) for dt in ["weekday", "weekend"]})
            s_tr = seg_sums(d_tr, w); t_tr = trips_rdh(g_tr, w)
            name = ("需要÷その週の便数: " if supply else "") + pn
            for ln, keys in LEVELS.items():
                tr = level_table(s_tr, t_tr, keys)
                te = level_table(s_te, t_te, keys, extra=["pa", "pb"])
                m = te.merge(tr[keys + ["pax", "T"]].rename(columns={"pax": "pax_tr", "T": "T_tr"}), on=keys)
                m = m[m.pax_tr > 0]
                m["y"] = m.pax / m["T"]
                if supply:   # 1 日あたりの人数（需要）を学習期間から、便数は検証週に実際に走った数（運行計画・リアルタイムで分かる量）
                    m["pred"] = m.pax_tr / m.day_type.map(wdt) * m.day_type.map(ndays_te) / m["T"]
                else:
                    m["pred"] = m.pax_tr / m.T_tr
                for mn in [5, 20]:
                    x = m[m.n >= mn]
                    rel = (x.pred - x.y).abs() / x.y
                    fl = ((x.pa - x.pb).abs() / (x.pa + x.pb))
                    r = {"units": int(len(x)), "median_rel_%": round(float(rel.median() * 100), 1),
                         "floor_%": round(float(fl.median() * 100), 1),
                         "within10_%": round(float((rel <= 0.1).mean() * 100), 1),
                         "WAPE_%": round(float((x.pred - x.y).abs().sum() / x.y.sum() * 100), 1),
                         "bias_med_log": round(float(np.median(np.log(x.pred / x.y))), 3),
                         "pax_share_%": round(float(x.pax.sum() / m.pax.sum() * 100), 1)}
                    res.setdefault(ln, {}).setdefault(f"券≥{mn}", {})[name] = r
                    print(ln, f"券≥{mn}", name, r, flush=True)
    (OUT / "agg_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
