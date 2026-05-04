"""modules.doctors — 의사 도메인 (post-19-P / 20-3-3 / F-1 가벼운 의사).

사용자 §5-7 (c) 결정 — *가벼운 의사만*:
  - `Doctor` 단일 테이블만 신설.
  - Department / Room / DoctorSchedule / Patient.doctor_id 부재 (post-(c) 후속).

# COMPAT: 기존 `Employee.role="doctor"` 분기 (도수치료 내부 의료직군) 보존.
#         `Doctor` 별도 테이블은 *외부 진료 의사 등록 후보 모델* — Employee 와
#         별개 도메인.

# SAFETY: license_no / specialty 평문 저장 — admin 권한 게이트 (require_admin).
#         응답 dict 에 평문 노출 (UI 표시용). audit_log detail 에 license_no 부재
#         (PII 비저장 정책 정합).
"""

from app.modules.doctors.router import router
from app.modules.doctors.schemas import (
    DOCTOR_RESPONSE_KEYS,
    DoctorIn,
)
from app.modules.doctors.service import serialize_doctor, serialize_doctors

__all__ = [
    "DOCTOR_RESPONSE_KEYS",
    "DoctorIn",
    "router",
    "serialize_doctor",
    "serialize_doctors",
]
