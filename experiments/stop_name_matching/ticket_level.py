import pandas as pd
ROOT = "C:/Users/aoi/Desktop/india/transport-stack-hackathon-2026/data"
R = pd.read_csv("match_exp2_out.csv")
tk = pd.read_csv(ROOT + "/raw/ticketing/October-Delhi.csv", dtype=str, usecols=["route", "start_stop_name", "end_stop_name"])
n0 = len(tk)
b = {(r, n): v for r, n, v in zip(R.route, R.name, R.base)}
m = {(r, n): v for r, n, v in zip(R.route, R.name, R.imp)}
def cls(d, r, s, e):
    a, z = d.get((r, s), "noroute"), d.get((r, e), "noroute")
    if "noroute" in (a, z): return "noroute"
    if "none" in (a, z): return "unmatched"
    if a == "exact" and z == "exact": return "exact"
    return "other_matched"
for nm, d in [("baseline(no nearby)", b), ("cascade(no nearby)", m)]:
    c = pd.Series([cls(d, r, s, e) for r, s, e in zip(tk.route, tk.start_stop_name, tk.end_stop_name)]).value_counts() / n0 * 100
    print(nm, c.round(2).to_dict())
