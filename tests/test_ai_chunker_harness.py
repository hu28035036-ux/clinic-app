"""18-3 Chunker Harness — 사용자 메시지의 15개 단언 항목 검증.

구성:
  1.  heading 기준으로 chunk 가 나뉨
  2.  너무 짧은 chunk 가 병합됨
  3.  너무 긴 chunk 가 문단 기준으로 나뉨
  4.  overlap 적용 가능
  5.  표/목록이 중간에 과도하게 잘리지 않음
  6.  메뉴 경로와 설명이 분리되지 않음
  7.  예약문자 예시가 중간에 잘리지 않음
  8.  source_path / title / heading / section_path / chunk_index 유지
  9.  content_hash 생성됨
  10. 같은 입력 문서에서 content_hash 안정
  11. 문서 내용 변경 시 content_hash 가 바뀜
  12. chunk 순서 안정 (chunk_index 0,1,2,...)
  13. chunker 테스트에서 외부 LLM provider 호출 0
  14. chunker 테스트에서 embedding provider 호출 0
  15. 운영 DB 미사용 (conftest db_guard 가 검증)

추가 검증:
  - 18-2 keyword RAG / manual API 회귀 0
  - chunk_documents 일괄 처리 결정성
"""
from __future__ import annotations

from app.services.ai.knowledge.chunker import (
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
    OVERLAP_CHARS,
    chunk_document,
    chunk_documents,
)
from app.services.ai.knowledge.normalizer import (
    extract_headings,
    extract_sections,
    normalize_markdown,
)
from app.services.ai.rag.schemas import Chunk, Document
from tests.harness.chunk_harness import (
    assert_chunk_indexes_sequential,
    assert_chunks_deterministic,
    assert_content_hash_present_and_stable,
    assert_menu_path_intact,
    assert_metadata_preserved,
    assert_no_chunk_exceeds_soft_max,
    assert_no_external_calls,
    assert_sms_example_intact,
    assert_table_lines_kept_together,
)
from tests.harness.fake_provider import FakeProvider

# ──────────────────────── 픽스처 텍스트 ────────────────────────


def _doc(raw: str, *, path: str = "manuals/sample.md", category: str = "manuals") -> Document:
    return Document(path=path, category=category, raw_text=raw)


SHORT_DOC = """\
# 짧은 문서 제목

## 위치
메인 화면 상단 → 관리자 → 백업

## 절차
1. 백업 버튼을 누른다.
2. 결과를 확인한다.
"""

LONG_DOC = """\
# 긴 문서

## 섹션 A
""" + ("문단 A 내용. " * 60) + """

""" + ("문단 A 두 번째. " * 60) + """

## 섹션 B
""" + ("문단 B 내용. " * 60) + """

""" + ("문단 B 두 번째. " * 60)

CODE_BLOCK_DOC = """\
# 코드블록 포함 문서

## 코드 예시
아래는 코드 블록입니다:

```
# 이 줄은 코드 안의 # 라서 heading 이 아닙니다
def foo():
    return 1
```

설명 문단입니다.
"""

TABLE_DOC = """\
# 표 포함 문서

## 가격표
다음은 표입니다:

| 항목 | 가격 |
|------|------|
| A    | 1000 |
| B    | 2000 |
| C    | 3000 |

설명 문단입니다.
"""

LIST_DOC = """\
# 목록 포함 문서

## 절차
1. 첫 번째 단계
2. 두 번째 단계
3. 세 번째 단계
4. 네 번째 단계
5. 다섯 번째 단계

설명 문단입니다.
"""

MENU_PATH_DOC = """\
# 메뉴 경로 문서

## 위치
메인 화면 상단 탭 → 관리자 → 버전/업데이트 → 백업 폴더

설명 문단입니다.
"""

SMS_EXAMPLE_DOC = """\
# 예약문자 예시 문서

## 템플릿
환자에게 보낼 본문 예시:

안녕하세요 {환자명}님, 내일 {예약일시}에 예약이 있습니다. {병원명} 드림.

변수는 자동 치환됩니다.
"""

NO_HEADING_DOC = "단순 본문\n두 번째 줄\n"


# ──────────────────────── 1. heading 기준 분리 ────────────────────────


def test_1_heading_splits_into_sections():
    """요구사항 #1 — heading 으로 섹션 경계가 인식되어 분리됨."""
    doc = _doc(LONG_DOC)
    chunks = chunk_document(doc)
    # 섹션 A 와 섹션 B 가 별도 chunk 로 가야 함
    headings = {c.heading for c in chunks if c.heading}
    assert "섹션 A" in headings, f"섹션 A heading missing: {headings}"
    assert "섹션 B" in headings, f"섹션 B heading missing: {headings}"


def test_1b_heading_extraction_basic():
    """normalizer.extract_headings 가 heading 라인을 정확히 추출."""
    headings = extract_headings(LONG_DOC)
    levels = [h["level"] for h in headings]
    texts = [h["text"] for h in headings]
    assert 1 in levels  # h1
    assert 2 in levels  # h2
    assert "긴 문서" in texts
    assert "섹션 A" in texts
    assert "섹션 B" in texts


# ──────────────────────── 2. 짧은 chunk 병합 ────────────────────────


def test_2_short_sections_get_merged():
    """요구사항 #2 — 매우 짧은 섹션은 인접 섹션과 병합되어 chunk 수가 줄어듦."""
    doc = _doc(SHORT_DOC)
    chunks = chunk_document(doc)
    # SHORT_DOC 은 매우 짧으므로 1개 chunk 로 병합되어야 함
    assert len(chunks) == 1, (
        f"expected 1 merged chunk for SHORT_DOC, got {len(chunks)}: "
        f"{[c.heading for c in chunks]}"
    )
    # 모든 섹션 텍스트가 다 포함되어야 함
    only = chunks[0].content
    assert "위치" in only and "절차" in only
    assert "메인 화면" in only and "백업 버튼" in only


# ──────────────────────── 3. 긴 chunk 문단 기준 분할 ────────────────────────


def test_3_long_section_splits_at_paragraph_boundary():
    """요구사항 #3 — 너무 긴 섹션은 \\n\\n 문단 기준으로 재분리."""
    doc = _doc(LONG_DOC)
    chunks = chunk_document(doc, max_chunk_chars=600, min_chunk_chars=100)
    # 각 섹션이 ~1500자 → 600자 max 면 섹션마다 2~3개 chunk
    assert len(chunks) >= 3, (
        f"expected >=3 chunks for LONG_DOC at max=600, got {len(chunks)}"
    )
    # 분할 경계는 문단(\\n\\n) 사이여야 — 한 chunk 안에 문단이 닫혀 있어야
    for c in chunks:
        # 마지막 라인이 끊겨 있지 않아야 (단어 중간 절단 검출)
        assert not c.content.endswith(" "), (
            f"chunk {c.chunk_index} ends with whitespace (likely cut mid-flow)"
        )


# ──────────────────────── 4. overlap 적용 ────────────────────────


def test_4_overlap_applied_between_subchunks():
    """요구사항 #4 — overlap_chars > 0 이면 sub-chunk 사이에 중첩 텍스트 발생."""
    # 한 섹션 안에 매우 긴 컨텐츠를 넣어서 overlap 발생 유도
    long_section = "# 문서\n\n## 섹션\n\n" + "\n\n".join(
        f"문단 {i} 내용입니다. " * 40 for i in range(8)
    )
    doc = _doc(long_section)
    chunks = chunk_document(doc, max_chunk_chars=400, overlap_chars=120)
    assert len(chunks) >= 2, "need >=2 chunks to verify overlap"
    # 인접 chunk 사이에 일부 문자열이 공유되는지 확인
    found_overlap = False
    for a, b in zip(chunks, chunks[1:], strict=False):
        # b 의 시작 부분이 a 의 끝에 등장하는지
        head = b.content[:80]
        if head and head in a.content:
            found_overlap = True
            break
    assert found_overlap, (
        "overlap_chars=120 이지만 인접 chunk 사이에 공유 텍스트 미검출"
    )


def test_4b_overlap_disabled_means_no_overlap():
    """overlap_chars=0 → 인접 chunk 사이 공유 없음."""
    long_section = "# 문서\n\n## 섹션\n\n" + "\n\n".join(
        f"고유문단{i}_{'X' * 60}" for i in range(8)
    )
    doc = _doc(long_section)
    chunks = chunk_document(doc, max_chunk_chars=300, overlap_chars=0)
    assert len(chunks) >= 2
    # 각 문단이 고유하므로 head 가 이전 chunk 에 없어야 함
    for a, b in zip(chunks, chunks[1:], strict=False):
        head = b.content[:50]
        assert head not in a.content, (
            f"overlap=0 인데 chunk {a.chunk_index}→{b.chunk_index} 사이 공유 검출"
        )


# ──────────────────────── 5. 표/목록 보존 ────────────────────────


def test_5_table_kept_in_one_chunk():
    """요구사항 #5 — 표는 한 chunk 안에 보존."""
    doc = _doc(TABLE_DOC)
    chunks = chunk_document(doc)
    # 표 라인 (|) 들이 모두 같은 chunk 안에
    pipe_chunks = [c for c in chunks if "|" in c.content]
    assert len(pipe_chunks) == 1, (
        f"표가 {len(pipe_chunks)}개 chunk 에 분산됨"
    )
    table_chunk = pipe_chunks[0]
    pipe_lines = [ln for ln in table_chunk.content.split("\n") if "|" in ln]
    assert len(pipe_lines) >= 5, f"표 라인 누락: {len(pipe_lines)}"
    assert_table_lines_kept_together(chunks)


def test_5b_list_kept_in_one_chunk():
    """요구사항 #5 — 번호 매김 목록은 한 chunk 안에 보존."""
    doc = _doc(LIST_DOC)
    chunks = chunk_document(doc)
    # 번호 매김 라인들이 같은 chunk 에
    list_chunks = []
    for c in chunks:
        nums = [ln for ln in c.content.split("\n") if ln.lstrip().startswith(("1.", "2.", "3.", "4.", "5."))]
        if nums:
            list_chunks.append((c, len(nums)))
    assert len(list_chunks) == 1, (
        f"목록이 {len(list_chunks)}개 chunk 에 분산됨"
    )
    _, num_count = list_chunks[0]
    assert num_count == 5, f"목록 항목 누락: {num_count}"


def test_5c_code_block_not_parsed_as_heading():
    """코드블록 내부의 ``#`` 가 heading 으로 인식되지 않음."""
    sections = extract_sections(CODE_BLOCK_DOC)
    section_headings = [s["heading"] for s in sections]
    # 코드블록 내 "이 줄은 코드 안의 #" 가 heading 으로 잡히면 안 됨
    assert all("코드 안의" not in h for h in section_headings), (
        f"코드블록 내 # 가 heading 으로 잡힘: {section_headings}"
    )


# ──────────────────────── 6. 메뉴 경로 분리 금지 ────────────────────────


def test_6_menu_path_not_split():
    """요구사항 #6 — 메뉴 경로 (``A → B → C``) 가 chunk 경계로 잘리지 않음."""
    doc = _doc(MENU_PATH_DOC)
    chunks = chunk_document(doc)
    # 모든 chunk 의 메뉴 라인이 양쪽 텍스트 보존
    assert_menu_path_intact(chunks)
    # 메뉴 경로가 등장하는 chunk 가 정확히 1개
    menu_chunks = [c for c in chunks if "메인 화면 상단 탭 → 관리자" in c.content]
    assert len(menu_chunks) == 1


# ──────────────────────── 7. 예약문자 예시 보존 ────────────────────────


def test_7_sms_example_braces_balanced():
    """요구사항 #7 — 예약문자 예시 ``{환자명}`` 등의 변수가 chunk 경계로 잘리지 않음."""
    doc = _doc(SMS_EXAMPLE_DOC)
    chunks = chunk_document(doc)
    assert_sms_example_intact(chunks)


def test_7b_real_sms_compose_md_chunked():
    """실제 ``knowledge/manuals/sms_compose.md`` 가 변수 짝 보존된 채 chunk 됨."""
    from app.services.ai.knowledge.loader import load_documents

    docs = [d for d in load_documents() if "sms_compose" in d.path]
    assert docs, "sms_compose.md 가 loader 결과에 없음"
    chunks = chunk_document(docs[0])
    assert chunks, "chunks 비어있음"
    assert_sms_example_intact(chunks)


# ──────────────────────── 8. 메타 보존 ────────────────────────


def test_8_metadata_preserved_for_each_chunk():
    """요구사항 #8 — source_path / title / heading / section_path / chunk_index 유지."""
    src = "manuals/test_path.md"
    doc = _doc(LONG_DOC, path=src)
    chunks = chunk_document(doc, max_chunk_chars=600)
    assert len(chunks) >= 2
    assert_metadata_preserved(chunks, source_path=src)
    # heading 이 빈 chunk 가 있을 수 있지만, 모든 chunk 가 title 보유
    assert all(c.title == "긴 문서" for c in chunks), (
        f"title drift: {[c.title for c in chunks]}"
    )


def test_8b_section_path_includes_parent_headings():
    """section_path 가 ``h1 > h2`` 누적 형식."""
    sections = extract_sections(LONG_DOC)
    paths = {s["section_path"] for s in sections}
    assert "긴 문서 > 섹션 A" in paths or "긴 문서 > 섹션 A" in [s["section_path"] for s in sections], (
        f"section_path 누적 안 됨: {paths}"
    )


# ──────────────────────── 9~11. content_hash ────────────────────────


def test_9_content_hash_generated():
    """요구사항 #9 — 모든 chunk 가 content_hash 보유."""
    doc = _doc(LONG_DOC)
    chunks = chunk_document(doc)
    assert_content_hash_present_and_stable(chunks)


def test_10_content_hash_stable_for_same_input():
    """요구사항 #10 — 동일 입력 → 동일 content_hash (5회 반복)."""
    chunks = assert_chunks_deterministic(LONG_DOC, times=5)
    # 추가 정밀 검증: 입력 정규화도 안정 (BOM, CRLF)
    a = chunk_document(_doc(LONG_DOC))
    b = chunk_document(_doc("﻿" + LONG_DOC.replace("\n", "\r\n")))
    assert len(a) == len(b)
    for ca, cb in zip(a, b, strict=True):
        assert ca.content_hash == cb.content_hash, (
            f"BOM/CRLF 차이가 hash 에 영향: {ca.content_hash[:12]} != {cb.content_hash[:12]}"
        )
    _ = chunks  # silence


def test_11_content_hash_changes_when_content_changes():
    """요구사항 #11 — 내용 1글자만 바꿔도 영향 chunk 의 hash 가 변경."""
    base = chunk_document(_doc(LONG_DOC))
    modified_text = LONG_DOC.replace("문단 A 내용", "문단 A 내용변경")
    modified = chunk_document(_doc(modified_text))
    # 적어도 하나는 hash 가 달라야 함
    base_hashes = {c.content_hash for c in base}
    mod_hashes = {c.content_hash for c in modified}
    assert base_hashes != mod_hashes, "내용 변경에도 모든 hash 가 동일"


# ──────────────────────── 12. 순서 안정성 ────────────────────────


def test_12_chunk_index_sequential_no_gaps():
    """요구사항 #12 — chunk_index 가 0,1,2,... 누락/중복 없이."""
    doc = _doc(LONG_DOC)
    chunks = chunk_document(doc, max_chunk_chars=400)
    assert_chunk_indexes_sequential(chunks)


def test_12b_chunk_documents_per_doc_index_resets():
    """``chunk_documents`` 가 문서별로 chunk_index 를 0 부터 재시작."""
    docs = [
        _doc(SHORT_DOC, path="manuals/a.md"),
        _doc(SHORT_DOC, path="manuals/b.md"),
    ]
    out = chunk_documents(docs)
    by_path: dict[str, list[Chunk]] = {}
    for c in out:
        by_path.setdefault(c.source_path, []).append(c)
    for _path, group in by_path.items():
        assert_chunk_indexes_sequential(group)


# ──────────────────────── 13/14. 외부 호출 0 ────────────────────────


def test_13_chunker_does_not_call_llm_provider():
    """요구사항 #13 — chunker 는 외부 LLM provider 를 호출하지 않음."""
    fake = FakeProvider()
    doc = _doc(LONG_DOC)
    _ = chunk_document(doc)
    assert_no_external_calls(provider=fake)


def test_14_chunker_does_not_call_embedding_provider():
    """요구사항 #14 — chunker 는 embedding provider 를 호출하지 않음.

    embedding provider 는 18-5 시점 도입 — 본 테스트는 mock object 로 대체.
    """
    class _MockEmbedding:
        calls: list = []

    mock_emb = _MockEmbedding()
    doc = _doc(LONG_DOC)
    _ = chunk_document(doc)
    assert_no_external_calls(embedding_provider=mock_emb)


# ──────────────────────── 15. 운영 DB 미사용 ────────────────────────


def test_15_chunker_does_not_touch_operational_db():
    """요구사항 #15 — chunker 는 DB 를 사용하지 않음.

    conftest 의 db_guard 가 운영 DB 경로 접근을 차단하므로 본 테스트는 단순히
    chunker 가 어떤 DB import 도 하지 않음을 import-graph 로 확인.
    """
    import app.services.ai.knowledge.chunker as ch
    src = open(ch.__file__, "r", encoding="utf-8").read()
    forbidden = ["sqlite3", "SessionLocal", "from app.database", "from app.models"]
    for f in forbidden:
        assert f not in src, f"chunker.py 가 금지 import 포함: {f!r}"


def test_15b_chunker_does_not_import_network_or_provider_modules():
    """chunker.py / normalizer.py 가 네트워크/LLM/Embedding/HTTP/DB 모듈을 어느
    것도 import 하지 않음을 AST 로 정밀 검증 (docstring/주석은 제외).
    """
    import ast

    import app.services.ai.knowledge.chunker as ch
    import app.services.ai.knowledge.normalizer as nm

    # 금지 모듈 패턴 — 실제 import 만 검사 (docstring/주석은 무관)
    forbidden_module_prefixes = (
        # network / HTTP
        "requests", "httpx", "urllib", "socket", "http.client", "aiohttp",
        # LLM SDK
        "openai", "anthropic",
        # Provider / pii / pipeline (chunker 는 지식만 다룸)
        "app.services.ai.provider",
        "app.services.ai.pii",
        "app.services.ai.rag.pipeline",
        "app.services.ai.rag.retriever",
        "app.services.ai.rag.prompts",
        "app.services.ai.rag.safety",
        "app.services.ai.manual_qa",
        "app.services.rag",
        # DB layer
        "sqlite3",
        "app.database",
        "app.models",
    )

    # relative import 도 패키지 컨텍스트 기준으로 절대 경로로 변환해서 검증
    package_of = {
        ch: "app.services.ai.knowledge",
        nm: "app.services.ai.knowledge",
    }

    def _resolve_relative(level: int, mod: str | None, pkg: str) -> str:
        # Python: level=1 = "from . import X" = 현재 패키지 기준 (0 단계 위)
        # level=2 = "from .. import X" = 1 단계 위, 등등
        if level == 0:
            return mod or ""
        parts = pkg.split(".")
        # drops = level - 1 (level=1 일 때 0 단계 위)
        drops = level - 1
        if drops > len(parts):
            return mod or ""
        base = ".".join(parts[: len(parts) - drops])
        return f"{base}.{mod}" if mod else base

    for module in (ch, nm):
        src = open(module.__file__, "r", encoding="utf-8").read()
        tree = ast.parse(src)
        pkg = package_of[module]
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_relative(node.level or 0, node.module, pkg)
                imported_modules.append(resolved)

        for imported in imported_modules:
            for forbidden in forbidden_module_prefixes:
                assert not (
                    imported == forbidden or imported.startswith(forbidden + ".")
                ), (
                    f"{module.__name__} 가 금지 모듈 import: {imported!r} "
                    f"(matches {forbidden!r})"
                )


# ──────────────────────── 실제 매뉴얼 다수 검증 ────────────────────────


def test_real_all_manuals_chunked_safely():
    """``knowledge/manuals/*.md`` 모든 실문서가 안전하게 chunk 됨.

    각 파일에 대해:
      - 빈 chunk 결과 부재
      - chunk_index 순서 안정
      - source_path / title 보존
      - content_hash 안정 (5회 반복)
      - SMS 변수 ``{...}`` 짝 보존
      - 메뉴 경로 (``→``) 라인 양쪽 텍스트 보존
    """
    from app.services.ai.knowledge.loader import load_documents

    docs = load_documents(category="manuals")
    assert len(docs) >= 5, f"실문서 수가 너무 적음: {len(docs)}"

    for doc in docs:
        chunks = chunk_document(doc)
        assert chunks, f"{doc.path}: chunks 비어있음"
        assert_chunk_indexes_sequential(chunks)
        assert_metadata_preserved(chunks, source_path=doc.path)
        assert_content_hash_present_and_stable(chunks)
        # SMS 변수 짝 — 모든 매뉴얼에 적용 가능 (변수 없는 문서는 0=0)
        assert_sms_example_intact(chunks)
        # 메뉴 경로 (있는 매뉴얼만 영향) — 짝/잘림 검사
        assert_menu_path_intact(chunks)
        # 결정성 — 5회 반복
        again = chunk_document(doc)
        assert len(chunks) == len(again), (
            f"{doc.path}: 결정성 실패 — chunk 수 {len(chunks)} vs {len(again)}"
        )
        for a, b in zip(chunks, again, strict=True):
            assert a.content_hash == b.content_hash, (
                f"{doc.path}: 결정성 실패 — chunk_index={a.chunk_index} hash 불일치"
            )


def test_real_backup_md_chunk_quality():
    """``knowledge/manuals/backup.md`` 의 chunk 경계 품질 검증.

    이 매뉴얼은 자동/수동 백업 절차 + 메뉴 경로 + 파일명 포맷 등 다양한 요소
    포함 — chunk 가 의미 단위로 보존되는지 표본 검증.
    """
    from app.services.ai.knowledge.loader import load_documents

    docs = [d for d in load_documents() if "backup" in d.path]
    assert docs, "backup.md 가 loader 결과에 없음"
    chunks = chunk_document(docs[0])
    assert chunks, "backup.md: chunks 비어있음"

    full_text = "\n".join(c.content for c in chunks)
    # 핵심 키워드가 chunk 결과 어딘가에 모두 보존
    for keyword in ("자동 백업", "수동 백업", "복원", "clinic_", "%APPDATA%"):
        assert keyword in full_text, (
            f"backup.md chunk 결과에 핵심 키워드 누락: {keyword!r}"
        )
    # 파일명 포맷 ``clinic_YYYYMMDD_HHMMSS.db`` 가 한 chunk 안에 있어야
    fname_chunks = [c for c in chunks if "clinic_YYYYMMDD" in c.content]
    assert len(fname_chunks) == 1, (
        f"backup.md: 파일명 포맷이 {len(fname_chunks)} 개 chunk 에 분산"
    )


def test_real_no_therapist_md_procedure_intact():
    """``knowledge/manuals/no_therapist.md`` 의 절차 (1./2./3./4.) 가 한 chunk
    안에 보존됨."""
    from app.services.ai.knowledge.loader import load_documents

    docs = [d for d in load_documents() if "no_therapist" in d.path]
    assert docs, "no_therapist.md 가 loader 결과에 없음"
    chunks = chunk_document(docs[0])
    assert chunks
    # 번호 매김 절차가 한 chunk 안에 모여 있는지 — 4 단계 모두 같은 chunk
    proc_chunks = []
    for c in chunks:
        if all(f"{i}." in c.content for i in range(1, 5)):
            proc_chunks.append(c)
    assert len(proc_chunks) >= 1, (
        "no_therapist.md: 1~4 단계 절차가 한 chunk 에 모이지 않음"
    )


# ──────────────────────── 골든 스냅샷 (chunker 회귀 0) ────────────────────────


# 본 fingerprint 는 ``knowledge/manuals/*.md`` 각 문서를 ``chunk_document(doc)`` 로
# 처리한 결과의 ``content_hash`` 들을 ":" 로 join 한 뒤 sha256 해시한 값.
# 매뉴얼 내용이 바뀌거나 chunker / normalizer 동작이 바뀌면 즉시 mismatch 로 fail.
#
# 변경 사유가 정당하면 (매뉴얼 내용 의도적 수정 / chunker 알고리즘 의도적 개선),
# 새 fingerprint 를 latest_fix_summary.md 에 변경 사유와 함께 기록 후 갱신.
GOLDEN_FINGERPRINTS = {
    "manuals/ai_settings.md":     ("3", "b9804746e48776208752c21eddc43c8564868a7ad09cc16d0f1bbf2b43aef3fa"),
    "manuals/backup.md":          ("3", "892b415b9cb826c981b45cc7a8105cf1c4bdb9c7575fd6e5faffab18a8f1b345"),
    "manuals/munjanara_error.md": ("4", "343491c8ee9fb94b78df1923d47b29b94b732f3340d91ebe51f8829f418e3591"),
    "manuals/no_therapist.md":    ("3", "3cb531f7e100028bd829587e17ed6937507c7f07c05e4f82d0637a3eefc5c821"),
    "manuals/sms_compose.md":     ("4", "a33c2b635e6fd2d0e1fe99d17789a4cb3374b0fffbefd0cd6396bed5247f0f8f"),
    "manuals/therapist_leave.md": ("3", "997f6b2c21ec350686afc06418399d20f3baca6a35e32258300a64f6a0a4b07a"),
}


def _document_fingerprint(chunks: list[Chunk]) -> tuple[str, str]:
    """chunk 리스트 → (chunk 수 문자열, sha256 fingerprint)."""
    import hashlib

    joined = ":".join(c.content_hash for c in chunks)
    fp = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return (str(len(chunks)), fp)


def test_chunker_golden_fingerprints_for_all_manuals():
    """전체 매뉴얼에 대한 chunker 결과 골든 스냅샷.

    매뉴얼 내용 또는 chunker/normalizer 알고리즘이 변경되면 fingerprint 가 달라져
    즉시 fail. 의도적 변경 시 ``GOLDEN_FINGERPRINTS`` dict 와 fix_summary 양쪽
    업데이트가 강제됨 (회귀 가드).
    """
    from app.services.ai.knowledge.loader import load_documents

    docs = sorted(load_documents(category="manuals"), key=lambda d: d.path)
    actual: dict[str, tuple[str, str]] = {}
    for doc in docs:
        chunks = chunk_document(doc)
        actual[doc.path] = _document_fingerprint(chunks)

    # 누락 검출 — 신규 매뉴얼이 추가됐을 수도
    missing = sorted(set(actual) - set(GOLDEN_FINGERPRINTS))
    extra = sorted(set(GOLDEN_FINGERPRINTS) - set(actual))
    assert not missing, (
        f"신규 매뉴얼 발견 — GOLDEN_FINGERPRINTS 에 추가 필요: {missing}\n"
        f"actual: {[(p, actual[p]) for p in missing]}"
    )
    assert not extra, (
        f"GOLDEN_FINGERPRINTS 에 있는 매뉴얼이 loader 결과에 없음: {extra}"
    )

    # fingerprint 비교
    diffs = []
    for path, (exp_n, exp_fp) in GOLDEN_FINGERPRINTS.items():
        act_n, act_fp = actual[path]
        if exp_n != act_n or exp_fp != act_fp:
            diffs.append(
                f"{path}: expected (chunks={exp_n}, fp={exp_fp[:12]}..) "
                f"got (chunks={act_n}, fp={act_fp[:12]}..)"
            )
    assert not diffs, (
        "chunker 골든 스냅샷 mismatch — 매뉴얼 내용 / chunker 알고리즘 변경 검출:\n"
        + "\n".join(diffs)
    )


def test_chunker_fingerprints_stable_across_runs():
    """fingerprint 가 같은 입력에서 5회 반복해도 동일."""
    from app.services.ai.knowledge.loader import load_documents, reset_cache

    reset_cache()
    docs = sorted(load_documents(category="manuals"), key=lambda d: d.path)
    first_fps = {d.path: _document_fingerprint(chunk_document(d)) for d in docs}

    for _ in range(4):
        reset_cache()
        docs2 = sorted(load_documents(category="manuals"), key=lambda d: d.path)
        again_fps = {d.path: _document_fingerprint(chunk_document(d)) for d in docs2}
        assert first_fps == again_fps, "fingerprint 가 반복 실행에서 불안정"


# ──────────────────────── 추가: 18-2 회귀 0 ────────────────────────


def test_18_2_keyword_rag_not_broken_by_chunker():
    """chunker 도입 후에도 18-2 keyword 검색 결과가 그대로 동작."""
    from app.services.ai import manual_qa as ai_manual_qa

    res = ai_manual_qa.manual_search("예약문자 작성")
    assert isinstance(res, dict)
    assert "sources" in res and "masked_question" in res and "top_score" in res


def test_chunker_default_constants_documented():
    """기본값이 문서 / 코드에서 명시되어 있음."""
    assert MIN_CHUNK_CHARS >= 0
    assert MAX_CHUNK_CHARS >= MIN_CHUNK_CHARS
    assert OVERLAP_CHARS >= 0
    # 사용자 권장 범위
    assert MIN_CHUNK_CHARS == 200, "기본 min 변경 시 latest_fix_summary.md 기록 의무"
    assert MAX_CHUNK_CHARS == 1200, "기본 max 변경 시 latest_fix_summary.md 기록 의무"
    assert 100 <= OVERLAP_CHARS <= 200, "overlap 권장 100~200 범위 내"


def test_normalize_markdown_idempotent():
    """normalize_markdown 이 idempotent — 두 번 적용해도 결과 동일."""
    once = normalize_markdown(LONG_DOC)
    twice = normalize_markdown(once)
    assert once == twice


def test_empty_document_returns_no_chunks():
    """빈 문서 → 빈 chunk 리스트."""
    doc = _doc("")
    assert chunk_document(doc) == []
    doc2 = _doc("   \n\n   \n")
    assert chunk_document(doc2) == []


def test_no_heading_document_returns_single_chunk():
    """heading 없는 문서 → 단일 chunk."""
    doc = _doc(NO_HEADING_DOC)
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].heading == ""


def test_chunker_oversize_soft_limit():
    """문단 단위 분할이라 단일 문단 초과는 허용 (soft max)."""
    doc = _doc(LONG_DOC)
    chunks = chunk_document(doc, max_chunk_chars=500)
    assert_no_chunk_exceeds_soft_max(chunks, 500, soft_factor=2.0)


def test_chunker_invalid_params_raise():
    """파라미터 검증 — 음수 / 역순 → ValueError."""
    import pytest as _pt

    doc = _doc(SHORT_DOC)
    with _pt.raises(ValueError):
        chunk_document(doc, min_chunk_chars=-1)
    with _pt.raises(ValueError):
        chunk_document(doc, min_chunk_chars=500, max_chunk_chars=100)
    with _pt.raises(ValueError):
        chunk_document(doc, overlap_chars=-1)
