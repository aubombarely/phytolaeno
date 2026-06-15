from pydantic import BaseModel
from typing import Optional
import datetime


class ProtocolCreate(BaseModel):
    tool: str
    tool_version: Optional[str] = None
    commands: Optional[str] = None
    date_run: Optional[datetime.date] = None
    notes: Optional[str] = None


class RepeatAnnotationCreate(BaseModel):
    assembly_id: int
    protocol: ProtocolCreate
    rank: Optional[int] = None
    version_label: Optional[str] = None
    total_pct: Optional[float] = None
    raw_output: Optional[str] = None
    parsed_results: Optional[dict] = None


class GeneModelAnnotationCreate(BaseModel):
    assembly_id: int
    protocol: ProtocolCreate
    pid: Optional[str] = None
    ref_type: Optional[int] = None
    rank: Optional[int] = None
    version_label: Optional[str] = None
    methodology: Optional[str] = None
    gene_models_n: Optional[int] = None
    transcript_models_n: Optional[int] = None
    cds_models_n: Optional[int] = None
    exons_n: Optional[int] = None
    utr5_n: Optional[int] = None
    utr3_n: Optional[int] = None
    both_utrs_n: Optional[int] = None
    overlapping_gene_models_n: Optional[int] = None
    single_exon_gene_models_n: Optional[int] = None
    single_exon_transcripts_n: Optional[int] = None
    total_gene_space_mb: Optional[float] = None
    mean_gene_model_length_bp: Optional[float] = None
    mean_cds_length_bp: Optional[float] = None
    mean_exon_length_bp: Optional[float] = None
    mean_intron_length_bp: Optional[float] = None
    longest_gene_model_bp: Optional[float] = None
    longest_cds_bp: Optional[float] = None
    longest_intron_bp: Optional[float] = None
    shortest_gene_model_bp: Optional[float] = None
    shortest_cds_bp: Optional[float] = None
    shortest_intron_bp: Optional[float] = None
    models_early_stop: Optional[int] = None
    models_start_missing: Optional[int] = None
    models_stop_missing: Optional[int] = None
    models_start_stop_missing: Optional[int] = None
    busco_viridi_raw: Optional[str] = None
    busco_embryo_raw: Optional[str] = None
    omark_completeness_raw: Optional[str] = None
    omark_consistency_raw: Optional[str] = None
    omark_species_composition: Optional[str] = None
    psauron_score: Optional[float] = None
    detenga_fpv_raw: Optional[str] = None
    detenga_fp_pct_raw: Optional[str] = None
    proteins_swissprot_pct: Optional[float] = None
    proteins_trembl_pct: Optional[float] = None
    gaqet_plot_area: Optional[float] = None
    f1_score_base: Optional[float] = None
    f1_score_locus: Optional[float] = None
    missed_loci: Optional[float] = None
    new_loci: Optional[float] = None
