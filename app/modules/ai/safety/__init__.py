"""AI safety guards (post-19-P / 20-1 그룹 A).

기존 RAG / SMS / Action_leave 의 hallucination guard 패턴 외에 추가로
도메인 부재 항목 (doctors / 진료실 / 진료과 / 진료일정) 의 임의 생성을
차단하는 가드 모듈.

본 패키지는 19-13 의 ``app/modules/ai/commands/safety.py`` 와 별개 — commands
도메인 한정이 아닌 *AI 응답 공통* safety 가드.
"""

from app.modules.ai.safety.doctor_guard import (
    block_doctor_claims,
    has_doctor_claim,
)

__all__ = ["block_doctor_claims", "has_doctor_claim"]
