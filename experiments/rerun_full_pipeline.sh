#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONUNBUFFERED=1

cd "$(dirname "$0")/.."
PY=${PYTHON:-.venv/bin/python}
SOLOMON_DIR=${SOLOMON_DIR:-data/dimacs_vrptw/raw/VRPTWController-master/Instances/Solomon}
LILIM_DIR=${LILIM_DIR:-data/li_lim/hexaly/raw/pdptw/instances}
HOMBERGER_DIR=${HOMBERGER_DIR:-data/homberger/selected_200_400}
STATUS_FILE=${STATUS_FILE:-results/logs/rerun_full_pipeline.status}
ADVANCED_SEEDS=${ADVANCED_SEEDS:-"42 11 23"}
PAIR_ALNS_SEEDS=${PAIR_ALNS_SEEDS:-"42 11 23"}

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

step "verify code"
"$PY" -m compileall -q src experiments tests
"$PY" -m pytest
"$PY" experiments/write_bks_tables.py

step "Solomon stage-1 full"
"$PY" experiments/run_solomon_batch.py "$SOLOMON_DIR" --output results/tables/solomon_stage1_all.csv --workers 24
"$PY" experiments/summarize_results.py results/tables/solomon_stage1_all.csv --output results/tables/solomon_stage1_summary.csv
"$PY" experiments/compute_gap.py results/tables/solomon_stage1_all.csv data/bks/solomon_100_bks.csv --output results/tables/solomon_stage1_gap.csv
"$PY" experiments/summarize_gap.py results/tables/solomon_stage1_gap.csv --output results/tables/solomon_stage1_gap_summary.csv
cat results/tables/solomon_stage1_summary.csv
cat results/tables/solomon_stage1_gap_summary.csv

step "Solomon Basic ALNS full"
"$PY" experiments/run_solomon_alns.py "$SOLOMON_DIR" --iterations 400 --time-limit 15 --workers 24 --output results/tables/solomon_alns_all.csv
"$PY" experiments/compute_gap.py results/tables/solomon_alns_all.csv data/bks/solomon_100_bks.csv --output results/tables/solomon_alns_all_gap.csv
"$PY" experiments/summarize_gap.py results/tables/solomon_alns_all_gap.csv --output results/tables/solomon_alns_all_gap_summary.csv
cat results/tables/solomon_alns_all_gap_summary.csv

step "Advanced ALNS parameter sweep"
"$PY" experiments/run_alns_param_sweep.py "$SOLOMON_DIR" --time-limit 20 --workers 9 --output results/tables/advanced_alns_param_sweep.csv
"$PY" experiments/summarize_param_sweep.py results/tables/advanced_alns_param_sweep.csv --output results/tables/advanced_alns_param_sweep_summary.csv
cat results/tables/advanced_alns_param_sweep_summary.csv
ADVANCED_CONFIG=$("$PY" - <<'PY'
import csv
from pathlib import Path

rows = list(csv.DictReader(Path("results/tables/advanced_alns_param_sweep_summary.csv").open(newline="", encoding="utf-8")))
best = min(rows, key=lambda row: (float(row["avg_vehicles"]), float(row["avg_distance"])))
print(best["config"])
PY
)
echo "selected advanced config: ${ADVANCED_CONFIG}"

step "Advanced ALNS full"
"$PY" experiments/run_advanced_alns_all.py "$SOLOMON_DIR" --config "$ADVANCED_CONFIG" --seeds $ADVANCED_SEEDS --time-limit 25 --workers 24 --output results/tables/advanced_alns_all.csv
"$PY" experiments/compute_gap.py results/tables/advanced_alns_all.csv data/bks/solomon_100_bks.csv --output results/tables/advanced_alns_all_gap.csv
"$PY" experiments/summarize_gap.py results/tables/advanced_alns_all_gap.csv --output results/tables/advanced_alns_all_gap_summary.csv
cat results/tables/advanced_alns_all_gap_summary.csv

step "Li & Lim PDPTW full with pair ALNS"
"$PY" experiments/run_li_lim_batch.py "$LILIM_DIR" --output results/tables/li_lim_stage1_all.csv --workers 24 --pair-seeds $PAIR_ALNS_SEEDS
"$PY" experiments/summarize_results.py results/tables/li_lim_stage1_all.csv --output results/tables/li_lim_stage1_all_summary.csv
"$PY" experiments/compute_gap.py results/tables/li_lim_stage1_all.csv data/bks/li_lim_100_bks.csv --output results/tables/li_lim_stage1_gap.csv
"$PY" experiments/summarize_gap.py results/tables/li_lim_stage1_gap.csv --output results/tables/li_lim_stage1_gap_summary.csv
cat results/tables/li_lim_stage1_all_summary.csv
cat results/tables/li_lim_stage1_gap_summary.csv

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
