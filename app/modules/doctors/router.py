"""modules.doctors.router — /api/doctors CRUD endpoints (post-19-P / 20-3-3 / F-1 (c)).

# SAFETY: 모든 write endpoint = require_admin 권한. audit 기록 (license_no 부재 —
# PII 비저장 정책 정합).

# NOTE: 사용자 §5-7 (c) — 가벼운 의사만. Department / Room / Schedule 부재.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import models
from app.modules.audit.service import cap_detail
from app.modules.doctors.schemas import DoctorIn
from app.modules.doctors.service import serialize_doctor, serialize_doctors
from app.routers.api import require_admin

router = APIRouter(prefix="/api", tags=["doctors"])


@router.get("/doctors")
def list_doctors(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """의사 목록 조회 (활성 우선 정렬).

    # NOTE: active_only=False 시 비활성 포함. 정렬 = (active DESC, sort_order ASC).
    """
    q = db.query(models.Doctor)
    if active_only:
        q = q.filter(models.Doctor.active == True)  # noqa: E712
    rows = q.order_by(
        models.Doctor.active.desc(),
        models.Doctor.sort_order.asc(),
        models.Doctor.created_at.asc(),
    ).all()
    return serialize_doctors(rows)


@router.post("/doctors")
def create_doctor(
    p: DoctorIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """의사 생성 (admin 권한 필수)."""
    if not p.name.strip():
        raise HTTPException(400, "의사 이름은 필수입니다.")
    doctor = models.Doctor(
        name=p.name.strip(),
        specialty=p.specialty,
        license_no=p.license_no,
        color=p.color,
        active=p.active,
        sort_order=p.sort_order,
    )
    db.add(doctor)
    db.flush()
    # SAFETY: audit detail 에 name 만 (license_no / specialty 비저장)
    from app.routers.api import _log, audit
    _log(db, "doctor", doctor.id, "upsert", doctor)
    audit(db, "doctor.create", doctor.id, cap_detail(f"name={doctor.name}"))
    db.commit()
    db.refresh(doctor)
    return serialize_doctor(doctor)


@router.put("/doctors/{did}")
def update_doctor(
    did: str,
    p: DoctorIn,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """의사 수정 (admin 권한 필수)."""
    doctor = db.get(models.Doctor, did)
    if not doctor:
        raise HTTPException(404, "의사를 찾을 수 없습니다.")
    if not p.name.strip():
        raise HTTPException(400, "의사 이름은 필수입니다.")
    doctor.name = p.name.strip()
    doctor.specialty = p.specialty
    doctor.license_no = p.license_no
    doctor.color = p.color
    doctor.active = p.active
    doctor.sort_order = p.sort_order
    db.flush()
    from app.routers.api import _log, audit
    _log(db, "doctor", doctor.id, "upsert", doctor)
    audit(db, "doctor.update", doctor.id, cap_detail(f"name={doctor.name}"))
    db.commit()
    db.refresh(doctor)
    return serialize_doctor(doctor)


@router.delete("/doctors/{did}")
def delete_doctor(
    did: str,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """의사 삭제 (admin 권한 필수)."""
    doctor = db.get(models.Doctor, did)
    if not doctor:
        raise HTTPException(404, "의사를 찾을 수 없습니다.")
    name = doctor.name
    db.delete(doctor)
    from app.routers.api import _log, audit
    _log(db, "doctor", did, "delete", None)
    audit(db, "doctor.delete", did, cap_detail(f"name={name}"))
    db.commit()
    return {"ok": True}
