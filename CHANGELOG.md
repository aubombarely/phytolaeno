# Changelog

All notable changes to Phytolaeno are documented here.

## [v0.3.0] — 2026-11-06

### Added
- All-real demo: *Arabidopsis thaliana*, *Oryza sativa* and *Cucumis sativus*
  (5 assemblies, 41 annotations) from the KATULU / GAQET benchmark, extracted
  by `scripts/build_demo_data.py` into `demo/data/`.
- Species pages follow Species → Assemblies → Annotations: descriptions and
  source links, NCBI Taxonomy / GoaT / Wikispecies links, an assembly table
  with QUAST metrics (type, size, sequences, N90/L90, N's per 100 kbp,
  sequences > 10 kb, plastid and mitochondrion), and per-assembly annotation
  tables ranked by the Global Annotation Score.
- `app/metrics.py`: GAQET radar axes and Global Annotation Score (GAS),
  following GAQET2's `gaqet_plot.py` (revision branch), with per-analysis
  weights; insight tags (*No UTRs* when < 1% of transcripts have a UTR;
  *1 isoform/gene*; a micro-exon tag that stays hidden until data exist).
- Plots: per-species selectors (assembly, annotations, metric), annotation dot
  plot, per-assembly tool comparison, interactive GAQET radar with GAS weight
  sliders, repeat content; new **Compare species** page (`/compare`).
- New nullable columns for assembly metrics, descriptions, links, Zenodo URL,
  micro-exon percentage and GAS (`import_excel.py` unchanged).
- Tests for data extraction, metrics, pages and plots (47 in total).

### Changed
- The 11 synthetic species and the "synthetic data" banner are removed.

## [v0.2.0] — 2026-11-06

### Added
- One-command demo (`scripts/demo.py`). It builds a SQLite database and starts
  the portal. *Arabidopsis thaliana* uses real GAQET metrics for 17 annotations
  (`demo/data/Athaliana_GAQET_benchmark.tsv`); 11 other species are synthetic.
  Every page carries a banner saying which data are real.
- GitHub Codespaces configuration (`.devcontainer/`) to run the demo in the
  browser without installing anything, plus an "Open in Codespaces" badge.
- Screenshots in the README (`docs/screenshots/`).
- Test of the demo builder (`tests/test_demo.py`).

### Fixed
- The Plots page drew nothing: the template called `JSON.parse` on figures that
  were already embedded as objects (bug present since the initial commit).
- The Plots page now loads Plotly.js 4.1.1, matching the pinned Python Plotly 7.
- Assembly names on the species page were white text on a light header and
  could not be read.

## [v0.1.1] — 2026-11-06

### Added
- Test suite (`tests/`): smoke tests that render every portal page and store a
  gene-model annotation through the upload form, plus unit tests for the
  BUSCO/EarlGrey parsers. Runs against a throw-away SQLite database, no
  PostgreSQL needed.
- `requirements-dev.txt` (pytest, httpx).
- README: version/python/platform/license badges, project status section,
  testing instructions.

### Fixed
- Fresh clones failed at startup because `app/static/` (mounted by
  `app/main.py`) was an empty, untracked directory; it is now tracked.
- Installing without version pins pulled SQLAlchemy 2.1, whose default
  PostgreSQL driver is psycopg v3 (not installed), so the portal could not
  connect to PostgreSQL.
- README license section said "To be defined"; the project is MIT-licensed.
- `CITATION.cff` abstract gave a wrong name etymology.

### Changed
- All dependencies pinned to exact versions in `requirements.txt`.

## [v0.1.0] — 2026-06-24

### Added
- Directory scaffolding (`generate_species_dir.py`), manifest generation
  (`generate_manifest.py`), stats collection (`collect_annotation_stats.py`),
  Excel import, and the FastAPI + PostgreSQL web portal.
- MIT `LICENSE` and `CITATION.cff`.
