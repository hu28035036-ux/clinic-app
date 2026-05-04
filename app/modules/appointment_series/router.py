"""modules.appointment_series.router — /api/appointment-series CRUD (post-19-P / 20-3-4 / F-2).

# NOTE: 사용자 §6-6 결정값 정합:
#   - (a) N회만 (interval_days + count)
#   - (i) 미래만 일괄 처리 (DELETE 시 today 이후 슬롯만)
#   - (ii) 충돌 슬롯 skip + 응답에 안내

# SAFETY: 시리즈 등록 시 각 슬롯에 대해 점심창 검사 (_check_lunch_block).
# 도수 중복 / 휴무 차단은 19-4 백엔드 검증이 자동 적용 (HTTPException 잡음).
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.modules.appointment_series.schemas import AppointmentSeriesIn
from app.modules.appointment_series.service import (
    compute_slot_starts,
    serialize_series,
)

router = APIRouter(prefix="/api", tags=["appointment-series"])


@router.post("/appointment-series")
def create_series(
    p: AppointmentSeriesIn,
    db: Session = Depends(get_db),
):
    """반복 예약 시리즈 등록.

    응답:
      - ``series``: 시리즈 dict (7키).
      - ``created``: 성공 생성 슬롯 ID 리스트.
      - ``conflicts``: skip 된 슬롯 정보 ``{start_at, reason}`` 리스트.

    NOTE: 충돌 슬롯은 *DB 입력 ⊥* (사용자 §6-6 (ii) 합리적 구현 — 데이터
    정합성 보존 + 응답 안내). 사용자가 conflicts 정보로 별도 처리.
    """
    from app.routers.api import (
        _check_lunch_block,
        _existing_codes_set,
        _log,
        _therapist_only_codes_set,
    )

    # 환자 / 치료사 검증
    patient = db.get(models.Patient, p.patient_id)
    if not patient:
        raise HTTPException(404, "환자를 찾을 수 없습니다.")
    if p.therapist_id:
        therapist = db.get(models.Employee, p.therapist_id)
        if not therapist:
            raise HTTPException(404, "치료사를 찾을 수 없습니다.")

    # 치료항목 검증
    valid_codes = _existing_codes_set(db)
    therapist_only_codes = _therapist_only_codes_set(db)
    codes = [c for c in (p.treatment_codes or []) if c in valid_codes]
    if not codes:
        raise HTTPException(400, "치료항목(treatment_codes)을 하나 이상 선택하세요.")

    # 슬롯 시작 시각 계산
    slot_starts = compute_slot_starts(
        start_at=p.start_at,
        interval_days=p.interval_days,
        count=p.count,
    )

    # 시리즈 row 생성 (슬롯 등록 후 commit 까지 보류)
    pattern_data = json.dumps(
        {"interval_days": p.interval_days, "count": p.count},
        ensure_ascii=False,
    )
    series = models.AppointmentSeries(
        patient_id=p.patient_id,
        therapist_id=p.therapist_id,
        pattern="n_times",
        pattern_data=pattern_data,
        start_date=p.start_at,
        end_date=slot_starts[-1] if slot_starts else None,
        treatment_codes=json.dumps(codes, ensure_ascii=False),
    )
    db.add(series)
    db.flush()

    created_ids: list[str] = []
    conflicts: list[dict] = []

    for slot_start in slot_starts:
        # 점심창 검사 — HTTPException 시 skip
        try:
            _check_lunch_block(slot_start, p.duration_min)
        except HTTPException as e:
            conflicts.append({
                "start_at": slot_start.isoformat(),
                "reason": str(e.detail) if e.detail else "lunch_block",
            })
            continue

        # 슬롯 생성
        appt = models.Appointment(
            patient_id=p.patient_id,
            therapist_id=p.therapist_id,
            start_at=slot_start,
            end_at=slot_start + __import__("datetime").timedelta(minutes=p.duration_min),
            duration_min=p.duration_min,
            treatment_codes=json.dumps(codes, ensure_ascii=False),
            memo=p.memo,
            status="reserved",
            series_id=series.id,
        )
        db.add(appt)
        db.flush()

        # 누락 항목: NULL handler 로 채우기
        for code in codes:
            if code in therapist_only_codes:
                continue
            db.add(models.TreatmentAssignment(
                appointment_id=appt.id, treatment_code=code, handler_id=None,
            ))
        db.flush()
        _log(db, "appointment", appt.id, "upsert", appt)
        created_ids.append(appt.id)

    db.commit()
    db.refresh(series)
    return {
        "series": serialize_series(series),
        "created": created_ids,
        "conflicts": conflicts,
    }


@router.delete("/appointment-series/{sid}")
def cancel_series(
    sid: str,
    db: Session = Depends(get_db),
):
    """시리즈 일괄 취소 — 미래 슬롯만 (사용자 §6-6 (i)).

    NOTE: 오늘 (UTC) 이전 슬롯은 보존 — 완료된 통계 / 매출 / 인센티브 카운트
    안전. 미래 슬롯만 status="canceled" + 메모 [취소-시리즈] prefix.
    """
    from app.routers.api import _bump_version, _log

    series = db.get(models.AppointmentSeries, sid)
    if not series:
        raise HTTPException(404, "시리즈를 찾을 수 없습니다.")

    now = datetime.utcnow()
    future_slots = (
        db.query(models.Appointment)
        .filter(models.Appointment.series_id == sid)
        .filter(models.Appointment.start_at >= now)
        .all()
    )
    canceled_ids: list[str] = []
    for appt in future_slots:
        if appt.status == "canceled":
            continue
        if appt.status == "approved":
            # 승인된 예약은 시리즈 일괄 취소에서 제외 (개별 처리)
            continue
        appt.status = "canceled"
        appt.memo = (appt.memo or "") + "\n[취소-시리즈]"
        _bump_version(appt)
        db.flush()
        _log(db, "appointment", appt.id, "upsert", appt)
        canceled_ids.append(appt.id)

    db.commit()
    return {
        "ok": True,
        "series_id": sid,
        "canceled": canceled_ids,
        "skipped_count": len(future_slots) - len(canceled_ids),
    }
