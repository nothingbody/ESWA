# FTV Logistics Decision Framework

This repository contains the code and reproducibility artifacts for a
knowledge-driven fast-slow decision support framework for auditable logistics
routing with time-window and pickup-delivery constraints.

The implementation is intentionally CPU-oriented. It separates:

- fast candidate route construction;
- process-level constraint verification;
- typed diagnostic feedback;
- reflection-guided repair, route merge, route elimination, and ALNS;
- verified multi-candidate route selection.

The repository does not implement an LLM-based vehicle routing solver. The
fast-slow terminology describes the implemented routing pipeline: lightweight
candidate generation followed by slower verification, repair, improvement, and
selection.

## Repository Layout

```text
src/                         Core routing, verification, and optimization code
experiments/                 Experiment, summary, statistics, and export scripts
tests/                       Unit tests for parsers, verifiers, repair, and ALNS
results/tables/              Processed CSV result tables used by the manuscript
results/figures/             Generated result figures
docs/                        Anonymized manuscript materials and final figures
```

Author-identifying submission files, remote server notes, runtime logs, local
benchmark data, Python caches, and DOCX exports are excluded from version
control.

## Installation

Python 3.11 or 3.12 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Unix-like environments:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Quick Verification

```bash
python -m pytest -q
python experiments/statistical_tests.py
python experiments/fast_slow_runtime_analysis.py
```

The test suite uses embedded miniature VRPTW and PDPTW instances, so it does
not require downloading the full benchmark datasets.

## Benchmark Data

Raw benchmark instances are not vendored in this repository. To rerun the full
experiments, place public benchmark files under:

```text
data/dimacs_vrptw/raw/VRPTWController-master/Instances/Solomon/
data/li_lim/hexaly/raw/pdptw/instances/
data/homberger/selected_200_400/
```

The processed tables under `results/tables/` are included so that manuscript
statistics, figures, and significance tests can be regenerated without rerunning
all solver experiments.

## Main Commands

Generate benchmark BKS tables:

```bash
python experiments/write_bks_tables.py
```

Run the Solomon VRPTW stage-1 pipeline for one instance:

```bash
python experiments/run_solomon.py path/to/C101.txt --output results/tables/C101_stage1.csv
```

Run the Li & Lim PDPTW pipeline for one instance:

```bash
python experiments/run_li_lim.py path/to/lc101.txt --output results/tables/lc101_pdptw.csv
```

Recompute Wilcoxon paired tests:

```bash
python experiments/statistical_tests.py --output results/tables/eswa_statistical_tests.csv
```

Recompute fast-slow runtime summaries:

```bash
python experiments/fast_slow_runtime_analysis.py
```

Regenerate ESWA figures:

```bash
python experiments/create_eswa_figures.py
```

The OR-Tools comparison is optional:

```bash
python -m pip install ortools
python experiments/run_ortools_solomon.py path/to/Solomon --time-limit 30 --workers 1
```

OR-Tools is treated as an engineering reference, not as the main paired
statistical baseline, because paired significance testing requires the same
instances to be solved feasibly by both compared methods.

## Manuscript Artifacts

The anonymized manuscript source is available at:

```text
docs/ESWA_Final_Anonymized_Manuscript.md
```

Final figures are available under:

```text
docs/eswa_figures/
```

Title page, cover letter, and author-identifying files are intentionally kept
outside this repository boundary.
