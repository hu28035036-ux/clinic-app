"""modules.notes.rules — 메모 분류 / 정책 도메인 규칙 (19-7 신규).

본 모듈은 *현재 구현된 2종류 메모* 의 분류 + 정책 상수 + 마스킹 helper 를 제공한다.

19-7 본 세션 범위:
  - 메모 종류 enum (환자별 / 예약별 — *현재 구현된 것만*).
  - 취소 prefix 패턴 (api.py 정합 — Appointment.memo 의 ``\\n[취소]`` 자동 추가).
  - PII 마스킹 helper (로그 / AI prompt 용 — patients.rules.mask_memo 와 동등 정책).

# COMPAT: ``api.py:cancel_appointment`` (line 2016) 의 ``\\n[취소] {memo}`` 패턴 정합.

# SAFETY: 메모 원문은 *로그 / AI prompt / audit_log* 에 노출 ⊥ — 마스킹 후 truncate.
#         운영 응답 / 환자 모달 / SMS 발송 흐름은 평문 메모 필요 (UI 정합).

# NOTE: *현재 구현* 은 ``Patient.memo`` (지속 메모 후보) + ``Appointment.memo`` (당일
#       메모 후보) 두 종류만. 별도 ``Note`` 테이블 / 다중 메모 / 작성자 추적 등은
#       19-P 범위 외 (m014+ 후속).

# RISK: 메모 분류 단정 ⊥ — *현재 코드 사실* 만 표현. "지속 메모 = 환자 메모" 매핑은
#       *기능적 분류* 이지 *공식 정의* 가 아님 (사용자 명시 — 단정 ⊥).
"""
from __future__ import annotations

import re
from typing import Final


# ─── 메모 종류 (현재 구현된 2종) ─────────────────────────────────────────────


# Patient.memo — 환자 모달 / 검색 결과 / 환자 카드에 노출되는 *영구 누적* 메모.
# 사용자 분류상 *지속 메모 후보* — 단, "지속 메모" 라는 별도 개념은 현재 DB / 코드에
# 정식 정의되어 있지 ⊥. 본 enum 은 *기능적 매핑* (단정 ⊥).
NOTE_KIND_PATIENT: Final[str] = "patient"

# Appointment.memo — 예약 1건 단위 메모. 취소 시 `[취소] {memo}` 자동 추가.
# 사용자 분류상 *당일 메모 후보* — 단, "당일 메모" 라는 별도 개념은 현재 정식 정의 ⊥.
NOTE_KIND_APPOINTMENT: Final[str] = "appointment"

NOTE_KIND_VALUES: Final[tuple[str, ...]] = (
    NOTE_KIND_PATIENT,
    NOTE_KIND_APPOINTMENT,
)


# ─── 취소 prefix 패턴 (api.py 정합) ────────────────────────────────────────


# COMPAT: ``api.py:cancel_appointment`` (line 2016) 의 ``\n[취소]`` 또는 ``\n[취소] {memo}``
# 패턴.
CANCEL_MEMO_PREFIX: Final[str] = "\n[취소]"


def append_cancel_memo(existing_memo: str | None, cancel_reason: str | None) -> str:
    """기존 메모 + ``\\n[취소] {reason}`` 자동 추가.

    COMPAT: ``api.py:cancel_appointment`` line 2016 의 인라인 패턴과 byte-equivalent:
        ``obj.memo = (obj.memo or "") + (f"\\n[취소] {p.memo}" if p.memo else "\\n[취소]")``
    """
    base = existing_memo or ""
    reason = (cancel_reason or "").strip() if cancel_reason else ""
    if reason:
        suffix = f"\n[취소] {reason}"
    else:
        suffix = "\n[취소]"
    return base + suffix


# ─── 메모 마스킹 (로그 / AI prompt 전용) ──────────────────────────────────


# COMPAT: ``patients.rules.mask_memo`` 와 동일 정책 — 본 모듈은 *메모 단독 마스킹*
# 진입점.
DEFAULT_MEMO_MASK_LIMIT: Final[int] = 20


def _scrub_pii_patterns(text: str) -> str:
    """메모 안 *전화번호 / 주민번호 패턴* 을 ``***`` 로 치환.

    SAFETY: ``patients.rules._scrub_pii_patterns`` 와 *byte-equivalent* — 평행 정의
    (modules 간 직접 import ⊥, D-4 정합).
    """
    text = re.sub(r"\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}", "***", text)
    text = re.sub(r"\d{6}[-\s]?\d{7}", "***", text)
    return text


def mask_memo_for_log(memo: str | None, *, max_chars: int = DEFAULT_MEMO_MASK_LIMIT) -> str:
    """메모 원문 → 로그 / AI prompt 용 PII 스크럽 + truncated 결과.

    SAFETY: 메모 안 PII (전화 / 주민번호) 패턴을 truncate 이전에 ``***`` 로 치환.
    운영 응답 dict 에는 사용 ⊥.

    NOTE: ``patients.rules.mask_memo`` 와 *byte-equivalent* — 19-7 contract 테스트가
    동등성 검증.
    """
    if not memo:
        return ""
    m = memo.strip()
    original_len = len(m)
    scrubbed = _scrub_pii_patterns(m)
    if len(scrubbed) <= max_chars:
        return scrubbed
    return f"{scrubbed[:max_chars]}…({original_len}자)"


# ─── 메모 종류별 정책 (RISK 표기) ─────────────────────────────────────────


def is_persistent_note(note_kind: str) -> bool:
    """*지속 메모 후보* — Patient.memo 에 영구 저장.

    NOTE: 현재 구현 = ``patient`` 만. *공식 정의* 는 아님 — 사용자가 "지속 메모" 분류를
    별도 도입할 경우 본 매핑을 갱신.
    """
    return note_kind == NOTE_KIND_PATIENT


def is_per_appointment_note(note_kind: str) -> bool:
    """*당일 메모 후보* — Appointment.memo (1건 단위, 취소 시 자동 prefix).

    NOTE: 현재 구현 = ``appointment`` 만. *공식 정의* 는 아님.
    """
    return note_kind == NOTE_KIND_APPOINTMENT


__all__ = [
    "NOTE_KIND_PATIENT",
    "NOTE_KIND_APPOINTMENT",
    "NOTE_KIND_VALUES",
    "CANCEL_MEMO_PREFIX",
    "append_cancel_memo",
    "DEFAULT_MEMO_MASK_LIMIT",
    "mask_memo_for_log",
    "is_persistent_note",
    "is_per_appointment_note",
]
