"""Shared fixtures: run the portal against a throw-away SQLite database.

DATABASE_URL must be set before ``app`` is imported, because
``app.database`` builds the engine at import time.
"""
import os
import tempfile
from pathlib import Path

import pytest

_TMPDIR = tempfile.mkdtemp(prefix="phytolaeno_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMPDIR) / 'test.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def seeded_ids() -> dict:
    """Insert one species, assembly, protocol, gene-model and repeat annotation."""
    db = SessionLocal()
    try:
        sp = models.Species(name="Testus plantae", ncbi_taxid=1,
                            family="Testaceae", lineage="Viridiplantae")
        db.add(sp)
        db.flush()
        asm = models.Assembly(species_id=sp.id, version="TestAsm1",
                              size_gb=0.5, status="public",
                              busco_viridi_raw="C:98.1%[S:76.0%,D:22.1%],F:1.2%,M:0.7%",
                              busco_viridi_complete=98.1)
        db.add(asm)
        db.flush()
        prot = models.AnnotationProtocol(tool="ANNEVO", tool_version="1.0")
        db.add(prot)
        db.flush()
        gm = models.GeneModelAnnotation(assembly_id=asm.id, protocol_id=prot.id,
                                        version_label="gm1", gene_models_n=25000)
        re_ = models.RepeatAnnotation(assembly_id=asm.id, protocol_id=prot.id,
                                      version_label="re1", total_pct=45.0,
                                      parsed_results={"LTR": 34.9, "DNA": 7.8})
        db.add_all([gm, re_])
        db.commit()
        return {"species": sp.id, "assembly": asm.id, "gm": gm.id, "re": re_.id}
    finally:
        db.close()


@pytest.fixture(scope="session")
def client(seeded_ids) -> TestClient:
    return TestClient(app)
