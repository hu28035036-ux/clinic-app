"""modules.sms.rules — 전화번호 정규화 / 형식 판정 / 마스킹 도메인 규칙 (19-10 신규).

본 모듈은 ``api.py:_normalize_phone_for_sms`` (line 3115) /
``_is_valid_kr_mobile`` (line 3123) / ``_mask_phone_for_log`` (line 3139) /
``_sms_sanitize`` (line 3160) 의 *순수 helper* 를 제공한다. ORM / DB / 외부 API
미참조 — primitives 만 받음 (D-4 정합).

19-10 본 세션 범위:
  - 전화번호 정규화 (숫자만 추출).
  - 한국 휴대폰 / 전화 형식 판정.
  - 로그용 전화번호 마스킹.
  - 평문 비밀 (passwd / api key) 마스킹.
  - 라우터 무수정 (helper 미채택).

# COMPAT: ``api.py:_normalize_phone_for_sms`` (line 3115~3120) /
#         ``_is_valid_kr_mobile`` (line 3123~3136) / ``_mask_phone_for_log``
#         (line 3139~3147) / ``_sms_sanitize`` (line 3160~3180) 와 byte-equivalent.

# SAFETY: ``mask_phone_for_log`` 는 *로그 / audit 용* — 운영 응답 / SMS 발송 대상
#         dict 에는 *기존 평문 그대로* (UI 가 평문 phone 필요). ``sanitize_secrets``
#         는 외부 응답 echo / 예외 메시지에 평문 비밀이 섞여 있을 가능성을 차단.

# NOTE: 한국 휴대폰 형식: 010 (11자리), 011/016~019 (10~11자리), 02 (9~10자리),
#       지역번호 03x~08x (10~11자리, 0 시작). spec 정합 — api.py:3127~3135.

# RISK: 짧은 비밀 (4자 미만) 은 마스킹 시 의미없는 치환 폭증 → 스킵 (api.py:3177
#       정합). secrets 인자에 빈 값 / None 이 섞여 있어도 안전.
"""
from __future__ import annotations

import re
from typing import Final


# ─── 전화번호 정규화 (api.py:_normalize_phone_for_sms 정합) ──────────────────


def normalize_phone(raw: str | None) -> str:
    """수신/발신 번호 → 숫자만. 하이픈 / 공백 / 점 / 괄호 / + 모두 제거.

    COMPAT: ``api.py:_normalize_phone_for_sms`` (line 3115~3120) 정합.
    빈 / None → 빈 문자열.
    """
    if not raw:
        return ""
    return re.sub(r"[^0-9]", "", str(raw))


# ─── 한국 휴대폰 / 전화 형식 판정 (api.py:_is_valid_kr_mobile 정합) ──────────


def is_valid_kr_mobile(digits: str | None) -> bool:
    """한국 휴대폰 / 전화 번호 형식 체크 (정규화 후 숫자만 문자열).

    COMPAT: ``api.py:_is_valid_kr_mobile`` (line 3123~3136) 정합.

    매핑:
      - 010 (11자리) : 휴대폰.
      - 011 / 016 / 017 / 018 / 019 (10~11자리) : 구형 휴대폰.
      - 02 (9~10자리) : 서울.
      - 0X (10~11자리) : 지역번호 (03x~06x / 07x / 08x).
    """
    if not digits:
        return False
    if digits.startswith("010") and len(digits) == 11:
        return True
    if digits.startswith(("011", "016", "017", "018", "019")) and len(digits) in (10, 11):
        return True
    if digits.startswith("02") and len(digits) in (9, 10):
        return True
    if len(digits) in (10, 11) and digits[0] == "0":
        return True
    return False


# ─── 로그용 전화번호 마스킹 (api.py:_mask_phone_for_log 정합) ────────────────


PHONE_MASK_FALLBACK: Final[str] = "(없음)"
PHONE_MASK_PARTIAL: Final[str] = "***"


def mask_phone_for_log(phone: str | None) -> str:
    """로그용 전화번호 마스킹 — 끝 4자리만 노출.

    COMPAT: ``api.py:_mask_phone_for_log`` (line 3139~3147) 정합.

    SAFETY: 운영 응답 / SMS 대상 dict 에는 사용 ⊥ (UI 가 평문 phone 필요). 로그 /
    audit / 진단 출력 전용.
    """
    if not phone:
        return PHONE_MASK_FALLBACK
    digits = re.sub(r"[^0-9]", "", str(phone))
    if len(digits) >= 4:
        return f"***-****-{digits[-4:]}"
    return PHONE_MASK_PARTIAL


# ─── 평문 비밀 마스킹 (api.py:_sms_sanitize 정합) ─────────────────────────────


SECRET_MIN_LENGTH: Final[int] = 4
SECRET_MASK: Final[str] = "***"


def sanitize_secrets(text: str | None, secrets: list[str | None] | None) -> str:
    """텍스트에서 평문 비밀들을 ``***`` 로 치환.

    COMPAT: ``api.py:_sms_sanitize`` (line 3160~3180) 정합.

    적용 대상:
      - urllib / socket 예외 메시지에 요청 body 일부가 끼어 들어오는 경우.
      - SMS 서버가 요청 echo 형태로 응답해 passwd / key 값을 그대로 돌려보내는 경우.

    인자:
      ``text`` : 마스킹 대상 문자열 (로그 / 응답 / 예외 메시지).
      ``secrets`` : 마스킹할 비밀 리스트. 빈 / None / ``len < 4`` 항목은 스킵.

    NOTE: 너무 짧은 비밀 (4자 미만) 은 의미없는 치환 폭증 방지 위해 스킵.
    """
    if not text:
        return text or ""
    out = str(text)
    for s in (secrets or []):
        if not s:
            continue
        s_str = str(s)
        if len(s_str) < SECRET_MIN_LENGTH:
            continue
        out = out.replace(s_str, SECRET_MASK)
    return out


# ─── API key / passwd 마스킹 (응답 dict 용) ──────────────────────────────────


PASSWORD_PLACEHOLDER: Final[str] = "****"


def mask_password_for_response(value: str | None) -> str:
    """비밀번호 응답용 마스킹 — 빈 값이면 "" / 있으면 ``****``.

    COMPAT: ``api.py:sms_get`` (line 2932) ``"****" if obj.munjanara_pw else ""``
    정합. 응답 dict 에 *원문 노출 ⊥*.
    """
    if not value:
        return ""
    return PASSWORD_PLACEHOLDER


def mask_api_key_for_response(value: str | None) -> str:
    """API key 응답용 마스킹 — 앞 4자 + ``****``.

    COMPAT: ``api.py:sms_get`` (line 2933) ``obj.munjanara_key[:4] + "****" if
    obj.munjanara_key else ""`` 정합.
    """
    if not value:
        return ""
    return value[:4] + PASSWORD_PLACEHOLDER


__all__ = [
    "normalize_phone",
    "is_valid_kr_mobile",
    "PHONE_MASK_FALLBACK",
    "PHONE_MASK_PARTIAL",
    "mask_phone_for_log",
    "SECRET_MIN_LENGTH",
    "SECRET_MASK",
    "sanitize_secrets",
    "PASSWORD_PLACEHOLDER",
    "mask_password_for_response",
    "mask_api_key_for_response",
]
