"""今の区間 LightGBM（60m の通過で学習、data/processed/seg_ml）を、補間した通過で作った検証の区間で測る（docs 17章）。
TSH_PROCESSED=data/processed TSH_RESULTS=experiments/p1_passages/results_v1_truthv2 python experiments/p1_passages/segml_old_on_v2.py"""
import sys
import lightgbm as lgb
import numpy as np
sys.path.insert(0, "src")
from tsh import common as C
from tsh.seg_ml import FEATS, OUT, con_with_base, build_features, test_segments
from tsh.validate_p1 import metrics
sys.stdout.reconfigure(encoding="utf-8")
con = C.connect()
con_with_base(con)
test_segments(con)
te = build_features(con, "seg_test", "ot", "test_feats_v2truth")
no_rec = [f for f in FEATS if not (f.startswith("rec_") or f.startswith("up_") or f.startswith("route_") or f.startswith("city_"))]
for tag, feats in (("hist", no_rec), ("live", FEATS)):
    p = te.H0.to_numpy() * np.exp(lgb.Booster(model_file=str(OUT / f"lgb_seg_{tag}_q50.txt")).predict(te[feats]))
    q85 = te.H0.to_numpy() * np.exp(lgb.Booster(model_file=str(OUT / f"lgb_seg_{tag}_q85.txt")).predict(te[feats]))
    print(tag, metrics(te.actual_s, p), "85%点以内", round(float((te.actual_s <= q85).mean() * 100), 1))
