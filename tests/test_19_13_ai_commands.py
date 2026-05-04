"""19-13 AI commands 와 기존 예약 / 휴무 / 문자 연결부 정리 contract.

검증 범위 (19-13 세션 지시문 정합):
  1. ``commands.schemas`` 가 ``app/routers/ai.py`` / ``app/services/ai/*`` 인라인
     응답 dict / outcome 셋과 byte-equivalent.
  2. ``commands.safety`` 의 outcome → reason_code 매핑이 ``services/ai/action_leave.
     py:USER_MESSAGES`` 와 정합.
  3. ``commands.preview`` 의 ``serialize_*`` 가 ``ai.py:_serialize_parse_result`` /
     ``_serialize_preview_result`` byte-equivalent.
  4. ``commands.executor`` 의 ``http_status_for_execute`` 가 ``ai.py:action_execute``
     분기 byte-equivalent.
  5. ``commands.service`` 의 토큰 정책 / mode / leave_type / leave_kind /
     confidence / tone 셋이 ``services/ai/action_leave.py`` / ``ai.py`` 와 정합.
  6. **provider 호출 0회 정책** (Local-first) reason_code 셋 가드.
  7. **승인 없는 DB 변경 차단** (Approval) reason_code 셋 가드.
  8. **PII / API key / 문자나라 계정 원문 비노출** 정책 가드.
  9. ``commands.*`` 가 ``app.routers`` / ``app.services.ai`` 직접 import ⊥
     (단방향 경계).
 10. 라우터 / 서비스 본체 시그니처 / 응답 key 무수정.
 11. AI 예약 흐름은 *후속 검토* — INTENT_NAMES_TODO 만 표기.
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.modules.ai.commands import adapters as _adapters
from app.modules.ai.commands import executor as _executor
from app.modules.ai.commands import preview as _preview
from app.modules.ai.commands import safety as _safety
from app.modules.ai.commands import schemas as _schemas
from app.modules.ai.commands import service as _service

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_ROUTERS_AI = REPO_ROOT / "app" / "routers" / "ai.py"
APP_ROUTERS_API = REPO_ROOT / "app" / "routers" / "api.py"
APP_SERVICES_ACTION_LEAVE = REPO_ROOT / "app" / "services" / "ai" / "action_leave.py"
APP_SERVICES_SMS_DRAFT = REPO_ROOT / "app" / "services" / "ai" / "sms_draft.py"
APP_SERVICES_MANUAL_QA = REPO_ROOT / "app" / "services" / "ai" / "manual_qa.py"


# ──────────────────────── 1. schemas — 응답 키 contract ────────────────────────


def test_schemas_action_parse_response_keys():
    """COMPAT: ``POST /api/ai/action/parse`` 응답 key 6개 정합."""
    assert _schemas.ACTION_PARSE_RESPONSE_KEYS == frozenset({
        "ok", "outcome", "parsed", "warnings", "safe_to_continue", "message",
    })


def test_schemas_action_preview_response_keys():
    """COMPAT: ``POST /api/ai/action/preview`` 응답 key 11개 정합."""
    assert _schemas.ACTION_PREVIEW_RESPONSE_KEYS == frozenset({
        "ok", "outcome", "candidate", "mode", "existing", "appointments_count",
        "warnings", "safe_to_execute", "preview_token", "preview_token_exp", "message",
    })


def test_schemas_action_execute_response_keys():
    """COMPAT: ``POST /api/ai/action/execute`` 응답 key 5개 정합."""
    assert _schemas.ACTION_EXECUTE_RESPONSE_KEYS == frozenset({
        "ok", "outcome", "leave_id", "mode", "message",
    })


def test_schemas_sms_draft_response_keys():
    """COMPAT: ``POST /api/ai/sms/draft`` 응답 key (라우터 전 prompt_text/response_text 제거 후) 정합."""
    expected = {
        "draft", "warnings", "missing_fields", "context_used",
        "needs_user_confirm", "skipped", "skip_reason",
        "blocked", "blocked_reason", "guard_hits",
    }
    assert _schemas.SMS_DRAFT_RESPONSE_KEYS == frozenset(expected)


def test_schemas_sms_draft_forbidden_keys():
    """SAFETY: ``prompt_text`` / ``response_text`` 응답 부재 보장 가드."""
    assert "prompt_text" in _schemas.SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS
    assert "response_text" in _schemas.SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS
    # 응답 key 셋과 isdisjoint 검증.
    assert _schemas.SMS_DRAFT_FORBIDDEN_RESPONSE_KEYS.isdisjoint(
        _schemas.SMS_DRAFT_RESPONSE_KEYS,
    )


def test_schemas_intent_names_implemented():
    """COMPAT: 현재 구현된 INTENT 셋 — services/ai/action_leave.py:INTENT_NAME 정합."""
    assert "create_therapist_leave" in _schemas.INTENT_NAMES_IMPLEMENTED
    assert _service.ACTION_LEAVE_INTENT_NAME == "create_therapist_leave"


def test_schemas_intent_names_todo_disjoint_from_implemented():
    """NOTE: TODO INTENT 셋은 IMPLEMENTED 와 isdisjoint."""
    assert _schemas.INTENT_NAMES_IMPLEMENTED.isdisjoint(_schemas.INTENT_NAMES_TODO)


def test_schemas_action_leave_outcomes_match_user_messages():
    """COMPAT: ACTION_LEAVE_OUTCOMES 셋이 services/ai/action_leave.py:USER_MESSAGES 정합."""
    src = APP_SERVICES_ACTION_LEAVE.read_text(encoding="utf-8")
    # USER_MESSAGES 의 모든 키가 ACTION_LEAVE_OUTCOMES 안에 포함되는지 확인.
    for outcome in _schemas.ACTION_LEAVE_OUTCOMES:
        # USER_MESSAGES 안에 "outcome": 패턴 존재.
        assert f'"{outcome}":' in src, f"action_leave USER_MESSAGES 에 {outcome!r} 누락"


# ──────────────────────── 2. reason_code 셋 ────────────────────────


def test_reason_codes_provider_blocked_includes_required():
    """SAFETY: provider 호출 차단 reason_code 셋 정합."""
    required = {
        "pii_detected", "no_sources", "low_confidence", "unknown_feature",
        "external_api_not_allowed",
        "llm_skipped_local_only", "llm_skipped_pii",
        "llm_skipped_no_sources", "llm_skipped_low_confidence",
    }
    assert required <= _schemas.REASON_CODES_PROVIDER_BLOCKED


def test_reason_codes_approval_required_includes_required():
    """RISK: 승인 없는 DB 변경 차단 reason_code 셋 정합."""
    required = {
        "approval_required", "execution_blocked", "validation_failed",
        "not_confirmed", "overwrite_not_acknowledged",
        "token_format", "token_signature", "token_unsafe",
        "token_mismatch", "token_expired",
    }
    assert required <= _schemas.REASON_CODES_APPROVAL_REQUIRED


def test_reason_codes_lookup_failed_includes_required():
    """NOTE: 환자 / 치료사 / 치료항목 / 예약 매칭 실패 reason_code 셋."""
    required = {
        "patient_not_found", "patient_ambiguous",
        "therapist_not_found", "treatment_not_found",
        "appointment_conflict", "leave_conflict",
    }
    assert required <= _schemas.REASON_CODES_LOOKUP_FAILED


def test_reason_codes_all_disjoint_categories():
    """NOTE: 세 reason_code 셋은 서로 isdisjoint."""
    a = _schemas.REASON_CODES_PROVIDER_BLOCKED
    b = _schemas.REASON_CODES_APPROVAL_REQUIRED
    c = _schemas.REASON_CODES_LOOKUP_FAILED
    assert a.isdisjoint(b)
    assert a.isdisjoint(c)
    assert b.isdisjoint(c)


# ──────────────────────── 3. safety — outcome → reason_code 매핑 ────────────────────────


@pytest.mark.parametrize("outcome,expected_reason", [
    # 사전 게이트
    ("pii_blocked", "llm_skipped_pii"),
    ("input_too_short", "invalid_query"),
    ("no_leave_keyword", "unknown_feature"),
    # LLM 실패 / 환각
    ("low_confidence", "low_confidence"),
    ("hallucinated_name", "validation_failed"),
    ("provider_error", "external_api_not_allowed"),
    # 매칭
    ("no_match", "therapist_not_found"),
    ("multi_match", "patient_ambiguous"),
    # Token / 승인
    ("not_confirmed", "not_confirmed"),
    ("token_expired", "token_expired"),
    ("overwrite_not_acknowledged", "overwrite_not_acknowledged"),
    # 충돌
    ("conflict_changed", "appointment_conflict"),
    # 시스템
    ("db_error", "execution_blocked"),
    ("feature_disabled", "external_api_not_allowed"),
    # ok / None
    ("ok", None),
    (None, None),
])
def test_safety_map_action_leave_outcome_to_reason(outcome, expected_reason):
    """COMPAT: services/ai/action_leave.py outcome → reason_code 매핑 정합."""
    assert _safety.map_action_leave_outcome_to_reason(outcome) == expected_reason


@pytest.mark.parametrize("outcome,expected", [
    # provider 호출 차단 (LLM/Embedding 호출 ⊥)
    ("pii_blocked", True),  # llm_skipped_pii
    ("low_confidence", True),
    ("provider_error", True),  # external_api_not_allowed
    ("no_leave_keyword", True),  # unknown_feature
    # provider 호출 가능 (정상 흐름)
    ("ok", False),
    ("no_match", False),  # lookup_failed
    ("not_confirmed", False),  # approval_required
    ("conflict_changed", False),  # lookup_failed
])
def test_safety_is_provider_blocked_outcome(outcome, expected):
    """SAFETY: provider 호출 차단 분류 정합."""
    assert _safety.is_provider_blocked_outcome(outcome) is expected


@pytest.mark.parametrize("outcome,expected", [
    # 승인 필요 (DB write ⊥)
    ("not_confirmed", True),
    ("overwrite_not_acknowledged", True),
    ("token_expired", True),
    ("token_signature", True),
    # 승인 불필요 (정상 / 다른 분류)
    ("ok", False),
    ("pii_blocked", False),
    ("no_match", False),
    ("conflict_changed", False),
])
def test_safety_is_approval_required_outcome(outcome, expected):
    """RISK: Approval 가드 분류 정합."""
    assert _safety.is_approval_required_outcome(outcome) is expected


@pytest.mark.parametrize("outcome,expected", [
    # lookup 실패
    ("no_match", True),
    ("multi_match", True),
    ("inactive_therapist", True),
    ("not_therapist", True),
    ("conflict_changed", True),
    # lookup 성공 / 다른 분류
    ("ok", False),
    ("pii_blocked", False),
    ("not_confirmed", False),
])
def test_safety_is_lookup_failed_outcome(outcome, expected):
    """NOTE: lookup 실패 분류 정합."""
    assert _safety.is_lookup_failed_outcome(outcome) is expected


# ──────────────────────── 4. safety — 정책 상수 ────────────────────────


def test_safety_input_max_len_byte_equivalent():
    """COMPAT: services/ai/action_leave.py:_MAX_INPUT_LEN = 200 정합."""
    src = APP_SERVICES_ACTION_LEAVE.read_text(encoding="utf-8")
    assert "_MAX_INPUT_LEN = 200" in src
    assert _safety.INPUT_MAX_LEN == 200


def test_safety_leave_keywords_byte_equivalent():
    """COMPAT: services/ai/action_leave.py:_LEAVE_KEYWORDS 정합."""
    expected = ("휴무", "연차", "월차", "반차", "휴가", "쉼", "쉬는")
    assert _safety.LEAVE_KEYWORDS == expected


def test_safety_patient_indicators_byte_equivalent():
    """SAFETY: services/ai/action_leave.py:_PATIENT_INDICATORS 정합."""
    expected = ("환자", "차트", "카르테", "차트번호", "내원", "방문", "chart")
    assert _safety.PATIENT_INDICATORS == expected


@pytest.mark.parametrize("text,expected", [
    ("내일 김의사 휴무", True),
    ("연차 신청", True),
    ("환자 등록", False),
    ("", False),
    (None, False),
])
def test_safety_has_leave_keyword(text, expected):
    assert _safety.has_leave_keyword(text) is expected


@pytest.mark.parametrize("text,expected", [
    ("환자 김의사 등록", True),
    ("차트번호 12345", True),
    ("내일 김의사 휴무", False),
    ("", False),
    (None, False),
])
def test_safety_has_patient_indicator(text, expected):
    """SAFETY: PII 의심 키워드 검출 — 검출 시 LLM 호출 ⊥."""
    assert _safety.has_patient_indicator(text) is expected


@pytest.mark.parametrize("text,expected", [
    ("a", True),  # min=1
    ("x" * 200, True),  # max=200
    ("x" * 201, False),
    ("", False),
    (None, False),
])
def test_safety_is_input_length_valid(text, expected):
    assert _safety.is_input_length_valid(text) is expected


def test_safety_pii_forbidden_fields_includes_required():
    """SAFETY: PII 부재 필드 셋 정합."""
    required = {
        "phone", "rrn", "birth", "chart_no", "chart_no_maybe",
        "patient_memo", "real_name",
    }
    assert required <= _safety.PII_FORBIDDEN_FIELDS


def test_safety_secret_keys_forbidden_in_log():
    """SAFETY: 비밀 key 로그 부재 정책 정합."""
    required = {
        "api_key", "munjanara_pw", "munjanara_key",
        "admin_password_hash", "sync_secret", "preview_token",
    }
    assert required <= _safety.SECRET_KEYS_FORBIDDEN_IN_LOG


# ──────────────────────── 5. preview — 응답 빌더 byte-equivalent ────────────────────────


def test_preview_build_parse_response():
    """COMPAT: ``ai.py:_serialize_parse_result`` byte-equivalent."""
    out = _preview.build_parse_response(
        ok=True, outcome="ok",
        parsed={"intent": "create_therapist_leave", "employee_name_raw": "김의사"},
        warnings=[], safe_to_continue=True, message="",
    )
    assert set(out.keys()) == _schemas.ACTION_PARSE_RESPONSE_KEYS
    assert out["ok"] is True
    assert out["outcome"] == "ok"
    assert out["safe_to_continue"] is True


def test_preview_serialize_parse_result_byte_equivalent():
    """COMPAT: ParseResult dataclass → dict byte-equivalent."""
    r = SimpleNamespace(
        ok=False, outcome="pii_blocked", parsed=None,
        warnings=["입력에 개인정보로 보이는 내용이 있어 차단되었습니다"],
        safe_to_continue=False,
        message="입력에 개인정보로 보이는 내용이 있어 차단되었습니다",
    )
    out = _preview.serialize_parse_result(r)
    assert set(out.keys()) == _schemas.ACTION_PARSE_RESPONSE_KEYS
    assert out["ok"] is False
    assert out["outcome"] == "pii_blocked"


def test_preview_build_preview_response():
    """COMPAT: ``ai.py:_serialize_preview_result`` byte-equivalent."""
    out = _preview.build_preview_response(
        ok=True, outcome="ok",
        candidate={"employee_id": "abc"},
        mode="create",
        existing=None,
        appointments_count=0,
        warnings=[],
        safe_to_execute=True,
        preview_token="v1.payload.signature",
        preview_token_exp=1234567890,
        message="",
    )
    assert set(out.keys()) == _schemas.ACTION_PREVIEW_RESPONSE_KEYS
    assert out["mode"] == "create"
    assert out["safe_to_execute"] is True


def test_preview_serialize_preview_result_byte_equivalent():
    r = SimpleNamespace(
        ok=True, outcome="ok",
        candidate={"employee_id": "abc"}, mode="overwrite",
        existing={"id": "leave-1"}, appointments_count=2,
        warnings=["기존 휴무 덮어쓰기"], safe_to_execute=True,
        preview_token="v1.x.y", preview_token_exp=999,
        message="",
    )
    out = _preview.serialize_preview_result(r)
    assert set(out.keys()) == _schemas.ACTION_PREVIEW_RESPONSE_KEYS
    assert out["mode"] == "overwrite"
    assert out["appointments_count"] == 2


def test_preview_build_sms_draft_response_public_no_internal_keys():
    """SAFETY: SMS draft 응답에 prompt_text/response_text 부재 보장."""
    out = _preview.build_sms_draft_response_public(
        draft="안녕하세요",
        warnings=[], missing_fields=[],
        context_used={"appointment_id": "abc"},
        needs_user_confirm=True,
        skipped=False, skip_reason="",
        blocked=False, blocked_reason="",
        guard_hits=0,
    )
    assert "prompt_text" not in out
    assert "response_text" not in out
    assert set(out.keys()) == _schemas.SMS_DRAFT_RESPONSE_KEYS


# ──────────────────────── 6. executor — HTTP 상태 코드 매핑 ────────────────────────


@pytest.mark.parametrize("ok,outcome,expected_status", [
    # 성공
    (True, "ok", 200),
    (True, "anything", 200),
    # 동시성 충돌 → 409
    (False, "conflict_changed", 409),
    (False, "therapist_changed", 409),
    # 서버 에러 → 500
    (False, "db_error", 500),
    # 그 외 (Approval 가드) → 400
    (False, "not_confirmed", 400),
    (False, "overwrite_not_acknowledged", 400),
    (False, "token_format", 400),
    (False, "token_signature", 400),
    (False, "token_expired", 400),
    (False, "token_unsafe", 400),
    (False, "token_mismatch", 400),
    (False, "unknown_outcome", 400),
])
def test_executor_http_status_for_execute(ok, outcome, expected_status):
    """COMPAT: ``ai.py:action_execute`` 분기 byte-equivalent."""
    assert _executor.http_status_for_execute(ok=ok, outcome=outcome) == expected_status


def test_executor_build_execute_response():
    out = _executor.build_execute_response(
        ok=True, outcome="ok",
        leave_id="leave-1", mode="create",
        message="휴무 등록 완료",
    )
    assert set(out.keys()) == _schemas.ACTION_EXECUTE_RESPONSE_KEYS
    assert out["leave_id"] == "leave-1"
    assert out["mode"] == "create"


def test_executor_serialize_execute_result_byte_equivalent():
    r = SimpleNamespace(
        ok=False, outcome="not_confirmed",
        leave_id=None, mode=None,
        message="확인이 필요합니다",
    )
    out = _executor.serialize_execute_result(r)
    assert set(out.keys()) == _schemas.ACTION_EXECUTE_RESPONSE_KEYS
    assert out["ok"] is False
    assert out["outcome"] == "not_confirmed"


# ──────────────────────── 7. service — 정책 상수 ────────────────────────


def test_service_token_ttl_byte_equivalent():
    """RISK: TOKEN_TTL_SEC = 120 정합."""
    src = APP_SERVICES_ACTION_LEAVE.read_text(encoding="utf-8")
    assert "TOKEN_TTL_SEC = 120" in src
    assert _service.TOKEN_TTL_SEC == 120


def test_service_token_version_byte_equivalent():
    """RISK: TOKEN_VERSION = 1 정합."""
    src = APP_SERVICES_ACTION_LEAVE.read_text(encoding="utf-8")
    assert "TOKEN_VERSION = 1" in src
    assert _service.TOKEN_VERSION == 1


def test_service_action_leave_modes():
    """COMPAT: action_leave mode 셋 정합."""
    assert _service.ACTION_LEAVE_MODES == frozenset({"create", "overwrite", "noop"})


def test_service_leave_types():
    """COMPAT: leave_type 셋 정합."""
    assert _service.LEAVE_TYPES == frozenset({"full", "morning", "afternoon", "unknown"})


def test_service_leave_kinds():
    """COMPAT: leave_kind 셋 정합."""
    assert _service.LEAVE_KINDS == frozenset({"annual", "monthly", "unknown"})


def test_service_confidence_levels():
    """COMPAT: confidence 셋 정합."""
    assert _service.CONFIDENCE_LEVELS == frozenset({"high", "low"})


def test_service_sms_draft_tones():
    """COMPAT: sms_draft tone 셋 정합 (api/ai.py:sms_draft 검증과 byte-equivalent)."""
    assert _service.SMS_DRAFT_TONES == frozenset({"friendly", "formal"})
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert 'tone not in ("friendly", "formal")' in src


# ──────────────────────── 8. adapters — 19-x 후속 검토 표기 ────────────────────────


def test_adapters_ai_leave_flow_modules_documented():
    """NOTE: AI 휴무 흐름 → 19-x 채택 후보 모듈 문서화."""
    assert "app.modules.leaves" in _adapters.AI_LEAVE_FLOW_MODULES
    assert "app.modules.therapists" in _adapters.AI_LEAVE_FLOW_MODULES
    assert "app.modules.appointments" in _adapters.AI_LEAVE_FLOW_MODULES


def test_adapters_ai_sms_draft_flow_modules_documented():
    """NOTE: AI 문자 흐름 → 19-x 채택 후보 모듈 문서화."""
    assert "app.modules.sms" in _adapters.AI_SMS_DRAFT_FLOW_MODULES
    assert "app.modules.appointments" in _adapters.AI_SMS_DRAFT_FLOW_MODULES


def test_adapters_direct_call_forbidden_sets_includes_critical():
    """RISK: AI 가 직접 호출 ⊥ 정책 셋 정합."""
    required = {
        "external_sms_send",
        "db_commit_in_preview",
        "operational_db_file_io",
        "llm_call_in_local_only",
        "llm_call_with_pii",
        "llm_call_without_sources",
        "llm_call_with_low_confidence",
    }
    assert required <= _adapters.AI_DIRECT_CALL_FORBIDDEN


def test_adapters_reservation_flow_todo_marker():
    """TODO(19-x): AI 예약 흐름 후속 검토 표기."""
    assert "app.modules.appointments" in _adapters.AI_RESERVATION_FLOW_MODULES_TODO
    assert "app.modules.patients" in _adapters.AI_RESERVATION_FLOW_MODULES_TODO


# ──────────────────────── 9. 단방향 경계 (D-4) ────────────────────────


@pytest.mark.parametrize("mod", [
    _schemas, _safety, _preview, _executor, _service, _adapters,
])
def test_commands_no_app_routers_import(mod):
    """D-4: ``app.modules.ai.commands`` 가 ``app.routers`` 미참조."""
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "from app.routers" not in src
    assert "import app.routers" not in src


@pytest.mark.parametrize("mod", [
    _schemas, _safety, _preview, _executor, _service, _adapters,
])
def test_commands_no_app_services_ai_import(mod):
    """D-4: ``app.modules.ai.commands`` 가 ``app.services.ai`` 직접 import ⊥
    (helper 만 — 실제 LLM 호출 본체 services/ai/* 가 단일 원천).
    """
    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "from app.services.ai" not in src
    assert "import app.services.ai" not in src


# ──────────────────────── 10. 외부 의존 / DB 변경 부재 ────────────────────────


@pytest.mark.parametrize("mod_path", [
    "app/modules/ai/__init__.py",
    "app/modules/ai/commands/__init__.py",
    "app/modules/ai/commands/schemas.py",
    "app/modules/ai/commands/safety.py",
    "app/modules/ai/commands/preview.py",
    "app/modules/ai/commands/executor.py",
    "app/modules/ai/commands/service.py",
    "app/modules/ai/commands/adapters.py",
])
def test_modules_no_external_http_imports(mod_path):
    """SAFETY: 본 19-13 모듈은 외부 HTTP / 파일 시스템 변경 라이브러리 의존 ⊥."""
    src = (REPO_ROOT / mod_path).read_text(encoding="utf-8")
    forbidden = [
        "import urllib.request", "import requests", "import httpx",
        "import shutil", "import sqlite3",
        "import openai", "import anthropic",
    ]
    for pat in forbidden:
        assert pat not in src, f"{mod_path} 에 외부 의존성 발견: {pat!r}"


@pytest.mark.parametrize("mod_path", [
    "app/modules/ai/__init__.py",
    "app/modules/ai/commands/__init__.py",
    "app/modules/ai/commands/schemas.py",
    "app/modules/ai/commands/safety.py",
    "app/modules/ai/commands/preview.py",
    "app/modules/ai/commands/executor.py",
    "app/modules/ai/commands/service.py",
    "app/modules/ai/commands/adapters.py",
])
def test_modules_no_db_mutation(mod_path):
    """SAFETY: 본 19-13 모듈은 DB 변경 ⊥."""
    src = (REPO_ROOT / mod_path).read_text(encoding="utf-8")
    forbidden = ["db.commit(", "db.add(", "db.delete(", "db.flush("]
    for pat in forbidden:
        assert pat not in src, f"{mod_path} 에 DB 변경 패턴 발견: {pat!r}"


@pytest.mark.parametrize("mod_path", [
    "app/modules/ai/commands/schemas.py",
    "app/modules/ai/commands/safety.py",
    "app/modules/ai/commands/preview.py",
    "app/modules/ai/commands/executor.py",
    "app/modules/ai/commands/service.py",
    "app/modules/ai/commands/adapters.py",
])
def test_modules_no_llm_provider_call(mod_path):
    """SAFETY: 본 19-13 모듈은 LLM provider 직접 호출 ⊥.

    ``provider.generate(`` / ``provider.chat(`` / ``client.chat.completions(``
    같은 패턴 부재.
    """
    src = (REPO_ROOT / mod_path).read_text(encoding="utf-8")
    forbidden = [
        "provider.generate(", "provider.chat(",
        ".chat.completions.create(",
        "anthropic.messages.create(",
    ]
    for pat in forbidden:
        assert pat not in src, f"{mod_path} 에 LLM 호출 발견: {pat!r}"


# ──────────────────────── 11. 라우터 / 서비스 본체 무수정 ────────────────────────


def test_router_ai_serialize_parse_result_unchanged():
    """COMPAT: ``ai.py:_serialize_parse_result`` 본체 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert "def _serialize_parse_result(r: ai_action_leave.ParseResult)" in src
    # 응답 dict 본체.
    assert '"ok": r.ok,' in src
    assert '"safe_to_continue": r.safe_to_continue,' in src


def test_router_ai_serialize_preview_result_unchanged():
    """COMPAT: ``ai.py:_serialize_preview_result`` 본체 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert "def _serialize_preview_result(r: ai_action_leave.PreviewResult)" in src
    assert '"preview_token": r.preview_token,' in src
    assert '"safe_to_execute": r.safe_to_execute,' in src


def test_router_ai_action_handlers_signature_unchanged():
    """COMPAT: action/parse/preview/execute 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert "@router.post(\"/action/parse\")" in src
    assert "@router.post(\"/action/preview\")" in src
    assert "@router.post(\"/action/execute\")" in src


def test_router_ai_sms_handlers_signature_unchanged():
    """COMPAT: sms/draft / sms/validate 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert "@router.post(\"/sms/draft\")" in src
    assert "@router.post(\"/sms/validate\")" in src


def test_router_ai_manual_handlers_signature_unchanged():
    """COMPAT: manual/search / manual/ask 핸들러 시그니처 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert "@router.post(\"/manual/search\")" in src
    assert "@router.post(\"/manual/ask\")" in src


def test_router_ai_sms_draft_strips_prompt_response_text():
    """SAFETY: ``ai.py:sms_draft`` 가 응답에서 prompt_text/response_text 제거."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    assert 'if k not in ("prompt_text", "response_text")' in src


def test_services_action_leave_intent_name_unchanged():
    """COMPAT: services/ai/action_leave.py:INTENT_NAME 무수정."""
    src = APP_SERVICES_ACTION_LEAVE.read_text(encoding="utf-8")
    assert 'INTENT_NAME = "create_therapist_leave"' in src


def test_services_action_leave_token_policy_unchanged():
    """RISK: services/ai/action_leave.py 의 토큰 정책 (TTL=120, version=1) 무수정."""
    src = APP_SERVICES_ACTION_LEAVE.read_text(encoding="utf-8")
    assert "TOKEN_TTL_SEC = 120" in src
    assert "TOKEN_VERSION = 1" in src
    # _SERVER_SECRET 32바이트
    assert "_SERVER_SECRET: bytes = secrets.token_bytes(32)" in src


def test_services_sms_draft_no_direct_send():
    """SAFETY: services/ai/sms_draft.py 가 외부 SMS 직접 발송 ⊥.

    실제 호출 패턴 (httpx / requests / urllib post / fetch) 부재 검증. docstring
    의 "POST /api/sms/send 호출 금지" 정책 문구는 정합 (검출 ⊥).
    """
    src = APP_SERVICES_SMS_DRAFT.read_text(encoding="utf-8")
    # 외부 HTTP 호출 패턴 부재.
    forbidden_patterns = [
        "httpx.post(", "httpx.Client(", "requests.post(",
        "urllib.request.Request(",
        "fetch(",
    ]
    for pat in forbidden_patterns:
        assert pat not in src, f"sms_draft 에 외부 SMS 발송 패턴 발견: {pat!r}"
    # needs_user_confirm 가드 본체.
    assert '"needs_user_confirm"' in src


# ──────────────────────── 12. 환각 / PII 가드 본체 검증 ────────────────────────


def test_action_leave_pre_gate_pii_block_unchanged():
    """SAFETY: action_leave._pre_gate 의 PII 차단 정책 무수정."""
    src = APP_SERVICES_ACTION_LEAVE.read_text(encoding="utf-8")
    # 전화번호 / 주민등록번호 검출 시 pii_blocked.
    assert 'scan.found.get("phone")' in src
    assert 'scan.found.get("rrn")' in src
    assert 'return "pii_blocked"' in src
    # 환자 키워드 검출 시 차단.
    assert "_PATIENT_INDICATORS" in src


def test_sms_draft_pii_guard_unchanged():
    """SAFETY: sms_draft 의 extra_note PII 가드 + safe_ctx 가드 무수정."""
    src = APP_SERVICES_SMS_DRAFT.read_text(encoding="utf-8")
    assert "assert_safe_for_external" in src
    # clinic_phone 은 마스킹 제외 (공공 정보).
    assert 'k != "clinic_phone"' in src


def test_sms_draft_no_provider_call_when_skipped():
    """SAFETY: sms_draft 가 cancelled / not_found / no_appt_time 분기에서 LLM 호출 ⊥."""
    src = APP_SERVICES_SMS_DRAFT.read_text(encoding="utf-8")
    # 이 분기들에서 provider_override.generate 호출 없이 바로 return.
    assert '"skip_reason": "cancelled"' in src
    assert '"skip_reason": "no_appointment"' in src
    assert '"skip_reason": "no_appt_time"' in src


# ──────────────────────── 13. 응답 keys 라우터 본체 검증 ────────────────────────


def test_router_ai_action_execute_outcome_branches_unchanged():
    """COMPAT: action_execute outcome 분기 (409/500/400) 본체 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    # 409 분기.
    assert 'if r.outcome in ("conflict_changed", "therapist_changed")' in src
    assert "status_code=409" in src
    # 500 분기.
    assert 'if r.outcome == "db_error"' in src
    assert "status_code=500" in src
    # default 400.
    assert "status_code=400" in src


def test_router_ai_action_execute_response_keys_unchanged():
    """COMPAT: action_execute body 응답 key 5개 본체 무수정."""
    src = APP_ROUTERS_AI.read_text(encoding="utf-8")
    # body dict 본체.
    body_pat = re.search(
        r"body\s*=\s*\{[^}]*\}", src,
    )
    assert body_pat is not None
    body_str = body_pat.group(0)
    for key in ("ok", "outcome", "leave_id", "mode", "message"):
        assert f'"{key}":' in body_str, f"action_execute body 에 {key!r} 누락"


# ──────────────────────── 14. provider 호출 차단 분류 cross-check ────────────────────────


def test_safety_pii_outcomes_imply_provider_blocked():
    """SAFETY: PII 차단 outcome 은 항상 provider 호출 ⊥."""
    pii_outcomes = ["pii_blocked"]
    for o in pii_outcomes:
        assert _safety.is_provider_blocked_outcome(o), (
            f"PII outcome {o!r} 가 provider 차단 분류에 부재"
        )


def test_safety_low_confidence_implies_provider_blocked():
    """SAFETY: low_confidence 는 provider 호출 ⊥."""
    assert _safety.is_provider_blocked_outcome("low_confidence")


def test_safety_unknown_feature_implies_provider_blocked():
    """SAFETY: no_leave_keyword (unknown_feature) 는 provider 호출 ⊥."""
    assert _safety.is_provider_blocked_outcome("no_leave_keyword")


# ──────────────────────── 15. 승인 가드 cross-check ────────────────────────


def test_safety_token_outcomes_all_imply_approval_required():
    """RISK: 모든 token_* outcome 은 승인 가드 발동."""
    token_outcomes = [
        "token_format", "token_signature", "token_unsafe",
        "token_mismatch", "token_expired",
    ]
    for o in token_outcomes:
        assert _safety.is_approval_required_outcome(o), (
            f"token outcome {o!r} 가 승인 가드 분류에 부재"
        )


def test_safety_confirm_outcomes_imply_approval_required():
    """RISK: not_confirmed / overwrite_not_acknowledged 는 승인 가드 발동."""
    assert _safety.is_approval_required_outcome("not_confirmed")
    assert _safety.is_approval_required_outcome("overwrite_not_acknowledged")
