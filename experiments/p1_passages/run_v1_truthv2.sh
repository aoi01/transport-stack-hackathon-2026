#!/bin/bash
# 比較用: 今のモデル（60m の通過で作ったもの、data/processed）を、補間した通過で作った正解で測り直す（docs 17章）。
set -e
cd "$(dirname "$0")/../.."
export PYTHONPATH=src TSH_PASSAGES=stop_passages TSH_TRUTH_PASSAGES=stop_passages_v2 TSH_PROCESSED=data/processed \
       TSH_RESULTS=experiments/p1_passages/results_v1_truthv2
mkdir -p "$TSH_RESULTS"
python -m tsh.validate_p1
python -m tsh.validate_journeys
python -m tsh.validate_journeys live
python -m tsh.validate_journeys arrive
