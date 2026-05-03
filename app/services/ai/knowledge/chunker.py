"""Markdown chunker — 18-3 구현.

heading 기준 섹션 분리 → min/max 크기 조정 (병합/분할) → overlap 옵션 적용.
순수 함수 (외부 호출 0, 결정적, 테스트 친화).

요구사항 (docs/checklists/18-3_chunker_checklist.md, 사용자 메시지):
  1. heading 기준 우선 분리
  2. 너무 짧은 chunk 는 인접 chunk 와 병합
  3. 너무 긴 chunk 는 문단(``\\n\\n``) 기준으로 재분리
  4. overlap 적용 가능 (sub-chunk 간)
  5. 표/목록/코드블록은 가능하면 한 chunk 안에 유지 (문단 분할만 사용)
  6. 메뉴 경로와 설명 분리 금지 (문단 단위 보존으로 자연 보호)
  7. 예약문자 예시 보존 (문단 단위로 같이 묶이도록)
  8. source_path / title / heading / section_path / chunk_index 유지
  9. content_hash 생성 (sha256(content) hex)
  10. 동일 입력 → 동일 content_hash (결정적)
  11. 문서 내용 변경 → content_hash 변경 (해시 입력에 content 만)
  12. chunk 순서 안정성 (chunk_index 0,1,2,... 누락/중복 없음)

기본값 (변경 시 latest_fix_summary.md 기록 의무):
  - ``MIN_CHUNK_CHARS = 200``
  - ``MAX_CHUNK_CHARS = 1200``
  - ``OVERLAP_CHARS = 150``  (사용자 권장 100~200 의 중앙값)

DB 영속화 / embedding / vector store 는 본 단계 범위 밖 (18-4/18-5).
"""
from __future__ import annotations

import hashlib
from typing import Iterable

from ..rag.schemas import Chunk, Document
from .normalizer import extract_sections, normalize_markdown

# 기본 크기 — 변경 시 latest_fix_summary.md 에 사유/이전값/신규값 기록.
MIN_CHUNK_CHARS = 200
MAX_CHUNK_CHARS = 1200
OVERLAP_CHARS = 150


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha1_hex(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _document_title(raw_text: str) -> str:
    """문서의 첫 h1/h2 텍스트 — 없으면 빈 문자열."""
    sections = extract_sections(raw_text)
    for s in sections:
        if s.get("heading"):
            return s["heading"]
    return ""


def _is_heading_only_section(sec: dict) -> bool:
    """섹션 content 가 사실상 heading 라인 하나뿐인지 (body 부재)."""
    content = (sec.get("content") or "").strip()
    if not content:
        return True
    lines = [ln for ln in content.split("\n") if ln.strip()]
    return len(lines) <= 1


def _merge_short_sections(
    sections: list[dict],
    min_chars: int,
    max_chars: int,
) -> list[dict]:
    """짧은 섹션을 인접 섹션과 병합.

    탐욕적: content 길이 합이 min 이상이 될 때까지 다음 섹션과 합친다.
    단, max 를 넘어가면 멈춘다 (분할 단계가 따로 처리).

    metadata 처리:
      - 일반 케이스: buf 의 heading/section_path 유지 (entry-point 보존).
      - buf 가 heading-only (예: 문서 첫 ``# 제목`` 만) 인 경우, 다음 섹션의
        heading/section_path 를 promote — 의미 있는 heading 이 chunk 메타에 남도록.

    ``content`` 는 각 섹션의 raw content 를 ``\\n\\n`` 으로 연결.
    """
    if not sections:
        return []

    merged: list[dict] = []
    buf: dict | None = None

    for sec in sections:
        if buf is None:
            buf = dict(sec)
            continue

        # buf 가 이미 충분히 길거나, 합치면 max 를 넘어가면 flush.
        if len(buf["content"]) >= min_chars:
            merged.append(buf)
            buf = dict(sec)
            continue

        joined = buf["content"] + "\n\n" + sec["content"]
        if len(joined) > max_chars and len(buf["content"]) >= min_chars:
            # buf 가 충분히 차면 flush
            merged.append(buf)
            buf = dict(sec)
            continue

        # buf 가 heading-only 면 sec 의 heading metadata 로 promote
        if _is_heading_only_section(buf):
            buf["heading"] = sec.get("heading", buf.get("heading", ""))
            buf["section_path"] = sec.get(
                "section_path", buf.get("section_path", "")
            )
            buf["level"] = sec.get("level", buf.get("level", 0))

        buf["content"] = joined

    if buf is not None:
        merged.append(buf)

    return merged


def _split_large_section_content(
    content: str,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    """단일 섹션 content 가 max 를 초과하면 문단(``\\n\\n``) 기준 분할.

    문단 단위로만 자르므로 표/목록/메뉴 경로/예약문자 예시 등이 한 문단 안에
    있다면 보존된다. 한 문단이 max 를 넘어가면 그대로 유지 (soft max).

    overlap_chars > 0 이면 sub-chunk 사이에 overlap 적용 — 직전 chunk 의
    마지막 N 글자를 다음 chunk 시작에 동봉.
    """
    if len(content) <= max_chars:
        return [content]

    paragraphs = content.split("\n\n")
    out: list[str] = []
    current = ""

    for para in paragraphs:
        if not current:
            current = para
            continue

        candidate_len = len(current) + 2 + len(para)
        if candidate_len <= max_chars:
            current = current + "\n\n" + para
        else:
            out.append(current)
            if overlap_chars > 0 and len(current) >= overlap_chars:
                tail = current[-overlap_chars:]
                current = tail + "\n\n" + para
            else:
                current = para

    if current:
        out.append(current)

    return out


def chunk_document(
    doc: Document,
    *,
    min_chunk_chars: int = MIN_CHUNK_CHARS,
    max_chunk_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[Chunk]:
    """단일 ``Document`` → ``Chunk`` 리스트.

    결정적: 동일 ``Document.raw_text`` 입력 + 동일 파라미터 → 동일 결과.
    파라미터 검증:
      - ``min_chunk_chars`` 는 0 이상.
      - ``max_chunk_chars`` 는 ``min_chunk_chars`` 이상.
      - ``overlap_chars`` 는 0 이상이며 ``max_chunk_chars`` 미만 권장.
    """
    if min_chunk_chars < 0:
        raise ValueError(f"min_chunk_chars must be >= 0, got {min_chunk_chars}")
    if max_chunk_chars < min_chunk_chars:
        raise ValueError(
            f"max_chunk_chars ({max_chunk_chars}) must be >= "
            f"min_chunk_chars ({min_chunk_chars})"
        )
    if overlap_chars < 0:
        raise ValueError(f"overlap_chars must be >= 0, got {overlap_chars}")

    raw_text = doc.raw_text or ""
    title = _document_title(raw_text)
    sections = extract_sections(raw_text)

    if not sections:
        # heading 없는 단일 섹션 — 정규화된 raw_text 만 단일 chunk
        normalized = normalize_markdown(raw_text)
        if not normalized.strip():
            return []
        return [
            _build_chunk(
                doc=doc,
                title=title,
                heading="",
                section_path="",
                chunk_index=0,
                content=normalized,
            )
        ]

    merged = _merge_short_sections(
        sections,
        min_chars=min_chunk_chars,
        max_chars=max_chunk_chars,
    )

    chunks: list[Chunk] = []
    chunk_idx = 0
    for sec in merged:
        sub_contents = _split_large_section_content(
            sec["content"],
            max_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )
        for sub in sub_contents:
            chunks.append(
                _build_chunk(
                    doc=doc,
                    title=title,
                    heading=sec.get("heading", ""),
                    section_path=sec.get("section_path", ""),
                    chunk_index=chunk_idx,
                    content=sub,
                )
            )
            chunk_idx += 1

    return chunks


def chunk_documents(
    docs: Iterable[Document],
    *,
    min_chunk_chars: int = MIN_CHUNK_CHARS,
    max_chunk_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[Chunk]:
    """여러 문서를 일괄 chunking.

    각 문서는 자기 ``chunk_index`` 가 0 부터 다시 시작 (문서별 안정 인덱스).
    """
    out: list[Chunk] = []
    for d in docs:
        out.extend(
            chunk_document(
                d,
                min_chunk_chars=min_chunk_chars,
                max_chunk_chars=max_chunk_chars,
                overlap_chars=overlap_chars,
            )
        )
    return out


def _build_chunk(
    *,
    doc: Document,
    title: str,
    heading: str,
    section_path: str,
    chunk_index: int,
    content: str,
) -> Chunk:
    source_path = doc.path or ""
    return Chunk(
        doc_id=_sha1_hex(source_path),
        source_path=source_path,
        category=doc.category or "",
        title=title,
        heading=heading,
        section_path=section_path,
        chunk_index=chunk_index,
        content=content,
        content_hash=_sha256_hex(content),
        token_count=len(content),
        tags="",
        document_version="",
    )


__all__ = [
    "chunk_document",
    "chunk_documents",
    "MIN_CHUNK_CHARS",
    "MAX_CHUNK_CHARS",
    "OVERLAP_CHARS",
]
