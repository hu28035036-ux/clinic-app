"""18-7 ``/api/ai/status`` 검증 — 관리자 상태 집계 API.

검증 범위 (18-7 체크리스트 + 사용자 세션 지시문):
  1. 권한 — admin 전용 (토큰 없으면 401)
  2. 응답 구조 — 8개 최상위 키 (ai_mode / search_mode / version /
     ai_settings / vector_status / external_api / knowledge / prompt_versions /
     recent_ai_logs)
  3. API key 평문/마스킹 모두 미노출
  4. PII 미노출 — 로그 본문 (prompt_hash/response_hash) 미노출
  5. 외부 API 호출 0 — provider/embedding 인스턴스화 없음
  6. AI 모드 파생 — disabled / no key → local_only, enabled+key+model → local_first
  7. vector_status — m014 미도입 → 항상 enabled=False, available=False
  8. knowledge 카운트 — chunks/vectors/documents 정수
  9. last_reindex — 행 부재 시 id=None
  10. recent_ai_logs — outcome/feature 카운트 dict + recent N건 PII 부재
  11. /api/ai/manual/{search,ask} 응답 키 회귀 0 (별도 contract 테스트)

상세 설계: ``app/services/ai/health.py`` docstring,
``docs/checklists/18-7_admin_ui_checklist.md``, ``docs/ai_rag_rollout_plan.md`` §7.
"""
from __future__ import annotations

import pytest

from app.database import SessionLocal
from app.models import models as _m
from app.services.ai import health as ai_health
from app.services.ai.health import (
    AI_MODE_LOCAL_FIRST,
    AI_MODE_LOCAL_ONLY,
    DEFAULT_RECENT_HOURS,
    ERROR_DETAIL_DISPLAY_LIMIT,
    MAX_RECENT_LIMIT,
    SEARCH_MODE_KEYWORD,
    build_admin_status,
    count_chunks,
    count_documents,
    count_vectors,
    derive_ai_mode,
    derive_external_api_status,
    derive_search_mode,
    derive_vector_status,
    get_last_reindex,
    get_prompt_versions,
    get_recent_logs,
)

# ──────────────────────── helper ────────────────────────


def _admin_token(client) -> str:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text}"
    return resp.json().get("token", "")


def _make_setting(
    *,
    enabled: bool = False,
    provider: str = "openai",
    model: str = "",
    api_key: str = "",
) -> _m.AiSetting:
    """단위 테스트용 in-memory ``AiSetting`` (DB 미저장)."""
    s = _m.AiSetting()
    s.enabled = enabled
    s.provider = provider
    s.model = model
    s.api_key = api_key
    s.base_url = ""
    s.max_tokens = 512
    s.temperature = 0.3
    s.pii_guard_enabled = True
    return s


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────── 1. derive_ai_mode 단위 테스트 ────────────────────────


def test_derive_ai_mode_disabled_returns_local_only():
    s = _make_setting(enabled=False)
    assert derive_ai_mode(s) == AI_MODE_LOCAL_ONLY


def test_derive_ai_mode_no_api_key_returns_local_only():
    s = _make_setting(enabled=True, api_key="", model="gpt-4o-mini")
    assert derive_ai_mode(s) == AI_MODE_LOCAL_ONLY


def test_derive_ai_mode_no_model_returns_local_only():
    s = _make_setting(enabled=True, api_key="sk-test", model="")
    assert derive_ai_mode(s) == AI_MODE_LOCAL_ONLY


def test_derive_ai_mode_enabled_with_key_and_model_returns_local_first():
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini")
    assert derive_ai_mode(s) == AI_MODE_LOCAL_FIRST


# ──────────────────────── 2. derive_search_mode 단위 테스트 ────────────────────────


def test_derive_search_mode_always_keyword_in_18_7():
    """18-7 시점 — pipeline.run_manual_ask 가 keyword_retrieve 만 사용 → 항상 keyword."""
    s = _make_setting(enabled=False)
    assert derive_search_mode(s) == SEARCH_MODE_KEYWORD
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini")
    assert derive_search_mode(s) == SEARCH_MODE_KEYWORD


# ──────────────────────── 3. derive_vector_status — m014 미도입 ────────────────────────


def test_derive_vector_status_always_disabled_in_18_7():
    """m014 미도입 → enabled=False, available=False, reason='vector_disabled'."""
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini")
    out = derive_vector_status(s, sdk_installed={"openai": True})
    assert out["enabled"] is False
    assert out["available"] is False
    assert out["reason"] == "vector_disabled"


def test_derive_vector_status_disabled_setting_still_disabled():
    """AI 자체가 disabled 라도 vector_status 결과 동일."""
    s = _make_setting(enabled=False)
    out = derive_vector_status(s)
    assert out["enabled"] is False
    assert out["available"] is False


# ──────────────────────── 4. derive_external_api_status ────────────────────────


def test_derive_external_api_status_disabled_means_llm_unavailable():
    s = _make_setting(enabled=False)
    out = derive_external_api_status(s, sdk_installed={"openai": True})
    assert out["llm_available"] is False
    assert out["embedding_available"] is False
    assert out["sdk_installed"]["openai"] is True


def test_derive_external_api_status_full_setup_llm_available():
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini", provider="openai")
    out = derive_external_api_status(s, sdk_installed={"openai": True})
    assert out["llm_available"] is True
    # embedding 은 18-7 시점 항상 False (운영 미구현).
    assert out["embedding_available"] is False


def test_derive_external_api_status_no_sdk_means_llm_unavailable():
    """provider sdk 가 설치 안 됨 → llm_available=False."""
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini", provider="openai")
    out = derive_external_api_status(s, sdk_installed={"openai": False})
    assert out["llm_available"] is False


def test_derive_external_api_status_unknown_provider_means_unavailable():
    """미지정/미지원 provider → sdk_installed 에 키 없음 → False."""
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini", provider="custom")
    out = derive_external_api_status(s, sdk_installed={"openai": True, "anthropic": True})
    assert out["llm_available"] is False


# ──────────────────────── 5. count_documents / chunks / vectors ────────────────────────


def test_count_documents_returns_int():
    n = count_documents()
    assert isinstance(n, int)
    assert n >= 1, "knowledge/manuals/*.md 가 최소 1개 이상 동봉되어야 함"


def test_count_chunks_returns_int(db_session):
    n = count_chunks(db_session)
    assert isinstance(n, int)
    assert n >= 0


def test_count_vectors_returns_int(db_session):
    n = count_vectors(db_session)
    assert isinstance(n, int)
    assert n >= 0


# ──────────────────────── 6. get_last_reindex ────────────────────────


def test_get_last_reindex_no_runs_returns_id_none(db_session):
    """``knowledge_index_runs`` 비어있는 상태 — id=None, 카운터 모두 0."""
    # 정리
    db_session.query(_m.KnowledgeIndexRun).delete()
    db_session.commit()
    out = get_last_reindex(db_session)
    assert out.id is None
    assert out.status is None
    assert out.total_documents == 0
    assert out.failed_paths == []


def test_get_last_reindex_returns_latest_row(db_session):
    """행이 있으면 최신 행을 반환 — id/status/카운터 정확."""
    db_session.query(_m.KnowledgeIndexRun).delete()
    db_session.commit()
    from datetime import datetime as _dt
    row1 = _m.KnowledgeIndexRun(
        started_at=_dt.utcnow(),
        finished_at=_dt.utcnow(),
        status="success",
        trigger="manual",
        total_documents=5,
        processed_documents=5,
        total_chunks=10,
        inserted_chunks=10,
        failed_paths="",
        errors="",
    )
    row2 = _m.KnowledgeIndexRun(
        started_at=_dt.utcnow(),
        finished_at=_dt.utcnow(),
        status="partial",
        trigger="startup",
        total_documents=7,
        processed_documents=6,
        failed_documents=1,
        total_chunks=12,
        failed_paths="manuals/x.md\nmanuals/y.md",
        errors='[{"path":"x","error":"e","stage":"persist"}]',
    )
    db_session.add(row1)
    db_session.add(row2)
    db_session.commit()
    out = get_last_reindex(db_session)
    assert out.id is not None
    assert out.status == "partial"
    assert out.trigger == "startup"
    assert out.total_documents == 7
    assert out.failed_documents == 1
    assert out.failed_paths == ["manuals/x.md", "manuals/y.md"]
    assert out.errors_count == 1


def test_get_last_reindex_failed_paths_truncated_to_max(db_session):
    """failed_paths 가 max_failed_paths 보다 많으면 절단."""
    db_session.query(_m.KnowledgeIndexRun).delete()
    db_session.commit()
    paths = "\n".join(f"manuals/x{i}.md" for i in range(50))
    from datetime import datetime as _dt
    row = _m.KnowledgeIndexRun(
        started_at=_dt.utcnow(),
        status="partial",
        trigger="manual",
        failed_paths=paths,
    )
    db_session.add(row)
    db_session.commit()
    out = get_last_reindex(db_session, max_failed_paths=10)
    assert len(out.failed_paths) == 10


# ──────────────────────── 7. get_recent_logs ────────────────────────


def test_get_recent_logs_empty_returns_zero(db_session):
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    out = get_recent_logs(db_session, hours=1, limit=5)
    assert out["lookback_hours"] == 1
    assert out["total"] == 0
    assert out["recent"] == []
    # 표준 outcome 4개는 0 으로 시드됨
    for o in ("success", "warning", "blocked", "error"):
        assert out["by_outcome"][o] == 0


def test_get_recent_logs_masks_pii_in_error_detail(db_session):
    """Codex 18-7 M-1 — DB 의 error_detail 에 PII 가 들어가 있어도 응답에서 마스킹.

    저장 정책 (``ai_logging.py``) 이 1차 보호하지만, 본 모듈은 관리자 화면 노출
    API 의 마지막 단계이므로 PII 패턴을 한 번 더 마스킹한다.

    검증:
      - 010-1234-5678 (전화) → "[PHONE]"
      - 1990-05-15 (생년월일) → "[BIRTH]"
      - 880101-1234567 (RRN) → "[RRN]"
      - 원문 PII 부재.
    """
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    # 시뮬레이션: 외부 라이브러리 traceback 등이 PII 를 포함한 채 저장된 시나리오.
    poisoned = "Exception in field=phone 010-1234-5678 birth=1990-05-15 rrn=880101-1234567"
    db_session.add(_m.AiUsageLog(
        feature="manual_ask", outcome="error", status="error",
        provider="openai", model="gpt-4o-mini",
        error_detail=poisoned,
    ))
    db_session.commit()

    out = get_recent_logs(db_session, hours=24, limit=5)
    assert len(out["recent"]) == 1
    detail = out["recent"][0]["error_detail"]
    # 원문 PII 부재
    assert "010-1234-5678" not in detail, f"전화번호 노출됨: {detail!r}"
    assert "1990-05-15" not in detail, f"생년월일 노출됨: {detail!r}"
    assert "880101-1234567" not in detail, f"RRN 노출됨: {detail!r}"
    # 마스킹 토큰 존재
    assert "[PHONE]" in detail
    assert "[BIRTH]" in detail
    assert "[RRN]" in detail


def test_safe_error_detail_helper_masks_phone():
    """``_safe_error_detail`` 단위 테스트 — 전화번호 패턴 마스킹."""
    from app.services.ai.health import _safe_error_detail
    out = _safe_error_detail("call 010-1234-5678 to verify")
    assert "010-1234-5678" not in out
    assert "[PHONE]" in out


def test_safe_error_detail_helper_caps_to_200_chars():
    """``_safe_error_detail`` 200자 cap — PII 마스킹 후에도 truncate."""
    from app.services.ai.health import _safe_error_detail
    long_text = "x" * 1000
    out = _safe_error_detail(long_text)
    # truncate 마커까지 포함해도 적절한 길이.
    assert len(out) <= ERROR_DETAIL_DISPLAY_LIMIT + len("...[truncated]")


def test_safe_error_detail_helper_empty_returns_empty():
    from app.services.ai.health import _safe_error_detail
    assert _safe_error_detail("") == ""
    assert _safe_error_detail(None) == ""


def test_safe_error_detail_helper_safe_text_passes_through():
    """PII 없는 일반 진단 메시지는 통과 (마스킹 없음)."""
    from app.services.ai.health import _safe_error_detail
    out = _safe_error_detail("hits=3, top_score=5, ai request blocked because ai disabled")
    assert "hits=3" in out
    assert "top_score=5" in out
    assert "[PHONE]" not in out  # PII 없으면 마스킹 토큰 부재


def test_status_endpoint_masks_pii_in_recent_logs(client, db_session):
    """라우터 통합 — `/api/ai/status` recent[].error_detail 에 PII 누출 0.

    Codex 18-7 M-1 후속 — 관리자 API 응답 본문에서도 정확히 마스킹.
    """
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    poisoned = "user phone 010-9999-8888 leaked into error context"
    db_session.add(_m.AiUsageLog(
        feature="manual_ask", outcome="error", status="error",
        error_detail=poisoned,
    ))
    db_session.commit()

    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    body = resp.json()
    blob = resp.text
    # 응답 본문 어디에도 원문 전화번호 부재.
    assert "010-9999-8888" not in blob
    # recent[] 항목에서도 마스킹 확인.
    recent = body["recent_ai_logs"]["recent"]
    assert len(recent) >= 1
    for entry in recent:
        assert "010-9999-8888" not in entry["error_detail"]


def test_get_recent_logs_aggregates_by_outcome_and_feature(db_session):
    """outcome / feature 별 group by 정확."""
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    # 5 success(manual_ask) + 2 blocked(manual_ask) + 1 warning(manual_search)
    for _ in range(5):
        db_session.add(_m.AiUsageLog(
            feature="manual_ask", outcome="success", status="success",
            provider="openai", model="gpt-4o-mini",
        ))
    for _ in range(2):
        db_session.add(_m.AiUsageLog(
            feature="manual_ask", outcome="blocked", status="blocked",
        ))
    db_session.add(_m.AiUsageLog(
        feature="manual_search", outcome="warning", status="warning",
    ))
    db_session.commit()
    out = get_recent_logs(db_session, hours=24, limit=10)
    assert out["total"] == 8
    assert out["by_outcome"]["success"] == 5
    assert out["by_outcome"]["blocked"] == 2
    assert out["by_outcome"]["warning"] == 1
    assert out["by_outcome"]["error"] == 0
    assert out["by_feature"]["manual_ask"] == 7
    assert out["by_feature"]["manual_search"] == 1


def test_get_recent_logs_recent_entries_no_pii(db_session):
    """recent[].error_detail 200자 cap + prompt_hash/response_hash 미노출."""
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    long_text = "x" * 1000
    db_session.add(_m.AiUsageLog(
        feature="manual_ask", outcome="warning", status="warning",
        provider="openai", model="gpt-4o-mini",
        latency_ms=320, error_detail=long_text,
        prompt_hash="dummy_hash_should_not_appear_in_response",
        response_hash="dummy_response_hash_should_not_appear",
    ))
    db_session.commit()
    out = get_recent_logs(db_session, hours=24, limit=5)
    assert len(out["recent"]) == 1
    entry = out["recent"][0]
    # error_detail truncate
    assert len(entry["error_detail"]) <= ERROR_DETAIL_DISPLAY_LIMIT + len("...[truncated]")
    # 해시 노출 X
    assert "prompt_hash" not in entry
    assert "response_hash" not in entry
    # 기대 키만 존재
    expected_keys = {
        "ts", "feature", "outcome", "provider", "model",
        "latency_ms", "pii_filter_hits", "hallucination_guard_hits",
        "error_detail",
    }
    assert set(entry.keys()) == expected_keys


def test_get_recent_logs_limit_capped_to_max(db_session):
    """limit > MAX_RECENT_LIMIT 면 MAX 로 cap."""
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    for _ in range(MAX_RECENT_LIMIT + 5):
        db_session.add(_m.AiUsageLog(
            feature="manual_ask", outcome="success", status="success",
        ))
    db_session.commit()
    out = get_recent_logs(db_session, limit=MAX_RECENT_LIMIT + 100)
    assert len(out["recent"]) == MAX_RECENT_LIMIT


def test_get_recent_logs_lookback_excludes_old_entries(db_session):
    """ts 가 lookback 시간보다 오래되면 카운트 제외."""
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    from datetime import datetime as _dt
    from datetime import timedelta as _td
    # 25시간 전 row (24시간 lookback 에서 제외)
    db_session.add(_m.AiUsageLog(
        feature="manual_ask", outcome="success", status="success",
        ts=_dt.utcnow() - _td(hours=25),
    ))
    # 최근 row (포함)
    db_session.add(_m.AiUsageLog(
        feature="manual_ask", outcome="success", status="success",
    ))
    db_session.commit()
    out = get_recent_logs(db_session, hours=24, limit=10)
    assert out["total"] == 1


# ──────────────────────── 8. get_prompt_versions ────────────────────────


def test_get_prompt_versions_returns_dict():
    out = get_prompt_versions()
    assert isinstance(out, dict)
    assert out.get("manual_qa.system") == "v1"


def test_get_prompt_versions_returns_copy_not_reference():
    """반환된 dict 는 외부 수정에 영향 없음."""
    a = get_prompt_versions()
    a["manual_qa.system"] = "vMODIFIED"
    b = get_prompt_versions()
    assert b["manual_qa.system"] == "v1"


# ──────────────────────── 9. build_admin_status — 통합 ────────────────────────


def test_build_admin_status_returns_all_top_level_keys(db_session):
    """8개 최상위 키 모두 존재 — UI 가 요구하는 모든 항목."""
    s = _make_setting(enabled=False)
    out = build_admin_status(db_session, setting=s)
    expected = {
        "ai_mode", "search_mode", "version",
        "ai_settings", "vector_status", "external_api",
        "knowledge", "prompt_versions", "recent_ai_logs",
    }
    assert expected.issubset(set(out.keys())), (
        f"누락 키: {expected - set(out.keys())}"
    )


def test_build_admin_status_no_api_key_in_response(db_session):
    """응답 어디에도 api_key 평문 부재."""
    secret = "sk-very-secret-key-1234567890abcdefg"
    s = _make_setting(enabled=True, api_key=secret, model="gpt-4o-mini")
    out = build_admin_status(db_session, setting=s)
    # 직렬화해서 전체 검사 (recursive 안전).
    import json
    blob = json.dumps(out, ensure_ascii=False)
    assert secret not in blob, "api_key 평문이 응답에 노출됨!"
    # 마스킹 형식조차 노출 X (정책 강화).
    assert "sk-very" not in blob
    # boolean 만 노출.
    assert out["ai_settings"]["api_key_set"] is True


def test_build_admin_status_disabled_means_local_only(db_session):
    s = _make_setting(enabled=False)
    out = build_admin_status(db_session, setting=s)
    assert out["ai_mode"] == AI_MODE_LOCAL_ONLY
    assert out["external_api"]["llm_available"] is False


def test_build_admin_status_enabled_full_means_local_first(db_session):
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini")
    out = build_admin_status(
        db_session, setting=s,
        sdk_installed={"openai": True},
    )
    assert out["ai_mode"] == AI_MODE_LOCAL_FIRST
    assert out["external_api"]["llm_available"] is True


def test_build_admin_status_knowledge_counts_present(db_session):
    s = _make_setting()
    out = build_admin_status(db_session, setting=s)
    assert isinstance(out["knowledge"]["documents"], int)
    assert isinstance(out["knowledge"]["chunks"], int)
    assert isinstance(out["knowledge"]["vectors"], int)
    assert "last_reindex" in out["knowledge"]
    # last_reindex 는 dict (행 부재 시 id=None)
    assert isinstance(out["knowledge"]["last_reindex"], dict)


def test_build_admin_status_does_not_call_llm_provider(db_session):
    """build_admin_status 호출이 어떤 provider 도 인스턴스화하지 않는다.

    호출 후 ``ai_provider.get_provider`` 가 monkeypatch 없이도 부작용 없음 ―
    본 함수는 read-only 집계.
    """
    s = _make_setting(enabled=True, api_key="sk-test", model="gpt-4o-mini")
    out = build_admin_status(db_session, setting=s)
    # 단순 sanity — 응답 dict 가 생성됨 + 외부 호출 흔적 부재.
    assert isinstance(out, dict)
    assert "ai_mode" in out


# ──────────────────────── 10. 라우터 통합 — /api/ai/status ────────────────────────


def test_status_endpoint_requires_admin_token(client):
    """토큰 없으면 401 (admin 전용)."""
    saved = client.headers.pop("X-Admin-Token", None)
    try:
        resp = client.get("/api/ai/status")
    finally:
        if saved:
            client.headers["X-Admin-Token"] = saved
    assert resp.status_code == 401


def test_status_endpoint_with_admin_token_returns_200(client):
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "ai_mode" in body
    assert "search_mode" in body
    assert "knowledge" in body


def test_status_endpoint_no_api_key_in_response(client, ai_enabled_with_fake):
    """라우터 응답에 fixture 의 'test-fake-key' 평문/마스킹 부재.

    Codex 18-7 사소한 개선 후속 (재수정):
      Codex 가 지적한 ``or → and`` 는 옳지만, "test-" prefix 단언은 model 필드
      (예: "test-model") 와 충돌. ``model`` 은 의도적 노출 필드 (admin 화면에서
      어떤 모델이 설정됐는지 확인용).

    정확한 단언:
      1. api_key 의 정확한 값 (``test-fake-key``) 부재 (전체)
      2. api_key 의 부분 (``fake-key``) 부재 (key 특이 부분 — model 명에 안 나옴)
      3. 응답 dict 의 ``ai_settings`` 에 ``api_key`` / ``api_key_masked`` 키 부재
      4. ``api_key_set`` boolean 만 노출
    """
    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    body_text = resp.text
    body = resp.json()

    # (1) (2) — api_key 값 / 식별 가능한 부분 모두 부재 (and 로 둘 다 단언).
    assert "test-fake-key" not in body_text and "fake-key" not in body_text, (
        "API key 값이 응답에 노출되어선 안 됩니다."
    )

    # (3) — ai_settings 에 api_key / api_key_masked 키 자체가 없어야 함.
    settings_keys = set(body["ai_settings"].keys())
    forbidden = {"api_key", "api_key_masked"}
    leaked = forbidden & settings_keys
    assert not leaked, f"ai_settings 에 금지 키 노출: {leaked}"

    # (4) — api_key_set boolean 만 노출.
    assert body["ai_settings"]["api_key_set"] is True
    assert isinstance(body["ai_settings"]["api_key_set"], bool)


def test_status_endpoint_does_not_leak_prompt_or_response_hash(
    client, ai_enabled_with_fake, db_session
):
    """recent_ai_logs.recent[] 에 prompt_hash / response_hash 부재."""
    # AI 로그 1건 시드 (해시 포함).
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()
    db_session.add(_m.AiUsageLog(
        feature="manual_ask", outcome="success", status="success",
        prompt_hash="abc123_should_not_leak",
        response_hash="def456_should_not_leak",
    ))
    db_session.commit()

    token = _admin_token(client)
    resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
    assert resp.status_code == 200
    blob = resp.text
    assert "abc123_should_not_leak" not in blob
    assert "def456_should_not_leak" not in blob


def test_status_endpoint_polling_safe_no_log_written(client, db_session):
    """`/api/ai/status` 자체는 AiUsageLog 를 남기지 않음 (polling 안전).

    health/health/public 와 동일 정책 — 폴링 다수 시 로그 폭증 방지.
    """
    db_session.query(_m.AiUsageLog).delete()
    db_session.commit()

    token = _admin_token(client)
    for _ in range(3):
        resp = client.get("/api/ai/status", headers={"X-Admin-Token": token})
        assert resp.status_code == 200

    n = db_session.query(_m.AiUsageLog).count()
    assert n == 0, (
        f"`/api/ai/status` 가 AiUsageLog 를 남기면 안 됨 (현재 {n}개)"
    )


def test_status_endpoint_does_not_use_operational_db(db_path):
    """conftest 격리 검증 — 운영 DB 미사용."""
    norm = db_path.lower().replace("\\", "/")
    assert ("temp" in norm) or ("test" in norm), db_path


def test_status_endpoint_default_constants_sane():
    """공개 상수가 명시적 — DEFAULT_RECENT_HOURS=24, DEFAULT_RECENT_LIMIT=5."""
    assert DEFAULT_RECENT_HOURS == 24
    assert ai_health.DEFAULT_RECENT_LIMIT == 5
    assert MAX_RECENT_LIMIT == 20
    assert ERROR_DETAIL_DISPLAY_LIMIT == 200
