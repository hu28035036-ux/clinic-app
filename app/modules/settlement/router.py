from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...routers.api import _log, audit, require_admin
from . import service
from .schemas import SettlementGridIn

router = APIRouter(prefix="/api/settlement", tags=["settlement"])


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/records")
def get_records(
    date_from: str,
    date_to: str,
    category_id: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        return service.get_grid(db, date_from, date_to, category_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/records/grid")
def get_records_grid(
    date_from: str,
    date_to: str,
    category_id: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        return service.get_grid(db, date_from, date_to, category_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/records/grid")
def save_records_grid(
    payload: SettlementGridIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        changed = service.upsert_grid(
            db,
            payload,
            log_callback=None if payload.silent else _log,
            audit_callback=None if payload.silent else audit,
        )
        db.commit()
        data = service.get_grid(db, payload.date_from, payload.date_to, payload.category_id)
        data["ok"] = True
        data["changed"] = changed
        return data
    except ValueError as exc:
        db.rollback()
        raise _bad_request(exc) from exc


@router.get("/reports/incentives")
def get_incentive_report(
    date_from: str,
    date_to: str,
    category_id: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        return service.report_incentives(db, date_from, date_to, category_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/reports/incentives.xlsx")
def export_incentive_report_xlsx(
    date_from: str,
    date_to: str,
    category_id: str = "",
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        buf, filename = service.build_incentive_workbook(db, date_from, date_to, category_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )
