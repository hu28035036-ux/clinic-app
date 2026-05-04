"""20-3-5 F-3 자원 (치료실 v1) contract.

검증 범위 (20-P-2 §7 사용자 §7-7 결정값 정합):
  1. m018 마이그레이션 — Resource 테이블 + Appointment.resource_id.
  2. Resource ORM (id/type/name/capacity=1/active/sort_order/created_at/updated_at).
  3. Appointment.resource_id 컬럼 (FK nullable).
  4. _serialize_appointment 18키 → 19키 (resource_id 추가).
  5. /api/resources GET (목록) + POST/PUT/DELETE (require_admin).
  6. RESOURCE_RESPONSE_KEYS frozenset 7키.
  7. check_resource_conflict — 같은 자원 + 시간 겹침 검사.
  8. POST /api/appointments — 자원 충돌 시 409.
  9. PUT /api/appointments — 자원 변경 시 충돌 검사 (자기 자신 제외).
  10. POST /api/appointment-series — 자원 충돌 슬롯 skip + conflicts 응답 (Codex caveat 3 반영).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.models import models as _m
from app.modules.appointments import schemas as _appt_schemas
from app.modules.resources import schemas as _res_schemas
from app.modules.resources import service as _res_service

# ────────────────── 모델 ──────────────────


class TestF3Model:
    def test_resource_model_exists(self):
        assert hasattr(_m, "Resource")

    def test_resource_columns(self):
        R = _m.Resource
        for col in ("id", "type", "name", "capacity", "active",
                    "sort_order", "created_at", "updated_at"):
            assert hasattr(R, col)

    def test_appointment_has_resource_id(self):
        assert hasattr(_m.Appointment, "resource_id")

    def test_resource_id_nullable(self):
        col = _m.Appointment.__table__.columns["resource_id"]
        assert col.nullable is True

    def test_resource_capacity_default_one(self):
        col = _m.Resource.__table__.columns["capacity"]
        # default=1 (사용자 §7-7 (i))
        assert col.default is not None or col.server_default is not None


# ────────────────── 응답 스키마 ──────────────────


class TestF3Schemas:
    def test_response_keys(self):
        assert _res_schemas.RESOURCE_RESPONSE_KEYS == frozenset({
            "id", "type", "name", "capacity",
            "active", "sort_order", "created_at",
        })

    def test_extendedprops_includes_resource_id(self):
        # 19-9 EXTENDED_PROPS_KEYS contract 갱신 (18키 → 19키)
        assert "resource_id" in _appt_schemas.APPOINTMENT_EXTENDED_PROPS_KEYS


# ────────────────── 자원 충돌 검사 ──────────────────


class TestF3ConflictCheck:
    def test_no_resource_returns_none(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            result = _res_service.check_resource_conflict(
                db, resource_id=None,
                start_at=datetime(2099, 6, 1, 10, 0),
                end_at=datetime(2099, 6, 1, 10, 30),
            )
            assert result is None
        finally:
            db.close()

    def test_same_resource_overlap_blocks(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            # 자원 + 환자 + 첫 예약
            res = _m.Resource(type="room", name="20_3_5_R1", capacity=1)
            db.add(res)
            db.flush()
            patient = _m.Patient(
                name="20_3_5_conflict_p1", phone="010-1111-2222",
                birth_date="1990-01-01", chart_no="C-2035-C1",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            ts = datetime(2099, 6, 1, 10, 0)
            appt1 = _m.Appointment(
                patient_id=patient.id,
                start_at=ts,
                end_at=ts + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
                resource_id=res.id,
            )
            db.add(appt1)
            db.flush()

            # 같은 자원 + 시간 겹침 → 충돌
            conflict = _res_service.check_resource_conflict(
                db, resource_id=res.id,
                start_at=ts + timedelta(minutes=10),
                end_at=ts + timedelta(minutes=40),
            )
            assert conflict is not None
            assert conflict.id == appt1.id
        finally:
            db.rollback()
            db.close()

    def test_canceled_excluded_from_conflict(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            res = _m.Resource(type="room", name="20_3_5_R2", capacity=1)
            db.add(res)
            db.flush()
            patient = _m.Patient(
                name="20_3_5_canceled_p", phone="010-3333-4444",
                birth_date="1991-01-01", chart_no="C-2035-CC",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            ts = datetime(2099, 6, 2, 10, 0)
            # 취소된 예약은 충돌 검사에서 제외
            canceled = _m.Appointment(
                patient_id=patient.id,
                start_at=ts,
                end_at=ts + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
                resource_id=res.id,
                status="canceled",
            )
            db.add(canceled)
            db.flush()

            # 충돌 검사 → None (canceled 제외)
            conflict = _res_service.check_resource_conflict(
                db, resource_id=res.id,
                start_at=ts,
                end_at=ts + timedelta(minutes=30),
            )
            assert conflict is None
        finally:
            db.rollback()
            db.close()

    def test_self_excluded_via_exclude_appt_id(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            res = _m.Resource(type="room", name="20_3_5_R3", capacity=1)
            db.add(res)
            db.flush()
            patient = _m.Patient(
                name="20_3_5_self_p", phone="010-5555-6666",
                birth_date="1992-01-01", chart_no="C-2035-S",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            ts = datetime(2099, 6, 3, 10, 0)
            appt = _m.Appointment(
                patient_id=patient.id,
                start_at=ts,
                end_at=ts + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
                resource_id=res.id,
            )
            db.add(appt)
            db.flush()

            # 자기 자신 제외 → None
            conflict = _res_service.check_resource_conflict(
                db, resource_id=res.id,
                start_at=ts,
                end_at=ts + timedelta(minutes=30),
                exclude_appt_id=appt.id,
            )
            assert conflict is None
        finally:
            db.rollback()
            db.close()


# ────────────────── /api/resources endpoints ──────────────────


class TestF3Endpoints:
    def test_list_resources_returns_200(self, client):
        resp = client.get("/api/resources")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_resources_type_filter(self, client):
        resp = client.get("/api/resources?type=room")
        assert resp.status_code == 200

    def test_post_resources_requires_admin(self, client):
        resp = client.post("/api/resources", json={"name": "치료실 1", "type": "room"})
        assert resp.status_code in (401, 403)

    def test_put_resources_requires_admin(self, client):
        resp = client.put("/api/resources/nonexistent", json={"name": "치료실", "type": "room"})
        assert resp.status_code in (401, 403)

    def test_delete_resources_requires_admin(self, client):
        resp = client.delete("/api/resources/nonexistent")
        assert resp.status_code in (401, 403)


# ────────────────── 예약 + 자원 충돌 ──────────────────


class TestF3AppointmentResourceConflict:
    def test_post_appointment_resource_conflict_409(self, client):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            res = _m.Resource(type="room", name="20_3_5_R_appt", capacity=1)
            db.add(res)
            db.flush()
            patient = _m.Patient(
                name="20_3_5_appt_p1", phone="010-7777-8888",
                birth_date="1993-01-01", chart_no="C-2035-AP",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            ts = datetime(2099, 7, 1, 10, 0)
            appt1 = _m.Appointment(
                patient_id=patient.id,
                start_at=ts,
                end_at=ts + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
                resource_id=res.id,
                status="reserved",
            )
            db.add(appt1)
            db.commit()
            res_id = res.id
            pid = patient.id
        finally:
            db.close()

        # 같은 자원 + 시간 겹침 → 409
        resp = client.post(
            "/api/appointments",
            json={
                "patient_id": pid,
                "start_at": (ts + timedelta(minutes=15)).isoformat(),
                "duration_min": 30,
                "treatment_codes": ["manual30"],
                "resource_id": res_id,
            },
        )
        assert resp.status_code == 409
        assert "자원 충돌" in resp.text


# ────────────────── 시리즈 + 자원 충돌 통합 ──────────────────


class TestF3SeriesResourceConflict:
    def test_series_resource_conflict_in_conflicts_list(self, client):
        """Codex 20-3-4 caveat 3 반영 — 시리즈 등록 시 자원 충돌 검사."""
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            res = _m.Resource(type="room", name="20_3_5_R_series", capacity=1)
            db.add(res)
            db.flush()
            patient1 = _m.Patient(
                name="20_3_5_other_p", phone="010-9999-0000",
                birth_date="1994-01-01", chart_no="C-2035-OP",
                created_at=datetime.utcnow(),
            )
            db.add(patient1)
            db.flush()
            # 다른 환자가 11/12 14:00 같은 자원 사용 중
            ts_blocked = datetime(2099, 11, 12, 14, 0)
            blocking = _m.Appointment(
                patient_id=patient1.id,
                start_at=ts_blocked,
                end_at=ts_blocked + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
                resource_id=res.id,
                status="reserved",
            )
            db.add(blocking)
            patient2 = _m.Patient(
                name="20_3_5_series_p", phone="010-2222-3333",
                birth_date="1995-01-01", chart_no="C-2035-SP",
                created_at=datetime.utcnow(),
            )
            db.add(patient2)
            db.commit()
            res_id = res.id
            pid2 = patient2.id
        finally:
            db.close()

        # 환자 2 매주 11/5, 11/12, 11/19 같은 자원 시리즈 → 11/12 충돌 skip
        resp = client.post(
            "/api/appointment-series",
            json={
                "patient_id": pid2,
                "start_at": datetime(2099, 11, 5, 14, 0).isoformat(),
                "duration_min": 30,
                "interval_days": 7,
                "count": 3,
                "treatment_codes": ["manual30"],
                "resource_id": res_id,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # 11/12 슬롯이 conflicts 에 포함
        conflict_dates = [c["start_at"] for c in data["conflicts"]]
        assert any("2099-11-12" in c for c in conflict_dates)
        # 11/5, 11/19 는 created
        assert len(data["created"]) == 2
        # 충돌 reason = "resource_conflict"
        for c in data["conflicts"]:
            if "2099-11-12" in c["start_at"]:
                assert c["reason"] == "resource_conflict"
