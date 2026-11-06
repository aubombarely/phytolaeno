"""GAQET axes and Global Annotation Score (must match GAQET2 revision gaqet_plot.py) and tags."""
import csv
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.metrics import AXES, annotation_tags, gaqet_axes, gas_score, role_shares

DATA = Path(__file__).resolve().parents[1] / "demo" / "data" / "benchmark_3species.tsv"


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ann_from_row(r: dict) -> SimpleNamespace:
    """Map a benchmark spreadsheet row to GeneModelAnnotation attribute names."""
    busco_c = lambda raw: _num(re.search(r"C:([\d.]+)", raw).group(1)) if raw else None
    return SimpleNamespace(
        proteins_swissprot_pct=_num(r["ProteinsWithSwissprotHits (%)"]),
        proteins_trembl_pct=_num(r["ProteinsWithTremblHits (%)"]),
        omark_species_composition=r["OMArk 2.0.3 Species Composition"],
        busco_viridi_complete=busco_c(r["Annotation_BUSCO_ViridiOdb10 (n:425)"]),
        busco_embryo_complete=busco_c(r["Annotation_BUSCO_EmbryoOdb10 (n:1614)"]),
        detenga_fp_pct_raw=r["DETENGA_FP%"],
        psauron_score=_num(r["PSAURON SCORE"]),
        models_start_missing=_num(r["Models START missing"]),
        models_stop_missing=_num(r["Models STOP missing"]),
        models_start_stop_missing=_num(r["Models START & STOP missing"]),
        transcript_models_n=_num(r["Transcript_Models (N)"]),
    )


def _annevo_row() -> dict:
    with open(DATA, newline="") as fh:
        return next(r for r in csv.DictReader(fh, delimiter="\t")
                    if r["Annotation_Version"] == "ArthaTAIR10_ANv1")


def _full(**over) -> SimpleNamespace:
    base = dict(proteins_swissprot_pct=70.0, proteins_trembl_pct=95.0,
                omark_species_composition="Arabidopsis thaliana: 90.0%",
                busco_viridi_complete=98.0, busco_embryo_complete=96.0,
                detenga_fp_pct_raw="T: 100;PcpM0: 80.0;PteM0: 0.1", psauron_score=94.0,
                models_start_missing=10, models_stop_missing=10, models_start_stop_missing=0,
                transcript_models_n=1000, utr5_n=500, utr3_n=500, gene_models_n=800,
                is_reference=False, micro_exon_pct=None)
    base.update(over)
    return SimpleNamespace(**base)


def test_axes_match_gaqet():
    r = _annevo_row()
    ann = _ann_from_row(r)
    expected = {
        "swissprot": float(r["ProteinsWithSwissprotHits (%)"]),
        "trembl": float(r["ProteinsWithTremblHits (%)"]),
        "omark_species": float(re.search(r":\s*([\d.]+)%", r["OMArk 2.0.3 Species Composition"]).group(1)),
        "busco_viridiplantae": float(re.search(r"C:([\d.]+)", r["Annotation_BUSCO_ViridiOdb10 (n:425)"]).group(1)),
        "busco_embryophyta": float(re.search(r"C:([\d.]+)", r["Annotation_BUSCO_EmbryoOdb10 (n:1614)"]).group(1)),
        "detenga_pcpm0": float(re.search(r"PcpM0:\s*([\d.]+)", r["DETENGA_FP%"]).group(1)),
        "psauron": float(r["PSAURON SCORE"]),
        "agat_no_startstop": 100 - 100 * (float(r["Models START missing"]) + float(r["Models STOP missing"])
                                          + float(r["Models START & STOP missing"]))
                             / float(r["Transcript_Models (N)"]),
    }
    assert [k for k, _ in AXES] == list(expected)
    assert gaqet_axes(ann) == pytest.approx(expected)


def test_gas_equal_shares_is_mean():
    axes = gaqet_axes(_full())
    assert gas_score(axes) == pytest.approx(sum(axes.values()) / 8)


def test_gas_role_weights():
    axes = gaqet_axes(_full())
    others = [v for k, v in axes.items() if not k.startswith("busco")]
    expected = 0.2 * axes["busco_viridiplantae"] + 0.2 * axes["busco_embryophyta"] \
        + sum(0.6 / 6 * v for v in others)
    assert gas_score(axes, {"busco": 40}) == pytest.approx(expected)


def test_gas_skips_missing_axis():
    axes = gaqet_axes(_full(psauron_score=None))
    present = [v for v in axes.values() if v is not None]
    assert len(present) == 7
    assert gas_score(axes) == pytest.approx(sum(present) / 7)


def test_role_shares_rejects_over_100():
    with pytest.raises(ValueError):
        role_shares({"busco": 80, "omark": 30})
    with pytest.raises(ValueError):
        role_shares({"nonsense": 10})


def _keys(tags):
    return {t.key for t in tags}


def test_no_utr_tag_threshold():
    assert "no_utrs" in _keys(annotation_tags(_full(transcript_models_n=30000, utr5_n=1, utr3_n=0)))
    assert "no_utrs" not in _keys(annotation_tags(_full(transcript_models_n=30000, utr5_n=600, utr3_n=0)))


def test_isoform_tag():
    tags = annotation_tags(_full(transcript_models_n=48456, gene_models_n=27655))
    iso = [t for t in tags if t.key == "isoforms"]
    assert iso and iso[0].label == "1.75 isoforms/gene" and iso[0].kind == "info"
    tags = annotation_tags(_full(transcript_models_n=25000, gene_models_n=25000))
    assert [t.label for t in tags if t.key == "isoforms"] == ["1 isoform per gene"]


def test_micro_exon_tag_hidden_without_data():
    assert "micro_exons" not in _keys(annotation_tags(_full(micro_exon_pct=None)))
    tags = annotation_tags(_full(micro_exon_pct=20.0))
    assert any(t.key == "micro_exons" and t.kind == "warning" for t in tags)


def test_reference_never_warned():
    tags = annotation_tags(_full(is_reference=True, utr5_n=0, utr3_n=0, micro_exon_pct=30.0))
    assert not [t for t in tags if t.kind == "warning"]


def test_tags_handle_zero_transcripts():
    for n in (0, None):
        tags = annotation_tags(_full(transcript_models_n=n, gene_models_n=n))
        assert "no_utrs" not in _keys(tags) and "isoforms" not in _keys(tags)
    assert gaqet_axes(_full(transcript_models_n=0))["agat_no_startstop"] is None
