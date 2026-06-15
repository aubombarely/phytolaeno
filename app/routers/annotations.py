from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app import models

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


@router.get("/annotations/gm/{annotation_id}", name="gm_detail")
def gm_detail(annotation_id: int, request: Request, db: Session = Depends(get_db)):
    ann = db.query(models.GeneModelAnnotation).filter(
        models.GeneModelAnnotation.id == annotation_id
    ).first()
    return templates.TemplateResponse("gm_annotation_detail.html", {
        "request": request,
        "ann": ann,
    })


@router.get("/annotations/re/{annotation_id}", name="re_detail")
def re_detail(annotation_id: int, request: Request, db: Session = Depends(get_db)):
    ann = db.query(models.RepeatAnnotation).filter(
        models.RepeatAnnotation.id == annotation_id
    ).first()
    return templates.TemplateResponse("re_annotation_detail.html", {
        "request": request,
        "ann": ann,
    })
