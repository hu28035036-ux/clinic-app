"""Anthropic (Claude) Provider 구현 (lazy import).

SDK 가 미설치인 환경에서도 이 모듈 자체는 import 가능해야 함.
실제 anthropic 패키지 import 는 generate() 호출 시점.

이 단계에서는 라우터가 호출하지 않으므로 generate() 는 골격만.
"""
from __future__ import annotations
import time

from .provider import AiProvider, AiResult, AiUnavailable


class AnthropicProvider(AiProvider):
    name = "anthropic"

    def _load_sdk(self):
        try:
            import anthropic  # noqa: F401
            return anthropic
        except Exception as e:
            raise AiUnavailable(
                "sdk_missing",
                f"anthropic SDK 가 설치돼 있지 않습니다 (pip install anthropic). 원인: {e}",
            )

    def generate(self, prompt: str, system: str = "") -> AiResult:
        if not self.api_key:
            raise AiUnavailable("no_api_key", "Anthropic API key 가 설정되지 않았습니다.")
        if not self.model:
            raise AiUnavailable("no_model", "Anthropic 모델명이 비어 있습니다.")

        anthropic = self._load_sdk()
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = anthropic.Anthropic(**kwargs)

        t0 = time.time()
        msg = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        _ = int((time.time() - t0) * 1000)

        # anthropic 응답: msg.content 는 블록 리스트 — text 블록만 합치기
        parts = []
        for block in (msg.content or []):
            t = getattr(block, "text", None)
            if t:
                parts.append(t)
        text = "".join(parts).strip()
        usage = getattr(msg, "usage", None)
        pt = getattr(usage, "input_tokens", 0) if usage else 0
        ct = getattr(usage, "output_tokens", 0) if usage else 0
        return AiResult(text=text, prompt_tokens=pt, completion_tokens=ct)
