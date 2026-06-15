from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import engine
from app import models
from app.routers import species, assemblies, annotations, upload, plots

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Phytolaeno", description="Plant Genome Annotation Archive")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(species.router)
app.include_router(assemblies.router)
app.include_router(annotations.router)
app.include_router(upload.router)
app.include_router(plots.router)
