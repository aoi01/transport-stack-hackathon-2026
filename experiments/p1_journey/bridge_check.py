"""正解（Replay）を、分かれて記録された便をつなぐ前と後で比べる（docs 16.8）。ランダムな 2 万件の乗車。

python experiments/p1_journey/bridge_check.py
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, pandas as pd
from tsh import common as C
from tsh.traveltime import TravelTimeModel
from tsh.validate_journeys import Replay, load_passages
tt = TravelTimeModel("train")
ps = load_passages(C.TEST_DAYS)
t = time.time(); a = Replay(ps, tt.cum); print("plain", round(time.time() - t), "s")
t = time.time(); b = Replay(ps, tt.cum, tt=tt); print("bridged", round(time.time() - t), "s")
# 単調か
bad = sum(int((np.diff(ts) <= 0).any() or (np.diff(s) <= 0).any()) for lst in b.trips.values() for s, ts in lst)
print("単調でない走り", bad)
rng = np.random.default_rng(1)
keys = [k for k in a.trips if k[0] in tt.cum]
rows = []
while len(rows) < 20000:
    rid, d = keys[int(rng.integers(len(keys)))]
    n = len(tt.cum[rid])
    if n < 10: continue
    i = int(rng.integers(0, n - 5)); j = int(rng.integers(i + 3, n))
    t0 = pd.Timestamp(pd.Timestamp(d) + pd.Timedelta(seconds=int(rng.integers(7*3600, 21*3600))), tz=C.TZ).timestamp()
    ra, rb = a.ride_detail(rid, d, i, j, t0), b.ride_detail(rid, d, i, j, t0)
    st = lambda r: "nobus" if r is None else ("untracked" if r[1] is None else "ok")
    rows.append({"sa": st(ra), "sb": st(rb), "wa": (ra[0] - t0) if ra else np.nan, "wb": (rb[0] - t0) if rb else np.nan})
df = pd.DataFrame(rows)
print(pd.crosstab(df.sa, df.sb, margins=True))
both = df.dropna()
print("待ちが短くなった", round((both.wb < both.wa - 1).mean() * 100, 1), "%  そのときの差の中央値(分)", round(((both.wa - both.wb)[both.wb < both.wa - 1]).median() / 60, 1))
print("待ちの中央値(分)", round(both.wa.median() / 60, 2), "→", round(both.wb.median() / 60, 2))
