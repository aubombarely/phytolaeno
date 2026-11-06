#!/usr/bin/env python3
"""build_demo_data.py — extract the Phytolaeno demo tables from the benchmark spreadsheet.

Reads the plant annotation benchmark spreadsheet (one row per annotation) and
the collected QUAST assembly metrics, keeps three species (Arabidopsis
thaliana, Oryza sativa, Cucumis sativus) and writes sorted TSVs to --outdir:

    benchmark_3species.tsv   41 annotations + annotation_key, assembly_key,
                             display_name, tool_name, is_reference
    assembly_metrics.tsv     5 assemblies (QUAST-derived fields)
    downloads.tsv            one row per tool run, zenodo_url left empty

    python scripts/build_demo_data.py --xlsx PlantAnnotationBenchmark2025.xlsx \\
        --metrics assembly_metrics_collected.tsv --outdir demo/data
"""
import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

VERSION = "v0.1.0"

SPECIES = ("Arabidopsis_thaliana", "Oryza_sativa", "Cucumis_sativus")

# Both Arabidopsis names refer to the same TAIR10 assembly (confirmed by the user).
ASSEMBLY_ALIASES = {
    "Athaliana_447_Araport11": "TAIR10",
    "TAIR10_chr_all": "TAIR10",
    "Athaliana_447_TAIR10": "TAIR10",
    "ChineseLong_genome_v3": "ChineseLong_v3",
}

# Reference annotations, keyed on Annotation_Version -> display name.
REFERENCE_VERSIONS = {
    "https://doi.org/10.1111/tpj.13415": "Araport11",
    "TAIR10": "TAIR10",
    "TAIR12": "TAIR12",
    "GCF_000001735.4_TAIR10": "RefSeq GCF_000001735.4",
    "osa1_r7": "MSU r7 (osa1_r7)",
    "GCF_034140825.1": "RefSeq GCF_034140825.1",
    "ChineseLong_v3": "ChineseLong v3 (CuGenDB)",
    "GCF_000004075.3": "RefSeq GCF_000004075.3",
}

TOOL_ALIASES = {"Maker3": "MAKER"}

_QUOTE_LINES = [
    "\"The most merciful thing in the world, I think, is the inability",
    " of the human mind to correlate all its contents.\"",
    "          — H.P. Lovecraft, The Call of Cthulhu (1928)",
]


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr)


def _print_quote() -> None:
    width = max(len(line) for line in _QUOTE_LINES) + 4
    _log(f"┌{'─' * width}┐")
    for line in _QUOTE_LINES:
        _log(f"│ {line}{' ' * (width - len(line) - 1)}│")
    _log(f"└{'─' * width}┘")


def tool_name(methodology: str) -> str:
    """Main tool of an Annotation_Methodology string ('GIP:' pipeline first)."""
    text = str(methodology)
    m = re.search(r"GIP:\s*([A-Za-z0-9+]+)", text)
    if m:
        return TOOL_ALIASES.get(m.group(1), m.group(1))
    if re.search(r"STAR.{0,3}StringTie.{0,3}Transdecoder", text, re.I):
        return "StringTie+TD"
    m = re.search(r"(?:AbI|EvP|EVP|EvT|EVT):\s*([A-Za-z0-9+]+)", text)
    return TOOL_ALIASES.get(m.group(1), m.group(1)) if m else text.split()[0]


def display_name(row: pd.Series) -> str:
    version = str(row["Annotation_Version"])
    if version in REFERENCE_VERSIONS:
        return REFERENCE_VERSIONS[version]
    meth = re.sub(r"\s*\[[^\]]*\]\s*$", "", str(row["Annotation_Methodology"]))
    tool = tool_name(meth)
    ver = re.search(rf"{re.escape(tool)}\s+v([\d.]+)", meth, re.I)
    name = f"{tool} v{ver.group(1)}" if ver else tool
    model = re.search(r"v[\d.]+\s+-\s+(.+?)(?:;|$)", meth)          # ANNEVO/Helixer model
    evid = re.search(r"\(([^)]*)\)", meth)                          # protein species / SwissProt
    if model:
        name += f" ({model.group(1).strip()})"
    elif evid:
        name += f" ({evid.group(1).strip()})"
    return name


def build_benchmark_table(xlsx: Path) -> pd.DataFrame:
    df = pd.read_excel(xlsx)
    df = df[df["Species"].isin(SPECIES)].copy()
    df["assembly_key"] = df["Assembly_Version"].map(lambda a: ASSEMBLY_ALIASES.get(a, a))
    df["is_reference"] = df["Annotation_Version"].astype(str).isin(REFERENCE_VERSIONS)
    df["tool_name"] = [("Reference" if ref else tool_name(m))
                       for ref, m in zip(df["is_reference"], df["Annotation_Methodology"])]
    df["display_name"] = df.apply(display_name, axis=1)
    version_key = df["Annotation_Version"].astype(str).map(
        lambda v: REFERENCE_VERSIONS[v] if v.startswith("http") else v)
    df["annotation_key"] = df["Species"] + "|" + df["assembly_key"] + "|" + version_key
    dup = df.duplicated(["assembly_key", "display_name"], keep=False)
    if dup.any():
        raise ValueError(f"Duplicate display names: {df.loc[dup, 'display_name'].tolist()}")
    return df.sort_values(["Species", "assembly_key", "annotation_key"]).reset_index(drop=True)


def build_assembly_metrics(metrics_tsv: Path, assembly_keys: set[str]) -> list[dict]:
    with open(metrics_tsv, newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    out = {}
    for r in rows:
        key = ASSEMBLY_ALIASES.get(r["assembly"], r["assembly"])
        if key in out:          # TAIR10_chr_all duplicates TAIR10
            continue
        out[key] = {"assembly_key": key, "assembly_type": r["type"], "size_bp": r["size_bp"],
                    "n_sequences": r["n_sequences"], "n90_bp": r["n90_bp"], "l90": r["l90"],
                    "ns_per_100kbp": r["ns_per_100kbp"],
                    "total_length_ge10kb": r["total_length_ge10kb"],
                    "plastid": r["plastid"], "mitochondrion": r["mitochondrion"]}
    missing = assembly_keys - set(out)
    if missing:
        raise ValueError(f"No assembly metrics for: {sorted(missing)}")
    return [out[k] for k in sorted(out) if k in assembly_keys]


def _write_tsv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    _print_quote()
    ap = argparse.ArgumentParser(description="Extract the Phytolaeno demo tables.")
    ap.add_argument("--xlsx", type=Path, required=True, help="Benchmark spreadsheet (.xlsx)")
    ap.add_argument("--metrics", type=Path, required=True, help="Collected assembly metrics TSV")
    ap.add_argument("--outdir", type=Path, default=Path("demo/data"), help="Output directory")
    ap.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = ap.parse_args()
    for flag, path in (("--xlsx", args.xlsx), ("--metrics", args.metrics)):
        if not path.exists():
            print(f"ERROR: {flag} not found: {path}", file=sys.stderr)
            sys.exit(1)
    args.outdir.mkdir(parents=True, exist_ok=True)

    bench = build_benchmark_table(args.xlsx.resolve())
    bench.to_csv(args.outdir / "benchmark_3species.tsv", sep="\t", index=False)
    _log(f"benchmark_3species.tsv: {len(bench)} annotations")

    metrics = build_assembly_metrics(args.metrics.resolve(), set(bench["assembly_key"]))
    _write_tsv(metrics, args.outdir / "assembly_metrics.tsv")
    _log(f"assembly_metrics.tsv: {len(metrics)} assemblies")

    downloads = [{"annotation_key": k, "zenodo_url": ""}
                 for k in bench.loc[~bench["is_reference"], "annotation_key"]]
    _write_tsv(downloads, args.outdir / "downloads.tsv")
    _log(f"downloads.tsv: {len(downloads)} tool runs (Zenodo URLs to be filled)")


if __name__ == "__main__":
    main()
