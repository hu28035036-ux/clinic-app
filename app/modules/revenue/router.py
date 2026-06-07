from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.routers.api import _log, audit, require_admin

from . import service
from .schemas import RevenueGridIn

router = APIRouter(prefix="/api/revenue", tags=["revenue"])


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _require_category(db: Session, category_id: str):
    if category_id and not db.get(models.EmployeeCategory, category_id):
        raise HTTPException(404, "과를 찾을 수 없습니다.")


@router.get("/records")
def get_revenue_records(
    date_from: str,
    date_to: str,
    category_id: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    _require_category(db, category_id)
    try:
        return service.list_records(db, date_from, date_to, category_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/records/grid")
def save_revenue_records_grid(
    payload: RevenueGridIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    _require_category(db, payload.category_id)
    try:
        changed = service.upsert_grid(db, payload, log_callback=_log, audit_callback=audit)
        db.commit()
        data = service.list_records(db, payload.date_from, payload.date_to, payload.category_id)
        data["ok"] = True
        data["changed"] = changed
        return data
    except ValueError as exc:
        db.rollback()
        raise _bad_request(exc) from exc


@router.get("/stats")
def get_revenue_stats(
    date_from: str,
    date_to: str,
    category_id: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    _require_category(db, category_id)
    try:
        return service.stats(db, date_from, date_to, category_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
