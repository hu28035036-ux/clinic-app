from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.api import _log, audit

from . import service
from .schemas import RecordEntryIn, RecordTabSettingIn

router = APIRouter(prefix="/api/records", tags=["records"])


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("")
def get_records(db: Session = Depends(get_db)):
    return service.list_records(db)


@router.put("/tabs/{tab_key}")
def update_record_tab(
    tab_key: str,
    payload: RecordTabSettingIn,
    db: Session = Depends(get_db),
):
    try:
        setting = service.update_tab_setting(
            db,
            tab_key,
            label=payload.label,
            category_id=payload.category_id,
            log_callback=_log,
        )
        audit(db, "records.tab.update", setting.id, f"tab={tab_key} label={setting.label}")
        db.commit()
        return service.serialize_setting(setting)
    except ValueError as exc:
        db.rollback()
        raise _bad_request(exc) from exc


@router.post("/entries")
def create_record_entry(
    payload: RecordEntryIn,
    db: Session = Depends(get_db),
):
    try:
        entry = service.create_entry(
            db,
            tab_key=payload.tab_key,
            chart_no=payload.chart_no,
            patient_name=payload.patient_name,
            employee_id=payload.employee_id,
            log_callback=_log,
        )
        audit(db, "records.entry.create", entry.id, f"tab={entry.tab_key} employee={entry.employee_name_snapshot}")
        db.commit()
        db.refresh(entry)
        return service.serialize_entry(entry)
    except ValueError as exc:
        db.rollback()
        raise _bad_request(exc) from exc


@router.delete("/entries/{entry_id}")
def delete_record_entry(
    entry_id: str,
    db: Session = Depends(get_db),
):
    try:
        service.delete_entry(db, entry_id, log_callback=_log)
        audit(db, "records.entry.delete", entry_id, "")
        db.commit()
        return {"ok": True}
    except ValueError as exc:
        db.rollback()
        raise _bad_request(exc) from exc
