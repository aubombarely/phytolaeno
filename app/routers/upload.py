from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional

from app.database import get_db
from app import models
from app.metrics import gaqet_axes, gas_score
from app.utils import parse_busco

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


@router.get("/upload", name="upload")
def upload_form(request: Request, db: Session = Depends(get_db)):
    all_species   = db.query(models.Species).order_by(models.Species.name).all()
    all_assemblies = db.query(models.Assembly).order_by(models.Assembly.version).all()
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "all_species": all_species,
        "all_assemblies": all_assemblies,
    })


@router.post("/upload/gm", name="upload_gm")
def upload_gm(
    request: Request,
    db: Session = Depends(get_db),
    assembly_id: int = Form(...),
    tool: str = Form(...),
    tool_version: Optional[str] = Form(None),
    commands: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    rank: Optional[int] = Form(None),
    version_label: Optional[str] = Form(None),
    pid: Optional[str] = Form(None),
    ref_type: Optional[str] = Form(None),
    methodology: Optional[str] = Form(None),
    gene_models_n: Optional[int] = Form(None),
    transcript_models_n: Optional[int] = Form(None),
    cds_models_n: Optional[int] = Form(None),
    exons_n: Optional[int] = Form(None),
    utr5_n: Optional[int] = Form(None),
    utr3_n: Optional[int] = Form(None),
    both_utrs_n: Optional[int] = Form(None),
    overlapping_gene_models_n: Optional[int] = Form(None),
    single_exon_gene_models_n: Optional[int] = Form(None),
    single_exon_transcripts_n: Optional[int] = Form(None),
    total_gene_space_mb: Optional[float] = Form(None),
    mean_gene_model_length_bp: Optional[float] = Form(None),
    mean_cds_length_bp: Optional[float] = Form(None),
    mean_exon_length_bp: Optional[float] = Form(None),
    mean_intron_length_bp: Optional[float] = Form(None),
    longest_gene_model_bp: Optional[float] = Form(None),
    longest_cds_bp: Optional[float] = Form(None),
    longest_intron_bp: Optional[float] = Form(None),
    shortest_gene_model_bp: Optional[float] = Form(None),
    shortest_cds_bp: Optional[float] = Form(None),
    shortest_intron_bp: Optional[float] = Form(None),
    models_early_stop: Optional[int] = Form(None),
    models_start_missing: Optional[int] = Form(None),
    models_stop_missing: Optional[int] = Form(None),
    models_start_stop_missing: Optional[int] = Form(None),
    busco_viridi_raw: Optional[str] = Form(None),
    busco_embryo_raw: Optional[str] = Form(None),
    omark_completeness_raw: Optional[str] = Form(None),
    omark_consistency_raw: Optional[str] = Form(None),
    omark_species_composition: Optional[str] = Form(None),
    psauron_score: Optional[float] = Form(None),
    detenga_fpv_raw: Optional[str] = Form(None),
    detenga_fp_pct_raw: Optional[str] = Form(None),
    proteins_swissprot_pct: Optional[float] = Form(None),
    proteins_trembl_pct: Optional[float] = Form(None),
    gaqet_plot_area: Optional[float] = Form(None),
    f1_score_base: Optional[float] = Form(None),
    f1_score_locus: Optional[float] = Form(None),
    missed_loci: Optional[float] = Form(None),
    new_loci: Optional[float] = Form(None),
):
    protocol = models.AnnotationProtocol(
        tool=tool, tool_version=tool_version or "",
        commands=commands, notes=notes,
    )
    db.add(protocol)
    db.flush()

    bv = parse_busco(busco_viridi_raw or "")
    be = parse_busco(busco_embryo_raw or "")

    ann = models.GeneModelAnnotation(
        assembly_id=assembly_id, protocol_id=protocol.id,
        rank=rank, version_label=version_label,
        pid=pid, ref_type=ref_type, methodology=methodology,
        gene_models_n=gene_models_n, transcript_models_n=transcript_models_n,
        cds_models_n=cds_models_n, exons_n=exons_n,
        utr5_n=utr5_n, utr3_n=utr3_n, both_utrs_n=both_utrs_n,
        overlapping_gene_models_n=overlapping_gene_models_n,
        single_exon_gene_models_n=single_exon_gene_models_n,
        single_exon_transcripts_n=single_exon_transcripts_n,
        total_gene_space_mb=total_gene_space_mb,
        mean_gene_model_length_bp=mean_gene_model_length_bp,
        mean_cds_length_bp=mean_cds_length_bp,
        mean_exon_length_bp=mean_exon_length_bp,
        mean_intron_length_bp=mean_intron_length_bp,
        longest_gene_model_bp=longest_gene_model_bp,
        longest_cds_bp=longest_cds_bp,
        longest_intron_bp=longest_intron_bp,
        shortest_gene_model_bp=shortest_gene_model_bp,
        shortest_cds_bp=shortest_cds_bp,
        shortest_intron_bp=shortest_intron_bp,
        models_early_stop=models_early_stop,
        models_start_missing=models_start_missing,
        models_stop_missing=models_stop_missing,
        models_start_stop_missing=models_start_stop_missing,
        busco_viridi_raw=busco_viridi_raw,
        busco_viridi_complete=bv.get("complete"),
        busco_viridi_single=bv.get("single"),
        busco_viridi_duplicated=bv.get("duplicated"),
        busco_viridi_fragmented=bv.get("fragmented"),
        busco_viridi_missing=bv.get("missing"),
        busco_embryo_raw=busco_embryo_raw,
        busco_embryo_complete=be.get("complete"),
        busco_embryo_single=be.get("single"),
        busco_embryo_duplicated=be.get("duplicated"),
        busco_embryo_fragmented=be.get("fragmented"),
        busco_embryo_missing=be.get("missing"),
        omark_completeness_raw=omark_completeness_raw,
        omark_consistency_raw=omark_consistency_raw,
        omark_species_composition=omark_species_composition,
        psauron_score=psauron_score,
        detenga_fpv_raw=detenga_fpv_raw,
        detenga_fp_pct_raw=detenga_fp_pct_raw,
        proteins_swissprot_pct=proteins_swissprot_pct,
        proteins_trembl_pct=proteins_trembl_pct,
        gaqet_plot_area=gaqet_plot_area,
        f1_score_base=f1_score_base,
        f1_score_locus=f1_score_locus,
        missed_loci=missed_loci, new_loci=new_loci,
    )
    ann.gas_score = gas_score(gaqet_axes(ann))
    db.add(ann)
    db.commit()
    return RedirectResponse(f"/assemblies/{assembly_id}", status_code=303)


@router.post("/upload/re", name="upload_re")
def upload_re(
    request: Request,
    db: Session = Depends(get_db),
    assembly_id: int = Form(...),
    tool: str = Form(...),
    tool_version: Optional[str] = Form(None),
    commands: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    rank: Optional[int] = Form(None),
    version_label: Optional[str] = Form(None),
    total_pct: Optional[float] = Form(None),
    raw_output: Optional[str] = Form(None),
):
    protocol = models.AnnotationProtocol(
        tool=tool, tool_version=tool_version or "",
        commands=commands, notes=notes,
    )
    db.add(protocol)
    db.flush()

    ann = models.RepeatAnnotation(
        assembly_id=assembly_id, protocol_id=protocol.id,
        rank=rank, version_label=version_label,
        total_pct=total_pct, raw_output=raw_output,
    )
    db.add(ann)
    db.commit()
    return RedirectResponse(f"/assemblies/{assembly_id}", status_code=303)
