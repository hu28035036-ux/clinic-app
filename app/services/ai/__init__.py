"""AI/RAG 공통 서비스 패키지 (v1.3 단계 1+2 통합).

구성:
    provider.py          — 추상 Provider 인터페이스 + 팩토리 (단계 1)
    openai_client.py     — OpenAI Provider 구현 (lazy import) (단계 1)
    anthropic_client.py  — Anthropic Provider 구현 (lazy import) (단계 1)
    pii.py               — 개인정보 마스킹/필터 (외부 LLM 전송 전 강제) (단계 1)
    prompts.py           — 시스템 프롬프트 / 컨텍스트 빌더 템플릿 (단계 1)
    validators.py        — 예약문자 발송 전 결정론적 검증 (단계 2, LLM 미사용)

원칙 (이 단계에서는 골격 + sms 검증만):
    - AI 는 절대 DB 를 수정하거나 SMS 를 발송하지 않는다.
    - 외부 LLM 호출 전 반드시 pii.sanitize() 를 거친다.
    - SDK (openai/anthropic) 는 lazy import — 미설치 환경에서도 앱 기동 OK.
    - validators 는 외부 LLM API 를 절대 호출하지 않는다 (결정론적 로직만).
"""

from .provider import (
    AiProvider,
    AiUnavailable,
    AiPiiBlocked,
    get_provider,
    list_known_providers,
)

__all__ = [
    "AiProvider",
    "AiUnavailable",
    "AiPiiBlocked",
    "get_provider",
    "list_known_providers",
]
