"""환자 차팅 도메인 로직.

- 차트는 PatientChart (appointment_id UNIQUE → 한 치료완료 = 차트 1장).
- 차팅 탭은 approved 예약을 방문일 단위로 묶어 보여주며, 각 예약에 차트 요약을 embed.
  (patient_history(api.py)의 날짜묶기 형식과 동일하나, 환자관리 탭 동작에 영향이
   없도록 본 모듈에서 독립 구현 — chart 요약 embed 가 차팅 탭 전용이기 때문.)
"""

from __future__ import annotations

import json
from collections import OrderedDict

from sqlalchemy.orm import Session

from app.models import models


def _parse_codes(raw: str | None) -> list:
    try:
        v = json.loads(raw or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def serialize_chart(ch: models.PatientChart) -> dict:
    """차트 단건 응답 (작성/조회 공통)."""
    return {
        "id": ch.id,
        "appointment_id": ch.appointment_id,
        "patient_id": ch.patient_id,
        "content": ch.content or "",
        "treatment_start_date": ch.treatment_start_date or "",
        "session_no": ch.session_no,
        "author_id": ch.author_id,
        "author_name": ch.author_name_snapshot or "",
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
    }


def _chart_summary(ch: models.PatientChart) -> dict:
    """치료내역 목록에 얹는 가벼운 요약 (작성 여부/작성자/시각)."""
    return {
        "id": ch.id,
        "author_id": ch.author_id,
        "author_name": ch.author_name_snapshot or "",
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
        "has_content": bool((ch.content or "").strip()),
        "session_no": ch.session_no,
    }


def get_chart_by_appointment(db: Session, appointment_id: str) -> models.PatientChart | None:
    return (
        db.query(models.PatientChart)
        .filter(models.PatientChart.appointment_id == appointment_id)
        .first()
    )


def upsert_chart(
    db: Session,
    appointment: models.Appointment,
    *,
    content: str = "",
    treatment_start_date: str = "",
    session_no: int | None = None,
    author_id: str = "",
    log_callback=None,
) -> models.PatientChart:
    """차트 생성 또는 수정(appointment_id 기준 upsert).

    호출 전 router 에서 예약 존재 + status=='approved' 를 검증한다.
    content 는 SOAP 통합 본문(단일 텍스트). treatment_start_date(치료 시작일)와
    session_no(회차)는 선택 입력. author_id 가 비면 예약 담당치료사
    (therapist_id)로 폴백하고 이름 스냅샷을 보존.
    """
    resolved_author = (author_id or "").strip() or appointment.therapist_id
    author_name = ""
    if resolved_author:
        emp = db.get(models.Employee, resolved_author)
        author_name = emp.name if emp else ""

    start_date = (treatment_start_date or "").strip()
    sess = session_no if (session_no and session_no > 0) else None

    ch = get_chart_by_appointment(db, appointment.id)
    if ch is None:
        ch = models.PatientChart(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            content=content or "",
            treatment_start_date=start_date,
            session_no=sess,
            author_id=resolved_author or None,
            author_name_snapshot=author_name,
        )
        db.add(ch)
    else:
        ch.content = content or ""
        ch.treatment_start_date = start_date
        ch.session_no = sess
        ch.author_id = resolved_author or None
        ch.author_name_snapshot = author_name
        ch.patient_id = appointment.patient_id  # 정합성 유지(정본 = 예약)

    db.flush()
    if log_callback:
        log_callback(db, "patient_chart", ch.id, "upsert", ch)
    return ch


def get_patient_chart_history(db: Session, patient_id: str) -> dict:
    """차팅 탭 좌측: approved 방문을 날짜별로 묶고 각 예약에 차트 요약을 embed."""
    rows = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.patient_id == patient_id,
            models.Appointment.status == "approved",
        )
        .order_by(models.Appointment.start_at.desc())
        .all()
    )

    appt_ids = [a.id for a in rows]
    charts: dict[str, models.PatientChart] = {}
    if appt_ids:
        for ch in (
            db.query(models.PatientChart)
            .filter(models.PatientChart.appointment_id.in_(appt_ids))
            .all()
        ):
            charts[ch.appointment_id] = ch

    emp_ids = {a.therapist_id for a in rows if a.therapist_id}
    emp_map: dict[str, str] = {}
    if emp_ids:
        for e in db.query(models.Employee).filter(models.Employee.id.in_(emp_ids)).all():
            emp_map[e.id] = e.name

    grouped: "OrderedDict[str, list]" = OrderedDict()
    for a in rows:
        dkey = a.start_at.date().isoformat()
        grouped.setdefault(dkey, []).append(a)

    days = []
    for dkey, appts in grouped.items():
        appts_asc = sorted(appts, key=lambda a: a.start_at)
        day_items = []
        for a in appts_asc:
            ch = charts.get(a.id)
            day_items.append({
                "appointment_id": a.id,
                "start_at": a.start_at.isoformat(),
                "treatment_codes": _parse_codes(a.treatment_codes),
                "therapist_id": a.therapist_id,
                "therapist_name": emp_map.get(a.therapist_id),
                "chart": _chart_summary(ch) if ch else None,
            })
        days.append({"date": dkey, "appointments": day_items})

    pt = db.get(models.Patient, patient_id)
    return {
        "patient_id": patient_id,
        "patient_name": pt.name if pt else "",
        "total": len(grouped),
        "days": days,
    }
