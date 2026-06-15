from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app import models

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


@router.get("/assemblies/{assembly_id}", name="assembly_detail")
def assembly_detail(assembly_id: int, request: Request, db: Session = Depends(get_db)):
    assembly = db.query(models.Assembly).filter(models.Assembly.id == assembly_id).first()
    if assembly is None:
        raise HTTPException(status_code=404, detail="Assembly not found")
    return templates.TemplateResponse("assembly_detail.html", {
        "request": request,
        "assembly": assembly,
    })
