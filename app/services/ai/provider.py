"""AI Provider 추상 인터페이스 + 팩토리 (v1.3 단계 1).

구조:
    AiProvider          : 모든 백엔드가 구현해야 하는 추상 클래스
    AiUnavailable       : SDK 미설치/키 미설정 등 호출 불가 상태
    AiPiiBlocked        : pii_guard 가 외부 전송을 차단했을 때
    get_provider(name)  : 이름→Provider 인스턴스 (지연 import)

지원 provider:
    - openai     : openai_client.OpenAIProvider
    - anthropic  : anthropic_client.AnthropicProvider
    - local      : v2 보류 (선택지만 등록, 호출 시 AiUnavailable)

이 단계에서는 라우터가 provider 를 실제로 호출하지 않음 — 골격만.
실제 generate() 호출은 다음 세션에서 sms_suggest 등을 만들 때 연결.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


class AiUnavailable(RuntimeError):
    """Provider 가 호출 가능한 상태가 아님 (SDK 미설치, 키 미설정 등)."""
    def __init__(self, kind: str, message: str = ""):
        super().__init__(message or kind)
        self.kind = kind  # 'sdk_missing' | 'no_api_key' | 'disabled' | 'unknown_provider'


class AiPiiBlocked(RuntimeError):
    """PII 가드가 외부 전송을 차단했을 때."""
    def __init__(self, fields: list[str]):
        super().__init__(f"PII fields blocked: {', '.join(fields)}")
        self.fields = fields


@dataclass
class AiResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: Optional[dict] = None


class AiProvider:
    """모든 LLM 백엔드가 구현해야 하는 인터페이스.

    구현체는 generate(prompt, system, ...) 에서 외부 LLM 호출.
    호출 전에 라우터/서비스 레이어에서 pii.sanitize() 를 통과시킬 책임.
    """
    name: str = "abstract"

    def __init__(self, model: str, api_key: str, base_url: str = "",
                 max_tokens: int = 512, temperature: float = 0.3):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature

    def is_ready(self) -> bool:
        """SDK 임포트 가능 + 필수 설정(api_key/model) 채워졌는지."""
        return bool(self.api_key and self.model)

    def generate(self, prompt: str, system: str = "") -> AiResult:
        raise NotImplementedError


# ────────── 팩토리 ──────────

KNOWN_PROVIDERS = ("openai", "anthropic", "local")


def list_known_providers() -> list[str]:
    return list(KNOWN_PROVIDERS)


def get_provider(name: str, *, model: str, api_key: str,
                 base_url: str = "", max_tokens: int = 512,
                 temperature: float = 0.3) -> AiProvider:
    """이름→Provider 인스턴스 생성.

    SDK import 는 각 client 모듈 안에서 lazy 로 일어남 — 이 함수 자체는
    실패하지 않는다. 실제 generate() 호출 시 SDK 미설치라면 AiUnavailable.
    """
    n = (name or "").strip().lower()
    if n == "openai":
        from .openai_client import OpenAIProvider
        return OpenAIProvider(model=model, api_key=api_key,
                              base_url=base_url, max_tokens=max_tokens,
                              temperature=temperature)
    if n == "anthropic":
        from .anthropic_client import AnthropicProvider
        return AnthropicProvider(model=model, api_key=api_key,
                                 base_url=base_url, max_tokens=max_tokens,
                                 temperature=temperature)
    if n == "local":
        # v2 보류 — 선택지로만 노출. 실제 호출 시도하면 AiUnavailable.
        return _LocalStubProvider(model=model, api_key=api_key,
                                  base_url=base_url, max_tokens=max_tokens,
                                  temperature=temperature)
    raise AiUnavailable("unknown_provider", f"unknown provider: {name!r}")


class _LocalStubProvider(AiProvider):
    """로컬 LLM (ollama 등) — v2 까지 비활성. 호출 시 명시적 에러."""
    name = "local"

    def is_ready(self) -> bool:
        return False

    def generate(self, prompt: str, system: str = "") -> AiResult:
        raise AiUnavailable("disabled",
                            "local provider 는 v2 에서 지원 예정입니다.")
