#!/usr/bin/env python3
"""
earlgrey_tgzip.py — Compress or decompress EarlGrey tool run directories.

In compress mode (default) each tool subdirectory found inside the given
EarlGrey output directory is archived to {name}.tar.gz and then deleted.
In decompress mode (--decompress) the process is reversed: each .tar.gz
is extracted and then deleted.

Directories handled (prefix = --species_name):
    {species}_Database
    {species}_RepeatLandscape
    {species}_RepeatMasker_Against_Custom_Library
    {species}_RepeatModeler
    {species}_heliano
    {species}_mergedRepeats
    {species}_strainer

Usage
-----
    python earlgrey_tgzip.py --earlgrey_dir EarlGrey_out/ --species_name Nicotiana_tabacum
    python earlgrey_tgzip.py --earlgrey_dir EarlGrey_out/ --species_name Nicotiana_tabacum --decompress
"""

import argparse
import logging
import shutil
import sys
import tarfile
from pathlib import Path

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

EARLGREY_SUFFIXES = [
    "_Database",
    "_RepeatLandscape",
    "_RepeatMasker_Against_Custom_Library",
    "_RepeatModeler",
    "_heliano",
    "_mergedRepeats",
    "_strainer",
]


def compress_dir(path: Path) -> None:
    archive = path.with_suffix(".tar.gz")
    log.info("Compressing  %s  ->  %s", path.name, archive.name)
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(path, arcname=path.name)
    shutil.rmtree(path)
    log.info("Removed      %s", path.name)


def decompress_dir(archive: Path) -> None:
    name = archive.name[: -len(".tar.gz")]
    log.info("Decompressing  %s  ->  %s", archive.name, name)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(archive.parent)
    archive.unlink()
    log.info("Removed        %s", archive.name)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Compress or decompress EarlGrey tool run directories."
    )
    ap.add_argument(
        "--earlgrey_dir", required=True, type=Path,
        help="EarlGrey output directory",
    )
    ap.add_argument(
        "--species_name", required=True,
        help="Species name used as directory prefix (e.g. Nicotiana_tabacum)",
    )
    ap.add_argument(
        "--decompress", action="store_true",
        help="Extract previously compressed directories (default: compress)",
    )
    args = ap.parse_args(argv)

    earlgrey_dir = args.earlgrey_dir
    if not earlgrey_dir.is_dir():
        log.error("Directory not found: %s", earlgrey_dir)
        sys.exit(1)

    processed = 0
    skipped   = 0

    if args.decompress:
        for suffix in EARLGREY_SUFFIXES:
            archive = earlgrey_dir / f"{args.species_name}{suffix}.tar.gz"
            if archive.exists():
                decompress_dir(archive)
                processed += 1
            else:
                log.debug("Not found, skipping: %s", archive.name)
                skipped += 1
    else:
        for suffix in EARLGREY_SUFFIXES:
            path = earlgrey_dir / f"{args.species_name}{suffix}"
            if path.is_dir():
                compress_dir(path)
                processed += 1
            else:
                log.debug("Not found, skipping: %s", path.name)
                skipped += 1

    mode = "decompressed" if args.decompress else "compressed"
    log.info(
        "Done — %d director%s %s, %d skipped.",
        processed, "ies" if processed != 1 else "y", mode, skipped,
    )


if __name__ == "__main__":
    main()
