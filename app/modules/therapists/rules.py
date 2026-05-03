"""modules.therapists.rules — 직원 역할 / 분류 / 색상 도메인 규칙 (19-8 신규).

본 모듈은 ``ROLE_DOCTOR / ROLE_THERAPIST`` 상수와 *역할 분류 / 활성 판정 / 색상
fallback* 의 순수 helper 를 제공한다. ORM / DB / 웹 프레임워크 미참조 —
primitives 인자만 받음 (D-4 정합).

D-4 경계 정밀화:
  - ORM 테이블 클래스 (``app.models.models``) 직접 import *⊥*.
  - DB 엔진 / 세션 (``app.database``) 직접 import *⊥*.
  - 라우터 본체 직접 import *⊥*.
  - 순수 상수 모듈 (``app.models.constants`` — 역할 / 시드 상수만 정의) 의
    *re-export* 는 *허용* — 단일 진실원천 보존이 목적이며, ORM / DB 의존을
    가져오지 않음. 19-8 contract 테스트가 ``constants`` 와의 byte-equivalent 검증.
  - 19-3 표시용 view-model 의 색상 상수 *re-export* 는 함수 호출 lazy import 로
    처리 — top-level circular 회피.

19-8 본 세션 범위:
  - 역할 상수 (``ROLE_DOCTOR / ROLE_THERAPIST / ROLES``) — ``app.models.constants``
    의 단일 진실원천을 *re-export* (본 모듈이 독자 정의 ⊥).
  - ``is_therapist_role`` / ``is_doctor_role`` / ``is_valid_role`` 판정 helper.
  - ``normalize_role`` — 빈 값 / None → ``"therapist"`` (DB 기본값 정합).
  - ``DEFAULT_THERAPIST_COLOR`` — ``calendar.view_models`` 의 단일 진실원천
    re-export (색상 fallback 정합).
  - 활성 판정 (``is_active_employee``) + ``can_handle_*`` 권한 판정 helper.

# COMPAT: ``api.py:1010`` (``role`` 쿼리 파라미터) / ``api.py:897`` /
#         ``api.py:935`` (``if p.role not in ("doctor", "therapist")``) /
#         ``api.py:1035`` (``if p.role not in C.ROLES``) 정합. 19-8 contract
#         테스트가 ``app.models.constants`` 와 동등성 검증.

# SAFETY: 본 helper 는 *판정 / 분류 / 정규화* 만 — 실제 DB 변경 / raise ⊥.
#         호출자가 raise / fallback 결정. 환자 PII 미참조 (직원 role / color
#         만 다룸).

# NOTE: ``Employee`` 모델은 ``role`` 컬럼 default ``"therapist"`` (m001 정합).
#       ``role`` 값은 ``ROLES`` 안에서만 허용 (m001 / api.py:1035 검증).
#       ``DEFAULT_THERAPIST_COLOR`` 는 *치료사 미배정 / 색상 미설정* fallback 색
#       — 19-3 ``calendar.view_models.UNASSIGNED_THERAPIST_COLOR`` 와 동일 값.

# RISK: doctors / medical_staff 향후 분리 시 ``ROLE_DOCTOR`` 가 의사 전용 모듈로
#       이관 후보. 본 19-8 시점에는 *공통 직원 도메인* 으로 두 역할 모두 다룸.
#
# TODO(후속 검토): 역할별 *권한 매트릭스* (예: 의사만 처방 / 치료사만 도수치료)
#                 는 *현재 코드에 ``can_eswt`` / ``can_manual`` Boolean 만* 존재.
#                 향후 doctors / medical_staff 분리 시점에 *역할별 권한 정책* 추가
#                 후보 — 본 19-8 시점에는 기존 두 Boolean 컬럼 그대로.
"""
from __future__ import annotations

from typing import Final

from app.models import constants as _C

# ─── 역할 상수 — app.models.constants 단일 진실원천 re-export ─────────────────

# COMPAT: ``app.models.constants.ROLE_DOCTOR`` / ``ROLE_THERAPIST`` / ``ROLES`` 와
# byte-equivalent. 본 모듈은 *re-export* — 독자 정의 ⊥.
ROLE_DOCTOR: Final[str] = _C.ROLE_DOCTOR
ROLE_THERAPIST: Final[str] = _C.ROLE_THERAPIST
ROLES: Final[tuple[str, ...]] = tuple(_C.ROLES)


# ─── 색상 fallback — calendar.view_models 단일 진실원천 re-export ────────────


def _import_default_therapist_color() -> str:
    """``calendar.view_models.UNASSIGNED_THERAPIST_COLOR`` lazy import.

    SAFETY: 모듈 top-level circular import 회피 — view_models 가 본 모듈 import
    하지 않지만, 향후 라우터 채택 시점의 의존 방향 안전성 확보.
    """
    from app.modules.calendar import view_models as _vm

    return _vm.UNASSIGNED_THERAPIST_COLOR


# COMPAT: ``api.py:188`` (``a.therapist.color if a.therapist else "#9CA3AF"``) /
# ``api.py:3789`` (``t.color or "#9CA3AF"``) / ``api.py:4501`` 등 정합. 19-3
# ``calendar.view_models.UNASSIGNED_THERAPIST_COLOR`` 와 동일 값 (``"#9CA3AF"``).
DEFAULT_THERAPIST_COLOR: Final[str] = _import_default_therapist_color()


# ─── 역할 판정 ────────────────────────────────────────────────────────────────


def is_therapist_role(role: str | None) -> bool:
    """``role`` 이 ``"therapist"`` 인지.

    COMPAT: ``api.py:160`` / ``api.py:824`` / ``api.py:1179``
    (``models.Employee.role == C.ROLE_THERAPIST``) 정합.
    """
    return role == ROLE_THERAPIST


def is_doctor_role(role: str | None) -> bool:
    """``role`` 이 ``"doctor"`` 인지.

    COMPAT: ``api.py:155`` / ``api.py:823`` / ``api.py:3525``
    (``models.Employee.role == "doctor"``) 정합.
    """
    return role == ROLE_DOCTOR


def is_valid_role(role: str | None) -> bool:
    """``role`` 이 ``ROLES`` 안에 있는지.

    COMPAT: ``api.py:897`` / ``api.py:935`` (``if p.role not in ("doctor",
    "therapist")``) / ``api.py:1035`` (``if p.role not in C.ROLES``) 정합.
    """
    return role in ROLES


def normalize_role(role: str | None) -> str:
    """raw ``role`` 값을 표준 ROLE 로 정규화.

    None / 빈 값 → ``"therapist"`` (DB 기본값 정합 — m001).
    유효하지 않은 값은 그대로 통과 (raw 보존 — 호출자가 검증).
    """
    if not role:
        return ROLE_THERAPIST
    return role


# ─── 활성 판정 ────────────────────────────────────────────────────────────────


def is_active_employee(active: bool | int | None) -> bool:
    """``Employee.active`` 값이 활성인지.

    COMPAT: ``api.py:_serialize_employee`` (line 173) ``"active": bool(e.active)``
    정합. None / 0 / False → 비활성.
    """
    return bool(active)


# ─── 권한 판정 (can_eswt / can_manual) ───────────────────────────────────────


def can_handle_eswt(can_eswt: bool | int | None) -> bool:
    """치료사가 체외충격파 가능 여부.

    COMPAT: ``api.py:_serialize_employee`` (line 174) ``"can_eswt": bool(e.can_eswt)``
    + ``api.py:4368`` (``models.Employee.can_eswt == True``) 정합.

    NOTE: 본 helper 는 *Boolean 정규화* 만 — 의료/도메인 정책 (예: 치료사 역할만
    can_eswt 허용) 변경 ⊥. 호출자가 결정.
    """
    return bool(can_eswt)


def can_handle_manual(can_manual: bool | int | None) -> bool:
    """치료사가 도수치료 가능 여부.

    COMPAT: ``api.py:_serialize_employee`` (line 174) ``"can_manual": bool(e.can_manual)``
    + ``api.py:4368`` (``models.Employee.can_manual == True``) 정합.
    """
    return bool(can_manual)


# ─── 색상 fallback ────────────────────────────────────────────────────────────


def therapist_color_or_default(color: str | None) -> str:
    """치료사 색상 (없으면 ``DEFAULT_THERAPIST_COLOR`` fallback).

    COMPAT: 19-3 ``calendar.view_models.therapist_color`` 와 byte-equivalent.
    빈 문자열 / None → ``DEFAULT_THERAPIST_COLOR``.
    """
    if not color:
        return DEFAULT_THERAPIST_COLOR
    return color


# ─── 미배정 / 표시 라벨 (통계 / 캘린더 정합) ──────────────────────────────────


# COMPAT: ``api.py:3495`` 등 (``a.therapist_id or "__none__"``) / ``api.py:3528``
# (``therapists["__none__"] = "미배정"``) 정합. 통계 / 일별 차트 빌더가 미배정
# 슬롯을 같은 sentinel 키로 모음.
UNASSIGNED_SENTINEL: Final[str] = "__none__"
UNASSIGNED_LABEL: Final[str] = "미배정"


def is_unassigned(therapist_id: str | None) -> bool:
    """``therapist_id`` 가 빈 값 / None / sentinel 인지.

    COMPAT: ``api.py:3495`` (``tid = a.therapist_id or "__none__"``) /
    ``api.py:4685`` (``tid = a.therapist_id  # 미배정 제외 위해 None 그대로``) 정합.
    """
    if not therapist_id:
        return True
    return therapist_id == UNASSIGNED_SENTINEL


__all__ = [
    "ROLE_DOCTOR",
    "ROLE_THERAPIST",
    "ROLES",
    "DEFAULT_THERAPIST_COLOR",
    "is_therapist_role",
    "is_doctor_role",
    "is_valid_role",
    "normalize_role",
    "is_active_employee",
    "can_handle_eswt",
    "can_handle_manual",
    "therapist_color_or_default",
    "UNASSIGNED_SENTINEL",
    "UNASSIGNED_LABEL",
    "is_unassigned",
]
