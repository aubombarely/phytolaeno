#!/usr/bin/env python3
"""
generate_manifest.py — Phytolaeno manifest generator

Walks a BySpecies/ root directory and auto-discovers analysis outputs for
each annotation, producing a manifest TSV ready for collect_annotation_stats.py.

Expected directory structure under BySpecies/:

    {species_name}/
    ├── 00_GenomeSource/
    │   └── {assembly_id}/
    │       ├── {species_name}_{accession}_{id}_genome.fasta  ← assembly_name source
    │       └── AssemblyQC/                                   ← QUAST + BUSCO
    ├── 03_AbInitioPredictions/
    │   └── {annotation_id}/         ← one row per annotation
    │       └── AnnotationQC_{ts}/   ← GAQET output
    └── 10_RepetitiveLandscape/
        ├── 02_EarlGrey/             ← repeat composition
        └── 10_rDNAtDNA/             ← rDNA/tRNA log

One manifest row is produced per annotation directory found under
03_AbInitioPredictions/. Naming conventions:
  - assembly_name  : stem of *_genome.fasta (without the _genome.fasta suffix)
  - gene_annotation_name  : {species_name}_{TOOL} (e.g. Arabidopsis_thaliana_HELIXER)
  - repelem_annotation_name: {species_name}_{RE_TOOL} (e.g. Arabidopsis_thaliana_EARLGREY)

If more than one candidate is found for a single-value field the field is
left blank and a warning is written to both the console and a timestamped
warning log file (generate_manifest_warning_{timestamp}.log).

Usage:
    python generate_manifest.py --root /path/to/BySpecies --output manifest.tsv

    # Limit to specific species:
    python generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \\
        --species Arabidopsis_thaliana Nicotiana_benthamiana

    # Custom RE tool priority (default: 02_EarlGrey):
    python generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \\
        --re_landscape_priority 01_RepeatModelerMasker,02_EarlGrey

    # Ignore specific directories during discovery:
    python generate_manifest.py --root /path/to/BySpecies --output manifest.tsv \\
        --ignore_dir 99_Comparison 98_Scratch
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

MANIFEST_COLUMNS = [
    "species_name",
    "assembly_name",
    "assembly_qc_dir",
    "repelem_annotation_name",
    "rdna_log",
    "earlgrey_dir",
    "gene_annotation_name",
    "gaqet_dir",
]


# ── Naming helpers ────────────────────────────────────────────────────────────

def _tool_name(dir_name: str) -> str:
    """Strip leading NN_ numeric prefix and uppercase the remainder.

    Examples: '00_HELIXER' → 'HELIXER', '02_EarlGrey' → 'EARLGREY'
    """
    parts = dir_name.split("_", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1].upper()
    return dir_name.upper()


def _pick_one(candidates: list[Path], label: str, context: str) -> str:
    """Return the single candidate as a string, or blank with a warning."""
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


# ── Discovery helpers ─────────────────────────────────────────────────────────

def find_assembly_info(species_dir: Path, ignore: set[str]) -> tuple[str, str]:
    """Return (assembly_name, assembly_qc_dir).

    assembly_name is the stem of *_genome.fasta (without _genome.fasta suffix).
    Returns ("", "") when ambiguous or required files are missing.
    """
    genome_source = species_dir / "00_GenomeSource"
    if not genome_source.is_dir():
        log.warning(f"{species_dir.name}: 00_GenomeSource not found")
        return "", ""

    assembly_dirs = [d for d in sorted(genome_source.iterdir()) if d.is_dir() and d.name not in ignore]
    if not assembly_dirs:
        log.warning(f"{species_dir.name}: no assembly directories in 00_GenomeSource")
        return "", ""

    if len(assembly_dirs) > 1:
        log.warning(
            f"{species_dir.name}: found {len(assembly_dirs)} assembly directories in "
            f"00_GenomeSource, expected 1 — leaving assembly_name and assembly_qc_dir blank. "
            f"Directories:\n" + "\n".join(f"  {d}" for d in assembly_dirs)
        )
        return "", ""

    assembly_dir = assembly_dirs[0]

    # Derive assembly_name from the renamed *_genome.fasta file
    genome_fastas = list(assembly_dir.glob("*_genome.fasta"))
    if not genome_fastas:
        log.warning(f"{species_dir.name}: no *_genome.fasta found in {assembly_dir}")
        assembly_name = ""
    elif len(genome_fastas) > 1:
        log.warning(
            f"{species_dir.name}: found {len(genome_fastas)} *_genome.fasta files in "
            f"{assembly_dir}, expected 1 — leaving assembly_name blank. Files:\n"
            + "\n".join(f"  {f}" for f in genome_fastas)
        )
        assembly_name = ""
    else:
        fname = genome_fastas[0].name
        assembly_name = fname[: -len("_genome.fasta")] if fname.endswith("_genome.fasta") else genome_fastas[0].stem

    # AssemblyQC directory
    assembly_qc = assembly_dir / "AssemblyQC"
    if assembly_qc.is_dir():
        assembly_qc_dir = str(assembly_qc)
    else:
        log.warning(f"{species_dir.name}: AssemblyQC not found in {assembly_dir}")
        assembly_qc_dir = ""

    return assembly_name, assembly_qc_dir


def find_repelem_tool_name(species_dir: Path, priority: list[str], ignore: set[str]) -> str:
    """Return the RE tool name from 10_RepetitiveLandscape/ (excludes 10_rDNAtDNA).

    When multiple tool directories exist, the first match in *priority* (a list
    of directory names, e.g. ["02_EarlGrey"]) is used.  Falls back to the
    alphabetically first directory if none match, with a warning.

    E.g. 02_EarlGrey → EARLGREY.
    """
    re_root = species_dir / "10_RepetitiveLandscape"
    if not re_root.is_dir():
        return ""
    tool_dirs = [
        d for d in sorted(re_root.iterdir())
        if d.is_dir() and d.name != "10_rDNAtDNA" and d.name not in ignore
    ]
    if not tool_dirs:
        return ""
    if len(tool_dirs) == 1:
        return _tool_name(tool_dirs[0].name)

    tool_dir_names = {d.name: d for d in tool_dirs}
    for preferred in priority:
        if preferred in tool_dir_names:
            log.info(
                f"{species_dir.name}: found {len(tool_dirs)} RE tool directories — "
                f"using priority match: {preferred}"
            )
            return _tool_name(preferred)

    log.warning(
        f"{species_dir.name}: found {len(tool_dirs)} RE tool directories and none "
        f"matched the priority list {priority} — using first: {tool_dirs[0].name}. "
        f"All directories:\n" + "\n".join(f"  {d}" for d in tool_dirs)
    )
    return _tool_name(tool_dirs[0].name)


def find_earlgrey(species_dir: Path) -> str:
    """Find EarlGrey summaryFiles directory under 10_RepetitiveLandscape/02_EarlGrey/."""
    eg_root = species_dir / "10_RepetitiveLandscape" / "02_EarlGrey"
    if not eg_root.is_dir():
        return ""
    candidates = list(eg_root.rglob("*_summaryFiles"))
    if not candidates:
        candidates = list({f.parent for f in eg_root.rglob("*.highLevelCount.txt")})
    return _pick_one(candidates, "EarlGrey summaryFiles", species_dir.name)


def find_rdna_log(species_dir: Path) -> str:
    """Find rDNA/tRNA log file under 10_RepetitiveLandscape/10_rDNAtDNA/."""
    rdna_root = species_dir / "10_RepetitiveLandscape" / "10_rDNAtDNA"
    if not rdna_root.is_dir():
        return ""
    candidates = list(rdna_root.glob("*.log"))
    return _pick_one(candidates, "rDNA log", species_dir.name)


def find_annotation_dirs(species_dir: Path, ignore: set[str]) -> list[Path]:
    """Return all annotation directories under 03_AbInitioPredictions/."""
    predictions_dir = species_dir / "03_AbInitioPredictions"
    if not predictions_dir.is_dir():
        log.warning(f"{species_dir.name}: 03_AbInitioPredictions not found")
        return []
    annotation_dirs = [d for d in sorted(predictions_dir.iterdir()) if d.is_dir() and d.name not in ignore]
    if not annotation_dirs:
        log.warning(f"{species_dir.name}: no annotation directories in 03_AbInitioPredictions")
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
    parser.add_argument("--re_landscape_priority", metavar="DIR1,DIR2,...",
                        default="02_EarlGrey",
                        help="Comma-separated priority list of 10_RepetitiveLandscape "
                             "subdirectory names; the first match is used when multiple "
                             "RE tool directories are present (default: 02_EarlGrey)")
    parser.add_argument("--ignore_dir", nargs="+", metavar="DIR",
                        default=[],
                        help="Directory names to skip during discovery (applied to "
                             "assembly, RE tool, and annotation directories)")
    args = parser.parse_args()
    re_priority  = [d.strip() for d in args.re_landscape_priority.split(",") if d.strip()]
    ignore_dirs  = set(args.ignore_dir)

    # Timestamped warning log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    warn_log_path = Path(f"generate_manifest_warning_{timestamp}.log")
    warn_handler = logging.FileHandler(warn_log_path)
    warn_handler.setLevel(logging.WARNING)
    warn_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    log.addHandler(warn_handler)
    log.info(f"Warnings will also be written to {warn_log_path}")

    root = Path(args.root)
    if not root.is_dir():
        log.error(f"Root directory not found: {root}")
        sys.exit(1)

    species_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    if args.species:
        requested = set(args.species)
        species_dirs = [d for d in species_dirs if d.name in requested]
        found = {d.name for d in species_dirs}
        missing = requested - found
        if missing:
            log.warning(f"Species not found in root: {', '.join(sorted(missing))}")

    rows = []
    n_species = n_annotations = n_skipped = 0

    for species_dir in species_dirs:
        n_species += 1
        species_name = species_dir.name

        assembly_name, assembly_qc_dir = find_assembly_info(species_dir, ignore_dirs)
        re_tool       = find_repelem_tool_name(species_dir, re_priority, ignore_dirs)
        earlgrey      = find_earlgrey(species_dir)
        rdna_log      = find_rdna_log(species_dir)

        for ann_dir in find_annotation_dirs(species_dir, ignore_dirs):
            if not has_annotationqc(ann_dir):
                log.warning(
                    f"{species_name}/{ann_dir.name}: no AnnotationQC_* directory — skipping"
                )
                n_skipped += 1
                continue

            gene_annotation_name   = f"{species_name}_{_tool_name(ann_dir.name)}"
            repelem_annotation_name = f"{species_name}_{re_tool}" if re_tool else ""

            rows.append({
                "species_name":            species_name,
                "assembly_name":           assembly_name,
                "assembly_qc_dir":         assembly_qc_dir,
                "repelem_annotation_name": repelem_annotation_name,
                "rdna_log":                rdna_log,
                "earlgrey_dir":            earlgrey,
                "gene_annotation_name":    gene_annotation_name,
                "gaqet_dir":               str(ann_dir),
            })
            log.info(f"Added: {gene_annotation_name}")
            n_annotations += 1

    if not rows:
        log.error("No annotation directories found — manifest not written")
        sys.exit(1)

    df = pd.DataFrame(rows, columns=MANIFEST_COLUMNS)
    df.to_csv(args.output, sep="\t", index=False)

    # Remove warning log if it is empty
    if warn_log_path.exists() and warn_log_path.stat().st_size == 0:
        warn_log_path.unlink()
        log.info("No warnings — warning log removed")
    else:
        log.info(f"Warnings written to {warn_log_path}")

    log.info(
        f"Done: {n_species} species, {n_annotations} annotations added, "
        f"{n_skipped} skipped → {args.output}"
    )


if __name__ == "__main__":
    main()
