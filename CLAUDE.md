# Phytolaeno — Project Notes

Plant genome annotation management system: directory scaffolding, manifest
generation, stats collection, and a FastAPI + PostgreSQL web portal for
browsing and comparing assemblies and annotations.

**Current version:** v0.3.0 (2026-11-06)

This project follows the shared coding blueprint at `../CLAUDE.md` where
applicable. Note that the web application (`app/`) follows FastAPI conventions
rather than the CLI pipeline pattern — apply blueprint standards to the
standalone scripts in `scripts/` and note the web-specific deviations below.

---

## Components

| Component | Purpose |
|---|---|
| `scripts/generate_species_dir.py` | Scaffold standardised directory tree per species/assembly |
| `scripts/generate_manifest.py` | Walk directory tree, auto-discover outputs, write manifest TSV |
| `scripts/collect_annotation_stats.py` | Parse GAQET, QUAST, BUSCO, EarlGrey, barrnap, tRNAscan into combined TSV |
| `scripts/import_excel.py` | Bulk-load annotation stats from Excel into PostgreSQL |
| `app/` | FastAPI web portal (routes: species, assemblies, annotations, plots, upload) |
| `scripts/migrate_to_v2.py` | One-off database migration script |

## External dependencies

- **PostgreSQL** — database backend; connection string via environment variable
- `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2` — web app stack
- `pandas`, `openpyxl` — stats parsing and Excel import
- `plotly` — server-side plot generation
- Dependencies pinned in `requirements.txt`; keep SQLAlchemy on 2.0.x
  (2.1 defaults to psycopg v3) unless the driver is switched.
- Tests: `python -m pytest -q tests` (SQLite, no PostgreSQL needed).
- Demo: `python scripts/demo.py` — real data only (3 species, 5 assemblies, 41
  annotations) from `demo/data/`, regenerated with `scripts/build_demo_data.py`
  from the benchmark spreadsheet + collected QUAST metrics. Descriptions/links in
  `demo/data/descriptions.tsv` (user-reviewed); Zenodo URLs go in
  `demo/data/downloads.tsv`. GAS/axes in `app/metrics.py` must stay in sync with
  GAQET2 `gaqet_plot.py` (revision branch). Codespaces config in `.devcontainer/`.
  Screenshots in `docs/screenshots/` are taken from the demo with headless Chrome
  (kill Chrome after each file appears; it does not exit by itself).

## Blueprint compliance status

The standalone scripts **predate the shared blueprint** and do not yet fully
follow it. Priority gaps to address when making changes:

- [ ] Add `VERSION` strings to all scripts in `scripts/`
- [ ] Add run log (date/user/server/command) to long-running scripts
- [x] Add `CHANGELOG.md` (v0.1.1)
- [x] Add version badge to README (v0.1.1)
- [ ] Authentication for `/upload/*` before any public deployment
- [ ] `import_excel.py` connects to the DB at import time (even for `--help`)

## Web app conventions (deviations from CLI blueprint)

- The `app/` directory follows FastAPI project structure — do not apply
  the `results/workdir/logs/` layout or checkpoint logic there.
- Database connection is managed via SQLAlchemy sessions in `app/database.py`.
- Routes are organised by resource type under `app/routers/`.
- Schemas (Pydantic models) live in `app/schemas.py`; ORM models in `app/models.py`.

---

## FAIR compliance status

- [x] `LICENSE` — MIT, added 2026-06-24
- [x] `CITATION.cff` — author, ORCID, version, keywords, repository URL
- [ ] Zenodo DOI — mint after first public release; add `doi:` field to `CITATION.cff`
- [ ] bio.tools registration — register after first public release
