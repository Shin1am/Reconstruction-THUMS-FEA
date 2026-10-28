#!/usr/bin/env bash
# Re-run the frozen baseline notebook end-to-end without touching any existing output.
# Usage: bash run_baseline.sh
set -euo pipefail

ROOT="/Volumes/Extreme SSD/2d_3d_regis dataset/New_version"
HERE="$ROOT/Document/Day1_Baseline"
PY=/opt/homebrew/anaconda3/bin/python3
RUN="$HERE/rerun"

mkdir -p "$RUN/outputs"
"$PY" "$HERE/make_scratch_notebook.py" \
  "$HERE/frozen/CPD_TPS_Skin_Only_Pipeline_v2.ipynb" \
  "$RUN/scratch_input.ipynb" "$ROOT" "$RUN/outputs"

cd "$RUN"
/usr/bin/time -p "$PY" -m jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.kernel_name=python3 \
  --ExecutePreprocessor.timeout=1800 \
  --output scratch_executed.ipynb scratch_input.ipynb
