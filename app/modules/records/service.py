from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.models import models

# v1.3.37+: 기록 탭이 더 이상 고정(메뉴얼/C-Arm/리뷰이벤트)이 아니라,
# 치료항목 중 requires_record=True 인 항목으로 동적 구성된다.
# 호환을 위해 응답의 tab_key 에는 치료항목 code 를 그대로 사용한다.


def _serialize_category(c: models.EmployeeCategory) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "color": c.color or "#9CA3AF",
        "active": bool(c.active),
        "sort_order": c.sort_order or 0,
    }


def _serialize_employee(e: models.Employee) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "category_id": e.category_id,
        "color": e.color or "#9CA3AF",
        "active": bool(e.active),
        "sort_order": e.sort_order or 0,
    }


def serialize_entry(entry: models.RecordEntry) -> dict:
    record_date = entry.record_date
    if not record_date and entry.created_at:
        record_date = entry.created_at.date().isoformat()
    return {
        "id": entry.id,
        "tab_key": entry.tab_key,
        "treatment_id": entry.treatment_id or "",
        "record_date": record_date or "",
        "chart_no": entry.chart_no or "",
        "patient_name": entry.patient_name or "",
        "memo": entry.memo or "",
        "employee_id": entry.employee_id,
        "employee_name": entry.employee_name_snapshot or "",
        "employee_category_id": entry.employee_category_id_snapshot or "",
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def serialize_tab(t: models.Treatment) -> dict:
    """기록 탭 = 기록필요 치료항목. 기존 프론트 계약(tab_key/label/category_id) 유지.
    tab_key 는 치료항목 code 를 그대로 사용한다."""
    return {
        "id": t.id,
        "tab_key": t.code,
        "label": t.name,
        "category_id": t.category_id or "",
        "sort_order": t.sort_order or 0,
    }


def _record_treatments(db: Session) -> list[models.Treatment]:
    """기록 탭으로 노출할 치료항목 — requires_record & active, sort_order 순."""
    return (
        db.query(models.Treatment)
        .filter(models.Treatment.active == True,  # noqa: E712
                models.Treatment.requires_record == True)  # noqa: E712
        .order_by(models.Treatment.sort_order, models.Treatment.name)
        .all()
    )


def _treatment_for_tab(db: Session, tab_key: str) -> models.Treatment:
    """tab_key(=치료항목 code)로 기록필요 활성 치료항목을 찾는다 (신규 입력용)."""
    code = (tab_key or "").strip()
    t = db.query(models.Treatment).filter(models.Treatment.code == code).first()
    if t is None:
        raise ValueError("기록 탭(치료항목)을 찾을 수 없습니다.")
    if not t.active or not getattr(t, "requires_record", False):
        raise ValueError("기록 대상 치료항목이 아닙니다.")
    return t


def _treatment_for_entry(db: Session, entry: models.RecordEntry) -> models.Treatment:
    """기존 기록 항목이 속한 치료항목 (수정용). requires_record 여부는 따지지 않는다."""
    t = None
    if entry.treatment_id:
        t = db.get(models.Treatment, entry.treatment_id)
    if t is None:
        t = db.query(models.Treatment).filter(models.Treatment.code == entry.tab_key).first()
    if t is None:
        raise ValueError("기록 탭(치료항목)을 찾을 수 없습니다.")
    return t


def normalize_record_date(value: str | None = None) -> str:
    text = (value or "").strip()
    if not text:
        return date.today().isoformat()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("날짜 형식은 YYYY-MM-DD 이어야 합니다.") from exc


def _week_bounds(record_date_str: str) -> tuple[str, str, list[str]]:
    base = datetime.strptime(record_date_str, "%Y-%m-%d").date()
    start = base - timedelta(days=base.weekday())
    dates = [(start + timedelta(days=i)).isoformat() for i in range(7)]
    return dates[0], dates[-1], dates


def list_records(db: Session, record_date: str | None = None) -> dict:
    record_date_str = normalize_record_date(record_date)
    week_start, week_end, week_dates = _week_bounds(record_date_str)
    tabs = _record_treatments(db)
    categories = (
        db.query(models.EmployeeCategory)
        .filter(models.EmployeeCategory.active == True)  # noqa: E712
        .order_by(models.EmployeeCategory.sort_order, models.EmployeeCategory.name)
        .all()
    )
    employees = (
        db.query(models.Employee)
        .filter(models.Employee.active == True)  # noqa: E712
        .order_by(models.Employee.sort_order, models.Employee.name)
        .all()
    )
    entries = (
        db.query(models.RecordEntry)
        .filter(models.RecordEntry.record_date == record_date_str)
        .order_by(models.RecordEntry.created_at, models.RecordEntry.patient_name)
        .all()
    )
    weekly_entries = (
        db.query(models.RecordEntry)
        .filter(models.RecordEntry.record_date >= week_start,
                models.RecordEntry.record_date <= week_end)
        .all()
    )
    employee_names = {e.id: e.name for e in employees}
    counts: dict[str, dict[str, int]] = {}
    for entry in entries:
        counts.setdefault(entry.tab_key, {})
        counts[entry.tab_key][entry.employee_id] = (
            counts[entry.tab_key].get(entry.employee_id, 0) + 1
        )
        if not entry.employee_name_snapshot and entry.employee_id in employee_names:
            entry.employee_name_snapshot = employee_names[entry.employee_id]
    week_counts: dict[str, dict[str, int]] = {}
    for entry in weekly_entries:
        week_counts.setdefault(entry.tab_key, {})
        week_counts[entry.tab_key][entry.record_date] = (
            week_counts[entry.tab_key].get(entry.record_date, 0) + 1
        )
    return {
        "tabs": [serialize_tab(t) for t in tabs],
        "categories": [_serialize_category(c) for c in categories],
        "employees": [_serialize_employee(e) for e in employees],
        "entries": [serialize_entry(e) for e in entries],
        "counts": counts,
        "record_date": record_date_str,
        "week_start": week_start,
        "week_end": week_end,
        "week_dates": week_dates,
        "week_counts": week_counts,
    }


def update_tab_setting(
    db: Session,
    tab_key: str,
    *,
    label: str,
    category_id: str,
    log_callback: Callable | None = None,
) -> models.Treatment:
    """기록 탭(치료항목) 인라인 편집 — 이름/과를 해당 치료항목에 반영한다."""
    treatment = _treatment_for_tab(db, tab_key)
    label = (label or "").strip()
    if label:
        treatment.name = label[:50]
    category_id = (category_id or "").strip()
    if category_id:
        if not db.get(models.EmployeeCategory, category_id):
            raise ValueError("과를 찾을 수 없습니다.")
        treatment.category_id = category_id
    treatment.updated_at = datetime.utcnow()
    db.flush()
    if log_callback:
        log_callback(db, "treatment", treatment.id, "upsert", treatment)
    return treatment


def _validated_entry_values(
    db: Session,
    treatment: models.Treatment,
    *,
    record_date: str,
    chart_no: str,
    patient_name: str,
    memo: str,
    employee_id: str,
) -> tuple[str, str, str, str, models.Employee]:
    employee = db.get(models.Employee, employee_id)
    if not employee or not employee.active:
        raise ValueError("직원을 선택하세요.")
    if treatment.category_id and employee.category_id != treatment.category_id:
        raise ValueError("선택한 과의 직원만 입력할 수 있습니다.")
    chart_no = (chart_no or "").strip()[:30]
    patient_name = (patient_name or "").strip()[:50]
    memo = (memo or "").strip()[:200]
    if not chart_no and not patient_name:
        raise ValueError("차트번호 또는 성함을 입력하세요.")
    return normalize_record_date(record_date), chart_no, patient_name, memo, employee


def create_entry(
    db: Session,
    *,
    tab_key: str,
    record_date: str,
    chart_no: str,
    patient_name: str,
    memo: str,
    employee_id: str,
    log_callback: Callable | None = None,
) -> models.RecordEntry:
    treatment = _treatment_for_tab(db, tab_key)
    record_date_str, chart_no, patient_name, memo, employee = _validated_entry_values(
        db,
        treatment,
        record_date=record_date,
        chart_no=chart_no,
        patient_name=patient_name,
        memo=memo,
        employee_id=employee_id,
    )
    entry = models.RecordEntry(
        tab_key=treatment.code,
        treatment_id=treatment.id,
        record_date=record_date_str,
        chart_no=chart_no,
        patient_name=patient_name,
        memo=memo,
        employee_id=employee.id,
        employee_name_snapshot=employee.name,
        employee_category_id_snapshot=employee.category_id or "",
    )
    db.add(entry)
    db.flush()
    if log_callback:
        log_callback(db, "record_entry", entry.id, "upsert", entry)
    return entry


def update_entry(
    db: Session,
    entry_id: str,
    *,
    record_date: str,
    chart_no: str,
    patient_name: str,
    memo: str,
    employee_id: str,
    log_callback: Callable | None = None,
) -> models.RecordEntry:
    entry = db.get(models.RecordEntry, entry_id)
    if not entry:
        raise ValueError("기록을 찾을 수 없습니다.")
    treatment = _treatment_for_entry(db, entry)
    record_date_str, chart_no, patient_name, memo, employee = _validated_entry_values(
        db,
        treatment,
        record_date=record_date,
        chart_no=chart_no,
        patient_name=patient_name,
        memo=memo,
        employee_id=employee_id,
    )
    entry.record_date = record_date_str
    entry.chart_no = chart_no
    entry.patient_name = patient_name
    entry.memo = memo
    entry.employee_id = employee.id
    entry.employee_name_snapshot = employee.name
    entry.employee_category_id_snapshot = employee.category_id or ""
    entry.updated_at = datetime.utcnow()
    db.flush()
    if log_callback:
        log_callback(db, "record_entry", entry.id, "upsert", entry)
    return entry


def delete_entry(
    db: Session,
    entry_id: str,
    *,
    log_callback: Callable | None = None,
) -> None:
    entry = db.get(models.RecordEntry, entry_id)
    if not entry:
        raise ValueError("기록을 찾을 수 없습니다.")
    db.delete(entry)
    if log_callback:
        log_callback(db, "record_entry", entry_id, "delete", None)
