# Phytolaeno

**Phytolaeno** is a web-based portal for browsing, comparing, and managing plant genome assembly and annotation data. The name blends *Phyto-* (plant) with *Celaeno*, the mythical library from the Cthulhu Mythos — consistent with the lab's naming convention (see also: ShoggoTEh).

---

## Features

- Browse hundreds of plant species, their genome assemblies, and associated annotations
- Filter species by name, taxonomic family, or lineage
- Detailed views for each assembly, gene model annotation, and repeat element annotation
- Upload new annotations (gene models and repeat elements) through a web form
- Interactive plots: BUSCO distributions, gene model statistics, PSAURON scores, and repeat composition
- Excel import script to bulk-load existing benchmark data

---

## Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Templates | Jinja2 |
| UI | Bootstrap 5.3 + Bootstrap Icons |
| Plots | Plotly.js (client-side) + Plotly Python (server-side) |

---

## Database Schema

Five relational tables model the hierarchy of plant genomic data:

```
Species
  └── Assembly
        ├── RepeatAnnotation  ← EarlGrey, Barrnap, tRNAScan-SE, …
        │     └── AnnotationProtocol
        └── GeneModelAnnotation  ← MAKER, BRAKER, …
              └── AnnotationProtocol
```

- **Species** — name, NCBI TaxID, family, lineage
- **Assembly** — version, source, size, status, assembly-level BUSCO (viridiplantae + embryophyta)
- **AnnotationProtocol** — tool, version, commands, notes (shared by both annotation types)
- **RepeatAnnotation** — total repeat %, raw output, per-class breakdown (JSON)
- **GeneModelAnnotation** — gene/transcript/CDS/exon counts, length statistics, quality flags, BUSCO, OMArk, PSAURON, DETENGA, protein homology, GAQET, F1 scores

---

## Project Layout

```
phytolaeno/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # SQLAlchemy engine and session
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── utils.py             # BUSCO/EarlGrey string parsers, safe converters
│   ├── routers/
│   │   ├── species.py       # GET /, /species, /species/{id}
│   │   ├── assemblies.py    # GET /assemblies/{id}
│   │   ├── annotations.py   # GET /annotations/gm/{id}, /annotations/re/{id}
│   │   ├── upload.py        # GET /upload, POST /upload/gm, POST /upload/re
│   │   └── plots.py         # GET /plots
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── species_list.html
│       ├── species_detail.html
│       ├── assembly_detail.html
│       ├── gm_annotation_detail.html
│       ├── re_annotation_detail.html
│       ├── upload.html
│       └── plots.html
├── scripts/
│   └── import_excel.py      # Bulk import from Excel benchmark table
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Installation

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd phytolaeno
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the database

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL, e.g.:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/phytolaeno
```

Create the database in PostgreSQL:

```sql
CREATE DATABASE phytolaeno;
```

### 3. Start the server

```bash
uvicorn app.main:main --reload
```

The app creates all tables automatically on startup via `Base.metadata.create_all()`. Open your browser at `http://localhost:8000`.

---

## Bulk Import

To load data from the Excel benchmark table (`PlantAnnotationBenchmark2025.xlsx`):

```bash
python scripts/import_excel.py PlantAnnotationBenchmark2025.xlsx
```

The script expects Sheet1 with one row per gene model annotation. It groups rows by `Assembly_Version` and:

- Creates one **Species** record per unique species name
- Creates one **Assembly** record per unique assembly version
- Creates three **RepeatAnnotation** records per assembly: EarlGrey, Barrnap, tRNAScan-SE
- Creates one **GeneModelAnnotation** per row (with auto-detected protocol from `Annotation_Methodology`)

Re-running the script is safe — existing species and assemblies are looked up by name/version and reused.

---

## URL Map

| URL | Description |
|---|---|
| `/` | Home — summary stats and navigation cards |
| `/species` | Paginated species list with search/filter |
| `/species/{id}` | Species detail with all assemblies |
| `/assemblies/{id}` | Assembly detail with GM and RE annotation tables |
| `/annotations/gm/{id}` | Full gene model annotation detail |
| `/annotations/re/{id}` | Repeat annotation detail with breakdown chart |
| `/upload` | Tabbed form to add new annotations |
| `/plots` | Interactive analysis plots |

---

## Analysis Plots

The `/plots` page renders five Plotly figures:

1. **BUSCO completeness by tool** — box plot of viridiplantae BUSCO completeness per annotation tool
2. **Gene models by tool** — box plot of gene model counts per tool
3. **Mean intron vs mean exon length** — scatter plot coloured by tool
4. **PSAURON score by tool** — box plot of annotation quality scores
5. **Repeat content by species** — stacked bar chart of EarlGrey repeat classes (DNA, LTR, LINE, SINE, RC, Other)

---

## Dependencies

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
alembic
jinja2
python-multipart
python-dotenv
pandas
openpyxl
plotly
```

---

## License

To be defined.

---

*Phytolaeno — Plant Genome Annotation Archive. Named after the Library of Celaeno.*
