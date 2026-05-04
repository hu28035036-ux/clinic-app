"""modules.sms.service — SMS 응답 dict 빌더 service helper (19-10 신규).

본 모듈은 ``api.py:sms_get`` (line 2928) / ``_serialize_sms_template``
(line 3036) / ``sms_tomorrow`` 응답 dict (line 3022~3029) / ``sms_send`` 응답
envelope (line 3442~3445) 의 *byte-equivalent* 빌더를 제공한다. 라우터 무수정.

19-10 본 세션 범위:
  - SMS 설정 응답 dict (마스킹 적용 — 8키).
  - 템플릿 응답 dict (6키).
  - 내일 대상 dict (8키).
  - 발송 응답 envelope (4키).
  - 라우터 미채택 (라우터 본체 무수정).

# COMPAT: ``api.py:sms_get`` (line 2929~2939, 8키) /
#         ``_serialize_sms_template`` (line 3036~3044, 6키) /
#         ``sms_tomorrow`` 응답 (line 3022~3029, 8키 per item) /
#         ``sms_send`` envelope (line 3442~3445, 4키) 와 byte-equivalent.

# SAFETY: 본 helper 는 *기존 응답 dict 그대로* — UI / SMS 흐름이 의존. 본 19-10
#         이 응답 키 / 타입 변경 ⊥. 문자나라 계정 / 비밀번호 / API key 는
#         ``rules.mask_*_for_response`` 가 *마스킹된 형태로만* 노출 — 응답 dict
#         / 로그 / 캐시에 *원문 노출 ⊥*.

# NOTE: 환자 PII (이름 / 전화 / 차트번호) 는 *기존 평문 그대로* 응답 dict 에 포함
#       — UI / SMS 발송 흐름 정합. 본 19-10 가 마스킹 정책 변경 ⊥. 로그용 마스킹은
#       ``rules.mask_phone_for_log`` 별도.

# RISK: 응답 dict 키 변경 ⊥ — UI 가 의존 (``main.html`` SMS 탭 / 관리자 SMS 설정
#       탭). ``schemas.py`` contract 상수가 회귀 검출.
"""
from __future__ import annotations

from typing import Any

from app.modules.sms import rules as _rules


# ─── SMS 설정 응답 (api.py:sms_get 동등) ─────────────────────────────────────


def serialize_sms_setting_masked(setting: Any) -> dict[str, Any]:
    """``SmsSetting`` ORM → 8키 응답 dict (비밀 마스킹 적용).

    COMPAT: ``api.py:sms_get`` (line 2929~2939) 와 byte-equivalent. 8키:
    ``munjanara_id / munjanara_pw / munjanara_key / sender_phone / clinic_phone /
    clinic_name / api_url``.

    SAFETY: ``munjanara_pw`` 는 ``mask_password_for_response`` (있으면 ``"****"``,
    없으면 빈) / ``munjanara_key`` 는 ``mask_api_key_for_response`` (앞 4자 + ``****``).
    원문 *노출 ⊥*. ``munjanara_id`` 는 마스킹 ⊥ (UI 가 평문 표시 — 기존 동작 정합).

    NOTE: 응답 dict 는 7키이지만 ``api_url`` 포함하면 7+1=8 키. dict 매핑 표:
      ``munjanara_id``  : 평문 (기존 동작).
      ``munjanara_pw``  : 마스킹.
      ``munjanara_key`` : 부분 마스킹.
      ``sender_phone``  : 평문.
      ``clinic_phone``  : 평문.
      ``clinic_name``   : 평문.
      ``api_url``       : 평문 (관리자가 설정한 endpoint).
    """
    return {
        "munjanara_id": setting.munjanara_id,
        "munjanara_pw": _rules.mask_password_for_response(setting.munjanara_pw),
        "munjanara_key": _rules.mask_api_key_for_response(setting.munjanara_key),
        "sender_phone": setting.sender_phone,
        "clinic_phone": setting.clinic_phone,
        "clinic_name": setting.clinic_name,
        "api_url": getattr(setting, "api_url", "") or "",
    }


# ─── 템플릿 응답 (api.py:_serialize_sms_template 동등) ───────────────────────


def serialize_sms_template(template: Any) -> dict[str, Any]:
    """``SmsTemplate`` ORM → 6키 응답 dict.

    COMPAT: ``api.py:_serialize_sms_template`` (line 3036~3044) 와 byte-equivalent.
    6키: ``id / name / body / sort_order / active / updated_at``.
    """
    return {
        "id": template.id,
        "name": template.name,
        "body": template.body or "",
        "sort_order": template.sort_order or 0,
        "active": bool(template.active),
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


# ─── 내일 대상 dict (api.py:sms_tomorrow line 3022~3029 동등) ────────────────


def build_tomorrow_target_dict(
    *,
    appointment_id: str,
    patient_id: str,
    chart_no: str | None,
    name: str,
    phone: str,
    reserved_at_iso: str,
    body: str,
    treatment_summary: str,
) -> dict[str, Any]:
    """내일 예약 알림 대상 dict — 8키.

    COMPAT: ``api.py:sms_tomorrow`` (line 3022~3029) 와 byte-equivalent.
    8키: ``appointment_id / patient_id / chart_no / name / phone / reserved_at /
    body / treatment_summary``.

    NOTE: ``chart_no`` 가 빈 / None 이면 ``"-"`` (api.py:3025 정합).
    NOTE: 환자 PII (name / phone) 는 *기존 동작* 그대로 평문 — UI / SMS 발송이
    의존. 마스킹 정책 변경 ⊥.
    """
    return {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "chart_no": chart_no or "-",
        "name": name,
        "phone": phone,
        "reserved_at": reserved_at_iso,
        "body": body,
        "treatment_summary": treatment_summary,
    }


# ─── 발송 응답 envelope (api.py:sms_send line 3442~3445 동등) ────────────────


def build_send_envelope(
    *,
    items: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """``POST /api/sms/send`` 응답 envelope — 4키.

    COMPAT: ``api.py:sms_send`` (line 3442~3445) ``{"sent": ..., "failed": ...,
    "total": ..., "results": ...}`` 와 byte-equivalent.

    인자:
      ``items``   : 입력 ``payload["items"]``.
      ``results`` : 항목별 결과 dict 리스트 (``{"phone", "result", "kind", ...}``).
    """
    sent = sum(1 for r in results if r.get("result") == "success")
    failed = len(items) - sent
    return {
        "sent": sent,
        "failed": failed,
        "total": len(items),
        "results": results,
    }


# ─── 누락 항목 메시지 빌드 (api.py:sms_send line 3239~3248 동등) ─────────────


def build_missing_setting_message(missing: list[str]) -> str:
    """SMS 설정 누락 시 한국어 사용자 노출 메시지.

    COMPAT: ``api.py:sms_send`` (line 3247~3248) 정합.
    포맷:
      ``"문자나라 설정을 먼저 완료하세요 (관리자 → 문자나라)\n누락 항목: {a, b, c}"``
    """
    return (
        "문자나라 설정을 먼저 완료하세요 (관리자 → 문자나라)\n"
        "누락 항목: " + ", ".join(missing)
    )


def collect_missing_setting_fields(setting: Any) -> list[str]:
    """SMS 설정에서 발송에 필요한 필수 필드 누락 항목 수집.

    COMPAT: ``api.py:sms_send`` (line 3239~3244) 정합. 4개 필드 검사:
      - ``munjanara_id`` → ``"아이디"``
      - ``munjanara_key`` → ``"2차 비밀번호 (API 인증용)"``
      - ``sender_phone`` → ``"발신번호"``
      - ``api_url``      → ``"API URL"``

    NOTE: ``munjanara_pw`` 는 발송 API 호출에 사용되지 않으므로 누락 검사 ⊥
    (api.py:3279~3280 주석 정합).
    """
    missing: list[str] = []
    if not getattr(setting, "munjanara_id", None):
        missing.append("아이디")
    if not getattr(setting, "munjanara_key", None):
        missing.append("2차 비밀번호 (API 인증용)")
    if not getattr(setting, "sender_phone", None):
        missing.append("발신번호")
    if not getattr(setting, "api_url", None):
        missing.append("API URL")
    return missing


# ─── 비밀번호 보호 정책 (api.py:sms_set line 2962~2966 동등) ─────────────────


PASSWORD_PROTECTION_KEYS: tuple[str, ...] = ("munjanara_pw", "munjanara_key")


def should_skip_password_update(key: str, value: Any) -> bool:
    """비밀번호 / API key 가 빈 값 또는 마스킹 placeholder 일 때 *update 스킵*.

    COMPAT: ``api.py:sms_set`` (line 2961~2966) 정합. 두 가지 스킵 조건:
      1) 모든 필드 : 마스킹된 값 (``****`` 로 시작) → "수정 안 함".
      2) PASSWORD_PROTECTION_KEYS : 빈 값 → "수정 안 함" (기존 DB 값 보존).

    SAFETY: 페이지 새로고침 후 password input 이 빈 값으로 그려지므로, 빈 값으로
    덮어씌워지면 *기존 비번이 빈 값으로 초기화* 되는 사고 방지 (v1.2.16 보강).
    """
    if value is None:
        return True
    val = str(value)
    if val.startswith("****"):
        return True
    if key in PASSWORD_PROTECTION_KEYS and val == "":
        return True
    return False


__all__ = [
    "serialize_sms_setting_masked",
    "serialize_sms_template",
    "build_tomorrow_target_dict",
    "build_send_envelope",
    "build_missing_setting_message",
    "collect_missing_setting_fields",
    "PASSWORD_PROTECTION_KEYS",
    "should_skip_password_update",
]
