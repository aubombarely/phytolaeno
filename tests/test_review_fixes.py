"""Regression tests for the final-review findings."""
from sqlalchemy import create_engine, inspect, text

from app import models
from app.database import SessionLocal
from app.utils import parse_busco


def test_pages_survive_upload_next_to_scored_annotations(client, seeded_ids):
    db = SessionLocal()
    try:
        gm = db.get(models.GeneModelAnnotation, seeded_ids["gm"])
        gm.gas_score = 90.0                       # one scored, the upload will be unscored
        db.commit()
    finally:
        db.close()
    r = client.post("/upload/gm", data={"assembly_id": seeded_ids["assembly"], "tool": "X"},
                    follow_redirects=False)
    assert r.status_code in (200, 303)
    for path in (f"/assemblies/{seeded_ids['assembly']}", f"/species/{seeded_ids['species']}"):
        assert client.get(path).status_code == 200, path


def test_parse_busco_truncated_string_like_gaqet():
    b = parse_busco("C:92.9%[S:89.9%,D:3.1%],F:4.7%,M:2.4")
    assert b["complete"] == 92.9 and b["missing"] == 2.4
    assert parse_busco("C:99.5%[S:98.6%,D:0.9%],F:0.0%,M:0.5%,n:425")["complete"] == 99.5


def test_upgrade_adds_missing_columns_to_existing_db(tmp_path):
    from app.schema_upgrade import ensure_columns
    eng = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as con:                       # an old (v0.2) table without the new columns
        con.execute(text("CREATE TABLE assemblies (id INTEGER PRIMARY KEY, species_id INTEGER, "
                         "version VARCHAR)"))
    added = ensure_columns(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("assemblies")}
    assert {"assembly_type", "n90_bp", "plastid", "source_url"} <= cols
    assert "assemblies.assembly_type" in added
    assert ensure_columns(eng) == []               # idempotent
