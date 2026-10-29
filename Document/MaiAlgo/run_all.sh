#!/bin/bash
# Usage: ./run_all.sh <case> <name> [run_exp flags...]   -> run, interior eval, Jacobian check for one experiment
set -e
PY=${PY:-/c/Users/Acer/AppData/Local/Temp/rv/Scripts/python.exe}
export PYTHONUTF8=1
cd "$(dirname "$0")"
CASE=$1; NAME=$2; shift 2
OUT="$PWD/out_${CASE}_${NAME}"
$PY run_exp.py "$CASE" "$NAME" "$@" > "log_${CASE}_${NAME}.txt" 2>&1
$PY eval_exp.py "$OUT" "$CASE" >> "log_${CASE}_${NAME}.txt" 2>&1
JAC_OUT="$OUT/jacobian" JAC_REGISTERED="$OUT/Head_V6_registered.vtu" $PY jacobian_diagnostic.py >> "log_${CASE}_${NAME}.txt" 2>&1
echo "finished $CASE $NAME" >> "log_${CASE}_${NAME}.txt"
