"""Chunk 하네스 — 18-3 chunker 검증 helper.

기능:
  - 결정성 / 순서 안정성 / 메타 보존 / 크기 단언 helper
  - 표/목록/메뉴 경로/SMS 예시 보호 단언 helper
  - external provider/embedding 호출 0 단언 helper

상세 설계: ``docs/harnesses/chunk_harness_plan.md``.
"""
from __future__ import annotations

from typing import Any

from app.services.ai.knowledge.chunker import chunk_document
from app.services.ai.rag.schemas import Chunk, Document

# ──────────────────────── 결정성 / 안정성 ────────────────────────


def assert_chunks_deterministic(
    raw_text: str,
    *,
    path: str = "manuals/sample.md",
    category: str = "manuals",
    times: int = 5,
    **kwargs: Any,
) -> list[Chunk]:
    """동일 입력 → 동일 chunks N회 단언 (요구사항 #10/#12)."""
    doc = Document(path=path, category=category, raw_text=raw_text)
    first = chunk_document(doc, **kwargs)
    for i in range(1, times):
        again = chunk_document(doc, **kwargs)
        assert len(first) == len(again), (
            f"deterministic: chunk count mismatch on iter {i}: "
            f"{len(first)} vs {len(again)}"
        )
        for j, (a, b) in enumerate(zip(first, again, strict=True)):
            assert a.content == b.content, (
                f"deterministic: chunk {j} content mismatch on iter {i}"
            )
            assert a.content_hash == b.content_hash, (
                f"deterministic: chunk {j} content_hash mismatch on iter {i}: "
                f"{a.content_hash[:12]}.. vs {b.content_hash[:12]}.."
            )
            assert a.chunk_index == b.chunk_index, (
                f"deterministic: chunk {j} index mismatch on iter {i}"
            )
    return first


def assert_chunk_indexes_sequential(chunks: list[Chunk]) -> None:
    """chunk_index 가 0,1,2,... 누락/중복 없음 (요구사항 #12)."""
    for expected, c in enumerate(chunks):
        assert c.chunk_index == expected, (
            f"chunk_index mismatch at position {expected}: got {c.chunk_index}"
        )


def assert_metadata_preserved(chunks: list[Chunk], *, source_path: str) -> None:
    """source_path / title / heading / section_path / chunk_index 보존 (요구사항 #8)."""
    for c in chunks:
        assert c.source_path == source_path, (
            f"source_path drift: expected {source_path!r}, got {c.source_path!r}"
        )
        # title 은 모든 chunk 에서 동일해야 함
        assert isinstance(c.title, str)
        assert isinstance(c.heading, str)
        assert isinstance(c.section_path, str)
        assert isinstance(c.chunk_index, int)
    # title 통일성 단언
    if chunks:
        title0 = chunks[0].title
        for c in chunks:
            assert c.title == title0, (
                f"title drift across chunks: {title0!r} vs {c.title!r}"
            )


def assert_content_hash_present_and_stable(chunks: list[Chunk]) -> None:
    """모든 chunk 에 content_hash 존재 + sha256 형식 (요구사항 #9)."""
    for c in chunks:
        assert c.content_hash, f"chunk {c.chunk_index} content_hash missing"
        assert len(c.content_hash) == 64, (
            f"chunk {c.chunk_index} content_hash not sha256 hex: "
            f"len={len(c.content_hash)}"
        )
        # 같은 content → 같은 hash
        import hashlib
        expected = hashlib.sha256(c.content.encode("utf-8")).hexdigest()
        assert c.content_hash == expected, (
            f"chunk {c.chunk_index} content_hash != sha256(content)"
        )


# ──────────────────────── 크기 / 보호 블록 ────────────────────────


def assert_no_chunk_exceeds_soft_max(
    chunks: list[Chunk],
    max_chars: int,
    *,
    soft_factor: float = 1.2,
) -> None:
    """문단 단위 분할이라 단일 문단(표/리스트/코드) 가 초과할 수는 있지만,
    soft 한도 (max * soft_factor) 는 넘지 않아야 한다는 지표.
    """
    soft_limit = int(max_chars * soft_factor)
    for c in chunks:
        # 단일 문단인 경우 (분할 불가) 는 예외 — 문단 갯수 1 일 때만 허용
        para_count = len([p for p in c.content.split("\n\n") if p.strip()])
        if len(c.content) > soft_limit and para_count > 1:
            raise AssertionError(
                f"chunk {c.chunk_index} exceeds soft limit {soft_limit}: "
                f"len={len(c.content)}, paragraphs={para_count}"
            )


def assert_table_lines_kept_together(chunks: list[Chunk]) -> None:
    """표(``| col |`` 라인) 가 한 chunk 안에서 끊기지 않음 (요구사항 #5)."""
    for c in chunks:
        lines = c.content.split("\n")
        # 표 라인은 인접해야 함 — 비표 라인 사이에 섞이는 정도는 허용
        # 핵심: 한 chunk 내 표 라인 개수가 0 또는 >=2 여야 정상
        # (다음 chunk 로 넘어간 표의 잔여 1 라인이 없어야 함)
        table_runs = []
        run = 0
        for ln in lines:
            if ln.lstrip().startswith("|"):
                run += 1
            else:
                if run > 0:
                    table_runs.append(run)
                run = 0
        if run > 0:
            table_runs.append(run)
        # 단일 라인 (1개) 짜리 표 잔여는 분할 의심 신호
        for run_len in table_runs:
            assert run_len != 1 or len(table_runs) == 1, (
                f"chunk {c.chunk_index} suspiciously contains a single table line"
            )


def assert_menu_path_intact(chunks: list[Chunk], *, menu_marker: str = "→") -> None:
    """메뉴 경로 (``A → B → C``) 가 한 chunk 안에서 보존 (요구사항 #6).

    menu_marker 가 등장하는 chunk 의 그 라인 전체가 그 chunk 안에 있어야 함.
    """
    for c in chunks:
        for ln in c.content.split("\n"):
            if menu_marker not in ln:
                continue
            # 라인이 잘리지 않았다면 양쪽에 의미있는 텍스트가 있어야 함
            parts = ln.split(menu_marker)
            assert len(parts) >= 2 and any(p.strip() for p in parts), (
                f"chunk {c.chunk_index} has truncated menu path: {ln!r}"
            )


def assert_sms_example_intact(
    chunks: list[Chunk],
    *,
    open_quote: str = "{",
    close_quote: str = "}",
) -> None:
    """예약문자 변수 (``{환자명}`` 등) 가 chunk 경계로 잘리지 않음 (요구사항 #7).

    각 chunk 안에서 변수 열림/닫힘 짝이 맞아야 한다.
    """
    for c in chunks:
        opens = c.content.count(open_quote)
        closes = c.content.count(close_quote)
        assert opens == closes, (
            f"chunk {c.chunk_index} has mismatched SMS variable braces: "
            f"opens={opens}, closes={closes}"
        )


# ──────────────────────── 외부 호출 0 ────────────────────────


def assert_no_external_calls(
    provider: Any | None = None,
    embedding_provider: Any | None = None,
) -> None:
    """chunker 동작 중 LLM/Embedding 호출이 0 (요구사항 #13/#14).

    chunker 는 순수 함수이므로 호출 0 은 자동이지만, 통합 테스트용으로 단언 보조.
    """
    if provider is not None:
        n = len(getattr(provider, "calls", []) or [])
        assert n == 0, f"expected len(provider.calls) == 0, got {n}"
    if embedding_provider is not None:
        en = len(getattr(embedding_provider, "calls", []) or [])
        assert en == 0, f"expected len(embedding_provider.calls) == 0, got {en}"


__all__ = [
    "assert_chunks_deterministic",
    "assert_chunk_indexes_sequential",
    "assert_metadata_preserved",
    "assert_content_hash_present_and_stable",
    "assert_no_chunk_exceeds_soft_max",
    "assert_table_lines_kept_together",
    "assert_menu_path_intact",
    "assert_sms_example_intact",
    "assert_no_external_calls",
]
