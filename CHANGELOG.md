# Changelog

All notable changes to Phytolaeno are documented here.

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
