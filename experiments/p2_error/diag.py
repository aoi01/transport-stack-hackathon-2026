"""今の推定（学習期間の 人数/便数）を作り直して検証の値と合うか確かめ、誤差の内訳を見る。"""
from base import *  # noqa: F401,F403
sys.stdout.reconfigure(encoding="utf-8")
d, grid = train_daily()
a = cells_from_daily(d, grid)
old = pd.read_parquet(C.PROCESSED / "train" / "crowding.parquet", columns=K + ["sample_per_trip", "trips_total", "pax"])
chk = old.merge(a, on=K, how="left")
print("再現: 便数の一致", np.mean(np.isclose(chk.trips_total, chk["T"])), " 人数/便の一致", np.mean(np.isclose(chk.sample_per_trip, chk.pax_y / chk["T"])))
print(chk[~np.isclose(chk.trips_total, chk["T"])].head())
