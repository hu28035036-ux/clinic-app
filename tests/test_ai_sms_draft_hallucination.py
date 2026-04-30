"""세션 09 검증 — sms_draft 할루시네이션 방어.

검증:
  ① 치료사 미배정 + AI 응답에 가짜 치료사명 → blocked
  ② 응답 시간이 DB 와 다름 → blocked (invented appointment time)
  ③ AI 응답이 "문자 발송했습니다" → blocked (execution claim)
  ④ extra_note 에 PII (전화번호) → ValueError (PII 가드)

실행:
    venv/Scripts/python.exe -m pytest tests/test_ai_sms_draft_hallucination.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models import models  # noqa: E402
from app.services.ai import provider as ai_provider  # noqa: E402
from app.services.ai import sms_draft as ai_sms_draft  # noqa: E402


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def seed_clinic(db):
    db.add(models.SmsSetting(id=1, clinic_name="ㅇㅇ의원", clinic_phone="02-000-0000"))
    db.flush()


def seed_appointment(db, *, with_therapist=True):
    seed_clinic(db)
    db.add(models.Treatment(
        code="manual30", name="도수치료 30분", short="도수",
        default_minutes=30, role="therapist", count_increment=1,
    ))
    therapist = None
    if with_therapist:
        therapist = models.Employee(name="김치료", role="therapist")
        db.add(therapist)
        db.flush()
    patient = models.Patient(name="홍길동", phone="010-1234-5678")
    db.add(patient)
    db.flush()
    appt = models.Appointment(
        patient_id=patient.id,
        therapist_id=therapist.id if therapist else None,
        start_at=datetime(2026, 5, 1, 14, 0),
        end_at=datetime(2026, 5, 1, 14, 30),
        duration_min=30,
        treatment_codes='["manual30"]',
        status="reserved",
    )
    db.add(appt)
    db.flush()
    return patient, therapist, appt


class FakeProvider(ai_provider.AiProvider):
    name = "fake"

    def __init__(self, return_text=""):
        super().__init__(model="fake-1", api_key="fake-key")
        self.return_text = return_text
        self.calls = []

    def is_ready(self) -> bool:
        return True

    def generate(self, prompt: str, system: str = "") -> ai_provider.AiResult:
        self.calls.append({"prompt": prompt, "system": system})
        return ai_provider.AiResult(text=self.return_text)


# ─────────── ① 치료사 미배정 + 가짜 치료사명 ───────────

def test_invented_therapist_blocked():
    db = setup_db()
    p, t, a = seed_appointment(db, with_therapist=False)
    fake = FakeProvider(
        return_text="홍길동님, 5월 1일 (수) 14:00 박철수 선생님 진료 예정입니다."
    )
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    assert res["blocked"] is True
    assert res["blocked_reason"] == "invented therapist"
    assert "박철수" not in res["draft"]
    assert "차단" in res["draft"]
    assert res["needs_user_confirm"] is False


# ─────────── ② 응답 시간 변조 ───────────

def test_invented_appointment_time_blocked():
    db = setup_db()
    p, t, a = seed_appointment(db, with_therapist=True)
    # DB 는 14:00 인데 응답에는 15:30 — 환각 (시간 변조)
    fake = FakeProvider(
        return_text="홍길동님, 5월 1일 (수) 15:30 도수치료 안내드립니다."
    )
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    assert res["blocked"] is True
    assert res["blocked_reason"] == "invented appointment time"


# ─────────── ③ 실행 완료 표현 ───────────

def test_execution_claim_blocked():
    db = setup_db()
    p, t, a = seed_appointment(db, with_therapist=True)
    fake = FakeProvider(
        return_text="홍길동님, 문자를 발송했습니다. 14:00 도수치료 안내."
    )
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    assert res["blocked"] is True
    assert res["blocked_reason"] == "execution claim blocked"
    assert "발송했" not in res["draft"]


# ─────────── ④ extra_note PII 차단 ───────────

def test_extra_note_with_phone_blocked():
    db = setup_db()
    p, t, a = seed_appointment(db, with_therapist=True)
    fake = FakeProvider(return_text="안녕하세요 홍길동님")
    with pytest.raises(ValueError) as exc:
        ai_sms_draft.make_draft(
            db, appointment_id=a.id, tone="friendly",
            extra_note="환자 010-1234-5678 에게 연락 요망",
            provider_override=fake,
        )
    assert "PII" in str(exc.value)
    # LLM 호출 전 차단되어야 함
    assert len(fake.calls) == 0


# ─────────── ⑤ 정상 경로는 영향 없음 (회귀 방지) ───────────

def test_normal_draft_unchanged():
    db = setup_db()
    p, t, a = seed_appointment(db, with_therapist=True)
    fake = FakeProvider(
        return_text="홍길동님, 5월 1일 (수) 14:00 도수치료 30분 예약 안내드립니다. 김치료 선생님."
    )
    res = ai_sms_draft.make_draft(
        db, appointment_id=a.id, tone="friendly",
        provider_override=fake,
    )
    assert res["blocked"] is False
    assert res["needs_user_confirm"] is True
    assert "홍길동" in res["draft"]
