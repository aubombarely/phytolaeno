"""The demo builder runs end to end and its database renders in the portal."""
import os
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
    assert db.exists() and db.stat().st_size > 0
    assert "Real (GAQET benchmark): Arabidopsis thaliana" in r.stderr
    assert "17 gene-model annotations" in r.stderr
    assert "Synthetic: 11 species" in r.stderr

    # Render the demo database in a separate interpreter (the test session's
    # app is bound to its own SQLite file).
    check = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "for p in ['/', '/species', '/plots', '/species/1', '/assemblies/1',\n"
        "          '/annotations/gm/1', '/annotations/re/1']:\n"
        "    r = c.get(p); assert r.status_code == 200, p\n"
        "assert 'synthetic' in c.get('/').text\n"
        "assert 'Arabidopsis thaliana' in c.get('/species').text\n"
        "assert 'real' in c.get('/').text and 'synthetic' in c.get('/').text\n"
    )
    r2 = subprocess.run([sys.executable, "-c", check], capture_output=True, text=True,
                        cwd=REPO, env={**os.environ, "PYTHONPATH": str(REPO),
                                       "DATABASE_URL": f"sqlite:///{db}",
                                       "PHYTOLAENO_DEMO": "1"})
    assert r2.returncode == 0, r2.stderr[-2000:]
