# Changelog

All notable changes to Phytolaeno are documented here.

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
