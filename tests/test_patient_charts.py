"""환자 차팅(PatientChart) API 계약 + 동작 테스트.

차트는 치료완료(approved) 예약 1건당 1장(서버 UNIQUE appointment_id), SOAP 통합
본문(content 단일 텍스트). 격리 DB(conftest) + 시드 환자/치료사 사용. 예약 시각은
검증된 평일(수요일, 2026-05-20 기준)을 주 단위로 분산해 상호 간섭 차단.
"""
from __future__ import annotations

from datetime import datetime

from app.database import SessionLocal
from app.models import models
from tests.harness.helpers import (
    approve_appointment,
    cancel_appointment,
    make_appointment,
)
from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

_CHART_KEYS = {
    "id", "appointment_id", "patient_id", "content",
    "treatment_start_date", "session_no",
    "author_id", "author_name", "created_at", "updated_at",
}


def _reserved_appt(client, *, start: datetime, codes=None, therapist=None):
    pid = get_test_patient_id("홍길동테스트")
    r = make_appointment(
        client, patient_id=pid, start_at=start,
        treatment_codes=codes or ["manual30"], therapist_id=therapist,
    )
    assert r.status_code == 200, r.text
    return pid, r.json()["id"]


def _approved_appt(client, *, start: datetime, codes=None, therapist=None):
    pid, aid = _reserved_appt(client, start=start, codes=codes, therapist=therapist)
    ar = approve_appointment(client, aid)
    assert ar.status_code == 200, ar.text
    return pid, aid


def _put_chart(client, aid, **fields):
    body = {"content": "", "author_id": ""}
    body.update(fields)
    return client.put(f"/api/charts/by-appointment/{aid}", json=body)


# ──────────────────────── 1. 작성 + 조회 계약 ────────────────────────


def test_create_and_get_chart(client):
    _pid, aid = _approved_appt(client, start=datetime(2026, 5, 27, 10, 0))
    r = _put_chart(client, aid, content="[S] 허리 통증\n[A] 요추 염좌")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == _CHART_KEYS
    assert body["appointment_id"] == aid
    assert "허리 통증" in body["content"]
    assert "요추 염좌" in body["content"]

    g = client.get(f"/api/charts/by-appointment/{aid}")
    assert g.status_code == 200
    assert "허리 통증" in g.json()["content"]


# ──────────────────────── 2. 미작성 예약 조회 → null ────────────────────────


def test_get_missing_chart_returns_null(client):
    _pid, aid = _approved_appt(client, start=datetime(2026, 6, 3, 10, 0))
    g = client.get(f"/api/charts/by-appointment/{aid}")
    assert g.status_code == 200
    assert g.json() is None


# ──────────────────────── 3. approved 예약에만 작성 (reserved 거부) ────────────────────────


def test_reserved_appt_rejected(client):
    _pid, aid = _reserved_appt(client, start=datetime(2026, 6, 10, 10, 0))
    r = _put_chart(client, aid, content="x")
    assert r.status_code == 400


# ──────────────────────── 4. canceled 예약 거부 ────────────────────────


def test_canceled_appt_rejected(client):
    _pid, aid = _reserved_appt(client, start=datetime(2026, 6, 17, 10, 0))
    assert cancel_appointment(client, aid).status_code == 200
    r = _put_chart(client, aid, content="x")
    assert r.status_code == 400


# ──────────────────────── 5. 존재하지 않는 예약 → 404 ────────────────────────


def test_nonexistent_appt_404(client):
    r = _put_chart(client, "nonexistent_appt_id", content="x")
    assert r.status_code == 404


# ──────────────────────── 6. upsert: 같은 예약 = 차트 1장 (UNIQUE) ────────────────────────


def test_upsert_keeps_single_chart(client):
    _pid, aid = _approved_appt(client, start=datetime(2026, 6, 24, 10, 0))
    _put_chart(client, aid, content="v1")
    _put_chart(client, aid, content="v2 재활 운동")

    g = client.get(f"/api/charts/by-appointment/{aid}").json()
    assert g["content"] == "v2 재활 운동"

    db = SessionLocal()
    try:
        cnt = db.query(models.PatientChart).filter_by(appointment_id=aid).count()
    finally:
        db.close()
    assert cnt == 1


# ──────────────────────── 7. 환자 차트 히스토리: 방문 + 차트 embed ────────────────────────


def test_patient_history_embeds_chart(client):
    pid, aid = _approved_appt(client, start=datetime(2026, 7, 1, 10, 0))
    _put_chart(client, aid, content="기록 있음")

    d = client.get(f"/api/charts/patient/{pid}").json()
    assert d["patient_id"] == pid
    assert d["total"] >= 1

    found = None
    for day in d["days"]:
        for a in day["appointments"]:
            if a["appointment_id"] == aid:
                found = a
    assert found is not None, "작성한 차트의 예약이 히스토리에 없음"
    assert found["chart"] is not None
    assert found["chart"]["has_content"] is True


# ──────────────────────── 8. 빈 본문 저장 → has_content False ────────────────────────


def test_blank_content_not_marked_written(client):
    pid, aid = _approved_appt(client, start=datetime(2026, 7, 15, 10, 0))
    # 공백만 저장 (작성 안 함)
    assert _put_chart(client, aid, content="   \n  ").status_code == 200
    d = client.get(f"/api/charts/patient/{pid}").json()
    found = next(
        (a for day in d["days"] for a in day["appointments"] if a["appointment_id"] == aid),
        None,
    )
    assert found is not None
    assert found["chart"]["has_content"] is False


# ──────────────────────── 9. 작성자 미지정 → 예약 담당치료사 폴백 ────────────────────────


def test_author_defaults_to_therapist(client):
    ther = get_test_therapist_id("김테스트치료사")
    _pid, aid = _approved_appt(client, start=datetime(2026, 7, 22, 10, 0), therapist=ther)
    r = _put_chart(client, aid, content="x")
    assert r.status_code == 200
    body = r.json()
    assert body["author_id"] == ther
    assert body["author_name"] == "김테스트치료사"


# ──────────────────────── 10. sync ENTITY_MAP 등록 ────────────────────────


def test_entity_map_registered():
    from app.services.sync import ENTITY_MAP
    assert ENTITY_MAP.get("patient_chart") is models.PatientChart


# ──────────────────────── 11. 예약 삭제 시 차트도 삭제(orphan 방지) ────────────────────────


def test_chart_cascade_on_appointment_delete():
    """ORM cascade — 예약을 지우면 그 차트도 사라져 orphan 이 남지 않는다.

    SQLite 는 FK OFF(PRAGMA foreign_keys 미설정)라 DB CASCADE 가 아니라
    Appointment.charts relationship 의 cascade='all, delete-orphan' 으로 동작.
    """
    db = SessionLocal()
    try:
        p = models.Patient(name="cascade차트테스트")
        db.add(p)
        db.flush()
        a = models.Appointment(
            patient_id=p.id,
            start_at=datetime(2027, 1, 4, 10, 0),
            end_at=datetime(2027, 1, 4, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="approved",
        )
        db.add(a)
        db.flush()
        ch = models.PatientChart(appointment_id=a.id, patient_id=p.id, content="x")
        db.add(ch)
        db.flush()
        chid = ch.id
        db.delete(a)
        db.commit()
        assert db.query(models.PatientChart).filter_by(id=chid).count() == 0
    finally:
        db.close()


# ──────────────────────── 12. 치료시작일 + 회차 저장/조회 ────────────────────────


def test_start_date_and_session_roundtrip(client):
    _pid, aid = _approved_appt(client, start=datetime(2026, 8, 5, 10, 0))
    r = _put_chart(
        client, aid, content="x", treatment_start_date="2026-07-01", session_no=3,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["treatment_start_date"] == "2026-07-01"
    assert body["session_no"] == 3

    g = client.get(f"/api/charts/by-appointment/{aid}").json()
    assert g["treatment_start_date"] == "2026-07-01"
    assert g["session_no"] == 3


# ──────────────────────── 13. 회차 0/미입력 → null 정규화 ────────────────────────


def test_session_no_blank_normalized_to_null(client):
    _pid, aid = _approved_appt(client, start=datetime(2026, 8, 19, 10, 0))
    r = _put_chart(client, aid, content="x", session_no=0)
    assert r.status_code == 200, r.text
    assert r.json()["session_no"] is None


# ──────────────────────── 14. 히스토리 요약에 회차 포함 ────────────────────────


def test_history_summary_includes_session_no(client):
    pid, aid = _approved_appt(client, start=datetime(2026, 8, 26, 10, 0))
    _put_chart(client, aid, content="x", session_no=5)
    d = client.get(f"/api/charts/patient/{pid}").json()
    found = next(
        (a for day in d["days"] for a in day["appointments"] if a["appointment_id"] == aid),
        None,
    )
    assert found is not None
    assert found["chart"]["session_no"] == 5
