"""SMS 발송 시 비밀 값(passwd/key) 이 stderr 로그나 DB(SmsLog.detail) 에
평문으로 새지 않는지 회귀 방지.

이 테스트가 깨진다면:
  - _sms_sanitize 헬퍼가 사라졌거나 시그니처가 바뀜
  - sms_send 의 응답 echo / 예외 처리 경로에서 sanitize 호출이 누락됨
  → 실 운영 환경에서 SMS 서버 echo 또는 urllib 예외 메시지에 passwd/key 가
     섞여 stderr 와 DB 에 영구 저장되는 보안 사고 가능.
"""
from __future__ import annotations

import inspect

from app.routers import api as api_mod

# ─────────────────────────────────────────────────────────
# (1) _sms_sanitize 헬퍼 동작
# ─────────────────────────────────────────────────────────


def test_sanitize_replaces_secret_in_text():
    out = api_mod._sms_sanitize("응답: passwd=mySecret123 기타 정보", ["mySecret123"])
    assert "mySecret123" not in out
    assert "***" in out


def test_sanitize_handles_multiple_secrets():
    out = api_mod._sms_sanitize(
        "userid=admin passwd=keySecret9 second=pwSecret9",
        ["keySecret9", "pwSecret9"],
    )
    assert "keySecret9" not in out
    assert "pwSecret9" not in out


def test_sanitize_skips_empty_or_none():
    """빈 비밀/None 은 스킵 — 모두 *** 로 치환되는 사고 방지."""
    out = api_mod._sms_sanitize("payload=hello", [None, "", "  "])
    assert out == "payload=hello"


def test_sanitize_skips_short_secrets():
    """3자 이하 비밀은 스킵 — 너무 짧으면 일반 단어와 충돌해 무관한 텍스트가 다 마스킹됨."""
    out = api_mod._sms_sanitize("user=ab passwd=ab message=abacus", ["ab"])
    # 'ab' 는 len<4 이라 마스킹 대상 아님 → 원본 그대로
    assert out == "user=ab passwd=ab message=abacus"


def test_sanitize_handles_none_input():
    assert api_mod._sms_sanitize(None, ["secret"]) is None
    assert api_mod._sms_sanitize("", ["secret"]) == ""


# ─────────────────────────────────────────────────────────
# (2) sms_send 함수가 실제로 sanitize 를 사용하는지 (소스 검증)
# ─────────────────────────────────────────────────────────


def test_sms_send_calls_sanitize_on_response_and_exceptions():
    """sms_send 의 응답 echo / 예외 처리 경로에서 _sms_sanitize 호출이 살아있어야 함.

    런타임 통합 테스트는 외부 SMS 벤더 mock 이 필요해 무거우므로,
    소스 단위로 sanitize 호출 위치를 보장.
    """
    src = inspect.getsource(api_mod.sms_send)

    # 적용되어야 할 곳 (최소 4 곳):
    #   1) 정상 응답 디코딩 직후 resp_text 마스킹
    #   2) HTTPError 응답 디코딩 직후 resp_text 마스킹
    #   3) URLError 의 reason 마스킹
    #   4) 일반 Exception 의 e 마스킹
    sanitize_calls = src.count("_sms_sanitize(")
    assert sanitize_calls >= 4, (
        f"sms_send 안의 _sms_sanitize 호출이 {sanitize_calls}건 — "
        f"응답 echo / URLError / Exception 경로 중 일부에 누락된 것으로 보입니다."
    )

    # _secrets 변수가 정의되어 있어야 함
    assert "_secrets = [" in src, (
        "sms_send 진입부에서 _secrets 리스트 정의가 사라짐 — sanitize 가 무력화됨."
    )
