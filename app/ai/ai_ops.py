"""ai_ops — Phase 11 운영 도우미 / 데이터 품질 검사 AI.

intent: `data_quality_check`, `ops_assistant`

역할:
- 데이터 품질 검사 (차트번호 중복 / 연락처 누락 / 이름+생년월일 / 연락처 중복)
- 운영 도우미 (빈 시간대 / 치료사 과부하 분석 / 추천)
- 모든 함수 **read-only** + **추천만** — 자동 수정 / 자동 예약 ⊥

설계:
- 본 모듈은 **read-only** + **자동 수정 함수 미노출** — 자동 수정 ⊥ 게이트.
- 환자 목록 응답에 차트번호 / 이름 / 생년월일 / 연락처 포함 — *내부 화면 표시용*.
  외부 AI API 전송 ⊥ (caller 가 외부 전송 시 별도 차단 필요).
- 수정은 별도 intent (`update_appointment` / `create_appointment` / 환자관리 service) 로만 분리.

cross-reference:
- 13 필드 정의 → AI_FEATURE_MASTER_PLAN.md § 5.5
- 자동 수정 ⊥ → AI_SAFETY_POLICY.md § 1.1 #1~#7 / § 5.5 (5차 기능 공통)

하네스: tests/test_phase11_ai_ops.py
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any


# ────────────────────────────── 결과 데이터 ──────────────────────────────


@dataclass
class DataQualityIssue:
    """데이터 품질 이슈 1건 — 추천만 (자동 수정 ⊥)."""

    kind: str  # "chart_no_duplicate" / "phone_missing" / "name_birth_duplicate" / "phone_duplicate"
    severity: str  # "warning" / "info"
    description: str
    affected_patients: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DataQualityReport:
    issues: list[DataQualityIssue] = field(default_factory=list)
    total_count: int = 0


@dataclass
class EmptySlot:
    therapist_id: str
    therapist_name: str
    target_date: date
    hour: int  # 시작 시 (정시 기준 슬롯)


@dataclass
class TherapistLoad:
    therapist_id: str
    therapist_name: str
    appointment_count: int
    total_minutes: int


# ────────────────────────────── 1. data_quality_check ──────────────────────────────


def check_chart_no_duplicates(session: Any) -> DataQualityIssue | None:
    from sqlalchemy import select

    from app.models.models import Patient

    rows = list(session.execute(select(Patient)).scalars())
    by_chart: defaultdict[str, list[Any]] = defaultdict(list)
    for p in rows:
        if p.chart_no:
            by_chart[p.chart_no].append(p)

    duplicates = [(k, v) for k, v in by_chart.items() if len(v) > 1]
    if not duplicates:
        return None

    affected: list[dict[str, Any]] = []
    for chart_no, patients in duplicates:
        for p in patients:
            affected.append(
                {
                    "id": p.id,
                    "chart_no": p.chart_no,
                    "name": p.name,
                    "birth_date": p.birth_date,
                    "phone": p.phone,
                }
            )
    return DataQualityIssue(
        kind="chart_no_duplicate",
        severity="warning",
        description=f"차트번호 중복 의심 {len(duplicates)} 그룹 ({len(affected)} 환자)",
        affected_patients=affected,
    )


def check_phone_missing(session: Any) -> DataQualityIssue | None:
    from sqlalchemy import select

    from app.models.models import Patient

    rows = list(
        session.execute(
            select(Patient).where((Patient.phone.is_(None)) | (Patient.phone == ""))
        ).scalars()
    )
    if not rows:
        return None
    return DataQualityIssue(
        kind="phone_missing",
        severity="info",
        description=f"연락처 누락 환자 {len(rows)} 명",
        affected_patients=[
            {
                "id": p.id,
                "chart_no": p.chart_no,
                "name": p.name,
                "birth_date": p.birth_date,
                "phone": p.phone,
            }
            for p in rows
        ],
    )


def check_name_birth_duplicates(session: Any) -> DataQualityIssue | None:
    from sqlalchemy import select

    from app.models.models import Patient

    rows = list(session.execute(select(Patient)).scalars())
    by_key: defaultdict[tuple[str, str], list[Any]] = defaultdict(list)
    for p in rows:
        if p.name and p.birth_date:
            by_key[(p.name, p.birth_date)].append(p)

    duplicates = [(k, v) for k, v in by_key.items() if len(v) > 1]
    if not duplicates:
        return None

    affected: list[dict[str, Any]] = []
    for (_name, _birth), patients in duplicates:
        for p in patients:
            affected.append(
                {
                    "id": p.id,
                    "chart_no": p.chart_no,
                    "name": p.name,
                    "birth_date": p.birth_date,
                    "phone": p.phone,
                }
            )
    return DataQualityIssue(
        kind="name_birth_duplicate",
        severity="warning",
        description=f"같은 이름+생년월일 환자 {len(duplicates)} 그룹 ({len(affected)} 명)",
        affected_patients=affected,
    )


def check_phone_duplicates(session: Any) -> DataQualityIssue | None:
    from sqlalchemy import select

    from app.models.models import Patient

    rows = list(session.execute(select(Patient)).scalars())
    by_phone: defaultdict[str, list[Any]] = defaultdict(list)
    for p in rows:
        if p.phone:
            by_phone[p.phone].append(p)

    duplicates = [(k, v) for k, v in by_phone.items() if len(v) > 1]
    if not duplicates:
        return None

    affected: list[dict[str, Any]] = []
    for _phone, patients in duplicates:
        for p in patients:
            affected.append(
                {
                    "id": p.id,
                    "chart_no": p.chart_no,
                    "name": p.name,
                    "birth_date": p.birth_date,
                    "phone": p.phone,
                }
            )
    return DataQualityIssue(
        kind="phone_duplicate",
        severity="warning",
        description=f"같은 연락처 환자 {len(duplicates)} 그룹 ({len(affected)} 명)",
        affected_patients=affected,
    )


def run_data_quality_check(
    session: Any,
    *,
    check_kinds: tuple[str, ...] | None = None,
) -> DataQualityReport:
    """전체 또는 선택 검사. read-only.

    check_kinds: ("chart_no" / "phone_missing" / "name_birth" / "phone") 중 선택.
    """
    available = {
        "chart_no": check_chart_no_duplicates,
        "phone_missing": check_phone_missing,
        "name_birth": check_name_birth_duplicates,
        "phone": check_phone_duplicates,
    }
    selected = check_kinds or tuple(available.keys())

    report = DataQualityReport()
    for kind in selected:
        fn = available.get(kind)
        if fn is None:
            continue
        issue = fn(session)
        if issue is not None:
            report.issues.append(issue)
            report.total_count += len(issue.affected_patients)
    return report


# ────────────────────────────── 2. ops_assistant ──────────────────────────────


def find_empty_slots(
    session: Any,
    *,
    target_date: date,
    therapist_id: str,
    hour_range: tuple[int, int] = (9, 18),
    slot_minutes: int = 30,
) -> list[EmptySlot]:
    """치료사 + 날짜 + 시간 범위 내의 빈 슬롯 추천 (read-only).

    - 시간 범위 hour_range = (start_hour, end_hour) — 끝 미포함.
    - status='canceled' 예약은 충돌 후보에서 제외.
    - 치료사 휴무 (full / am / pm) 도 고려 — 휴무 시간대는 빈 슬롯 후보에서 제외.
    """
    from sqlalchemy import select

    from app.models.models import Appointment, Employee, EmployeeLeave

    therapist = session.execute(
        select(Employee).where(Employee.id == therapist_id)
    ).scalar_one_or_none()
    if therapist is None or not therapist.active:
        return []

    # 휴무 검사
    leaves = list(
        session.execute(
            select(EmployeeLeave)
            .where(EmployeeLeave.employee_id == therapist_id)
            .where(EmployeeLeave.leave_date == target_date.isoformat())
        ).scalars()
    )
    leave_blocks: list[tuple[int, int]] = []  # (start_hour, end_hour)
    for lv in leaves:
        if lv.leave_type == "full":
            return []  # 종일 휴무 → 빈 슬롯 0
        if lv.leave_type == "am":
            leave_blocks.append((0, 13))
        elif lv.leave_type == "pm":
            leave_blocks.append((13, 24))

    # 기존 예약 (canceled 제외)
    day_start = datetime.combine(target_date, time(0, 0))
    day_end = day_start + timedelta(days=1)
    appts = list(
        session.execute(
            select(Appointment)
            .where(Appointment.therapist_id == therapist_id)
            .where(Appointment.start_at >= day_start)
            .where(Appointment.start_at < day_end)
        ).scalars()
    )
    booked_intervals: list[tuple[datetime, datetime]] = [
        (a.start_at, a.end_at) for a in appts if getattr(a, "status", None) != "canceled"
    ]

    # 슬롯 생성 — 정시 기준 (slot_minutes 단위)
    slots: list[EmptySlot] = []
    start_h, end_h = hour_range
    for h in range(start_h, end_h):
        # 휴무 블록 검사
        if any(b[0] <= h < b[1] for b in leave_blocks):
            continue
        slot_start = datetime.combine(target_date, time(h, 0))
        slot_end = slot_start + timedelta(minutes=slot_minutes)
        # 기존 예약과 겹치는지
        conflict = any(
            slot_start < bend and bstart < slot_end for bstart, bend in booked_intervals
        )
        if not conflict:
            slots.append(
                EmptySlot(
                    therapist_id=therapist_id,
                    therapist_name=therapist.name,
                    target_date=target_date,
                    hour=h,
                )
            )
    return slots


def analyze_therapist_load(
    session: Any,
    *,
    period_start: date,
    period_end: date,
) -> list[TherapistLoad]:
    """기간 내 치료사별 부하 분석 (read-only).

    appointment_count 가 많은 순으로 정렬.
    canceled 제외.
    """
    from sqlalchemy import select

    from app.models.models import Appointment, Employee

    if period_start > period_end:
        raise ValueError("period_start 가 period_end 보다 이후입니다.")

    range_start = datetime.combine(period_start, time(0, 0))
    range_end = datetime.combine(period_end, time(0, 0)) + timedelta(days=1)

    rows = list(
        session.execute(
            select(Appointment, Employee)
            .outerjoin(Employee, Employee.id == Appointment.therapist_id)
            .where(Appointment.start_at >= range_start)
            .where(Appointment.start_at < range_end)
        ).all()
    )

    counter: Counter[tuple[str, str]] = Counter()
    minutes: defaultdict[tuple[str, str], int] = defaultdict(int)
    for appt, therapist in rows:
        if getattr(appt, "status", None) == "canceled":
            continue
        if therapist is None:
            key = ("(미배정)", "(미배정)")
        else:
            key = (therapist.id, therapist.name)
        counter[key] += 1
        dur_min = int((appt.end_at - appt.start_at).total_seconds() // 60)
        minutes[key] += dur_min

    loads = [
        TherapistLoad(
            therapist_id=tid,
            therapist_name=tname,
            appointment_count=count,
            total_minutes=minutes[(tid, tname)],
        )
        for (tid, tname), count in counter.items()
    ]
    loads.sort(key=lambda x: x.appointment_count, reverse=True)
    return loads


# ────────────────────────────── 3. preview ──────────────────────────────


def build_data_quality_preview(report: DataQualityReport) -> dict[str, Any]:
    """데이터 품질 검사 결과 카드.

    actions 에 "자동 수정" / "자동 병합" 없음 — 자동 수정 ⊥.
    """
    return {
        "kind": "data_quality_report",
        "title": "데이터 품질 검사 결과",
        "total_count": report.total_count,
        "issues": [
            {
                "kind": i.kind,
                "severity": i.severity,
                "description": i.description,
                "affected_patients": i.affected_patients,
            }
            for i in report.issues
        ],
        "actions": ["환자관리에서 직접 검토", "닫기"],  # 자동 수정 ⊥
        "auto_modify_disabled": True,
        "read_only": True,
    }


def build_empty_slots_preview(
    slots: list[EmptySlot], *, target_date: date, therapist_id: str
) -> dict[str, Any]:
    return {
        "kind": "empty_slots_recommendation",
        "title": "빈 시간 추천",
        "target_date": target_date.isoformat(),
        "therapist_id": therapist_id,
        "slots": [
            {
                "therapist_id": s.therapist_id,
                "therapist_name": s.therapist_name,
                "hour": s.hour,
                "target_date": s.target_date.isoformat(),
            }
            for s in slots
        ],
        "actions": ["예약 등록 화면으로 이동", "닫기"],  # 자동 예약 ⊥
        "auto_create_disabled": True,
        "read_only": True,
    }


def build_therapist_load_preview(
    loads: list[TherapistLoad], *, period_start: date, period_end: date
) -> dict[str, Any]:
    return {
        "kind": "therapist_load_analysis",
        "title": "치료사별 부하 분석",
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "loads": [
            {
                "therapist_id": x.therapist_id,
                "therapist_name": x.therapist_name,
                "appointment_count": x.appointment_count,
                "total_minutes": x.total_minutes,
            }
            for x in loads
        ],
        "actions": ["닫기"],
        "auto_balance_disabled": True,
        "read_only": True,
    }
