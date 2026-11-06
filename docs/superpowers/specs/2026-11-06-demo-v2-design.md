# Phytolaeno demo v2 — design

Date: 2026-11-06 · Status: user answers incorporated, awaiting approval · Repo: `tools/phytolaeno` (public, github.com/aubombarely/phytolaeno)

## Intent and why

Phytolaeno is cited in the GeneDAIS proposal (AEI PID 2026, Subobjective 1.3, deadline 2026-11-24). Reviewers will open
the demo (GitHub Codespaces or `python scripts/demo.py`). The demo must make them think **"this is useful"** within a
couple of minutes.

The expected reviewer journey (from the user): open their favourite genome (most likely *Arabidopsis*), check what they
already know (species, assembly metrics, annotation metrics), try to download annotations, look at figures that tell
them something, compare annotations, and find **new insights** — e.g. a tag saying an annotation has no UTRs, which ties
directly to the proposal's argument (AI annotators predict CDS only; missing UTRs hide uORFs and 3′ UTR elements).

## Goals

1. **All-real demo data** for three species: *Arabidopsis thaliana*, *Oryza sativa*, *Cucumis sativus*.
2. Pages follow Phytolaeno's own structure: **Species → Assemblies → Annotations**.
3. Every species, assembly and annotation has a **description**, and a **clickable source link** when it is public.
4. Species page links to **NCBI Taxonomy, GoaT and Wikispecies**.
5. New **assembly metrics** (below).
6. **Annotation tags** that surface insights (no UTRs; isoforms; short introns later).
7. **Downloads**: public annotations link to their source; the lab's runs link to Zenodo (URL filled later by the user).
8. **Plots** selectable by species, assembly and annotations, with two views (within-species and across-species) and an
   interactive **GAQET radar** with the Global Annotation Score (GAS) and live weight sliders.

## Non-goals

- The other 527 species of the benchmark spreadsheet are **not** in the public demo.
- No GFF3/FASTA files stored in the repo (downloads are links only).
- No public deployment/authentication work (separate, already noted in CLAUDE.md).
- No static GAQET image (the existing JPEGs come from older runs and may not match the demo's annotation set — *builder's
  note: my call, avoids inconsistency*).

## Anti-goals (would make this a failure even if it works)

- Flagging a **reference** annotation (Araport11, RefSeq, MSU r7, TAIR10/12) with a warning that is really an artefact of
  a weak metric. Tags must only appear when the underlying number supports them.
- Anything that looks unfinished to a reviewer: dead links, empty download buttons, "TODO" text, broken plots.
- Mixing real and invented numbers. The 11 synthetic species, their generator code and the "synthetic data" banner are
  **removed** (confirmed by the user 2026-11-06). The demo is entirely real: 3 species, 5 assemblies, 41 annotations.
  A short neutral note may still say the demo is a subset of the benchmark.
- Plots/radar numbers that disagree with what GAQET itself computes.

## Data

### Source

Single source for annotation and per-assembly QC values:
`agent_test/data/genomes/PlantAnnotationBenchmark2025.xlsx` (Sheet1, 917 rows × 65 cols; one row per annotation).
Extract only rows with `Species` ∈ {`Arabidopsis_thaliana`, `Oryza_sativa`, `Cucumis_sativus`} (41 rows: 16 + 12 + 13)
into a committed, sorted TSV: `demo/data/benchmark_3species.tsv`. The user has approved releasing these values publicly
(they include the GAQET paper's tool runs, García-Carpintero et al., in revision).

This replaces `demo/data/Athaliana_GAQET_benchmark.tsv` (the GAQET `.txt` table) — the spreadsheet is more complete
(includes Tiberius; repeat/rDNA/tRNA/assembly BUSCO columns). Remove the old file and its loader.

Known spreadsheet quirks the loader must handle:
- `Species` uses underscores (`Oryza_sativa`) → display with a space.
- Arabidopsis `Assembly_Version` values: `Athaliana_447_Araport11`, `TAIR10_chr_all`, `GCA_978657495.1_TAIR12_genomic`.
  `Athaliana_447_Araport11` and `TAIR10_chr_all` are **the same assembly** (user) → merge into one assembly "TAIR10";
  keep both names in its description.
- Some rows have empty `Annotation_Rank` (cucumber ChineseLong) — rank by GAS instead (see Plots).
- `Annotation_Version` sometimes holds a DOI URL instead of a name (e.g. Araport11 row) → derive a display name from
  `Annotation_Methodology`/known references; keep the DOI as the publication link.
- `Annotation_Methodology` uses codes (`AbI:`, `EvT:`, `EvP:`, `GIP:`) → parse the main tool name for grouping in plots
  (e.g. ANNEVO, Helixer, BRAKER1/2/3, EviAnn, GeMoMa, MAKER, StringTie+TD, EGAPx/Gnomon, Tiberius; references as
  "Reference").

### Assembly metrics (new; user-provided QUAST values, collected 2026-11-06)

Stored in `demo/data/assembly_metrics.tsv` (copy of `.superpowers/brainstorm/assembly_metrics_collected.tsv`, minus the
merged `TAIR10_chr_all` row):

| Assembly | Size (bp) | Type | Seqs | N90 | L90 | N's/100 kbp | Length ≥10 kb | Plastid | Mito |
|---|---|---|---|---|---|---|---|---|---|
| TAIR10 (Athaliana_447 = TAIR10_chr_all) | 119,667,750 | Chromosome-level | 7 | 18,585,056 | 5 | 155.60 | 119,667,750 | Yes | Yes |
| GCA_978657495.1 TAIR12 | 142,481,245 | T2T gapless | 5 | 25,768,865 | 5 | 0.00 | 142,481,245 | No | No |
| Osativa_204 | 374,471,240 | Chromosome-level | 14 | 23,207,287 | 11 | 44.13 | 374,471,240 | Not identified | Not identified |
| ChineseLong_genome_v3 | 226,211,662 | Chromosome-level | 85 | 22,466,726 | 7 | 15.99 | 226,206,186 | Not identified | Not identified |
| GCF_000004075.3 Cucumber 9930 V3 | 226,640,966 | Chromosome-level | 88 | 22,466,726 | 7 | 15.96 | 226,635,490 | Yes | Yes |

Fields (decided by the user): assembly size; type (T2T gapless / chromosome-level / long scaffolds / short scaffolds /
contigs); number of sequences; N90/L90; # N's per 100 kbp; total length (≥10,000 bp); plastid genome; mitochondrial
genome. Organelle fields are **three-state**: Yes (sequence labelled as organelle), Not identified (none labelled, may be
among unplaced scaffolds), No (cannot be present, e.g. all sequences are chromosomes). Type is a stored label; if absent,
the builder may infer it from the metrics (rule left to the builder).

Cucumber: ChineseLong v3 (CuGenDB) and 9930 v3 (RefSeq) share the 7 chromosomes but differ in small sequences and
organelles → **two separate assemblies**.

Assembly BUSCO, EarlGrey repeat content, rDNA (Barrnap) and tRNA (tRNAscan-SE) come from the spreadsheet.

### Descriptions and links

Every species, assembly and annotation gets a short description (1–3 sentences) and, if public, a source URL. The
builder **drafts** them from public sources and the methodology column, records the source of each, and sends the full
list to the user for review **before** committing them. Store in `demo/data/descriptions.tsv`
(`level`, `key`, `description`, `source_url`).

Species external links are built from the NCBI TaxID / name: NCBI Taxonomy, GoaT (`goat.genomehubs.org`, taxon search),
Wikispecies. Verify each URL pattern resolves for the three species.

### Downloads

- Public annotations (Araport11, TAIR10, TAIR12, RefSeq ×3, MSU r7, ChineseLong v3 official): link to their public
  source pages (Phytozome, NCBI, TAIR, CuGenDB).
- The lab's tool runs: a `zenodo_url` field per annotation, empty for now; the user uploads to Zenodo and fills it later.
- **While empty, show no download control** (no greyed "coming soon" button) — *my call, avoids looking unfinished*.

## Pages

### Species page (main entry point)

Top to bottom: header (name, family, lineage, description) + buttons NCBI Taxonomy / GoaT / Wikispecies → **Assemblies
table** (one row per assembly with the fields above, description, source link) → for each assembly, **annotation
comparison table** (one row per annotation: display name, tool, genes, transcripts, BUSCO C%, PSAURON, GAS, tags,
source/download link) → **plots already filtered to this species** (same components as the Plots page).

Breadcrumbs and navigation must make Species → Assemblies → Annotations obvious on every page. Existing assembly and
annotation detail pages stay, gaining description, link and tags.

### Tags on annotations

| Tag | Kind | Rule | Status |
|---|---|---|---|
| No UTRs | warning (amber) | **fewer than 1% of transcripts have a UTR** (5′ or 3′), i.e. max(UTR5', UTR3') / transcript models < 0.01 — user-approved 2026-11-06, so BRAKER1/2 runs with a handful of UTRs are tagged consistently across species; threshold configurable | build now |
| Isoforms | neutral info (grey), e.g. "1.75 isoforms/gene" or "1 isoform per gene" | transcripts / genes | build now; neutral by user's agreement (one isoform per gene is normal for AI tools; many isoforms is not an error) |
| Short introns / micro-exons | warning (red) | needs a **per-annotation percentage** (new nullable field, e.g. `micro_exon_pct`); threshold left to builder, configurable | build the code path now; **hidden while the field is empty** (data later, from GAQET2 or the lab's analysis). Do NOT use `Shortest Intron Length`: it is 1–5 bp even for RefSeq/MSU r7 |

Clicking a tag shows a one-paragraph explanation of why it matters (UTRs → uORFs, 3′ UTR elements, transcript
boundaries; short introns/micro-exons → AI annotation artefacts), phrased consistently with the GeneDAIS proposal.

## Plots

One page with selectors: **species**, **assembly**, **annotations** (multi-select), **metric**. Same component embedded
(pre-filtered) on the species page.

- **View A — within one assembly:** horizontal bar chart, one bar per annotation, sorted by value, labels on the axis
  (bars aligned), reference annotations grey, tool runs coloured, tags shown next to bars.
- **View B — across species:** for the chosen metric, each tool's value per species; the selected species highlighted,
  others grey.
- Metrics menu: BUSCO complete % (Viridiplantae/Embryophyta), gene models, PSAURON, % transcripts with UTRs,
  isoforms per gene, mean intron, single-exon genes, GAS, repeat content (assembly level). Builder may add others
  present in the data.
- **GAQET radar:** interactive polar chart (Plotly `Scatterpolar`), one polygon per selected annotation, legend toggles.
  Axes and formulas must match GAQET2 `revision` branch `GAQET/gaqet_plot.py`
  (https://github.com/victorgcb1987/GAQET2/blob/revision/GAQET/gaqet_plot.py), confirmed by the user:
  - SwissProt hits % and TrEMBL hits % (`ProteinsWith…Hits (%)`, first two such columns)
  - Proteins fitting their taxonomic rank: **OMArk Species Composition %**
  - BUSCO C% for the two Annotation BUSCO columns
  - Proteins with functional domains: DeTEnGA `PcpM0` from `DETENGA_FP%`
  - Transcripts flagged as coding: PSAURON score
  - No start/stop codon errors: `100 − 100 × (START missing + STOP missing + START&STOP missing) / transcript models`
  - Axis order as in GAQET: homology ×2, OMArk, BUSCO ×2, DeTEnGA, PSAURON, AGAT.
  - **Global Annotation Score (GAS)** = Σ share_i × metric_i over available metrics; default equal shares; metrics from a
    missing analysis are skipped. Annotations ranked by GAS.
  - **Weight sliders** (one per analysis role: homology, BUSCO, OMArk, PSAURON, DeTEnGA, AGAT) re-rank live,
    reproducing GAQET's `--weights` role semantics (role share split equally among its metrics; shares sum to 100%).
  - Add a unit test that computes GAS for at least one row and checks it against GAQET's formula.

## Constraints

- Python 3.10+, FastAPI + SQLAlchemy 2.0.x (stay on 2.0: 2.1 switches the PG driver), Plotly.js 4.1.1 (matches
  plotly.py 7), pinned deps; tests run on SQLite without PostgreSQL. Codespaces config already works (user-tested).
- Schema changes need new nullable columns (assembly metrics, organelle three-state, descriptions/links, zenodo_url,
  micro-exon %). `create_all` is used, no Alembic migrations in practice; the demo DB is rebuilt from scratch each run.
  The production loader (`scripts/import_excel.py`) must keep working with the spreadsheet.
- Follow the workspace blueprint where applicable (VERSION, sorted outputs, CHANGELOG, version bump → v0.3.0).
- Screenshots in `docs/screenshots/` regenerated after the change (headless Chrome; kill each process after the file
  appears — Chrome does not exit by itself).
- Must be finished, committed and pushed well before 2026-11-24 (proposal deadline); the user pushes.

## Settled after builder check (Claude's calls, 2026-11-06)

- **Ranking:** ignore the spreadsheet's `Annotation_Rank` (inconsistent: duplicate ranks, cucumber empty). Compute GAS
  on load and use the GAS order **everywhere** (tables, radar, plots), so a reviewer never sees two orders.
- **Production loader:** the new fields (assembly metrics, organelle states, descriptions/links, `zenodo_url`,
  `micro_exon_pct`) are loaded by the demo from TSVs in `demo/data/` for now. `import_excel.py` must keep working
  unchanged; pages hide any new field that is empty, so production pages are unaffected. Zenodo URLs go in a committed
  `demo/data/downloads.tsv` (`annotation_key`, `zenodo_url`) that the user edits later.
- **Proposal wording for tag explanations:** source is `agent_test/docs/proposals/PID2026/GeneDAIS_agreed_text.md`
  (Subobjective 1.1, error class 5 "Missing UTRs" and the micro-exon paragraph). The builder drafts the explanations
  and sends them to the user together with the descriptions for review. Do not copy restricted proposal text verbatim
  into the public repo; paraphrase the scientific point.
- **F1-Score Base/Locus, Missed/New Loci:** sparse (Arabidopsis only, no references) → show them on the annotation
  detail page when present, but **not** in the Plots metric menu.

## Reference annotations (user-confirmed 2026-11-06)

Drawn grey and grouped as "Reference" in plots; all others are tool runs. Store as an explicit `is_reference` column in
`demo/data/benchmark_3species.tsv` (the spreadsheet's `RefType` does not distinguish them).

- *A. thaliana*: Araport11, TAIR10, TAIR12, RefSeq (GCF_000001735.4)
- *O. sativa*: MSU r7 (`osa1_r7`), RefSeq (GCF_034140825.1)
- *C. sativus*: official ChineseLong v3 annotation (source:
  http://cucurbitgenomics.org/v2/ftp/genome/cucumber/Chinese_long/v3/), RefSeq 9930 v3 (GCF_000004075.3)
- The lab's EGAPx run is a **tool run**, not a reference, even though it uses the same NCBI pipeline as RefSeq (Claude's
  call; the user did not object).

## Left to the builder

Visual details, exact colours within the blueprint palette, how selectors are implemented (server-side query params or
client-side filtering), the assembly-type inference rule, the micro-exon tag threshold (configurable), naming of new
columns, and test structure.
