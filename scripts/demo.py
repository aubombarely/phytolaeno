#!/usr/bin/env python3
"""demo.py — one-command Phytolaeno demo with real data.

Builds a small SQLite database from the tables in demo/data/ (extracted from
the KATULU / GAQET plant annotation benchmark by scripts/build_demo_data.py)
and starts the web portal. No PostgreSQL server is needed.

    python scripts/demo.py                 # build demo DB and serve on :8000
    python scripts/demo.py --port 8080
    python scripts/demo.py --no_serve      # only build the database

Contents: Arabidopsis thaliana, Oryza sativa and Cucumis sativus; 5 genome
assemblies and 41 gene-model annotations (public references and the lab's
annotation-tool runs; García-Carpintero et al., in revision).
"""
import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

VERSION = "v0.2.0"

REPO_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_DIR / "demo" / "data"
DEFAULT_DB = REPO_DIR / "demo" / "phytolaeno_demo.db"

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


def _read_tsv(name: str) -> list[dict]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _s(value) -> str | None:
    value = (value or "").strip()
    return value or None


def _f(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _i(value) -> int | None:
    f = _f(value)
    return None if f is None else int(f)


def _busco_fields(prefix: str, raw: str | None, parse_busco) -> dict:
    b = parse_busco(raw or "")
    return {f"{prefix}_raw": raw,
            **{f"{prefix}_{k}": b.get(k) for k in
               ("complete", "single", "duplicated", "fragmented", "missing")}}


def _annotation_fields(r: dict, parse_busco) -> dict:
    """Spreadsheet row -> GeneModelAnnotation column values (same mapping as import_excel)."""
    ints = {"gene_models_n": "Gene_Models (N)", "transcript_models_n": "Transcript_Models (N)",
            "cds_models_n": "CDS_Models (N)", "exons_n": "Exons (N)", "utr5_n": "UTR5' (N)",
            "utr3_n": "UTR3' (N)", "both_utrs_n": "Both sides UTR' (N)",
            "overlapping_gene_models_n": "Overlapping_Gene_Models (N)",
            "single_exon_gene_models_n": "Single Exon Gene Models (N)",
            "single_exon_transcripts_n": "Single Exon Transcripts (N)",
            "models_early_stop": "Models with early STOP",
            "models_start_missing": "Models START missing",
            "models_stop_missing": "Models STOP missing",
            "models_start_stop_missing": "Models START & STOP missing"}
    floats = {"total_gene_space_mb": "Total Gene Space (Mb)",
              "mean_gene_model_length_bp": "Mean Gene Model Length (bp)",
              "mean_cds_length_bp": "Mean CDS Model Length (bp)",
              "mean_exon_length_bp": "Mean Exon Length (bp)",
              "mean_intron_length_bp": "Mean Intron Length (bp)",
              "longest_gene_model_bp": "Longest Gene Model Length (bp)",
              "longest_cds_bp": "Longest CDS Model Length (bp)",
              "longest_intron_bp": "Longest Intron Length (bp)",
              "shortest_gene_model_bp": "Shortest Gene Model Length (bp)",
              "shortest_cds_bp": "Shortest CDS Model Length (bp)",
              "shortest_intron_bp": "Shortest Intron Length (bp)",
              "psauron_score": "PSAURON SCORE",
              "proteins_swissprot_pct": "ProteinsWithSwissprotHits (%)",
              "proteins_trembl_pct": "ProteinsWithTremblHits (%)",
              "gaqet_plot_area": "GAQET_Plot_Area", "f1_score_base": "F1-Score Base",
              "f1_score_locus": "F1-Score Locus", "missed_loci": "Missed Loci",
              "new_loci": "New Loci"}
    texts = {"omark_completeness_raw": "OMArk 2.0.3 Completeness Results",
             "omark_consistency_raw": "OMArk 2.0.3 Consistency Results",
             "omark_species_composition": "OMArk 2.0.3 Species Composition",
             "detenga_fpv_raw": "DETENGA_FPV", "detenga_fp_pct_raw": "DETENGA_FP%"}
    out = {k: _i(r.get(c)) for k, c in ints.items()}
    out.update({k: _f(r.get(c)) for k, c in floats.items()})
    out.update({k: _s(r.get(c)) for k, c in texts.items()})
    out.update(_busco_fields("busco_viridi", _s(r.get("Annotation_BUSCO_ViridiOdb10 (n:425)")), parse_busco))
    out.update(_busco_fields("busco_embryo", _s(r.get("Annotation_BUSCO_EmbryoOdb10 (n:1614)")), parse_busco))
    return out


def build_demo_db() -> dict:
    """Populate the (empty) database that app.database points to from demo/data/."""
    from app import models
    from app.database import Base, SessionLocal, engine
    from app.metrics import gaqet_axes, gas_score
    from app.utils import extract_tool_info, parse_busco, parse_earlgrey

    bench = _read_tsv("benchmark_3species.tsv")
    metrics = {r["assembly_key"]: r for r in _read_tsv("assembly_metrics.tsv")}
    zenodo = {r["annotation_key"]: _s(r["zenodo_url"]) for r in _read_tsv("downloads.tsv")}
    desc = {(r["level"], r["key"]): r for r in _read_tsv("descriptions.tsv")}
    if not bench:
        raise SystemExit(f"ERROR: {DATA_DIR / 'benchmark_3species.tsv'} not found or empty")

    def d(level: str, key: str) -> tuple[str | None, str | None]:
        row = desc.get((level, key), {})
        return _s(row.get("description")), _s(row.get("source_url"))

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    species, assemblies, n_gm, n_re = {}, {}, 0, 0
    try:
        for r in bench:
            sp_name = r["Species"].replace("_", " ")
            if sp_name not in species:
                sdesc, _ = d("species", sp_name)
                sp = models.Species(name=sp_name, species_number=_i(r["SpeciesNumber"]),
                                    ncbi_taxid=_i(r["NCBI_TaxID"]), family=_s(r["Family"]),
                                    lineage=_s(r["Lineage"]), description=sdesc)
                db.add(sp)
                db.flush()
                species[sp_name] = sp

            akey = r["assembly_key"]
            if akey not in assemblies:
                m = metrics.get(akey, {})
                adesc, aurl = d("assembly", akey)
                asm = models.Assembly(
                    species_id=species[sp_name].id, version=akey, source=_s(r["Source"]),
                    # exact QUAST size when available, else the spreadsheet's rounded value
                    size_gb=(_f(m.get("size_bp")) / 1e9 if _f(m.get("size_bp"))
                             else _f(r["Assembly_Size (Gb)"])),
                    status=_s(r["Assembly_Status"]),
                    pub_doi=_s(r["PUB_DOI"]),
                    **_busco_fields("busco_viridi", _s(r["Assembly_BUSCO_ViridiOdb10 (n:425)"]), parse_busco),
                    **_busco_fields("busco_embryo", _s(r["Assembly_BUSCO_EmbryoOdb10 (n:1614)"]), parse_busco),
                    assembly_type=_s(m.get("assembly_type")), n_sequences=_i(m.get("n_sequences")),
                    n90_bp=_i(m.get("n90_bp")), l90=_i(m.get("l90")),
                    ns_per_100kbp=_f(m.get("ns_per_100kbp")),
                    total_length_ge10kb=_i(m.get("total_length_ge10kb")),
                    plastid=_s(m.get("plastid")), mitochondrion=_s(m.get("mitochondrion")),
                    description=adesc, source_url=aurl,
                )
                db.add(asm)
                db.flush()
                assemblies[akey] = asm
                n_re += _add_repeats(db, models, asm, r, parse_earlgrey)

            methodology = _s(r["Annotation_Methodology"])
            _, tool_version = extract_tool_info(methodology or "")
            proto = models.AnnotationProtocol(tool=r["tool_name"], tool_version=tool_version or None,
                                              commands=methodology)
            db.add(proto)
            db.flush()
            gdesc, gurl = d("annotation", r["annotation_key"])
            gm = models.GeneModelAnnotation(
                assembly_id=assemblies[akey].id, protocol_id=proto.id,
                version_label=_s(r["Annotation_Version"]), methodology=methodology,
                display_name=r["display_name"], tool_name=r["tool_name"],
                is_reference=r["is_reference"] == "True", description=gdesc,
                source_url=gurl, zenodo_url=zenodo.get(r["annotation_key"]),
                **_annotation_fields(r, parse_busco),
            )
            gm.gas_score = gas_score(gaqet_axes(gm))
            db.add(gm)
            n_gm += 1
        db.commit()
    finally:
        db.close()
    return {"species": len(species), "assemblies": len(assemblies), "gm": n_gm, "re": n_re}


def _add_repeats(db, models, asm, r: dict, parse_earlgrey) -> int:
    """EarlGrey, Barrnap and tRNAscan-SE results of an assembly (one set per assembly)."""
    added = 0
    specs = [("EarlGrey", "RepetitiveElement_Annotation (EarlGrey)", True),
             ("Barrnap", "rDNA (Barrnap)", False),
             ("tRNAscan-SE", "tDNA (tRNAScan-SE)", False)]
    for tool, col, is_eg in specs:
        raw = _s(r.get(col))
        if not raw:
            continue
        proto = models.AnnotationProtocol(tool=tool)
        db.add(proto)
        db.flush()
        db.add(models.RepeatAnnotation(
            assembly_id=asm.id, protocol_id=proto.id, version_label=asm.version,
            total_pct=_f(r.get("Total_Repeats (EarlGrey)")) if is_eg else None,
            raw_output=raw, parsed_results=parse_earlgrey(raw) if is_eg else {"raw": raw},
        ))
        added += 1
    return added


def main() -> None:
    _print_quote()
    ap = argparse.ArgumentParser(description="Build the real-data demo database "
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
    c = build_demo_db()
    _log(f"  {c['species']} species, {c['assemblies']} assemblies, {c['gm']} gene-model "
         f"annotations, {c['re']} repeat/ncRNA annotations (real data)")
    if args.no_serve:
        return

    import uvicorn
    _log(f"Open http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{args.port} "
         f"— press Ctrl+C to stop")
    uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
