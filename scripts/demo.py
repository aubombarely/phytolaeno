#!/usr/bin/env python3
"""demo.py — one-command Phytolaeno demo.

Builds a small SQLite database and starts the web portal (no PostgreSQL
server needed). It holds two kinds of records:

* Arabidopsis thaliana — REAL GAQET quality metrics for 17 genome annotations
  (public references and annotation-tool runs) from the GAQET benchmark
  (García-Carpintero et al., in revision), read from
  demo/data/Athaliana_GAQET_benchmark.tsv.
* Eleven other plant species — SYNTHETIC values, generated with
  random.seed(42), to show how the portal compares many genomes.

    python scripts/demo.py                 # build demo DB and serve on :8000
    python scripts/demo.py --port 8080
    python scripts/demo.py --no_serve      # only build the database

For the synthetic species, names and approximate genome sizes are real but
every QC value is invented. A banner on every page and the assembly "source"
field say which records are real and which are synthetic.
"""
import argparse
import csv
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

VERSION = "v0.1.0"

REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_DIR / "demo" / "phytolaeno_demo.db"
GAQET_TABLE = REPO_DIR / "demo" / "data" / "Athaliana_GAQET_benchmark.tsv"
GAQET_SOURCE = "GAQET benchmark (real data; García-Carpintero et al., in revision)"
SYNTHETIC_SOURCE = "synthetic demo data"

_QUOTE_LINES = [
    "\"The most merciful thing in the world, I think, is the inability",
    " of the human mind to correlate all its contents.\"",
    "          — H.P. Lovecraft, The Call of Cthulhu (1928)",
]

# name, NCBI taxid, family, lineage, genome size (Gb), lineage group
SPECIES = [
    ("Citrus sinensis", 2711, "Rutaceae", "eudicots; rosids; Sapindales", 0.33, "eudicot"),
    ("Vitis vinifera", 29760, "Vitaceae", "eudicots; rosids; Vitales", 0.49, "eudicot"),
    ("Solanum lycopersicum", 4081, "Solanaceae", "eudicots; asterids; Solanales", 0.83, "eudicot"),
    ("Nicotiana benthamiana", 4100, "Solanaceae", "eudicots; asterids; Solanales", 2.9, "eudicot"),
    ("Oryza sativa", 4530, "Poaceae", "monocots; commelinids; Poales", 0.39, "monocot"),
    ("Zea mays", 4577, "Poaceae", "monocots; commelinids; Poales", 2.2, "monocot"),
    ("Musa acuminata", 4641, "Musaceae", "monocots; commelinids; Zingiberales", 0.48, "monocot"),
    ("Amborella trichopoda", 13333, "Amborellaceae", "ANA grade; Amborellales", 0.75, "early"),
    ("Picea abies", 3329, "Pinaceae", "gymnosperms; Pinales", 19.6, "early"),
    ("Physcomitrium patens", 3218, "Funariaceae", "bryophytes; mosses", 0.47, "early"),
    ("Marchantia polymorpha", 3197, "Marchantiaceae", "bryophytes; liverworts", 0.23, "early"),
]

# tool, version, kind, BUSCO offset by lineage group
TOOLS = [
    ("ANNEVO", "1.0", "AI", {"eudicot": 0, "monocot": -1, "early": -9}),
    ("Helixer", "0.3.4", "AI", {"eudicot": -1, "monocot": -1, "early": -12}),
    ("Tiberius", "1.1", "AI", {"eudicot": 0, "monocot": -2, "early": -10}),
    ("Braker3", "3.0.8", "evidence", {"eudicot": -2, "monocot": -3, "early": -4}),
    ("EviAnn", "2.0", "evidence", {"eudicot": -1, "monocot": -2, "early": -3}),
]


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr)


def _print_quote() -> None:
    width = max(len(line) for line in _QUOTE_LINES) + 4
    _log(f"┌{'─' * width}┐")
    for line in _QUOTE_LINES:
        _log(f"│ {line}{' ' * (width - len(line) - 1)}│")
    _log(f"└{'─' * width}┘")


def _busco(complete: float, dup_frac: float, rng: random.Random) -> str:
    complete = max(40.0, min(99.5, complete))
    dup = round(complete * dup_frac, 1)
    single = round(complete - dup, 1)
    frag = round(rng.uniform(0.5, 3.0), 1)
    missing = round(max(0.0, 100 - complete - frag), 1)
    return f"C:{complete:.1f}%[S:{single:.1f}%,D:{dup:.1f}%],F:{frag:.1f}%,M:{missing:.1f}%"


def _num(val: str, cast=float):
    try:
        return cast(float(val))
    except (TypeError, ValueError):
        return None


def _tool_and_version(label: str) -> tuple[str, str]:
    """'Helixer v0.3.4 (m:...) (Garcia-Carpintero 2026)' -> ('Helixer', '0.3.4')."""
    tool = label.split()[0]
    m = re.search(r"\bv(\d[\w.]*)", label)
    return tool, (m.group(1) if m else "")


def _assembly_name(fasta: str) -> str:
    name = re.sub(r"\.(fa|fna|fas|fasta)$", "", fasta)
    return name.replace(".softmasked", "")


def load_gaqet_table(db, models, protocols: dict, path: Path) -> dict:
    """Load the real Arabidopsis GAQET metrics (one row per annotation)."""
    from app.utils import parse_busco

    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    sp = models.Species(species_number=0, name="Arabidopsis thaliana", ncbi_taxid=3702,
                        family="Brassicaceae", lineage="eudicots; rosids; Brassicales")
    db.add(sp)
    db.flush()
    assemblies, n_gm = {}, 0
    for rank, r in enumerate(rows, 1):
        asm_name = _assembly_name(r["Assembly_Version"])
        if asm_name not in assemblies:
            asm = models.Assembly(species_id=sp.id, version=asm_name, source=GAQET_SOURCE,
                                  size_gb=0.135, status="real")
            db.add(asm)
            db.flush()
            assemblies[asm_name] = asm
        tool, ver = _tool_and_version(r["Species"])
        if (tool, ver) not in protocols:
            p = models.AnnotationProtocol(tool=tool, tool_version=ver,
                                          notes=f"GAQET benchmark: {r['Species']}")
            db.add(p)
            db.flush()
            protocols[(tool, ver)] = p
        bv = parse_busco(r["Annotation_BUSCO_viridiplantae_odb10"])
        be = parse_busco(r["Annotation_BUSCO_embryophyta_odb10"])
        I, F = (lambda k: _num(r[k], int)), (lambda k: _num(r[k]))
        db.add(models.GeneModelAnnotation(
            assembly_id=assemblies[asm_name].id, protocol_id=protocols[(tool, ver)].id,
            rank=rank, version_label=r["Species"], methodology=r["Species"],
            gene_models_n=I("Gene_Models (N)"), transcript_models_n=I("Transcript_Models (N)"),
            cds_models_n=I("CDS_Models (N)"), exons_n=I("Exons (N)"),
            utr5_n=I("UTR5' (N)"), utr3_n=I("UTR3' (N)"), both_utrs_n=I("Both sides UTR' (N)"),
            overlapping_gene_models_n=I("Overlapping_Gene_Models (N)"),
            single_exon_gene_models_n=I("Single Exon Gene Models (N)"),
            single_exon_transcripts_n=I("Single Exon Transcripts (N)"),
            total_gene_space_mb=F("Total Gene Space (Mb)"),
            mean_gene_model_length_bp=F("Mean Gene Model Length (bp)"),
            mean_cds_length_bp=F("Mean CDS Model Length (bp)"),
            mean_exon_length_bp=F("Mean Exon Length (bp)"),
            mean_intron_length_bp=F("Mean Intron Length (bp)"),
            longest_gene_model_bp=F("Longest Gene Model Length (bp)"),
            longest_cds_bp=F("Longest CDS Model Length (bp)"),
            longest_intron_bp=F("Longest Intron Length (bp)"),
            shortest_gene_model_bp=F("Shortest Gene Model Length (bp)"),
            shortest_cds_bp=F("Shortest CDS Model Length (bp)"),
            shortest_intron_bp=F("Shortest Intron Length (bp)"),
            models_early_stop=I("Models with early STOP"),
            models_start_missing=I("Models START missing"),
            models_stop_missing=I("Models STOP missing"),
            models_start_stop_missing=I("Models START & STOP missing"),
            busco_viridi_raw=r["Annotation_BUSCO_viridiplantae_odb10"],
            busco_viridi_complete=bv.get("complete"), busco_viridi_single=bv.get("single"),
            busco_viridi_duplicated=bv.get("duplicated"),
            busco_viridi_fragmented=bv.get("fragmented"), busco_viridi_missing=bv.get("missing"),
            busco_embryo_raw=r["Annotation_BUSCO_embryophyta_odb10"],
            busco_embryo_complete=be.get("complete"), busco_embryo_single=be.get("single"),
            busco_embryo_duplicated=be.get("duplicated"),
            busco_embryo_fragmented=be.get("fragmented"), busco_embryo_missing=be.get("missing"),
            omark_consistency_raw=r["OMArk Consistency Results"],
            omark_completeness_raw=r["OMArk Completeness Results"],
            omark_species_composition=r["OMArk Species Composition"],
            psauron_score=F("PSAURON SCORE"),
            detenga_fpv_raw=r["DETENGA_FPV"], detenga_fp_pct_raw=r["DETENGA_FP%"],
            proteins_trembl_pct=F("ProteinsWithTREMBLHits (%)"),
            proteins_swissprot_pct=F("ProteinsWithSWISSPROTHits (%)"),
        ))
        n_gm += 1
    return {"species": 1, "assemblies": len(assemblies), "gm": n_gm}


def build_demo_db(rng: random.Random) -> dict:
    """Populate the (empty) database that app.database points to."""
    from app import models
    from app.database import Base, SessionLocal, engine
    from app.utils import parse_busco

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    counts = {"species": 0, "assemblies": 0, "gm": 0, "re": 0}
    try:
        protocols = {}
        for tool, ver, _, _ in TOOLS + [("EarlGrey", "4.4.0", "", {}),
                                        ("Barrnap", "0.9", "", {}),
                                        ("tRNAscan-SE", "2.0.12", "", {})]:
            p = models.AnnotationProtocol(tool=tool, tool_version=ver,
                                          notes="Demo protocol (synthetic data).")
            db.add(p)
            protocols[tool] = p
        db.flush()

        real = load_gaqet_table(db, models, {}, GAQET_TABLE)
        counts["real_gm"] = real["gm"]
        counts["real_assemblies"] = real["assemblies"]

        for i, (name, taxid, family, lineage, size_gb, group) in enumerate(SPECIES, 1):
            sp = models.Species(species_number=i, name=name, ncbi_taxid=taxid,
                                family=family, lineage=lineage)
            db.add(sp)
            db.flush()
            dup_frac = 0.25 if name in ("Nicotiana benthamiana", "Zea mays") else 0.05
            asm_busco = _busco(rng.uniform(95, 99) - (3 if group == "early" else 0),
                               dup_frac, rng)
            ab = parse_busco(asm_busco)
            code = "".join(w[:2] for w in name.split())
            asm = models.Assembly(
                species_id=sp.id, version=f"{code}_demo_v1", source=SYNTHETIC_SOURCE,
                size_gb=size_gb, status="synthetic",
                busco_viridi_raw=asm_busco,
                busco_viridi_complete=ab["complete"], busco_viridi_single=ab["single"],
                busco_viridi_duplicated=ab["duplicated"],
                busco_viridi_fragmented=ab["fragmented"], busco_viridi_missing=ab["missing"],
            )
            db.add(asm)
            db.flush()
            counts["species"] += 1
            counts["assemblies"] += 1

            base_genes = rng.randint(24000, 36000) * (2 if dup_frac > 0.2 else 1)
            for rank, (tool, ver, kind, offset) in enumerate(TOOLS, 1):
                busco_c = ab["complete"] - rng.uniform(0.5, 3.0) + offset[group]
                raw = _busco(busco_c, dup_frac, rng)
                b = parse_busco(raw)
                genes = int(base_genes * rng.uniform(0.9, 1.25))
                transcripts = int(genes * (rng.uniform(1.1, 1.4) if kind == "evidence" else 1.0))
                utr_frac = 0.0 if tool in ("ANNEVO", "Tiberius") else rng.uniform(0.55, 0.85)
                gm = models.GeneModelAnnotation(
                    assembly_id=asm.id, protocol_id=protocols[tool].id, rank=rank,
                    version_label=f"{asm.version}.{tool.lower()}",
                    methodology=f"AbI: {tool} v{ver}",
                    gene_models_n=genes, transcript_models_n=transcripts,
                    cds_models_n=transcripts, exons_n=int(transcripts * rng.uniform(4.5, 5.8)),
                    utr5_n=int(transcripts * utr_frac),
                    utr3_n=int(transcripts * utr_frac * 1.05),
                    both_utrs_n=int(transcripts * utr_frac * 0.9),
                    single_exon_gene_models_n=int(genes * rng.uniform(0.15, 0.3)),
                    total_gene_space_mb=round(genes * rng.uniform(2.2, 3.4) / 1000, 1),
                    mean_gene_model_length_bp=round(rng.uniform(2200, 3600)),
                    mean_cds_length_bp=round(rng.uniform(1050, 1400)),
                    mean_exon_length_bp=round(rng.uniform(210, 320)),
                    mean_intron_length_bp=round(rng.uniform(150, 900)
                                                * (2.5 if group == "early" else 1)),
                    models_start_missing=int(genes * rng.uniform(0.0, 0.02)),
                    models_stop_missing=int(genes * rng.uniform(0.0, 0.02)),
                    busco_viridi_raw=raw,
                    busco_viridi_complete=b["complete"], busco_viridi_single=b["single"],
                    busco_viridi_duplicated=b["duplicated"],
                    busco_viridi_fragmented=b["fragmented"], busco_viridi_missing=b["missing"],
                    psauron_score=round(rng.uniform(88, 97)
                                        - (6 if group == "early" and kind == "AI" else 0), 1),
                    proteins_swissprot_pct=round(rng.uniform(55, 75), 1),
                    proteins_trembl_pct=round(rng.uniform(85, 97), 1),
                    gaqet_plot_area=round(rng.uniform(0.55, 0.85), 3),
                )
                db.add(gm)
                counts["gm"] += 1

            classes = {"DNA": rng.uniform(3, 12), "RC": rng.uniform(0.2, 3),
                       "LTR": rng.uniform(10, 55) * (1.4 if size_gb > 1.5 else 1),
                       "LINE": rng.uniform(0.5, 5), "SINE": rng.uniform(0, 1),
                       "Unclassified": rng.uniform(2, 12)}
            classes = {k: round(v, 2) for k, v in classes.items()}
            total = round(min(92.0, sum(classes.values())), 2)
            raw = ";".join(f"{k}:{v:.2f}%" for k, v in classes.items())
            db.add(models.RepeatAnnotation(assembly_id=asm.id, protocol_id=protocols["EarlGrey"].id,
                                           version_label=asm.version, total_pct=total,
                                           raw_output=raw, parsed_results=classes))
            rdna = f"5S:{rng.randint(5, 400)};5_8S:{rng.randint(1, 30)};18S:{rng.randint(1, 30)};28S:{rng.randint(1, 30)}"
            db.add(models.RepeatAnnotation(assembly_id=asm.id, protocol_id=protocols["Barrnap"].id,
                                           version_label=asm.version, raw_output=rdna,
                                           parsed_results={"raw": rdna}))
            trna = f"tRNA:{rng.randint(450, 1600)}"
            db.add(models.RepeatAnnotation(assembly_id=asm.id, protocol_id=protocols["tRNAscan-SE"].id,
                                           version_label=asm.version, raw_output=trna,
                                           parsed_results={"raw": trna}))
            counts["re"] += 3
        db.commit()
    finally:
        db.close()
    return counts


def main() -> None:
    _print_quote()
    ap = argparse.ArgumentParser(description="Build a synthetic demo database "
                                 "and start the Phytolaeno portal.")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB,
                    help=f"SQLite file to create (default: {DEFAULT_DB.relative_to(REPO_DIR)})")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Host to bind (use 0.0.0.0 in containers/Codespaces)")
    ap.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    ap.add_argument("--no_serve", action="store_true",
                    help="Only build the demo database, do not start the server")
    ap.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = ap.parse_args()

    args.db = args.db.resolve()
    args.db.parent.mkdir(parents=True, exist_ok=True)
    # Must be set before app.database is imported (engine is built at import).
    os.environ["DATABASE_URL"] = f"sqlite:///{args.db}"
    os.environ["PHYTOLAENO_DEMO"] = "1"
    sys.path.insert(0, str(REPO_DIR))

    _log(f"Building demo database: {args.db}")
    counts = build_demo_db(random.Random(42))
    _log(f"  Real (GAQET benchmark): Arabidopsis thaliana, {counts['real_assemblies']} "
         f"assemblies, {counts['real_gm']} gene-model annotations")
    _log(f"  Synthetic: {counts['species']} species, {counts['assemblies']} assemblies, "
         f"{counts['gm']} gene-model and {counts['re']} repeat/ncRNA annotations")
    if args.no_serve:
        return

    import uvicorn
    _log(f"Open http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{args.port} "
         f"— press Ctrl+C to stop")
    uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
