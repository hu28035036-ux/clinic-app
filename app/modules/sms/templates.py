"""modules.sms.templates — 문자 본문 / 템플릿 조립 helper (19-10 신규).

본 모듈은 ``api.py:_normalize_tx_name_for_sms`` (line 2973) /
``_format_tx_summary_for_sms`` (line 2983) / ``sms_tomorrow`` 의 body 조립
(line 3019~3021) 의 *순수 helper* 를 제공한다. DB / ORM 미참조 — primitives /
caller 가 만든 dict 만 받음.

19-10 본 세션 범위:
  - 도수치료 시간 수치 제거 (``도수치료30분`` → ``도수치료``).
  - 치료 코드 → 문자용 짧은 표시 (``"도수치료, 체외충격파"``).
  - 내일 예약 알림 body 조립 (clinic 이름 / 환자명 / 날짜 / 시간 / 치료요약 / 변경취소 안내).
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:_normalize_tx_name_for_sms`` (line 2973~2980) /
#         ``_format_tx_summary_for_sms`` (line 2983~2995) /
#         ``sms_tomorrow`` body literal (line 3019~3021) 와 byte-equivalent.

# SAFETY: body 조립은 *환자명 / 환자 phone / 예약 시간* 등 PII 를 포함 — *기존
#         동작 보존* (UI / SMS 발송 흐름이 평문 PII 필요). 본 helper 는 *마스킹
#         정책 변경 ⊥*. 로그 마스킹은 19-7 ``patients.rules.patient_summary_for_log``
#         별도.

# NOTE: 도수치료 시간 수치 제거 패턴: ``r'(도수치료)\\s*\\d+\\s*분' → r'\\1'`` —
#       ``도수치료30분`` / ``도수치료 60분`` / ``도수치료 60 분`` 모두 ``도수치료`` 로.
#       기타 치료명 (``체외충격파`` / ``주사`` / ``연골주사``) 은 변경 ⊥.

# RISK: 치료요약 텍스트 변경 시 SMS 본문 일관성 깨짐 — 기존 패턴 정합 보존 필수.
#       변경 시 19-10 contract 테스트가 fail.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Final


# ─── 한국어 요일 (api.py:sms_tomorrow line 3008 정합) ─────────────────────────


KOREAN_WEEKDAYS: Final[tuple[str, ...]] = ("월", "화", "수", "목", "금", "토", "일")


def korean_weekday(dt: datetime) -> str:
    """``datetime`` → 한국어 요일 (월/화/.../일).

    COMPAT: ``api.py:sms_tomorrow`` (line 3008 / 3014) ``weekdays[tt.weekday()]``
    정합.
    """
    return KOREAN_WEEKDAYS[dt.weekday()]


# ─── 도수치료 시간 수치 제거 (api.py:_normalize_tx_name_for_sms 정합) ────────


_MANUAL_DURATION_PATTERN: Final[re.Pattern] = re.compile(r"(도수치료)\s*\d+\s*분")


def normalize_tx_name_for_sms(name: str | None) -> str | None:
    """문자 본문 표시용 — 도수치료 시간 수치 제거.

    COMPAT: ``api.py:_normalize_tx_name_for_sms`` (line 2973~2980) 와 byte-equivalent.

    매핑:
      ``"도수치료30분"`` → ``"도수치료"``.
      ``"도수치료 60분"`` → ``"도수치료"``.
      ``"체외충격파"`` → ``"체외충격파"`` (변경 ⊥).
      None → None (api.py 정합 — raw 보존).
      "" → "" (api.py 정합).
    """
    if not name:
        return name
    return _MANUAL_DURATION_PATTERN.sub(r"\1", name)


# ─── 치료 코드 → 짧은 표시 (api.py:_format_tx_summary_for_sms 정합) ─────────


def format_tx_summary_for_sms(
    codes: list[str] | None,
    treatments_by_code: dict[str, Any],
) -> str:
    """치료항목 코드 리스트 → 문자용 짧은 표시 (``"도수치료, 체외충격파"``).

    COMPAT: ``api.py:_format_tx_summary_for_sms`` (line 2983~2995) 와 byte-equivalent.

    인자:
      ``codes``               : 예약의 ``treatment_codes`` 파싱 결과.
      ``treatments_by_code``  : ``{code: Treatment-like}`` 매핑 (``.name`` 속성 보유).
                                caller 가 ``db.query(Treatment).all()`` 결과 dict 빌드.

    NOTE: 정규화 후 *중복 제거* (``도수치료30분`` + ``도수치료60분`` → ``"도수치료"`` 1개).
    NOTE: 알 수 없는 코드는 스킵 (caller 사전 필터링 정합).
    """
    names: list[str] = []
    seen: set[str] = set()
    for c in (codes or []):
        t = treatments_by_code.get(c)
        if not t:
            continue
        normalized = normalize_tx_name_for_sms(t.name)
        if normalized in seen:
            continue
        seen.add(normalized)
        names.append(normalized)
    return ", ".join(names) if names else ""


# ─── 내일 예약 알림 body 조립 (api.py:sms_tomorrow line 3019~3021 정합) ─────


def build_tomorrow_target_body(
    *,
    clinic_name: str,
    patient_name: str,
    appointment_dt: datetime,
    tx_summary: str,
    clinic_phone: str,
) -> str:
    """내일 예약 알림 SMS 본문 조립.

    COMPAT: ``api.py:sms_tomorrow`` (line 3019~3021) 와 byte-equivalent.
    포맷:
        ``[{clinic_name}] {patient_name} 님, 내일({M}/{D} {요일}) {HH}:{MM}{tx_part}``
        ``예약이 있습니다. 변경/취소는 {clinic_phone}``

    ``tx_summary`` 가 빈 값이면 ``tx_part`` 도 빈 — 치료요약 미포함.
    """
    weekday = korean_weekday(appointment_dt)
    tx_part = f" {tx_summary}" if tx_summary else ""
    return (
        f"[{clinic_name}] {patient_name} 님, "
        f"내일({appointment_dt.month}/{appointment_dt.day} {weekday}) "
        f"{appointment_dt.hour:02d}:{appointment_dt.minute:02d}{tx_part} "
        f"예약이 있습니다. 변경/취소는 {clinic_phone}"
    )


__all__ = [
    "KOREAN_WEEKDAYS",
    "korean_weekday",
    "normalize_tx_name_for_sms",
    "format_tx_summary_for_sms",
    "build_tomorrow_target_body",
]
