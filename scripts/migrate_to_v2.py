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
                                               00_FigshareAnnotation_{doi}_Run01/
    03_AbInitioPredictions/
        00_HELIXER/                     -> 03_Annotations/01_Gene_model_annotations/01_HELIXER_{v}_Run01/
        05_ANNEVO/                      -> 03_Annotations/01_Gene_model_annotations/02_ANNEVO_{v}_Run01/
        99_Comparisons/                 -> 03_Annotations/01_Gene_model_annotations/99_Comparisons/
    10_RepetitiveLandscape/
        02_EarlGrey/                    -> 03_Annotations/00_Repetitive_landscape_annotations/03_EarlGrey_{v}_Run01/
        10_rDNAtDNA/                    -> 03_Annotations/00_Repetitive_landscape_annotations/
                                               01_Barrnap_{v}_Run01/   (moved, tRNAscan files removed)
                                               02_tRNAScanSE_{v}_Run01/ (copied, barrnap files removed)

Pre-move cleanup and post-move reporting performed automatically:
    - AnnotationQCRun* dirs (old GAQET naming) are deleted
    - AnnotationQC_* dirs (new GAQET naming): tool subdirs compressed via gaqet_tgzip.py
    - EarlGrey tool subdirs ({species}_Database, etc.) compressed via earlgrey_tgzip.py
    - AGAT log files (mrna.agat.log, reformatted_annotation.agat.log) are deleted
    - get_barrnap_summary.py run on the GFF3 in 01_Barrnap_*/
    - get_trnascan_summary.py run on the GFF3 in 02_tRNAScanSE_*/

Source directory naming rules
------------------------------
    NCBI_GCA_037074495_1  -> GCA_037074495.1  (last underscore becomes a dot)
    NCBI_GCF_000001405_40 -> GCF_000001405.40
    All other sources     -> kept as-is (e.g. CNCB_GWHBECT00000000, Phytozome_317)

File classification inside each source directory
-------------------------------------------------
    Files whose name starts with the species name -> 02_WorkingFiles/
    All other files                               -> 00_SourceFiles/

Configuration
-------------
    Tool versions and the Figshare DOI are read from directory_mapping.conf
    (same directory as this script). Individual values can be overridden via
    CLI arguments (see --help).

Usage
-----
    # Single accession species
    python migrate_to_v2.py --old_dir ../BySpecies/Acacia_confusa \\
                            --new_dir ./Acacia_confusa

    # Multiple accessions: specify which receives species-level data
    python migrate_to_v2.py --old_dir ../BySpecies/Acacia_confusa \\
                            --new_dir ./Acacia_confusa \\
                            --accession GCA_037074495.1

    # Use a different config file
    python migrate_to_v2.py --old_dir ../BySpecies/Acacia_confusa \\
                            --new_dir ./Acacia_confusa \\
                            --config /path/to/directory_mapping.conf

    # Preview without making changes
    python migrate_to_v2.py --old_dir ../BySpecies/Acacia_confusa \\
                            --new_dir ./Acacia_confusa --dry_run
"""

import argparse
import configparser
import logging
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
DEFAULT_CONFIG = SCRIPTS_DIR / "directory_mapping.conf"

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

TOOL_KEYS = [
    "quast_version",
    "busco_version",
    "helixer_version",
    "annevo_version",
    "barrnap_version",
    "trnascan_version",
    "earlgrey_version",
    "figshare_doi",
]

AGAT_LOG_FILES = [
    "mrna.agat.log",
    "reformatted_annotation.agat.log",
]

BUSCO_RUN_DIRS = [
    "run_viridiplantae_odb10",
    "run_embryophyta_odb10",
]


# ── Local compress helper (no dedicated script for BUSCO runs) ─────────────────

def _compress_dir(path: Path, dry_run: bool) -> None:
    """Compress a directory to {name}.tar.gz in the same parent, then delete it."""
    archive = path.parent / f"{path.name}.tar.gz"
    if dry_run:
        log.info("[DRY] tar czf  %s  &&  rm -rf  %s", archive.name, path.name)
        return
    log.info("Compressing  %s  ->  %s", path.name, archive.name)
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(path, arcname=path.name)
    shutil.rmtree(path)
    log.info("Removed  %s", path.name)


def compress_busco_runs(busco_dir: Path, dry_run: bool) -> None:
    """Compress unarchived BUSCO run dirs (run_viridiplantae_odb10, etc.)."""
    for name in BUSCO_RUN_DIRS:
        path = busco_dir / name
        if path.is_dir():
            _compress_dir(path, dry_run)
        else:
            log.debug("BUSCO run dir not found or already compressed: %s", name)


# ── Config loading ─────────────────────────────────────────────────────────────

def load_config(config_path: Path) -> dict:
    cfg = configparser.ConfigParser()
    if not cfg.read(config_path):
        log.error("Config file not found: %s", config_path)
        sys.exit(1)
    if "tool_versions" not in cfg:
        log.error("[tool_versions] section missing in %s", config_path)
        sys.exit(1)
    return dict(cfg["tool_versions"])


def apply_config(args, config: dict) -> None:
    """Populate any tool key that was not overridden on the CLI from config."""
    for key in TOOL_KEYS:
        if getattr(args, key) is None:
            val = config.get(key)
            if val is None:
                log.error("Missing key '%s' in [tool_versions] of %s", key, args.config)
                sys.exit(1)
            setattr(args, key, val)


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


# ── Pre-move cleanup ───────────────────────────────────────────────────────────

def _run_script(cmd: list, dry_run: bool) -> None:
    if dry_run:
        log.info("[DRY] %s", " ".join(str(c) for c in cmd))
        return
    subprocess.run([sys.executable] + [str(c) for c in cmd], check=True)


def compress_gaqet_runs(parent_dir: Path, dry_run: bool) -> None:
    """Find AnnotationQC_* dirs and compress their tool subdirectories via gaqet_tgzip.py."""
    script = SCRIPTS_DIR / "gaqet_tgzip.py"
    for gaqet_dir in sorted(parent_dir.glob("AnnotationQC_*")):
        if not gaqet_dir.is_dir():
            continue
        log.info("Compressing GAQET run: %s", gaqet_dir.name)
        _run_script([script, "--gaqet_dir", gaqet_dir], dry_run)


def compress_earlgrey(earlgrey_dir: Path, dry_run: bool) -> None:
    """Compress EarlGrey tool subdirectories via earlgrey_tgzip.py.

    Navigates into AnnotationRepeatsEarlGrey/<species>_EarlGrey/ and derives
    the species name from that directory name.
    """
    script = SCRIPTS_DIR / "earlgrey_tgzip.py"
    annotation_dir = earlgrey_dir / "AnnotationRepeatsEarlGrey"
    if not annotation_dir.is_dir():
        log.warning("AnnotationRepeatsEarlGrey not found in %s — skipping EarlGrey compression",
                    earlgrey_dir.name)
        return
    eg_dirs = [d for d in annotation_dir.iterdir()
               if d.is_dir() and d.name.endswith("_EarlGrey")]
    if not eg_dirs:
        log.warning("No *_EarlGrey directory found in %s — skipping", annotation_dir)
        return
    if len(eg_dirs) > 1:
        log.warning("Multiple *_EarlGrey dirs in %s, using: %s", annotation_dir, eg_dirs[0].name)
    eg_dir = eg_dirs[0]
    eg_species = eg_dir.name.removesuffix("_EarlGrey")
    log.info("Compressing EarlGrey dirs for: %s", eg_species)
    _run_script([script, "--earlgrey_dir", eg_dir, "--species_name", eg_species], dry_run)


def remove_agat_logs(parent_dir: Path, dry_run: bool) -> None:
    """Recursively remove AGAT log files from parent_dir."""
    for log_name in AGAT_LOG_FILES:
        for found in sorted(parent_dir.rglob(log_name)):
            log.info("Removing AGAT log: %s", found)
            _delete(found, dry_run)


def run_rna_summary(script_name: str, rna_dir: Path, dry_run: bool) -> None:
    """Find a GFF3 file in rna_dir and run the given summary script on it."""
    script = SCRIPTS_DIR / script_name
    if dry_run:
        log.info("[DRY] %s %s/*.gff3", script.name, rna_dir)
        return
    gff3_files = sorted(rna_dir.glob("*.gff3")) + sorted(rna_dir.glob("*.gff"))
    if not gff3_files:
        log.warning("No GFF3 file found in %s — skipping summary", rna_dir.name)
        return
    if len(gff3_files) > 1:
        log.warning("Multiple GFF3 files in %s, using: %s", rna_dir.name, gff3_files[0].name)
    _run_script([script, gff3_files[0]], False)


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
            compress_busco_runs(item, args.dry_run)
            dst = aqc_dir / f"02_BUSCO_{args.busco_version}_Run01_Viridiplantae_odb10"
            _move(item, dst, args.dry_run)
        elif "busco" in name and ("embryo" in name or "embryophyta" in name):
            compress_busco_runs(item, args.dry_run)
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
                compress_gaqet_runs(item, args.dry_run)
                dst = gm_dir / f"00_FigshareAnnotation_{args.figshare_doi}_Run01"
                _move(item, dst, args.dry_run)
            elif item.name == "busco_downloads":
                log.info("Removing busco_downloads in %s", source_dir.name)
                _delete(item, args.dry_run)
            else:
                log.warning("Unknown subdirectory in source dir, skipping: %s", item.name)
        elif item.is_file():
            dest = classify_file(item.name, species_name)
            target_dir = wk_dir if dest == "02_WorkingFiles" else src_dir
            _move(item, target_dir / item.name, args.dry_run)

    return acc


# ── Species-level migration ────────────────────────────────────────────────────

def migrate_gene_models(old_dir: Path, gm_dir: Path, species_name: str, args) -> None:
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

        compress_gaqet_runs(src, args.dry_run)
        remove_agat_logs(src, args.dry_run)

        _move(src, gm_dir / new_name, args.dry_run)


def migrate_repetitive_landscape(old_dir: Path, re_dir: Path, species_name: str, args) -> None:
    """Migrate 10_RepetitiveLandscape/ -> 00_Repetitive_landscape_annotations/."""
    landscape = old_dir / "10_RepetitiveLandscape"
    if not landscape.is_dir():
        log.warning("10_RepetitiveLandscape not found — skipping repetitive landscape")
        return

    # EarlGrey: compress tool subdirs before moving
    earlgrey_src = landscape / "02_EarlGrey"
    if earlgrey_src.is_dir():
        compress_earlgrey(earlgrey_src, args.dry_run)
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
        _clean_glob(barrnap_dst, "*.fasta",             args.dry_run)
        _clean_glob(barrnap_dst, "*.fasta.gz",          args.dry_run)
        _clean_glob(barrnap_dst, "*tDNA*",              args.dry_run)
        _clean_glob(barrnap_dst, "RuntRNAscan*",        args.dry_run)
        _clean_glob(barrnap_dst, "*trnascan.out.txt",   args.dry_run)
        _clean_glob(barrnap_dst, "*trnascan.stats.txt", args.dry_run)

        log.info("Cleaning tRNAscan dir (removing barrnap-specific files)")
        _clean_glob(trnascan_dst, "*.fasta",    args.dry_run)
        _clean_glob(trnascan_dst, "*.fasta.gz", args.dry_run)
        _clean_glob(trnascan_dst, "*rDNA*",     args.dry_run)

        run_rna_summary("get_barrnap_summary.py",  barrnap_dst,  args.dry_run)
        run_rna_summary("get_trnascan_summary.py", trnascan_dst, args.dry_run)


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
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                    help=f"Config file with tool versions (default: {DEFAULT_CONFIG.name})")
    ap.add_argument("--dry_run", action="store_true",
                    help="Preview all operations without touching the filesystem")

    vg = ap.add_argument_group(
        "tool version overrides",
        "Override individual values from --config. All default to None (use config).",
    )
    for key in TOOL_KEYS:
        vg.add_argument(f"--{key}", default=None, metavar="VALUE",
                        help=f"Override {key} from config")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    config = load_config(args.config)
    apply_config(args, config)

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

    migrate_gene_models(args.old_dir, gm_dir, species_name, args)
    migrate_repetitive_landscape(args.old_dir, re_dir, species_name, args)

    log.info("Done.")


if __name__ == "__main__":
    main()
