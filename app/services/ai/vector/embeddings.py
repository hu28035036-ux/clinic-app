"""Embedding provider 추상 + FakeEmbeddingProvider + factory — 18-5.

설계 원칙 (docs/ai_rag_architecture_plan.md §3-17, §8, §11):
  1. Embedding 은 선택 기능 — 키워드 RAG 만으로도 동작해야 함 (Local-first).
  2. ``local_only`` 모드 / API key 없음 / disabled → factory 단계에서 인스턴스
     생성 자체를 차단 (``EmbeddingUnavailable`` raise).
  3. content_hash 동일 → 재생성 skip (store/indexer 책임).
  4. query 너무 짧음 / invalid → ``is_embeddable_query`` 가 False 반환 (호출 X).
  5. provider 오류 → 즉시 raise — indexer 가 catch 후 keyword fallback.
  6. 테스트는 100% ``FakeEmbeddingProvider``. 실제 외부 OpenAI/Anthropic
     embedding 호출 코드는 본 세션 범위 외 (NotImplementedError slot 만).

외부 호출 차단 layer:
  - ``tests/conftest.py:_block_sdk_modules`` — openai/anthropic SDK 클래스를
    RuntimeError 로 교체.
  - 본 모듈 factory — ``local_only`` 등 사전 차단.
  - 본 모듈에 실제 OpenAIEmbeddingProvider 구현 부재.

reason_code 매핑 (docs/ai_rag_error_codes.md §1-8, §3, §5):
  - ``mode == local_only``           → ``EmbeddingUnavailable(kind="local_only")``
  - ``allow_external == False``      → ``EmbeddingUnavailable(kind="disabled")``
  - api_key/provider 없음            → ``EmbeddingUnavailable(kind="api_key_missing")``
  - 미지원 provider                   → ``EmbeddingUnavailable(kind="unknown_provider")``
  - SDK 미설치 (외부 implementation) → ``EmbeddingUnavailable(kind="sdk_missing")``

ai_setting (선택 인자) — duck-typed:
  ``ai_setting.api_key``, ``ai_setting.provider`` 가 있으면 사용. 본 세션은
  실제 외부 호출이 없으므로 fake/Test fixture 도 dict-style 전달 가능.
"""
from __future__ import annotations

import hashlib
import math
import struct
from typing import Any, Optional

# ──────────────────────── 정책 상수 ────────────────────────

# 짧은 query / invalid query 차단 임계 (사용자 요구 #10/#11).
# 2자 미만 → embedding 생성 skip — 키워드 검색이 더 효과적인 영역.
QUERY_MIN_CHARS = 2

# FakeEmbeddingProvider 기본 dimension — 본 세션 단위 테스트 표준값.
DEFAULT_FAKE_DIMENSION = 16

# AI 모드 (rag.schemas 와 동일 값 — 순환 import 회피 위해 문자열 상수 재선언).
_MODE_LOCAL_ONLY = "local_only"
_MODE_LOCAL_FIRST = "local_first"
_MODE_AI_ASSIST = "ai_assist"
_VALID_MODES = (_MODE_LOCAL_ONLY, _MODE_LOCAL_FIRST, _MODE_AI_ASSIST)

# kind ↔ reason_code 매핑 (factory 호출자가 reason_code 발급 시 참조).
KIND_LOCAL_ONLY = "local_only"
KIND_DISABLED = "disabled"
KIND_API_KEY_MISSING = "api_key_missing"
KIND_UNKNOWN_PROVIDER = "unknown_provider"
KIND_SDK_MISSING = "sdk_missing"
KIND_PROVIDER_ERROR = "provider_error"

ALL_KINDS = (
    KIND_LOCAL_ONLY,
    KIND_DISABLED,
    KIND_API_KEY_MISSING,
    KIND_UNKNOWN_PROVIDER,
    KIND_SDK_MISSING,
    KIND_PROVIDER_ERROR,
)


# ──────────────────────── 예외 ────────────────────────


class EmbeddingUnavailable(Exception):
    """Embedding factory/provider 가 차단된 사유.

    ``kind`` 는 reason_code 매핑에 사용. ``message`` 는 안내용 — API key/원문
    개인정보 절대 포함 금지 (PII/secret 노출 방지).
    """

    def __init__(self, kind: str, message: str = ""):
        self.kind = kind
        self.message = message or kind
        super().__init__(f"[{kind}] {self.message}")


class VectorDimensionMismatch(ValueError):
    """저장된 vector 와 현재 provider 의 dimension 불일치.

    store 에서 발생 — content_hash 가 같아도 dimension 이 달라지면 안전 실패.
    indexer/retriever 가 catch 후 keyword fallback.
    """

    def __init__(self, expected: int, got: int, *, where: str = ""):
        self.expected = expected
        self.got = got
        self.where = where
        super().__init__(
            f"dimension mismatch{(' at ' + where) if where else ''}: "
            f"expected={expected}, got={got}"
        )


# ──────────────────────── 추상 ────────────────────────


class EmbeddingProvider:
    """추상 인터페이스 — 모든 embedding 구현체 공통.

    필드:
      ``name``      : provider 식별자 (예: ``"fake"``, ``"openai"``)
      ``model``     : 모델명 (예: ``"fake-embed-1"``)
      ``dimension`` : 출력 벡터 길이

    메서드:
      ``embed_documents(texts)`` : 다건 문서 임베딩 (indexer 용 — 배치)
      ``embed_query(text)``      : 단건 query 임베딩 (retriever 용)

    호출 관찰:
      ``self.calls`` (list) — 각 호출마다 ``{"texts": [...]}`` 또는
      ``{"text": ...}`` append. 테스트에서 ``len(provider.calls)`` 단언.
    """

    name: str = "abstract"
    model: str = ""
    dimension: int = 0

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


# ──────────────────────── 차단용 stub ────────────────────────


class _UnavailableEmbeddingProvider(EmbeddingProvider):
    """factory 가 차단 케이스에서 반환할 수도 있는 명시적 stub.

    호출 시 ``EmbeddingUnavailable`` raise — 실수로 호출되어도 외부 API 호출
    경로 자체가 부재함을 보장. 본 세션의 factory 는 이 stub 을 사용하지 않고
    raise 만 하지만, 18-7 에서 silent fallback 경로가 필요해질 수 있어 정의.
    """

    name = "unavailable"
    model = ""
    dimension = 0

    def __init__(self, kind: str = KIND_DISABLED):
        super().__init__()
        self._kind = kind

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append({"texts": list(texts)})
        raise EmbeddingUnavailable(self._kind, "embedding provider unavailable")

    def embed_query(self, text: str) -> list[float]:
        self.calls.append({"text": text})
        raise EmbeddingUnavailable(self._kind, "embedding provider unavailable")


# ──────────────────────── Fake (테스트 전용) ────────────────────────


class FakeEmbeddingProvider(EmbeddingProvider):
    """결정적 sha256 hash 기반 임베딩 — 외부 호출 0.

    동작:
      1. ``hashlib.sha256(text)`` digest (32 bytes).
      2. dimension 개의 4-byte 슬라이스로 split (dimension 이 8 초과면
         hash 를 반복 stretch).
      3. 각 슬라이스를 ``struct.unpack(">I", ...)`` → uint32 → 정규화하여
         [-1, 1] float 로 매핑.

    옵션:
      ``raise_on_call=True`` → ``embed_documents``/``embed_query`` 호출 시
      RuntimeError raise. ``local_only`` / disabled 케이스의 "호출 자체가
      안 일어났는지" 강건 검증용.

    호출 관찰 (사용자 요구 #2/#9 단언용):
      ``self.calls`` — 각 호출마다 ``{"texts": [...]}`` 또는 ``{"text": ...}``
      ``self.last_inputs`` (property) — 가장 최근 호출의 입력 (편의).

    PII 보호:
      입력 text 는 self.calls 에 그대로 보존된다. 본 클래스는 테스트 전용이며
      production 경로에서는 절대 사용되지 않는다 (factory 가 fake provider 는
      운영 모드에서 거부함). 테스트 입력은 hardcoded 한국어 manual 텍스트만
      사용 — 환자/실 PII 미포함.
    """

    name = "fake"

    def __init__(
        self,
        *,
        dimension: int = DEFAULT_FAKE_DIMENSION,
        model: str = "fake-embed-1",
        raise_on_call: bool = False,
    ):
        super().__init__()
        if dimension <= 0:
            raise ValueError(f"FakeEmbeddingProvider dimension must be > 0, got {dimension}")
        self.dimension = dimension
        self.model = model
        self.raise_on_call = raise_on_call

    @property
    def last_inputs(self) -> Optional[Any]:
        if not self.calls:
            return None
        c = self.calls[-1]
        if "texts" in c:
            return c["texts"]
        return c.get("text")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.raise_on_call:
            self.calls.append({"texts": list(texts)})
            raise RuntimeError("[FakeEmbeddingProvider raise_on_call] embed_documents called")
        self.calls.append({"texts": list(texts)})
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.raise_on_call:
            self.calls.append({"text": text})
            raise RuntimeError("[FakeEmbeddingProvider raise_on_call] embed_query called")
        self.calls.append({"text": text})
        return self._embed_one(text)

    # ── 내부 ──

    def _embed_one(self, text: str) -> list[float]:
        """결정적 vector 생성 — 같은 text → 같은 vector. 다른 text → 다른 vector."""
        if not isinstance(text, str):
            text = str(text)
        # dimension * 4 bytes 가 필요 — sha256 32B 만으로 부족하면 반복 hash chain.
        needed = self.dimension * 4
        buf = b""
        seed = text.encode("utf-8")
        i = 0
        while len(buf) < needed:
            buf += hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
            i += 1
        out: list[float] = []
        for k in range(self.dimension):
            chunk = buf[k * 4:(k + 1) * 4]
            (n,) = struct.unpack(">I", chunk)
            # uint32 → [-1, 1]
            v = (n / 0xFFFFFFFF) * 2.0 - 1.0
            out.append(v)
        # L2 정규화 (cosine similarity 안정성).
        norm = math.sqrt(sum(x * x for x in out))
        if norm > 0:
            out = [x / norm for x in out]
        return out


# ──────────────────────── helper ────────────────────────


def is_embeddable_query(text: Optional[str]) -> bool:
    """query 가 embedding 가치가 있는지 판정 (사용자 요구 #10/#11).

    False 시:
      - reason_code = ``REASON_EMBEDDING_SKIPPED_SHORT_QUERY``
      - keyword fallback 으로 진행
    """
    if text is None:
        return False
    if not isinstance(text, str):
        return False
    cleaned = text.strip()
    if len(cleaned) < QUERY_MIN_CHARS:
        return False
    return True


# ──────────────────────── factory ────────────────────────


def get_embedding_provider(
    *,
    ai_setting: Optional[Any] = None,
    mode: str = _MODE_LOCAL_FIRST,
    allow_external: bool = True,
    provider_name: Optional[str] = None,
    fake_dimension: int = DEFAULT_FAKE_DIMENSION,
) -> EmbeddingProvider:
    """Embedding provider factory — 차단 우선순위 (docs/ai_rag_error_codes.md §5).

    1. ``mode == "local_only"``    → ``EmbeddingUnavailable(kind="local_only")``.
       사용자 요구 #4 만족 — factory 가 인스턴스 자체를 만들지 않는다.
    2. ``allow_external == False`` → kind="disabled"
    3. provider_name 미지정 + ai_setting 의 provider 도 없음 → kind="unknown_provider"
    4. provider 가 외부 SDK 필요 (openai/anthropic) + api_key 없음 → kind="api_key_missing"
    5. provider == "fake"          → ``FakeEmbeddingProvider`` 반환 (테스트 hook)
    6. provider == "openai"|"anthropic" → 18-5 범위 외 — kind="sdk_missing" (slot)

    인자:
      ai_setting     : duck-typed. ``.api_key``, ``.provider`` 사용.
      mode           : "local_only" | "local_first" | "ai_assist"
      allow_external : ``AI_EXTERNAL_EMBEDDING_ENABLED`` 시뮬레이션
      provider_name  : 명시적 override (테스트가 ``"fake"`` 강제용)
      fake_dimension : provider == "fake" 일 때 dimension

    반환: ``EmbeddingProvider`` 인스턴스
    raise: ``EmbeddingUnavailable`` (kind 명시)
    """
    # 1. local_only — 가장 강한 차단
    if mode == _MODE_LOCAL_ONLY:
        raise EmbeddingUnavailable(KIND_LOCAL_ONLY, "local_only mode forbids embedding")

    # mode 검증 — 알 수 없는 모드는 disabled 로 안전 차단
    if mode not in _VALID_MODES:
        raise EmbeddingUnavailable(KIND_DISABLED, f"unknown mode: {mode}")

    # 2. allow_external == False
    if not allow_external:
        raise EmbeddingUnavailable(KIND_DISABLED, "external embedding disabled")

    # 3. provider 결정
    name: Optional[str] = provider_name
    if name is None and ai_setting is not None:
        name = getattr(ai_setting, "provider", None) or None
    if name is None:
        raise EmbeddingUnavailable(KIND_UNKNOWN_PROVIDER, "no embedding provider specified")

    # 5. fake provider — 테스트 전용
    if name == "fake":
        return FakeEmbeddingProvider(dimension=fake_dimension)

    # 4. 외부 SDK provider — api_key 검사
    api_key = getattr(ai_setting, "api_key", "") if ai_setting is not None else ""
    if not api_key:
        raise EmbeddingUnavailable(KIND_API_KEY_MISSING, f"api_key required for provider={name}")

    # 6. 외부 SDK 실제 구현은 본 세션 범위 외
    if name in ("openai", "anthropic"):
        raise EmbeddingUnavailable(
            KIND_SDK_MISSING,
            f"external embedding provider '{name}' not implemented in 18-5 (use 18-7+)",
        )

    raise EmbeddingUnavailable(KIND_UNKNOWN_PROVIDER, f"unknown provider: {name}")


# ──────────────────────── 안전 helper ────────────────────────


def safe_embed_documents(
    provider: EmbeddingProvider,
    texts: list[str],
) -> tuple[list[list[float]], Optional[Exception]]:
    """provider.embed_documents 를 안전 호출 — 예외 포착해 fallback 신호.

    반환:
      (vectors, None)  → 성공
      ([], exception)  → 실패 (indexer 가 keyword fallback)

    PII/원문 미노출 — 예외 메시지를 그대로 raise 하지 않고 caller 로 전달만 함.
    """
    if not texts:
        return [], None
    try:
        vectors = provider.embed_documents(texts)
    except Exception as e:  # noqa: BLE001 — fallback 정책상 광범위 catch
        return [], e
    if len(vectors) != len(texts):
        return [], EmbeddingUnavailable(
            KIND_PROVIDER_ERROR,
            f"provider returned {len(vectors)} vectors for {len(texts)} texts",
        )
    return vectors, None


__all__ = [
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "_UnavailableEmbeddingProvider",
    "EmbeddingUnavailable",
    "VectorDimensionMismatch",
    "get_embedding_provider",
    "is_embeddable_query",
    "safe_embed_documents",
    "QUERY_MIN_CHARS",
    "DEFAULT_FAKE_DIMENSION",
    "KIND_LOCAL_ONLY",
    "KIND_DISABLED",
    "KIND_API_KEY_MISSING",
    "KIND_UNKNOWN_PROVIDER",
    "KIND_SDK_MISSING",
    "KIND_PROVIDER_ERROR",
    "ALL_KINDS",
]
