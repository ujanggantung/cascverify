#!/usr/bin/env bash
# CascToolBench — full experiment driver (checkpointed, resumable).
# Usage:  bash run_all.sh [model] [seeds]
set -u
cd "$(dirname "$0")"

MODEL="${1:-tokenharbor}"
SEEDS="${2:-1,2,3}"
PY="${PY:-python}"

echo "=============================================="
echo " CascToolBench full run"
echo " model=$MODEL seeds=$SEEDS"
echo "=============================================="

# T1 (10 tasks) - basic single hallucination
echo; echo ">>> TIER 1"; $PY run_benchmark.py --tasks T1 --model "$MODEL" --seeds "$SEEDS" --timeout 200

# T2 (2 tasks) - standard contamination
echo; echo ">>> TIER 2"; $PY run_benchmark.py --tasks T2 --model "$MODEL" --seeds "$SEEDS" --timeout 200

# T3 (10 tasks) - complex cascade
echo; echo ">>> TIER 3"; $PY run_benchmark.py --tasks T3 --model "$MODEL" --seeds "$SEEDS" --timeout 200

# T4 (5 tasks) - long horizon, poison seed
echo; echo ">>> TIER 4"; $PY run_benchmark.py --tasks T4 --model "$MODEL" --seeds "$SEEDS" --timeout 200

# P5 (5 tasks) - PERSISTENT failure (fabrication trigger per Sethi et al. 2026)
echo; echo ">>> TIER P5 (persistent failure)"; $PY run_benchmark.py --tasks P5 --model "$MODEL" --seeds "$SEEDS" --timeout 200

echo; echo "=== ALL DONE ==="
echo "Results: results/"
ls -1 results/*.json 2>/dev/null | wc -l | xargs echo "checkpoint files:"
echo
echo "Aggregate:"
cat results/summary_table.txt 2>/dev/null || echo "(no summary yet)"