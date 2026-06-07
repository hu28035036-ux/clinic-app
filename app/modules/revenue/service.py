from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

from sqlalchemy.orm import Session

from app.models import models

from .schemas import RevenueGridIn, RevenueRecordEntry


PAYMENT_FIELDS = ("cash_amount", "card_amount", "transfer_amount", "other_amount")
PAYMENT_LABELS = {
    "cash_amount": "현금",
    "card_amount": "카드",
    "transfer_amount": "계좌",
    "other_amount": "기타",
}


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat((value or "").strip())
    except Exception as exc:
        raise ValueError("날짜 형식은 YYYY-MM-DD 이어야 합니다.") from exc


def resolve_range(date_from: str, date_to: str) -> tuple[date, date, list[str]]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start > end:
        raise ValueError("시작일이 종료일보다 늦을 수 없습니다.")
    days = (end - start).days + 1
    if days > 370:
        raise ValueError("조회 기간은 최대 370일입니다.")
    keys = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    return start, end, keys


def _category_id(value: str | None) -> str:
    return (value or "").strip()


def _amount(value) -> int:
    try:
        return max(0, int(value or 0))
    except Exception:
        return 0


def _total_from_parts(data) -> int:
    return sum(_amount(getattr(data, f, 0) if not isinstance(data, dict) else data.get(f)) for f in PAYMENT_FIELDS)


def serialize_category(c: models.EmployeeCategory) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "color": c.color or "#9CA3AF",
        "active": bool(c.active),
        "sort_order": c.sort_order or 0,
    }


def active_categories(db: Session) -> list[dict]:
    return [
        serialize_category(c)
        for c in db.query(models.EmployeeCategory)
        .filter(models.EmployeeCategory.active == True)  # noqa: E712
        .order_by(models.EmployeeCategory.sort_order, models.EmployeeCategory.name)
        .all()
    ]


def category_name_map(db: Session) -> dict[str, str]:
    return {
        c.id: c.name
        for c in db.query(models.EmployeeCategory).all()
    }


def serialize_record(rec: models.RevenueRecord | None, record_date: str, category_id: str, categories: dict[str, str] | None = None) -> dict:
    categories = categories or {}
    data = {
        "id": rec.id if rec else "",
        "record_date": record_date,
        "category_id": category_id,
        "category_name": categories.get(category_id, "전체") if category_id else "전체",
        "cash_amount": int(rec.cash_amount or 0) if rec else 0,
        "card_amount": int(rec.card_amount or 0) if rec else 0,
        "transfer_amount": int(rec.transfer_amount or 0) if rec else 0,
        "other_amount": int(rec.other_amount or 0) if rec else 0,
        "memo": (rec.memo or "") if rec else "",
        "created_at": rec.created_at.isoformat() if rec and rec.created_at else None,
        "updated_at": rec.updated_at.isoformat() if rec and rec.updated_at else None,
    }
    data["total_amount"] = _total_from_parts(data)
    return data


def list_records(db: Session, date_from: str, date_to: str, category_id: str = "") -> dict:
    start, end, date_keys = resolve_range(date_from, date_to)
    category_id = _category_id(category_id)
    categories = category_name_map(db)
    rows = (
        db.query(models.RevenueRecord)
        .filter(
            models.RevenueRecord.record_date >= start.isoformat(),
            models.RevenueRecord.record_date <= end.isoformat(),
            models.RevenueRecord.category_id == category_id,
        )
        .all()
    )
    by_date = {r.record_date: r for r in rows}
    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "category_id": category_id,
        "categories": active_categories(db),
        "records": [
            serialize_record(by_date.get(day), day, category_id, categories)
            for day in date_keys
        ],
    }


def _entry_has_value(entry: RevenueRecordEntry) -> bool:
    return _total_from_parts(entry) > 0 or bool((entry.memo or "").strip())


def upsert_grid(
    db: Session,
    payload: RevenueGridIn,
    *,
    log_callback: Callable | None = None,
    audit_callback: Callable | None = None,
) -> dict:
    start, end, date_keys = resolve_range(payload.date_from, payload.date_to)
    allowed_dates = set(date_keys)
    category_id = _category_id(payload.category_id)
    changed = {"upserted": 0, "deleted": 0}

    for entry in payload.entries:
        record_date = (entry.record_date or "").strip()
        if record_date not in allowed_dates:
            continue
        row_category = category_id
        rec = (
            db.query(models.RevenueRecord)
            .filter(
                models.RevenueRecord.record_date == record_date,
                models.RevenueRecord.category_id == row_category,
            )
            .first()
        )
        if not _entry_has_value(entry):
            if rec:
                rec_id = rec.id
                db.delete(rec)
                db.flush()
                if log_callback:
                    log_callback(db, "revenue_record", rec_id, "delete", None)
                changed["deleted"] += 1
            continue
        if not rec:
            rec = models.RevenueRecord(record_date=record_date, category_id=row_category)
            db.add(rec)
        rec.cash_amount = _amount(entry.cash_amount)
        rec.card_amount = _amount(entry.card_amount)
        rec.transfer_amount = _amount(entry.transfer_amount)
        rec.other_amount = _amount(entry.other_amount)
        rec.memo = (entry.memo or "").strip()[:500]
        rec.updated_at = datetime.utcnow()
        db.flush()
        if log_callback:
            log_callback(db, "revenue_record", rec.id, "upsert", rec)
        changed["upserted"] += 1

    if audit_callback:
        audit_callback(
            db,
            "revenue.records.grid.save",
            "",
            f"{start.isoformat()}~{end.isoformat()} category_id={category_id}",
        )
    return changed


def _records_for_period(db: Session, start: date, end: date, category_id: str) -> list[models.RevenueRecord]:
    return (
        db.query(models.RevenueRecord)
        .filter(
            models.RevenueRecord.record_date >= start.isoformat(),
            models.RevenueRecord.record_date <= end.isoformat(),
            models.RevenueRecord.category_id == category_id,
        )
        .order_by(models.RevenueRecord.record_date)
        .all()
    )


def _revenue_summary(records: list[models.RevenueRecord]) -> dict:
    by_payment = {
        key: {"key": key, "label": PAYMENT_LABELS[key], "amount": 0}
        for key in PAYMENT_FIELDS
    }
    daily = []
    total = 0
    for rec in records:
        row = serialize_record(rec, rec.record_date, rec.category_id)
        total += row["total_amount"]
        for key in PAYMENT_FIELDS:
            by_payment[key]["amount"] += row[key]
        daily.append({
            "date": rec.record_date,
            "total_amount": row["total_amount"],
            "cash_amount": row["cash_amount"],
            "card_amount": row["card_amount"],
            "transfer_amount": row["transfer_amount"],
            "other_amount": row["other_amount"],
        })
    return {
        "record_count": len(records),
        "revenue_total": total,
        "cash_amount": by_payment["cash_amount"]["amount"],
        "card_amount": by_payment["card_amount"]["amount"],
        "transfer_amount": by_payment["transfer_amount"]["amount"],
        "other_amount": by_payment["other_amount"]["amount"],
        "by_payment": list(by_payment.values()),
        "daily": daily,
    }


def _settlement_summary(db: Session, start: date, end: date, category_id: str) -> dict:
    q = db.query(models.SettlementRecord).filter(
        models.SettlementRecord.performed_on >= start.isoformat(),
        models.SettlementRecord.performed_on <= end.isoformat(),
    )
    if category_id:
        q = q.filter(models.SettlementRecord.employee_category_id_snapshot == category_id)
    records = q.all()
    quantity_total = 0
    price_total = 0
    incentive_total = 0
    employee_ids = set()
    treatment_ids = set()
    by_treatment: dict[str, dict] = {}
    for rec in records:
        qty = _amount(rec.quantity)
        rec_price_total = _amount(rec.price_snapshot) * qty
        rec_incentive_total = _amount(rec.incentive_amount)
        quantity_total += qty
        price_total += rec_price_total
        incentive_total += rec_incentive_total
        if rec.employee_id:
            employee_ids.add(rec.employee_id)
        if rec.treatment_id:
            treatment_ids.add(rec.treatment_id)
        treatment_key = rec.treatment_id or rec.treatment_code_snapshot or rec.treatment_name_snapshot or "-"
        treatment_row = by_treatment.setdefault(treatment_key, {
            "key": treatment_key,
            "treatment_id": rec.treatment_id or "",
            "treatment_name": rec.treatment_name_snapshot or "-",
            "treatment_short": rec.treatment_short_snapshot or rec.treatment_name_snapshot or "-",
            "quantity_total": 0,
            "price_total": 0,
            "incentive_total": 0,
            "record_count": 0,
        })
        treatment_row["quantity_total"] += qty
        treatment_row["price_total"] += rec_price_total
        treatment_row["incentive_total"] += rec_incentive_total
        treatment_row["record_count"] += 1
    return {
        "record_count": len(records),
        "quantity_total": quantity_total,
        "price_total": price_total,
        "incentive_total": incentive_total,
        "employee_count": len(employee_ids),
        "treatment_count": len(treatment_ids),
        "by_treatment": sorted(
            by_treatment.values(),
            key=lambda row: (-row["price_total"], str(row["treatment_short"] or row["treatment_name"])),
        ),
    }


def _previous_period(start: date, end: date) -> tuple[date, date]:
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return prev_start, prev_end


def _delta(current: int, previous: int) -> dict:
    amount = current - previous
    pct = None if previous == 0 else round((amount / previous) * 100, 1)
    return {"amount": amount, "pct": pct}


def stats(db: Session, date_from: str, date_to: str, category_id: str = "") -> dict:
    start, end, _ = resolve_range(date_from, date_to)
    category_id = _category_id(category_id)
    prev_start, prev_end = _previous_period(start, end)

    current_records = _records_for_period(db, start, end, category_id)
    previous_records = _records_for_period(db, prev_start, prev_end, category_id)
    current = _revenue_summary(current_records)
    previous = _revenue_summary(previous_records)
    settlement = _settlement_summary(db, start, end, category_id)

    revenue_total = current["revenue_total"]
    settlement["revenue_minus_settlement_price"] = revenue_total - settlement["price_total"]
    settlement["revenue_after_incentive"] = revenue_total - settlement["incentive_total"]
    settlement["incentive_rate"] = round((settlement["incentive_total"] / revenue_total) * 100, 1) if revenue_total else 0
    settlement["settlement_price_rate"] = round((settlement["price_total"] / revenue_total) * 100, 1) if revenue_total else 0

    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "category_id": category_id,
        "categories": active_categories(db),
        "compare_from": prev_start.isoformat(),
        "compare_to": prev_end.isoformat(),
        "current": current,
        "previous": previous,
        "delta": {
            "revenue_total": _delta(current["revenue_total"], previous["revenue_total"]),
            "record_count": _delta(current["record_count"], previous["record_count"]),
        },
        "settlement": settlement,
    }
