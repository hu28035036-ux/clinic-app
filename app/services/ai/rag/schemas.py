"""RAG 공용 schemas — 18-2 keyword 분리 + 18-3 chunker.

v1.3.3 ``/api/ai/manual/{search,ask}`` 응답 키 후방호환을 코드에서 보장
하기 위한 dataclass 와 reason_code 상수.

세션 이력:
  - 18-1: ``Source`` / ``Document`` / ``Chunk`` / ``Answer`` 골격 + 29개 reason_code.
  - 18-2: ``Chunk`` / ``Answer.embedding_called`` / ``REASON_VECTOR_DISABLED`` /
    ``REASON_EMBEDDING_SKIPPED_*`` 5개 제거 (18-2 keyword 분리 스코프 엄격화).
  - 18-3: ``Chunk`` 단독 재도입 (chunker 산출물 dataclass). embedding/vector
    관련 항목은 여전히 부재 (18-5 도입 예정).

후방호환 (``docs/ai_rag_current_state.md`` §3):
  - ``Source`` 의 키는 v1.3.3 응답 ``sources[]`` 항목 키와 1:1 매핑
    (``title`` / ``path`` / ``snippet``)
  - ``Answer`` 의 9개 필수 필드는 v1.3.3 manual/ask 응답 키와 1:1
  - 신규 optional 필드는 v1.3.3 응답에는 없으나, 18-3 이후 점진 추가

reason_code 상수 (``docs/ai_rag_error_codes.md`` §1~§4):
  - 29개 정의 (§1 RAG/Safety/Provider 11 + §2 LLM skip 10 + §4 Provider 별칭 2
    + §1-8/§3 Embedding skip 6).
  - 18-5 시점에 vector / embedding 관련 6개 추가 (REASON_VECTOR_DISABLED +
    REASON_EMBEDDING_SKIPPED_*).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ──────────────────────── reason_code 상수 (총 29개) ────────────────────────
#
# 본 상수는 응답 JSON 의 optional ``reason_code`` 와 ``AiUsageLog`` 의 신규
# 컬럼(m014 시점에 도입 예정) 양쪽에서 사용한다. 다른 별칭 사용 금지.
# 18-5 에서 vector / embedding 관련 6개 추가됨.

# §1. 기본 reason_code (RAG / Safety / Provider 공통) — 11개
REASON_NO_SOURCES = "no_sources"
REASON_LOW_CONFIDENCE = "low_confidence"
REASON_PII_DETECTED = "pii_detected"
REASON_UNSUPPORTED_QUESTION = "unsupported_question"
REASON_UNKNOWN_FEATURE = "unknown_feature"
REASON_PROVIDER_DISABLED = "provider_disabled"
REASON_PROVIDER_ERROR = "provider_error"
REASON_REINDEX_IN_PROGRESS = "reindex_in_progress"
REASON_INVALID_QUERY = "invalid_query"
REASON_TIMEOUT = "timeout"
REASON_INTERNAL_ERROR = "internal_error"

# §2. LLM 호출 skip reason_code — 10개
REASON_LLM_SKIPPED_LOCAL_ONLY = "llm_skipped_local_only"
REASON_LLM_SKIPPED_LOCAL_ANSWER = "llm_skipped_local_answer"
REASON_LLM_SKIPPED_KEYWORD_ONLY = "llm_skipped_keyword_only"
REASON_LLM_SKIPPED_DB_ANSWER = "llm_skipped_db_answer"
REASON_LLM_SKIPPED_RULE_BASED = "llm_skipped_rule_based"
REASON_LLM_SKIPPED_NO_SOURCES = "llm_skipped_no_sources"
REASON_LLM_SKIPPED_LOW_CONFIDENCE = "llm_skipped_low_confidence"
REASON_LLM_SKIPPED_PII = "llm_skipped_pii"
REASON_LLM_SKIPPED_UNKNOWN_FEATURE = "llm_skipped_unknown_feature"
REASON_LLM_SKIPPED_INVALID_QUERY = "llm_skipped_invalid_query"

# §4. Provider reason_code (별칭) — 2개
REASON_PROVIDER_API_KEY_MISSING = "provider_api_key_missing"
REASON_EXTERNAL_API_NOT_ALLOWED = "external_api_not_allowed"

# §3 Embedding skip reason_code — 18-5 vector/embedding 도입 시 추가 (총 6개).
# docs/ai_rag_error_codes.md §1-8 + §3-1~§3-5 + 우선순위(§5).
# 본 시점에는 indexer 의 ReindexResult.vector_disabled_reason 과 vector
# 모듈에서 사용. AiUsageLog 컬럼 추가는 18-7 admin/router m014 시점.
REASON_VECTOR_DISABLED = "vector_disabled"
REASON_EMBEDDING_SKIPPED_LOCAL_ONLY = "embedding_skipped_local_only"
REASON_EMBEDDING_SKIPPED_SAME_HASH = "embedding_skipped_same_hash"
REASON_EMBEDDING_SKIPPED_SHORT_QUERY = "embedding_skipped_short_query"
REASON_EMBEDDING_SKIPPED_DISABLED = "embedding_skipped_disabled"
REASON_EMBEDDING_SKIPPED_API_KEY_MISSING = "embedding_skipped_api_key_missing"

ALL_REASON_CODES: tuple[str, ...] = (
    REASON_NO_SOURCES,
    REASON_LOW_CONFIDENCE,
    REASON_PII_DETECTED,
    REASON_UNSUPPORTED_QUESTION,
    REASON_UNKNOWN_FEATURE,
    REASON_PROVIDER_DISABLED,
    REASON_PROVIDER_ERROR,
    REASON_REINDEX_IN_PROGRESS,
    REASON_INVALID_QUERY,
    REASON_TIMEOUT,
    REASON_INTERNAL_ERROR,
    REASON_LLM_SKIPPED_LOCAL_ONLY,
    REASON_LLM_SKIPPED_LOCAL_ANSWER,
    REASON_LLM_SKIPPED_KEYWORD_ONLY,
    REASON_LLM_SKIPPED_DB_ANSWER,
    REASON_LLM_SKIPPED_RULE_BASED,
    REASON_LLM_SKIPPED_NO_SOURCES,
    REASON_LLM_SKIPPED_LOW_CONFIDENCE,
    REASON_LLM_SKIPPED_PII,
    REASON_LLM_SKIPPED_UNKNOWN_FEATURE,
    REASON_LLM_SKIPPED_INVALID_QUERY,
    REASON_PROVIDER_API_KEY_MISSING,
    REASON_EXTERNAL_API_NOT_ALLOWED,
    # 18-5 vector/embedding 6개
    REASON_VECTOR_DISABLED,
    REASON_EMBEDDING_SKIPPED_LOCAL_ONLY,
    REASON_EMBEDDING_SKIPPED_SAME_HASH,
    REASON_EMBEDDING_SKIPPED_SHORT_QUERY,
    REASON_EMBEDDING_SKIPPED_DISABLED,
    REASON_EMBEDDING_SKIPPED_API_KEY_MISSING,
)

# AI 모드 (``docs/ai_rag_architecture_plan.md`` §9)
AI_MODE_LOCAL_ONLY = "local_only"
AI_MODE_LOCAL_FIRST = "local_first"
AI_MODE_AI_ASSIST = "ai_assist"
ALL_AI_MODES: tuple[str, ...] = (
    AI_MODE_LOCAL_ONLY,
    AI_MODE_LOCAL_FIRST,
    AI_MODE_AI_ASSIST,
)

# Confidence (``manual_qa._confidence_for`` 와 호환 — high/low/unknown)
CONFIDENCE_HIGH = "high"
CONFIDENCE_LOW = "low"
CONFIDENCE_UNKNOWN = "unknown"
ALL_CONFIDENCE: tuple[str, ...] = (CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_UNKNOWN)


# ──────────────────────── dataclass ────────────────────────


@dataclass(frozen=True)
class Source:
    """v1.3.3 ``sources[]`` 항목 키와 1:1.

    프론트(``app/templates/main.html:5787-5793``)는 ``s.title`` / ``s.path``
    만 사용하지만, ``snippet`` 도 v1.3.3 응답에 항상 포함된다.
    """
    title: str
    path: str
    snippet: str = ""


@dataclass
class Document:
    """원본 문서 — keyword 검색 / chunker 입력 단위."""
    path: str
    category: str            # "manuals" | "sms_guides" 등
    raw_text: str
    content_hash: str = ""
    mtime: float = 0.0


@dataclass
class Chunk:
    """청크 — 18-3 chunker 산출물 (in-memory only).

    필드는 18-4 ``knowledge_chunks`` 테이블 스키마와 정렬되어 있으나, 18-3
    시점에는 DB 영속화하지 않는다 (chunker는 순수 함수).

    필수 보존 (18-3 요구사항 #8):
      ``source_path``, ``title``, ``heading``, ``section_path``, ``chunk_index``.

    ``content_hash`` 는 ``content`` 만 sha256 해시 — chunk 위치/메타에 의존
    하지 않는 안정 식별자 (요구사항 #10/11).
    """
    doc_id: str = ""           # sha1(source_path)
    source_path: str = ""      # knowledge/<category>/<file>.md (relative)
    category: str = ""         # "manuals" | "sms_guides"
    title: str = ""            # 문서 제목 (첫 h1)
    heading: str = ""          # chunk 가 속한 가장 가까운 heading 텍스트
    section_path: str = ""     # "h1 > h2 > h3" 형태
    chunk_index: int = 0       # 문서 내 0-based 인덱스 (요구사항 #12 안정성)
    content: str = ""          # 실제 chunk 내용 (heading 라인 포함)
    content_hash: str = ""     # sha256(content) hex 64자 — 요구사항 #9~11
    token_count: int = 0       # 한국어 글자 수 기준 (len(content))
    tags: str = ""             # csv 형식 (현재 빈 값, 18-4 이후 채움)
    document_version: str = "" # reindex 추적 (18-4 이후 사용)


@dataclass
class Answer:
    """RAG pipeline 응답.

    필수 9개 필드는 v1.3.3 ``manual/ask`` 응답 키와 1:1 (``manual_qa.py:270-280``).
    optional 4개 필드는 18-3 이후 점진 도입 (``docs/ai_rag_error_codes.md`` §6).
    ``embedding_called`` 는 18-5 vector/embedding 도입 시점에 다시 추가.
    """
    # ── 필수 9개 (v1.3.3 후방호환) ──
    answer: str
    sources: list[Source] = field(default_factory=list)
    confidence: str = CONFIDENCE_UNKNOWN  # high | low | unknown
    not_found: bool = False
    blocked: bool = False
    blocked_reason: str = ""
    guard_hits: int = 0
    top_score: int = 0
    masked_question: str = ""
    # ── 신규 optional (18-3 이후) ──
    reason_code: Optional[str] = None
    llm_called: Optional[bool] = None
    ai_mode: Optional[str] = None
    prompt_version: Optional[str] = None


__all__ = [
    # reason_code 상수
    "REASON_NO_SOURCES", "REASON_LOW_CONFIDENCE", "REASON_PII_DETECTED",
    "REASON_UNSUPPORTED_QUESTION", "REASON_UNKNOWN_FEATURE",
    "REASON_PROVIDER_DISABLED", "REASON_PROVIDER_ERROR",
    "REASON_REINDEX_IN_PROGRESS",
    "REASON_INVALID_QUERY", "REASON_TIMEOUT", "REASON_INTERNAL_ERROR",
    "REASON_LLM_SKIPPED_LOCAL_ONLY", "REASON_LLM_SKIPPED_LOCAL_ANSWER",
    "REASON_LLM_SKIPPED_KEYWORD_ONLY", "REASON_LLM_SKIPPED_DB_ANSWER",
    "REASON_LLM_SKIPPED_RULE_BASED", "REASON_LLM_SKIPPED_NO_SOURCES",
    "REASON_LLM_SKIPPED_LOW_CONFIDENCE", "REASON_LLM_SKIPPED_PII",
    "REASON_LLM_SKIPPED_UNKNOWN_FEATURE", "REASON_LLM_SKIPPED_INVALID_QUERY",
    "REASON_PROVIDER_API_KEY_MISSING", "REASON_EXTERNAL_API_NOT_ALLOWED",
    # 18-5 vector/embedding 6개
    "REASON_VECTOR_DISABLED",
    "REASON_EMBEDDING_SKIPPED_LOCAL_ONLY",
    "REASON_EMBEDDING_SKIPPED_SAME_HASH",
    "REASON_EMBEDDING_SKIPPED_SHORT_QUERY",
    "REASON_EMBEDDING_SKIPPED_DISABLED",
    "REASON_EMBEDDING_SKIPPED_API_KEY_MISSING",
    "ALL_REASON_CODES",
    # 모드/신뢰도
    "AI_MODE_LOCAL_ONLY", "AI_MODE_LOCAL_FIRST", "AI_MODE_AI_ASSIST",
    "ALL_AI_MODES",
    "CONFIDENCE_HIGH", "CONFIDENCE_LOW", "CONFIDENCE_UNKNOWN",
    "ALL_CONFIDENCE",
    # dataclass
    "Source", "Document", "Chunk", "Answer",
]
