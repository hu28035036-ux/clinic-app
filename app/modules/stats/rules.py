"""modules.stats.rules — 통계 매칭 / mode / 카운트 정책 도메인 규칙 (19-11 신규).

본 모듈은 ``api.py`` 의 통계 핸들러에 *인라인으로 분산* 된 매칭 / 분류 / 카운트
정책 helper 의 *순수 helper* 를 제공한다. ORM / DB / 외부 API 미참조 —
primitives 만 받음 (D-4 정합).

19-11 본 세션 범위:
  - 매칭 helper (``_matches`` lambda 의 byte-equivalent).
  - mode 분류 helper (예약 기준 vs 완료 기준).
  - 카운트 증분 정책 상수 (시간 가중치 회귀 방지 — *RISK 가드*).
  - weekday 라벨.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:stats_summary`` (line 4006~4011) / ``stats_by_hour`` (line
#         4080~4085) / ``stats_by_weekday`` (line 4129~4134) / ``stats_by_treatment``
#         (line 4183~4188) / ``stats_daily`` (line 4236~4241) / ``stats_by_therapist``
#         (line 3466~3471) 의 ``_matches`` lambda 와 byte-equivalent.

# SAFETY: 본 helper 는 *판정 / 집계 정책* 만 — 실제 DB 변경 / raise ⊥.

# RISK: ``MANUAL_COUNT_INCREMENT_PER_APPT = 1`` *변경 ⊥* — 시간 가중치 방식
#       (manual30=1, manual60=2) 로 회귀하면 PatientTreatmentCount / 환자 표시 /
#       SMS 본문 / 통계 모두 위반. CLAUDE.md "manual60 을 다시 count_increment=2 로
#       되돌리지 않는다" 정합.

# NOTE: ``MODE_RESERVED`` / ``MODE_APPROVED`` / ``MODE_ALL`` 은 라우터 query
#       파라미터 정합. 알 수 없는 mode 는 안전 fallback (``reserved`` 분기).
"""
from __future__ import annotations

from typing import Final


# ─── 카운트 정책 상수 (CLAUDE.md / spec 03 정합) ─────────────────────────────


# 예약 1건 = count 1. *시간 가중치 방식 회귀 ⊥*.
# CLAUDE.md "manual60 = 1카운트 정책" 정합. 변경 시 환자 표시 / SMS 본문 / 통계
# 모두 위반.
MANUAL_COUNT_INCREMENT_PER_APPT: Final[int] = 1

# 본 모듈은 시간 가중치 (manual30=1, manual60=2) 정책을 *허용 ⊥* — 가드.
TIME_WEIGHTED_COUNT_DENIED: Final[bool] = True


# ─── mode 상수 (라우터 query 파라미터 정합) ──────────────────────────────────


MODE_RESERVED: Final[str] = "reserved"
MODE_APPROVED: Final[str] = "approved"
MODE_ALL: Final[str] = "all"

MODE_VALUES: Final[tuple[str, ...]] = (MODE_RESERVED, MODE_APPROVED, MODE_ALL)


# ─── treatment_code 매칭 (api.py 의 _matches lambda 정합) ───────────────────


TREATMENT_FILTER_ALL: Final[str] = "all"
TREATMENT_FILTER_MANUAL_ALL: Final[str] = "manual_all"


def treatment_code_matches(
    *,
    codes: list[str] | None,
    treatment_code: str | None,
    manual_codes_set: set[str],
) -> bool:
    """예약의 ``treatment_codes`` 가 query 의 ``treatment_code`` 필터에 매치되는가.

    COMPAT: ``api.py:stats_summary._matches`` (line 4006~4011) 등 모든 통계
    핸들러 인라인 lambda 와 byte-equivalent.

    매핑:
      ``treatment_code`` 가 빈 / None / ``"all"`` → 항상 True.
      ``treatment_code == "manual_all"`` → ``codes`` 안에 manual 코드가 있으면 True.
      그 외 → ``treatment_code in codes``.
    """
    if not treatment_code or treatment_code == TREATMENT_FILTER_ALL:
        return True
    if treatment_code == TREATMENT_FILTER_MANUAL_ALL:
        return any(c in manual_codes_set for c in (codes or []))
    return treatment_code in (codes or [])


# ─── mode 별 카운트 분류 (api.py 의 mode 분기 정합) ──────────────────────────


def is_counted_for_mode(*, status: str | None, mode: str | None) -> bool:
    """예약 status 와 mode 조합이 카운트 대상인지.

    COMPAT: ``api.py:stats_by_hour`` (line 4093~4098) / ``stats_by_weekday``
    (line 4142~4147) 의 mode 분기 정합.

    매핑:
      ``mode="all"``       → 전체 (취소/노쇼 포함 — 운영량 기준).
      ``mode="approved"``  → ``status == "approved"`` 만.
      ``mode="reserved"``  → ``status != "canceled"``.
      그 외 (None / 알 수 없음) → ``mode="reserved"`` 와 동일 (안전 fallback).
    """
    if mode == MODE_ALL:
        return True
    if mode == MODE_APPROVED:
        return status == "approved"
    # MODE_RESERVED 또는 None / 알 수 없음 → reserved 분기.
    return status != "canceled"


def is_counted_for_treatment_mode(*, status: str | None, mode: str | None) -> bool:
    """``stats_by_treatment`` 의 mode 분기 정합 (api.py:4192~4195).

    매핑 (위와 *약간 다름* — `stats_by_treatment` 는 ``mode="all"`` 분기 ⊥):
      ``mode="approved"``  → ``status == "approved"`` 만 카운트.
      ``mode="reserved"``  → ``status != "canceled"`` 만 카운트.
      그 외                → ``status != "canceled"`` (reserved fallback).
    """
    if mode == MODE_APPROVED:
        return status == "approved"
    return status != "canceled"


# ─── 한국어 weekday (api.py:stats_by_weekday line 4149 정합) ─────────────────


WEEKDAY_LABELS: Final[tuple[str, ...]] = ("월", "화", "수", "목", "금", "토", "일")


def weekday_label(weekday_index: int) -> str:
    """0~6 weekday → 한국어 라벨 ("월" ~ "일").

    COMPAT: ``api.py:stats_by_weekday`` (line 4149~4153) 정합.
    """
    if 0 <= weekday_index <= 6:
        return WEEKDAY_LABELS[weekday_index]
    return ""


# ─── 미배정 sentinel (19-8 therapists.rules 와 동일 — 통계 합산 정합) ────────


# COMPAT: ``api.py:stats_by_therapist`` (line 3495 / 3528) / ``stats_aggregate``
# (line 3681 / 3704) 등의 ``a.therapist_id or "__none__"`` 정합.
UNASSIGNED_SENTINEL: Final[str] = "__none__"
UNASSIGNED_LABEL: Final[str] = "미배정"


# ─── 도수치료 / 체외충격파 코드 — app.models.constants re-export ─────────────


def _import_eswt_code() -> str:
    """``app.models.constants.ESWT_CODE`` lazy re-export.

    SAFETY: top-level circular import 회피.
    """
    from app.models import constants as _C

    return _C.ESWT_CODE


# COMPAT: ``api.py:stats_aggregate`` line 3667 / 3674 등 정합. ``app.models.constants``
# 가 단일 진실원천.
ESWT_CODE: Final[str] = _import_eswt_code()


__all__ = [
    "MANUAL_COUNT_INCREMENT_PER_APPT",
    "TIME_WEIGHTED_COUNT_DENIED",
    "MODE_RESERVED",
    "MODE_APPROVED",
    "MODE_ALL",
    "MODE_VALUES",
    "TREATMENT_FILTER_ALL",
    "TREATMENT_FILTER_MANUAL_ALL",
    "treatment_code_matches",
    "is_counted_for_mode",
    "is_counted_for_treatment_mode",
    "WEEKDAY_LABELS",
    "weekday_label",
    "UNASSIGNED_SENTINEL",
    "UNASSIGNED_LABEL",
    "ESWT_CODE",
]
