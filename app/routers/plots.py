from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.plot_data import (build_figures, build_species_comparison, parse_plot_params,
                            selector_options)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


@router.get("/plots", name="plots")
def plots(request: Request, species_id: str | None = None, assembly_id: str | None = None,
          annotation_ids: str | None = None, metric: str | None = None,
          weights: str | None = None, db: Session = Depends(get_db)):
    params = parse_plot_params(species_id, assembly_id, annotation_ids, metric, weights)
    figures = build_figures(db, params)
    return templates.TemplateResponse("plots.html", {
        "request": request, "figures": figures, "params": params,
        "options": selector_options(db, params), "form_action": "/plots",
    })


@router.get("/compare", name="compare")
def compare(request: Request, species_id: str | None = None, metric: str | None = None,
            weights: str | None = None, db: Session = Depends(get_db)):
    params = parse_plot_params(species_id, None, None, metric, weights)
    if params.species_id is not None and db.get(models.Species, params.species_id) is None:
        params.notices.append(f"Species {params.species_id} not found.")
        params.species_id = None
    return templates.TemplateResponse("compare.html", {
        "request": request, "figures": build_species_comparison(db, params), "params": params,
        "options": selector_options(db, params),
    })
