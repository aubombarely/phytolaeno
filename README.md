# Phytolaeno

<p align="center">
  <img src="assets/phytolaeno_logo.svg" width="260" alt="Phytolaeno logo"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.3.0-teal"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue"/>
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey"/>
  <img src="https://img.shields.io/badge/license-MIT-green"/>
  <img src="https://img.shields.io/badge/status-active%20development-orange"/>
</p>

<p align="center">
  <a href="https://codespaces.new/aubombarely/phytolaeno?quickstart=1"><img src="https://github.com/codespaces/badge.svg" alt="Open the demo in GitHub Codespaces"/></a>
</p>

<p align="center"><a href="#try-the-demo">Try the demo</a> · <a href="#screenshots">Screenshots</a> · <a href="CHANGELOG.md">Changelog</a></p>

**Phytolaeno** is a plant genome annotation management system that covers the full lifecycle from raw analysis outputs to an interactive web portal. The name blends *Phyto-* (plant) with *Celaeno*, the mythical library from the Cthulhu Mythos — consistent with the lab's naming convention (see also: ShoggoTEh).

The system has four interconnected parts:

1. **Directory setup** (`generate_species_dir.py`) — scaffold a standardised directory tree for each species and assembly on the server
2. **Manifest generation** (`generate_manifest.py`) — walk the directory tree and auto-discover analysis outputs, producing a manifest TSV
3. **Stats collection** (`collect_annotation_stats.py`) — parse pipeline outputs (GAQET, QUAST, BUSCO, EarlGrey, Barrnap/tRNAscan) into a single combined TSV
4. **Web portal** (`app/`) — browse, compare, upload, and visualise assembly and annotation data through a FastAPI + PostgreSQL application

---

## Try the demo

The demo runs the full portal on a small SQLite database, with no PostgreSQL
needed. **All data are real**: three species from the KATULU / GAQET plant
annotation benchmark (García-Carpintero *et al.*, in revision).

| Species | Assemblies | Annotations |
|---|---|---|
| *Arabidopsis thaliana* | TAIR10, TAIR12 (T2T) | 16 |
| *Oryza sativa* | Osativa_204 (MSU r7) | 12 |
| *Cucumis sativus* | ChineseLong v3 (CuGenDB), 9930 v3 (RefSeq) | 13 |

The annotations are the public references (Araport11, TAIR10, TAIR12, MSU r7,
CuGenDB, three NCBI RefSeq) and 33 annotation-tool runs (ANNEVO, Helixer,
Tiberius, BRAKER1/2/3, EGAPx, EviAnn, GeMoMa, MAKER, StringTie+TD). Source tables:
[`demo/data/`](demo/data/), extracted with `scripts/build_demo_data.py`.

What a reviewer can do in two minutes:

- **Species → Assemblies → Annotations.** Each species page has links to NCBI
  Taxonomy, GoaT and Wikispecies, an assembly table (type, size, sequences,
  N90/L90, gaps, organelles, BUSCO) and, for each assembly, the annotations
  side by side, ranked by GAQET's **Global Annotation Score (GAS)**.
- **Insight tags.** *No UTRs* flags annotations where fewer than 1% of
  transcripts have a UTR (most ab initio and AI-based tools); *1 isoform/gene*
  marks tools that predict a single transcript per gene. Click a tag to read
  why it matters.
- **Plots.** Per species: the chosen metric per annotation, the same tool on
  each assembly, and the **GAQET radar** with sliders to change the weight of
  each analysis in the GAS and watch the ranking move. **Compare species**
  shows how each tool does across the three genomes.
- **Get the data.** Public annotations link to their source (Phytozome, NCBI,
  TAIR, RGAP, CuGenDB); the benchmark runs will link to Zenodo.

**Option 1: in your browser, no installation.** Click
[**Open in GitHub Codespaces**](https://codespaces.new/aubombarely/phytolaeno?quickstart=1)
(this needs a free GitHub account). The demo builds itself and opens the portal
on port 8000 after about 2 minutes.

**Option 2: on your computer** (Python 3.10+):

```bash
git clone https://github.com/aubombarely/phytolaeno.git
cd phytolaeno
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/demo.py          # then open http://localhost:8000
```

Use `python scripts/demo.py --no_serve` to only build the database
(`demo/phytolaeno_demo.db`), or `--port` to choose another port.

---

## Screenshots

All screenshots come from the demo database (real data).

| | |
|---|---|
| **Species:** *A. thaliana* — links, assembly metrics, annotations ranked by GAS with tags<br><img src="docs/screenshots/03_species_detail.png" width="420"/> | **Plots:** rice annotations, per-assembly comparison and the GAQET radar<br><img src="docs/screenshots/06_plots.png" width="420"/> |
| **Annotation:** full GAQET QC of ANNEVO on TAIR10 (note *No UTRs*)<br><img src="docs/screenshots/05_annotation_detail.png" width="420"/> | **Compare species:** each tool across the three genomes<br><img src="docs/screenshots/07_compare.png" width="420"/> |
| **Assembly:** TAIR10 and its 15 annotations<br><img src="docs/screenshots/04_assembly_detail.png" width="420"/> | **Home**<br><img src="docs/screenshots/01_home.png" width="420"/> |

---

## Project status

Phytolaeno is **under active development**. The data-management scripts (Parts 1–3) are used in production on the lab's servers to organise the annotation outputs of hundreds of plant genomes, and the web portal (Part 4) is functional but not yet publicly deployed. Current work:

- migration of the existing data to the v2 directory layout (see Part 1);
- a public instance of the portal, with authentication for the upload routes;
- extending the data model beyond annotations to gene families and ranked candidate genes.

Interfaces and the database schema may still change between minor versions. See the [CHANGELOG](CHANGELOG.md).

---

## Workflow Overview

```
                           ┌─────────────────────────────────┐
                           │  Genome annotation pipelines     │
                           │  (BRAKER, HELIXER, EarlGrey …)   │
                           └────────────────┬────────────────┘
                                            │ outputs land in
                                            ▼
┌─────────────────────┐     ┌──────────────────────────────┐
│ generate_species    │────▶│  BySpecies/ directory tree    │
│ _dir.py             │     │  (standardised v2 layout)     │
│                     │     └──────────────┬───────────────┘
│ • species skeleton  │                    │
│ • NCBI taxonomy     │                    ▼
│ • assembly dirs     │     ┌──────────────────────────────┐
└─────────────────────┘     │  generate_manifest.py         │
                            │                              │
                            │  • discovers assemblies      │
                            │  • discovers annotations     │
                            │  • produces manifest.tsv     │
                            └──────────────┬───────────────┘
                                           │
                                           ▼
                            ┌──────────────────────────────┐
                            │  collect_annotation_stats.py  │
                            │                              │
                            │  • parses GAQET, QUAST,      │
                            │    BUSCO, EarlGrey, rDNA     │
                            │  • produces combined_stats   │
                            └──────────────┬───────────────┘
                                           │
                                           ▼
                            ┌──────────────────────────────┐
                            │  Web portal (app/)            │
                            │                              │
                            │  • import_excel.py (bulk)    │
                            │  • upload form (per entry)   │
                            │  • browse / search / plots   │
                            └──────────────────────────────┘
```

---

## Part 1 — Directory Setup

Use `generate_species_dir.py` to create the standard directory skeleton for a new species or to add an assembly to an existing one. The script also fetches NCBI taxonomy data automatically.

```bash
# Create a species skeleton (fetches taxonomy from NCBI)
python scripts/generate_species_dir.py --root /path/to/BySpecies --species Nicotiana_tabacum

# Add an assembly to an existing species
python scripts/generate_species_dir.py --root /path/to/BySpecies --species Nicotiana_tabacum \
    --assembly NtK326IBMCPv1

# Preview what would be created without touching the filesystem
python scripts/generate_species_dir.py --root /path/to/BySpecies --species Nicotiana_tabacum \
    --assembly NtK326IBMCPv1 --dry_run

# Skip NCBI taxonomy fetch (for servers without internet access)
python scripts/generate_species_dir.py --root /path/to/BySpecies --species Nicotiana_tabacum \
    --no_taxonomy
```

The script creates the following layout (v2):

```
{species_name}/
├── 00_Taxonomy/
│   ├── taxonomy.txt          ← human-readable summary
│   ├── taxonomy.tsv          ← tab-separated fields
│   └── taxonomy.json         ← machine-readable with full lineage list
├── 01_Genomes/
│   └── {assembly_name}/      ← created with --assembly; dir name IS the assembly name
│       ├── 00_SourceFiles/   ← genome FASTA + equiv_seqID.txt
│       ├── 01_Assembly_QC/   ← QUAST + BUSCO output
│       ├── 02_WorkingFiles/
│       └── 03_Annotations/
│           ├── 00_Repetitive_landscape_annotations/   ← tool dirs added by analyses
│           └── 01_Gene_model_annotations/             ← tool dirs added by analyses
└── 02_Transcriptomes/        ← subdirs created by transcriptome analyses
```

All operations are idempotent — re-running with the same arguments is safe. Call the script once per assembly as new assemblies become available.

---

## Part 2 — Manifest Generation

`generate_manifest.py` walks a `BySpecies/` root directory and auto-discovers analysis outputs for each species, producing a manifest TSV that drives stats collection.

```bash
# v2 layout (generated by generate_species_dir.py)
python scripts/generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \
    --layout v2

# v1 legacy layout (default, for existing data)
python scripts/generate_manifest.py --root /path/to/BySpecies --output manifest.tsv

# Limit to specific species
python scripts/generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \
    --layout v2 --species Arabidopsis_thaliana Nicotiana_benthamiana

# Custom RE tool priority when multiple RE dirs are present (default: 02_EarlGrey)
python scripts/generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \
    --layout v2 --re_landscape_priority 01_RepeatModelerMasker,02_EarlGrey

# Ignore specific directories during discovery
python scripts/generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \
    --layout v2 --ignore_dir 99_Comparison 98_Scratch
```

Two directory layouts are supported with `--layout`:

### Layout v2 (new — generated by `generate_species_dir.py`)

Assembly linking is implicit: annotations live under their assembly directory, so no filename matching is needed.

```
{species_name}/
├── 01_Genomes/
│   └── {assembly_name}/                                  ← dir name IS the assembly name
│       ├── 00_SourceFiles/                               ← genome FASTA + equiv_seqID.txt
│       ├── 01_Assembly_QC/                               ← QUAST + BUSCO
│       └── 03_Annotations/
│           ├── 00_Repetitive_landscape_annotations/
│           │   ├── 02_EarlGrey/
│           │   └── 10_rDNAtDNA/
│           └── 01_Gene_model_annotations/
│               └── {tool}/
│                   └── AnnotationQC_{ts}/
```

### Layout v1 (legacy, default)

Used for existing data that predates `generate_species_dir.py`. Annotations are linked to assemblies via `{assembly_name}*.gff3` filename matching.

```
{species_name}/
├── 00_GenomeSource/
│   └── {assembly_id}/
│       ├── {assembly_name}_genome.fasta
│       ├── {assembly_name}_genome.equiv_seqID.txt
│       └── AssemblyQC/
├── 03_AbInitioPredictions/
│   └── {annotation_id}/
│       ├── {assembly_name}*.gff3                         ← links annotation to assembly
│       └── AnnotationQC_{ts}/
└── 10_RepetitiveLandscape/
    ├── 02_EarlGrey/
    └── 10_rDNAtDNA/
```

### Manifest columns

One manifest row is produced per `(assembly × annotation)` pair:

| Column | Derived from |
|--------|-------------|
| `species_name` | Species directory name |
| `assembly_name` | Stem of `*_genome.fasta` (v1) or assembly directory name (v2) |
| `assembly_qc_dir` | `AssemblyQC/` (v1) or `01_Assembly_QC/` (v2) |
| `equiv_seqid_file` | Path to `*.equiv_seqID.txt` (blank if absent) |
| `gene_annotation_name` | `{species_name}_{TOOL}` — e.g. `Arabidopsis_thaliana_HELIXER` |
| `repelem_annotation_name` | `{species_name}_{RE_TOOL}` — e.g. `Arabidopsis_thaliana_EARLGREY` |

**RE tool priority:** when multiple tool directories exist, the first match in the priority list is used (default: `02_EarlGrey`). Falls back to the first alphabetically with a warning.

All warnings are written to both the console and a timestamped file (`generate_manifest_warning_{timestamp}.log`), deleted automatically if empty. A summary table is printed at the end and saved to `generate_manifest_summary_{timestamp}.log`.

---

## Part 3 — Stats Collection

`collect_annotation_stats.py` reads the manifest produced in Part 2 and parses each pipeline's output files, combining everything into a single TSV ready for import into the portal.

```bash
python scripts/collect_annotation_stats.py \
    --manifest manifest.tsv \
    --output combined_stats.tsv
```

### What is collected

| Source | Output columns |
|--------|---------------|
| Manifest identity | `species_name`, `assembly_name`, `equiv_seqid_file`, `gene_annotation_name`, `repelem_annotation_name` |
| GAQET `*_GAQET.stats.tsv` | Gene/transcript/CDS/exon counts, lengths, BUSCO, PSAURON, OMArk, DETENGA, protein hits; `Annotation_Version` → `Gene_Model_Annotation_Version` |
| AssemblyQC BUSCO | `Assembly_BUSCO_viridiplantae_odb10`, `Assembly_BUSCO_embryophyta_odb10` |
| QUAST `report.txt` | `Assembly_Total_Length_bp`, `Assembly_Contigs_N`, `Assembly_Largest_Contig_bp`, `Assembly_GC_pct`, `Assembly_N50_bp`, `Assembly_N90_bp`, `Assembly_auN_bp`, `Assembly_L50`, `Assembly_L90`, `Assembly_Ns_per_100kbp` |
| EarlGrey `*.highLevelCount.txt` | `RE_{Class}_pct` and `RE_{Class}_Coverage_bp` for DNA, Rolling Circle, Penelope, LINE, SINE, LTR, Other, Unclassified, Non-Repeat; plus `RE_Genome_Size_bp` |
| Barrnap + tRNAscan log | `rRNA_18S_N`, `rRNA_28S_N`, `rRNA_5.8S_N`, `rRNA_5S_N` (+ partial counts), `tRNA_gene_N`, `tRNA_pseudogene_N`, `tRNA_exon_N` |

### Directory conventions expected

- **GAQET**: `gaqet_dir/AnnotationQC_{timestamp}/Species_GAQET.stats.tsv` — the most recent `AnnotationQC_*` subdirectory is selected automatically.
- **BUSCO**: subdirs inside `assembly_qc_dir` must contain both `busco` and either `virid` or `embry`.
- **QUAST**: subdir inside `assembly_qc_dir` must contain `quast`; `report.txt` is parsed inside it.
- **EarlGrey**: `*.highLevelCount.txt` searched directly in `earlgrey_dir`.
- **rDNA log**: the SUMMARY section at the end of the log file is parsed.

### Update behaviour

When `--output` already exists, rows are matched by species name. Existing rows are overwritten; rows not in the manifest are preserved; new rows are appended. This allows safe incremental updates as new species are processed.

---

## Part 4 — Web Portal

### Installation

#### 1. Clone and create a virtual environment

```bash
git clone https://github.com/aubombarely/phytolaeno.git
cd phytolaeno
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 2. Configure the database

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL, e.g.:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/phytolaeno
```

```sql
CREATE DATABASE phytolaeno;
```

#### 3. Start the server

```bash
uvicorn app.main:app --reload
```

Tables are created automatically on startup. Open your browser at `http://localhost:8000`.

### Loading data

**From the combined TSV** (output of Part 3, recommended for batch loads):

```bash
python scripts/import_excel.py --excel PlantAnnotationBenchmark2025.xlsx
```

The script expects Sheet1 with one row per gene model annotation, groups by `Assembly_Version`, and creates Species, Assembly, RepeatAnnotation (EarlGrey, Barrnap, tRNAScan-SE), and GeneModelAnnotation records. Re-running is safe — existing records are reused.

**From the web form** (for individual entries): navigate to `/upload` and fill the tabbed form.

### URL Map

| URL | Description |
|---|---|
| `/` | Home — summary stats and navigation cards |
| `/species` | Paginated species list with search/filter by name, family, lineage |
| `/species/{id}` | Species detail with all assemblies and annotation sub-lists |
| `/assemblies/{id}` | Assembly detail with sortable GM and RE annotation tables |
| `/annotations/gm/{id}` | Full gene model annotation detail: counts, lengths, quality flags, QC scores |
| `/annotations/re/{id}` | Repeat annotation detail with per-class breakdown chart |
| `/upload` | Tabbed form to add new gene model or repeat element annotations |
| `/plots` | Interactive analysis plots |

### Analysis Plots

The `/plots` page renders five Plotly figures:

1. **BUSCO completeness by tool** — box plot of viridiplantae BUSCO completeness per annotation tool
2. **Gene models by tool** — box plot of gene model counts per tool
3. **Mean intron vs mean exon length** — scatter plot coloured by tool
4. **PSAURON score by tool** — box plot of annotation quality scores
5. **Repeat content by species** — stacked bar chart of EarlGrey repeat classes (DNA, LTR, LINE, SINE, RC, Other)

### Database Schema

```
Species
  └── Assembly
        ├── RepeatAnnotation  ← EarlGrey, Barrnap, tRNAScan-SE, …
        │     └── AnnotationProtocol
        └── GeneModelAnnotation  ← BRAKER, HELIXER, ANNEVO, …
              └── AnnotationProtocol
```

- **Species** — name, NCBI TaxID, family, lineage
- **Assembly** — version, source, size, status, assembly-level BUSCO (viridiplantae + embryophyta)
- **AnnotationProtocol** — tool, version, commands, notes (shared by both annotation types)
- **RepeatAnnotation** — total repeat %, raw output, per-class breakdown (JSON)
- **GeneModelAnnotation** — gene/transcript/CDS/exon counts, length statistics, quality flags, BUSCO, OMArk, PSAURON, DETENGA, protein homology, GAQET, F1 scores

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
│   ├── generate_species_dir.py       # Part 1 — directory setup
│   ├── generate_manifest.py          # Part 2 — manifest generation
│   ├── collect_annotation_stats.py   # Part 3 — stats collection
│   └── import_excel.py               # Bulk import from Excel benchmark table
├── scripts/demo.py                   # one-command demo (SQLite, real data)
├── scripts/build_demo_data.py        # extracts demo/data/ from the benchmark spreadsheet
├── demo/data/                        # real 3-species demo tables
├── docs/screenshots/                 # README screenshots (from the demo)
├── .devcontainer/                    # GitHub Codespaces demo configuration
├── tests/                            # pytest suite (SQLite, no PostgreSQL needed)
├── requirements.txt
├── requirements-dev.txt
├── CHANGELOG.md
├── CITATION.cff
├── LICENSE
├── .env.example
└── .gitignore
```

---

## Dependencies

Python 3.10+ and PostgreSQL. All Python dependencies are pinned in
[`requirements.txt`](requirements.txt): FastAPI, Uvicorn, SQLAlchemy 2.0
(with psycopg2), Alembic, Jinja2, python-multipart, python-dotenv, pandas,
openpyxl and Plotly.

---

## Testing

The test suite runs against a throw-away SQLite database, so no PostgreSQL
server is needed:

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
```

It renders every portal page, stores an annotation through the upload form,
and checks the BUSCO/EarlGrey parsers.

---

## License

MIT — see [LICENSE](LICENSE). If you use Phytolaeno, please cite it using
[`CITATION.cff`](CITATION.cff).

---

*Phytolaeno — Plant Genome Annotation Archive. Named after the Library of Celaeno.*
