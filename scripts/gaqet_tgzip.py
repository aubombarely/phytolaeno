#!/usr/bin/env python3
"""
gaqet_tgzip.py — Compress or decompress GAQET tool run directories.

In compress mode (default) each tool subdirectory found inside the given
GAQET output directory is archived to {name}.tar.gz and then deleted.
In decompress mode (--decompress) the process is reversed: each .tar.gz
is extracted and then deleted.

Directories handled:
    AGAT_run, BUSCOCompleteness_run, DETENGA_run,
    DIAMOND_run, OMARK_run, PSAURON_run

Usage
-----
    python gaqet_tgzip.py --gaqet_dir AnnotationQC_20240501/
    python gaqet_tgzip.py --gaqet_dir AnnotationQC_20240501/ --decompress
"""

import argparse
import logging
import shutil
import sys
import tarfile
from pathlib import Path

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

GAQET_TOOL_DIRS = [
    "AGAT_run",
    "BUSCOCompleteness_run",
    "DETENGA_run",
    "DIAMOND_run",
    "OMARK_run",
    "PSAURON_run",
]


def compress_dir(path: Path) -> None:
    archive = path.with_suffix(".tar.gz")  # sibling file, same parent
    log.info("Compressing  %s  ->  %s", path.name, archive.name)
    with tarfile.open(archive, "w:gz") as tf:
        tf.add(path, arcname=path.name)
    shutil.rmtree(path)
    log.info("Removed      %s", path.name)


def decompress_dir(archive: Path) -> None:
    # Strip both .tar.gz suffixes to get the target directory name
    name = archive.name[: -len(".tar.gz")]
    out_dir = archive.parent / name
    log.info("Decompressing  %s  ->  %s", archive.name, name)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(archive.parent)
    archive.unlink()
    log.info("Removed        %s", archive.name)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Compress or decompress GAQET tool run directories."
    )
    ap.add_argument(
        "--gaqet_dir", required=True, type=Path,
        help="GAQET output directory (e.g. AnnotationQC_20240501/ or gaqet_out/)",
    )
    ap.add_argument(
        "--decompress", action="store_true",
        help="Extract previously compressed directories (default: compress)",
    )
    args = ap.parse_args(argv)

    gaqet_dir = args.gaqet_dir
    if not gaqet_dir.is_dir():
        log.error("Directory not found: %s", gaqet_dir)
        sys.exit(1)

    processed = 0
    skipped   = 0

    if args.decompress:
        for name in GAQET_TOOL_DIRS:
            archive = gaqet_dir / f"{name}.tar.gz"
            if archive.exists():
                decompress_dir(archive)
                processed += 1
            else:
                log.debug("Not found, skipping: %s", archive.name)
                skipped += 1
    else:
        for name in GAQET_TOOL_DIRS:
            path = gaqet_dir / name
            if path.is_dir():
                compress_dir(path)
                processed += 1
            else:
                log.debug("Not found, skipping: %s", name)
                skipped += 1

    mode = "decompressed" if args.decompress else "compressed"
    log.info(
        "Done — %d director%s %s, %d skipped.",
        processed, "ies" if processed != 1 else "y", mode, skipped,
    )


if __name__ == "__main__":
    main()
