"""路線 × 平日/休日 の単位で、学習期間 → 検証週の誤差が大きい路線は何が起きているか（人数・便数・車両番号の有無の内訳）。"""
from agg import *  # noqa: F401,F403
d, g = daily("train"); dte, gte = daily("test")
tk = pd.read_parquet(C.PROCESSED / "tickets_matched.parquet", columns=["route_id", "date", "pax", "vehicle_number", "i", "j"])
tk = tk[tk.j > tk.i]
tk["veh"] = tk.vehicle_number.notna()
tk["wk"] = np.where(tk.date.isin(set(C.TEST_DAYS)), "te", "tr")
tk["dt"] = tk.date.map(C.day_type)
v = tk.groupby(["route_id", "dt", "wk"]).agg(tickets=("pax", "size"), veh_share=("veh", "mean")).unstack("wk")
v.columns = [f"{a}_{b}" for a, b in v.columns]
v = v.reset_index().rename(columns={"dt": "day_type"})
ndays = {("tr", "weekday"): sum(C.day_type(x) == "weekday" for x in C.TRAIN_DAYS), ("tr", "weekend"): sum(C.day_type(x) == "weekend" for x in C.TRAIN_DAYS),
         ("te", "weekday"): 5, ("te", "weekend"): 2}
s_tr = seg_sums(d, None); t_tr = trips_rdh(g, None); s_te = seg_sums(dte, None); t_te = trips_rdh(gte, None)
keys = ["route_id", "day_type"]
a = level_table(s_tr, t_tr, keys).merge(level_table(s_te, t_te, keys), on=keys, suffixes=("_tr", "_te"))
a = a.merge(v, on=keys, how="left")
a["load_tr"] = a.pax_tr / a.T_tr; a["load_te"] = a.pax_te / a.T_te
a["Td_tr"] = a.T_tr / a.day_type.map(lambda x: ndays[("tr", x)]); a["Td_te"] = a.T_te / a.day_type.map(lambda x: ndays[("te", x)])
a["paxd_tr"] = a.pax_tr / a.day_type.map(lambda x: ndays[("tr", x)]); a["paxd_te"] = a.pax_te / a.day_type.map(lambda x: ndays[("te", x)])
a["err"] = (a.load_tr - a.load_te) / a.load_te
a["abs_contrib"] = (a.load_tr - a.load_te).abs() * a.T_te
a = a[a.n_te >= 20]
pd.set_option("display.width", 250)
cols = ["route_id", "day_type", "tickets_tr", "tickets_te", "paxd_tr", "paxd_te", "Td_tr", "Td_te", "load_tr", "load_te", "err", "veh_share_tr", "veh_share_te"]
print(a.sort_values("abs_contrib", ascending=False)[cols].head(15).round(2).to_string())
print("\n|log 比| の中央値: 1日の人数", round(np.median(np.abs(np.log(a.paxd_tr / a.paxd_te))) * 100, 1),
      " 1日の便数", round(np.median(np.abs(np.log(a.Td_tr / a.Td_te))) * 100, 1),
      " 1便あたり", round(np.median(np.abs(np.log(a.load_tr / a.load_te))) * 100, 1))
print("相関（log 比）: 人数の変化 vs 便数の変化", round(np.corrcoef(np.log(a.paxd_tr / a.paxd_te), np.log(a.Td_tr / a.Td_te))[0, 1], 3))
print("車両番号つきの割合の変化 vs 1日の人数の変化", round(np.corrcoef(a.veh_share_te - a.veh_share_tr, np.log(a.paxd_te / a.paxd_tr))[0, 1], 3))
