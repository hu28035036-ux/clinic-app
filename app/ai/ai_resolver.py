"""ai_resolver — AI 추출 텍스트를 DB 실제 값으로 매칭 (Phase 2).

역할:
- 환자명 / 차트번호 → Patient row
- 치료사명 → Employee (role='therapist') row
- 치료항목명 / 약어 → Treatment row (treatment_aliases 테이블 활용)
- 날짜 텍스트 → 실제 date
- 시간 텍스트 → 실제 time

주의:
- 본 모듈은 **read-only**. DB INSERT / UPDATE / DELETE 없음.
- 환자 후보 다수 시 차트번호 / 이름 / 생년월일 / 연락처 후보 목록 생성.
- AI 가 임의로 환자 / 치료사 / 치료항목을 선택하지 않음.
- 외부 AI API 에 환자 전체 / 생년월일 / 연락처 / 메모 미전송.

cross-reference:
- 환자 검색 우선순위 → AI_FEATURE_MASTER_PLAN.md § 7.1
- 치료항목 매칭 우선순위 → AI_FEATURE_MASTER_PLAN.md § 11.4
- 날짜 해석 규칙 → AI_FEATURE_MASTER_PLAN.md § 12

하네스: tests/test_phase02_ai_resolver.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Protocol

from app.ai.ai_command_schema import (
    DataSourceState,
    TreatmentItem,
    TreatmentItemStatus,
)


# ────────────────────────────── DB 의존성 추상화 ──────────────────────────────


class DBSession(Protocol):
    """SQLAlchemy Session 또는 호환 인터페이스 — execute / scalar / scalars 만 사용."""

    def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any: ...


# ────────────────────────────── 결과 데이터 ──────────────────────────────


@dataclass
class PatientCandidate:
    """환자 후보 1건 — 차트번호 / 이름 / 생년월일 / 연락처 표시용."""

    patient_id: str
    chart_no: str | None
    name: str
    birth_date: str | None
    phone: str | None


@dataclass
class PatientResolution:
    """환자 검색 결과.

    candidates 가 1건이면 자동 확정, 다수면 사용자 선택 필요.
    chart_no 와 name 이 서로 다른 환자를 가리키면 mismatch=True.
    """

    candidates: list[PatientCandidate] = field(default_factory=list)
    mismatch: bool = False
    not_found: bool = False
    # 매칭 우선순위 (1~5) — AI_FEATURE_MASTER_PLAN.md § 7.1
    match_rank: int | None = None


@dataclass
class TherapistResolution:
    therapist_id: str | None = None
    therapist_name: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    not_found: bool = False


@dataclass
class DateResolution:
    resolved_date: date | None = None
    is_past: bool = False
    is_ambiguous: bool = False  # 월 누락 등
    note: str = ""  # "30일을 2026년 5월 기준으로 해석" 등 사용자 안내용


@dataclass
class TimeResolution:
    hour: int | None = None
    minute: int = 0
    note: str = ""


# ────────────────────────────── 환자 매칭 (단일 책임) ──────────────────────────────


def resolve_patient(
    session: DBSession,
    *,
    patient_name: str | None,
    chart_number: str | None,
) -> PatientResolution:
    """환자 검색 우선순위 (AI_FEATURE_MASTER_PLAN § 7.1):
    1. 차트번호 정확히 일치
    2. 차트번호 + 이름 일치
    3. 환자명 정확히 일치
    4. 환자명 일부 일치
    5. 동명이인 후보 표시

    차트번호 + 이름 이 서로 다른 환자를 가리키면 mismatch=True.
    """
    from sqlalchemy import or_, select

    from app.models.models import Patient

    # 1. 차트번호 우선
    if chart_number:
        rows = list(session.execute(select(Patient).where(Patient.chart_no == chart_number)).scalars())
        if rows:
            # 차트번호 + 이름 모두 입력 — 일치 검사
            if patient_name:
                same_name_rows = [r for r in rows if r.name == patient_name]
                if not same_name_rows:
                    # 차트번호는 맞지만 이름 불일치
                    return PatientResolution(
                        candidates=[_to_candidate(r) for r in rows],
                        mismatch=True,
                        match_rank=2,
                    )
                rows = same_name_rows
            return PatientResolution(
                candidates=[_to_candidate(r) for r in rows],
                match_rank=1 if not patient_name else 2,
            )

    # 2. 환자명만 (차트번호 없거나 차트번호로 못 찾음)
    if patient_name:
        # 정확 일치
        exact = list(session.execute(select(Patient).where(Patient.name == patient_name)).scalars())
        if exact:
            return PatientResolution(
                candidates=[_to_candidate(r) for r in exact],
                match_rank=3,
            )
        # 일부 일치 (LIKE)
        like_pattern = f"%{patient_name}%"
        partial = list(
            session.execute(
                select(Patient).where(or_(Patient.name.like(like_pattern))).limit(20)
            ).scalars()
        )
        if partial:
            return PatientResolution(
                candidates=[_to_candidate(r) for r in partial],
                match_rank=4 if len(partial) == 1 else 5,
            )

    return PatientResolution(not_found=True)


def _to_candidate(p: Any) -> PatientCandidate:
    return PatientCandidate(
        patient_id=p.id,
        chart_no=p.chart_no,
        name=p.name,
        birth_date=p.birth_date,
        phone=p.phone,
    )


# ────────────────────────────── 치료사 매칭 ──────────────────────────────


def resolve_therapist(
    session: DBSession,
    *,
    therapist_name: str | None,
) -> TherapistResolution:
    """치료사 검색 — 활성 직원 중 이름 정확 일치 / 부분 일치."""
    if not therapist_name:
        return TherapistResolution(not_found=True)

    from sqlalchemy import select

    from app.models.models import Employee

    rows = list(
        session.execute(
            select(Employee)
            .where(Employee.name == therapist_name)
            .where(Employee.active.is_(True))
        ).scalars()
    )
    if not rows:
        # 부분 일치
        rows = list(
            session.execute(
                select(Employee)
                .where(Employee.name.like(f"%{therapist_name}%"))
                .where(Employee.active.is_(True))
                .limit(10)
            ).scalars()
        )

    if not rows:
        return TherapistResolution(not_found=True)
    if len(rows) == 1:
        return TherapistResolution(
            therapist_id=rows[0].id,
            therapist_name=rows[0].name,
        )
    return TherapistResolution(
        candidates=[{"id": r.id, "name": r.name, "role": r.role} for r in rows],
    )


# ────────────────────────────── 치료항목 / alias 매칭 ──────────────────────────────


def resolve_treatment_items(
    session: DBSession,
    *,
    treatment_text: str | None,
) -> list[TreatmentItem]:
    """치료항목 텍스트를 공백 / 쉼표 단위로 분리하여 각각 매칭.

    매칭 우선순위 (AI_FEATURE_MASTER_PLAN § 11.4):
    1. 치료항목 code 직접 매칭
    2. 치료항목 name 정확
    3. treatment_aliases.alias_name 정확
    4. 치료항목 name 일부
    5. 후보 다수 → 사용자 선택 필요
    """
    if not treatment_text:
        return []

    # 공백 / 쉼표로 분리 — "도수30 주 충" → ["도수30", "주", "충"]
    raw_tokens = [t for t in re.split(r"[\s,]+", treatment_text.strip()) if t]
    return [_resolve_one_treatment(session, raw) for raw in raw_tokens]


def _resolve_one_treatment(session: DBSession, raw: str) -> TreatmentItem:
    from sqlalchemy import select

    from app.models.models import Treatment

    # 1. code 직접 매칭
    direct = session.execute(select(Treatment).where(Treatment.code == raw)).scalar_one_or_none()
    if direct:
        return TreatmentItem(
            raw_text=raw,
            matched_treatment_id=direct.id,
            matched_treatment_name=direct.name,
            source=DataSourceState.DB_VERIFIED,
            status=TreatmentItemStatus.DB_VERIFIED,
        )

    # 2. name 정확 일치
    name_exact = session.execute(
        select(Treatment).where(Treatment.name == raw)
    ).scalar_one_or_none()
    if name_exact:
        return TreatmentItem(
            raw_text=raw,
            matched_treatment_id=name_exact.id,
            matched_treatment_name=name_exact.name,
            source=DataSourceState.DB_VERIFIED,
            status=TreatmentItemStatus.DB_VERIFIED,
        )

    # 2-1. Treatment.short (공식 약어 컬럼) 정확 일치 — 사용자 지시 정합 (하드코딩 ⊥, DB 기준)
    short_exact = session.execute(
        select(Treatment).where(Treatment.short == raw)
    ).scalar_one_or_none()
    if short_exact:
        return TreatmentItem(
            raw_text=raw,
            matched_treatment_id=short_exact.id,
            matched_treatment_name=short_exact.name,
            source=DataSourceState.DB_VERIFIED,
            status=TreatmentItemStatus.DB_VERIFIED,
        )

    # 3. treatment_aliases 정확 일치
    alias_rows = _query_alias(session, raw)

    if len(alias_rows) == 1:
        treatment_id = alias_rows[0]
        treatment = session.execute(
            select(Treatment).where(Treatment.id == treatment_id)
        ).scalar_one_or_none()
        if treatment:
            return TreatmentItem(
                raw_text=raw,
                matched_treatment_id=treatment.id,
                matched_treatment_name=treatment.name,
                source=DataSourceState.DB_VERIFIED,
                status=TreatmentItemStatus.DB_VERIFIED,
            )
    elif len(alias_rows) > 1:
        # alias 가 여러 치료항목과 충돌
        candidates: list[dict[str, Any]] = []
        for tid in alias_rows:
            t = session.execute(select(Treatment).where(Treatment.id == tid)).scalar_one_or_none()
            if t:
                candidates.append({"id": t.id, "name": t.name, "code": t.code})
        return TreatmentItem(
            raw_text=raw,
            source=DataSourceState.AI_EXTRACTED,
            status=TreatmentItemStatus.ALIAS_CONFLICT,
            candidates=candidates,
        )

    # 4. name 일부 일치
    partial = list(
        session.execute(
            select(Treatment).where(Treatment.name.like(f"%{raw}%")).limit(5)
        ).scalars()
    )
    if len(partial) == 1:
        return TreatmentItem(
            raw_text=raw,
            matched_treatment_id=partial[0].id,
            matched_treatment_name=partial[0].name,
            source=DataSourceState.SYSTEM_RESOLVED,
            status=TreatmentItemStatus.DB_VERIFIED,
        )
    if len(partial) > 1:
        return TreatmentItem(
            raw_text=raw,
            source=DataSourceState.AI_EXTRACTED,
            status=TreatmentItemStatus.NEEDS_CLARIFICATION,
            candidates=[{"id": t.id, "name": t.name, "code": t.code} for t in partial],
        )

    # 5. not found
    return TreatmentItem(
        raw_text=raw,
        source=DataSourceState.AI_EXTRACTED,
        status=TreatmentItemStatus.NOT_FOUND,
    )


def _query_alias(session: DBSession, alias_name: str) -> list[str]:
    """treatment_aliases.alias_name → treatment_id 조회 (raw SQL)."""
    from sqlalchemy import text

    result = session.execute(
        text("SELECT treatment_id FROM treatment_aliases WHERE alias_name = :alias"),
        {"alias": alias_name},
    )
    return [row[0] for row in result.fetchall()]


# ────────────────────────────── 날짜 해석 ──────────────────────────────


_WEEKDAY_KO = {
    "월": 0, "월요일": 0,
    "화": 1, "화요일": 1,
    "수": 2, "수요일": 2,
    "목": 3, "목요일": 3,
    "금": 4, "금요일": 4,
    "토": 5, "토요일": 5,
    "일": 6, "일요일": 6,
}


def resolve_date(
    date_text: str | None,
    *,
    current_calendar_year: int,
    current_calendar_month: int,
    today: date | None = None,
) -> DateResolution:
    """날짜 해석 (AI_FEATURE_MASTER_PLAN § 12):
    - 오늘 / 내일 / 모레
    - 이번 주 X요일 / 다음 주 X요일
    - 4월 30일 / 5월10일 (해당 연도)
    - 30일 (현재 캘린더 월 기준)
    - 과거 날짜는 is_past=True (저장 결정은 caller)
    """
    if not date_text:
        return DateResolution()

    today = today or date.today()
    text = date_text.strip()

    # "오늘"
    if "오늘" in text:
        return DateResolution(resolved_date=today)
    # "내일"
    if "내일" in text:
        return DateResolution(resolved_date=today + timedelta(days=1))
    # "모레"
    if "모레" in text:
        return DateResolution(resolved_date=today + timedelta(days=2))

    # "이번 주 X요일" / "다음 주 X요일"
    week_match = re.search(r"(이번\s*주|다음\s*주)\s*([월화수목금토일])(?:요일)?", text)
    if week_match:
        weekday = _WEEKDAY_KO[week_match.group(2)]
        days_diff = weekday - today.weekday()  # 음수 = 같은 주의 과거
        is_next_week = "다음" in week_match.group(1)
        # 이번 주: today 기준 같은 주의 해당 요일 (과거면 그대로 — 사용자 의도 유지)
        # 다음 주: 다음 주의 해당 요일 = 이번 주 + 7일
        if is_next_week:
            days_diff += 7
        target = today + timedelta(days=days_diff)
        return DateResolution(resolved_date=target, is_past=target < today)

    # "M월 D일" / "M월D일"
    md_match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if md_match:
        m = int(md_match.group(1))
        d = int(md_match.group(2))
        try:
            target = date(today.year, m, d)
            # 이미 지난 달 / 일이면 내년으로 해석 — 단, 현재 캘린더 월을 우선 따름
            return DateResolution(
                resolved_date=target,
                is_past=target < today,
                note=f"{m}월 {d}일을 {target.year}년 기준으로 해석했습니다.",
            )
        except ValueError:
            return DateResolution(is_ambiguous=True)

    # "D일" (월 누락) — 현재 선택된 캘린더 월 기준
    d_only_match = re.search(r"^(\d{1,2})\s*일$", text)
    if d_only_match:
        d = int(d_only_match.group(1))
        try:
            target = date(current_calendar_year, current_calendar_month, d)
            return DateResolution(
                resolved_date=target,
                is_past=target < today,
                note=f"{d}일을 현재 선택된 {current_calendar_year}년 {current_calendar_month}월 기준으로 해석했습니다.",
            )
        except ValueError:
            return DateResolution(is_ambiguous=True)

    return DateResolution(is_ambiguous=True)


# ────────────────────────────── 시간 해석 ──────────────────────────────


def resolve_time(time_text: str | None) -> TimeResolution:
    """시간 해석 — 9시 / 오전 9시 / 오후 2시 / 14:30 / 14시30분."""
    if not time_text:
        return TimeResolution()

    text = time_text.strip()

    # "오전 N시 M분" / "오후 N시 M분"
    period_match = re.search(r"(오전|오후|am|pm|AM|PM)\s*(\d{1,2})\s*시\s*(?:(\d{1,2})\s*분)?", text)
    if period_match:
        period = period_match.group(1)
        hour = int(period_match.group(2))
        minute = int(period_match.group(3)) if period_match.group(3) else 0
        if period in ("오후", "pm", "PM") and hour < 12:
            hour += 12
        if period in ("오전", "am", "AM") and hour == 12:
            hour = 0
        return TimeResolution(hour=hour, minute=minute)

    # "HH:MM"
    colon_match = re.search(r"(\d{1,2}):(\d{2})", text)
    if colon_match:
        return TimeResolution(hour=int(colon_match.group(1)), minute=int(colon_match.group(2)))

    # "N시 M분" / "N시"
    h_match = re.search(r"(\d{1,2})\s*시\s*(?:(\d{1,2})\s*분)?", text)
    if h_match:
        return TimeResolution(
            hour=int(h_match.group(1)),
            minute=int(h_match.group(2)) if h_match.group(2) else 0,
        )

    return TimeResolution()
