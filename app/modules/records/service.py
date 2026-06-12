from __future__ import annotations

from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.models import models

RECORD_TABS = (
    {"id": "record_tab_manual", "tab_key": "manual", "label": "메뉴얼", "sort_order": 1},
    {"id": "record_tab_carm", "tab_key": "carm", "label": "C-Arm", "sort_order": 2},
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
    return {
        "id": entry.id,
        "tab_key": entry.tab_key,
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


def list_records(db: Session) -> dict:
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
        .order_by(models.RecordEntry.created_at, models.RecordEntry.patient_name)
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
    return {
        "tabs": [serialize_setting(s) for s in settings],
        "categories": [_serialize_category(c) for c in categories],
        "employees": [_serialize_employee(e) for e in employees],
        "entries": [serialize_entry(e) for e in entries],
        "counts": counts,
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


def create_entry(
    db: Session,
    *,
    tab_key: str,
    chart_no: str,
    patient_name: str,
    employee_id: str,
    log_callback: Callable | None = None,
) -> models.RecordEntry:
    setting = next((s for s in ensure_default_settings(db) if s.tab_key == tab_key), None)
    if setting is None:
        raise ValueError("기록 탭을 찾을 수 없습니다.")
    employee = db.get(models.Employee, employee_id)
    if not employee or not employee.active:
        raise ValueError("직원을 선택하세요.")
    if setting.category_id and employee.category_id != setting.category_id:
        raise ValueError("선택한 과의 직원만 입력할 수 있습니다.")
    chart_no = (chart_no or "").strip()[:30]
    patient_name = (patient_name or "").strip()[:50]
    if not chart_no and not patient_name:
        raise ValueError("차트번호 또는 성함을 입력하세요.")
    entry = models.RecordEntry(
        tab_key=tab_key,
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
