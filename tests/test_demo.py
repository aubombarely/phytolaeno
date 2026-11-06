"""The demo builder loads the real 3-species benchmark and the portal renders it."""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_demo_builds_database(tmp_path):
    db = tmp_path / "demo.db"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "demo.py"),
                        "--db", str(db), "--no_serve"],
                       capture_output=True, text=True, cwd=REPO,
                       env={**os.environ, "PYTHONPATH": str(REPO)})
    assert r.returncode == 0, r.stderr[-2000:]
    assert "3 species, 5 assemblies, 41 gene-model annotations" in r.stderr

    con = sqlite3.connect(db)
    n_gm, n_gas = con.execute(
        "SELECT COUNT(*), COUNT(gas_score) FROM gm_annotations").fetchone()
    n_ref = con.execute(
        "SELECT COUNT(*) FROM gm_annotations WHERE is_reference = 1").fetchone()[0]
    con.close()
    assert (n_gm, n_gas, n_ref) == (41, 41, 8)

    check = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "for p in ['/', '/species', '/plots', '/species/1', '/assemblies/1',\n"
        "          '/annotations/gm/1', '/annotations/re/1']:\n"
        "    r = c.get(p); assert r.status_code == 200, p\n"
        "home = c.get('/').text\n"
        "assert 'synthetic' not in home.lower()\n"
        "assert 'real data' in home\n"
        "sp = c.get('/species').text\n"
        "for name in ('Arabidopsis thaliana', 'Oryza sativa', 'Cucumis sativus'):\n"
        "    assert name in sp, name\n"
    )
    r2 = subprocess.run([sys.executable, "-c", check], capture_output=True, text=True,
                        cwd=REPO, env={**os.environ, "PYTHONPATH": str(REPO),
                                       "DATABASE_URL": f"sqlite:///{db}",
                                       "PHYTOLAENO_DEMO": "1"})
    assert r2.returncode == 0, r2.stderr[-2000:]
