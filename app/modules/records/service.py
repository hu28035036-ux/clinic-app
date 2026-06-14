from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.models import models

RECORD_TABS = (
    {"id": "record_tab_manual", "tab_key": "manual", "label": "메뉴얼", "sort_order": 1},
    {"id": "record_tab_carm", "tab_key": "carm", "label": "C-Arm", "sort_order": 2},
    {"id": "record_tab_review_event", "tab_key": "review_event", "label": "리뷰이벤트", "sort_order": 3},
)


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
        "record_date": record_date or "",
        "chart_no": entry.chart_no or "",
        "patient_name": entry.patient_name or "",
        "employee_id": entry.employee_id,
        "employee_name": entry.employee_name_snapshot or "",
        "employee_category_id": entry.employee_category_id_snapshot or "",
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def serialize_setting(setting: models.RecordTabSetting) -> dict:
    return {
        "id": setting.id,
        "tab_key": setting.tab_key,
        "label": setting.label,
        "category_id": setting.category_id or "",
        "sort_order": setting.sort_order or 0,
    }


def ensure_default_settings(db: Session) -> list[models.RecordTabSetting]:
    rows = {
        row.tab_key: row
        for row in db.query(models.RecordTabSetting).all()
    }
    changed = False
    for item in RECORD_TABS:
        if item["tab_key"] in rows:
            continue
        setting = models.RecordTabSetting(
            id=item["id"],
            tab_key=item["tab_key"],
            label=item["label"],
            category_id="",
            sort_order=item["sort_order"],
        )
        db.add(setting)
        rows[item["tab_key"]] = setting
        changed = True
    if changed:
        db.flush()
    return sorted(rows.values(), key=lambda x: (x.sort_order or 0, x.tab_key))


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
    settings = ensure_default_settings(db)
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
        "tabs": [serialize_setting(s) for s in settings],
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
) -> models.RecordTabSetting:
    setting = next((s for s in ensure_default_settings(db) if s.tab_key == tab_key), None)
    if setting is None:
        raise ValueError("기록 탭을 찾을 수 없습니다.")
    category_id = (category_id or "").strip()
    if category_id and not db.get(models.EmployeeCategory, category_id):
        raise ValueError("과를 찾을 수 없습니다.")
    label = (label or "").strip()
    if not label:
        label = next((x["label"] for x in RECORD_TABS if x["tab_key"] == tab_key), tab_key)
    setting.label = label[:30]
    setting.category_id = category_id
    setting.updated_at = datetime.utcnow()
    db.flush()
    if log_callback:
        log_callback(db, "record_tab_setting", setting.id, "upsert", setting)
    return setting


def _setting_for_tab(db: Session, tab_key: str) -> models.RecordTabSetting:
    setting = next((s for s in ensure_default_settings(db) if s.tab_key == tab_key), None)
    if setting is None:
        raise ValueError("기록 탭을 찾을 수 없습니다.")
    return setting


def _validated_entry_values(
    db: Session,
    setting: models.RecordTabSetting,
    *,
    record_date: str,
    chart_no: str,
    patient_name: str,
    employee_id: str,
) -> tuple[str, str, str, models.Employee]:
    employee = db.get(models.Employee, employee_id)
    if not employee or not employee.active:
        raise ValueError("직원을 선택하세요.")
    if setting.category_id and employee.category_id != setting.category_id:
        raise ValueError("선택한 과의 직원만 입력할 수 있습니다.")
    chart_no = (chart_no or "").strip()[:30]
    patient_name = (patient_name or "").strip()[:50]
    if not chart_no and not patient_name:
        raise ValueError("차트번호 또는 성함을 입력하세요.")
    return normalize_record_date(record_date), chart_no, patient_name, employee


def create_entry(
    db: Session,
    *,
    tab_key: str,
    record_date: str,
    chart_no: str,
    patient_name: str,
    employee_id: str,
    log_callback: Callable | None = None,
) -> models.RecordEntry:
    setting = _setting_for_tab(db, tab_key)
    record_date_str, chart_no, patient_name, employee = _validated_entry_values(
        db,
        setting,
        record_date=record_date,
        chart_no=chart_no,
        patient_name=patient_name,
        employee_id=employee_id,
    )
    entry = models.RecordEntry(
        tab_key=tab_key,
        record_date=record_date_str,
        chart_no=chart_no,
        patient_name=patient_name,
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
    employee_id: str,
    log_callback: Callable | None = None,
) -> models.RecordEntry:
    entry = db.get(models.RecordEntry, entry_id)
    if not entry:
        raise ValueError("기록을 찾을 수 없습니다.")
    setting = _setting_for_tab(db, entry.tab_key)
    record_date_str, chart_no, patient_name, employee = _validated_entry_values(
        db,
        setting,
        record_date=record_date,
        chart_no=chart_no,
        patient_name=patient_name,
        employee_id=employee_id,
    )
    entry.record_date = record_date_str
    entry.chart_no = chart_no
    entry.patient_name = patient_name
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
