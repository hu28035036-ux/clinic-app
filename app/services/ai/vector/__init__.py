"""Vector / Embedding 패키지 — 18-5.

목표 RAG 아키텍처(``docs/ai_rag_architecture_plan.md`` §3-17~3-19, §8, §11)의
vector store / embedding provider 모듈 공간.

구성:
  - ``embeddings`` : ``EmbeddingProvider`` 추상 + ``FakeEmbeddingProvider``
    (테스트용) + factory ``get_embedding_provider``. 외부 OpenAI/Anthropic
    embedding 실제 호출은 18-5 범위 외 — slot 만 둠 (NotImplementedError).
  - ``store``      : ``knowledge_vectors`` 테이블 wrapper (upsert/find/list).
  - ``similarity`` : cosine similarity + top_k (안정 정렬).

의존 규칙 (circular import 방지 — ``rag/__init__.py`` 가이드와 동일 패턴):
  - 본 패키지는 ``app.config``, ``app.models.models``,
    ``app.services.ai.rag.schemas`` 만 import 가능.
  - 기존 ``app.services.ai.manual_qa`` / ``app.services.ai.rag.pipeline`` /
    ``app.services.ai.rag.retriever`` 는 import 하지 않는다 (역의존 회피).
  - 18-6 hybrid retriever 시점에 retriever 가 본 패키지를 import 하는 단방향
    의존만 허용.

실제 동작:
  - 18-5: indexer 의 vector 단계 옵션 hook + FakeEmbeddingProvider 검증.
  - 18-6: hybrid retriever (keyword + vector 결합).
  - 18-7: AiUsageLog m014 컬럼 + 라우터 응답 reason_code 노출.

외부 LLM/Embedding 실제 호출은 운영 환경에서만 (관리자 활성화 + API key 설정).
테스트는 100% FakeEmbeddingProvider — ``tests/conftest.py:_block_sdk_modules``
가 SDK 클래스를 raise 로 교체해 외부 호출을 차단한다.
"""
from __future__ import annotations
