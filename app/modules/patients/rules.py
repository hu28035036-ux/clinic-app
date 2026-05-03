"""modules.patients.rules — 환자 도메인 규칙 (19-7 신규).

본 모듈은 환자 중복 검사 / 신환 체크 / PII 마스킹 정책 등 *순수 helper* 를 제공한다.
DB / ORM 미참조 — primitives 인자만 받음 (D-4 정합).

19-7 본 세션 범위:
  - 중복 검사 정책 (chart_no / name+birth_date 매칭 — primitives + caller 가 DB 조회).
  - 신환 체크 정책 (manual_history / appointment.is_new_patient 로 from-data 판정).
  - PII 마스킹 helper (로그 / AI prompt / 진단 출력 용 — 응답 dict 미사용).

# COMPAT: ``api.py:_check_patient_duplicate`` (line 1408) / ``patient_manual_history_summary``
#         (line 1498) 의 분기 정합. 19-7 contract 테스트가 검증.

# SAFETY: PII 마스킹 helper 는 *로그 / AI prompt* 용. 운영 응답 dict 에는 *기존 PII
#         평문 그대로* (UI / SMS 발송 대상 추출 흐름 정합) — 본 모듈은 마스킹 정책
#         결정 ⊥, *마스킹 후 결과* 만 노출.

# NOTE: 중복 검사는 chart_no 우선 + name+birth_date 둘 다 있을 때 — name 만 / phone
#       만 / name+phone 만 같음은 차단 ⊥ (api.py 원본 정합).

# RISK: PII 마스킹 패턴 (성씨만 / 가운데 자리 / 월일 마스킹) 변경 시 로그 일관성
#       깨질 수 있음. 19-7 시점 라우터 / 로그 미채택 — 19-9/19-13 시점 채택.
"""
from __future__ import annotations

import re
from typing import Final


# ─── 중복 검사 — primitives 정규화 ───────────────────────────────────────────


def normalize_for_duplicate_check(
    name: str | None,
    birth_date: str | None,
    chart_no: str | None,
) -> tuple[str, str, str]:
    """``api.py:_check_patient_duplicate`` (line 1415~1417) 의 정규화 패턴.

    COMPAT: ``str.strip()`` + ``"" or value`` 분기 정합. 빈 / None → 빈 문자열.
    """
    nm = (name or "").strip()
    if isinstance(birth_date, str):
        bd = (birth_date or "").strip()
    else:
        bd = birth_date or ""
    cn = (chart_no or "").strip()
    return nm, bd, cn


def should_check_chart_no_duplicate(chart_no_normalized: str) -> bool:
    """``chart_no`` 가 비어 있지 않으면 중복 검사 대상.

    COMPAT: ``api.py:_check_patient_duplicate`` line 1418 ``if cn:`` 정합.
    """
    return bool(chart_no_normalized)


def should_check_name_birth_duplicate(
    name_normalized: str,
    birth_date_normalized: str,
) -> bool:
    """``name`` + ``birth_date`` 둘 다 비어 있지 않으면 중복 검사 대상.

    COMPAT: ``api.py:_check_patient_duplicate`` line 1422 ``if nm and bd:`` 정합.
    """
    return bool(name_normalized) and bool(birth_date_normalized)


# ─── 중복 검사 사유 메시지 (한국어, api.py 정합) ─────────────────────────────


DUPLICATE_CHART_NO_MESSAGE: Final[str] = "이미 등록된 차트번호입니다."
DUPLICATE_NAME_BIRTH_MESSAGE: Final[str] = (
    "같은 이름과 생년월일의 환자가 이미 등록되어 있습니다."
)


# ─── 신환 체크 정책 ──────────────────────────────────────────────────────────


def derive_has_new_patient_flag(appointments_with_flag: list[bool]) -> bool:
    """``appointments`` 중 하나라도 ``is_new_patient=True`` 면 True.

    COMPAT: ``api.py:patient_manual_history_summary`` (line 1509~1515) 의
    ``has_new_patient_flag`` 산정 정합.
    """
    return any(bool(flag) for flag in appointments_with_flag)


def derive_has_manual_history(manual_appointment_ids: list[str]) -> bool:
    """도수치료 이력 1건 이상이면 True.

    COMPAT: ``api.py:patient_manual_history_summary`` (line 1518) 의
    ``has_manual_history`` 산정 정합.
    """
    return len(manual_appointment_ids) > 0


# ─── PII 마스킹 (로그 / AI prompt / 진단 출력 용) ──────────────────────────


# 한글 성씨 + ** 패턴 (로그 / AI prompt 용 — 운영 응답에는 사용 ⊥).
NAME_MASK_SUFFIX: Final[str] = "**"

# 휴대폰 마스킹 정규식 (010-1234-5678 / 010 1234 5678 / 01012345678 모두 처리).
_PHONE_PATTERN: Final[re.Pattern] = re.compile(
    r"^(\d{2,3})[-\s]?(\d{3,4})[-\s]?(\d{4})$"
)


def mask_name(name: str | None) -> str:
    """환자명 마스킹 — 첫 글자만 남기고 ``**``.

    SAFETY: ``로그 / AI prompt`` 전용. 운영 응답 / 환자 모달 / SMS 발송 대상 추출
    에는 사용 ⊥ (UI 가 평문 환자명 필요).
    """
    if not name:
        return ""
    n = name.strip()
    if not n:
        return ""
    return n[0] + NAME_MASK_SUFFIX


def mask_phone(phone: str | None) -> str:
    """전화번호 마스킹 — 가운데 4자리를 ``****`` 로.

    SAFETY: 로그 / AI prompt 전용.
    """
    if not phone:
        return ""
    p = phone.strip()
    m = _PHONE_PATTERN.match(p)
    if m is None:
        # 패턴 매치 실패 — 안전 fallback (전체 마스킹).
        return "****"
    head, mid, tail = m.groups()
    _ = mid  # 가운데는 마스킹 — 미사용 표시.
    return f"{head}-****-{tail}"


def mask_birth_date(birth_date: str | None) -> str:
    """생년월일 마스킹 — 년도만 남기고 월/일 ``-**-**``.

    형식: ``YYYY-MM-DD`` 또는 ``YYYY/MM/DD`` 또는 ``YYYYMMDD`` 등.
    SAFETY: 로그 / AI prompt 전용.
    """
    if not birth_date:
        return ""
    bd = birth_date.strip()
    # 4자리 년도 매칭 시도.
    m = re.match(r"^(\d{4})", bd)
    if m is None:
        return "****-**-**"
    return f"{m.group(1)}-**-**"


def _scrub_pii_patterns(text: str) -> str:
    """메모 안의 *전화번호 / 주민번호 패턴* 을 ``***`` 로 치환.

    SAFETY: truncate 만으로는 head 부분에 PII 노출 가능 — 패턴 사전 스크럽.
    """
    # 휴대폰 / 일반 전화 (010-1234-5678 / 02-345-6789 / 01012345678 등).
    text = re.sub(r"\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}", "***", text)
    # 주민번호류 (000000-0000000).
    text = re.sub(r"\d{6}[-\s]?\d{7}", "***", text)
    return text


def mask_memo(memo: str | None, *, max_chars: int = 20) -> str:
    """환자 메모 / 예약 메모 PII 스크럽 + truncate (``"…(N자)"``).

    SAFETY: 로그 / AI prompt 전용. 메모 안 PII (전화 / 주민번호) 패턴을 *truncate
    이전에* ``***`` 로 치환 — head 영역에서도 원문 노출 ⊥. ``len(...)`` 길이는 *원문
    기준* (스크럽 전) 으로 표기.
    """
    if not memo:
        return ""
    m = memo.strip()
    original_len = len(m)
    scrubbed = _scrub_pii_patterns(m)
    if len(scrubbed) <= max_chars:
        return scrubbed
    return f"{scrubbed[:max_chars]}…({original_len}자)"


def mask_chart_no(chart_no: str | None) -> str:
    """차트번호 마스킹 — 앞 2자 + ``****``.

    SAFETY: 로그 / AI prompt 전용. 차트번호는 운영 응답 / SMS 대상 추출에는 평문 필요.
    """
    if not chart_no:
        return ""
    c = chart_no.strip()
    if len(c) <= 2:
        return "****"
    return c[:2] + "****"


def patient_summary_for_log(
    *,
    name: str | None = None,
    phone: str | None = None,
    birth_date: str | None = None,
    chart_no: str | None = None,
    memo: str | None = None,
) -> dict:
    """환자 정보 → 로그 / AI prompt 용 마스킹 dict.

    SAFETY: 본 helper 결과는 ``로그 / audit_log / AI prompt / 진단 출력`` 에만
    사용. 응답 dict / SMS 발송 / 환자 모달 / sync payload 에는 사용 ⊥ (운영
    흐름은 평문 PII 필요 — 19-7 시점 라우터 미채택).
    """
    return {
        "name": mask_name(name),
        "phone": mask_phone(phone),
        "birth_date": mask_birth_date(birth_date),
        "chart_no": mask_chart_no(chart_no),
        "memo": mask_memo(memo),
    }


__all__ = [
    "normalize_for_duplicate_check",
    "should_check_chart_no_duplicate",
    "should_check_name_birth_duplicate",
    "DUPLICATE_CHART_NO_MESSAGE",
    "DUPLICATE_NAME_BIRTH_MESSAGE",
    "derive_has_new_patient_flag",
    "derive_has_manual_history",
    "NAME_MASK_SUFFIX",
    "mask_name",
    "mask_phone",
    "mask_birth_date",
    "mask_memo",
    "mask_chart_no",
    "patient_summary_for_log",
]
