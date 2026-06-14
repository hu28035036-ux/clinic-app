import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.routers.api import _log, audit, require_admin

from . import service
from .schemas import DailyReportIn, RevenueGridIn

router = APIRouter(prefix="/api/revenue", tags=["revenue"])


def _get_or_create_system_setting(db: Session) -> models.SystemSetting:
    setting = db.query(models.SystemSetting).first()
    if not setting:
        setting = models.SystemSetting(
            id=1,
            manual_slot_limit=None,
            sms_template="",
            auto_backup_enabled=True,
            auto_backup_interval_min=60,
            auto_backup_keep_count=30,
            revenue_ui_settings_json="{}",
        )
        db.add(setting)
        db.flush()
    return setting


def _all_revenue_ui_fields() -> list[str]:
    return [*service.PAYMENT_FIELDS, *service.REVENUE_TOTAL_LABELS.keys()]


def _normalize_key_list(values, *, default_all: bool = False) -> list[str]:
    allowed = set(_all_revenue_ui_fields())
    out: list[str] = []
    if isinstance(values, list):
        for raw in values:
            key = str(raw or "").strip()
            if key in allowed and key not in out:
                out.append(key)
    if default_all and not out:
        out = _all_revenue_ui_fields()
    return out


def _normalize_field_order(values) -> list[str]:
    out = _normalize_key_list(values)
    for key in _all_revenue_ui_fields():
        if key not in out:
            out.append(key)
    return out


def _normalize_labels(values) -> dict[str, str]:
    allowed = set(_all_revenue_ui_fields())
    out: dict[str, str] = {}
    if isinstance(values, dict):
        for raw_key, raw_label in values.items():
            key = str(raw_key or "").strip()
            label = str(raw_label or "").strip()
            if key in allowed and label:
                out[key] = label[:30]
    return out


def _formula_allowed_keys(total_key: str) -> set[str]:
    totals = list(service.REVENUE_TOTAL_LABELS.keys())
    total_index = totals.index(total_key) if total_key in totals else 0
    return set(service.PAYMENT_FIELDS) | set(totals[:total_index])


def _normalize_formulas(values) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    if not isinstance(values, dict):
        return out
    for total_key in service.REVENUE_TOTAL_LABELS.keys():
        raw_terms = values.get(total_key)
        if not isinstance(raw_terms, list):
            continue
        allowed = _formula_allowed_keys(total_key)
        terms = []
        for raw in raw_terms:
            if not isinstance(raw, dict):
                continue
            key = str(raw.get("key") or "").strip()
            if key not in allowed:
                continue
            terms.append({
                "type": "total" if key in service.REVENUE_TOTAL_LABELS else "field",
                "key": key,
                "sign": -1 if int(raw.get("sign") or 1) < 0 else 1,
            })
        if terms:
            out[total_key] = terms
    return out


def _normalize_ui_settings(raw) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    out = {}
    labels = _normalize_labels(raw.get("field_labels"))
    order = _normalize_field_order(raw.get("field_order")) if "field_order" in raw else []
    formulas = _normalize_formulas(raw.get("total_formulas"))
    daily_fields = _normalize_key_list(raw.get("daily_fields"))
    if labels:
        out["field_labels"] = labels
    if order:
        out["field_order"] = order
    if formulas:
        out["total_formulas"] = formulas
    if daily_fields:
        out["daily_fields"] = daily_fields
    return out


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _require_category(db: Session, category_id: str):
    if category_id and not db.get(models.EmployeeCategory, category_id):
        raise HTTPException(404, "과를 찾을 수 없습니다.")


@router.get("/ui-settings")
def get_revenue_ui_settings(
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    setting = _get_or_create_system_setting(db)
    return {"settings": _normalize_ui_settings(setting.revenue_ui_settings_json or "{}")}


@router.post("/ui-settings")
def save_revenue_ui_settings(
    payload: dict,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    setting = _get_or_create_system_setting(db)
    settings = _normalize_ui_settings(payload.get("settings") if isinstance(payload, dict) else payload)
    setting.revenue_ui_settings_json = json.dumps(settings, ensure_ascii=False)
    setting.updated_at = datetime.utcnow()
    db.flush()
    _log(db, "system_setting", str(setting.id), "upsert", setting)
    audit(db, "revenue.ui_settings.save", str(setting.id))
    db.commit()
    return {"ok": True, "settings": settings}


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


@router.post("/records/import-preview")
async def preview_revenue_records_import(
    file: UploadFile = File(...),
    labels_json: str = Form(""),
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    try:
        labels = json.loads(labels_json or "{}")
        if not isinstance(labels, dict):
            labels = {}
    except Exception:
        labels = {}
    try:
        content = await file.read()
        data = service.preview_records_from_excel(
            db,
            content,
            file.filename or "",
            labels={str(k): str(v) for k, v in labels.items()},
        )
        data["ok"] = True
        return data
    except ValueError as exc:
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
