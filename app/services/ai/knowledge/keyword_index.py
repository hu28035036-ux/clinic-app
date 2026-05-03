"""Keyword inverted index — 18-2 분리.

기존 ``app.services.rag.search.search`` 의 토큰 교집합 + name 보너스 알고리즘을
본 모듈로 이전. ``loader.get_raw_documents()`` 가 제공하는 dict 리스트에서 검색.

분리 전후 동등성 보장 (알고리즘 v1.3.3 그대로):
  1. 쿼리를 토큰화 (``[\\s\\W_]+`` 분리, 길이>=2, lowercase)
  2. 문서별 ``query_tokens & doc.tokens`` 교집합 크기 = score
  3. 문서 name 이 query lower 에 그대로 포함되면 +5 보너스
  4. score==0 (name 매칭도 없음) → 제외
  5. score 내림차순, 상위 N개 반환

18-1 stub 인 ``build_index(chunks)`` / ``search(query, index, ...)`` 는 chunk
기반 인덱스 도입 시점(18-4) 용이라 NotImplementedError 그대로 유지.
**Document 단위 keyword 검색은 ``search_documents()`` 를 사용한다.**
"""
from __future__ import annotations

import re
from typing import Any, Optional

from .loader import get_raw_documents

_TOKEN_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.split(text) if len(t) >= 2]


def search_documents(
    query: str,
    *,
    category: Optional[str] = None,
    limit: int = 5,
) -> list[dict]:
    """Document 단위 keyword 검색 — 18-2 keyword RAG.

    인자:
        query    : 검색어 (자유 형식)
        category : ``"manuals"`` 등으로 좁히기. ``None`` 이면 전체.
        limit    : 상위 N개 반환

    반환 dict 키 (기존 ``app.services.rag.search.search`` 와 동일):
        ``path, category, name, title, snippet, score``.
    """
    if not query:
        return []
    query_tokens = set(_tokenize(query))
    query_lower = query.lower()
    if not query_tokens and not query_lower.strip():
        return []

    results: list[dict] = []
    for doc in get_raw_documents():
        if category and doc.get("category") != category:
            continue
        doc_tokens = set(doc.get("tokens", []))
        score = len(query_tokens & doc_tokens)
        name = (doc.get("name") or "").lower()
        if name and name in query_lower:
            score += 5
        if score == 0:
            continue
        full = doc.get("full_text") or ""
        results.append(
            {
                "path": doc.get("path", ""),
                "category": doc.get("category", ""),
                "name": doc.get("name", ""),
                "title": doc.get("title", ""),
                "snippet": full[:300],
                "score": score,
            }
        )
    results.sort(key=lambda r: -r["score"])
    return results[:limit]


# ── 18-1 stub 보존 — chunk 기반 인덱스(18-4) 진입점 ──
def build_index(chunks: list) -> dict[str, Any]:
    """chunk 리스트 → inverted index — **18-4 chunk 도입 후 구현**."""
    _ = chunks
    raise NotImplementedError(
        "knowledge.keyword_index.build_index 는 18-4 (chunks) 에서 구현됩니다."
    )


def search(query: str, index: dict[str, Any], *, limit: int = 5) -> list[dict]:
    """chunk 기반 index 검색 — **18-4 에서 구현**.

    18-2 시점의 Document 단위 검색은 ``search_documents()`` 를 사용한다.
    """
    _ = (query, index, limit)
    raise NotImplementedError(
        "knowledge.keyword_index.search 는 18-4 (chunks) 에서 구현됩니다. "
        "Document 단위 검색은 search_documents() 를 사용하세요."
    )


__all__ = ["search_documents", "build_index", "search"]
