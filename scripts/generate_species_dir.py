#!/usr/bin/env python3
"""
generate_species_dir.py — Set up a species directory skeleton for the Phytolaeno pipeline.

Usage
-----
# Create species skeleton only
python generate_species_dir.py --root /data/BySpecies --species Nicotiana_tabacum

# Create species skeleton + one assembly
python generate_species_dir.py --root /data/BySpecies --species Nicotiana_tabacum \
    --assembly NtK326IBMCPv1

Adds an assembly to an existing species without touching anything already there.
All operations are idempotent.
"""

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

NCBI_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------

SPECIES_DIRS = [
    "00_Taxonomy",
    "01_Genome",
    "02_Transcriptome",
]

ASSEMBLY_DIRS = [
    "00_SourceFiles",
    "01_Assembly_QC",
    "02_WorkingFiles",
    "03_Annotations/00_Repetitive_landscape_annotation",
    "03_Annotations/01_Gene_model_annotation",
]

# ---------------------------------------------------------------------------
# NCBI helpers
# ---------------------------------------------------------------------------

def _ncbi_get(url: str, params: dict) -> bytes:
    full_url = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(full_url, timeout=15) as resp:
        return resp.read()


def fetch_taxonomy(species_name: str) -> dict | None:
    """Return a dict with taxid, rank, division, lineage list; None on failure."""
    query = species_name.replace("_", " ")

    # 1. esearch — get taxid
    try:
        raw = _ncbi_get(NCBI_ESEARCH, {
            "db": "taxonomy", "term": query, "retmode": "json", "retmax": 1
        })
        data = json.loads(raw)
        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            log.warning("No NCBI taxonomy record found for %r", query)
            return None
        taxid = ids[0]
        time.sleep(0.4)  # stay well under 3 req/s
    except Exception as exc:
        log.warning("NCBI esearch failed: %s", exc)
        return None

    # 2. efetch — get full XML lineage
    try:
        raw = _ncbi_get(NCBI_EFETCH, {
            "db": "taxonomy", "id": taxid, "retmode": "xml"
        })
        xml = raw.decode()
        time.sleep(0.4)
    except Exception as exc:
        log.warning("NCBI efetch failed: %s", exc)
        return None

    # Parse what we need from the XML with simple string extraction
    def _tag(tag: str) -> str:
        start = xml.find(f"<{tag}>")
        end   = xml.find(f"</{tag}>")
        if start == -1 or end == -1:
            return ""
        return xml[start + len(tag) + 2 : end].strip()

    rank     = _tag("Rank")
    division = _tag("Division")

    # Lineage string — semicolon-separated names
    lineage_str = _tag("Lineage")
    lineage = [n.strip() for n in lineage_str.split(";") if n.strip()] if lineage_str else []

    return {
        "species":  query,
        "taxid":    int(taxid),
        "rank":     rank,
        "division": division,
        "lineage":  lineage,
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_taxonomy_txt(path: Path, info: dict) -> None:
    lineage_display = " > ".join(info["lineage"])
    # Wrap at 80 chars
    words = lineage_display.split(" > ")
    lines, current = [], ""
    for word in words:
        candidate = current + (" > " if current else "") + word
        if len("         " + candidate) > 79 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    indent = "         "
    lineage_block = f"\n{indent}".join(lines)

    path.write_text(
        f"Species:  {info['species']}\n"
        f"TaxID:    {info['taxid']}\n"
        f"Rank:     {info['rank']}\n"
        f"Division: {info['division']}\n"
        f"Lineage:  {lineage_block}\n"
        f"\nFetched:  {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n"
    )


def write_taxonomy_tsv(path: Path, info: dict) -> None:
    lineage_str = ";".join(info["lineage"])
    rows = [
        ("species",  info["species"]),
        ("taxid",    str(info["taxid"])),
        ("rank",     info["rank"]),
        ("division", info["division"]),
        ("lineage",  lineage_str),
    ]
    path.write_text("field\tvalue\n" + "\n".join(f"{k}\t{v}" for k, v in rows) + "\n")


def write_taxonomy_json(path: Path, info: dict) -> None:
    path.write_text(json.dumps(info, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

def create_dirs(paths: list[Path]) -> None:
    for p in paths:
        if not p.exists():
            p.mkdir(parents=True)
            log.info("Created  %s", p)
        else:
            log.info("Exists   %s", p)


def setup_species(root: Path, species: str) -> Path:
    species_dir = root / species
    create_dirs([species_dir / d for d in SPECIES_DIRS])
    return species_dir


def setup_assembly(species_dir: Path, assembly: str) -> Path:
    assembly_dir = species_dir / "01_Genome" / assembly
    create_dirs([assembly_dir / d for d in ASSEMBLY_DIRS])
    return assembly_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Set up a species directory skeleton for the Phytolaeno pipeline."
    )
    p.add_argument("--root",     required=True,  type=Path, help="BySpecies root directory")
    p.add_argument("--species",  required=True,  help="Species name (e.g. Nicotiana_tabacum)")
    p.add_argument("--assembly", default=None,   help="Assembly name to add (optional)")
    p.add_argument("--no_taxonomy", action="store_true",
                   help="Skip NCBI taxonomy fetch")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if not args.root.is_dir():
        log.error("Root directory does not exist: %s", args.root)
        sys.exit(1)

    # Species skeleton
    species_dir = setup_species(args.root, args.species)

    # Taxonomy
    taxonomy_dir = species_dir / "00_Taxonomy"
    if args.no_taxonomy:
        log.info("Skipping taxonomy fetch (--no_taxonomy)")
    else:
        log.info("Fetching taxonomy from NCBI for %r …", args.species)
        info = fetch_taxonomy(args.species)
        if info:
            write_taxonomy_txt(taxonomy_dir / "taxonomy.txt",  info)
            write_taxonomy_tsv(taxonomy_dir / "taxonomy.tsv",  info)
            write_taxonomy_json(taxonomy_dir / "taxonomy.json", info)
            log.info("Taxonomy written to %s", taxonomy_dir)
        else:
            log.warning("Taxonomy files not written — check species name or NCBI availability")

    # Assembly (optional)
    if args.assembly:
        setup_assembly(species_dir, args.assembly)
        log.info("Assembly directory ready: %s", species_dir / "01_Genome" / args.assembly)

    log.info("Done.")


if __name__ == "__main__":
    main()
