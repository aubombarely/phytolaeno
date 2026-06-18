#!/usr/bin/env python3
"""
generate_manifest.py — Phytolaeno manifest generator

Walks a BySpecies/ root directory and auto-discovers analysis outputs for
each annotation, producing a manifest TSV ready for collect_annotation_stats.py.

Expected directory structure under BySpecies/:

    {species_name}/
    ├── 00_GenomeSource/
    │   └── {assembly_id}/
    │       └── AssemblyQC/          ← QUAST + BUSCO
    ├── 03_AbInitioPredictions/
    │   └── {annotation_id}/         ← one row per annotation
    │       └── AnnotationQC_{ts}/   ← GAQET output
    └── 10_RepetitiveLandscape/
        ├── 02_EarlGrey/             ← repeat composition
        └── 10_rDNAtDNA/             ← rDNA/tRNA log

One manifest row is produced per annotation directory found under
03_AbInitioPredictions/. Optional fields are left blank when not found;
a warning is logged when more than one candidate exists for a field that
expects a single value (assembly_qc_dir, earlgrey_dir, rdna_log).

Usage:
    python generate_manifest.py --root /path/to/BySpecies --output manifest.tsv

    # Limit to specific species:
    python generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \\
        --species Arabidopsis_thaliana Nicotiana_benthamiana
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

MANIFEST_COLUMNS = [
    "species_label",
    "gaqet_dir",
    "assembly_qc_dir",
    "earlgrey_dir",
    "rdna_log",
    "re_annotation_version",
]


# ── Discovery helpers ─────────────────────────────────────────────────────────

def _pick_one(candidates: list[Path], label: str, context: str) -> str:
    """Return the single candidate path as a string, or blank with a warning."""
    if not candidates:
        return ""
    if len(candidates) > 1:
        log.warning(
            f"{context}: found {len(candidates)} candidates for {label}, "
            f"expected 1 — leaving blank. Candidates:\n"
            + "\n".join(f"  {p}" for p in candidates)
        )
        return ""
    return str(candidates[0])


def find_assembly_qc(species_dir: Path) -> str:
    """Find AssemblyQC/ directories across all assembly subdirs."""
    genome_source = species_dir / "00_GenomeSource"
    if not genome_source.is_dir():
        log.warning(f"{species_dir.name}: 00_GenomeSource not found")
        return ""
    candidates = [
        d / "AssemblyQC"
        for d in genome_source.iterdir()
        if d.is_dir() and (d / "AssemblyQC").is_dir()
    ]
    return _pick_one(candidates, "AssemblyQC", species_dir.name)


def find_earlgrey(species_dir: Path) -> str:
    """Find EarlGrey summaryFiles directories under 10_RepetitiveLandscape/02_EarlGrey/."""
    eg_root = species_dir / "10_RepetitiveLandscape" / "02_EarlGrey"
    if not eg_root.is_dir():
        return ""
    # summaryFiles dirs are typically nested a few levels deep
    candidates = list(eg_root.rglob("*_summaryFiles"))
    if not candidates:
        # Fallback: any dir containing *.highLevelCount.txt
        candidates = list({
            f.parent for f in eg_root.rglob("*.highLevelCount.txt")
        })
    return _pick_one(candidates, "EarlGrey summaryFiles", species_dir.name)


def find_rdna_log(species_dir: Path) -> str:
    """Find rDNA/tRNA log files under 10_RepetitiveLandscape/10_rDNAtDNA/."""
    rdna_root = species_dir / "10_RepetitiveLandscape" / "10_rDNAtDNA"
    if not rdna_root.is_dir():
        return ""
    candidates = list(rdna_root.glob("*.log"))
    return _pick_one(candidates, "rDNA log", species_dir.name)


def find_annotation_dirs(species_dir: Path) -> list[Path]:
    """Return all annotation directories under 03_AbInitioPredictions/."""
    predictions_dir = species_dir / "03_AbInitioPredictions"
    if not predictions_dir.is_dir():
        log.warning(f"{species_dir.name}: 03_AbInitioPredictions not found")
        return []
    annotation_dirs = [d for d in sorted(predictions_dir.iterdir()) if d.is_dir()]
    if not annotation_dirs:
        log.warning(f"{species_dir.name}: no annotation directories found in 03_AbInitioPredictions")
    return annotation_dirs


def has_annotationqc(annotation_dir: Path) -> bool:
    """Return True if at least one AnnotationQC_* directory exists."""
    return any(annotation_dir.glob("AnnotationQC_*"))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a collect_annotation_stats.py manifest from a BySpecies/ root"
    )
    parser.add_argument("--root", required=True,
                        help="Path to the BySpecies/ root directory")
    parser.add_argument("--output", required=True,
                        help="Output manifest TSV path")
    parser.add_argument("--species", nargs="+", metavar="SPECIES",
                        help="Limit to these species directory names (optional)")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        log.error(f"Root directory not found: {root}")
        sys.exit(1)

    species_dirs = sorted(
        d for d in root.iterdir() if d.is_dir()
    )
    if args.species:
        requested = set(args.species)
        species_dirs = [d for d in species_dirs if d.name in requested]
        found = {d.name for d in species_dirs}
        missing = requested - found
        if missing:
            log.warning(f"Species not found in root: {', '.join(sorted(missing))}")

    rows = []
    n_species = n_annotations = n_warnings = 0

    for species_dir in species_dirs:
        n_species += 1
        species_name = species_dir.name

        # Discover species-level data once
        assembly_qc = find_assembly_qc(species_dir)
        earlgrey = find_earlgrey(species_dir)
        rdna_log = find_rdna_log(species_dir)

        annotation_dirs = find_annotation_dirs(species_dir)

        for ann_dir in annotation_dirs:
            if not has_annotationqc(ann_dir):
                log.warning(
                    f"{species_name}/{ann_dir.name}: no AnnotationQC_* directory found — skipping"
                )
                n_warnings += 1
                continue

            species_label = f"{species_name}_{ann_dir.name}"
            rows.append({
                "species_label":             species_label,
                "gaqet_dir":                 str(ann_dir),
                "assembly_qc_dir":           assembly_qc,
                "earlgrey_dir":              earlgrey,
                "rdna_log":                  rdna_log,
                "re_annotation_version":     "",
            })
            log.info(f"Added: {species_label}")
            n_annotations += 1

    if not rows:
        log.error("No annotation directories found — manifest not written")
        sys.exit(1)

    df = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    df.to_csv(args.output, sep="\t", index=False)
    log.info(
        f"Done: {n_species} species, {n_annotations} annotations, "
        f"{n_warnings} warnings → {args.output}"
    )


if __name__ == "__main__":
    main()
