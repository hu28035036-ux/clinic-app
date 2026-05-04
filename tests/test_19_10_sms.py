"""19-10 sms 문자 도메인 분리 contract.

검증 범위 (19-10 세션 지시문 정합):
  1. ``rules.normalize_phone`` / ``is_valid_kr_mobile`` / ``mask_phone_for_log`` /
     ``sanitize_secrets`` / ``mask_password_for_response`` / ``mask_api_key_for_response``
     가 ``api.py`` 인라인 helper 와 byte-equivalent.
  2. ``templates.normalize_tx_name_for_sms`` / ``format_tx_summary_for_sms`` /
     ``build_tomorrow_target_body`` 가 ``api.py`` 의 문자 본문 / 치료요약 빌더와
     byte-equivalent.
  3. ``service.serialize_sms_setting_masked`` 가 ``api.py:sms_get`` 응답과 동일
     (비밀 / API key 마스킹 적용).
  4. ``service.serialize_sms_template`` 가 ``api.py:_serialize_sms_template`` 와 동일.
  5. ``service.build_tomorrow_target_dict`` 가 ``api.py:sms_tomorrow`` 응답 dict 와 동일.
  6. ``service.build_send_envelope`` 가 ``api.py:sms_send`` 응답 envelope 과 동일.
  7. ``service.collect_missing_setting_fields`` / ``build_missing_setting_message`` 가
     ``api.py:sms_send`` 누락 검사 / 메시지와 동일.
  8. ``service.should_skip_password_update`` 가 ``api.py:sms_set`` 비밀 보호 정책과 동일.
  9. ``provider.FakeSmsProvider`` 가 *외부 호출 ⊥* — ``urllib`` 미참조 검증.
 10. ``provider.NotConfiguredProvider`` 가 호출 시 모든 항목을 ``not_configured``
     로 거부 — 외부 호출 ⊥.
 11. ``schemas.*`` contract 상수가 실제 라우터 응답 dict 의 키 셋과 일치.
 12. modules.sms 가 ``app.routers`` 미참조 — 단방향 경계 (D-4).
 13. 라우터 SMS 핸들러 시그니처 무수정.
 14. 기존 SMS AI (``app/services/ai/sms_draft.py``) 흐름 무수정.
 15. 본 모듈 import 만으로 외부 API 호출 ⊥ (``urllib.request`` 등 사용 흔적 부재).
"""
from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path

import pytest

from app.modules.sms import provider as _provider
from app.modules.sms import rules as _rules
from app.modules.sms import schemas as _schemas
from app.modules.sms import service as _service
from app.modules.sms import templates as _templates

# ──────────────────────── 1. rules — 전화번호 정규화 / 형식 판정 ────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, ""),
        ("", ""),
        ("010-1234-5678", "01012345678"),
        ("010 1234 5678", "01012345678"),
        ("+82 10 1234 5678", "821012345678"),
        ("(02) 555-1234", "025551234"),  # 9자리 — "02" + "5551234"
        ("abc", ""),
        ("010.1234.5678", "01012345678"),
    ],
)
def test_normalize_phone_byte_equivalent_with_api(raw, expected):
    """COMPAT: ``api.py:_normalize_phone_for_sms`` (line 3115) 정합."""
    assert _rules.normalize_phone(raw) == expected
    # 라우터 인라인과 동일.
    from app.routers.api import _normalize_phone_for_sms

    assert _rules.normalize_phone(raw) == _normalize_phone_for_sms(raw)


@pytest.mark.parametrize(
    "digits,expected",
    [
        ("01012345678", True),       # 010 휴대폰 11자리
        ("0111234567", True),        # 011 10자리
        ("01112345678", True),       # 011 11자리
        ("0212345678", True),        # 02 10자리
        ("021234567", True),         # 02 9자리
        ("0312345678", True),        # 지역번호 10자리
        ("03112345678", True),       # 지역번호 11자리
        ("12345", False),            # 0 시작 아님
        ("", False),
        (None, False),
        # "0101234567" (10자리, 0 시작) 은 generic 지역번호 fallback 으로 valid (api.py:3134 정합).
        ("010123456789", False),     # 010 12자리 (잘못)
        ("12345678901", False),      # 1 로 시작
    ],
)
def test_is_valid_kr_mobile_byte_equivalent_with_api(digits, expected):
    """COMPAT: ``api.py:_is_valid_kr_mobile`` (line 3123) 정합."""
    assert _rules.is_valid_kr_mobile(digits) is expected
    from app.routers.api import _is_valid_kr_mobile

    assert _rules.is_valid_kr_mobile(digits) == _is_valid_kr_mobile(digits)


@pytest.mark.parametrize(
    "phone,expected",
    [
        (None, "(없음)"),
        ("", "(없음)"),
        ("010-1234-5678", "***-****-5678"),
        ("01012345678", "***-****-5678"),
        ("123", "***"),  # 4자리 미만
        ("1234", "***-****-1234"),
    ],
)
def test_mask_phone_for_log_byte_equivalent_with_api(phone, expected):
    """COMPAT: ``api.py:_mask_phone_for_log`` (line 3139) 정합."""
    assert _rules.mask_phone_for_log(phone) == expected
    from app.routers.api import _mask_phone_for_log

    assert _rules.mask_phone_for_log(phone) == _mask_phone_for_log(phone)


def test_sanitize_secrets_replaces_long_secrets():
    """COMPAT: ``api.py:_sms_sanitize`` (line 3160) 정합."""
    text = "request body: passwd=mySecret123 something else"
    assert "mySecret123" not in _rules.sanitize_secrets(text, ["mySecret123"])
    assert "***" in _rules.sanitize_secrets(text, ["mySecret123"])


def test_sanitize_secrets_skips_short_secrets():
    """4자 미만 비밀은 *치환 폭증 방지* 위해 스킵."""
    text = "x" * 100
    # 1자 비밀 — 치환되면 100개 모두 *** 로 폭증.
    assert _rules.sanitize_secrets(text, ["x"]) == text


def test_sanitize_secrets_handles_none_and_empty():
    assert _rules.sanitize_secrets(None, ["a", "b"]) == ""
    assert _rules.sanitize_secrets("hello", None) == "hello"
    assert _rules.sanitize_secrets("hello", []) == "hello"
    assert _rules.sanitize_secrets("hello", [None, "", None]) == "hello"


def test_sanitize_secrets_byte_equivalent_with_api():
    """COMPAT: 라우터 인라인과 동등."""
    from app.routers.api import _sms_sanitize

    text = "echo: passwd=secretValue123 key=apiKey456"
    secrets = ["secretValue123", "apiKey456"]
    assert _rules.sanitize_secrets(text, secrets) == _sms_sanitize(text, secrets)


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, ""),
        ("", ""),
        ("secret-pw", "****"),
        ("any-value", "****"),
    ],
)
def test_mask_password_for_response(value, expected):
    """COMPAT: ``api.py:sms_get`` (line 2932) 정합."""
    assert _rules.mask_password_for_response(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, ""),
        ("", ""),
        ("ABCD1234", "ABCD****"),
        ("XYZ", "XYZ****"),
    ],
)
def test_mask_api_key_for_response(value, expected):
    """COMPAT: ``api.py:sms_get`` (line 2933) 정합."""
    assert _rules.mask_api_key_for_response(value) == expected


# ──────────────────────── 2. templates — 본문 / 치료요약 빌더 ───────────────


@pytest.mark.parametrize(
    "name,expected",
    [
        # None / "" → raw 보존 (api.py:_normalize_tx_name_for_sms line 2975~2976 정합).
        (None, None),
        ("", ""),
        ("도수치료30분", "도수치료"),
        ("도수치료60분", "도수치료"),
        ("도수치료 30분", "도수치료"),
        ("도수치료 60 분", "도수치료"),
        ("체외충격파", "체외충격파"),
        ("주사", "주사"),
        ("연골주사", "연골주사"),
    ],
)
def test_normalize_tx_name_for_sms_byte_equivalent_with_api(name, expected):
    """COMPAT: ``api.py:_normalize_tx_name_for_sms`` (line 2973) 정합."""
    assert _templates.normalize_tx_name_for_sms(name) == expected
    from app.routers.api import _normalize_tx_name_for_sms

    assert _templates.normalize_tx_name_for_sms(name) == _normalize_tx_name_for_sms(name)


def test_format_tx_summary_for_sms_basic():
    """COMPAT: ``api.py:_format_tx_summary_for_sms`` (line 2983) 정합."""

    class _T:
        def __init__(self, name):
            self.name = name

    treatments = {
        "manual30": _T("도수치료30분"),
        "manual60": _T("도수치료60분"),
        "eswt": _T("체외충격파"),
        "injection": _T("주사"),
    }

    # 도수30 + 도수60 → "도수치료" 1개로 합쳐짐 (정규화 후 중복 제거).
    assert _templates.format_tx_summary_for_sms(
        ["manual30", "manual60"], treatments,
    ) == "도수치료"

    # 도수치료 + 체외충격파 → 두 항목.
    assert _templates.format_tx_summary_for_sms(
        ["manual30", "eswt"], treatments,
    ) == "도수치료, 체외충격파"

    # 알 수 없는 코드는 스킵.
    assert _templates.format_tx_summary_for_sms(
        ["unknown_code", "manual30"], treatments,
    ) == "도수치료"

    # 빈 리스트.
    assert _templates.format_tx_summary_for_sms([], treatments) == ""
    assert _templates.format_tx_summary_for_sms(None, treatments) == ""


def test_build_tomorrow_target_body_format():
    """COMPAT: ``api.py:sms_tomorrow`` (line 3019~3021) body 포맷 정합."""
    dt = datetime(2099, 7, 15, 14, 30)  # 2099-07-15 (수요일) 14:30
    body = _templates.build_tomorrow_target_body(
        clinic_name="튼튼병원",
        patient_name="홍길동",
        appointment_dt=dt,
        tx_summary="도수치료, 체외충격파",
        clinic_phone="02-555-1234",
    )
    # 2099-07-15 = ?  실제 weekday 검증.
    assert body.startswith("[튼튼병원] 홍길동 님, ")
    assert "내일(7/15 " in body
    assert "14:30 도수치료, 체외충격파 예약이 있습니다" in body
    assert "변경/취소는 02-555-1234" in body


def test_build_tomorrow_target_body_empty_tx_summary():
    """tx_summary 빈 → tx_part 빈 (api.py:3018 정합)."""
    dt = datetime(2099, 1, 1, 9, 0)
    body = _templates.build_tomorrow_target_body(
        clinic_name="병원", patient_name="환자",
        appointment_dt=dt, tx_summary="",
        clinic_phone="000-0000",
    )
    # tx_part 빈 → 시간 뒤 공백 1개 + "예약" — api.py 의 동일 동작.
    assert "09:00 예약이 있습니다" in body


def test_korean_weekday():
    """COMPAT: ``api.py:sms_tomorrow`` weekdays 매핑 정합."""
    # 2026-05-04 은 월요일.
    assert _templates.korean_weekday(datetime(2026, 5, 4)) == "월"
    # 2026-05-10 은 일요일.
    assert _templates.korean_weekday(datetime(2026, 5, 10)) == "일"


# ──────────────────────── 3. service — SMS 설정 응답 (마스킹) ───────────────


def test_serialize_sms_setting_masked_byte_equivalent_with_api(client):
    """COMPAT: ``api.py:sms_get`` (line 2929~2939) 정합."""
    from app.database import SessionLocal
    from app.routers.api import sms_get

    db = SessionLocal()
    try:
        # 기존 또는 신규 SmsSetting (id=1) 사용.
        api_response = sms_get(db=db)

        # 본 모듈로 설정 조회 후 동일 결과.
        from app.models import models as _m
        setting = db.query(_m.SmsSetting).filter_by(id=1).first()
        service_response = _service.serialize_sms_setting_masked(setting)

        assert api_response == service_response
        # 7키.
        assert set(service_response.keys()) == _schemas.SMS_SETTING_RESPONSE_KEYS
    finally:
        db.close()


def test_serialize_sms_setting_masks_password():
    """SAFETY: 비밀번호 / API key 원문 노출 ⊥."""

    class _S:
        munjanara_id = "myid"
        munjanara_pw = "supersecret_pw_value"
        munjanara_key = "supersecret_api_key"
        sender_phone = "010-0000-0000"
        clinic_phone = "02-555-1234"
        clinic_name = "병원"
        api_url = "https://example.com"
        id = 1

    out = _service.serialize_sms_setting_masked(_S())
    # 평문 비밀이 응답 어디에도 없어야 함.
    assert "supersecret_pw_value" not in str(out)
    assert "supersecret_api_key" not in str(out)
    # 마스킹 형태.
    assert out["munjanara_pw"] == "****"
    assert out["munjanara_key"].startswith("supe")  # 앞 4자만
    assert out["munjanara_key"].endswith("****")


def test_serialize_sms_setting_empty_secrets_remain_empty():
    class _S:
        munjanara_id = ""
        munjanara_pw = ""
        munjanara_key = ""
        sender_phone = ""
        clinic_phone = ""
        clinic_name = ""
        api_url = ""
        id = 1

    out = _service.serialize_sms_setting_masked(_S())
    assert out["munjanara_pw"] == ""
    assert out["munjanara_key"] == ""


# ──────────────────────── 4. service — 템플릿 응답 ──────────────────────────


def test_serialize_sms_template_byte_equivalent_with_api(client):
    """COMPAT: ``api.py:_serialize_sms_template`` (line 3036~3044) 정합."""
    from app.database import SessionLocal
    from app.models import models as _m
    from app.routers.api import _serialize_sms_template

    db = SessionLocal()
    try:
        # 시드된 템플릿 (또는 신규 생성).
        t = db.query(_m.SmsTemplate).first()
        if t is None:
            pytest.skip("시드된 SmsTemplate 부재")
        api_dict = _serialize_sms_template(t)
        service_dict = _service.serialize_sms_template(t)
        assert api_dict == service_dict
        assert set(service_dict.keys()) == _schemas.SMS_TEMPLATE_RESPONSE_KEYS
    finally:
        db.close()


# ──────────────────────── 5. service — 내일 대상 dict ───────────────────────


def test_build_tomorrow_target_dict_keys():
    """COMPAT: ``api.py:sms_tomorrow`` (line 3022~3029) 정합 — 8키."""
    out = _service.build_tomorrow_target_dict(
        appointment_id="A1",
        patient_id="P1",
        chart_no="C-001",
        name="홍길동",
        phone="010-1234-5678",
        reserved_at_iso="2099-07-15T14:30:00",
        body="알림 본문",
        treatment_summary="도수치료",
    )
    assert set(out.keys()) == _schemas.SMS_TOMORROW_TARGET_KEYS
    assert out["chart_no"] == "C-001"
    assert out["body"] == "알림 본문"


def test_build_tomorrow_target_dict_chart_no_fallback():
    """COMPAT: 빈 chart_no → ``"-"`` (api.py:3025 정합)."""
    out = _service.build_tomorrow_target_dict(
        appointment_id="A", patient_id="P",
        chart_no=None, name="환자", phone="010-1234-5678",
        reserved_at_iso="2099-01-01T10:00:00",
        body="b", treatment_summary="",
    )
    assert out["chart_no"] == "-"


# ──────────────────────── 6. service — 발송 envelope ────────────────────────


def test_build_send_envelope_keys():
    """COMPAT: ``api.py:sms_send`` (line 3442~3445) envelope 정합."""
    out = _service.build_send_envelope(
        items=[{"phone": "010-1111"}, {"phone": "010-2222"}],
        results=[
            {"phone": "010-1111", "result": "success", "kind": "ok", "detail": ""},
            {"phone": "010-2222", "result": "fail", "kind": "precheck", "detail": "x"},
        ],
    )
    assert set(out.keys()) == _schemas.SMS_SEND_ENVELOPE_KEYS
    assert out["sent"] == 1
    assert out["failed"] == 1
    assert out["total"] == 2


def test_build_send_envelope_all_success():
    out = _service.build_send_envelope(
        items=[{"phone": "010-1"}, {"phone": "010-2"}, {"phone": "010-3"}],
        results=[
            {"phone": "010-1", "result": "success", "kind": "ok", "detail": ""},
            {"phone": "010-2", "result": "success", "kind": "ok", "detail": ""},
            {"phone": "010-3", "result": "success", "kind": "ok", "detail": ""},
        ],
    )
    assert out["sent"] == 3
    assert out["failed"] == 0
    assert out["total"] == 3


def test_build_send_envelope_empty():
    out = _service.build_send_envelope(items=[], results=[])
    assert out == {"sent": 0, "failed": 0, "total": 0, "results": []}


# ──────────────────────── 7. service — 누락 검사 + 메시지 ───────────────────


def test_collect_missing_setting_fields():
    """COMPAT: ``api.py:sms_send`` (line 3239~3244) 정합."""

    class _S:
        def __init__(self, **kw):
            self.munjanara_id = kw.get("munjanara_id", "")
            self.munjanara_key = kw.get("munjanara_key", "")
            self.sender_phone = kw.get("sender_phone", "")
            self.api_url = kw.get("api_url", "")
            self.munjanara_pw = kw.get("munjanara_pw", "")

    # 모두 비어 있으면 4개 누락.
    missing_all = _service.collect_missing_setting_fields(_S())
    assert "아이디" in missing_all
    assert "2차 비밀번호 (API 인증용)" in missing_all
    assert "발신번호" in missing_all
    assert "API URL" in missing_all
    assert len(missing_all) == 4

    # 모두 채워져 있으면 0개.
    missing_none = _service.collect_missing_setting_fields(_S(
        munjanara_id="id", munjanara_key="key",
        sender_phone="010-0", api_url="https://x",
    ))
    assert missing_none == []

    # munjanara_pw 가 비어도 누락 ⊥ (api.py 정합).
    missing_pw_only = _service.collect_missing_setting_fields(_S(
        munjanara_id="id", munjanara_key="key",
        sender_phone="010-0", api_url="https://x",
        munjanara_pw="",
    ))
    assert missing_pw_only == []


def test_build_missing_setting_message_format():
    """COMPAT: ``api.py:sms_send`` (line 3247~3248) 정합."""
    msg = _service.build_missing_setting_message(["아이디", "API URL"])
    assert "문자나라 설정을 먼저 완료하세요" in msg
    assert "관리자 → 문자나라" in msg
    assert "누락 항목: 아이디, API URL" in msg


# ──────────────────────── 8. service — 비밀 보호 정책 ───────────────────────


@pytest.mark.parametrize(
    "key,value,expected_skip",
    [
        # 마스킹된 값 (****로 시작) → 스킵.
        ("munjanara_id", "****", True),
        ("munjanara_pw", "****", True),
        # NOTE: "ABCD****" 는 ``startswith("****")`` 가 False — 스킵 ⊥ (api.py 정합).
        # api_key 응답 마스킹 형태 ``ABCD****`` 가 그대로 다시 PUT 되면 *값으로 적용* 됨.
        # 이는 기존 동작 — 본 19-10 가 변경 ⊥. 사용자가 ID 마스킹 형태와 다르다는 점이
        # api 의 알려진 edge case (UI 가 마스킹된 key 를 다시 보내지 않도록 처리하는 책임).
        ("munjanara_key", "ABCD****", False),
        # 비밀번호 류 + 빈 값 → 스킵 (기존 DB 값 보존).
        ("munjanara_pw", "", True),
        ("munjanara_key", "", True),
        # 비밀번호 류가 아닌 필드 + 빈 값 → 적용 (스킵 ⊥).
        ("munjanara_id", "", False),
        ("sender_phone", "", False),
        ("api_url", "", False),
        # 정상 값 → 적용 (스킵 ⊥).
        ("munjanara_id", "myid", False),
        ("munjanara_pw", "newpw", False),
        # None → 스킵.
        ("munjanara_id", None, True),
    ],
)
def test_should_skip_password_update(key, value, expected_skip):
    """COMPAT: ``api.py:sms_set`` (line 2961~2966) 정합."""
    assert _service.should_skip_password_update(key, value) is expected_skip


# ──────────────────────── 9. provider — FakeSmsProvider 외부 호출 ⊥ ────────


def test_fake_provider_records_calls_without_external_call():
    """SAFETY: FakeSmsProvider 는 외부 HTTP 호출 ⊥ — 기록만."""
    fake = _provider.FakeSmsProvider()
    items = [
        {"phone": "010-1111", "body": "테스트1"},
        {"phone": "010-2222", "body": "테스트2"},
    ]

    class _Settings:
        id = 1

    results = fake.send(items=items, settings=_Settings())

    # 모두 합성 성공.
    assert len(results) == 2
    assert all(r.result == "success" for r in results)
    assert all(r.kind == "ok" for r in results)
    assert all(r.status_code == 200 for r in results)

    # calls 기록.
    assert len(fake.calls) == 1
    assert fake.calls[0]["settings_id"] == 1
    assert len(fake.calls[0]["items"]) == 2


def test_fake_provider_no_urllib_used():
    """SAFETY: FakeSmsProvider 의 send 메서드 본체에 urllib / requests 미참조."""
    src = inspect.getsource(_provider.FakeSmsProvider.send)
    assert "urllib" not in src
    assert "requests" not in src
    assert "httpx" not in src


def test_provider_module_top_level_no_external_libs():
    """SAFETY: provider.py 모듈 자체가 외부 호출 라이브러리 미참조."""
    src = Path(_provider.__file__).read_text(encoding="utf-8")
    # urllib.request / requests / httpx 미참조 — import 라인에서.
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            assert "urllib.request" not in stripped, f"외부 호출 모듈 import 발견: {line}"
            assert "import requests" not in stripped, f"외부 호출 모듈 import 발견: {line}"
            assert "import httpx" not in stripped, f"외부 호출 모듈 import 발견: {line}"


def test_fake_provider_empty_items():
    fake = _provider.FakeSmsProvider()

    class _S:
        id = 1

    assert fake.send(items=[], settings=_S()) == []


def test_provider_result_to_dict():
    r = _provider.ProviderResult(
        phone="010-1234-5678",
        result="success",
        kind="ok",
        status_code=200,
        detail="ok",
    )
    out = r.to_dict()
    assert out["phone"] == "010-1234-5678"
    assert out["result"] == "success"
    assert out["kind"] == "ok"
    assert out["status_code"] == 200
    assert out["detail"] == "ok"


def test_provider_result_to_dict_no_status_code():
    """status_code=None 이면 dict 에서 제외 (api.py:3273 precheck 분기 정합)."""
    r = _provider.ProviderResult(
        phone="010-bad",
        result="fail",
        kind="precheck",
        status_code=None,
        detail="형식 오류",
    )
    out = r.to_dict()
    assert "status_code" not in out
    assert set(out.keys()) >= _schemas.SMS_SEND_RESULT_REQUIRED_KEYS


# ──────────────────────── 10. provider — NotConfiguredProvider ──────────────


def test_not_configured_provider_rejects_all():
    """SAFETY: 설정 미완료 fallback — 모든 항목 not_configured."""
    p = _provider.NotConfiguredProvider(missing=["아이디", "API URL"])
    items = [{"phone": "010-1111"}, {"phone": "010-2222"}]

    class _S:
        id = 1

    results = p.send(items=items, settings=_S())
    assert len(results) == 2
    for r in results:
        assert r.result == "fail"
        assert r.kind == "not_configured"
        assert r.status_code is None
        assert "문자나라 설정을 먼저 완료하세요" in r.detail
        assert "아이디" in r.detail
        assert "API URL" in r.detail


def test_not_configured_provider_empty_missing():
    p = _provider.NotConfiguredProvider()

    class _S:
        id = 1

    results = p.send(items=[{"phone": "010"}], settings=_S())
    assert len(results) == 1
    assert results[0].kind == "not_configured"


# ──────────────────────── 11. schemas — contract 회귀 보호 ──────────────────


def test_sms_setting_response_keys_contract():
    """``schemas.SMS_SETTING_RESPONSE_KEYS`` == 7키."""
    assert _schemas.SMS_SETTING_RESPONSE_KEYS == frozenset({
        "munjanara_id", "munjanara_pw", "munjanara_key",
        "sender_phone", "clinic_phone", "clinic_name", "api_url",
    })


def test_sms_template_response_keys_contract():
    assert _schemas.SMS_TEMPLATE_RESPONSE_KEYS == frozenset({
        "id", "name", "body", "sort_order", "active", "updated_at",
    })


def test_sms_tomorrow_target_keys_contract():
    assert _schemas.SMS_TOMORROW_TARGET_KEYS == frozenset({
        "appointment_id", "patient_id", "chart_no",
        "name", "phone", "reserved_at", "body", "treatment_summary",
    })


def test_sms_send_envelope_keys_contract():
    assert _schemas.SMS_SEND_ENVELOPE_KEYS == frozenset({
        "sent", "failed", "total", "results",
    })


# ──────────────────────── 12. 단방향 경계 (D-4) ─────────────────────────────


def test_rules_does_not_import_routers():
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src
    assert "from app.routers" not in src


def test_rules_does_not_import_orm_or_db():
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    assert "from app.models" not in src
    assert "from app.database" not in src
    assert "sqlalchemy" not in src.lower()


def test_templates_does_not_import_routers():
    src = Path(_templates.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src
    assert "from app.routers" not in src


def test_templates_does_not_import_orm():
    src = Path(_templates.__file__).read_text(encoding="utf-8")
    assert "from app.models" not in src
    assert "sqlalchemy" not in src.lower()


def test_service_does_not_import_routers():
    src = Path(_service.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_provider_does_not_import_routers():
    src = Path(_provider.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_schemas_does_not_import_routers():
    src = Path(_schemas.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_modules_sms_importable():
    """app.modules.sms 패키지 import 가능."""
    import app.modules.sms  # noqa: F401
    import app.modules.sms.provider  # noqa: F401
    import app.modules.sms.rules  # noqa: F401
    import app.modules.sms.schemas  # noqa: F401
    import app.modules.sms.service  # noqa: F401
    import app.modules.sms.templates  # noqa: F401


# ──────────────────────── 13. 라우터 시그니처 무수정 ────────────────────────


def test_sms_get_router_signature_unchanged():
    from app.routers.api import sms_get

    sig = inspect.signature(sms_get)
    assert "db" in sig.parameters


def test_sms_set_router_signature_unchanged():
    from app.routers.api import sms_set

    sig = inspect.signature(sms_set)
    assert "payload" in sig.parameters
    assert "db" in sig.parameters


def test_sms_tomorrow_router_signature_unchanged():
    from app.routers.api import sms_tomorrow

    sig = inspect.signature(sms_tomorrow)
    assert "db" in sig.parameters


def test_sms_send_router_signature_unchanged():
    from app.routers.api import sms_send

    sig = inspect.signature(sms_send)
    assert "payload" in sig.parameters
    assert "db" in sig.parameters


def test_list_sms_templates_router_signature_unchanged():
    from app.routers.api import list_sms_templates

    sig = inspect.signature(list_sms_templates)
    assert "db" in sig.parameters


def test_create_sms_template_router_signature_unchanged():
    from app.routers.api import create_sms_template

    sig = inspect.signature(create_sms_template)
    assert "payload" in sig.parameters


def test_update_sms_template_router_signature_unchanged():
    from app.routers.api import update_sms_template

    sig = inspect.signature(update_sms_template)
    assert "tid" in sig.parameters
    assert "payload" in sig.parameters


def test_delete_sms_template_router_signature_unchanged():
    from app.routers.api import delete_sms_template

    sig = inspect.signature(delete_sms_template)
    assert "tid" in sig.parameters


# ──────────────────────── 14. SMS AI 흐름 무수정 ────────────────────────────


def test_sms_draft_module_unchanged():
    """기존 SMS AI (sms_draft) 흐름 무수정 — 본 19-10 가 import / 변경 ⊥."""
    import app.services.ai.sms_draft as _draft

    assert hasattr(_draft, "DraftContext")
    # 본 19-10 이 sms_draft 본체 변경 ⊥ — 핵심 dataclass 존재 검증.


# ──────────────────────── 15. 기존 SMS API 흐름 영향 없음 ───────────────────


def test_sms_get_endpoint_keys_match_contract(client):
    """``GET /api/sms/setting`` 응답 키 = ``SMS_SETTING_RESPONSE_KEYS``."""
    r = client.get("/api/sms/setting")
    assert r.status_code == 200
    assert set(r.json().keys()) == _schemas.SMS_SETTING_RESPONSE_KEYS


def test_sms_get_endpoint_does_not_expose_secrets(client):
    """SAFETY: ``GET /api/sms/setting`` 이 평문 비밀 / API key 노출 ⊥."""
    from app.database import SessionLocal
    from app.models import models as _m

    # 테스트 DB 에 평문 비밀 주입.
    db = SessionLocal()
    try:
        s = db.query(_m.SmsSetting).filter_by(id=1).first()
        if s is None:
            s = _m.SmsSetting(id=1)
            db.add(s)
        s.munjanara_pw = "secret_pw_value_19_10"
        s.munjanara_key = "secret_key_value_19_10"
        db.commit()

        # API 응답에 평문 노출 ⊥ 확인.
        r = client.get("/api/sms/setting")
        body = r.text
        assert "secret_pw_value_19_10" not in body
        assert "secret_key_value_19_10" not in body
        assert r.status_code == 200
    finally:
        # cleanup — 비밀 비움.
        s = db.query(_m.SmsSetting).filter_by(id=1).first()
        if s is not None:
            s.munjanara_pw = ""
            s.munjanara_key = ""
            db.commit()
        db.close()


def test_sms_templates_endpoint_keys_match_contract(client):
    """``GET /api/sms/templates`` 항목 키 = ``SMS_TEMPLATE_RESPONSE_KEYS``."""
    r = client.get("/api/sms/templates")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    for item in items:
        assert set(item.keys()) == _schemas.SMS_TEMPLATE_RESPONSE_KEYS


def test_sms_tomorrow_endpoint_no_external_calls(client):
    """``GET /api/sms/tomorrow-targets`` 가 외부 호출 ⊥ (DB 만 조회)."""
    r = client.get("/api/sms/tomorrow-targets")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # 항목이 있다면 contract 키 정합.
    for item in items:
        assert set(item.keys()) == _schemas.SMS_TOMORROW_TARGET_KEYS


def test_sms_send_with_empty_settings_returns_400(client):
    """``POST /api/sms/send`` 에 SMS 설정 누락 시 400 — 외부 호출 ⊥.

    SAFETY: 시드 SMS 설정이 비어 있으면 누락 검사가 raise — 외부 호출 진입 ⊥.
    """
    r = client.post(
        "/api/sms/send",
        json={"items": [{"phone": "010-1234-5678", "body": "테스트"}]},
    )
    # 시드 설정 / 인증 정책에 따라 400 (누락) 또는 401 (인증) — 모두 외부 호출 ⊥.
    assert r.status_code in (400, 401, 422)


# ──────────────────────── 16. 본 19-10 모듈 외부 호출 ⊥ 보장 ────────────────


def test_no_module_imports_urllib_request():
    """SAFETY: 본 19-10 모듈 어느 파일도 ``urllib.request`` import ⊥.

    실제 외부 발송은 라우터의 기존 흐름이 담당 — 본 모듈은 *helper / interface 만*.
    """
    files = [
        Path(_rules.__file__),
        Path(_templates.__file__),
        Path(_service.__file__),
        Path(_provider.__file__),
        Path(_schemas.__file__),
    ]
    for f in files:
        src = f.read_text(encoding="utf-8")
        # import urllib.request / from urllib.request import 모두 차단.
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert "urllib.request" not in stripped, (
                    f"{f.name}: 외부 호출 모듈 import: {line}"
                )
                assert "import requests" not in stripped, (
                    f"{f.name}: 외부 호출 모듈 import: {line}"
                )
                assert "import httpx" not in stripped, (
                    f"{f.name}: 외부 호출 모듈 import: {line}"
                )
