"""問2の予測の改善を、調整（学習期間の中だけ）→ 検証週で比べる。

調整: 10/1〜16 で作り、10/21〜24（異常の無い直近の日）を当てる。ここで κ・β・半減期を選ぶ。
検証: 10/1〜24 で作り、10/25〜31 を当てる（今の検証と同じ正解。頭打ちの前の 1 便あたりの人数）。

比べるマスの集合は全部の方法で同じにする:
  旧来の集合   … 学習期間に券があり、検証週の券が 5 枚以上のマス（今の tsh.validate_p2 と同じ）
  見込みの集合 … 学習期間の券の率 × 検証週の便数で見込んだ券が 5 枚以上のマス（検証週の結果で選ばないので偏りが無い）
ある方法でマスが作れない（例: 異常日を外したら券が無くなった）ときは、今の方式の値で埋める。
ノイズの床 … 検証週の券を無作為に半分に分けた A・B の |A−B|/(A+B) の中央値（完璧な予測でも避けられない誤差の目安）。
"""
from __future__ import annotations

import itertools
import json

from models import *  # noqa: F401,F403

sys.stdout.reconfigure(encoding="utf-8")
FIT_TUNE = [OCT(x) for x in range(1, 17)]
TGT_TUNE = [OCT(x) for x in range(21, 25)]


def metrics(m: pd.DataFrame, col="pred") -> dict:
    rel = (m[col] - m.y).abs() / m.y
    out = {"cells": int(len(m)), "median_rel_%": round(float(rel.median() * 100), 2),
           "within10_%": round(float((rel <= 0.10).mean() * 100), 1),
           "WAPE_%": round(float((m[col] - m.y).abs().sum() / m.y.sum() * 100), 2),
           "bias_med_log": round(float(np.median(np.log(m[col] / m.y))), 3)}
    if "pa" in m:
        out["floor_%"] = round(float(((m.pa - m.pb).abs() / (m.pa + m.pb)).median() * 100), 2)
    return out


def join(pred: pd.DataFrame, truth: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """truth のマスに pred を付け、無いものは base で埋める。"""
    m = truth.merge(pred[K + ["pred"]], on=K, how="left").merge(base[K + ["pred"]].rename(columns={"pred": "b"}), on=K, how="left")
    m["pred"] = m.pred.where(np.isfinite(m.pred) & (m.pred > 0), m.b)
    return m


def main():
    d, grid = train_daily()
    # ---- 調整 ----
    tt = cells_from_daily(d[d.date.isin(set(TGT_TUNE))], grid[grid.date.isin(set(TGT_TUNE))])
    tt = tt[tt["T"] > 0].assign(y=lambda x: x.pax / x["T"])
    b_t = predict(d, grid, FIT_TUNE, TGT_TUNE, calendar=False, compose=False)
    tt = tt.merge(b_t[K + ["n", "T"]].rename(columns={"n": "n_fit", "T": "T_fit"}), on=K)
    tt["n_exp"] = tt.n_fit / tt.T_fit * tt["T"]
    sets_t = {"旧来": tt[tt.n >= 5], "見込み": tt[tt.n_exp >= 5]}
    rows = []

    def ev(a, **kw):
        p = apply(a, **{k: v for k, v in kw.items() if k in ("kappa", "beta", "pool_daytype", "dseq", "dhr")})
        r = dict(kw)
        for nm, s in sets_t.items():
            mm = metrics(join(p, s, b_t))
            r[f"{nm}_median"] = mm["median_rel_%"]; r[f"{nm}_WAPE"] = mm["WAPE_%"]
        rows.append(r); print(r, flush=True)
        return r["見込み_median"]

    # 段階 1: 暦（異常日・曜日の構成・最近の重み）
    cells = {}
    for cal, comp, hl in [(False, False, None), (True, False, None), (True, True, None), (True, True, 7), (True, True, 14), (True, False, 7)]:
        cells[(cal, comp, hl)] = build_cells(d, grid, FIT_TUNE, TGT_TUNE, cal, comp, hl)
        ev(cells[(cal, comp, hl)], calendar=cal, compose=comp, half_life=hl, kappa=0, beta=0)
    st1 = pd.DataFrame(rows).sort_values("見込み_median").iloc[0]
    key = (bool(st1.calendar), bool(st1.compose), None if pd.isna(st1.half_life) else st1.half_life)
    a1 = cells[key]
    # 段階 2: 縮小（κ・区間の形を区分でまとめるか）と平滑化（β・窓）
    for kap in [2, 5, 10, 20, 50]:
        for pool in [True, False]:
            ev(a1, calendar=key[0], compose=key[1], half_life=key[2], kappa=kap, pool_daytype=pool, beta=0)
    for beta in [0.25, 0.5, 1.0]:
        for dseq, dhr in [(1, 0), (0, 1), (1, 1), (2, 1)]:
            ev(a1, calendar=key[0], compose=key[1], half_life=key[2], kappa=0, beta=beta, dseq=dseq, dhr=dhr)
    st2 = pd.DataFrame(rows).sort_values("見込み_median").iloc[0]
    # 段階 3: 縮小 × 平滑化の組み合わせ（段階 2 の最良の窓で）
    bk = pd.DataFrame(rows).query("beta > 0").sort_values("見込み_median").iloc[0]
    kk = pd.DataFrame(rows).query("kappa > 0").sort_values("見込み_median").iloc[0]
    for kap in [kk.kappa / 2, kk.kappa, kk.kappa * 2]:
        for beta in [bk.beta / 2, bk.beta]:
            ev(a1, calendar=key[0], compose=key[1], half_life=key[2], kappa=kap, pool_daytype=bool(kk.pool_daytype),
               beta=beta, dseq=int(bk.dseq), dhr=int(bk.dhr))
    tune = pd.DataFrame(rows)
    tune.to_csv(OUT / "tune.csv", index=False)
    best = tune.sort_values("見込み_median").iloc[0].to_dict()
    print("調整で選んだ設定（見込みの集合の誤差の中央値が最小）:", best)

    # ---- 検証 ----
    truth = test_truth().rename(columns={"y_te": "y"})
    sh = pd.read_parquet(OUT / "test_split_half.parquet")
    truth = truth.merge(sh, on=K, how="left")
    b = predict(d, grid, C.TRAIN_DAYS, C.TEST_DAYS, calendar=False, compose=False)
    truth = truth.merge(b[K + ["n", "T"]].rename(columns={"n": "n_tr", "T": "T_tr"}), on=K, how="inner")
    truth["n_exp"] = truth.n_tr / truth.T_tr * truth.T_te
    sets = {"旧来（検証週の券≥5）": truth[truth.n_te >= 5], "見込み（見込みの券≥5）": truth[truth.n_exp >= 5]}
    cfg = {k: best.get(k) for k in ["calendar", "compose", "half_life", "kappa", "beta", "pool_daytype", "dseq", "dhr"]}
    for k in ["half_life", "pool_daytype", "dseq", "dhr"]:
        if cfg[k] is None or (isinstance(cfg[k], float) and np.isnan(cfg[k])):
            cfg[k] = {"half_life": None, "pool_daytype": True, "dseq": 1, "dhr": 1}[k]
    cfg["calendar"] = bool(cfg["calendar"]); cfg["compose"] = bool(cfg["compose"]); cfg["pool_daytype"] = bool(cfg["pool_daytype"])
    cfg["dseq"] = int(cfg["dseq"]); cfg["dhr"] = int(cfg["dhr"])
    variants = {
        "今の方式": dict(calendar=False, compose=False),
        "異常日を外す": dict(calendar=True, compose=False),
        "異常日＋曜日の構成": dict(calendar=True, compose=True),
        "縮小のみ（κ=調整値）": dict(calendar=False, compose=False, kappa=cfg["kappa"], pool_daytype=cfg["pool_daytype"]),
        "平滑化のみ（β=調整値）": dict(calendar=False, compose=False, beta=cfg["beta"], dseq=cfg["dseq"], dhr=cfg["dhr"]),
        "調整で選んだ全部": cfg,
    }
    res = {}
    preds = {}
    for nm, kw in variants.items():
        p = predict(d, grid, C.TRAIN_DAYS, C.TEST_DAYS, **kw)
        preds[nm] = p
        res[nm] = {sn: metrics(join(p, s, b)) for sn, s in sets.items()}
        print(nm, kw, json.dumps(res[nm], ensure_ascii=False), flush=True)
    (OUT / "test_results.json").write_text(json.dumps({"tune_best": best, "cfg": cfg, "test": res}, ensure_ascii=False, indent=1,
                                                      default=str), encoding="utf-8")
    preds["調整で選んだ全部"][K + ["pred"]].to_parquet(OUT / "pred_best.parquet", index=False)


if __name__ == "__main__":
    main()
