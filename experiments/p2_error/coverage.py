"""GPS の捕捉率を、車両番号つきの券で測る: その券のバスが、その日その路線の停留所通過（GPS）に出てくるか。
路線 × 日ごとの「券から見た GPS の捕捉率」を保存する（out/gps_coverage.parquet）。"""
from base import *  # noqa: F401,F403
from tsh.traveltime import passages_glob
sys.stdout.reconfigure(encoding="utf-8")
days = C.TRAIN_DAYS + C.TEST_DAYS
tk = pd.read_parquet(C.PROCESSED / "tickets_matched.parquet", columns=["route_id", "date", "vehicle_number", "i", "j", "pax"])
tk = tk[(tk.j > tk.i) & tk.vehicle_number.notna() & tk.route_id.notna()]
con = C.connect()
con.register("tk", tk[["route_id", "date", "vehicle_number", "pax"]])
cov = con.execute(f"""
    WITH v AS (SELECT DISTINCT CAST(route_id AS VARCHAR) AS route_id, CAST(date AS DATE) AS date, vehicle_id
               FROM read_parquet({passages_glob(days)})),
         va AS (SELECT DISTINCT CAST(date AS DATE) AS date, vehicle_id FROM read_parquet({passages_glob(days)}))
    SELECT tk.route_id, CAST(tk.date AS DATE) AS date, count(*) AS veh_tickets,
           avg((v.vehicle_id IS NOT NULL)::INT) AS cov_route,
           avg((va.vehicle_id IS NOT NULL)::INT) AS cov_any_route
    FROM tk LEFT JOIN v ON tk.route_id = v.route_id AND CAST(tk.date AS DATE) = v.date AND tk.vehicle_number = v.vehicle_id
            LEFT JOIN va ON CAST(tk.date AS DATE) = va.date AND tk.vehicle_number = va.vehicle_id
    GROUP BY ALL""").df()
cov["date"] = pd.to_datetime(cov.date).dt.date
cov.to_parquet(OUT / "gps_coverage.parquet", index=False)
cov["wk"] = np.where(cov.date.isin(set(C.TEST_DAYS)), "te", "tr")
w = cov.groupby(["route_id", "wk"]).apply(lambda x: pd.Series({"n": x.veh_tickets.sum(),
        "cov": np.average(x.cov_route, weights=x.veh_tickets), "cov_any": np.average(x.cov_any_route, weights=x.veh_tickets)})).unstack("wk")
w.columns = [f"{a}_{b}" for a, b in w.columns]
print("全体の捕捉率（券の重み）: 路線一致", round(np.average(cov.cov_route, weights=cov.veh_tickets), 3),
      " どの路線でも", round(np.average(cov.cov_any_route, weights=cov.veh_tickets), 3))
print(w.loc[[r for r in ["355", "354", "1924", "2716", "1276", "2224", "786", "1273"] if r in w.index]].round(2).to_string())
big = w[(w.n_tr >= 300) & (w.n_te >= 100)]
print("路線ごとの捕捉率の分布（学習期間）:", big.cov_tr.quantile([.1, .25, .5, .75, .9]).round(2).to_dict())
print("学習→検証の捕捉率の変化 |差| の中央値:", round(float((big.cov_te - big.cov_tr).abs().median()), 3))
