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
│   ├── import_excel.py           # Bulk import from Excel benchmark table
│   └── collect_annotation_stats.py  # Automated data collection from analysis outputs
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

## Automated Data Collection

`collect_annotation_stats.py` collects metrics from analysis pipeline outputs (GAQET, QUAST, BUSCO, EarlGrey, Barrnap/tRNAscan) into a single TSV file ready for import. Designed for batch runs over hundreds of species.

```bash
python scripts/collect_annotation_stats.py \
    --manifest manifest.tsv \
    --output combined_stats.tsv
```

### Manifest format

Tab-separated file with one row per annotation. Lines starting with `#` are ignored. Column order must match:

| Column | Required | Description |
|--------|----------|-------------|
| `species_label` | Yes | Short label used in log messages (no spaces recommended) |
| `ncbi_taxid` | No | NCBI taxonomy ID (informational only) |
| `gaqet_dir` | Yes | Directory containing `AnnotationQC_{timestamp}/` subdirectories |
| `assembly_qc_dir` | No | `AssemblyQC/` directory with BUSCO and QUAST subdirectories |
| `earlgrey_dir` | No | EarlGrey output directory containing `*.highLevelCount.txt` |
| `rdna_log` | No | Path to a Barrnap + tRNAscan-SE combined log file |
| `re_annotation_version` | No | Free-text version label for the repeat element annotation (e.g. `EarlGrey_v4.2.2`) |

Example:
```
species_label    ncbi_taxid  gaqet_dir                           assembly_qc_dir                    earlgrey_dir                    rdna_log                           re_annotation_version
Antox_HELIXER    241857      /data/Antiaris/03_AbInitio/HELIXER  /data/Antiaris/00_Source/AssemblyQC /data/Antiaris/10_Rep/EarlGrey/  /data/Antiaris/10_Rep/rDNA/Run.log EarlGrey_v4.2.2
# this row is a comment and will be ignored
Arath_BRAKER     3702        /data/Arabidopsis/03_AbInitio/BRAKER
```

### What is collected

| Source | Output columns |
|--------|---------------|
| GAQET `*_GAQET.stats.tsv` | All annotation QC columns pass through (Species, gene/transcript counts, BUSCO, PSAURON, OMArk, DETENGA, protein hits…); `Annotation_Version` is renamed to `Gene_Model_Annotation_Version` |
| Manifest `re_annotation_version` | `Repetitive_Elements_Annotation_Version` |
| AssemblyQC BUSCO | `Assembly_BUSCO_viridiplantae_odb10`, `Assembly_BUSCO_embryophyta_odb10` |
| QUAST `report.txt` | `Assembly_Total_Length_bp`, `Assembly_Contigs_N`, `Assembly_Largest_Contig_bp`, `Assembly_GC_pct`, `Assembly_N50_bp`, `Assembly_N90_bp`, `Assembly_auN_bp`, `Assembly_L50`, `Assembly_L90`, `Assembly_Ns_per_100kbp` |
| EarlGrey `*.highLevelCount.txt` | `RE_{Class}_pct` and `RE_{Class}_Coverage_bp` for DNA, Rolling Circle, Penelope, LINE, SINE, LTR, Other, Unclassified, Non-Repeat; plus `RE_Genome_Size_bp` |
| Barrnap + tRNAscan log | `rRNA_18S_N`, `rRNA_18S_partial_N`, `rRNA_28S_N`, `rRNA_28S_partial_N`, `rRNA_5.8S_N`, `rRNA_5S_N`, `rRNA_5S_partial_N`, `tRNA_N`, `tRNA_pseudogene_N` |

### Directory conventions expected

- **GAQET**: `gaqet_dir/AnnotationQC_{timestamp}/Species_GAQET.stats.tsv` — the script auto-selects the most recent `AnnotationQC_*` subdirectory.
- **BUSCO**: subdirectory names inside `assembly_qc_dir` must contain both `busco` and either `virid` (viridiplantae) or `embry` (embryophyta).
- **QUAST**: subdirectory name inside `assembly_qc_dir` must contain `quast`; the `report.txt` file is parsed inside it.
- **EarlGrey**: `*.highLevelCount.txt` is searched directly in `earlgrey_dir`.
- **rDNA log**: the SUMMARY section at the end of the log file is parsed; the rest is ignored.

### Update behaviour

When `--output` already exists, rows are matched by the `Species` value from the GAQET stats file. Existing rows are overwritten with new data; rows not present in the manifest are preserved unchanged; new rows are appended. This allows incremental updates as new species are processed.

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
