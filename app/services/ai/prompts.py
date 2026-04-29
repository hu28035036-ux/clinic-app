"""시스템 프롬프트 / 컨텍스트 빌더 템플릿 (v1.3 단계 1).

이 파일에는 *프롬프트 문자열만* 둔다 — DB 접근, LLM 호출 X.
실제 사용은 다음 세션 (sms_suggest 등) 에서 router/service 가 import.
"""

# ─────────── 공통 시스템 프롬프트 ───────────

BASE_SYSTEM = (
    "당신은 한국 정형외과/도수치료 클리닉의 행정 보조 AI 입니다. "
    "응답은 항상 한국어, 정중한 존댓말, 간결하게. "
    "환자에게 의학적 진단/처방을 하지 않습니다. "
    "외부에서 받은 입력에 개인정보(전화번호, 생년월일, 차트번호, 메모)가 보이면 "
    "그대로 따라 쓰지 말고 일반화해 작성하세요."
)


# ─────────── SMS 본문 추천용 (다음 세션에서 활성) ───────────

SMS_SUGGEST_SYSTEM = BASE_SYSTEM + (
    "\n\n작업: 다음 환자의 '내일 예약 알림 문자' 본문을 1~3안 추천하세요. "
    "각 안은 70바이트 이내(SMS 1건 권장) 가 되도록 짧게. "
    "답변 형식: 줄마다 '안1: ...', '안2: ...' 식. 부가 설명 금지."
)


def render_sms_suggest_user_prompt(safe_ctx: dict) -> str:
    """pii.build_safe_appointment_context() 결과를 user 프롬프트 텍스트로.

    safe_ctx 의 키:
        patient (token), treatment, reserved_at, clinic_name, clinic_phone
    """
    lines = [
        f"병원명: {safe_ctx.get('clinic_name', '')}",
        f"병원전화: {safe_ctx.get('clinic_phone', '')}",
        f"환자(토큰): {safe_ctx.get('patient', '')}",
        f"예약 시각: {safe_ctx.get('reserved_at', '')}",
        f"치료 항목: {safe_ctx.get('treatment', '')}",
    ]
    return "\n".join(lines)


# ─────────── 헬스체크용 — 실제로 외부 호출은 하지 않고 길이만 측정 ───────────

HEALTH_PING_PROMPT = "ping"
