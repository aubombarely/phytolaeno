#!/usr/bin/env python3
"""
migrate_to_v2.py — Migrate a species directory from Phytolaeno v1 to v2 layout.

Old layout (BySpecies/{species}/):
    00_GenomeSource/{source_dir}/
        {accession}_*.fna / *.fasta     -> 01_Genomes/{acc}/00_SourceFiles/
        {species}_*.fasta / *.gz / ...  -> 01_Genomes/{acc}/02_WorkingFiles/
        AssemblyQC/*.quast/             -> 01_Genomes/{acc}/01_Assembly_QC/01_QUAST_{v}_Run01/
        AssemblyQC/*.busco.viridi*/     -> 01_Genomes/{acc}/01_Assembly_QC/02_BUSCO_{v}_Run01_Viridiplantae_odb10/
        AssemblyQC/*.busco.embryo*/     -> 01_Genomes/{acc}/01_Assembly_QC/02_BUSCO_{v}_Run02_Embryophyta_odb10/
        FigshareAnnotation/             -> 01_Genomes/{acc}/03_Annotations/01_Gene_model_annotations/
                                               00_FigshareAnnotation_{v}_Run01/
    03_AbInitioPredictions/
        00_HELIXER/                     -> 03_Annotations/01_Gene_model_annotations/01_HELIXER_{v}_Run01/
        05_ANNEVO/                      -> 03_Annotations/01_Gene_model_annotations/02_ANNEVO_{v}_Run01/
        99_Comparisons/                 -> 03_Annotations/01_Gene_model_annotations/99_Comparisons/
    10_RepetitiveLandscape/
        02_EarlGrey/                    -> 03_Annotations/00_Repetitive_landscape_annotations/03_EarlGrey_{v}_Run01/
        10_rDNAtDNA/                    -> 03_Annotations/00_Repetitive_landscape_annotations/
                                               01_Barrnap_{v}_Run01/   (moved, tRNAscan files removed)
                                               02_tRNAScanSE_{v}_Run01/ (copied, barrnap files removed)

Source directory naming rules
------------------------------
    NCBI_GCA_037074495_1  -> GCA_037074495.1  (last underscore becomes a dot)
    NCBI_GCF_000001405_40 -> GCF_000001405.40
    All other sources     -> kept as-is (e.g. CNCB_GWHBECT00000000, Phytozome_317)

File classification inside each source directory
-------------------------------------------------
    Files whose name starts with the species name -> 02_WorkingFiles/
    All other files                               -> 00_SourceFiles/

Usage
-----
    # Single accession species
    python migrate_to_v2.py --old_dir ../BySpecies/Acacia_confusa \\
                            --new_dir ./Acacia_confusa

    # Multiple accessions: specify which receives species-level data
    python migrate_to_v2.py --old_dir ../BySpecies/Acacia_confusa \\
                            --new_dir ./Acacia_confusa \\
                            --accession GCA_037074495.1

    # Preview without making changes
    python migrate_to_v2.py --old_dir ../BySpecies/Acacia_confusa \\
                            --new_dir ./Acacia_confusa --dry_run
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# Default tool versions used in destination directory names
TOOL_DEFAULTS = {
    "quast_version":    "v5.2.0",
    "busco_version":    "v5.6.1",
    "helixer_version":  "v0.3.4",
    "annevo_version":   "v2.2",
    "barrnap_version":  "v0.9",
    "trnascan_version": "v2.0.12",
    "earlgrey_version": "v5.1.1",
    "figshare_version": "v1",
}


# ── Low-level file operations ──────────────────────────────────────────────────

def _move(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        log.info("[DRY] mv  %s  ->  %s", src, dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    log.info("mv  %s  ->  %s", src.name, dst)


def _copy(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        log.info("[DRY] cp -r  %s  ->  %s", src, dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(src), str(dst))
    log.info("cp -r  %s  ->  %s", src.name, dst)


def _delete(path: Path, dry_run: bool) -> None:
    if dry_run:
        log.info("[DRY] rm -rf  %s", path)
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.is_file():
        path.unlink()
    log.info("rm  %s", path)


def _clean_glob(directory: Path, pattern: str, dry_run: bool) -> None:
    """Remove all files/dirs matching pattern inside directory."""
    for p in directory.glob(pattern):
        _delete(p, dry_run)


def _purge_old_qc_runs(directory: Path, dry_run: bool) -> None:
    """Delete old-format AnnotationQCRun* dirs (pre-GAQET2 naming)."""
    for d in list(directory.iterdir()):
        if d.is_dir() and d.name.startswith("AnnotationQCRun"):
            log.info("Removing old QC run dir: %s", d.name)
            _delete(d, dry_run)


# ── Accession ID helpers ───────────────────────────────────────────────────────

def ncbi_dir_to_accession(ncbi_dir_name: str) -> str:
    """Convert NCBI_GCA_037074495_1 -> GCA_037074495.1"""
    name = ncbi_dir_name.removeprefix("NCBI_")
    idx  = name.rfind("_")
    return name[:idx] + "." + name[idx + 1:]


def dir_name_to_accession(dir_name: str) -> str:
    """Return the v2 accession directory name for a given source directory name."""
    if dir_name.startswith("NCBI_"):
        return ncbi_dir_to_accession(dir_name)
    return dir_name


def classify_file(filename: str, species_name: str) -> str:
    """Return '00_SourceFiles' or '02_WorkingFiles' based on file naming."""
    if filename.startswith(species_name):
        return "02_WorkingFiles"
    return "00_SourceFiles"


# ── Per-accession migration ────────────────────────────────────────────────────

def migrate_assembly_qc(assembly_qc: Path, aqc_dir: Path, args) -> None:
    """Move QUAST and BUSCO directories into 01_Assembly_QC/."""
    for item in sorted(assembly_qc.iterdir()):
        if not item.is_dir():
            continue
        name = item.name.lower()
        if name.endswith(".quast"):
            dst = aqc_dir / f"01_QUAST_{args.quast_version}_Run01"
            _move(item, dst, args.dry_run)
        elif "busco" in name and ("viridi" in name or "viridiplantae" in name):
            dst = aqc_dir / f"02_BUSCO_{args.busco_version}_Run01_Viridiplantae_odb10"
            _move(item, dst, args.dry_run)
        elif "busco" in name and ("embryo" in name or "embryophyta" in name):
            dst = aqc_dir / f"02_BUSCO_{args.busco_version}_Run02_Embryophyta_odb10"
            _move(item, dst, args.dry_run)
        else:
            log.warning("Unrecognised AssemblyQC item, skipping: %s", item.name)


def migrate_source_dir(source_dir: Path, new_genomes: Path, species_name: str, args) -> str:
    """
    Migrate one source directory from 00_GenomeSource/. Returns the resolved accession ID.
    """
    acc = dir_name_to_accession(source_dir.name)
    log.info("── Accession: %s ──", acc)

    v2_acc  = new_genomes / acc
    src_dir = v2_acc / "00_SourceFiles"
    aqc_dir = v2_acc / "01_Assembly_QC"
    wk_dir  = v2_acc / "02_WorkingFiles"
    gm_dir  = v2_acc / "03_Annotations" / "01_Gene_model_annotations"

    if not args.dry_run:
        for d in [src_dir, aqc_dir, wk_dir, gm_dir]:
            d.mkdir(parents=True, exist_ok=True)

    for item in sorted(source_dir.iterdir()):
        if item.is_dir():
            if item.name == "AssemblyQC":
                migrate_assembly_qc(item, aqc_dir, args)
            elif item.name == "FigshareAnnotation":
                _purge_old_qc_runs(item, args.dry_run)
                dst = gm_dir / f"00_FigshareAnnotation_{args.figshare_version}_Run01"
                _move(item, dst, args.dry_run)
            else:
                log.warning("Unknown subdirectory in source dir, skipping: %s", item.name)
        elif item.is_file():
            dest = classify_file(item.name, species_name)
            target_dir = wk_dir if dest == "02_WorkingFiles" else src_dir
            _move(item, target_dir / item.name, args.dry_run)

    return acc


# ── Species-level migration ────────────────────────────────────────────────────

def migrate_gene_models(old_dir: Path, gm_dir: Path, args) -> None:
    """Migrate 03_AbInitioPredictions/ -> 01_Gene_model_annotations/."""
    predictions = old_dir / "03_AbInitioPredictions"
    if not predictions.is_dir():
        log.warning("03_AbInitioPredictions not found — skipping gene models")
        return

    tool_map = {
        "00_HELIXER":     f"01_HELIXER_{args.helixer_version}_Run01",
        "05_ANNEVO":      f"02_ANNEVO_{args.annevo_version}_Run01",
        "99_Comparisons": "99_Comparisons",
    }

    for old_name, new_name in tool_map.items():
        src = predictions / old_name
        if not src.is_dir():
            log.debug("Not found, skipping: %s", old_name)
            continue
        _purge_old_qc_runs(src, args.dry_run)
        busco_dl = src / "busco_downloads"
        if busco_dl.is_dir():
            log.info("Removing busco_downloads in %s", old_name)
            _delete(busco_dl, args.dry_run)
        _move(src, gm_dir / new_name, args.dry_run)


def migrate_repetitive_landscape(old_dir: Path, re_dir: Path, args) -> None:
    """Migrate 10_RepetitiveLandscape/ -> 00_Repetitive_landscape_annotations/."""
    landscape = old_dir / "10_RepetitiveLandscape"
    if not landscape.is_dir():
        log.warning("10_RepetitiveLandscape not found — skipping repetitive landscape")
        return

    # EarlGrey
    earlgrey_src = landscape / "02_EarlGrey"
    if earlgrey_src.is_dir():
        _move(earlgrey_src,
              re_dir / f"03_EarlGrey_{args.earlgrey_version}_Run01",
              args.dry_run)

    # rDNAtDNA -> Barrnap dir (move) + tRNAscan dir (copy with cleanup)
    rdna_src = landscape / "10_rDNAtDNA"
    if rdna_src.is_dir():
        barrnap_dst  = re_dir / f"01_Barrnap_{args.barrnap_version}_Run01"
        trnascan_dst = re_dir / f"02_tRNAScanSE_{args.trnascan_version}_Run01"

        _move(rdna_src, barrnap_dst, args.dry_run)
        _copy(barrnap_dst, trnascan_dst, args.dry_run)

        log.info("Cleaning barrnap dir (removing tRNAscan-specific files)")
        _clean_glob(barrnap_dst, "*.fasta",      args.dry_run)
        _clean_glob(barrnap_dst, "*.fasta.gz",   args.dry_run)
        _clean_glob(barrnap_dst, "*tDNA*",       args.dry_run)
        _clean_glob(barrnap_dst, "RuntRNAscan*", args.dry_run)

        log.info("Cleaning tRNAscan dir (removing barrnap-specific files)")
        _clean_glob(trnascan_dst, "*.fasta",    args.dry_run)
        _clean_glob(trnascan_dst, "*.fasta.gz", args.dry_run)
        _clean_glob(trnascan_dst, "*rDNA*",     args.dry_run)


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Migrate a species directory from Phytolaeno v1 to v2 layout."
    )
    ap.add_argument("--old_dir",   required=True, type=Path,
                    help="Old v1 species directory (e.g. ../BySpecies/Acacia_confusa)")
    ap.add_argument("--new_dir",   required=True, type=Path,
                    help="New v2 species directory, pre-created by generate_species_dir.py")
    ap.add_argument("--accession", default=None,
                    help="Target accession for species-level data (gene models, repeats). "
                         "Required when multiple source directories are present.")
    ap.add_argument("--dry_run", action="store_true",
                    help="Preview all operations without touching the filesystem")

    vg = ap.add_argument_group("tool versions (used in destination directory names)")
    for key, default in TOOL_DEFAULTS.items():
        vg.add_argument(f"--{key}", default=default, metavar=default,
                        help=f"Default: {default}")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    for path, label in [(args.old_dir, "--old_dir"), (args.new_dir, "--new_dir")]:
        if not path.is_dir():
            log.error("%s not found: %s", label, path)
            sys.exit(1)

    if args.dry_run:
        log.info("[DRY RUN] No files will be moved, copied, or deleted.")

    genome_source = args.old_dir / "00_GenomeSource"
    if not genome_source.is_dir():
        log.error("00_GenomeSource not found in %s", args.old_dir)
        sys.exit(1)

    source_dirs = sorted(d for d in genome_source.iterdir() if d.is_dir())
    if not source_dirs:
        log.error("No source directories found in %s", genome_source)
        sys.exit(1)

    species_name = args.old_dir.name  # e.g. "Acacia_confusa"
    log.info("Species: %s", species_name)

    new_genomes = args.new_dir / "01_Genomes"
    if not args.dry_run:
        new_genomes.mkdir(parents=True, exist_ok=True)

    # Determine target accession for species-level data
    if args.accession:
        target_acc = args.accession
    elif len(source_dirs) == 1:
        target_acc = dir_name_to_accession(source_dirs[0].name)
    else:
        candidates = [dir_name_to_accession(d.name) for d in source_dirs]
        log.error(
            "Multiple accessions found (%s). "
            "Use --accession to specify which one receives species-level data.",
            ", ".join(candidates),
        )
        sys.exit(1)

    # Per-accession migration
    for source_dir in source_dirs:
        migrate_source_dir(source_dir, new_genomes, species_name, args)

    # Species-level migration -> target accession
    log.info("── Species-level data -> %s ──", target_acc)
    target_v2 = new_genomes / target_acc
    gm_dir = target_v2 / "03_Annotations" / "01_Gene_model_annotations"
    re_dir = target_v2 / "03_Annotations" / "00_Repetitive_landscape_annotations"

    if not args.dry_run:
        gm_dir.mkdir(parents=True, exist_ok=True)
        re_dir.mkdir(parents=True, exist_ok=True)

    migrate_gene_models(args.old_dir, gm_dir, args)
    migrate_repetitive_landscape(args.old_dir, re_dir, args)

    log.info("Done.")


if __name__ == "__main__":
    main()
