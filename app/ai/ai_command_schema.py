"""ai_command_schema — AI 명령 데이터 / 상태값 정의 (Phase 1).

역할:
- AI 명령 (자연어 → 구조화 JSON) 의 입력 / 출력 데이터 모델 정의.
- AI 명령 상태값 (23종, 4 카테고리) 정의.
- 데이터 출처 상태 (5종) 정의.
- 치료항목 매칭 상태 정의.

주의:
- 본 모듈은 **순수 데이터 정의** 모듈입니다.
- DB 직접 수정 금지 / 외부 호출 금지.
- 기존 service 호출도 하지 않습니다 (단순 dataclass / Enum).
- Phase 2 이후 ai_parser / ai_resolver 등이 본 모듈의 데이터 구조를 사용.

cross-reference:
- 23 상태값 → AI_COMMAND_ARCHITECTURE.md § 3
- 9 추출 필드 → AI_FEATURE_MASTER_PLAN.md § 6.1
- treatment_items 배열 → AI_FEATURE_MASTER_PLAN.md § 11.5
- 데이터 출처 상태 → AI_SAFETY_POLICY.md § 2.3
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AiIntent(str, Enum):
    """AI 명령 intent (5 카테고리, Phase 2~11 에 걸쳐 단계 구현)."""

    # 1차 (Phase 2~5)
    CREATE_APPOINTMENT = "create_appointment"
    # 2차 (Phase 7)
    UPDATE_APPOINTMENT = "update_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    # 3차 (Phase 8~9)
    CREATE_LEAVE = "create_leave"
    PREPARE_SMS = "prepare_sms"
    # 4차 (Phase 10)
    SUMMARIZE_TODAY = "summarize_today"
    SUMMARIZE_TOMORROW = "summarize_tomorrow"
    ANALYZE_STATS = "analyze_stats"
    # 5차 (Phase 11)
    DATA_QUALITY_CHECK = "data_quality_check"
    OPS_ASSISTANT = "ops_assistant"


class AiCommandStatus(str, Enum):
    """AI 명령 상태값 — 23 종 / 4 카테고리.

    AI_COMMAND_ARCHITECTURE.md § 3 과 1:1 정합.
    """

    # § 3.1 기본 상태 (9)
    RECEIVED = "received"
    PARSED = "parsed"
    NEEDS_CLARIFICATION = "needs_clarification"
    VALIDATION_FAILED = "validation_failed"
    NEEDS_APPROVAL = "needs_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"

    # § 3.2 환자 후보 관련 (4)
    PATIENT_CANDIDATES_FOUND = "patient_candidates_found"
    PATIENT_SELECTION_REQUIRED = "patient_selection_required"
    PATIENT_SELECTED = "patient_selected"
    PATIENT_MISMATCH = "patient_mismatch"

    # § 3.3 신환 흐름 (6)
    PATIENT_NOT_FOUND = "patient_not_found"
    PATIENT_REGISTRATION_PROPOSED = "patient_registration_proposed"
    PATIENT_REGISTRATION_NEEDS_APPROVAL = "patient_registration_needs_approval"
    PATIENT_REGISTRATION_FAILED = "patient_registration_failed"
    PATIENT_REGISTERED = "patient_registered"
    APPOINTMENT_NEEDS_REVALIDATION = "appointment_needs_revalidation"

    # § 3.4 치료항목 (4)
    TREATMENT_RESOLVED = "treatment_resolved"
    TREATMENT_SELECTION_REQUIRED = "treatment_selection_required"
    TREATMENT_ALIAS_CONFLICT = "treatment_alias_conflict"
    TREATMENT_NOT_FOUND = "treatment_not_found"


class DataSourceState(str, Enum):
    """데이터 출처 상태 — 할루시네이션 방지.

    AI_SAFETY_POLICY.md § 2.3 의 5 상태.
    승인 화면에는 db_verified / user_confirmed / system_resolved 우선 표시.
    ai_extracted 만 남은 핵심 필드는 승인 차단 사유.
    """

    AI_EXTRACTED = "ai_extracted"
    DB_VERIFIED = "db_verified"
    USER_CONFIRMED = "user_confirmed"
    SYSTEM_RESOLVED = "system_resolved"
    SYSTEM_EXECUTED = "system_executed"


class TreatmentItemStatus(str, Enum):
    """treatment_items 배열의 각 항목 상태 — alias 매칭 결과."""

    DB_VERIFIED = "db_verified"
    NEEDS_CLARIFICATION = "needs_clarification"
    NOT_FOUND = "not_found"
    ALIAS_CONFLICT = "alias_conflict"


@dataclass
class TreatmentItem:
    """치료항목 후보 1건 — 다중 약어 입력 ("도수30 주 충") 지원.

    AI_FEATURE_MASTER_PLAN.md § 11.5 구조 예시 참조.
    """

    raw_text: str
    matched_treatment_id: str | None = None
    matched_treatment_name: str | None = None
    source: DataSourceState = DataSourceState.AI_EXTRACTED
    status: TreatmentItemStatus = TreatmentItemStatus.NEEDS_CLARIFICATION
    candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ParsedCommand:
    """AI parser 출력 — 9 추출 필드 (AI_FEATURE_MASTER_PLAN.md § 6.1).

    AI 가 자연어 명령에서 추출한 구조화 데이터. 아직 DB 검증 전이므로
    모든 필드의 source 는 기본 ai_extracted. resolver 가 DB 매칭 후 갱신.
    """

    intent: AiIntent | None = None
    patient_name: str | None = None
    chart_number: str | None = None
    date_text: str | None = None
    time_text: str | None = None
    therapist_name: str | None = None
    treatment_text: str | None = None
    treatment_items: list[TreatmentItem] = field(default_factory=list)
    memo: str | None = None
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """ai_command_logs.parsed_json 저장용 dict 변환."""
        return {
            "intent": self.intent.value if self.intent else None,
            "patient_name": self.patient_name,
            "chart_number": self.chart_number,
            "date_text": self.date_text,
            "time_text": self.time_text,
            "therapist_name": self.therapist_name,
            "treatment_text": self.treatment_text,
            "treatment_items": [
                {
                    "raw_text": ti.raw_text,
                    "matched_treatment_id": ti.matched_treatment_id,
                    "matched_treatment_name": ti.matched_treatment_name,
                    "source": ti.source.value,
                    "status": ti.status.value,
                    "candidates": ti.candidates,
                }
                for ti in self.treatment_items
            ],
            "memo": self.memo,
            "raw_text": self.raw_text,
        }


@dataclass
class ParserContext:
    """AI parser 호출 시 전달되는 최소 컨텍스트.

    외부 AI API 에 보내는 정보는 본 객체로 한정 (개인정보 미포함).
    AI_SAFETY_POLICY.md § 3.1 참조.
    """

    raw_text: str
    current_calendar_year: int
    current_calendar_month: int
    available_intents: list[str] = field(default_factory=list)
    treatment_names: list[str] = field(default_factory=list)
    # DB 의 모든 약어 — Treatment.short + treatment_aliases.alias_name + Treatment.code 등
    # parser 가 이 목록을 우선 사용해 raw_text 에서 토큰 추출 (하드코딩 정규식 fallback).
    treatment_aliases: list[str] = field(default_factory=list)
