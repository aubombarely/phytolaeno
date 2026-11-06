"""Build the real demo DB once and fetch portal pages from it in a separate interpreter.

The test session's app is bound to its own SQLite file (conftest.py), so pages
of the demo DB are rendered in a subprocess with DATABASE_URL pointing at it.
"""
import json
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def demo_db() -> Path:
    import tempfile
    db = Path(tempfile.mkdtemp(prefix="phytolaeno_demo_")) / "demo.db"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "demo.py"), "--db", str(db),
                        "--no_serve"], capture_output=True, text=True, cwd=REPO,
                       env={**os.environ, "PYTHONPATH": str(REPO)})
    assert r.returncode == 0, r.stderr[-2000:]
    return db


def fetch(paths: list[str]) -> dict[str, dict]:
    """{path: {"status": int, "text": str}} rendered against the demo DB."""
    code = (
        "import json, sys\n"
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "out = {}\n"
        "for p in json.loads(sys.argv[1]):\n"
        "    r = c.get(p)\n"
        "    out[p] = {'status': r.status_code, 'text': r.text}\n"
        "print(json.dumps(out))\n"
    )
    r = subprocess.run([sys.executable, "-c", code, json.dumps(paths)], capture_output=True,
                       text=True, cwd=REPO,
                       env={**os.environ, "PYTHONPATH": str(REPO),
                            "DATABASE_URL": f"sqlite:///{demo_db()}", "PHYTOLAENO_DEMO": "1"})
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def ids() -> dict[str, int]:
    """Look up demo ids by name: species, assembly version and annotation display name."""
    import sqlite3
    con = sqlite3.connect(demo_db())
    out = {f"species:{n}": i for i, n in con.execute("SELECT id, name FROM species")}
    out.update({f"assembly:{v}": i for i, v in con.execute("SELECT id, version FROM assemblies")})
    out.update({f"gm:{a}:{n}": i for i, a, n in con.execute(
        "SELECT g.id, a.version, g.display_name FROM gm_annotations g "
        "JOIN assemblies a ON a.id = g.assembly_id")})
    con.close()
    return out
