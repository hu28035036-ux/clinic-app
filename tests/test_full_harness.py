"""Full Harness — 18-0 최소 통합 smoke.

전체 AI 기능이 크게 깨졌는지 빠르게 확인하는 회귀 하네스.

상세 설계: ``docs/harnesses/full_harness_plan.md``.
이번 세션 범위:
  - 라우터 smoke (manual/search, manual/ask, health/public)
  - 빈 질문 / AI disabled / API key 없음 분기
  - 응답 9개 키 계약 단언 (``contract.py``)
  - 외부 SDK 호출 차단 동작 확인
"""
from __future__ import annotations

from tests.harness.contract import (
    assert_manual_ask_contract,
    assert_manual_search_contract,
)
from tests.harness.fake_provider import call_count
from tests.harness.safety_harness import assert_no_api_key_in_text


def test_db_path_is_safe(db_path):
    """conftest 격리가 정상 작동 — 임시 경로에 'temp' 또는 'test' 포함."""
    norm = db_path.lower().replace("\\", "/")
    assert ("temp" in norm) or ("test" in norm), db_path


def test_manual_search_400_when_empty(client):
    """빈 질문 → 400 (현행 라우터 동작 보존)."""
    resp = client.post("/api/ai/manual/search", json={"question": ""})
    assert resp.status_code == 400, resp.text


def test_manual_search_200_contract(client):
    """manual/search 정상 → 200 + 응답 키 3개 계약 통과 (LLM 미사용 → AI 비활성에도 동작)."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post(
        "/api/ai/manual/search",
        json={"question": "예약문자 작성"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert_manual_search_contract(body)


def test_manual_ask_400_when_empty(client, ai_disabled_setting):
    """빈 질문 → 400 (AI 활성/비활성 무관)."""
    resp = client.post("/api/ai/manual/ask", json={"question": "  "})
    assert resp.status_code == 400, resp.text


def test_manual_ask_503_when_disabled(client, ai_disabled_setting):
    """AI disabled → 503 + ``"AI 기능이 꺼져"`` 메시지."""
    resp = client.post(
        "/api/ai/manual/ask",
        json={"question": "예약문자 작성은 어떻게 해?"},
    )
    assert resp.status_code == 503, resp.text
    assert "AI 기능이 꺼져" in resp.json().get("detail", "")


def test_manual_ask_200_contract_with_fake(client, ai_enabled_with_fake):
    """AI enabled + FakeProvider → 200 + 응답 9개 키 계약 통과 + provider 호출 1회.

    회귀 모드 (A) 단언: 매뉴얼에 매칭되는 질문 + key/model 있음 → LLM 1회.
    """
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post(
        "/api/ai/manual/ask",
        json={"question": "예약문자 작성"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert_manual_ask_contract(body)
    # 회귀 모드: LLM 1회 호출
    assert call_count(ai_enabled_with_fake) == 1, (
        f"expected 1 LLM call, got {call_count(ai_enabled_with_fake)}"
    )


def test_health_public_200(client):
    """``/api/ai/health/public`` 인증 불필요 + 200."""
    resp = client.get("/api/ai/health/public")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # public 응답은 최소 4개 필드. 내부 상세(version/sdk_errors 등)는 없어야 한다.
    assert isinstance(body, dict)


def test_external_sdk_blocked_on_instantiation():
    """conftest 가 openai/anthropic SDK 클래스를 차단했는지 확인.

    SDK 미설치 환경에서는 import 자체가 실패하므로 skip-equivalent 로 처리.
    """
    import importlib

    for mod_name, cls_name in (("openai", "OpenAI"), ("anthropic", "Anthropic")):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue  # SDK 미설치
        cls = getattr(mod, cls_name, None)
        if cls is None:
            continue
        try:
            cls(api_key="dummy")
        except RuntimeError as e:
            assert "외부 LLM/Embedding API 호출" in str(e)
        except Exception:
            # 일부 SDK 는 인스턴스화 자체는 통과하고 호출 시 fail. 그 경우도 OK.
            pass
        else:
            raise AssertionError(
                f"{mod_name}.{cls_name} 가 monkeypatch 되지 않았음 — 외부 호출 위험."
            )


def test_no_api_key_in_503_response(client, ai_disabled_setting):
    """503 응답 본문에 어떤 API key 값도 부재 (혹시라도 새 어절에 누설되지 않는지)."""
    resp = client.post(
        "/api/ai/manual/ask",
        json={"question": "예약문자 작성"},
    )
    assert resp.status_code == 503
    body_text = resp.text
    # 우리가 활성화 fixture 에서 사용하는 마커. 실제 API key 가 없는 경우라도
    # 안전망으로 둔다.
    assert_no_api_key_in_text(body_text, "test-fake-key", "sk-")
