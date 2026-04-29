"""세션 02 검증 — POST /api/ai/sms/validate 자체 테스트.

⚠ 외부 LLM API 를 절대 호출하지 않는다. (검증 로직만)

실행:
    cd <repo_root>
    python tests/test_ai_sms_validate.py

In-memory SQLite + 모델로 시드한 뒤 validators.validate_sms_item / batch 를
직접 호출해 8개 시나리오를 검증한다.
"""
import os
import sys
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path 에 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# fmt: off — sys.path 조작 후 import (standalone 실행 호환). conftest.py 도 동일 패턴.
from sqlalchemy import create_engine  # noqa: E402, I001
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models import models  # noqa: E402
from app.services.ai import validators  # noqa: E402
# fmt: on


# ─────────── 테스트 헬퍼 ───────────

PASS = "[PASS]"
FAIL = "[FAIL]"


def codes(entries):
    return [e["code"] for e in entries]


def has_code(entries, code):
    return code in codes(entries)


def setup_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session()


def seed_basic(db, *, with_phone=True, with_therapist=True,
               with_treatments=True, status="reserved"):
    """기본 환자·치료사·예약 시드."""
    therapist = None
    if with_therapist:
        therapist = models.Employee(name="김치료", role="therapist")
        db.add(therapist)
        db.flush()
    patient = models.Patient(
        name="홍길동",
        phone="010-1234-5678" if with_phone else "",
    )
    db.add(patient)
    db.flush()
    appt = models.Appointment(
        patient_id=patient.id,
        therapist_id=therapist.id if therapist else None,
        start_at=datetime(2026, 5, 1, 10, 0),
        end_at=datetime(2026, 5, 1, 10, 30),
        duration_min=30,
        treatment_codes='["manual30"]' if with_treatments else "[]",
        status=status,
    )
    db.add(appt)
    db.flush()
    return patient, therapist, appt


# ─────────── 8개 테스트 ───────────

def test_1_normal():
    """① 정상 케이스 — blocker / warning 모두 없음."""
    db = setup_db()
    p, t, a = seed_basic(db)
    res = validators.validate_sms_item(
        db,
        appointment_id=a.id,
        body="홍길동님, 5월 1일 10시 도수치료 30분 예약 안내드립니다.",
    )
    ok = res["blockers"] == [] and res["warnings"] == []
    assert ok, res
    return ok, res


def test_2_no_phone():
    """② 전화번호 없음 → NO_PHONE blocker."""
    db = setup_db()
    p, t, a = seed_basic(db, with_phone=False)
    res = validators.validate_sms_item(
        db, appointment_id=a.id,
        body="안녕하세요, 예약 안내드립니다.",
    )
    ok = has_code(res["blockers"], "NO_PHONE")
    assert ok, res
    return ok, res


def test_2b_phone_format_invalid():
    """②-b 전화번호 형식 오류 → NO_PHONE blocker."""
    db = setup_db()
    p, t, a = seed_basic(db)
    res = validators.validate_sms_item(
        db, appointment_id=a.id,
        body="예약 안내",
        phone="0101234",  # 7자리 — 형식 오류
    )
    ok = has_code(res["blockers"], "NO_PHONE")
    assert ok, res
    return ok, res


def test_3_empty_body():
    """③ 본문 공백 → EMPTY_BODY blocker."""
    db = setup_db()
    p, t, a = seed_basic(db)
    res = validators.validate_sms_item(db, appointment_id=a.id, body="    ")
    ok = has_code(res["blockers"], "EMPTY_BODY")
    assert ok, res
    return ok, res


def test_4_no_therapist():
    """④ 치료사 미배정 → NO_THERAPIST warning (blocker 아님)."""
    db = setup_db()
    p, t, a = seed_basic(db, with_therapist=False)
    res = validators.validate_sms_item(
        db, appointment_id=a.id,
        body="홍길동님, 예약 안내드립니다.",
    )
    ok = (
        has_code(res["warnings"], "NO_THERAPIST")
        and not has_code(res["blockers"], "NO_THERAPIST")
    )
    assert ok, res
    return ok, res


def test_5_cancelled():
    """⑤ 취소 예약 → CANCELLED_PATIENT blocker."""
    db = setup_db()
    p, t, a = seed_basic(db, status="canceled")
    res = validators.validate_sms_item(
        db, appointment_id=a.id,
        body="홍길동님, 예약 안내드립니다.",
    )
    ok = has_code(res["blockers"], "CANCELLED_PATIENT")
    assert ok, res
    return ok, res


def test_6_unresolved_var():
    """⑥ 미치환 변수 → UNRESOLVED_VAR blocker."""
    db = setup_db()
    p, t, a = seed_basic(db)
    res = validators.validate_sms_item(
        db, appointment_id=a.id,
        body="{환자명}님, {다음예약시간} 예약 안내드립니다.",
    )
    ok = has_code(res["blockers"], "UNRESOLVED_VAR")
    tokens = next((e.get("tokens") for e in res["blockers"]
                  if e["code"] == "UNRESOLVED_VAR"), [])
    ok = ok and "{환자명}" in tokens and "{다음예약시간}" in tokens
    assert ok, res
    return ok, res


def test_7_emoji_cp949():
    """⑦ 이모지 포함 → CP949_ENCODING_ERROR blocker."""
    db = setup_db()
    p, t, a = seed_basic(db)
    res = validators.validate_sms_item(
        db, appointment_id=a.id,
        body="홍길동님, 예약 안내드립니다 😀✓",
    )
    ok = has_code(res["blockers"], "CP949_ENCODING_ERROR")
    assert ok, res
    return ok, res


def test_8_duplicate_recent():
    """⑧ 중복 발송 위험 → DUPLICATE_RECENT warning.
    같은 (phone, body) 가 5분 전에 SmsLog 에 success 로 있을 때.
    """
    db = setup_db()
    p, t, a = seed_basic(db)
    body = "홍길동님, 5월 1일 10시 도수치료 30분 예약 안내드립니다."
    # 5분 전에 같은 본문/번호로 발송된 이력
    db.add(models.SmsLog(
        patient_id=p.id,
        phone="01012345678",  # 정규화된 형태로 저장돼 있어도 매칭 가능해야 함
        body=body,
        sent_at=datetime.utcnow() - timedelta(minutes=5),
        result="success",
        detail="",
    ))
    db.flush()
    res = validators.validate_sms_item(
        db, appointment_id=a.id, body=body,
    )
    ok = (
        has_code(res["warnings"], "DUPLICATE_RECENT")
        and not has_code(res["blockers"], "DUPLICATE_RECENT")
    )
    assert ok, res
    return ok, res


def test_9_no_treatment():
    """(보너스) 치료항목 없음 → NO_TREATMENT blocker."""
    db = setup_db()
    p, t, a = seed_basic(db, with_treatments=False)
    res = validators.validate_sms_item(
        db, appointment_id=a.id,
        body="안내드립니다.",
    )
    ok = has_code(res["blockers"], "NO_TREATMENT")
    assert ok, res
    return ok, res


def test_10_appt_not_found():
    """(보너스) 존재하지 않는 예약 ID → APPT_NOT_FOUND blocker."""
    db = setup_db()
    res = validators.validate_sms_item(
        db, appointment_id="not-a-real-id",
        body="hi",
        phone="010-1111-2222",
    )
    ok = has_code(res["blockers"], "APPT_NOT_FOUND")
    assert ok, res
    return ok, res


def test_11_batch():
    """(보너스) batch 함수 응답 형식 확인."""
    db = setup_db()
    p, t, a = seed_basic(db)
    out = validators.validate_sms_batch(
        db,
        [
            {"appointment_id": a.id, "body": "정상 안내"},
            {"appointment_id": a.id, "body": ""},
        ],
    )
    ok = (
        isinstance(out, list) and len(out) == 2
        and out[0]["blockers"] == [] and out[0]["warnings"] == []
        and has_code(out[1]["blockers"], "EMPTY_BODY")
    )
    assert ok, out
    return ok, out


# ─────────── 러너 ───────────

ALL = [
    ("① 정상 케이스",            test_1_normal),
    ("② 전화번호 없음",          test_2_no_phone),
    ("②-b 전화번호 형식 오류",   test_2b_phone_format_invalid),
    ("③ 본문 공백",              test_3_empty_body),
    ("④ 치료사 미배정",          test_4_no_therapist),
    ("⑤ 취소 예약",              test_5_cancelled),
    ("⑥ 미치환 변수",            test_6_unresolved_var),
    ("⑦ 이모지(CP949 실패)",     test_7_emoji_cp949),
    ("⑧ 중복 발송 위험",         test_8_duplicate_recent),
    ("(보너스) 치료항목 없음",    test_9_no_treatment),
    ("(보너스) 예약 없음",        test_10_appt_not_found),
    ("(보너스) batch 응답",       test_11_batch),
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
            print(f"    ↳ {payload}")
            fail_n += 1
        else:
            pass_n += 1
    print()
    print(f"통과: {pass_n} / 전체: {pass_n + fail_n}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
