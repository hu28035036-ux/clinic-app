from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.routers.api import _log, audit, require_admin

from . import service
from .schemas import DailyReportIn, RevenueGridIn

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


@router.get("/daily-report")
def get_daily_work_report(
    date: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        return service.get_daily_report(db, date)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/daily-medical-summary/import")
async def import_daily_medical_summary(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        content = await file.read()
        data = service.import_medical_summaries_from_excel(
            db,
            content,
            file.filename or "",
            log_callback=_log,
            audit_callback=audit,
        )
        db.commit()
        data["ok"] = True
        return data
    except ValueError as exc:
        db.rollback()
        raise _bad_request(exc) from exc


@router.post("/daily-report")
def save_daily_work_report(
    payload: DailyReportIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        changed = service.save_daily_report(
            db, payload, log_callback=_log, audit_callback=audit
        )
        db.commit()
        data = service.get_daily_report(db, payload.report_date)
        data["ok"] = True
        data["changed"] = changed
        return data
    except ValueError as exc:
        db.rollback()
        raise _bad_request(exc) from exc
