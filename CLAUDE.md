# Phytolaeno — Project Notes

Plant genome annotation management system: directory scaffolding, manifest
generation, stats collection, and a FastAPI + PostgreSQL web portal for
browsing and comparing assemblies and annotations.

**Current version:** unversioned (versioning not yet applied)

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
- `matplotlib` — server-side plot generation

## Blueprint compliance status

The standalone scripts **predate the shared blueprint** and do not yet fully
follow it. Priority gaps to address when making changes:

- [ ] Add `VERSION` strings to all scripts in `scripts/`
- [ ] Add run log (date/user/server/command) to long-running scripts
- [ ] Add `CHANGELOG.md`
- [ ] Add version badge to README

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
