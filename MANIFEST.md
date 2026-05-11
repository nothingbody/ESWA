# Public Artifact Manifest

## Tracked

- `src/`: routing task abstraction, parser, verifier, construction heuristics,
  repair, route merge, route elimination, ALNS, pair-aware ALNS, and metrics.
- `experiments/`: reproducible experiment drivers, summary scripts,
  statistical tests, runtime analysis, and figure generation.
- `tests/`: embedded-sample tests for VRPTW and PDPTW behavior.
- `results/tables/`: processed CSV tables used for manuscript tables and
  statistical analysis.
- `results/figures/`: generated result plots.
- `docs/ESWA_Final_Anonymized_Manuscript.md`: anonymized manuscript source.
- `docs/ESWA_Highlights.md`, `docs/ESWA_Data_AI_Declarations.md`, and
  `docs/ESWA_Figure_Captions.md`: non-identifying submission support files.
- `docs/eswa_figures/`: final manuscript figures.

## Intentionally Not Tracked

- raw benchmark data under `data/`;
- runtime logs and status files under `results/logs/`;
- Python cache directories;
- DOCX exports that may contain local document metadata;
- title page and cover letter containing author identity;
- local revision plans and remote execution notes.

## Sensitive-Content Policy

Before pushing, run a staged scan for local paths, remote server markers,
credentials, author identity, and email addresses. Keep the concrete pattern in
the local shell history only, not in this public manifest:

```bash
git grep --cached -n -E "<local-sensitive-patterns>"
```

The command should return no matches for files selected for publication.
