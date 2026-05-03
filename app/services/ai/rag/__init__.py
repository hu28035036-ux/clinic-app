"""RAG 패키지 골격 — 18-1.

목표 RAG 아키텍처(``docs/ai_rag_architecture_plan.md`` §2~§3)의 신규 모듈
공간. 18-1 시점에는 **빈 골격 + 인터페이스 stub** 만 둔다.

의존 규칙 (circular import 방지):
  - 본 패키지의 모듈은 ``app.services.ai.{provider, pii}`` 만 import 가능
  - 기존 ``app.services.ai.manual_qa`` 는 import 하지 않는다 (역의존 회피)
  - 신규 모듈끼리는 가능 (``schemas`` → 다른 모듈에서 import)

실제 동작 이전은 18-2 (keyword RAG 분리) 이후.
"""
from __future__ import annotations
