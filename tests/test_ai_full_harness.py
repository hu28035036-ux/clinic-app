"""18-1/18-2 Full Harness — 신규 골격 도입 후 통합 회귀 검증.

18-0 의 ``tests/test_full_harness.py`` 와는 별개. 신규 ``rag/``, ``knowledge/``
패키지가 import 된 상태에서도 라우터 smoke / 응답 9+3 키 계약 / SDK 호출 차단이
그대로 통과해야 한다. (vector/ 패키지는 18-5 chunk + vector 도입 시점에 추가)

상세: ``docs/checklists/18-1_structure_refactor_checklist.md`` §6, §8.
"""
from __future__ import annotations

from tests.harness.contract import (
    assert_manual_ask_contract,
    assert_manual_search_contract,
)
from tests.harness.fake_provider import call_count


def test_rag_package_importable():
    """신규 ``app.services.ai.rag`` 패키지가 import 가능."""
    import app.services.ai.rag as _rag  # noqa: F401
    import app.services.ai.rag.pipeline as _pl  # noqa: F401
    import app.services.ai.rag.prompts as _pr  # noqa: F401
    import app.services.ai.rag.retriever as _ret  # noqa: F401
    import app.services.ai.rag.safety as _saf  # noqa: F401
    import app.services.ai.rag.schemas as _sch  # noqa: F401


def test_knowledge_package_importable():
    """신규 ``app.services.ai.knowledge`` 패키지가 import 가능."""
    import app.services.ai.knowledge as _kn  # noqa: F401
    import app.services.ai.knowledge.keyword_index as _ki  # noqa: F401
    import app.services.ai.knowledge.loader as _ld  # noqa: F401
    import app.services.ai.knowledge.normalizer as _nm  # noqa: F401


def test_existing_manual_qa_still_importable():
    """기존 import 경로(``app.services.ai.manual_qa``) 깨지지 않음."""
    from app.services.ai import manual_qa as ai_manual_qa
    # ``ask_manual_question`` 시그니처 보존
    assert callable(ai_manual_qa.ask_manual_question)
    assert callable(ai_manual_qa.manual_search)
    assert ai_manual_qa.LOW_SCORE_THRESHOLD == 2


def test_existing_rag_search_still_importable():
    """기존 ``app.services.rag.search`` 가 그대로 동작.

    ``app/services/rag/__init__.py`` 가 ``from .search import search`` 로
    함수를 직접 export 하므로 ``app.services.rag.search`` 의 attribute access
    는 함수를 반환한다 (Python import 메커니즘 — 패키지 namespace 의 동명
    이름이 우선). 모듈 객체는 ``sys.modules`` 또는 ``importlib`` 으로 명시
    획득 가능.
    """
    import importlib
    import sys

    # 함수 export 확인
    from app.services.rag import search as rag_search_func
    assert callable(rag_search_func)

    # 실제 모듈 객체 확인 — importlib 으로 명시 로드
    rag_search_module = importlib.import_module("app.services.rag.search")
    assert sys.modules["app.services.rag.search"] is rag_search_module
    assert callable(rag_search_module.search)
    assert callable(rag_search_module.reset_cache)


def test_router_manual_search_smoke_unchanged(client):
    """라우터 ``/api/ai/manual/search`` 응답 3개 키 계약 회귀 0."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/search", json={"question": "예약문자 작성"})
    assert resp.status_code == 200, resp.text
    assert_manual_search_contract(resp.json())


def test_router_manual_ask_disabled_unchanged(client, ai_disabled_setting):
    """AI disabled → 503 + ``"AI 기능이 꺼져"`` 메시지 (회귀 0)."""
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    assert resp.status_code == 503
    assert "AI 기능이 꺼져" in resp.json().get("detail", "")


def test_router_manual_ask_with_fake_unchanged(client, ai_enabled_with_fake):
    """라우터 ``/api/ai/manual/ask`` 응답 9개 키 계약 + 회귀 모드 (A) LLM 1회."""
    from app.services.rag.search import reset_cache

    reset_cache()
    resp = client.post("/api/ai/manual/ask", json={"question": "예약문자 작성"})
    assert resp.status_code == 200, resp.text
    assert_manual_ask_contract(resp.json())
    assert call_count(ai_enabled_with_fake) == 1


def test_no_circular_import_when_loading_skeleton():
    """신규 패키지가 ``app.services.ai.manual_qa`` / ``app.services.rag.search``
    를 import 하지 않는지 (역의존 회피) 검증.

    ``rag.pipeline`` 등이 ``manual_qa`` 를 import 하면 circular 위험이 생긴다.
    ``sys.modules`` 의 모듈 간 의존 그래프를 직접 체크하지는 않고, 신규 패키지
    의 모든 모듈이 독립적으로 import 가능한지로 간접 확인.
    """
    import importlib

    for name in (
        "app.services.ai.rag",
        "app.services.ai.rag.schemas",
        "app.services.ai.rag.safety",
        "app.services.ai.rag.prompts",
        "app.services.ai.rag.pipeline",
        "app.services.ai.rag.retriever",
        "app.services.ai.knowledge",
        "app.services.ai.knowledge.loader",
        "app.services.ai.knowledge.normalizer",
        "app.services.ai.knowledge.keyword_index",
    ):
        importlib.import_module(name)
