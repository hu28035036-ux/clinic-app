"""Knowledge 패키지 — 18-2 keyword RAG 분리 + 18-3 chunker.

구성:
  - ``loader``        : 마크다운 로딩 (캐시 + raw dict / Document 변환)
  - ``normalizer``    : 마크다운 정규화 + heading/section 추출 (순수 함수)
  - ``chunker``       : Document → list[Chunk] 결정적 분리 (순수 함수, 18-3)
  - ``keyword_index`` : Document 단위 keyword 검색 (18-2 RAG 진입점)

청크 영속화 (``knowledge_chunks`` 테이블) 와 embedding 은 18-4/18-5 이후.

의존 규칙:
  - ``app.services.ai.rag.schemas`` 와 ``app.config.resource_path`` 만 import.
  - 기존 ``app.services.rag`` 또는 ``app.services.ai.manual_qa`` 는 import 하지 않음.
"""
from __future__ import annotations
