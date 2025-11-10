#!/usr/bin/env bash
# run_parallel.sh
# Usage: ./run_parallel.sh 1 2000 20 4
# Arguments: start end step n_jobs
# Example: ./run_parallel.sh 1 2000 20 4

set -euo pipefail

START=${1:-1}
END=${2:-2000}
STEP=${3:-20}
JOBS=${4:-4}

# Make sure GNU parallel is installed
if ! command -v parallel &>/dev/null; then
  echo "Error: GNU parallel not found. Install it with: brew install parallel"
  exit 1
fi

# Build the list of ranges and run jobs
seq "$START" "$STEP" "$((END - 1))" | \
  parallel -j "$JOBS" '
    next=$(( {} + '"$STEP"' ))
    echo "Running range {} to $next"
    python3 fetch_cmip.py {} "$next"
  '
echo "All jobs completed."