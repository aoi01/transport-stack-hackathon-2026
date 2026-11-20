"""問2の誤差の内訳を見る（探索用）。"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa
sys.stdout.reconfigure(encoding="utf-8")

tr = pd.read_parquet(C.PROCESSED / "train" / "crowding.parquet")
te = pd.read_parquet(C.PROCESSED / "test" / "crowding.parquet")
print(tr.columns.tolist())
k = ["route_id", "seq", "day_type", "hr"]
m = tr[k + ["load", "n_tickets", "confidence", "pax", "trips_total"]].merge(
    te[k + ["load", "n_tickets", "pax", "trips_total"]], on=k, suffixes=("_tr", "_te"))
x = m[m.n_tickets_te >= 5]
rel = (x.load_tr - x.load_te).abs() / x.load_te
print("cells", len(x), "median rel", rel.median())
print("n_te quantiles", x.n_tickets_te.quantile([.1,.25,.5,.75,.9]).to_dict())
for lo, hi in [(5,10),(10,20),(20,50),(50,100),(100,200),(200,10**9)]:
    s = x[(x.n_tickets_te>=lo)&(x.n_tickets_te<hi)]
    r = (s.load_tr - s.load_te).abs()/s.load_te
    print(f"n_te {lo}-{hi}: cells {len(s)} median rel {r.median()*100:.1f}%  bias(med log ratio) {np.median(np.log(s.load_tr/s.load_te)):.3f}")
print("overall median log ratio tr/te", np.median(np.log(x.load_tr/x.load_te)))
print("WAPE", (x.load_tr-x.load_te).abs().sum()/x.load_te.sum())
# trips ratio
print("trips per day ratio median", np.median((x.trips_total_tr/24)/(x.trips_total_te/7)))
# daily volume trend
tk = pd.read_parquet(C.PROCESSED / "tickets_matched.parquet", columns=["date","pax","vehicle_number","i","j"])
d = tk.groupby("date").agg(pax=("pax","sum"), veh=("vehicle_number", lambda s: s.notna().sum()), n=("pax","size"))
d["blank"] = d.n - d.veh
d["dow"] = pd.to_datetime(d.index).day_name().str[:3]
print(d.to_string())
