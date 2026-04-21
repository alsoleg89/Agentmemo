#!/usr/bin/env bash
# noise_floor.sh — Run conv0 three times with identical settings and compute
# per-category stddev. Writes data/baselines/noise_floor_2conv.json.
#
# Usage:
#   cd aiknotbench
#   ./scripts/noise_floor.sh [--top-k 60] [--convs 0,1]
#
# Requires OPENAI_API_KEY to be set (or DEFAULT_JUDGE_MODEL / DEFAULT_ANSWER_MODEL
# pointing to a local Ollama instance that's running).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BENCH_ROOT"

TOP_K="${1:-60}"
CONVS="${2:-0,1}"
TS="$(date +%Y%m%d-%H%M%S)"

echo ""
echo "================================================================="
echo "  noise_floor.sh  3 replicates  convs=${CONVS}  top_k=${TOP_K}"
echo "================================================================="
echo ""

RUN_IDS=()

for i in 1 2 3; do
  RUN_ID="noise-${TS}-rep${i}"
  echo "  --- replicate ${i}/3 : run=${RUN_ID} ---"
  npx tsx src/index.ts run -r "$RUN_ID" --convs "$CONVS" --top-k "$TOP_K" --allow-drift --force
  RUN_IDS+=("$RUN_ID")
  echo ""
done

echo "  Computing stddev from ${#RUN_IDS[@]} replicates..."
python3 scripts/compare_runs.py --noise "${RUN_IDS[@]}"

echo ""
echo "  Noise-floor written to data/baselines/noise_floor_2conv.json"
echo ""
echo "  You can now update bench_gate.sh thresholds accordingly."
echo ""

# Print the stddev as a quick summary
if command -v jq &>/dev/null; then
  echo "  Summary:"
  jq '{ stddev_cat1_4, stddev_per_cat, replicates }' data/baselines/noise_floor_2conv.json
fi
