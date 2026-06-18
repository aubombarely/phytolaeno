#!/usr/bin/env python3
"""
collect_annotation_stats.py — Phytolaeno data collection

Reads a manifest TSV describing the locations of analysis outputs for one
or more genome annotations, collects metrics from each source, and writes
(or updates) a single combined TSV ready for Phytolaeno import.

For each manifest row the script:
  1. Finds the most recent AnnotationQC_{timestamp}/ directory in gaqet_dir
  2. Parses the *_GAQET.stats.tsv inside it  (annotation QC metrics)
  3. Parses AssemblyQC BUSCO (viridiplantae + embryophyta)             [optional]
  4. Parses the QUAST report.txt from AssemblyQC                       [optional]
  5. Parses the EarlGrey *.highLevelCount.txt (repeat composition)     [optional]
  6. Parses the SUMMARY section of a Barrnap+tRNAscan log              [optional]

Update behaviour: when --output already exists, rows are matched by the
Species key from the GAQET stats file.  Existing rows are overwritten with
new data; new rows are appended.  Rows not present in the manifest are
preserved unchanged.

Manifest format (tab-separated, lines starting with # are ignored).
Use generate_manifest.py to produce this file automatically.

    species_name           – species directory name
    assembly_name          – stem of *_genome.fasta (without _genome.fasta suffix)
    assembly_qc_dir        – AssemblyQC/ directory (BUSCO + QUAST);  leave empty if absent
    repelem_annotation_name – RE annotation identifier, e.g. Arabidopsis_thaliana_EARLGREY
    rdna_log               – path to Barrnap+tRNAscan log file;      leave empty if absent
    earlgrey_dir           – EarlGrey output dir with *.highLevelCount.txt; leave empty if absent
    gene_annotation_name   – gene annotation identifier, e.g. Arabidopsis_thaliana_HELIXER
    gaqet_dir              – directory that contains AnnotationQC_{timestamp}/ subdirs

Usage:
    python collect_annotation_stats.py --manifest manifest.tsv --output combined_stats.tsv
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _opt(value) -> Path | None:
    """Return Path if value is a non-empty, non-NA string; else None."""
    if pd.isna(value) or str(value).strip().upper() in ("NA", "NONE", ""):
        return None
    return Path(str(value).strip())


# ── AnnotationQC directory finder ─────────────────────────────────────────────

def find_latest_annotationqc(gaqet_dir: Path) -> Path:
    """Return the most recent AnnotationQC_{timestamp}/ subdir (sort by name)."""
    candidates = sorted(gaqet_dir.glob("AnnotationQC_*"), reverse=True)
    if not candidates:
        raise FileNotFoundError(
            f"No AnnotationQC_* directory found in {gaqet_dir}"
        )
    return candidates[0]


# ── GAQET stats parser ────────────────────────────────────────────────────────

def parse_gaqet_stats(annotationqc_dir: Path) -> dict:
    """Parse *_GAQET.stats.tsv; return first data row as a dict."""
    files = list(annotationqc_dir.glob("*_GAQET.stats.tsv"))
    if not files:
        raise FileNotFoundError(
            f"No *_GAQET.stats.tsv found in {annotationqc_dir}"
        )
    df = pd.read_csv(files[0], sep="\t", dtype=str)
    if df.empty:
        raise ValueError(f"Empty GAQET stats file: {files[0]}")
    return df.iloc[0].to_dict()


# ── Assembly BUSCO parser ─────────────────────────────────────────────────────

def _busco_summary_string(busco_dir: Path) -> str:
    """Return the C:X%[...] summary line from a BUSCO run directory."""
    for f in busco_dir.glob("short_summary.specific.*.txt"):
        with open(f) as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("C:"):
                    return stripped
    return ""


def parse_assembly_busco(assembly_qc_dir: Path) -> dict:
    """Parse BUSCO summary strings for viridiplantae and embryophyta."""
    result = {
        "Assembly_BUSCO_viridiplantae_odb10": "",
        "Assembly_BUSCO_embryophyta_odb10": "",
    }
    for entry in assembly_qc_dir.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name.lower()
        if "busco" not in name:
            continue
        if "virid" in name:
            result["Assembly_BUSCO_viridiplantae_odb10"] = _busco_summary_string(entry)
        elif "embry" in name:
            result["Assembly_BUSCO_embryophyta_odb10"] = _busco_summary_string(entry)
    return result


# ── QUAST parser ──────────────────────────────────────────────────────────────

# Maps the exact label from QUAST report.txt → output column name.
_QUAST_FIELDS = {
    "Total length":      "Assembly_Total_Length_bp",
    "# contigs":         "Assembly_Contigs_N",
    "Largest contig":    "Assembly_Largest_Contig_bp",
    "GC (%)":            "Assembly_GC_pct",
    "N50":               "Assembly_N50_bp",
    "N90":               "Assembly_N90_bp",
    "auN":               "Assembly_auN_bp",
    "L50":               "Assembly_L50",
    "L90":               "Assembly_L90",
    "# N's per 100 kbp": "Assembly_Ns_per_100kbp",
}


def parse_quast_report(assembly_qc_dir: Path) -> dict:
    """Parse report.txt from the *.quast/ subdir inside AssemblyQC/."""
    result = {v: "" for v in _QUAST_FIELDS.values()}

    quast_dirs = [d for d in assembly_qc_dir.iterdir()
                  if d.is_dir() and "quast" in d.name.lower()]
    if not quast_dirs:
        log.warning(f"No *.quast directory found in {assembly_qc_dir}")
        return result

    report = quast_dirs[0] / "report.txt"
    if not report.exists():
        log.warning(f"report.txt not found in {quast_dirs[0]}")
        return result

    with open(report) as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            # QUAST uses 2+ spaces between label and value for alignment.
            parts = re.split(r"\s{2,}", stripped)
            if len(parts) < 2:
                continue
            label, value = parts[0], parts[-1].strip()
            if label in _QUAST_FIELDS:
                result[_QUAST_FIELDS[label]] = value

    return result


# ── EarlGrey parser ───────────────────────────────────────────────────────────

# Maps TE Classification labels from highLevelCount.txt → output column prefix.
_EG_CLASS_MAP = {
    "DNA":                                        "RE_DNA",
    "Rolling Circle":                             "RE_RollingCircle",
    "Penelope":                                   "RE_Penelope",
    "LINE":                                       "RE_LINE",
    "SINE":                                       "RE_SINE",
    "LTR":                                        "RE_LTR",
    "Other (Simple Repeat, Microsatellite, RNA)": "RE_Other",
    "Unclassified":                               "RE_Unclassified",
    "Non-Repeat":                                 "RE_NonRepeat",
}


def parse_earlgrey(earlgrey_dir: Path) -> dict:
    """Parse *.highLevelCount.txt from an EarlGrey output directory."""
    result: dict = {}
    for prefix in _EG_CLASS_MAP.values():
        result[f"{prefix}_pct"] = ""
        if prefix != "RE_NonRepeat":
            result[f"{prefix}_Coverage_bp"] = ""
    result["RE_Genome_Size_bp"] = ""

    files = list(earlgrey_dir.glob("*.highLevelCount.txt"))
    if not files:
        log.warning(f"No *.highLevelCount.txt found in {earlgrey_dir}")
        return result

    df = pd.read_csv(files[0], sep="\t", dtype=str)
    for _, row in df.iterrows():
        cls = str(row["TE Classification"]).strip()
        prefix = _EG_CLASS_MAP.get(cls)
        if prefix is None:
            continue
        result[f"{prefix}_pct"] = row["% Genome Coverage"]
        if prefix != "RE_NonRepeat":
            result[f"{prefix}_Coverage_bp"] = row["Coverage (bp)"]
        if not result["RE_Genome_Size_bp"]:
            result["RE_Genome_Size_bp"] = row["Genome Size"]

    return result


# ── Output column order ───────────────────────────────────────────────────────

_COLUMN_ORDER = [
    # Identity
    "species_name", "assembly_name", "gene_annotation_name", "repelem_annotation_name",
    "Species", "NCBI_TaxID", "Assembly_Version",
    # Assembly QC
    "Assembly_BUSCO_viridiplantae_odb10", "Assembly_BUSCO_embryophyta_odb10",
    "Assembly_Total_Length_bp", "Assembly_Contigs_N", "Assembly_Largest_Contig_bp",
    "Assembly_GC_pct", "Assembly_N50_bp", "Assembly_N90_bp", "Assembly_auN_bp",
    "Assembly_L50", "Assembly_L90", "Assembly_Ns_per_100kbp",
    # Repetitive elements
    "RE_DNA_pct", "RE_RollingCircle_pct", "RE_Penelope_pct", "RE_LINE_pct",
    "RE_SINE_pct", "RE_LTR_pct", "RE_Other_pct", "RE_Unclassified_pct", "RE_NonRepeat_pct",
    "RE_DNA_Coverage_bp", "RE_RollingCircle_Coverage_bp", "RE_Penelope_Coverage_bp",
    "RE_LINE_Coverage_bp", "RE_SINE_Coverage_bp", "RE_LTR_Coverage_bp",
    "RE_Other_Coverage_bp", "RE_Unclassified_Coverage_bp", "RE_Genome_Size_bp",
    "rRNA_18S_N", "rRNA_18S_partial_N", "rRNA_28S_N", "rRNA_28S_partial_N",
    "rRNA_5.8S_N", "rRNA_5.8S_partial_N", "rRNA_5S_N", "rRNA_5S_partial_N",
    "tRNA_gene_N", "tRNA_pseudogene_N", "tRNA_exon_N",
    # Gene model annotation
    "Gene_Model_Annotation_Version",
    "Gene_Models (N)", "Transcript_Models (N)", "CDS_Models (N)", "Exons (N)",
    "UTR5' (N)", "UTR3' (N)", "Both sides UTR' (N)", "Overlapping_Gene_Models (N)",
    "Single Exon Gene Models (N)", "Single Exon Transcripts (N)",
    "Total Gene Space (Mb)", "Mean Gene Model Length (bp)", "Mean CDS Model Length (bp)",
    "Mean Exon Length (bp)", "Mean Intron Length (bp)",
    "Longest Gene Model Length (bp)", "Longest CDS Model Length (bp)", "Longest Intron Length (bp)",
    "Shortest Gene Model Length (bp)", "Shortest CDS Model Length (bp)", "Shortest Intron Length (bp)",
    "Models with early STOP", "Models START missing", "Models STOP missing", "Models START & STOP missing",
    "Annotation_BUSCO_viridiplantae_odb10", "Annotation_BUSCO_embryophyta_odb10",
    "PSAURON SCORE", "DETENGA_FPV", "DETENGA_FP%",
    "OMArk Consistency Results", "OMArk Completeness Results", "OMArk Species Composition",
    "ProteinsWithTREMBLHits (%)", "ProteinsWithSWISSPROTHits (%)",
]


def _round_value(v) -> str:
    """Round a decimal string to 2 dp; leave integers and non-numerics unchanged."""
    if not isinstance(v, str) or "." not in v:
        return v
    try:
        return str(round(float(v), 2))
    except (ValueError, TypeError):
        return v


# ── rDNA / tRNA log parser ────────────────────────────────────────────────────

def parse_rdna_log(log_path: Path) -> dict:
    """Extract counts from the SUMMARY section of a Barrnap+tRNAscan log."""
    result = {
        "rRNA_18S_N":          0,
        "rRNA_18S_partial_N":  0,
        "rRNA_28S_N":          0,
        "rRNA_28S_partial_N":  0,
        "rRNA_5.8S_N":         0,
        "rRNA_5.8S_partial_N": 0,
        "rRNA_5S_N":           0,
        "rRNA_5S_partial_N":   0,
        "tRNA_gene_N":         0,
        "tRNA_pseudogene_N":   0,
        "tRNA_exon_N":         0,
    }

    in_summary = False
    with open(log_path) as fh:
        for line in fh:
            if "SUMMARY" in line and "===" in line:
                in_summary = True
                continue
            if not in_summary:
                continue

            m = re.match(r"\s*(\d+)\s+product=(.+)", line)
            if m:
                count, product = int(m.group(1)), m.group(2).strip()
                mapping = {
                    "18S ribosomal RNA":            "rRNA_18S_N",
                    "18S ribosomal RNA (partial)":  "rRNA_18S_partial_N",
                    "28S ribosomal RNA":            "rRNA_28S_N",
                    "28S ribosomal RNA (partial)":  "rRNA_28S_partial_N",
                    "5.8S ribosomal RNA":           "rRNA_5.8S_N",
                    "5.8S ribosomal RNA (partial)": "rRNA_5.8S_partial_N",
                    "5S ribosomal RNA":             "rRNA_5S_N",
                    "5S ribosomal RNA (partial)":   "rRNA_5S_partial_N",
                }
                if product in mapping:
                    result[mapping[product]] = count
                continue

            m = re.match(r"\s*(\d+)\s+tRNA\b", line)
            if m:
                result["tRNA_gene_N"] = int(m.group(1))
                continue

            m = re.match(r"\s*(\d+)\s+pseudogene\b", line)
            if m:
                result["tRNA_pseudogene_N"] = int(m.group(1))
                continue

            m = re.match(r"\s*(\d+)\s+exon\b", line)
            if m:
                result["tRNA_exon_N"] = int(m.group(1))
                continue

    return result


# ── Output handling ───────────────────────────────────────────────────────────

def load_existing(output_path: Path) -> dict:
    """Load an existing output TSV as a dict keyed by gene_annotation_name."""
    df = pd.read_csv(output_path, sep="\t", dtype=str)
    if "gene_annotation_name" not in df.columns:
        raise ValueError(
            f"{output_path}: missing 'gene_annotation_name' column — cannot update"
        )
    return {str(row["gene_annotation_name"]): row.to_dict() for _, row in df.iterrows()}


def write_output(rows: dict, output_path: Path) -> None:
    df = pd.DataFrame(list(rows.values()))
    # Apply rounding to decimal-valued cells
    df = df.map(_round_value)
    # Reorder columns: known columns first (in defined order), then any extras
    known = [c for c in _COLUMN_ORDER if c in df.columns]
    extras = [c for c in df.columns if c not in _COLUMN_ORDER]
    df = df[known + extras]
    df.to_csv(output_path, sep="\t", index=False)
    log.info(f"Written {len(df)} rows to {output_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Collect annotation QC stats into a combined TSV for Phytolaeno"
    )
    parser.add_argument("--manifest", required=True,
                        help="Manifest TSV (see module docstring for column spec)")
    parser.add_argument("--output", required=True,
                        help="Output TSV path (created if absent, updated if present)")
    args = parser.parse_args()

    manifest = pd.read_csv(args.manifest, sep="\t", comment="#", dtype=str)
    required = {"gene_annotation_name", "gaqet_dir"}
    missing = required - set(manifest.columns)
    if missing:
        log.error(f"Manifest is missing required columns: {missing}")
        sys.exit(1)

    output_path = Path(args.output)
    existing: dict = {}
    if output_path.exists():
        existing = load_existing(output_path)
        log.info(f"Loaded {len(existing)} existing rows from {output_path}")

    n_ok = n_fail = 0

    for _, mrow in manifest.iterrows():
        label = str(mrow.get("gene_annotation_name", "?"))
        try:
            gaqet_dir = Path(str(mrow["gaqet_dir"]).strip())
            if not gaqet_dir.exists():
                raise FileNotFoundError(f"gaqet_dir not found: {gaqet_dir}")

            annotationqc_dir = find_latest_annotationqc(gaqet_dir)
            log.info(f"{label}: using {annotationqc_dir.name}")

            row = parse_gaqet_stats(annotationqc_dir)

            # Rename Annotation_Version to Gene_Model_Annotation_Version
            if "Annotation_Version" in row:
                row["Gene_Model_Annotation_Version"] = row.pop("Annotation_Version")

            # Identity fields from manifest
            row["species_name"]            = str(mrow.get("species_name", ""))
            row["assembly_name"]           = str(mrow.get("assembly_name", ""))
            row["gene_annotation_name"]    = label
            row["repelem_annotation_name"] = str(mrow.get("repelem_annotation_name", ""))

            species_key = label

            # Assembly-level data (BUSCO + QUAST)
            assembly_qc_dir = _opt(mrow.get("assembly_qc_dir"))
            if assembly_qc_dir:
                if assembly_qc_dir.exists():
                    row.update(parse_assembly_busco(assembly_qc_dir))
                    row.update(parse_quast_report(assembly_qc_dir))
                else:
                    log.warning(f"{label}: assembly_qc_dir not found: {assembly_qc_dir}")

            # Repeat composition
            earlgrey_dir = _opt(mrow.get("earlgrey_dir"))
            if earlgrey_dir:
                if earlgrey_dir.exists():
                    row.update(parse_earlgrey(earlgrey_dir))
                else:
                    log.warning(f"{label}: earlgrey_dir not found: {earlgrey_dir}")

            # rDNA / tRNA counts
            rdna_log = _opt(mrow.get("rdna_log"))
            if rdna_log:
                if rdna_log.exists():
                    row.update(parse_rdna_log(rdna_log))
                else:
                    log.warning(f"{label}: rdna_log not found: {rdna_log}")

            action = "updated" if species_key in existing else "added"
            existing[species_key] = row
            log.info(f"{label}: {action} → {species_key}")
            n_ok += 1

        except Exception as exc:
            log.error(f"{label}: FAILED — {exc}")
            n_fail += 1

    write_output(existing, output_path)
    log.info(f"Done: {n_ok} succeeded, {n_fail} failed")


if __name__ == "__main__":
    main()
