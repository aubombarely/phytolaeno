from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path

from app.database import get_db
from app import models
from app.plot_data import build_figures, parse_plot_params, selector_options

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


@router.get("/", name="index")
def index(request: Request, db: Session = Depends(get_db)):
    n_species   = db.query(func.count(models.Species.id)).scalar()
    n_assemblies = db.query(func.count(models.Assembly.id)).scalar()
    n_gm        = db.query(func.count(models.GeneModelAnnotation.id)).scalar()
    n_re        = db.query(func.count(models.RepeatAnnotation.id)).scalar()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "n_species": n_species,
        "n_assemblies": n_assemblies,
        "n_gm": n_gm,
        "n_re": n_re,
    })


@router.get("/species", name="species_list")
def species_list(
    request: Request,
    search: str = "",
    family: str = "",
    lineage: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):
    PAGE_SIZE = 50
    q = db.query(models.Species)
    if search:
        q = q.filter(models.Species.name.ilike(f"%{search}%"))
    if family:
        q = q.filter(models.Species.family.ilike(f"%{family}%"))
    if lineage:
        q = q.filter(models.Species.lineage.ilike(f"%{lineage}%"))

    total   = q.count()
    species = q.order_by(models.Species.name).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
    families = [r[0] for r in db.query(models.Species.family).distinct().order_by(models.Species.family).all() if r[0]]
    lineages = [r[0] for r in db.query(models.Species.lineage).distinct().order_by(models.Species.lineage).all() if r[0]]

    return templates.TemplateResponse("species_list.html", {
        "request": request,
        "species": species,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "pages": (total + PAGE_SIZE - 1) // PAGE_SIZE,
        "search": search,
        "family": family,
        "lineage": lineage,
        "families": families,
        "lineages": lineages,
    })


@router.get("/species/{species_id}", name="species_detail")
def species_detail(species_id: int, request: Request, assembly_id: str | None = None,
                   annotation_ids: str | None = None, metric: str | None = None,
                   weights: str | None = None, db: Session = Depends(get_db)):
    sp = db.query(models.Species).filter(models.Species.id == species_id).first()
    if sp is None:
        raise HTTPException(status_code=404, detail="Species not found")
    params = parse_plot_params(str(species_id), assembly_id, annotation_ids, metric, weights)
    figures = build_figures(db, params) if sp.assemblies else None
    return templates.TemplateResponse("species_detail.html", {
        "request": request,
        "species": sp,
        "figures": figures,
        "params": params,
        "options": selector_options(db, params),
        "form_action": f"/species/{species_id}",
    })
