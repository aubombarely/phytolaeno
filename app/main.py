import csv
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import engine
from app import models
from app.routers import species, assemblies, annotations, upload, plots
from app.links import species_links
from app.metrics import annotation_tags

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Phytolaeno", description="Plant Genome Annotation Archive")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(species.router)
app.include_router(assemblies.router)
app.include_router(annotations.router)
app.include_router(upload.router)
app.include_router(plots.router)

# Demo mode (scripts/demo.py): show the demo banner on every page.
DEMO_MODE = os.getenv("PHYTOLAENO_DEMO") == "1"


def _load_tag_explanations() -> dict[str, str]:
    """Tag explanations from demo/data/descriptions.tsv (level == "tag"), if present."""
    path = BASE_DIR.parent / "demo" / "data" / "descriptions.tsv"
    if not path.exists():
        return {}
    with open(path, newline="") as fh:
        return {r["key"]: r["description"] for r in csv.DictReader(fh, delimiter="\t")
                if r.get("level") == "tag"}


_TAG_EXPLANATIONS = _load_tag_explanations()
for _router_module in (species, assemblies, annotations, upload, plots):
    _env = _router_module.templates.env
    _env.globals.update(DEMO_MODE=DEMO_MODE, annotation_tags=annotation_tags,
                        species_links=species_links, tag_explanations=_TAG_EXPLANATIONS)
