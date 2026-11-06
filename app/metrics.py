"""GAQET quality axes, Global Annotation Score (GAS) and annotation tags.

Axes and score follow GAQET2 (revision branch, GAQET/gaqet_plot.py):
https://github.com/victorgcb1987/GAQET2/blob/revision/GAQET/gaqet_plot.py

GAS = sum(share_i * metric_i) over the metrics whose analysis was run. By
default every metric has the same share. With weights, a role (analysis) gets
that percentage split equally among its metrics, and the remaining
percentage is split equally among the metrics not mentioned.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (axis_key, role) in GAQET's radar order
AXES: list[tuple[str, str]] = [
    ("swissprot", "homology"),
    ("trembl", "homology"),
    ("omark_species", "omark"),
    ("busco_viridiplantae", "busco"),
    ("busco_embryophyta", "busco"),
    ("detenga_pcpm0", "detenga"),
    ("psauron", "psauron"),
    ("agat_no_startstop", "agat"),
]
ROLES = ("homology", "busco", "omark", "psauron", "detenga", "agat")

AXIS_LABELS: dict[str, str] = {
    "swissprot": "SWISSPROT Homology Hits (DIAMOND)",
    "trembl": "TREMBL Homology Hits (DIAMOND)",
    "omark_species": "Proteins fitting their Taxonomic rank (OMARK)",
    "busco_viridiplantae": "Viridiplantae Completeness (BUSCO)",
    "busco_embryophyta": "Embryophyta Completeness (BUSCO)",
    "detenga_pcpm0": "Proteins with functional domains (DeTEnGA)",
    "psauron": "Transcripts Flagged as coding sequences (PSAURON)",
    "agat_no_startstop": "No start/stop codon errors (AGAT)",
}

NO_UTR_FRACTION = 0.01        # "No UTRs": < 1% of transcripts carry a UTR
MICRO_EXON_WARN_PCT = 1.0     # micro-exon tag when >= 1% of transcripts are affected


def _num(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f          # NaN -> None


def _extract(pattern: str, text) -> float | None:
    if not text:
        return None
    m = re.search(pattern, str(text))
    return _num(m.group(1)) if m else None


def gaqet_axes(ann) -> dict[str, float | None]:
    """The eight GAQET radar values (0-100) of a gene-model annotation; None if missing."""
    tr = _num(getattr(ann, "transcript_models_n", None))
    missing = [_num(getattr(ann, a, None)) for a in
               ("models_start_missing", "models_stop_missing", "models_start_stop_missing")]
    agat = None
    if tr and all(m is not None for m in missing):
        agat = 100 - 100 * sum(missing) / tr
    return {
        "swissprot": _num(getattr(ann, "proteins_swissprot_pct", None)),
        "trembl": _num(getattr(ann, "proteins_trembl_pct", None)),
        "omark_species": _extract(r":\s*([\d.]+)%", getattr(ann, "omark_species_composition", None)),
        "busco_viridiplantae": _num(getattr(ann, "busco_viridi_complete", None)),
        "busco_embryophyta": _num(getattr(ann, "busco_embryo_complete", None)),
        "detenga_pcpm0": _extract(r"PcpM0:\s*([\d.]+)", getattr(ann, "detenga_fp_pct_raw", None)),
        "psauron": _num(getattr(ann, "psauron_score", None)),
        "agat_no_startstop": agat,
    }


def role_shares(weights: dict[str, float] | None) -> dict[str, float]:
    """Validate role weights (percentages 0-100, sum <= 100); return them as floats."""
    if not weights:
        return {}
    out = {}
    for role, pct in weights.items():
        if role not in ROLES:
            raise ValueError(f"Unknown analysis '{role}'. Use one of: {', '.join(ROLES)}")
        pct = float(pct)
        if not 0 <= pct <= 100:
            raise ValueError(f"Share for '{role}' must be between 0 and 100")
        out[role] = pct
    if sum(out.values()) > 100 + 1e-9:
        raise ValueError(f"Shares add up to {sum(out.values()):.1f}%, more than 100%")
    if len(out) == len(ROLES) and sum(out.values()) <= 0:
        raise ValueError("All analyses have a share of 0")
    return out


def axis_shares(available: list[str], weights: dict[str, float] | None = None) -> dict[str, float]:
    """Fraction of the score (summing to 1) for each available axis."""
    if not available:
        return {}
    shares: dict[str, float] = {}
    role_of = dict(AXES)
    for role, pct in role_shares(weights).items():
        axes = [a for a in available if role_of[a] == role]
        for a in axes:
            shares[a] = pct / len(axes)
    remaining = [a for a in available if a not in shares]
    if remaining:
        rest = max(0.0, 100 - sum(shares.values()))
        for a in remaining:
            shares[a] = rest / len(remaining)
    total = sum(shares.values())
    if total <= 0:
        return {a: 1 / len(available) for a in available}
    return {a: s / total for a, s in shares.items()}


def gas_score(axes: dict[str, float | None], weights: dict[str, float] | None = None) -> float | None:
    """Global Annotation Score (0-100); metrics with a missing analysis are left out."""
    available = [k for k, _ in AXES if axes.get(k) is not None]
    if not available:
        return None
    return sum(axes[a] * s for a, s in axis_shares(available, weights).items())


@dataclass(frozen=True)
class Tag:
    key: str
    label: str
    kind: str              # "warning" or "info"
    explanation_key: str


def annotation_tags(ann) -> list[Tag]:
    """Insight tags for an annotation. References never get warnings."""
    tags: list[Tag] = []
    is_ref = bool(getattr(ann, "is_reference", False))
    tr = _num(getattr(ann, "transcript_models_n", None))
    genes = _num(getattr(ann, "gene_models_n", None))
    if tr and not is_ref:
        utr5 = _num(getattr(ann, "utr5_n", None)) or 0
        utr3 = _num(getattr(ann, "utr3_n", None)) or 0
        if max(utr5, utr3) / tr < NO_UTR_FRACTION:
            tags.append(Tag("no_utrs", "No UTRs", "warning", "no_utrs"))
    micro = _num(getattr(ann, "micro_exon_pct", None))
    if micro is not None and micro >= MICRO_EXON_WARN_PCT and not is_ref:
        tags.append(Tag("micro_exons", f"Micro-exons {micro:.1f}%", "warning", "micro_exons"))
    if tr and genes:
        ratio = tr / genes
        label = "1 isoform per gene" if round(ratio, 2) == 1 else f"{ratio:.2f} isoforms/gene"
        tags.append(Tag("isoforms", label, "info", "isoforms"))
    return tags
