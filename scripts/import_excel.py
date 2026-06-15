#!/usr/bin/env python3
"""
import_excel.py  —  Phytolaeno one-time Excel import

Reads PlantAnnotationBenchmark2025.xlsx and populates the database.

Usage:
    python scripts/import_excel.py --excel /path/to/PlantAnnotationBenchmark2025.xlsx
"""
import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, engine
from app import models
from app.utils import parse_busco, parse_earlgrey, extract_tool_info, safe_float, safe_int

models.Base.metadata.create_all(bind=engine)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def import_excel(excel_path: str) -> None:
    df = pd.read_excel(excel_path, sheet_name="Sheet1")
    log.info(f"Loaded {len(df)} rows × {len(df.columns)} cols from {excel_path}")

    db = SessionLocal()
    n_species = n_assemblies = n_re = n_gm = 0

    # Track already-created species and assemblies to avoid duplicates
    species_cache: dict[str, models.Species] = {}    # name → Species
    assembly_cache: dict[str, models.Assembly] = {}  # version → Assembly

    for idx, row in df.iterrows():
        species_name  = str(row.get("Species", "")).strip()
        assembly_ver  = str(row.get("Assembly_Version", "")).strip()
        if not species_name or not assembly_ver:
            continue

        # ── Species ───────────────────────────────────────────────────────────
        if species_name not in species_cache:
            sp = models.Species(
                name=species_name,
                species_number=safe_int(row.get("SpeciesNumber")),
                ncbi_taxid=safe_int(row.get("NCBI_TaxID")),
                family=str(row.get("Family", "") or "").strip() or None,
                lineage=str(row.get("Lineage", "") or "").strip() or None,
            )
            db.add(sp)
            db.flush()
            species_cache[species_name] = sp
            n_species += 1
            log.info(f"  Species: {species_name} (id={sp.id})")

        sp = species_cache[species_name]

        # ── Assembly ──────────────────────────────────────────────────────────
        if assembly_ver not in assembly_cache:
            bv_raw = str(row.get("Assembly_BUSCO_ViridiOdb10 (n:425)", "") or "")
            be_raw = str(row.get("Assembly_BUSCO_EmbryoOdb10 (n:1614)", "") or "")
            bv = parse_busco(bv_raw)
            be = parse_busco(be_raw)

            asm = models.Assembly(
                species_id=sp.id,
                version=assembly_ver,
                source=str(row.get("Source", "") or "").strip() or None,
                size_gb=safe_float(row.get("Assembly_Size (Gb)")),
                status=str(row.get("Assembly_Status", "") or "").strip() or None,
                busco_viridi_raw=bv_raw or None,
                busco_viridi_complete=bv.get("complete"),
                busco_viridi_single=bv.get("single"),
                busco_viridi_duplicated=bv.get("duplicated"),
                busco_viridi_fragmented=bv.get("fragmented"),
                busco_viridi_missing=bv.get("missing"),
                busco_embryo_raw=be_raw or None,
                busco_embryo_complete=be.get("complete"),
                busco_embryo_single=be.get("single"),
                busco_embryo_duplicated=be.get("duplicated"),
                busco_embryo_fragmented=be.get("fragmented"),
                busco_embryo_missing=be.get("missing"),
                pub_doi=str(row.get("PUB_DOI", "") or "").strip() or None,
                prev_version_pub_doi=str(row.get("PREV_VERSION_PUB_DOI", "") or "").strip() or None,
                prev_version_annot=str(row.get("PREV_VERSION_ANNOT", "") or "").strip() or None,
            )
            db.add(asm)
            db.flush()
            assembly_cache[assembly_ver] = asm
            n_assemblies += 1

            # ── Repeat annotations (once per assembly) ────────────────────────

            # EarlGrey
            eg_raw = str(row.get("RepetitiveElement_Annotation (EarlGrey)", "") or "")
            eg_total = safe_float(row.get("Total_Repeats (EarlGrey)"))
            if eg_raw.strip():
                eg_proto = models.AnnotationProtocol(tool="EarlGrey")
                db.add(eg_proto)
                db.flush()
                db.add(models.RepeatAnnotation(
                    assembly_id=asm.id, protocol_id=eg_proto.id,
                    version_label=assembly_ver,
                    total_pct=eg_total,
                    raw_output=eg_raw,
                    parsed_results=parse_earlgrey(eg_raw),
                ))
                n_re += 1

            # Barrnap (rDNA)
            rdna_raw = str(row.get("rDNA (Barrnap)", "") or "")
            if rdna_raw.strip() and rdna_raw != "nan":
                rdna_proto = models.AnnotationProtocol(tool="Barrnap")
                db.add(rdna_proto)
                db.flush()
                db.add(models.RepeatAnnotation(
                    assembly_id=asm.id, protocol_id=rdna_proto.id,
                    version_label=assembly_ver,
                    raw_output=rdna_raw,
                    parsed_results={"raw": rdna_raw},
                ))
                n_re += 1

            # tRNAScan-SE
            tdna_raw = str(row.get("tDNA (tRNAScan-SE)", "") or "")
            if tdna_raw.strip() and tdna_raw != "nan":
                tdna_proto = models.AnnotationProtocol(tool="tRNAScan-SE")
                db.add(tdna_proto)
                db.flush()
                db.add(models.RepeatAnnotation(
                    assembly_id=asm.id, protocol_id=tdna_proto.id,
                    version_label=assembly_ver,
                    raw_output=tdna_raw,
                    parsed_results={"raw": tdna_raw},
                ))
                n_re += 1

        asm = assembly_cache[assembly_ver]

        # ── Gene model annotation ─────────────────────────────────────────────
        methodology = str(row.get("Annotation_Methodology", "") or "").strip()
        tool, tool_version = extract_tool_info(methodology)
        gm_proto = models.AnnotationProtocol(
            tool=tool,
            tool_version=tool_version or None,
            commands=methodology or None,
        )
        db.add(gm_proto)
        db.flush()

        bv_raw = str(row.get("Annotation_BUSCO_ViridiOdb10 (n:425)", "") or "")
        be_raw = str(row.get("Annotation_BUSCO_EmbryoOdb10 (n:1614)", "") or "")
        bv = parse_busco(bv_raw)
        be = parse_busco(be_raw)

        gm = models.GeneModelAnnotation(
            assembly_id=asm.id,
            protocol_id=gm_proto.id,
            pid=str(row.get("PID", "") or "").strip() or None,
            ref_type=safe_int(row.get("RefType")),
            rank=safe_int(row.get("Annotation_Rank")),
            version_label=str(row.get("Annotation_Version", "") or "").strip() or None,
            methodology=methodology or None,
            gene_models_n=safe_int(row.get("Gene_Models (N)")),
            transcript_models_n=safe_int(row.get("Transcript_Models (N)")),
            cds_models_n=safe_int(row.get("CDS_Models (N)")),
            exons_n=safe_int(row.get("Exons (N)")),
            utr5_n=safe_int(row.get("UTR5' (N)")),
            utr3_n=safe_int(row.get("UTR3' (N)")),
            both_utrs_n=safe_int(row.get("Both sides UTR' (N)")),
            overlapping_gene_models_n=safe_int(row.get("Overlapping_Gene_Models (N)")),
            single_exon_gene_models_n=safe_int(row.get("Single Exon Gene Models (N)")),
            single_exon_transcripts_n=safe_int(row.get("Single Exon Transcripts (N)")),
            total_gene_space_mb=safe_float(row.get("Total Gene Space (Mb)")),
            mean_gene_model_length_bp=safe_float(row.get("Mean Gene Model Length (bp)")),
            mean_cds_length_bp=safe_float(row.get("Mean CDS Model Length (bp)")),
            mean_exon_length_bp=safe_float(row.get("Mean Exon Length (bp)")),
            mean_intron_length_bp=safe_float(row.get("Mean Intron Length (bp)")),
            longest_gene_model_bp=safe_float(row.get("Longest Gene Model Length (bp)")),
            longest_cds_bp=safe_float(row.get("Longest CDS Model Length (bp)")),
            longest_intron_bp=safe_float(row.get("Longest Intron Length (bp)")),
            shortest_gene_model_bp=safe_float(row.get("Shortest Gene Model Length (bp)")),
            shortest_cds_bp=safe_float(row.get("Shortest CDS Model Length (bp)")),
            shortest_intron_bp=safe_float(row.get("Shortest Intron Length (bp)")),
            models_early_stop=safe_int(row.get("Models with early STOP")),
            models_start_missing=safe_int(row.get("Models START missing")),
            models_stop_missing=safe_int(row.get("Models STOP missing")),
            models_start_stop_missing=safe_int(row.get("Models START & STOP missing")),
            busco_viridi_raw=bv_raw or None,
            busco_viridi_complete=bv.get("complete"),
            busco_viridi_single=bv.get("single"),
            busco_viridi_duplicated=bv.get("duplicated"),
            busco_viridi_fragmented=bv.get("fragmented"),
            busco_viridi_missing=bv.get("missing"),
            busco_embryo_raw=be_raw or None,
            busco_embryo_complete=be.get("complete"),
            busco_embryo_single=be.get("single"),
            busco_embryo_duplicated=be.get("duplicated"),
            busco_embryo_fragmented=be.get("fragmented"),
            busco_embryo_missing=be.get("missing"),
            omark_completeness_raw=str(row.get("OMArk 2.0.3 Completeness Results", "") or "").strip() or None,
            omark_consistency_raw=str(row.get("OMArk 2.0.3 Consistency Results", "") or "").strip() or None,
            omark_species_composition=str(row.get("OMArk 2.0.3 Species Composition", "") or "").strip() or None,
            psauron_score=safe_float(row.get("PSAURON SCORE")),
            detenga_fpv_raw=str(row.get("DETENGA_FPV", "") or "").strip() or None,
            detenga_fp_pct_raw=str(row.get("DETENGA_FP%", "") or "").strip() or None,
            proteins_swissprot_pct=safe_float(row.get("ProteinsWithSwissprotHits (%)")),
            proteins_trembl_pct=safe_float(row.get("ProteinsWithTremblHits (%)")),
            gaqet_plot_area=safe_float(row.get("GAQET_Plot_Area")),
            f1_score_base=safe_float(row.get("F1-Score Base")),
            f1_score_locus=safe_float(row.get("F1-Score Locus")),
            missed_loci=safe_float(row.get("Missed Loci")),
            new_loci=safe_float(row.get("New Loci")),
        )
        db.add(gm)
        n_gm += 1

    db.commit()
    db.close()
    log.info(
        f"Import complete: {n_species} species | {n_assemblies} assemblies | "
        f"{n_re} repeat annotations | {n_gm} gene model annotations"
    )


def main():
    parser = argparse.ArgumentParser(description="Import Excel data into Phytolaeno")
    parser.add_argument("--excel", required=True, help="Path to the Excel file")
    args = parser.parse_args()
    import_excel(args.excel)


if __name__ == "__main__":
    main()
