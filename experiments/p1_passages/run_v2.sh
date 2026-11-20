#!/bin/bash
# 補間した通過（tsh.passages_v2）でモデルを作り直し、検証する（docs 17章）。
# 元のモデル（data/processed）と結果（results）は上書きしない。
set -e
cd "$(dirname "$0")/../.."
export PYTHONPATH=src TSH_PASSAGES=stop_passages_v2 TSH_PROCESSED=data/processed_v2 TSH_RESULTS=experiments/p1_passages/results_v2
mkdir -p "$TSH_RESULTS"
python -m tsh.traveltime train
python -m tsh.traveltime all
python -m tsh.validate_p1
python -m tsh.seg_ml
python -m tsh.validate_journeys livecal
python -m tsh.live_excess
python -m tsh.validate_journeys
python -m tsh.validate_journeys live
python -m tsh.validate_journeys arrive
