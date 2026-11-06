"""Figures for the Plots page and the species page.

One set of selectors (species, assembly, annotations, metric, GAS weights)
drives three views:

* within  — one bar per annotation in scope, sorted by the chosen metric
* across  — the chosen metric per annotation tool, one series per species,
            the selected species highlighted
* radar   — GAQET radar (eight axes), one polygon per annotation, legend
            ordered by the Global Annotation Score under the chosen weights
* repeats — EarlGrey repeat classes per assembly in scope

Parameters arrive as query strings; parse_plot_params never raises — bad
values fall back to defaults and add a notice for the page.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Callable

import plotly.graph_objects as go
from sqlalchemy.orm import Session

from app import models
from app.metrics import AXES, AXIS_LABELS, ROLES, gaqet_axes, gas_score, role_shares

BLUE, RED, GREY, AMBER = "#4C9BE8", "#E8604C", "#888888", "#F5A623"
ASM_COLOURS = [BLUE, AMBER, RED, GREY]
RADAR_MAX = 20


def _ratio(num, den):
    return None if not num or not den else num / den


METRICS: dict[str, tuple[str, Callable]] = {
    "gas": ("Global Annotation Score (GAS)", None),          # computed with the weights
    "busco_viridi": ("BUSCO complete % (Viridiplantae)", lambda a: a.busco_viridi_complete),
    "busco_embryo": ("BUSCO complete % (Embryophyta)", lambda a: a.busco_embryo_complete),
    "gene_models": ("Gene models (N)", lambda a: a.gene_models_n),
    "psauron": ("PSAURON score", lambda a: a.psauron_score),
    "utr_pct": ("Transcripts with a UTR (%)", lambda a: None if not a.transcript_models_n else
                100 * max(a.utr5_n or 0, a.utr3_n or 0) / a.transcript_models_n),
    "isoforms": ("Isoforms per gene", lambda a: _ratio(a.transcript_models_n, a.gene_models_n)),
    "mean_intron": ("Mean intron length (bp)", lambda a: a.mean_intron_length_bp),
    "single_exon": ("Single-exon genes (%)", lambda a: None if not a.gene_models_n
                    or a.single_exon_gene_models_n is None
                    else 100 * a.single_exon_gene_models_n / a.gene_models_n),
}


@dataclass
class PlotParams:
    species_id: int | None = None
    assembly_id: int | None = None
    annotation_ids: list[int] = field(default_factory=list)
    metric: str = "gas"
    weights: dict[str, float] | None = None
    notices: list[str] = field(default_factory=list)


def _int_or_none(value: str | None, label: str, notices: list[str]) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        notices.append(f"Ignored invalid {label} '{value}'.")
        return None


def parse_plot_params(species_id: str | None, assembly_id: str | None,
                      annotation_ids: str | None, metric: str | None,
                      weights: str | None) -> PlotParams:
    notices: list[str] = []
    p = PlotParams(notices=notices)
    p.species_id = _int_or_none(species_id, "species", notices)
    p.assembly_id = _int_or_none(assembly_id, "assembly", notices)
    for item in (annotation_ids or "").split(","):
        item = item.strip()
        if item:
            v = _int_or_none(item, "annotation id", notices)
            if v is not None:
                p.annotation_ids.append(v)
    if metric:
        if metric in METRICS:
            p.metric = metric
        else:
            notices.append(f"Unknown metric '{metric}', showing GAS.")
    if weights:
        try:
            parsed = {}
            for item in weights.split(","):
                role, _, pct = item.partition(":")
                parsed[role.strip()] = float(pct)
            role_shares(parsed)                 # validates roles and totals
            p.weights = parsed
        except (ValueError, TypeError) as err:
            notices.append(f"Ignored weights '{weights}' ({err}); using equal shares.")
    return p


def _scope(db: Session, p: PlotParams):
    """Selected species/assembly objects and the annotations in scope."""
    species = assembly = None
    if p.assembly_id is not None:
        assembly = db.get(models.Assembly, p.assembly_id)
        if assembly is None:
            p.notices.append(f"Assembly {p.assembly_id} not found; showing all assemblies.")
            p.assembly_id = None
    if p.species_id is not None:
        species = db.get(models.Species, p.species_id)
        if species is None:
            p.notices.append(f"Species {p.species_id} not found; showing all species.")
            p.species_id = None
    if assembly is not None:
        if species is not None and assembly.species_id != species.id:
            p.notices.append("Assembly does not belong to the selected species; using the assembly.")
        species = assembly.species
        p.species_id = species.id
    q = db.query(models.GeneModelAnnotation).join(models.Assembly)
    if assembly is not None:
        q = q.filter(models.GeneModelAnnotation.assembly_id == assembly.id)
    elif species is not None:
        q = q.filter(models.Assembly.species_id == species.id)
    anns = q.all()
    return species, assembly, anns


def _label(a, multi_assembly: bool) -> str:
    name = a.display_name or a.version_label or f"annotation {a.id}"
    return f"{name} [{a.assembly.version}]" if multi_assembly else name


def _tool(a) -> str:
    return a.tool_name or (a.protocol.tool if a.protocol else "?")


def _default_species(db: Session, p: PlotParams) -> None:
    """Plots compare annotations within one species: default to the first one."""
    if p.species_id is None and p.assembly_id is None:
        first = db.query(models.Species).order_by(models.Species.name).first()
        if first is not None:
            p.species_id = first.id


def build_figures(db: Session, p: PlotParams) -> dict[str, str]:
    """Single-species figures: within, assemblies, radar and repeats."""
    _default_species(db, p)
    species, assembly, anns = _scope(db, p)
    if species is None and p.species_id is None:      # invalid id was dropped -> default
        _default_species(db, p)
        species, assembly, anns = _scope(db, p)
    label, getter = METRICS[p.metric]
    gas = {a.id: gas_score(gaqet_axes(a), p.weights) for a in anns}
    value = (lambda a: gas[a.id]) if p.metric == "gas" else getter
    selected = [a for a in anns if a.id in p.annotation_ids] if p.annotation_ids else anns
    if p.annotation_ids and not selected:
        p.notices.append("None of the selected annotations is in scope; showing all.")
        selected = anns
    multi = len({a.assembly_id for a in selected}) > 1
    figs: dict[str, str] = {}

    # within: one bar per annotation, best at the top
    rows = sorted([(value(a), a) for a in selected if value(a) is not None], key=lambda t: t[0])
    # dot plot: no zero baseline, so close scores (e.g. GAS 88-94) stay distinguishable
    within = go.Figure(go.Scatter(
        x=[v for v, _ in rows], y=[_label(a, multi) for _, a in rows], mode="markers",
        marker=dict(size=12, color=[GREY if a.is_reference else BLUE for _, a in rows],
                    line=dict(width=1, color="#333")),
        hovertemplate="%{y}: %{x:.2f}<extra></extra>"))
    within.update_layout(title=dict(text=f"{label} per annotation<br><sub>grey = reference annotation</sub>"),
                         xaxis_title=label, template="plotly_white",
                         height=max(320, 26 * len(rows) + 140), margin=dict(l=10, r=10, t=80, b=40))
    within.update_xaxes(showgrid=True, zeroline=False)
    within.update_yaxes(automargin=True)
    figs["within"] = within.to_json()

    # assemblies: metric per tool, one series per assembly of the selected species
    asm_list = sorted({a.assembly for a in anns}, key=lambda x: x.version)
    tools = sorted({_tool(a) for a in anns})
    comp = go.Figure()
    for i, asm in enumerate(asm_list):
        ys = []
        for t in tools:
            vals = [value(a) for a in anns if a.assembly_id == asm.id and _tool(a) == t
                    and value(a) is not None]
            ys.append(mean(vals) if vals else None)
        comp.add_trace(go.Scatter(
            x=tools, y=ys, mode="markers", name=asm.version,
            marker=dict(size=12, color=ASM_COLOURS[i % len(ASM_COLOURS)],
                        line=dict(width=1, color="#333")),
            hovertemplate=f"{asm.version}<br>%{{x}}: %{{y:.2f}}<extra></extra>"))
    comp.update_layout(title=f"{label} by tool, per assembly (mean of runs)", yaxis_title=label,
                       template="plotly_white", height=420, legend_title="Assembly",
                       legend=dict(orientation="h", y=-0.35))
    figs["assemblies"] = comp.to_json()

    # radar: GAQET axes, legend ordered by GAS (best first)
    ranked = sorted(selected, key=lambda a: (gas[a.id] is None, -(gas[a.id] or 0)))
    if len(ranked) > RADAR_MAX:
        p.notices.append(f"Radar shows the top {RADAR_MAX} annotations by GAS; "
                         "select a species or assembly to see all of its annotations.")
        ranked = ranked[:RADAR_MAX]
    theta = [AXIS_LABELS[k] for k, _ in AXES] + [AXIS_LABELS[AXES[0][0]]]
    radar = go.Figure()
    for a in ranked:
        ax = gaqet_axes(a)
        r = [ax[k] if ax[k] is not None else 0 for k, _ in AXES]
        g = gas[a.id]
        radar.add_trace(go.Scatterpolar(
            r=r + r[:1], theta=theta, name=_label(a, multi), fill="toself", opacity=0.55,
            line=dict(dash="dot" if a.is_reference else "solid"),
            hovertemplate="%{theta}: %{r:.1f}<extra>" + _label(a, multi)
                          + (f" · GAS {g:.1f}" if g is not None else "") + "</extra>"))
    radar.update_layout(title="GAQET radar (legend ordered by GAS; click entries to show/hide)",
                        polar=dict(radialaxis=dict(range=[0, 100], ticksuffix="%")),
                        template="plotly_white", height=620, legend=dict(font=dict(size=10)))
    figs["radar"] = radar.to_json()

    # repeats: EarlGrey classes per assembly in scope
    asm_ids = {a.assembly_id for a in anns}
    reps = [r for r in db.query(models.RepeatAnnotation).all()
            if r.assembly_id in asm_ids and r.protocol and r.protocol.tool == "EarlGrey"
            and isinstance(r.parsed_results, dict)]
    if reps:
        classes = sorted({k for r in reps for k in r.parsed_results})
        rep = go.Figure([go.Bar(name=c, x=[r.assembly.version for r in reps],
                                y=[r.parsed_results.get(c, 0) for r in reps]) for c in classes])
        rep.update_layout(barmode="stack", title="Repeat content per assembly (EarlGrey)",
                          yaxis_title="% of genome", template="plotly_white", height=420,
                          legend_title="Class")
        figs["repeats"] = rep.to_json()
    return figs


def build_species_comparison(db: Session, p: PlotParams) -> dict[str, str]:
    """Across-species view: the chosen metric per tool, one series per species."""
    label, getter = METRICS[p.metric]
    species = db.get(models.Species, p.species_id) if p.species_id is not None else None
    # across: metric per tool, one series per species (all species, selected highlighted)
    all_anns = db.query(models.GeneModelAnnotation).all()
    all_gas = {a.id: gas_score(gaqet_axes(a), p.weights) for a in all_anns}
    val_all = (lambda a: all_gas[a.id]) if p.metric == "gas" else getter
    tools = sorted({a.tool_name or (a.protocol.tool if a.protocol else "?") for a in all_anns})
    across = go.Figure()
    for sp in sorted({a.assembly.species for a in all_anns}, key=lambda s: s.name):
        ys = []
        for t in tools:
            vals = [val_all(a) for a in all_anns if a.assembly.species_id == sp.id
                    and (a.tool_name or (a.protocol.tool if a.protocol else "?")) == t
                    and val_all(a) is not None]
            ys.append(mean(vals) if vals else None)
        hl = species is None or sp.id == species.id
        across.add_trace(go.Scatter(
            x=tools, y=ys, mode="markers", name=sp.name,
            marker=dict(size=13 if hl else 9, color=BLUE if (species and hl) else (None if not species else GREY),
                        opacity=1 if hl else 0.6, line=dict(width=1, color="#333")),
            hovertemplate=f"{sp.name}<br>%{{x}}: %{{y:.2f}}<extra></extra>"))
    across.update_layout(title=f"{label} by tool and species (mean of runs)", yaxis_title=label,
                         template="plotly_white", height=420, legend_title="Species")
    return {"across": across.to_json()}


def selector_options(db: Session, p: PlotParams) -> dict:
    """Choices for the selector form."""
    species_all = db.query(models.Species).order_by(models.Species.name).all()
    assemblies = db.query(models.Assembly).order_by(models.Assembly.version).all()
    if p.species_id is not None:
        assemblies = [a for a in assemblies if a.species_id == p.species_id]
    _, _, anns = _scope(db, PlotParams(species_id=p.species_id, assembly_id=p.assembly_id))
    return {"species": species_all, "assemblies": assemblies,
            "annotations": sorted(anns, key=lambda a: (a.assembly.version, a.display_name or "")),
            "metrics": [(k, v[0]) for k, v in METRICS.items()], "roles": ROLES}
