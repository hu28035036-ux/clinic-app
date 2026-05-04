"""20-3-4 F-2 반복 예약 contract.

검증 범위 (20-P-2 §6 사용자 §6-6 결정값 정합):
  1. m017 마이그레이션 — AppointmentSeries 테이블 + Appointment.series_id.
  2. AppointmentSeries ORM 모델 + pattern='n_times' / pattern_data JSON.
  3. Appointment.series_id 컬럼 (FK nullable).
  4. _serialize_appointment 응답에 series_id 추가 (17키 → 18키).
  5. compute_slot_starts (interval_days + count) 계산 정합.
  6. POST /api/appointment-series — 시리즈 + 슬롯 생성, 충돌 skip + 응답에 conflicts.
  7. DELETE /api/appointment-series/{sid} — 미래만 일괄 취소 (과거 보존).
  8. 19-9 EXTENDED_PROPS_KEYS frozenset 갱신 (18키).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.models import models as _m
from app.modules.appointment_series import schemas as _series_schemas
from app.modules.appointment_series import service as _series_service
from app.modules.appointments import schemas as _appt_schemas

# ────────────────── 모델 ──────────────────


class TestF2Model:
    def test_appointment_series_exists(self):
        assert hasattr(_m, "AppointmentSeries")

    def test_appointment_series_columns(self):
        S = _m.AppointmentSeries
        for col in (
            "id", "patient_id", "therapist_id",
            "pattern", "pattern_data",
            "start_date", "end_date",
            "treatment_codes", "created_at",
        ):
            assert hasattr(S, col)

    def test_appointment_has_series_id(self):
        assert hasattr(_m.Appointment, "series_id")

    def test_appointment_series_id_is_nullable(self):
        col = _m.Appointment.__table__.columns["series_id"]
        assert col.nullable is True


# ────────────────── 슬롯 시작 시각 계산 ──────────────────


class TestComputeSlotStarts:
    def test_n_times_pattern_basic(self):
        starts = _series_service.compute_slot_starts(
            start_at=datetime(2026, 5, 5, 14, 0),
            interval_days=7,
            count=4,
        )
        assert len(starts) == 4
        assert starts[0] == datetime(2026, 5, 5, 14, 0)
        assert starts[1] == datetime(2026, 5, 12, 14, 0)
        assert starts[2] == datetime(2026, 5, 19, 14, 0)
        assert starts[3] == datetime(2026, 5, 26, 14, 0)

    def test_count_one_returns_single_slot(self):
        starts = _series_service.compute_slot_starts(
            start_at=datetime(2026, 5, 5),
            interval_days=7,
            count=1,
        )
        assert len(starts) == 1


# ────────────────── _serialize_appointment series_id ──────────────────


class TestSerializeAppointmentSeriesId:
    def test_extendedprops_includes_series_id(self):
        # 19-9 EXTENDED_PROPS_KEYS contract 갱신 확인
        assert "series_id" in _appt_schemas.APPOINTMENT_EXTENDED_PROPS_KEYS

    def test_serialize_returns_none_for_single_appt(self, client):
        from app.database import SessionLocal
        from app.routers.api import _serialize_appointment

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_4_single", phone="010-0000-1111",
                birth_date="1990-01-01", chart_no="C-2034-S",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            appt = _m.Appointment(
                patient_id=patient.id,
                start_at=datetime.utcnow(),
                end_at=datetime.utcnow() + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
            )
            db.add(appt)
            db.flush()
            d = _serialize_appointment(appt)
            assert "series_id" in d["extendedProps"]
            assert d["extendedProps"]["series_id"] is None
        finally:
            db.rollback()
            db.close()


# ────────────────── 응답 스키마 ──────────────────


class TestResponseSchemas:
    def test_series_response_keys(self):
        assert _series_schemas.APPOINTMENT_SERIES_RESPONSE_KEYS == frozenset({
            "id", "patient_id", "therapist_id", "pattern",
            "pattern_data", "start_date", "treatment_codes",
        })

    def test_create_response_keys(self):
        assert _series_schemas.SERIES_CREATE_RESPONSE_KEYS == frozenset({
            "series", "created", "conflicts",
        })

    def test_conflict_info_keys(self):
        assert _series_schemas.CONFLICT_INFO_KEYS == frozenset({
            "start_at", "reason",
        })


# ────────────────── /api/appointment-series 엔드포인트 ──────────────────


class TestSeriesEndpoints:
    def test_post_series_basic(self, client):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_4_post", phone="010-2222-3333",
                birth_date="1991-01-01", chart_no="C-2034-P",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.commit()
            pid = patient.id
        finally:
            db.close()

        # 점심창 외 시간으로 등록
        ts = datetime(2099, 11, 5, 10, 0)
        resp = client.post(
            "/api/appointment-series",
            json={
                "patient_id": pid,
                "start_at": ts.isoformat(),
                "duration_min": 30,
                "interval_days": 7,
                "count": 3,
                "treatment_codes": ["manual30"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == _series_schemas.SERIES_CREATE_RESPONSE_KEYS
        assert "series" in data
        assert isinstance(data["created"], list)
        assert isinstance(data["conflicts"], list)
        # 3 슬롯 모두 점심창 외라면 모두 created
        assert len(data["created"]) + len(data["conflicts"]) == 3

    def test_post_series_invalid_patient(self, client):
        resp = client.post(
            "/api/appointment-series",
            json={
                "patient_id": "nonexistent_patient",
                "start_at": datetime(2099, 11, 5, 10, 0).isoformat(),
                "duration_min": 30,
                "interval_days": 7,
                "count": 3,
                "treatment_codes": ["manual30"],
            },
        )
        assert resp.status_code == 404

    def test_post_series_invalid_count(self, client):
        # count < 2 → pydantic validation
        resp = client.post(
            "/api/appointment-series",
            json={
                "patient_id": "any",
                "start_at": datetime(2099, 11, 5, 10, 0).isoformat(),
                "duration_min": 30,
                "interval_days": 7,
                "count": 1,
                "treatment_codes": ["manual30"],
            },
        )
        assert resp.status_code == 422  # pydantic validation error

    def test_delete_series_future_only(self, client):
        # 시리즈 생성 → 일부 슬롯 과거로 강제 → DELETE → 미래만 취소
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_4_delete", phone="010-4444-5555",
                birth_date="1992-01-01", chart_no="C-2034-D",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()

            series = _m.AppointmentSeries(
                patient_id=patient.id,
                pattern="n_times",
                pattern_data=json.dumps({"interval_days": 7, "count": 2}),
                start_date=datetime.utcnow() - timedelta(days=10),
                end_date=datetime.utcnow() + timedelta(days=10),
                treatment_codes='["manual30"]',
            )
            db.add(series)
            db.flush()

            # 과거 슬롯
            past = _m.Appointment(
                patient_id=patient.id,
                start_at=datetime.utcnow() - timedelta(days=10),
                end_at=datetime.utcnow() - timedelta(days=10) + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
                series_id=series.id,
            )
            # 미래 슬롯
            future = _m.Appointment(
                patient_id=patient.id,
                start_at=datetime.utcnow() + timedelta(days=10),
                end_at=datetime.utcnow() + timedelta(days=10) + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
                series_id=series.id,
            )
            db.add_all([past, future])
            db.commit()

            sid = series.id
            past_id = past.id
            future_id = future.id
        finally:
            db.close()

        resp = client.delete(f"/api/appointment-series/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["series_id"] == sid
        # 미래 슬롯만 취소
        assert future_id in data["canceled"]
        assert past_id not in data["canceled"]

        # DB 확인
        db = SessionLocal()
        try:
            past_after = db.query(_m.Appointment).filter_by(id=past_id).first()
            future_after = db.query(_m.Appointment).filter_by(id=future_id).first()
            assert past_after.status == "reserved"  # 과거 보존
            assert future_after.status == "canceled"
        finally:
            db.close()

    def test_delete_series_not_found(self, client):
        resp = client.delete("/api/appointment-series/nonexistent_sid")
        assert resp.status_code == 404


# ────────────────── 호환성 ──────────────────


class TestF2BackwardCompat:
    def test_single_appointment_series_id_none(self):
        from app.database import SessionLocal
        from app.routers.api import _serialize_appointment

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_4_compat", phone="010-7777-8888",
                birth_date="1993-01-01", chart_no="C-2034-CMP",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            appt = _m.Appointment(
                patient_id=patient.id,
                start_at=datetime.utcnow(),
                end_at=datetime.utcnow() + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
            )
            db.add(appt)
            db.flush()
            # 단일 예약 → series_id = None
            assert appt.series_id is None
            d = _serialize_appointment(appt)
            assert d["extendedProps"]["series_id"] is None
        finally:
            db.rollback()
            db.close()

    def test_existing_create_appointment_unchanged(self, client):
        # 기존 POST /api/appointments 동작 보존 (단일 예약 — series_id=None)
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_4_existing", phone="010-9999-0000",
                birth_date="1994-01-01", chart_no="C-2034-E",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.commit()
            pid = patient.id
        finally:
            db.close()

        resp = client.post(
            "/api/appointments",
            json={
                "patient_id": pid,
                "start_at": datetime(2099, 11, 5, 10, 0).isoformat(),
                "duration_min": 30,
                "treatment_codes": ["manual30"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "reserved"
