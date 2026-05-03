"""modules.treatments.rules — 치료항목 분류 도메인 규칙 (19-6 신규).

본 모듈은 치료항목의 role / ESWT 분리 / 도수 분류 / 완료체크 대상 판정 등
*도메인 규칙 단일 진실원천 후보* 다. 19-6 contract 테스트가 ``app/routers/api.py``
의 인라인 분류 로직 (`_doctor_codes_set` / `_therapist_only_codes_set` /
`_get_manual_treatment_rows` 등) 과의 동등성을 검증한다.

19-6 본 세션 범위:
  - role / ESWT 분리 / 도수 / 완료체크 *판정 helper* — primitives 인자 (DB / ORM ⊥).
  - 라우터 무수정 — 19-9 시점 채택.

# COMPAT: ``api.py`` 의 인라인 분류 패턴과 byte-equivalent. 19-6 contract 테스트가
#         정합 검증.

# NOTE: 도수치료 = ``role=="therapist" AND code != ESWT_CODE AND active`` (api.py:3732
#       정합). 코드 prefix (``manual...``) 가 아니라 *role 기반 판정* — 새 도수 항목
#       (도수90 / 도수120 등) 추가 시 자동 반영.

# RISK: 시간 가중치 합산 (``count_increment`` 가산) 으로 *되돌리지 ⊥*. 사용자 명시
#       "도수 30분=1, 도수 60분=2 같은 count_increment 합산 방식으로 되돌리는 것 금지".
#       본 helper 는 *항목별 개별 카운트* 만 — 시간 가중치 미사용.
"""
from __future__ import annotations

from typing import Any, Final


# ─── role 상수 (api.py 인라인 정합) ───────────────────────────────────────────

# m005 / m011 / models.Treatment.role 값.
ROLE_DOCTOR: Final[str] = "doctor"
ROLE_THERAPIST: Final[str] = "therapist"

ROLE_VALUES: Final[tuple[str, ...]] = (ROLE_DOCTOR, ROLE_THERAPIST)


# ─── ESWT (체외충격파) 코드 ───────────────────────────────────────────────────

# COMPAT: ``app.models.constants.ESWT_CODE`` 와 동일 — 본 모듈은 *primitives* 만 받음
# (caller 가 ESWT_CODE 를 인자로 주입). 직접 import 하지 않음 — D-4 정합.
DEFAULT_ESWT_CODE: Final[str] = "eswt"


# ─── 분류 helper (api.py 의 인라인 set comprehension 와 byte-equivalent) ─────


def is_doctor_role(treatment: Any) -> bool:
    """``Treatment.role == "doctor"`` 정합.

    COMPAT: ``api.py:_doctor_codes_set`` (line 153) 의 분기 정합.
    """
    return getattr(treatment, "role", None) == ROLE_DOCTOR


def is_therapist_role(treatment: Any) -> bool:
    """``Treatment.role == "therapist"`` 정합.

    COMPAT: ``api.py:_therapist_codes_set`` (line 158) 의 분기 정합.
    """
    return getattr(treatment, "role", None) == ROLE_THERAPIST


def is_manual_treatment(treatment: Any, *, eswt_code: str = DEFAULT_ESWT_CODE) -> bool:
    """*도수치료* 정의 — ``role="therapist"`` AND ``code != eswt_code``.

    COMPAT: ``api.py:_get_manual_treatment_rows`` (line 3732~3749) +
    ``_therapist_only_codes_set`` (line 163) 분기 정합.

    NOTE: code prefix (``manual...``) 가 아니라 *role 기반 판정* — 관리자 UI 에서
    한글 이름으로 새 도수 항목 (예: ``tx_xxx``) 을 추가해도 자동 반영. spec 01 §1 정합.
    """
    if not is_therapist_role(treatment):
        return False
    return getattr(treatment, "code", None) != eswt_code


def is_eswt_treatment(treatment: Any, *, eswt_code: str = DEFAULT_ESWT_CODE) -> bool:
    """``code == eswt_code`` 정합.

    COMPAT: ``api.py`` 의 ``code == C.ESWT_CODE`` 분기 정합.
    """
    return getattr(treatment, "code", None) == eswt_code


def is_active(treatment: Any) -> bool:
    """``Treatment.active == True`` 정합.

    COMPAT: ``api.py:_build_treatment_meta`` (line 820) / ``_get_manual_treatment_rows`` 정합.
    빈 / None 도 False (api.py 의 ``if t.active`` 짧은 평가 정합).
    """
    return bool(getattr(treatment, "active", False))


# ─── 분류 set comprehensions (api.py 와 byte-equivalent) ─────────────────────


def doctor_codes(treatments: list) -> set[str]:
    """``role="doctor"`` 코드 셋.

    COMPAT: ``api.py:_doctor_codes_set`` (line 153) 와 byte-equivalent.
    """
    return {t.code for t in treatments if is_doctor_role(t)}


def therapist_codes(treatments: list) -> set[str]:
    """``role="therapist"`` 코드 셋.

    COMPAT: ``api.py:_therapist_codes_set`` (line 158) 와 byte-equivalent.
    """
    return {t.code for t in treatments if is_therapist_role(t)}


def therapist_only_codes(
    treatments: list,
    *,
    eswt_code: str = DEFAULT_ESWT_CODE,
) -> set[str]:
    """``role="therapist" AND code != eswt_code`` (도수치료 + 기타 — 체외충격파 제외).

    COMPAT: ``api.py:_therapist_only_codes_set`` (line 163) 와 byte-equivalent.
    예약 assignment 분기에서 사용 — 체외충격파는 별도 흐름.
    """
    return {t.code for t in treatments if is_manual_treatment(t, eswt_code=eswt_code)}


def existing_codes(treatments: list) -> set[str]:
    """모든 (활성+비활성) 코드 셋.

    COMPAT: ``api.py:_existing_codes_set`` (line 148) 와 byte-equivalent.
    """
    return {t.code for t in treatments}


def active_manual_codes(
    treatments: list,
    *,
    eswt_code: str = DEFAULT_ESWT_CODE,
) -> list[str]:
    """*활성* 도수치료 코드 — sort_order 정렬 가정 (caller 가 정렬된 list 주입).

    COMPAT: ``api.py:_get_manual_therapy_codes`` (line 3752) +
    ``_get_manual_treatment_rows`` (line 3732) 와 byte-equivalent — sort_order 정렬은
    caller 책임 (repository 가 정렬된 list 주입).
    """
    return [
        t.code for t in treatments
        if is_active(t) and is_manual_treatment(t, eswt_code=eswt_code)
    ]


# ─── 완료체크 대상 판정 (시간 가중치 ⊥) ──────────────────────────────────────


def is_completion_target(treatment: Any) -> bool:
    """치료항목이 완료체크 대상인가 — *항목별 개별 체크* 원칙.

    NOTE: 모든 활성 치료항목이 완료체크 대상 (도수 / ESWT / doctor 모두). 통계 집계는
    *항목별 카운트* — 시간 가중치 합산 ⊥.
    RISK: ``count_increment`` 합산 방식으로 *되돌리지 ⊥*. ``manual60`` 의 카운트는 1
    (CLAUDE.md 정합). 시간이 늘어나도 *항목별 1 카운트* 만.
    """
    return is_active(treatment)


def get_count_increment(treatment: Any) -> int:
    """``Treatment.count_increment`` 그대로 반환 — caller 가 ±N 곱셈에 사용.

    COMPAT: ``api.py:_bump_patient_count`` 호출자가 ``_parse_codes(...)`` 후 매 코드마다
    ``+1`` 호출 — *count_increment 곱하기 ⊥*. 본 helper 는 *반환값 노출* 만.

    RISK: 합산 / 곱셈으로 사용 ⊥ (시간 가중치 금지). 본 값은 관리자 UI 노출용 + 향후
    정책 결정 자리. 현재 시드 정합: ``manual60`` = 1 (CLAUDE.md), 합산 방식 ⊥.
    """
    val = getattr(treatment, "count_increment", 0)
    try:
        return int(val or 0)
    except Exception:
        return 0


__all__ = [
    "ROLE_DOCTOR",
    "ROLE_THERAPIST",
    "ROLE_VALUES",
    "DEFAULT_ESWT_CODE",
    "is_doctor_role",
    "is_therapist_role",
    "is_manual_treatment",
    "is_eswt_treatment",
    "is_active",
    "doctor_codes",
    "therapist_codes",
    "therapist_only_codes",
    "existing_codes",
    "active_manual_codes",
    "is_completion_target",
    "get_count_increment",
]
