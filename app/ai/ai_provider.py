"""ai_provider — 외부 AI API provider 추상화 (Phase 1).

역할:
- 외부 AI API 호출부 (Anthropic / OpenAI / 로컬 LLM 교체 가능).
- API 키는 **환경변수 또는 관리자 설정** 에서 읽음 (코드 직접 저장 금지).
- 실패 시 안전한 에러 반환 — **기존 프로그램이 죽으면 안 됨** (AI_SAFETY_POLICY § 3.5).

주의:
- 본 모듈은 DB 직접 수정 금지.
- 기존 service 호출 안 함 (단순 외부 API 호출 + 에러 처리).
- 외부 AI API 에 환자 전체 / 생년월일 / 연락처 / 메모 / 진료내용 미전송
  (AI_SAFETY_POLICY § 3.2). 본 Phase 1 에서는 Mock 만 동작하므로 실제 전송 없음.
- 하네스: tests/test_ai_provider.py (Phase 6 풀세트), MockProvider 는 단위 테스트 가능.

cross-reference:
- AI_COMMAND_ARCHITECTURE.md § 2.2 / § 6 (provider 추상화)
- AI_CURRENT_DECISIONS.md § 11 (API 설계는 provider 가 외부 API 호출)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.ai.ai_command_schema import ParsedCommand, ParserContext


class ProviderError(Exception):
    """provider 호출 실패. 기존 프로그램은 본 예외를 잡고 정상 동작해야 함."""


@runtime_checkable
class AIProvider(Protocol):
    """provider 인터페이스 — Anthropic / OpenAI / Mock 모두 본 protocol 만족."""

    name: str

    def parse_command(
        self,
        raw_text: str,
        context: ParserContext,
    ) -> ParsedCommand:
        """자연어 명령 → 구조화 ParsedCommand.

        실패 시 ProviderError 발생. caller 는 잡고 fallback 처리.
        """
        ...


class MockProvider:
    """테스트 / 하네스 / API 키 부재 시 fallback provider.

    실제 외부 API 를 호출하지 않고 입력 raw_text 를 그대로 반환.
    intent / 환자명 등 추출 없음. parser / resolver 단위 테스트 시 사용.
    """

    name: str = "mock"

    def parse_command(
        self,
        raw_text: str,
        context: ParserContext,
    ) -> ParsedCommand:
        return ParsedCommand(raw_text=raw_text)


def get_default_provider() -> AIProvider:
    """현재 환경의 기본 provider 반환.

    Phase 1 에서는 항상 MockProvider 반환 (실제 parser 는 Phase 2 부터).
    Phase 2 이후 환경변수 / 관리자 설정으로 Anthropic / OpenAI 전환.
    """
    return MockProvider()
