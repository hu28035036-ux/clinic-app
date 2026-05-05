"""ai_summary — Phase 10 예약 요약 / 통계 분석 AI.

intent: `summarize_today`, `summarize_tomorrow`, `analyze_stats`

역할:
- 대상 날짜 / 기간의 예약 데이터를 **읽기 전용** 조회 + 한국어 요약 텍스트 생성.
- 모든 수치는 **DB 쿼리 결과만** (AI 임의 생성 ⊥).
- 외부 AI API 호출 0 — provider 미사용 (응답 텍스트는 결정적 템플릿).

설계:
- 본 모듈은 **read-only**. DB INSERT / UPDATE / DELETE / 수정 ⊥.
- 환자 식별 PII (이름 / 연락처) 는 본 모듈 응답에 *포함하지 않음* — 통계 수치만 (요약 표현).
  (AI_SAFETY_POLICY § 3.2 — 환자 전체 / 통계 원본 외부 전송 금지 정합)
- `manual_30=1` / `manual_60=1` 카운트 정책 유지 — 본 모듈은 단순 row 카운팅으로
  도수 30=1 / 60=2 가중치 합산 방식 ⊥.

cross-reference:
- 13 필드 정의 → AI_FEATURE_MASTER_PLAN.md § 5.4
- 수치 임의 생성 ⊥ → AI_SAFETY_POLICY.md § 1.3 #14 ~ #16
- 읽기 전용 → AI_SAFETY_POLICY.md § 1.1 #1 (DB 직접 수정 ⊥)
- manual60=1 정책 → CLAUDE.md § "절대 금지"

하네스: tests/test_phase10_ai_summary.py
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any


# ────────────────────────────── 결과 데이터 ──────────────────────────────


@dataclass
class DailySummary:
    """일일 예약 요약 (read-only DB 결과)."""

    target_date: date
    total_count: int = 0
    canceled_count: int = 0
    by_therapist: dict[str, int] = field(default_factory=dict)
    by_hour: dict[int, int] = field(default_factory=dict)
    by_treatment: dict[str, int] = field(default_factory=dict)


@dataclass
class StatsAnalysis:
    """기간 통계 분석 (read-only DB 결과)."""

    period_start: date
    period_end: date
    total_count: int = 0
    canceled_count: int = 0
    by_day: dict[str, int] = field(default_factory=dict)  # YYYY-MM-DD → count
    by_therapist: dict[str, int] = field(default_factory=dict)
    by_hour: dict[int, int] = field(default_factory=dict)
    by_treatment: dict[str, int] = field(default_factory=dict)


# ────────────────────────────── 1. 일일 요약 ──────────────────────────────


def summarize_for_date(session: Any, target_date: date) -> DailySummary:
    """대상 날짜의 read-only 예약 요약.

    - reserved + approved 예약을 total / by_* 에 합산.
    - canceled 는 canceled_count 만 계산 (본 그룹은 통계에서 제외).
    """
    from sqlalchemy import select

    from app.models.models import Appointment, Employee

    day_start = datetime.combine(target_date, time(0, 0))
    day_end = day_start + timedelta(days=1)

    rows = list(
        session.execute(
            select(Appointment, Employee)
            .outerjoin(Employee, Employee.id == Appointment.therapist_id)
            .where(Appointment.start_at >= day_start)
            .where(Appointment.start_at < day_end)
        ).all()
    )

    summary = DailySummary(target_date=target_date)
    by_therapist_counter: Counter[str] = Counter()
    by_hour_counter: Counter[int] = Counter()
    by_treatment_counter: Counter[str] = Counter()

    for appt, therapist in rows:
        if getattr(appt, "status", None) == "canceled":
            summary.canceled_count += 1
            continue
        summary.total_count += 1
        therapist_name = therapist.name if therapist else "(미배정)"
        by_therapist_counter[therapist_name] += 1
        by_hour_counter[appt.start_at.hour] += 1
        for code in _parse_codes(appt.treatment_codes):
            by_treatment_counter[code] += 1

    summary.by_therapist = dict(by_therapist_counter)
    summary.by_hour = dict(by_hour_counter)
    summary.by_treatment = dict(by_treatment_counter)
    return summary


def summarize_today(session: Any, today: date | None = None) -> DailySummary:
    return summarize_for_date(session, today or date.today())


def summarize_tomorrow(session: Any, today: date | None = None) -> DailySummary:
    base = today or date.today()
    return summarize_for_date(session, base + timedelta(days=1))


# ────────────────────────────── 2. 기간 통계 ──────────────────────────────


def analyze_stats_period(
    session: Any,
    *,
    period_start: date,
    period_end: date,
    therapist_id_filter: str | None = None,
    treatment_code_filter: str | None = None,
) -> StatsAnalysis:
    """기간 통계 분석 (read-only).

    period_start ~ period_end 양 끝 포함.
    """
    from sqlalchemy import select

    from app.models.models import Appointment, Employee

    if period_start > period_end:
        raise ValueError("period_start 가 period_end 보다 이후입니다.")

    range_start = datetime.combine(period_start, time(0, 0))
    range_end = datetime.combine(period_end, time(0, 0)) + timedelta(days=1)

    stmt = (
        select(Appointment, Employee)
        .outerjoin(Employee, Employee.id == Appointment.therapist_id)
        .where(Appointment.start_at >= range_start)
        .where(Appointment.start_at < range_end)
    )
    if therapist_id_filter:
        stmt = stmt.where(Appointment.therapist_id == therapist_id_filter)

    rows = list(session.execute(stmt).all())

    analysis = StatsAnalysis(period_start=period_start, period_end=period_end)
    by_day: Counter[str] = Counter()
    by_therapist: Counter[str] = Counter()
    by_hour: Counter[int] = Counter()
    by_treatment: Counter[str] = Counter()

    for appt, therapist in rows:
        if getattr(appt, "status", None) == "canceled":
            analysis.canceled_count += 1
            continue
        codes = _parse_codes(appt.treatment_codes)
        if treatment_code_filter and treatment_code_filter not in codes:
            continue
        analysis.total_count += 1
        by_day[appt.start_at.date().isoformat()] += 1
        therapist_name = therapist.name if therapist else "(미배정)"
        by_therapist[therapist_name] += 1
        by_hour[appt.start_at.hour] += 1
        for code in codes:
            by_treatment[code] += 1

    analysis.by_day = dict(by_day)
    analysis.by_therapist = dict(by_therapist)
    analysis.by_hour = dict(by_hour)
    analysis.by_treatment = dict(by_treatment)
    return analysis


def _parse_codes(raw: Any) -> list[str]:
    import json

    if not raw:
        return []
    if isinstance(raw, list):
        return list(raw)
    try:
        parsed = json.loads(raw)
        return list(parsed) if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


# ────────────────────────────── 3. 한국어 요약 텍스트 ──────────────────────────────


def build_daily_summary_text(summary: DailySummary) -> str:
    """일일 요약 한국어 텍스트.

    AI 가 새 수치 생성 ⊥ — 본 함수는 DB 쿼리 결과를 그대로 인용.
    """
    lines = [f"{summary.target_date.isoformat()} 예약 요약"]
    lines.append(f"- 총 예약: {summary.total_count}건")
    if summary.canceled_count:
        lines.append(f"- 취소: {summary.canceled_count}건 (통계 제외)")
    if summary.by_therapist:
        therapists = ", ".join(
            f"{name} {count}건" for name, count in sorted(summary.by_therapist.items())
        )
        lines.append(f"- 치료사별: {therapists}")
    if summary.by_hour:
        hours = ", ".join(
            f"{h:02d}시 {count}건" for h, count in sorted(summary.by_hour.items())
        )
        lines.append(f"- 시간대별: {hours}")
    if summary.by_treatment:
        treatments = ", ".join(
            f"{code} {count}건" for code, count in sorted(summary.by_treatment.items())
        )
        lines.append(f"- 치료항목별: {treatments}")
    return "\n".join(lines)


def build_stats_analysis_text(analysis: StatsAnalysis) -> str:
    """기간 통계 한국어 텍스트."""
    lines = [
        f"{analysis.period_start.isoformat()} ~ {analysis.period_end.isoformat()} 통계 분석"
    ]
    lines.append(f"- 총 예약: {analysis.total_count}건")
    if analysis.canceled_count:
        lines.append(f"- 취소: {analysis.canceled_count}건 (통계 제외)")
    if analysis.by_therapist:
        sorted_t = sorted(
            analysis.by_therapist.items(), key=lambda kv: kv[1], reverse=True
        )
        therapists = ", ".join(f"{name} {count}건" for name, count in sorted_t)
        lines.append(f"- 치료사별: {therapists}")
    if analysis.by_treatment:
        sorted_tr = sorted(
            analysis.by_treatment.items(), key=lambda kv: kv[1], reverse=True
        )
        treatments = ", ".join(f"{code} {count}건" for code, count in sorted_tr)
        lines.append(f"- 치료항목별: {treatments}")
    if analysis.by_hour:
        peak_hour = max(analysis.by_hour.items(), key=lambda kv: kv[1])
        lines.append(f"- 가장 바쁜 시간: {peak_hour[0]:02d}시 ({peak_hour[1]}건)")
    return "\n".join(lines)


# ────────────────────────────── 4. preview ──────────────────────────────


def build_summary_preview(summary: DailySummary) -> dict[str, Any]:
    return {
        "kind": "daily_summary",
        "target_date": summary.target_date.isoformat(),
        "total_count": summary.total_count,
        "canceled_count": summary.canceled_count,
        "by_therapist": summary.by_therapist,
        "by_hour": summary.by_hour,
        "by_treatment": summary.by_treatment,
        "text": build_daily_summary_text(summary),
        "read_only": True,
    }


def build_analysis_preview(analysis: StatsAnalysis) -> dict[str, Any]:
    return {
        "kind": "stats_analysis",
        "period_start": analysis.period_start.isoformat(),
        "period_end": analysis.period_end.isoformat(),
        "total_count": analysis.total_count,
        "canceled_count": analysis.canceled_count,
        "by_day": analysis.by_day,
        "by_therapist": analysis.by_therapist,
        "by_hour": analysis.by_hour,
        "by_treatment": analysis.by_treatment,
        "text": build_stats_analysis_text(analysis),
        "read_only": True,
    }
