"""세션 13 — AI 자연어 치료사 휴무 등록 백엔드 테스트.

[docs/specs/04_ai_action_leave.md] § 13 의 T1~T29 시나리오 + 회귀.

⚠ 외부 LLM 호출 절대 금지 — FakeProvider (tests/conftest.py) 로 stub.

흐름:
  - parse 엔드포인트는 LLM 추출만 (DB 미접근, 토큰 발급 없음)
  - preview 엔드포인트는 LLM + DB 매칭/검증 + HMAC 토큰 발급 (DB write 없음)
  - execute 엔드포인트는 confirm + 토큰 검증 + EmployeeLeave upsert + AuditLog
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from app.database import SessionLocal
from app.models import models
from app.routers import ai as ai_router
from app.services.ai import action_leave as al
from app.services.ai.date_resolver import KST
from tests.conftest import FakeProvider
from tests.harness.seed_data import (
    FIXED_LEAVE_DATE,
    get_test_therapist_id,
)

# ─────────── 공통 헬퍼 ───────────

def _admin_token(client) -> str:
    """관리자 로그인 토큰 (테스트 시드 비번 admin1234)."""
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, f"admin login failed: {resp.status_code}"
    return resp.json().get("token", "")


@pytest.fixture(autouse=True, scope="module")
def _admin_authed_client(client):
    """이 모듈의 모든 테스트에서 client 에 X-Admin-Token 자동 부착.

    teardown 에서 해제 — 다른 테스트 모듈에 헤더가 leak 되지 않도록.
    """
    token = _admin_token(client)
    client.headers.update({"X-Admin-Token": token})
    yield
    client.headers.pop("X-Admin-Token", None)


def _llm_response(*, intent="create_therapist_leave", name="김테스트치료사",
                  date_text="4월30일", type_hint="full", kind_hint="annual",
                  confidence="high") -> str:
    """ParsedAction 스키마에 맞는 JSON 문자열."""
    return json.dumps({
        "intent": intent,
        "employee_name_raw": name,
        "original_date_text": date_text,
        "leave_type_hint": type_hint,
        "leave_kind_hint": kind_hint,
        "confidence": confidence,
    }, ensure_ascii=False)


def _enable_ai(db) -> None:
    """AiSetting.enabled=True + 임시 api_key/model 설정 (테스트용)."""
    s = db.query(models.AiSetting).filter(models.AiSetting.id == 1).first()
    if s is None:
        s = models.AiSetting(id=1)
        db.add(s)
    s.enabled = True
    s.provider = "openai"
    s.model = "gpt-4o-mini"
    s.api_key = "fake-test-key"
    db.commit()


def _disable_ai(db) -> None:
    s = db.query(models.AiSetting).filter(models.AiSetting.id == 1).first()
    if s is None:
        return
    s.enabled = False
    db.commit()


def _setup_fake(client, fake: FakeProvider) -> None:
    client.app.dependency_overrides[ai_router._action_leave_provider] = lambda: fake


def _teardown_fake(client) -> None:
    client.app.dependency_overrides.pop(ai_router._action_leave_provider, None)


def _freeze_time(monkeypatch, year=2026, month=4, day=30, hour=10) -> datetime:
    fixed = datetime(year, month, day, hour, 0, tzinfo=KST)
    monkeypatch.setattr(al, "_now_provider", lambda: fixed)
    return fixed


# ─────────── 시드 픽스처 ───────────

@pytest.fixture
def db():
    """직접 DB 핸들 (테스트 시드 추가용)."""
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def extra_seed(db):
    """T11 (퇴사한치료사) / T12 (홍의사) 시드. 멱등."""
    inactive_name = "퇴사한테스트치료사"
    doctor_name = "홍테스트의사"

    if not db.query(models.Employee).filter(models.Employee.name == inactive_name).first():
        db.add(models.Employee(
            name=inactive_name, role="therapist", color="#9CA3AF",
            active=False, can_eswt=True, can_manual=True, sort_order=99,
        ))
        db.commit()

    if not db.query(models.Employee).filter(models.Employee.name == doctor_name).first():
        db.add(models.Employee(
            name=doctor_name, role="doctor", color="#9CA3AF",
            active=True, can_eswt=False, can_manual=False, sort_order=100,
        ))
        db.commit()

    yield {"inactive": inactive_name, "doctor": doctor_name}


@pytest.fixture(autouse=True)
def _ai_enabled(db):
    """모든 테스트에서 AI 기능을 켜둔다 (test_T_disabled_endpoint 만 끔)."""
    _enable_ai(db)
    yield
    # 다른 테스트 영향 줄이기 위해 끔
    _disable_ai(db)


@pytest.fixture
def cleanup_leaves(db):
    """테스트 후 시드 픽스 날짜에 만들어진 EmployeeLeave 정리."""
    yield
    db.query(models.EmployeeLeave).filter(
        models.EmployeeLeave.leave_date.notin_([FIXED_LEAVE_DATE]),
    ).delete(synchronize_session=False)
    db.commit()


# ─────────── T1~T4 정상 플로우 ───────────

def test_T1_normal_create(client, db, monkeypatch, cleanup_leaves):
    """T1: '김테스트치료사 4월30일 종일 연차' → preview ok create → execute ok."""
    _freeze_time(monkeypatch, 2026, 4, 28)   # today=4월28일, target=4월30일
    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        # preview
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["outcome"] == "ok"
        assert body["safe_to_execute"] is True
        assert body["preview_token"]
        assert body["mode"] == "create"
        assert body["candidate"]["resolved_date"] == "2026-04-30"
        assert body["candidate"]["leave_type"] == "full"
        assert body["candidate"]["leave_kind"] == "annual"

        # execute
        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": body["preview_token"],
            "confirm": True,
            "memo": "AI 등록",
        })
        assert r2.status_code == 200, r2.text
        body2 = r2.json()
        assert body2["ok"] is True
        assert body2["mode"] == "create"
        leave_id = body2["leave_id"]
        assert leave_id

        # DB 검증 — EmployeeLeave 1건 + AuditLog 1건
        leave = db.query(models.EmployeeLeave).filter(
            models.EmployeeLeave.id == leave_id,
        ).first()
        assert leave is not None
        assert leave.leave_type == "full"
        assert leave.leave_kind == "annual"
        assert leave.memo == "AI 등록"

        audit = db.query(models.AuditLog).filter(
            models.AuditLog.action == "ai.leave.create",
            models.AuditLog.entity_id == leave_id,
        ).first()
        assert audit is not None

        # AiUsageLog ≥ 2건 (preview + execute)
        usage_count = db.query(models.AiUsageLog).filter(
            models.AiUsageLog.feature.in_(("action_leave_preview", "action_leave_execute")),
        ).count()
        assert usage_count >= 2
    finally:
        _teardown_fake(client)


def test_T2_tomorrow_morning(client, db, monkeypatch, cleanup_leaves):
    """T2: '이테스트치료사 내일 오전반차' → resolved=내일, type=am (DB 표준)."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(
        name="이테스트치료사", date_text="내일", type_hint="morning",
    ))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "이테스트치료사 내일 오전반차",
        })
        body = r.json()
        assert body["safe_to_execute"] is True, body
        assert body["candidate"]["resolved_date"] == "2026-04-29"
        assert body["candidate"]["leave_type"] == "am"
        assert body["candidate"]["assumption"]   # 상대일은 assumption 채워야 함
    finally:
        _teardown_fake(client)


def test_T3_next_week_monday_afternoon(client, db, monkeypatch, cleanup_leaves):
    """T3: '박테스트치료사 다음주 월요일 오후반차' → resolved=다음주 월요일, type=pm."""
    # 2026-04-28 = 화요일 (ISO weekday=2). 다음주 월요일 = 2026-05-04
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(
        name="박테스트치료사", date_text="다음주 월요일", type_hint="afternoon",
    ))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "박테스트치료사 다음주 월요일 오후반차",
        })
        body = r.json()
        assert body["safe_to_execute"] is True, body
        assert body["candidate"]["resolved_date"] == "2026-05-04"
        assert body["candidate"]["leave_type"] == "pm"
    finally:
        _teardown_fake(client)


def test_T4_day_only_monthly(client, db, monkeypatch, cleanup_leaves):
    """T4: '김테스트치료사 30일 월차' → assumption 채움 + leave_kind=monthly."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(
        date_text="30일", kind_hint="monthly",
    ))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 30일 월차",
        })
        body = r.json()
        assert body["safe_to_execute"] is True, body
        assert body["candidate"]["resolved_date"] == "2026-04-30"
        assert body["candidate"]["leave_kind"] == "monthly"
        assert body["candidate"]["assumption"]
        assert any("월이 생략" in w or "현재 월" in w for w in body["warnings"])
    finally:
        _teardown_fake(client)


# ─────────── T5~T9 모호/차단 ───────────

def test_T5_ambiguous_date(client, db, monkeypatch):
    """T5: '김테스트치료사 말일쯤 휴무' → ambiguous_date."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="말일쯤"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 말일쯤 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "ambiguous_date"
        assert body["preview_token"] is None
    finally:
        _teardown_fake(client)


def test_T6_ambiguous_half_day(client, db, monkeypatch):
    """T6: '김테스트치료사 5월30일 반차' → ambiguous_half_day."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="5월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 5월30일 반차",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "ambiguous_half_day"
    finally:
        _teardown_fake(client)


def test_T7_invalid_date(client, db, monkeypatch):
    """T7: '김테스트치료사 2월30일 종일' → invalid_date."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="2월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 2월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "invalid_date"
    finally:
        _teardown_fake(client)


def test_T8_past_out_of_range(client, db, monkeypatch):
    """T8: '김테스트치료사 2024-01-01 종일' → out_of_range_date (과거 90일↑)."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="2024-01-01"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 2024-01-01 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "out_of_range_date"
    finally:
        _teardown_fake(client)


def test_T9_future_out_of_range(client, db, monkeypatch):
    """T9: '김테스트치료사 2030-01-01 종일' → out_of_range_date (미래 365일↑)."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="2030-01-01"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 2030-01-01 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "out_of_range_date"
    finally:
        _teardown_fake(client)


# ─────────── T10~T12 매칭 ───────────

def test_T10_no_match(client, monkeypatch):
    """T10: '없는치료사 4월30일 종일' → no_match."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(name="없는테스트치료사"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "없는테스트치료사 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "no_match"
    finally:
        _teardown_fake(client)


def test_T11_inactive(client, extra_seed, monkeypatch):
    """T11: 비활성 치료사 → inactive_therapist."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(name=extra_seed["inactive"]))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": f"{extra_seed['inactive']} 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "inactive_therapist"
    finally:
        _teardown_fake(client)


def test_T12_not_therapist(client, extra_seed, monkeypatch):
    """T12: role=doctor → not_therapist."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(name=extra_seed["doctor"]))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": f"{extra_seed['doctor']} 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "not_therapist"
    finally:
        _teardown_fake(client)


# ─────────── T13~T15 충돌 ───────────

def test_T13_overwrite_then_block_without_ack(client, db, monkeypatch, cleanup_leaves):
    """T13: 같은 키 다른 값 → mode=overwrite. ack 없이 execute 하면 차단."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    # 사전 휴무 (오전 반차) 시드 — DB 표준 am/pm/full
    emp_id = get_test_therapist_id("김테스트치료사")
    target_date = "2026-04-30"
    db.add(models.EmployeeLeave(
        employee_id=emp_id, leave_date=target_date,
        leave_type="am", leave_kind="annual", memo="기존",
    ))
    db.commit()

    fake = FakeProvider(return_text=_llm_response(date_text="4월30일", type_hint="full"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        body = r.json()
        assert body["safe_to_execute"] is True
        assert body["mode"] == "overwrite"
        assert any("덮어씁니다" in w for w in body["warnings"])

        # ack=False → 차단 (400)
        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": body["preview_token"],
            "confirm": True,
            "overwrite_acknowledged": False,
            "memo": "",
        })
        assert r2.status_code == 400
        assert r2.json()["outcome"] == "overwrite_not_acknowledged"

        # ack=True → 통과
        r3 = client.post("/api/ai/action/execute", json={
            "preview_token": body["preview_token"],
            "confirm": True,
            "overwrite_acknowledged": True,
            "memo": "",
        })
        assert r3.status_code == 200
        assert r3.json()["mode"] == "overwrite"

        leave = db.query(models.EmployeeLeave).filter(
            models.EmployeeLeave.employee_id == emp_id,
            models.EmployeeLeave.leave_date == target_date,
        ).first()
        assert leave.leave_type == "full"     # 덮어쓰기 성공
    finally:
        _teardown_fake(client)


def test_T14_noop_same_value(client, db, monkeypatch, cleanup_leaves):
    """T14: 같은 키 같은 값 → mode=noop, warnings 에 안내."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    emp_id = get_test_therapist_id("김테스트치료사")
    target_date = "2026-04-30"
    db.add(models.EmployeeLeave(
        employee_id=emp_id, leave_date=target_date,
        leave_type="full", leave_kind="annual", memo="",
    ))
    db.commit()

    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        body = r.json()
        assert body["mode"] == "noop"
        assert any("같은 내용" in w for w in body["warnings"])
        assert body["safe_to_execute"] is True   # noop 도 안전 (재실행해도 동일)
    finally:
        _teardown_fake(client)


def test_T15_appointment_warning(client, db, monkeypatch, cleanup_leaves):
    """T15: 그 날짜에 예약 N건 → warnings 에 알림 (차단 X)."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    emp_id = get_test_therapist_id("김테스트치료사")
    # 환자 + 예약 시드 (검증용)
    pat = models.Patient(name="테스트환자_T15")
    db.add(pat)
    db.flush()
    a = models.Appointment(
        patient_id=pat.id, therapist_id=emp_id,
        start_at=datetime(2026, 4, 30, 10, 0),
        end_at=datetime(2026, 4, 30, 10, 30),
        duration_min=30, treatment_codes='["manual30"]',
        status="reserved",
    )
    db.add(a)
    db.commit()

    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        body = r.json()
        assert body["safe_to_execute"] is True   # warning 만 — 차단 X
        assert body["appointments_count"] >= 1
        assert any("예약" in w for w in body["warnings"])
    finally:
        _teardown_fake(client)
        # 시드 정리
        db.query(models.Appointment).filter(models.Appointment.id == a.id).delete()
        db.query(models.Patient).filter(models.Patient.id == pat.id).delete()
        db.commit()


# ─────────── T16~T24 보안/위조 ───────────

def test_T16_no_token(client):
    """T16: token 없이 execute → 400 token_format."""
    r = client.post("/api/ai/action/execute", json={
        "preview_token": "",
        "confirm": True,
    })
    assert r.status_code == 400
    body = r.json()
    assert body["outcome"] in ("token_format", "token_signature")


def test_T17_token_signature_forged(client):
    """T17: 위조한 token → 400 token_signature."""
    forged = "abcd.0000000000000000000000000000000000000000000000000000000000000000"
    r = client.post("/api/ai/action/execute", json={
        "preview_token": forged,
        "confirm": True,
    })
    assert r.status_code == 400
    assert r.json()["outcome"] in ("token_format", "token_signature")


def test_T18_token_expired(client, db, monkeypatch, cleanup_leaves):
    """T18: 만료된 token → 400 token_expired."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        token = r.json()["preview_token"]
        # token 의 exp 이 지난 시각으로 _now_provider 를 미래로 점프
        future = datetime(2027, 1, 1, 0, 0, tzinfo=KST)
        monkeypatch.setattr(al, "_now_provider", lambda: future)

        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": token,
            "confirm": True,
        })
        assert r2.status_code == 400
        assert r2.json()["outcome"] == "token_expired"
    finally:
        _teardown_fake(client)


def test_T19_token_unsafe_unreachable(client, db, monkeypatch):
    """T19: safe=False 로 발급된 토큰은 _issue_token 이 만들지 않음.

    실제 코드는 차단 케이스에서 token 자체를 None 으로 반환하므로 token_unsafe 는
    내부 가드 — 직접 위조 시 token_signature 에서 막힘. 통합으로는 도달 불가능
    경로 → 단위 테스트로 _verify_token 의 token_unsafe 분기만 검증.
    """
    # 직접 _issue_token 으로 safe_to_execute=False 토큰 만들기
    token, _exp = al._issue_token({
        "intent": al.INTENT_NAME,
        "employee_id": "x" * 32,
        "leave_date": "2026-04-30",
        "leave_type": "full",
        "leave_kind": "annual",
        "mode": "create",
        "existing_id": None,
        "safe_to_execute": False,    # ← 강제로 False
    })
    with pytest.raises(al._InvalidToken) as excinfo:
        al._verify_token(token, now_unix=int(datetime.now(KST).timestamp()))
    assert excinfo.value.outcome == "token_unsafe"


def test_T20_token_mismatch_invalid_payload(client):
    """T20: 페이로드의 leave_type 이 enum 외 값 → token_mismatch."""
    token, _exp = al._issue_token({
        "intent": al.INTENT_NAME,
        "employee_id": "x" * 32,
        "leave_date": "2026-04-30",
        "leave_type": "BOGUS",     # ← 잘못된 값 (서명은 valid)
        "leave_kind": "annual",
        "mode": "create",
        "existing_id": None,
        "safe_to_execute": True,
    })
    with pytest.raises(al._InvalidToken) as excinfo:
        al._verify_token(token, now_unix=int(datetime.now(KST).timestamp()))
    assert excinfo.value.outcome == "token_mismatch"


def test_T21_not_confirmed(client, db, monkeypatch, cleanup_leaves):
    """T21: confirm=False → 400 not_confirmed."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        token = r.json()["preview_token"]

        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": token,
            "confirm": False,      # ← 미확인
        })
        assert r2.status_code == 400
        assert r2.json()["outcome"] == "not_confirmed"
    finally:
        _teardown_fake(client)


def test_T22_overwrite_not_acknowledged(client, db, monkeypatch, cleanup_leaves):
    """T22: mode=overwrite + ack=False → 400 overwrite_not_acknowledged. (T13 과 중복)"""
    # T13 에서 검증 완료 — 여기는 별칭 테스트
    _freeze_time(monkeypatch, 2026, 4, 28)
    emp_id = get_test_therapist_id("김테스트치료사")
    target_date = "2026-04-30"
    db.add(models.EmployeeLeave(
        employee_id=emp_id, leave_date=target_date,
        leave_type="am", leave_kind="annual",
    ))
    db.commit()

    fake = FakeProvider(return_text=_llm_response(date_text="4월30일", type_hint="full"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        token = r.json()["preview_token"]
        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": token,
            "confirm": True,
            "overwrite_acknowledged": False,
        })
        assert r2.status_code == 400
        assert r2.json()["outcome"] == "overwrite_not_acknowledged"
    finally:
        _teardown_fake(client)


def test_T22b_outcome_full_length_persisted(client, db, monkeypatch, cleanup_leaves):
    """outcome='overwrite_not_acknowledged' (26자) 가 truncate 없이 AiUsageLog 에 저장되는지.

    회귀: 이전엔 String(20) + ai_logging.py [:20] 로 'overwrite_not_acknow' 으로 잘림.
    수정 후엔 String(50) + [:50] 으로 full 값이 DB 에 저장되어야 함.
    legacy `status` 컬럼은 [:20] 그대로 유지되어 잘림 — 호환성 의도.
    """
    _freeze_time(monkeypatch, 2026, 4, 28)
    emp_id = get_test_therapist_id("김테스트치료사")
    target_date = "2026-04-30"

    # 사전 정리 — 이전 테스트 leak 방지
    db.query(models.AiUsageLog).filter(
        models.AiUsageLog.outcome.like("overwrite_not%"),
    ).delete(synchronize_session=False)
    db.query(models.EmployeeLeave).filter(
        models.EmployeeLeave.leave_date == target_date,
    ).delete(synchronize_session=False)
    db.commit()

    db.add(models.EmployeeLeave(
        employee_id=emp_id, leave_date=target_date,
        leave_type="am", leave_kind="annual",
    ))
    db.commit()

    fake = FakeProvider(return_text=_llm_response(date_text="4월30일", type_hint="full"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        token = r.json()["preview_token"]
        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": token,
            "confirm": True,
            "overwrite_acknowledged": False,
        })
        assert r2.status_code == 400
        assert r2.json()["outcome"] == "overwrite_not_acknowledged"

        # DB 의 AiUsageLog 에 full 값이 저장되었는지 확인 — 이게 핵심 회귀 어서션
        db.expire_all()
        log = (
            db.query(models.AiUsageLog)
            .filter(models.AiUsageLog.feature == "action_leave_execute")
            .filter(models.AiUsageLog.outcome.like("overwrite_not%"))
            .order_by(models.AiUsageLog.ts.desc())
            .first()
        )
        assert log is not None, "AiUsageLog 에 overwrite_not 관련 row 가 없음"
        assert log.outcome == "overwrite_not_acknowledged", (
            f"outcome 이 truncate 됨: {log.outcome!r} (length={len(log.outcome)})"
        )
        # legacy status 는 [:20] 잘림 의도 그대로 — 호환성
        assert log.status == "overwrite_not_acknow", (
            f"legacy status 컬럼은 [:20] 잘림 그대로여야 함: {log.status!r}"
        )
    finally:
        _teardown_fake(client)


def test_T23_conflict_changed_after_preview(client, db, monkeypatch, cleanup_leaves):
    """T23: preview 후 다른 사용자가 같은 키 등록 → execute 409 conflict_changed."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        token = r.json()["preview_token"]
        assert r.json()["mode"] == "create"

        # preview 후, 다른 경로로 휴무 등록 (race 시뮬레이션)
        emp_id = get_test_therapist_id("김테스트치료사")
        db.add(models.EmployeeLeave(
            employee_id=emp_id, leave_date="2026-04-30",
            leave_type="am", leave_kind="annual", memo="race",
        ))
        db.commit()

        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": token,
            "confirm": True,
        })
        assert r2.status_code == 409
        assert r2.json()["outcome"] == "conflict_changed"
    finally:
        _teardown_fake(client)


def test_T24_therapist_changed_after_preview(client, db, monkeypatch, cleanup_leaves):
    """T24: preview 후 치료사 비활성화 → execute 409 therapist_changed."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    emp_id = get_test_therapist_id("박테스트치료사")
    fake = FakeProvider(return_text=_llm_response(name="박테스트치료사", date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "박테스트치료사 4월30일 종일 연차",
        })
        token = r.json()["preview_token"]
        assert r.status_code == 200

        # preview 후 치료사 비활성화
        emp = db.query(models.Employee).filter(models.Employee.id == emp_id).first()
        emp.active = False
        db.commit()

        r2 = client.post("/api/ai/action/execute", json={
            "preview_token": token,
            "confirm": True,
        })
        assert r2.status_code == 409
        assert r2.json()["outcome"] == "therapist_changed"
    finally:
        _teardown_fake(client)
        # 복구
        emp = db.query(models.Employee).filter(models.Employee.id == emp_id).first()
        if emp:
            emp.active = True
            db.commit()


# ─────────── T25~T29 할루시네이션 ───────────

def test_T25_hallucinated_name(client, monkeypatch):
    """T25: LLM 이 입력에 없는 이름 반환 → hallucinated_name."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(
        name="가짜이름환자",     # 입력에 없음
        date_text="4월30일",
    ))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "hallucinated_name"
    finally:
        _teardown_fake(client)


def test_T26_hallucinated_date(client, monkeypatch):
    """T26: LLM 이 입력에 없는 날짜 토큰 반환 → hallucinated_date."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(
        date_text="2099-12-31",   # 입력에 없음
    ))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "hallucinated_date"
    finally:
        _teardown_fake(client)


def test_T27_intent_mismatch(client, monkeypatch):
    """T27: LLM 이 intent='other' → ParsedAction Literal 실패 → parse_fail."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    bogus = json.dumps({
        "intent": "other",     # Literal 위반
        "employee_name_raw": "김테스트치료사",
        "original_date_text": "4월30일",
        "leave_type_hint": "full",
        "leave_kind_hint": "annual",
        "confidence": "high",
    }, ensure_ascii=False)
    fake = FakeProvider(return_text=bogus)
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        # Pydantic Literal 실패는 parse_fail 로 분류
        assert body["outcome"] == "parse_fail"
    finally:
        _teardown_fake(client)


def test_T28_low_confidence(client, monkeypatch):
    """T28: LLM 이 confidence='low' → low_confidence."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(confidence="low"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "low_confidence"
    finally:
        _teardown_fake(client)


def test_T29_parse_fail(client, monkeypatch):
    """T29: LLM 이 깨진 JSON → parse_fail."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text="이건 JSON 이 아닙니다 — 일반 텍스트")
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "parse_fail"
    finally:
        _teardown_fake(client)


# ─────────── 추가: parse 엔드포인트 (DB 미접근) ───────────

def test_parse_endpoint_returns_candidate(client, db, monkeypatch):
    """/api/ai/action/parse 는 LLM 추출 결과만 반환. DB 매칭 없음."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    leave_count_before = db.query(models.EmployeeLeave).count()

    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/parse", json={
            "text": "김테스트치료사 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["ok"] is True
        assert body["outcome"] == "ok"
        assert body["parsed"]["employee_name_raw"] == "김테스트치료사"
        assert body["parsed"]["original_date_text"] == "4월30일"
        # parse 자체는 토큰 발급 안 함
        assert "preview_token" not in body
    finally:
        _teardown_fake(client)

    # parse 호출은 DB 를 수정하지 않아야 함 (휴무 수 변화 없음)
    leave_count_after = db.query(models.EmployeeLeave).count()
    assert leave_count_before == leave_count_after


# ─────────── 추가: preview 가 DB 를 수정하지 않는지 ───────────

def test_preview_does_not_write_db(client, db, monkeypatch):
    _freeze_time(monkeypatch, 2026, 4, 28)
    leave_count_before = db.query(models.EmployeeLeave).count()
    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 휴무",
        })
    finally:
        _teardown_fake(client)
    leave_count_after = db.query(models.EmployeeLeave).count()
    assert leave_count_before == leave_count_after


# ─────────── 추가: 입력 사전 게이트 ───────────

def test_no_leave_keyword(client, monkeypatch):
    """휴무 키워드 없으면 LLM 호출 자체 안 하고 차단."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response())
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 점심먹자",
        })
        body = r.json()
        assert body["outcome"] == "no_leave_keyword"
        assert body["safe_to_execute"] is False
        assert len(fake.calls) == 0     # LLM 호출 0회
    finally:
        _teardown_fake(client)


def test_pii_blocked_phone(client, monkeypatch):
    """입력에 전화번호 → pii_blocked. LLM 호출 안 함."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response())
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "010-1234-5678 김테스트치료사 4월30일 휴무",
        })
        body = r.json()
        assert body["outcome"] == "pii_blocked"
        assert len(fake.calls) == 0
    finally:
        _teardown_fake(client)


def test_pii_blocked_chart_no(client, monkeypatch):
    """입력에 5자리 이상 순수 숫자 (차트번호 의심) → pii_blocked. LLM 호출 안 함."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response())
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 휴무 123456",
        })
        body = r.json()
        assert body["outcome"] == "pii_blocked"
        assert len(fake.calls) == 0
    finally:
        _teardown_fake(client)


def test_pii_blocked_patient_keyword(client, monkeypatch):
    """입력에 환자 관련 키워드 (환자/차트/내원 등) → pii_blocked. LLM 호출 안 함."""
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response())
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 휴무 환자 홍길동",
        })
        body = r.json()
        assert body["outcome"] == "pii_blocked"
        assert len(fake.calls) == 0
    finally:
        _teardown_fake(client)


def test_pii_blocked_double_birth(client, monkeypatch):
    """birth 패턴 (YYYY-MM-DD) 이 2회 이상 등장 → pii_blocked.

    1회 (휴무 날짜) 는 통과. 2회 이상이면 환자 생년월일 동반 추정 → 차단.
    """
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response())
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 2026-04-30 휴무 1990-05-15",
        })
        body = r.json()
        assert body["outcome"] == "pii_blocked"
        assert len(fake.calls) == 0
    finally:
        _teardown_fake(client)


# ─────────── 추가: AI 비활성 시 503 ───────────

def test_endpoint_503_when_disabled(client, db):
    """AI 비활성 시 preview/execute 둘 다 503."""
    _disable_ai(db)
    r = client.post("/api/ai/action/preview", json={"text": "김테스트치료사 4월30일 휴무"})
    assert r.status_code == 503


# ─────────── 회귀: 기존 휴무 API 동작 ───────────

def test_regression_legacy_leave_api(client, db, cleanup_leaves):
    """_upsert_employee_leave_core 추출 후 /api/employee-leaves 동작 확인.

    DB 표준 am/pm/full 로 round-trip 검증 (기존 캘린더 / fetchLeavesOn 호환).
    """
    emp_id = get_test_therapist_id("김테스트치료사")
    r = client.post("/api/employee-leaves", json={
        "employee_id": emp_id,
        "leave_date": "2027-01-15",
        "leave_type": "am",
        "leave_kind": "annual",
        "memo": "회귀",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["leave_type"] == "am"
    assert body["leave_kind"] == "annual"

    # upsert 동작
    r2 = client.post("/api/employee-leaves", json={
        "employee_id": emp_id,
        "leave_date": "2027-01-15",
        "leave_type": "pm",
        "leave_kind": "monthly",
        "memo": "갱신",
    })
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["id"] == body["id"]      # 같은 row (upsert)
    assert body2["leave_type"] == "pm"
    assert body2["leave_kind"] == "monthly"


# ─────────── 세션 15: 추가 검증 (보안·할루시네이션·PII·매칭·회귀) ───────────

def test_T_multi_match_blocked(client, db, monkeypatch, cleanup_leaves):
    """동명이인 active 치료사 2명 → multi_match 차단 (자동 선택 금지).

    spec § 5.3: 정확 일치 ≥ 2 → 차단 + 사용자가 다른 식별자로 재입력.
    """
    _freeze_time(monkeypatch, 2026, 4, 28)
    # 동명이인 2명 시드 (멱등 처리는 cleanup 에 맡김)
    duplicate_name = "동명테스트치료사"
    existing = db.query(models.Employee).filter(
        models.Employee.name == duplicate_name,
    ).all()
    extra_ids: list[str] = []
    if len(existing) < 2:
        for i in range(2 - len(existing)):
            e = models.Employee(
                name=duplicate_name, role="therapist", color="#9CA3AF",
                active=True, can_eswt=True, can_manual=True,
                sort_order=200 + i,
            )
            db.add(e)
            db.flush()
            extra_ids.append(e.id)
        db.commit()

    fake = FakeProvider(return_text=_llm_response(
        name=duplicate_name, date_text="4월30일",
    ))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": f"{duplicate_name} 4월30일 종일 휴무",
        })
        body = r.json()
        assert r.status_code == 200
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "multi_match"
        assert body["preview_token"] is None  # 차단 시 토큰 미발급
    finally:
        _teardown_fake(client)
        # 시드 정리
        if extra_ids:
            db.query(models.Employee).filter(
                models.Employee.id.in_(extra_ids),
            ).delete(synchronize_session=False)
            db.commit()


def test_T_partial_name_rejected(client, monkeypatch):
    """부분/유사 이름 매칭 금지 — '김테스트' 만 입력 시 no_match (자동 선택 금지).

    spec § 5.3: '부분/유사 매칭 절대 금지'. 시드된 '김테스트치료사' 와
    부분 일치하지만 정확 일치는 아니므로 no_match.
    """
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(
        name="김테스트", date_text="4월30일",   # 정확 일치하는 직원 없음
    ))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트 4월30일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "no_match"
        assert body["preview_token"] is None
    finally:
        _teardown_fake(client)


def test_T_day_before_today_ambiguous(client, monkeypatch):
    """'D일' 인데 D < today.day → ambiguous_date (다음달 자동 보정 금지).

    spec § 3.3: '의도 추정 금지'. today=4/28 일 때 입력 '20일' 은 모호 → 차단.
    사용자가 '다음달 20일' 로 명시하도록 강제.
    """
    _freeze_time(monkeypatch, 2026, 4, 28)
    fake = FakeProvider(return_text=_llm_response(date_text="20일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 20일 종일 휴무",
        })
        body = r.json()
        assert body["safe_to_execute"] is False
        assert body["outcome"] == "ambiguous_date"
    finally:
        _teardown_fake(client)


def test_no_patient_or_appointment_pii_in_llm_prompt(client, db, monkeypatch, cleanup_leaves):
    """LLM prompt 에 환자명·전화·차트번호·예약id 가 포함되지 않는지 검증.

    spec § 10.3 + plan § 4-7: AI 휴무 흐름은 환자/예약 컨텍스트를 LLM 에 전달하지 않는다.
    같은 날짜에 환자+예약 시드가 있어도, prompt 에는 사용자 입력 텍스트만 들어가야 함.
    """
    _freeze_time(monkeypatch, 2026, 4, 28)
    emp_id = get_test_therapist_id("김테스트치료사")
    # PII 가 들어간 환자 + 예약 시드
    pat = models.Patient(
        name="김유출환자", phone="010-9999-8888",
        birth_date="1990-01-01", chart_no="LEAK-001",
    )
    db.add(pat)
    db.flush()
    a = models.Appointment(
        patient_id=pat.id, therapist_id=emp_id,
        start_at=datetime(2026, 4, 30, 10, 0),
        end_at=datetime(2026, 4, 30, 10, 30),
        duration_min=30, treatment_codes='["manual30"]',
        status="reserved", memo="비밀메모-LEAK",
    )
    db.add(a)
    db.commit()

    fake = FakeProvider(return_text=_llm_response(date_text="4월30일"))
    _setup_fake(client, fake)
    try:
        r = client.post("/api/ai/action/preview", json={
            "text": "김테스트치료사 4월30일 종일 연차",
        })
        assert r.status_code == 200
        # LLM 호출은 1회만, 그 prompt 에 PII 유출 검증
        assert len(fake.calls) == 1, fake.calls
        call = fake.calls[0]
        haystack = (call.get("prompt") or "") + "\n" + (call.get("system") or "")
        # 환자 PII 가 LLM 으로 새지 않아야 함
        assert "김유출환자" not in haystack
        assert "010-9999-8888" not in haystack
        assert "1990-01-01" not in haystack
        assert "LEAK-001" not in haystack
        # 예약 식별자 / 메모도 미포함
        assert a.id not in haystack
        assert "비밀메모-LEAK" not in haystack
    finally:
        _teardown_fake(client)
        db.query(models.Appointment).filter(models.Appointment.id == a.id).delete()
        db.query(models.Patient).filter(models.Patient.id == pat.id).delete()
        db.commit()


def test_T_random_payload_with_bad_sig_blocked(client):
    """임의 base64 페이로드 + 잘못된 시그니처 → execute 400 token_signature.

    공격자가 토큰 페이로드를 valid JSON 으로 만들어도 HMAC 시그니처를 모르면 차단.
    server_secret 없이 발급된 토큰은 절대 통과 못함.
    """
    import base64
    import json as _json

    # 정상 형태의 페이로드 (intent/employee_id/leave_date/leave_type/leave_kind/mode/safe...)
    payload = {
        "v": 1,
        "intent": "create_therapist_leave",
        "employee_id": "x" * 32,
        "leave_date": "2026-04-30",
        "leave_type": "full",
        "leave_kind": "annual",
        "mode": "create",
        "existing_id": None,
        "safe_to_execute": True,
        "exp": 9999999999,    # 만료 안 됨
    }
    body_json = _json.dumps(payload, sort_keys=True, separators=(",", ":"))
    body_b64 = base64.urlsafe_b64encode(body_json.encode("utf-8")).decode("ascii").rstrip("=")
    forged_token = f"{body_b64}.{'0' * 64}"   # ← 시그니처 위조

    r = client.post("/api/ai/action/execute", json={
        "preview_token": forged_token,
        "confirm": True,
    })
    assert r.status_code == 400
    assert r.json()["outcome"] == "token_signature"
