"""試す順番 4: 雨の時間帯に、バスが「いつもの値」よりどれだけ遅くなったか（検証週の全区間の観測）。

いつもの値 = 区間 × 平日/休日 × 時間帯 の対数平均（学習期間 10/1〜24）。
比 = 実際の区間所要時間 / いつもの値。日付 × 時間ごとに、比の中央値（全区間）を出す。
雨（報道・IMD）: 10/29 夜〜10/30 朝（24 時間で Safdarjung 61.4mm）。学習期間では 10/11 夜〜10/12 朝（41.6mm）。
Open-Meteo（キー不要）の時間雨量も並べる（10/11〜12 の雨は取り逃しているので、雨の有無は報道を正とする）。
使い方: python -X utf8 experiments/p1_external/rain_check.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tsh import common as C  # noqa: E402

IMP = C.PROCESSED / "improve"


def rain_hourly() -> pd.Series:
    url = ("https://archive-api.open-meteo.com/v1/archive?latitude=28.58&longitude=77.21"
           "&start_date=2026-10-01&end_date=2026-10-31&hourly=precipitation&timezone=Asia%2FKolkata")
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    return pd.Series(d["hourly"]["precipitation"], index=pd.to_datetime(d["hourly"]["time"]))


def main():
    con = C.connect()
    q = f"""
        WITH o AS (SELECT from_stop, to_stop, ln(link_s) AS ls, day_type,
                          hour(timezone('{C.TZ}', to_timestamp(t))) AS hr, CAST(timezone('{C.TZ}', to_timestamp(t)) AS DATE) AS d
                   FROM '{{p}}' WHERE link_s > 0)
        SELECT * FROM o"""
    con.execute(f"CREATE TABLE tr AS {q.format(p=(IMP / 'obs_train.parquet').as_posix())}")
    con.execute(f"CREATE TABLE te AS {q.format(p=(IMP / 'obs_test.parquet').as_posix())}")
    con.execute("CREATE TABLE m AS SELECT from_stop, to_stop, day_type, hr, avg(ls) AS m, count(*) AS n FROM tr GROUP BY ALL")
    r = con.execute("""
        SELECT x.d, x.hr, median(exp(x.ls - m.m)) AS ratio, count(*) AS n
        FROM (SELECT * FROM te UNION ALL SELECT * FROM tr) x
        JOIN m USING (from_stop, to_stop, day_type, hr) WHERE m.n >= 5 GROUP BY ALL ORDER BY ALL""").df()
    r["ts"] = pd.to_datetime(r.d.astype(str)) + pd.to_timedelta(r.hr, unit="h")
    try:
        rain = rain_hourly()
        r["rain_mm"] = r.ts.map(rain)
    except Exception as e:  # noqa: BLE001
        print("Open-Meteo を取れなかった:", e)
        r["rain_mm"] = float("nan")
    pd.set_option("display.width", 200)
    piv = r.pivot_table(index="hr", columns=r.d.astype(str).str[5:], values="ratio").round(2)
    cols = [c for c in piv.columns if c in ("10-11", "10-12", "10-13", "10-28", "10-29", "10-30", "10-31")]
    print("区間所要時間 / いつもの値 の中央値（時間 × 日付）")
    print(piv[cols].loc[6:23].to_string())
    print("\n時間雨量（Open-Meteo, mm）")
    rp = r.pivot_table(index="hr", columns=r.d.astype(str).str[5:], values="rain_mm")
    print(rp[[c for c in cols if c in rp.columns]].loc[0:23].round(1).to_string())
    day = r[r.hr.between(7, 21)].groupby(r.d.astype(str)).apply(lambda g: (g.ratio * g.n).sum() / g.n.sum()).round(3)
    print("\n日ごとの比（7〜21 時、件数で重み）")
    print(day.to_string())


if __name__ == "__main__":
    main()
