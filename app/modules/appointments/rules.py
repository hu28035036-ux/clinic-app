"""modules.appointments.rules — 예약 상태 전이 / 메모 포맷 도메인 규칙 (19-9 신규).

본 모듈은 ``Appointment.status`` 의 전이 판정 (수정 가능 / 승인 가능 / 승인 되돌림
가능 / 취소 가능) 과 취소 메모 포맷 helper 등 *순수 도메인 규칙* 을 제공한다.
ORM / DB / 웹 프레임워크 미참조 — primitives 인자만 받음 (D-4 정합).

19-9 본 세션 범위:
  - 상태 상수 (``APPT_STATUS_*``) — ``app.models.models.APPT_STATUSES`` 정합.
  - 상태 전이 판정 helper.
  - 취소 메모 포맷 helper.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:update_appointment`` (line 1686) ``if obj.status in ("approved",
#         "canceled")`` / ``approve_appointment`` (line 1963~1966) ``if obj.status
#         == "approved" / == "canceled"`` / ``revert_approve`` (line 1989) ``if
#         obj.status != "approved"`` / ``cancel_appointment`` (line 2012) ``if
#         obj.status == "approved"`` / ``split_appointment_code`` (line 1814)
#         ``if obj.status in ("approved", "canceled")`` / ``cancel_appointment``
#         (line 2016) 의 메모 포맷 ``"\n[취소] {memo}" / "\n[취소]"`` 정합.

# SAFETY: 본 helper 는 *판정 / 포맷* 만 — 실제 DB 변경 / raise ⊥. 호출자가
#         ``raise HTTPException`` 결정. devtools / curl POST 우회는 본 helper 외
#         (라우터 본체 결정). 환자 PII 미참조 — status / memo 만 다룸.

# NOTE: ``APPT_STATUSES = ("reserved", "approved", "canceled")`` (m001 정합).
#       ``treated`` 는 view-model 표시용 라벨 (19-3 calendar.view_models) 이며 DB
#       enum 에는 부재 — 본 모듈은 *DB 표준 상태값* 만 다룸.

# RISK: 상태 전이 정책 변경 ⊥ — 라우터 본체와 본 helper 가 분기 분산되어 있어
#       byte-equivalent 검증 필수. 19-9 contract 테스트가 라우터 인라인 분기와
#       본 helper 결과의 동등성을 검증.
"""
from __future__ import annotations

from typing import Final


# ─── 예약 상태 상수 — app.models.models.APPT_STATUSES 정합 ────────────────────


APPT_STATUS_RESERVED: Final[str] = "reserved"
APPT_STATUS_APPROVED: Final[str] = "approved"
APPT_STATUS_CANCELED: Final[str] = "canceled"

APPT_STATUSES: Final[tuple[str, ...]] = (
    APPT_STATUS_RESERVED,
    APPT_STATUS_APPROVED,
    APPT_STATUS_CANCELED,
)


# ─── 상태 전이 판정 (api.py 인라인 분기 정합) ────────────────────────────────


def is_editable_status(status: str | None) -> bool:
    """예약을 수정 (PUT /appointments/{aid}) 할 수 있는 상태인가.

    COMPAT: ``api.py:update_appointment`` (line 1686) /
    ``split_appointment_code`` (line 1814) 의 ``if obj.status in ("approved",
    "canceled"): raise`` 인라인 정합. 본 helper 는 *True = 수정 가능* 반환.
    """
    return status not in (APPT_STATUS_APPROVED, APPT_STATUS_CANCELED)


def is_approvable_status(status: str | None) -> bool:
    """예약을 승인 (POST /appointments/{aid}/approve) 할 수 있는 상태인가.

    COMPAT: ``api.py:approve_appointment`` (line 1963~1966) — 이미 ``approved`` /
    ``canceled`` 면 raise. 본 helper 는 *True = 승인 가능* 반환.
    """
    return status not in (APPT_STATUS_APPROVED, APPT_STATUS_CANCELED)


def is_revertable_status(status: str | None) -> bool:
    """승인 되돌림 (POST /appointments/{aid}/revert-approve) 가능한 상태인가.

    COMPAT: ``api.py:revert_approve`` (line 1989) ``if obj.status != "approved":
    raise`` 인라인 정합. 본 helper 는 *True = 되돌림 가능* (= ``approved`` 일 때만).
    """
    return status == APPT_STATUS_APPROVED


def is_cancelable_status(status: str | None) -> bool:
    """예약을 취소 (POST /appointments/{aid}/cancel) 할 수 있는 상태인가.

    COMPAT: ``api.py:cancel_appointment`` (line 2012) ``if obj.status ==
    "approved": raise`` 인라인 정합. 본 helper 는 *True = 취소 가능* (= ``approved``
    가 아닌 모든 상태 — ``reserved`` / ``canceled`` / 기타).

    NOTE: 이미 ``canceled`` 인 예약을 다시 cancel 호출해도 라우터가 raise 하지 않음
    (메모 누적). 본 helper 는 라우터 인라인 분기 정합 — 호출자가 결정.
    """
    return status != APPT_STATUS_APPROVED


def is_already_approved(status: str | None) -> bool:
    """이미 승인된 예약인지.

    COMPAT: ``api.py:approve_appointment`` (line 1963) ``if obj.status ==
    "approved": raise`` 정합.
    """
    return status == APPT_STATUS_APPROVED


def is_canceled(status: str | None) -> bool:
    """취소된 예약인지.

    COMPAT: ``api.py:approve_appointment`` (line 1965) ``if obj.status ==
    "canceled": raise`` / ``api.py:1493`` (last_appointments) ``status !=
    "canceled"`` 정합.
    """
    return status == APPT_STATUS_CANCELED


# ─── 한국어 사용자 노출 메시지 (api.py 인라인 정합) ──────────────────────────


EDIT_BLOCKED_MESSAGE: Final[str] = "확정/취소된 예약은 수정할 수 없습니다."
ALREADY_APPROVED_MESSAGE: Final[str] = "이미 승인된 예약입니다."
APPROVE_BLOCKED_CANCELED_MESSAGE: Final[str] = "취소된 예약은 승인할 수 없습니다."
REVERT_BLOCKED_MESSAGE: Final[str] = "approved 상태에서만 되돌릴 수 있습니다."
CANCEL_BLOCKED_APPROVED_MESSAGE: Final[str] = (
    "승인된 예약은 취소할 수 없습니다. 먼저 승인을 되돌리세요."
)


# ─── 취소 메모 포맷 (api.py:cancel_appointment line 2016 정합) ───────────────


CANCEL_MEMO_PREFIX: Final[str] = "\n[취소]"


def append_cancel_memo(existing_memo: str | None, new_memo: str | None) -> str:
    """기존 메모 + 취소 prefix + 사용자 입력 취소 메모 합산.

    COMPAT: ``api.py:cancel_appointment`` (line 2016) ``(obj.memo or "") +
    (f"\\n[취소] {p.memo}" if p.memo else "\\n[취소]")`` 와 byte-equivalent.

    NOTE: 빈 ``new_memo`` 또는 None → ``"\\n[취소]"`` (사용자 사유 없음 표기).
    값이 있으면 ``"\\n[취소] {new_memo}"`` (사용자 사유 표기).
    """
    base = existing_memo or ""
    if new_memo:
        suffix = f"{CANCEL_MEMO_PREFIX} {new_memo}"
    else:
        suffix = CANCEL_MEMO_PREFIX
    return base + suffix


# ─── 승인자 정규화 (api.py:approve_appointment line 1970 정합) ───────────────


DEFAULT_APPROVED_BY: Final[str] = "원무과"


def normalize_approved_by(value: str | None) -> str:
    """승인자 입력 정규화 — 빈 값 → ``DEFAULT_APPROVED_BY``.

    COMPAT: ``api.py:approve_appointment`` (line 1970) ``(p.approved_by or
    "원무과").strip() or "원무과"`` 와 byte-equivalent.
    """
    if value is None:
        return DEFAULT_APPROVED_BY
    stripped = value.strip()
    if not stripped:
        return DEFAULT_APPROVED_BY
    return stripped


# ─── 카운트 증감 가드 (api.py:_bump_patient_count line 1934 정합) ────────────


def clamp_count_at_zero(current: int | None, delta: int) -> int:
    """``current + delta`` 를 0 이상으로 clamp.

    COMPAT: ``api.py:_bump_patient_count`` (line 1946) ``max(0, (row.done_count
    or 0) + inc)`` / (line 1952) ``max(0, inc)`` 정합.

    NOTE: 본 helper 는 *카운트 산정* 만 — 실제 DB row 생성 / update 는 호출자
    책임 (PatientTreatmentCount lazy 생성 정책 보존).
    """
    return max(0, (current or 0) + int(delta))


__all__ = [
    "APPT_STATUS_RESERVED",
    "APPT_STATUS_APPROVED",
    "APPT_STATUS_CANCELED",
    "APPT_STATUSES",
    "is_editable_status",
    "is_approvable_status",
    "is_revertable_status",
    "is_cancelable_status",
    "is_already_approved",
    "is_canceled",
    "EDIT_BLOCKED_MESSAGE",
    "ALREADY_APPROVED_MESSAGE",
    "APPROVE_BLOCKED_CANCELED_MESSAGE",
    "REVERT_BLOCKED_MESSAGE",
    "CANCEL_BLOCKED_APPROVED_MESSAGE",
    "CANCEL_MEMO_PREFIX",
    "append_cancel_memo",
    "DEFAULT_APPROVED_BY",
    "normalize_approved_by",
    "clamp_count_at_zero",
]
