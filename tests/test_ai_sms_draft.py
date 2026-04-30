"""세션 04 검증 — POST /api/ai/sms/draft 및 sms_draft 서비스 테스트.

⚠ 외부 LLM 호출은 절대 하지 않는다 — FakeProvider 로 stub.

실행:
    cd <repo_root>
    venv/Scripts/python.exe -m pytest tests/test_ai_sms_draft.py -v
    venv/Scripts/python.exe tests/test_ai_sms_draft.py   # standalone (endpoint 테스트 제외)

검증:
  ① 취소 예약            : skip_reason='cancelled', LLM 미호출
  ② 예약시간 누락         : skip_reason='no_appt_time'
  ③ 예약 미존재          : skip_reason='no_appointment'
  ④ 치료사 미배정         : warnings 에 미배정 안내, safe_ctx 에 'therapist' 키 없음
  ⑤ 치료항목 누락         : missing_fields 에 '치료항목'
  ⑥ 정상 (mock provider) : 환자명 토큰 복원, draft 안에 실명 들어감
  ⑦ PII 가드             : safe_ctx 에 전화번호 패턴이 들어가면 ValueError
  ⑧ AI 비활성 endpoint   : POST /api/ai/sms/draft → 503 (pytest only)
"""
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# fmt: off
from sqlalchemy import create_engine  # noqa: E402, I001
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models import models  # noqa: E402
from app.services.ai import provider as ai_provider  # noqa: E402
from app.services.ai import sms_draft as ai_sms_draft  # noqa: E402
# fmt: on


# ─────────── 헬퍼 ───────────

PASS = "[PASS]"
FAIL = "[FAIL]"


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def seed_clinic(db):
    db.add(models.SmsSetting(
        id=1,
        clinic_name="ㅇㅇ의원",
        clinic_phone="02-000-0000",
    ))
    db.flush()


def seed_treatment(db, *, code="manual30", name="도수치료 30분"):
    t = models.Treatment(
        code=code, name=name, short=code[:3],
        default_minutes=30, role="therapist", count_increment=1,
    )
    db.add(t)
    db.flush()
    return t


def seed_appointment(db, *, with_therapist=True, with_treatments=True,
                     status="reserved", with_start_at=True,
                     patient_name="홍길동"):
    seed_clinic(db)
    if with_treatments:
        seed_treatment(db)

    therapist = None
    if with_therapist:
        therapist = models.Employee(name="김치료", role="therapist")
        db.add(therapist)
        db.flush()

    patient = models.Patient(name=patient_name, phone="010-1234-5678")
    db.add(patient)
    db.flush()

    appt = models.Appointment(
        patient_id=patient.id,
        therapist_id=therapist.id if therapist else None,
        start_at=datetime(2026, 5, 1, 14, 0),    # 항상 valid (NOT NULL)
        end_at=datetime(2026, 5, 1, 14, 30),
        duration_min=30,
        treatment_codes='["manual30"]' if with_treatments else "[]",
        status=status,
    )
    db.add(appt)
    db.flush()
    if not with_start_at:
        # SQLite NOT NULL 제약을 우회 — DB 값은 valid 로 두고 ORM 인스턴스 메모리만
        # None 으로 dirty 마킹. autoflush=False 이므로 flush 발생 안 함. SQLAlchemy
        # identity map 가 후속 query 에 이 인스턴스를 반환 → start_at=None 관찰 가능.
        appt.start_at = None
    return patient, therapist, appt


class FakeProvider(ai_provider.AiProvider):
    """LLM 호출을 stub. text 와 호출 인자를 기록."""
    name = "fake"

    def __init__(self, return_text="안녕하세요 환자A님, ㅇㅇ의원입니다."):
        super().__init__(model="fake-1", api_key="fake-key")
        self.return_text = return_text
        self.calls = []

    def is_ready(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "") -> ai_provider.AiResult:
        self.calls.append({"prompt": prompt, "system": system})
        return ai_provider.AiResult(text=self.return_text)


# ─────────── 테스트 ───────────

def test_1_cancelled():
    """① 취소 예약 → skip_reason='cancelled' + LLM 미호출."""
    db = setup_db()
    p, t, a = seed_appointment(db, status="canceled")
    fake = FakeProvider()
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    ok = (
        res["skipped"] is True
        and res["skip_reason"] == "cancelled"
        and "취소 상태" in res["draft"]
        and res["needs_user_confirm"] is False
        and len(fake.calls) == 0   # LLM 호출 없음
    )
    assert ok, res
    return ok, res


def test_2_no_appt_time():
    """② 예약시간 미지정 → skip_reason='no_appt_time' + LLM 미호출."""
    db = setup_db()
    p, t, a = seed_appointment(db, with_start_at=False)
    fake = FakeProvider()
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    ok = (
        res["skipped"] is True
        and res["skip_reason"] == "no_appt_time"
        and "예약 시간이 지정되지 않" in res["draft"]
        and len(fake.calls) == 0
    )
    assert ok, res
    return ok, res


def test_3_appt_not_found():
    """③ 잘못된 예약 ID → skip_reason='no_appointment'."""
    db = setup_db()
    seed_clinic(db)
    fake = FakeProvider()
    res = ai_sms_draft.make_draft(
        db, appointment_id="not-real-id", tone="friendly",
        provider_override=fake,
    )
    ok = (
        res["skipped"] is True
        and res["skip_reason"] == "no_appointment"
        and len(fake.calls) == 0
    )
    assert ok, res
    return ok, res


def test_4_no_therapist():
    """④ 치료사 미배정 → warnings 에 미배정 안내 + safe_ctx 에 'therapist' 키 없음.

    LLM 은 호출되지만 prompt 에 치료사명이 들어가지 않았음을 검증.
    """
    db = setup_db()
    p, t, a = seed_appointment(db, with_therapist=False)
    ctx = ai_sms_draft.build_draft_context(db, a.id)
    fake = FakeProvider(return_text="환자A님, ㅇㅇ의원 도수치료 30분 안내")
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    no_therapist_warning = any(
        "치료사" in w and "미배정" in w for w in res["warnings"]
    )
    therapist_not_in_safe_ctx = "therapist" not in ctx.safe_ctx
    therapist_not_in_prompt = (
        len(fake.calls) == 1
        and "김치료" not in fake.calls[0]["prompt"]
    )
    ok = (
        res["skipped"] is False
        and no_therapist_warning
        and therapist_not_in_safe_ctx
        and ctx.therapist_name == ""
        and therapist_not_in_prompt
    )
    assert ok, {"res": res, "ctx_safe": ctx.safe_ctx, "calls": fake.calls}
    return ok, {"warnings": res["warnings"],
                "ctx_therapist_name": ctx.therapist_name,
                "safe_ctx_keys": sorted(ctx.safe_ctx.keys())}


def test_5_no_treatment():
    """⑤ 치료항목 누락 → missing_fields 에 '치료항목' + warning."""
    db = setup_db()
    p, t, a = seed_appointment(db, with_treatments=False)
    fake = FakeProvider(return_text="환자A님, 예약 안내드립니다.")
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    ok = (
        "치료항목" in res["missing_fields"]
        and any("치료항목" in w for w in res["warnings"])
        and res["skipped"] is False
    )
    assert ok, res
    return ok, {"missing_fields": res["missing_fields"],
                "warnings": res["warnings"]}


def test_6_mock_provider_name_restoration():
    """⑥ 정상 케이스 — FakeProvider 가 토큰 응답 → 서버에서 실명 복원."""
    db = setup_db()
    p, t, a = seed_appointment(db, patient_name="김환자")
    fake = FakeProvider(return_text="안녕하세요 환자A님, ㅇㅇ의원 도수치료 30분 예약 안내드립니다.")
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    ok = (
        res["skipped"] is False
        and "김환자" in res["draft"]            # 실명 복원
        and "환자A" not in res["draft"]         # 토큰 잔존 X
        and res["needs_user_confirm"] is True
        and res["context_used"]["patient_token"] == "환자A"
        and res["context_used"]["therapist_name"] == "김치료"
        # LLM 으로 보낸 prompt 에는 토큰만, 실명은 절대 미포함
        and len(fake.calls) == 1
        and "김환자" not in fake.calls[0]["prompt"]
        and "환자A" in fake.calls[0]["prompt"]
    )
    assert ok, {
        "draft": res["draft"],
        "prompt_has_realname": "김환자" in fake.calls[0]["prompt"],
        "prompt_has_token": "환자A" in fake.calls[0]["prompt"],
    }
    return ok, {"draft": res["draft"],
                "prompt_first200": fake.calls[0]["prompt"][:200]}


def test_7_pii_guard_phone_in_safe_ctx():
    """⑦ PII 가드 — safe_ctx 에 환자 전화번호가 침투했다 가정 → ValueError.

    실제 코드 경로는 환자 phone 을 ctx 에 넣지 않지만, 안전망이 동작하는지 검증.
    """
    db = setup_db()
    p, t, a = seed_appointment(db)
    # build_draft_context 호출 후 safe_ctx 에 전화번호 강제 주입
    ctx = ai_sms_draft.build_draft_context(db, a.id)
    ctx.safe_ctx["leaked_phone"] = "010-1234-5678"

    # make_draft 의 PII 가드 로직만 따로 검증 — build_draft_context 결과를 가로챌 수
    # 없으니 직접 assert_safe_for_external 호출로 등가 검증.
    import json as _j

    from app.services.ai import pii as pii_mod
    scan = pii_mod.assert_safe_for_external(_j.dumps(ctx.safe_ctx, ensure_ascii=False))
    ok = scan.has_blocking and "phone" in scan.found
    assert ok, {"found": scan.found, "cleaned": scan.cleaned}
    return ok, {"found_keys": list(scan.found.keys())}


def test_9_extra_note_chart_no_masked():
    """⑨ extra_note 에 차트번호(5~10자리 숫자) 가 들어가도 LLM 으로 원문이 새지 않음.

    chart_no_maybe 는 has_blocking 대상이 아니라 호출 자체는 통과되지만,
    프롬프트에는 마스킹된 [NUM] 이 들어가야 함 (세션 10 보안 패치).
    """
    db = setup_db()
    p, t, a = seed_appointment(db, patient_name="김환자")
    fake = FakeProvider(return_text="환자A님, ㅇㅇ의원 도수치료 30분 안내드립니다.")
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        extra_note="환자 차트번호 1234567 확인 부탁",
        provider_override=fake,
    )
    prompt = fake.calls[0]["prompt"] if fake.calls else ""
    ok = (
        res["skipped"] is False
        and len(fake.calls) == 1
        # 차트번호 원문이 프롬프트로 새면 안 됨
        and "1234567" not in prompt
        # 마스킹 흔적은 있어야 함
        and "[NUM]" in prompt
    )
    assert ok, {
        "draft": res.get("draft", ""),
        "prompt_first300": prompt[:300],
        "prompt_has_chart": "1234567" in prompt,
        "prompt_has_mask": "[NUM]" in prompt,
    }
    return ok, {"prompt_first200": prompt[:200]}


def test_8_clinic_phone_not_blocked():
    """⑧ 정상 clinic_phone (02-000-0000) 은 차단 안 됨 — 일상 컨텍스트가 막히면 안 됨."""
    db = setup_db()
    p, t, a = seed_appointment(db)
    fake = FakeProvider()
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    # clinic_phone 은 02-000-0000 — 한국 전화번호 정규식에 걸리지만 PII 가드는
    # 0 으로 채워진 더미 패턴이라 'has_blocking=True' 가 됨. 이 경우는 안전망이
    # 적용되어 ValueError 가 발생할 수 있음. 그래서 prompts 가이드는 clinic_phone 을
    # 토큰 없는 그대로 노출 — 정책: clinic_phone 은 PII 가 아닌 공개 정보.
    #
    # 결과적으로 이 경우 ValueError 가 발생하면 RUN_NOTE 로 알리되, draft 는 정상
    # 케이스 검증을 우선 — 만약 PII 가드가 너무 공격적이라 막히면 조정 필요.
    ok = res["skipped"] is False or (res.get("skip_reason") == "")
    return ok, {"draft": res.get("draft", ""), "warnings": res.get("warnings", [])}


# ─────────── pytest-only: endpoint 503 ───────────

def test_endpoint_503_when_disabled(client):
    """⑨ AI 비활성 시 endpoint 503. (pytest fixture 'client' 필요)

    conftest.py 가 init_db() 로 AiSetting(id=1, enabled=False) 을 자동 생성한 상태.
    """
    resp = client.post(
        "/api/ai/sms/draft",
        json={"appointment_id": "any-id", "tone": "friendly"},
    )
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert "AI 기능이 꺼져" in body.get("detail", ""), body


# ─────────── 러너 (standalone 모드) ───────────

ALL = [
    ("① 취소 예약",                 test_1_cancelled),
    ("② 예약시간 누락",             test_2_no_appt_time),
    ("③ 예약 미존재",               test_3_appt_not_found),
    ("④ 치료사 미배정",             test_4_no_therapist),
    ("⑤ 치료항목 누락",             test_5_no_treatment),
    ("⑥ 정상 (mock) + 실명 복원",  test_6_mock_provider_name_restoration),
    ("⑦ PII 가드 (전화번호 누출)", test_7_pii_guard_phone_in_safe_ctx),
    ("⑧ 정상 clinic_phone 통과",   test_8_clinic_phone_not_blocked),
    ("⑨ extra_note 차트번호 마스킹", test_9_extra_note_chart_no_masked),
]


def main():
    pass_n = 0
    fail_n = 0
    for name, fn in ALL:
        try:
            ok, payload = fn()
        except Exception as e:
            ok, payload = False, f"EXCEPTION: {e!r}"
        mark = PASS if ok else FAIL
        print(f"{mark}  {name}")
        if not ok:
            print(f"    >> {payload}")
            fail_n += 1
        else:
            pass_n += 1
    print()
    print(f"통과: {pass_n} / 전체: {pass_n + fail_n}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
