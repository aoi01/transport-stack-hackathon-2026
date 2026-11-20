#!/bin/bash
# 前もって計画の較正（docs 17章）: 較正の週で外れ方を集める → 較正を作る → 較正の週の内側で確認 → 検証週で測る。
set -e
cd "$(dirname "$0")/../.."
export PYTHONPATH=src TSH_PASSAGES=stop_passages_v2 TSH_PROCESSED=data/processed_v2 TSH_RESULTS=experiments/p1_passages/results_v2
python -m tsh.validate_journeys plancal
python -m tsh.plan_calib
TSH_PLAN_CALIB=1 TSH_TAG=_calcheck python -m tsh.validate_journeys plancal
TSH_PLAN_CALIB=1 python -m tsh.validate_journeys
python -m tsh.validate_journeys livecal
python -m tsh.live_excess
TSH_PLAN_CALIB=1 python -m tsh.validate_journeys live
