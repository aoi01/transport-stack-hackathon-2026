"""実際の通過の時刻表（PassageTimetable）が出す「次のバス」と、正解（Replay）の「次のバス」が、同じ日・同じ通過データで一致するか。
python experiments/p1_passages/wait_check.py（環境変数 TSH_PASSAGES で通過を選ぶ）"""
import sys
from datetime import datetime
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from tsh import common as C
from tsh.traveltime import TravelTimeModel
from tsh.validate_journeys import Replay, load_passages
from tsh.waitmodel import PassageTimetable
sys.stdout.reconfigure(encoding="utf-8")
days = C.TEST_DAYS
tt = TravelTimeModel("train")
ps = load_passages(days)
rp = Replay(ps, tt.cum, tt=tt)
pt = PassageTimetable(days)
rng = np.random.default_rng(1)
keys = list(rp.trips.keys())
rows = []
while len(rows) < 3000:
    rid, d = keys[rng.integers(len(keys))]
    if rid not in tt.cum: continue
    i = int(rng.integers(len(tt.cum[rid]) - 1))
    sec = int(rng.integers(7 * 3600, 21 * 3600))
    t = datetime(d.year, d.month, d.day) + pd.Timedelta(seconds=sec)
    t0 = pd.Timestamp(t, tz=C.TZ).timestamp()
    r = rp.ride_detail(rid, d, i, i, t0)
    k = days.index(d)
    b = pt._next(rid, i, C.day_type(d), [x for x in pt.days_of[C.day_type(d)]].index(k) * 0 + k, sec)
    rows.append((r[0] - t0 if r else np.nan, b - sec if b is not None else np.nan))
x = pd.DataFrame(rows, columns=["replay", "table"]).dropna()
x["diff"] = (x.table - x.replay) / 60
print(len(x), "中央値 表−正解（分）", round(x["diff"].median(), 2), "平均", round(x["diff"].mean(), 2),
      "一致(±1分)", round((x["diff"].abs() <= 1).mean() * 100, 1), "表が早い", round((x["diff"] < -1).mean() * 100, 1), "表が遅い", round((x["diff"] > 1).mean() * 100, 1))
