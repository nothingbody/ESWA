#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONUNBUFFERED=1

cd "$(dirname "$0")/.."
PY=${PYTHON:-.venv/bin/python}
SOLOMON_DIR=${SOLOMON_DIR:-data/dimacs_vrptw/raw/VRPTWController-master/Instances/Solomon}
HOMBERGER_DIR=${HOMBERGER_DIR:-data/homberger/selected_200_400}
STATUS_FILE=${STATUS_FILE:-results/logs/rerun_post_route_elim.status}

mkdir -p results/logs results/tables results/figures
printf RUNNING > "$STATUS_FILE"

step() {
  echo
  echo "===== $(date -Is) $* ====="
}

finish_failed() {
  rc=$?
  echo "===== $(date -Is) FAILED rc=$rc ====="
  echo FAILED > "$STATUS_FILE"
  exit "$rc"
}
trap finish_failed ERR

step "verify bounded route elimination"
"$PY" -m compileall -q src experiments tests
"$PY" -m pytest

step "Homberger 200/400 selected"
"$PY" experiments/run_solomon_batch.py "$HOMBERGER_DIR" --output results/tables/homberger_200_400_selected.csv --workers 12 --skip-relocate --skip-two-opt
"$PY" experiments/summarize_results.py results/tables/homberger_200_400_selected.csv --output results/tables/homberger_200_400_summary.csv
"$PY" experiments/compute_gap.py results/tables/homberger_200_400_selected.csv data/bks/homberger_200_400_selected_bks.csv --output results/tables/homberger_200_400_gap.csv
"$PY" experiments/summarize_gap.py results/tables/homberger_200_400_gap.csv --output results/tables/homberger_200_400_gap_summary.csv
cat results/tables/homberger_200_400_summary.csv
cat results/tables/homberger_200_400_gap_summary.csv

step "Solomon ablation"
"$PY" experiments/run_ablation.py "$SOLOMON_DIR" --instances C101.txt R101.txt RC101.txt --output results/tables/solomon_ablation_selected.csv --workers 3
"$PY" experiments/summarize_ablation.py results/tables/solomon_ablation_selected.csv --output results/tables/solomon_ablation_summary.csv
cat results/tables/solomon_ablation_summary.csv

step "figures and manuscript"
"$PY" experiments/plot_stage_results.py
"$PY" experiments/generate_results_report.py
"$PY" experiments/generate_manuscript.py

step "final checks"
"$PY" -m pytest
python3 - <<'PY'
from pathlib import Path

for path in [Path("docs/results_and_discussion_draft.md"), Path("docs/FTV_Logistics_SCI_Manuscript_Draft.md")]:
    text = path.read_text(encoding="utf-8")
    bad = [token for token in ("{table", "TODO", "nan", "None") if token in text]
    if bad:
        raise SystemExit(f"{path}: unresolved tokens {bad}")
    print(path, len(text.splitlines()), "lines")
PY
find results/tables -maxdepth 2 -type f -name "*.csv" | wc -l

echo COMPLETED > "$STATUS_FILE"
echo "===== $(date -Is) COMPLETED ====="
