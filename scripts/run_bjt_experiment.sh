#!/usr/bin/env bash
# Run in the existing cloud checkout and retain evidence in a fresh directory.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
source .local/env.sh
if (($# > 1)); then
    printf 'Usage: %s [fresh-output-directory]\n' "$0" >&2
    exit 2
fi
if (($# == 1)); then
    EXPERIMENT_DIR="$1"
    mkdir -p -- "$EXPERIMENT_DIR"
    EXPERIMENT_DIR="$(cd -- "$EXPERIMENT_DIR" && pwd)"
else
    mkdir -p results
    EXPERIMENT_DIR="$(mktemp -d "$PROJECT_DIR/results/bjt_XXXXXX")"
fi
python scripts/test_ngspice_models.py --output-dir "$EXPERIMENT_DIR/code_models"
python scripts/simulate_bjt_resistance.py --output-dir "$EXPERIMENT_DIR"
python scripts/verify_bjt_substrate.py --output-dir "$EXPERIMENT_DIR/substrate_diagnostic"
python scripts/report_bjt_resistance.py --output-dir "$EXPERIMENT_DIR" \
    --model-dir "$EXPERIMENT_DIR/code_models"
printf '\nExperiment report: %s/report.md\n' "$EXPERIMENT_DIR"
