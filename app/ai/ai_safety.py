"""ai_safety — AI 안전 정책 검사 helper (SSOT § 9 모듈 구조 정합).

역할:
- AI_SAFETY_POLICY.md 의 정책 검사 로직을 단일 모듈로 통합:
  * Privacy — 외부 AI API 전송 페이로드의 PII 미포함 검사
  * Hallucination — 단정 표현 / 데이터 출처-상태 정합 검사
  * 금지 문구 / 금지 키 상수
- 다른 AI 모듈 (ai_harness, ai_executor, 향후 router) 이 본 모듈을 import 해서
  *동일한 안전 게이트* 를 사용하도록 단일 원천 보장.

설계:
- 본 모듈은 **순수 함수** (DB 의존 0 / 외부 호출 0).
- ParserContext / dict / dataclass 등 임의 페이로드를 받아 검사.
- AI_HARNESS_PLAN § 1.7 (Privacy 하네스) / § 1.8 (Hallucination 하네스) 정합.

cross-reference:
- AI_SAFETY_POLICY.md § 2 (할루시네이션 방지)
- AI_SAFETY_POLICY.md § 3.2 (외부 전송 금지 항목)
- AI_CURRENT_DECISIONS.md § 9 (모듈 구조) — 본 모듈 위치
- AI_MISTAKES_LOG.md § #003 (본 모듈 미구현 실수 보강)

하네스: tests/test_phase06_ai_safety.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.ai_command_schema import (
    DataSourceState,
    ParsedCommand,
    TreatmentItem,
    TreatmentItemStatus,
)
from app.ai.ai_resolver import PatientResolution


# ────────────────────────────── Privacy ──────────────────────────────


PRIVACY_FORBIDDEN_KEYS: tuple[str, ...] = (
    "patient_list",
    "all_patients",
    "all_phones",
    "phone_list",
    "all_birth_dates",
    "birth_date_list",
    "patient_memo",
    "appointment_memo",
    "all_appointments",
    "all_stats",
    "patient_birth_date",
    "patient_phone",
)


@dataclass
class PrivacyCheckResult:
    """외부 전송 페이로드 PII 검사 결과."""

    ok: bool = True
    violations: list[str] = field(default_factory=list)


def check_privacy_payload(payload: Any) -> PrivacyCheckResult:
    """페이로드에 PII 키가 섞여있는지 재귀 검사 (AI_SAFETY_POLICY § 3.2).

    - dict → 키 이름 검사 + 값 재귀.
    - list → 항목 재귀.
    - dataclass → asdict 변환 후 검사.
    - 그 외 → 통과.
    """
    result = PrivacyCheckResult()
    if payload is None:
        return result

    if hasattr(payload, "__dataclass_fields__"):
        from dataclasses import asdict

        payload = asdict(payload)

    _scan_for_privacy(payload, path="", result=result)
    result.ok = not result.violations
    return result


def _scan_for_privacy(node: Any, *, path: str, result: PrivacyCheckResult) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            sub_path = f"{path}.{key}" if path else key
            if isinstance(key, str) and key.lower() in PRIVACY_FORBIDDEN_KEYS:
                result.violations.append(f"{sub_path} (금지 키)")
                continue
            _scan_for_privacy(value, path=sub_path, result=result)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _scan_for_privacy(item, path=f"{path}[{i}]", result=result)


# ────────────────────────────── Hallucination ──────────────────────────────


FORBIDDEN_PHRASES: tuple[str, ...] = (
    "예약 완료했습니다",
    "예약 완료되었습니다",
    "예약 완료",
    "환자 등록 완료",
)


@dataclass
class HallucinationCheckResult:
    """할루시네이션 검사 결과."""

    ok: bool = True
    violations: list[str] = field(default_factory=list)


def check_hallucination(
    parsed: ParsedCommand,
    *,
    patient_resolution: PatientResolution | None = None,
    treatment_items: list[TreatmentItem] | None = None,
    response_text: str | None = None,
) -> HallucinationCheckResult:
    """할루시네이션 검사 (AI_SAFETY_POLICY § 2).

    검사 항목:
    - 응답 텍스트의 단정 표현 ("예약 완료" 등)
    - 치료항목 status / matched_id / source 정합성
    - parsed 의 raw_text 와 채워진 필드 정합성
    """
    result = HallucinationCheckResult()

    if response_text:
        for phrase in FORBIDDEN_PHRASES:
            if phrase in response_text:
                result.violations.append(f"단정적 표현: '{phrase}'")

    for ti in treatment_items or []:
        if ti.status == TreatmentItemStatus.DB_VERIFIED:
            if not ti.matched_treatment_id:
                result.violations.append(
                    f"치료항목 '{ti.raw_text}' status=db_verified 인데 matched_treatment_id 없음"
                )
        elif ti.status in (
            TreatmentItemStatus.ALIAS_CONFLICT,
            TreatmentItemStatus.NOT_FOUND,
            TreatmentItemStatus.NEEDS_CLARIFICATION,
        ):
            if ti.matched_treatment_id:
                result.violations.append(
                    f"치료항목 '{ti.raw_text}' status={ti.status.value} 인데 matched_treatment_id 가 채워짐"
                )
            if ti.source == DataSourceState.DB_VERIFIED:
                result.violations.append(
                    f"치료항목 '{ti.raw_text}' source=db_verified 인데 status={ti.status.value}"
                )

    if parsed.raw_text == "" and (
        parsed.patient_name or parsed.chart_number or parsed.therapist_name
    ):
        result.violations.append("raw_text 가 비어있는데 parsed 필드가 채워짐")

    # patient_resolution 은 현재 위반 패턴 미정의 (resolver 가 자체 mismatch / not_found 처리)
    # 향후 단정 표현 추가 시 본 자리에서 검사.
    _ = patient_resolution  # 명시적 무시 (향후 사용 예약)

    result.ok = not result.violations
    return result
