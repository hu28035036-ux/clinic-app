"""Knowledge document loader — 18-2 분리.

기존 ``app.services.rag.search._load_index`` / ``_build_runtime_index`` 의 로딩
로직을 본 모듈로 이전. ``_index.json`` 우선, 없으면 런타임에 ``*.md`` 스캔.

동작 원칙 (분리 전후 동등):
  - 결과는 v1.3.3 와 동일한 ``{path,category,name,title,tokens,full_text}`` dict.
  - 외부 호출 없음 (deterministic).
  - 캐시는 모듈 전역 1회. ``reset_cache()`` 로 명시적 초기화.

18-1 stub 인 ``load_documents()`` 는 본 모듈에서 정식 구현 (``Document``
dataclass 리스트 반환). ``get_raw_documents()`` 는 keyword_index 가 사용하는
원본 dict 리스트.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Optional

from ....config import resource_path
from ..rag.schemas import Document

_TOKEN_RE = re.compile(r"[\s\W_]+", re.UNICODE)

_LOADER_CACHE: Optional[list[dict]] = None
_LOADER_LOCK = Lock()


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.split(text) if len(t) >= 2]


def _doc_dict_from_md(md_path: Path, root: Path) -> Optional[dict]:
    try:
        rel = md_path.relative_to(root).as_posix()
        text = md_path.read_text(encoding="utf-8")
    except Exception:
        return None
    category = rel.split("/")[0] if "/" in rel else ""
    first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
    title = first_line.lstrip("#").strip() or md_path.stem
    return {
        "path": rel,
        "category": category,
        "name": md_path.stem,
        "title": title,
        "tokens": _tokenize(text)[:300],
        "full_text": text,
    }


def _load_raw_index() -> list[dict]:
    """``_index.json`` 우선, 없으면 ``*.md`` 직접 스캔."""
    idx_path = resource_path("knowledge") / "_index.json"
    if idx_path.exists():
        try:
            data = json.loads(idx_path.read_text(encoding="utf-8"))
            docs = data.get("documents")
            if isinstance(docs, list):
                return docs
        except Exception:
            pass

    root = resource_path("knowledge")
    docs: list[dict] = []
    if root.exists():
        for md in sorted(root.rglob("*.md")):
            d = _doc_dict_from_md(md, root)
            if d:
                docs.append(d)
    return docs


def get_raw_documents() -> list[dict]:
    """Cached 원본 dict 리스트 — keyword_index 가 사용하는 내부 형식.

    각 dict 키: ``path, category, name, title, tokens, full_text``.
    """
    global _LOADER_CACHE
    if _LOADER_CACHE is not None:
        return _LOADER_CACHE
    with _LOADER_LOCK:
        if _LOADER_CACHE is not None:
            return _LOADER_CACHE
        _LOADER_CACHE = _load_raw_index()
    return _LOADER_CACHE


def reset_cache() -> None:
    """Loader 내부 캐시 초기화 (테스트/재인덱스 후)."""
    global _LOADER_CACHE
    with _LOADER_LOCK:
        _LOADER_CACHE = None


def load_documents(
    root: Optional[str] = None,
    category: Optional[str] = None,
) -> list[Document]:
    """``knowledge/<category>/*.md`` 로딩 → ``Document`` dataclass 리스트.

    ``root`` 인자는 18-3 chunker 도입 시 외부 경로 주입을 위한 것 (현재 미사용,
    인터페이스만 보존). ``category`` 필터링은 즉시 적용.
    """
    _ = root  # 18-3 에서 활용 예정 (외부 root 주입)
    raw = get_raw_documents()
    out: list[Document] = []
    for d in raw:
        if category and d.get("category") != category:
            continue
        out.append(
            Document(
                path=d.get("path", ""),
                category=d.get("category", ""),
                raw_text=d.get("full_text", ""),
                content_hash="",
                mtime=0.0,
            )
        )
    return out


__all__ = ["load_documents", "get_raw_documents", "reset_cache"]
