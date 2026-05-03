"""modules.treatments.completion_rules — 완료체크 / 카운트 ±N service helper (19-6 신규).

본 모듈은 ``api.py:_bump_patient_count`` (line 1934) 의 *동등 service helper* 를
제공한다. 현재 라우터 패턴: approve / revert / delete 시 *예약의 각 코드별로 +1 또는
-1 호출* — *count_increment 곱셈 ⊥*, *시간 가중치 합산 ⊥*.

19-6 본 세션 범위:
  - ``bump_patient_count`` : ``_bump_patient_count`` 와 byte-equivalent.
    - 0 미만 방지.
    - Lazy 생성 (PatientTreatmentCount 행 없으면 ``+delta`` 일 때만 생성).
    - 시간 가중치 / count_increment 합산 ⊥ — *항목별 ±1*.
  - 라우터 미채택 (라우터 본체 무수정) — 19-9 시점 채택.

# COMPAT: ``api.py:_bump_patient_count`` (line 1934~1953) 와 byte-equivalent — 동일
#         시그니처 + 동일 동작. 호출자가 commit 책임.

# SAFETY: 본 helper 가 *실제 DB 변경* 하지만, 라우터 미채택이므로 운영 흐름 영향 ⊥.
#         호출자가 ``commit`` 책임. 환자 PII 미참조 (patient_id / treatment_code 만).

# NOTE: 완료체크 정책 — *항목별 개별 ±1*. 즉:
#       - approve 시 예약의 각 코드마다 ``bump_patient_count(..., +1)`` 호출.
#       - revert 시 각 코드마다 ``bump_patient_count(..., -1)``.
#       - delete (approved 였던 경우) 도 -1 보정.
#       시간 가중치 / count_increment 합산 ⊥ — 사용자 명시 정합.

# RISK: ``count_increment`` 를 *delta 곱셈에 사용 ⊥*. 사용자 명시 "도수 30분=1, 도수
#       60분=2 같은 count_increment 합산 방식으로 되돌리는 것 금지". 본 helper 는
#       *항목별 ±1* 만 — 시간 가중치 부재.
"""
from __future__ import annotations

from typing import Any


def bump_patient_count(
    db: Any,
    *,
    patient_id: str,
    treatment_code: str,
    delta: int,
) -> None:
    """환자 완료 카운트 ±N (Lazy 생성, 0 미만 방지).

    COMPAT: ``api.py:_bump_patient_count`` (line 1934~1953) 와 byte-equivalent.

    인자:
      ``db``               : SQLAlchemy 세션 (호출자 주입).
      ``patient_id``       : 환자 ID.
      ``treatment_code``   : 치료항목 코드 (Treatment.code).
      ``delta``            : ±N (보통 ±1 — *시간 가중치 ⊥*).

    동작:
      - ``delta == 0`` → no-op.
      - ``Treatment(code=...)`` 없으면 → no-op (silent fail, api.py 정합).
      - ``PatientTreatmentCount`` 행 있으면 → ``done_count = max(0, current + delta)``.
      - 행 없고 ``delta > 0`` → 새 행 생성 (``rx_count=0``, ``done_count=max(0, delta)``).
      - 행 없고 ``delta <= 0`` → no-op (Lazy 생성 + 음수 방지).

    SAFETY: 호출자가 ``commit`` 책임 — 본 helper 는 ``flush`` 도 안 함 (api.py 본체와
    동일 — 호출자가 트랜잭션 스코프 결정).
    """
    if delta == 0:
        return

    from app.models import models as _m

    t = db.query(_m.Treatment).filter_by(code=treatment_code).first()
    if not t:
        return

    inc = delta
    row = (
        db.query(_m.PatientTreatmentCount)
        .filter_by(patient_id=patient_id, treatment_id=t.id)
        .first()
    )
    if row is not None:
        row.done_count = max(0, (row.done_count or 0) + inc)
    elif delta > 0:
        db.add(
            _m.PatientTreatmentCount(
                patient_id=patient_id,
                treatment_id=t.id,
                rx_count=0,
                done_count=max(0, inc),
            )
        )


# ─── 정책 상수 (사용자 명시 정합) ─────────────────────────────────────────────


# RISK: ``manual60`` (도수치료 60분) 의 ``count_increment`` 정책 — 사용자 명시 + CLAUDE.md
# 정합: **1** (시간 가중치 ⊥). 시드 / 관리자 UI 가 책임. 본 helper 는 정책 결정 ⊥.
EXPECTED_MANUAL60_COUNT_INCREMENT: int = 1

# 항목별 개별 ±1 카운트 — 시간 가중치 합산 부재 명시.
DEFAULT_COMPLETION_DELTA_PER_CODE: int = 1


def expected_count_per_appointment_code() -> int:
    """예약의 각 치료 코드마다 approve 시 +1 / revert 시 -1.

    NOTE: 사용자 명시 "치료항목별 개별 체크 원칙". 시간 가중치 / 합산 ⊥.
    """
    return DEFAULT_COMPLETION_DELTA_PER_CODE


__all__ = [
    "bump_patient_count",
    "EXPECTED_MANUAL60_COUNT_INCREMENT",
    "DEFAULT_COMPLETION_DELTA_PER_CODE",
    "expected_count_per_appointment_code",
]
