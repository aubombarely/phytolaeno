"""Smoke tests: every page renders and the upload form stores a record."""
import pytest

from app import models
from app.database import SessionLocal


@pytest.mark.parametrize("path", ["/", "/species", "/plots", "/upload"])
def test_static_pages_render(client, path):
    r = client.get(path)
    assert r.status_code == 200, r.text[:500]


def test_detail_pages_render(client, seeded_ids):
    for path in (f"/species/{seeded_ids['species']}",
                 f"/assemblies/{seeded_ids['assembly']}",
                 f"/annotations/gm/{seeded_ids['gm']}",
                 f"/annotations/re/{seeded_ids['re']}"):
        r = client.get(path)
        assert r.status_code == 200, f"{path}: {r.text[:500]}"
    assert "Testus plantae" in client.get("/species").text


def test_upload_gene_model_annotation(client, seeded_ids):
    db = SessionLocal()
    try:
        before = db.query(models.GeneModelAnnotation).count()
    finally:
        db.close()
    r = client.post("/upload/gm", data={
        "assembly_id": seeded_ids["assembly"],
        "tool": "Helixer",
        "tool_version": "0.3",
        "version_label": "gm-upload",
        "gene_models_n": 31000,
        "busco_viridi_raw": "C:95.0%[S:90.0%,D:5.0%],F:2.0%,M:3.0%",
    }, follow_redirects=False)
    assert r.status_code in (200, 303), r.text[:500]
    db = SessionLocal()
    try:
        after = db.query(models.GeneModelAnnotation).count()
        new = (db.query(models.GeneModelAnnotation)
               .filter_by(version_label="gm-upload").one())
        assert after == before + 1
        assert new.gene_models_n == 31000
    finally:
        db.close()
