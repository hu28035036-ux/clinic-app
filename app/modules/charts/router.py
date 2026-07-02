from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.routers.api import _log, audit

from . import service
from .schemas import PatientChartIn

router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.get("/by-appointment/{aid}")
def get_chart_by_appointment(aid: str, db: Session = Depends(get_db)):
    """예약(치료완료) 1건의 차트. 없으면 null."""
    ch = service.get_chart_by_appointment(db, aid)
    return service.serialize_chart(ch) if ch else None


@router.put("/by-appointment/{aid}")
def upsert_chart_by_appointment(
    aid: str,
    payload: PatientChartIn,
    db: Session = Depends(get_db),
):
    """차트 작성/수정(upsert). 치료완료(approved) 예약에만 허용."""
    appt = db.get(models.Appointment, aid)
    if not appt:
        raise HTTPException(404, "예약을 찾을 수 없습니다.")
    if appt.status != "approved":
        raise HTTPException(400, "치료완료된 예약에만 차트를 작성할 수 있습니다.")
    ch = service.upsert_chart(
        db,
        appt,
        content=payload.content,
        treatment_start_date=payload.treatment_start_date,
        session_no=payload.session_no,
        author_id=payload.author_id,
        log_callback=_log,
    )
    audit(db, "charts.upsert", ch.id, f"appt={aid} author={ch.author_name_snapshot}")
    db.commit()
    db.refresh(ch)
    return service.serialize_chart(ch)


@router.get("/patient/{pid}")
def get_patient_charts(pid: str, db: Session = Depends(get_db)):
    """차팅 탭: 환자의 approved 방문(날짜별) + 각 예약 차트 요약."""
    return service.get_patient_chart_history(db, pid)
