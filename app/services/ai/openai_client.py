"""OpenAI Provider 구현 (lazy import).

SDK 가 미설치인 환경에서도 이 모듈 자체는 import 가능해야 함 →
실제 openai 패키지 import 는 generate() 호출 시점에만.

이 단계에서는 라우터가 호출하지 않으므로 generate() 는 골격만.
실제 호출 (sms_suggest 등) 은 다음 세션에서 연결.
"""
from __future__ import annotations
import time

from .provider import AiProvider, AiResult, AiUnavailable


class OpenAIProvider(AiProvider):
    name = "openai"

    def _load_sdk(self):
        try:
            import openai  # noqa: F401
            return openai
        except Exception as e:
            raise AiUnavailable(
                "sdk_missing",
                f"openai SDK 가 설치돼 있지 않습니다 (pip install openai). 원인: {e}",
            )

    def generate(self, prompt: str, system: str = "") -> AiResult:
        if not self.api_key:
            raise AiUnavailable("no_api_key", "OpenAI API key 가 설정되지 않았습니다.")
        if not self.model:
            raise AiUnavailable("no_model", "OpenAI 모델명이 비어 있습니다.")

        openai = self._load_sdk()
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = openai.OpenAI(**kwargs)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        t0 = time.time()
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        _ = int((time.time() - t0) * 1000)  # latency_ms — 호출자 쪽에서 다시 측정 가능

        text = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        pt = getattr(usage, "prompt_tokens", 0) if usage else 0
        ct = getattr(usage, "completion_tokens", 0) if usage else 0
        return AiResult(text=text, prompt_tokens=pt, completion_tokens=ct)
