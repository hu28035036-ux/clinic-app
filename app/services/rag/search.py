"""knowledge/ 키워드 검색 — 결정론적 (외부 호출 없음).

우선순위:
  1) knowledge/_index.json 이 있으면 그걸 로드 (tools/build_knowledge_index.py 산출)
  2) 없으면 런타임에 *.md 를 직접 스캔 (배포 누락 안전망)

검색:
  - 쿼리를 토큰화 → 문서별 토큰 교집합 크기로 score
  - 문서 name (예: 'tone_confirm') 이 쿼리에 그대로 포함되면 +5 보너스
  - score 0 이고 name 도 매칭 안 되면 결과에서 제외
"""
from __future__ import annotations
import json
import re
from threading import Lock
from typing import Optional

from ...config import resource_path


_INDEX_CACHE: Optional[dict] = None
_INDEX_LOCK = Lock()
_TOKEN_RE = re.compile(r"[\s\W_]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.split(text) if len(t) >= 2]


def _load_index() -> dict:
    """인덱스 1회 로딩 + 캐시. 호출 사이트에서 mutate 금지."""
    global _INDEX_CACHE
    if _INDEX_CACHE is not None:
        return _INDEX_CACHE
    with _INDEX_LOCK:
        if _INDEX_CACHE is not None:
            return _INDEX_CACHE
        idx_path = resource_path("knowledge") / "_index.json"
        if idx_path.exists():
            try:
                _INDEX_CACHE = json.loads(idx_path.read_text(encoding="utf-8"))
                return _INDEX_CACHE
            except Exception:
                # 손상된 인덱스는 무시하고 런타임 스캔으로 폴백
                pass
        _INDEX_CACHE = _build_runtime_index()
    return _INDEX_CACHE


def _build_runtime_index() -> dict:
    """인덱스 파일이 없을 때 *.md 를 직접 스캔."""
    root = resource_path("knowledge")
    docs = []
    if root.exists():
        for md in sorted(root.rglob("*.md")):
            try:
                rel = md.relative_to(root).as_posix()
                text = md.read_text(encoding="utf-8")
            except Exception:
                continue
            category = rel.split("/")[0] if "/" in rel else ""
            first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
            title = first_line.lstrip("#").strip() or md.stem
            docs.append({
                "path": rel,
                "category": category,
                "name": md.stem,
                "title": title,
                "tokens": _tokenize(text)[:300],
                "full_text": text,
            })
    return {"version": 1, "built_at": "runtime", "documents": docs}


def search(
    query: str,
    *,
    category: Optional[str] = None,
    limit: int = 5,
) -> list[dict]:
    """knowledge/ 키워드 검색.

    인자:
        query    : 검색어 (자유 형식)
        category : "sms_guides" 등으로 좁히기. None 이면 전체.
        limit    : 상위 N개 반환

    반환:
        [{path, category, name, title, snippet, score}, ...]
    """
    if not query:
        return []
    idx = _load_index()
    query_tokens = set(_tokenize(query))
    query_lower = query.lower()
    if not query_tokens and not query_lower.strip():
        return []

    results: list[dict] = []
    for doc in idx.get("documents", []):
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
        results.append({
            "path": doc.get("path", ""),
            "category": doc.get("category", ""),
            "name": doc.get("name", ""),
            "title": doc.get("title", ""),
            "snippet": full[:300],
            "score": score,
        })
    results.sort(key=lambda r: -r["score"])
    return results[:limit]


def reset_cache() -> None:
    """테스트/재인덱스 후 캐시 초기화."""
    global _INDEX_CACHE
    with _INDEX_LOCK:
        _INDEX_CACHE = None
