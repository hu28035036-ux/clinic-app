"""core.errors — 공통 예외 / reason_code 매핑 (신규).

19-P-2 §2-1 V2 트리의 ``app/core/errors.py`` — 신규 helper.

본 모듈은 modules 가 ``HTTPException(detail=...)`` 을 일관되게 만들 때 쓸 수 있는
공통 reason_code 상수와 helper 를 제공한다. 19-1 시점에는 *기존 라우터가 본 모듈을
참조하지 않는다* — 그저 신규 modules 가 점진적으로 채택할 수 있는 facade.

# NOTE: 응답 dict 키 / HTTPException ``detail`` 형식 / status_code 는 19-P-1 §21
#       33+ 키 셋과 동일. 본 모듈이 *기존 응답 구조를 변경하지 않음*.
#       (DEC-C 절대 원칙 정합 — 추가만 허용, 제거/rename/타입 변경 ⊥.)

# RISK: 본 모듈을 modules 에서 채택할 때, 기존 ``raise HTTPException(400, "...")``
#       형식과 결과 응답 dict 가 동일해야 한다. 채택 전 contract 테스트로 확인.
"""
from typing import Final


# ─── reason_code 상수 (19-x 분리 시점에 modules 가 채택) ─────────────────────────

# 인증 / 권한
REASON_NOT_AUTHENTICATED: Final[str] = "not_authenticated"
REASON_FORBIDDEN: Final[str] = "forbidden"
REASON_LOGIN_LOCKED: Final[str] = "login_locked"

# 입력 검증
REASON_INVALID_INPUT: Final[str] = "invalid_input"
REASON_MISSING_FIELD: Final[str] = "missing_field"
REASON_VALIDATION_ERROR: Final[str] = "validation_error"

# 자원 존재 / 충돌
REASON_NOT_FOUND: Final[str] = "not_found"
REASON_CONFLICT: Final[str] = "conflict"
REASON_VERSION_MISMATCH: Final[str] = "version_mismatch"  # 낙관적 락 (Appointment.version)

# 업무 규칙
REASON_LUNCH_BLOCK: Final[str] = "lunch_block"
REASON_LEAVE_BLOCK: Final[str] = "leave_block"
REASON_DUPLICATE_MANUAL: Final[str] = "duplicate_manual"

# AI / 외부 서비스
REASON_AI_DISABLED: Final[str] = "ai_disabled"
REASON_AI_NO_API_KEY: Final[str] = "ai_no_api_key"
REASON_AI_NO_MODEL: Final[str] = "ai_no_model"
REASON_AI_PROVIDER_UNAVAILABLE: Final[str] = "ai_provider_unavailable"
REASON_AI_PII_BLOCKED: Final[str] = "ai_pii_blocked"
REASON_AI_LOW_CONFIDENCE: Final[str] = "ai_low_confidence"
REASON_AI_NOT_FOUND: Final[str] = "ai_not_found"

# 시스템 / 인프라
REASON_OPERATIONAL_DB_BLOCKED: Final[str] = "operational_db_blocked"
REASON_EXTERNAL_API_BLOCKED: Final[str] = "external_api_blocked"


__all__ = [
    "REASON_NOT_AUTHENTICATED",
    "REASON_FORBIDDEN",
    "REASON_LOGIN_LOCKED",
    "REASON_INVALID_INPUT",
    "REASON_MISSING_FIELD",
    "REASON_VALIDATION_ERROR",
    "REASON_NOT_FOUND",
    "REASON_CONFLICT",
    "REASON_VERSION_MISMATCH",
    "REASON_LUNCH_BLOCK",
    "REASON_LEAVE_BLOCK",
    "REASON_DUPLICATE_MANUAL",
    "REASON_AI_DISABLED",
    "REASON_AI_NO_API_KEY",
    "REASON_AI_NO_MODEL",
    "REASON_AI_PROVIDER_UNAVAILABLE",
    "REASON_AI_PII_BLOCKED",
    "REASON_AI_LOW_CONFIDENCE",
    "REASON_AI_NOT_FOUND",
    "REASON_OPERATIONAL_DB_BLOCKED",
    "REASON_EXTERNAL_API_BLOCKED",
]
