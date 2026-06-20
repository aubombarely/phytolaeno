#!/usr/bin/env python3
"""
get_trnascan_summary.py — Summarise a tRNAscan-SE GFF3 annotation file.

For each feature type found in the file (tRNA, exon, pseudogene), reports:
    tDNA_type | count | total_length

Usage
-----
    python get_trnascan_summary.py trnascan.gff3
    python get_trnascan_summary.py trnascan.gff3 --format csv
    python get_trnascan_summary.py trnascan.gff3 --format all
    python get_trnascan_summary.py trnascan.gff3 --output my_summary.tsv
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


HEADER = ("tDNA_type", "count", "total_length")

FORMAT_EXT = {
    "tsv":  ".summary.tsv",
    "csv":  ".summary.csv",
    "json": ".summary.json",
}

# Feature types to report; others are silently ignored
FEATURE_TYPES = {"tRNA", "exon", "pseudogene"}


def parse_trnascan_gff3(path):
    """
    Yield (feature_type, length) for each relevant feature.
    Skips comment/header lines and feature types not in FEATURE_TYPES.
    """
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 5:
                continue
            feature = parts[2]
            if feature not in FEATURE_TYPES:
                continue
            start  = int(parts[3])
            end    = int(parts[4])
            length = end - start + 1
            yield feature, length


def summarise(path):
    """Return a list of row dicts, one per feature type, in order of first occurrence."""
    counts = defaultdict(lambda: {"count": 0, "total_length": 0})
    order  = []

    for feature, length in parse_trnascan_gff3(path):
        if feature not in counts:
            order.append(feature)
        counts[feature]["count"]        += 1
        counts[feature]["total_length"] += length

    return [{"tDNA_type": t, **counts[t]} for t in order]


# ── Writers ───────────────────────────────────────────────────────────────────

def write_tsv(rows, path):
    with open(path, "w", newline="") as fh:
        fh.write("\t".join(HEADER) + "\n")
        for row in rows:
            fh.write("\t".join(str(row[k]) for k in HEADER) + "\n")


def write_csv(rows, path):
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows, path):
    with open(path, "w") as fh:
        json.dump(rows, fh, indent=2)
        fh.write("\n")


WRITERS = {"tsv": write_tsv, "csv": write_csv, "json": write_json}


# ── Main ──────────────────────────────────────────────────────────────────────

def default_output(input_path, fmt):
    """Derive default output path from input filename and format."""
    stem = input_path.name
    for ext in (".gff3", ".gff", ".txt"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return input_path.parent / (stem + FORMAT_EXT[fmt])


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Summarise a tRNAscan-SE GFF3 annotation file."
    )
    ap.add_argument("input", type=Path, help="tRNAscan-SE GFF3 file")
    ap.add_argument(
        "--output", type=Path, default=None,
        help=(
            "Output file (default: <input_stem>.summary.{tsv|csv|json}). "
            "Ignored when --format all is used."
        ),
    )
    ap.add_argument(
        "--format", choices=["tsv", "csv", "json", "all"], default="tsv",
        help="Output format (default: tsv). 'all' writes one file per format.",
    )
    args = ap.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    rows = summarise(args.input)

    if args.format == "all":
        for fmt, writer in WRITERS.items():
            out = default_output(args.input, fmt)
            writer(rows, out)
            print(f"Written: {out}")
    else:
        out = args.output or default_output(args.input, args.format)
        WRITERS[args.format](rows, out)
        print(f"Written: {out}")


if __name__ == "__main__":
    main()
