import json
import plotly.graph_objects as go
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path

from app.database import get_db
from app import models

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")

PALETTE = [
    "#2d6a4f", "#52b788", "#74c69d", "#b7e4c7",
    "#1b4332", "#40916c", "#95d5b2", "#d8f3dc",
]


def _json(fig) -> str:
    return json.dumps(fig, cls=go.Figure.__class__)


@router.get("/plots", name="plots")
def plots(request: Request, db: Session = Depends(get_db)):

    # ── BUSCO completeness by methodology ─────────────────────────────────────
    rows = (
        db.query(
            models.AnnotationProtocol.tool,
            models.GeneModelAnnotation.busco_viridi_complete,
        )
        .join(models.GeneModelAnnotation,
              models.GeneModelAnnotation.protocol_id == models.AnnotationProtocol.id)
        .filter(models.GeneModelAnnotation.busco_viridi_complete.isnot(None))
        .all()
    )
    tools   = sorted(set(r[0] for r in rows))
    fig_busco = go.Figure()
    for i, tool in enumerate(tools):
        vals = [r[1] for r in rows if r[0] == tool]
        fig_busco.add_trace(go.Box(
            y=vals, name=tool,
            marker_color=PALETTE[i % len(PALETTE)],
            boxpoints="outliers",
        ))
    fig_busco.update_layout(
        title="Annotation BUSCO completeness (viridiplantae) by tool",
        yaxis_title="Complete (%)", showlegend=False,
        template="plotly_white",
    )

    # ── Gene model counts by tool ─────────────────────────────────────────────
    rows2 = (
        db.query(
            models.AnnotationProtocol.tool,
            models.GeneModelAnnotation.gene_models_n,
        )
        .join(models.GeneModelAnnotation,
              models.GeneModelAnnotation.protocol_id == models.AnnotationProtocol.id)
        .filter(models.GeneModelAnnotation.gene_models_n.isnot(None))
        .all()
    )
    fig_genes = go.Figure()
    for i, tool in enumerate(sorted(set(r[0] for r in rows2))):
        vals = [r[1] for r in rows2 if r[0] == tool]
        fig_genes.add_trace(go.Box(
            y=vals, name=tool,
            marker_color=PALETTE[i % len(PALETTE)],
            boxpoints="outliers",
        ))
    fig_genes.update_layout(
        title="Gene model count by tool",
        yaxis_title="Gene models (N)", showlegend=False,
        template="plotly_white",
    )

    # ── Mean intron vs mean exon length ──────────────────────────────────────
    rows3 = (
        db.query(
            models.AnnotationProtocol.tool,
            models.GeneModelAnnotation.mean_intron_length_bp,
            models.GeneModelAnnotation.mean_exon_length_bp,
        )
        .join(models.GeneModelAnnotation,
              models.GeneModelAnnotation.protocol_id == models.AnnotationProtocol.id)
        .filter(
            models.GeneModelAnnotation.mean_intron_length_bp.isnot(None),
            models.GeneModelAnnotation.mean_exon_length_bp.isnot(None),
        )
        .all()
    )
    fig_lengths = go.Figure()
    for i, tool in enumerate(sorted(set(r[0] for r in rows3))):
        subset = [(r[1], r[2]) for r in rows3 if r[0] == tool]
        fig_lengths.add_trace(go.Scatter(
            x=[s[0] for s in subset],
            y=[s[1] for s in subset],
            mode="markers", name=tool,
            marker=dict(color=PALETTE[i % len(PALETTE)], size=6, opacity=0.7),
        ))
    fig_lengths.update_layout(
        title="Mean intron vs mean exon length",
        xaxis_title="Mean intron length (bp)",
        yaxis_title="Mean exon length (bp)",
        template="plotly_white",
    )

    # ── PSAURON score by tool ─────────────────────────────────────────────────
    rows4 = (
        db.query(
            models.AnnotationProtocol.tool,
            models.GeneModelAnnotation.psauron_score,
        )
        .join(models.GeneModelAnnotation,
              models.GeneModelAnnotation.protocol_id == models.AnnotationProtocol.id)
        .filter(models.GeneModelAnnotation.psauron_score.isnot(None))
        .all()
    )
    fig_psauron = go.Figure()
    for i, tool in enumerate(sorted(set(r[0] for r in rows4))):
        vals = [r[1] for r in rows4 if r[0] == tool]
        fig_psauron.add_trace(go.Box(
            y=vals, name=tool,
            marker_color=PALETTE[i % len(PALETTE)],
            boxpoints="outliers",
        ))
    fig_psauron.update_layout(
        title="PSAURON score by tool",
        yaxis_title="PSAURON score", showlegend=False,
        template="plotly_white",
    )

    # ── Repeat content — LTR% across assemblies ───────────────────────────────
    re_rows = (
        db.query(
            models.Species.name,
            models.RepeatAnnotation.parsed_results,
        )
        .join(models.Assembly, models.Assembly.id == models.RepeatAnnotation.assembly_id)
        .join(models.Species, models.Species.id == models.Assembly.species_id)
        .join(models.AnnotationProtocol,
              models.AnnotationProtocol.id == models.RepeatAnnotation.protocol_id)
        .filter(models.AnnotationProtocol.tool == "EarlGrey")
        .filter(models.RepeatAnnotation.parsed_results.isnot(None))
        .order_by(models.Species.name)
        .all()
    )
    re_classes = ["DNA", "LTR", "LINE", "SINE", "RC", "Other", "Uncl"]
    fig_repeats = go.Figure()
    sp_names = [r[0] for r in re_rows]
    for i, cls in enumerate(re_classes):
        fig_repeats.add_trace(go.Bar(
            name=cls,
            x=sp_names,
            y=[r[1].get(cls, 0) if r[1] else 0 for r in re_rows],
            marker_color=PALETTE[i % len(PALETTE)],
        ))
    fig_repeats.update_layout(
        barmode="stack", title="Repeat content by species (EarlGrey)",
        yaxis_title="% of genome", xaxis_tickangle=-45,
        template="plotly_white", legend_title="Class",
    )

    def to_json(fig):
        return fig.to_json()

    return templates.TemplateResponse("plots.html", {
        "request": request,
        "busco_json":        to_json(fig_busco),
        "gene_models_json":  to_json(fig_genes),
        "intron_exon_json":  to_json(fig_lengths),
        "psauron_json":      to_json(fig_psauron),
        "repeats_json":      to_json(fig_repeats),
    })
