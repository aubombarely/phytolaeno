#!/usr/bin/env python3
"""
get_barrnap_summary.py — Summarise a barrnap GFF3 rRNA annotation file.

For each rDNA type found in the file, reports:
    rDNA_type | full_count | partial_count | full_total_length | partial_total_length

A record is considered full when its product attribute does not contain
"(partial)"; partial otherwise.

Usage
-----
    python get_barrnap_summary.py barrnap.gff3
    python get_barrnap_summary.py barrnap.gff3 --format csv
    python get_barrnap_summary.py barrnap.gff3 --format all
    python get_barrnap_summary.py barrnap.gff3 --output my_summary.tsv
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


HEADER = ("rDNA_type", "full_count", "partial_count",
          "full_total_length", "partial_total_length")

FORMAT_EXT = {
    "tsv":  ".summary.tsv",
    "csv":  ".summary.csv",
    "json": ".summary.json",
}


def parse_attributes(attr_str):
    """Return a dict from a GFF3 attribute string (key=value pairs)."""
    attrs = {}
    for field in attr_str.strip().split(";"):
        field = field.strip()
        if "=" in field:
            k, v = field.split("=", 1)
            attrs[k.strip()] = v.strip()
    return attrs


def parse_barrnap_gff3(path):
    """
    Yield (rdna_type, is_partial, length) for each rRNA feature.
    Skips comment/header lines and non-rRNA feature types.
    """
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 9:
                continue
            if parts[2] != "rRNA":
                continue
            start  = int(parts[3])
            end    = int(parts[4])
            length = end - start + 1
            attrs  = parse_attributes(parts[8])
            rdna_type  = attrs.get("Name", "unknown")
            product    = attrs.get("product", "")
            is_partial = "(partial)" in product
            yield rdna_type, is_partial, length


def summarise(path):
    """Return a list of row dicts, one per rDNA type, in order of first occurrence."""
    counts = defaultdict(lambda: {"full_count": 0, "partial_count": 0,
                                  "full_total_length": 0, "partial_total_length": 0})
    order  = []

    for rdna_type, is_partial, length in parse_barrnap_gff3(path):
        if rdna_type not in counts:
            order.append(rdna_type)
        if is_partial:
            counts[rdna_type]["partial_count"]       += 1
            counts[rdna_type]["partial_total_length"] += length
        else:
            counts[rdna_type]["full_count"]       += 1
            counts[rdna_type]["full_total_length"] += length

    return [{"rDNA_type": t, **counts[t]} for t in order]


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
        description="Summarise a barrnap GFF3 rRNA annotation file."
    )
    ap.add_argument("input", type=Path, help="barrnap GFF3 file")
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

    # Print summary table to stderr for quick inspection
    print("\t".join(HEADER), file=sys.stderr)
    for row in rows:
        print("\t".join(str(row[k]) for k in HEADER), file=sys.stderr)


if __name__ == "__main__":
    main()
