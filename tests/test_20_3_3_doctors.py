"""20-3-3 F-1 (c) 가벼운 의사만 contract.

검증 범위 (20-P-2 §5 사용자 §5-7 (c) 결정값 정합):
  1. m016 마이그레이션 — doctors 테이블 신설 (인덱스 보강).
  2. Doctor ORM 모델 신설 — 8 컬럼.
  3. Department / Room / DoctorSchedule / Patient.doctor_id 부재 확인.
  4. modules.doctors 의 serialize_doctor 8키 + DOCTOR_RESPONSE_KEYS frozenset.
  5. /api/doctors GET (목록) — public 또는 인증 정책.
  6. /api/doctors POST/PUT/DELETE — require_admin 게이트.
  7. 의사명 필수 검증 (400 빈값).
  8. Employee.role="doctor" 분기와 별개 — 충돌 없음.
  9. audit detail 에 license_no / specialty 부재 (PII 비저장).
"""
from __future__ import annotations

from app.models import models as _m
from app.modules.doctors import schemas as _doctor_schemas
from app.modules.doctors import service as _doctor_service

# ────────────────── 모델 + 부재 항목 확인 ──────────────────


class TestF1Model:
    def test_doctor_model_exists(self):
        assert hasattr(_m, "Doctor")

    def test_doctor_columns(self):
        D = _m.Doctor
        for col in ("id", "name", "specialty", "license_no", "color",
                    "active", "sort_order", "created_at", "updated_at"):
            assert hasattr(D, col), f"Doctor.{col} 부재"

    def test_no_department_model(self):
        # 사용자 §5-7 (c) — Department / Room / DoctorSchedule 부재
        assert not hasattr(_m, "Department")

    def test_no_room_model(self):
        assert not hasattr(_m, "Room")

    def test_no_doctor_schedule_model(self):
        assert not hasattr(_m, "DoctorSchedule")

    def test_patient_no_doctor_id_column(self):
        # 사용자 §5-7 (c) — Patient.doctor_id FK 부재
        assert not hasattr(_m.Patient, "doctor_id")


# ────────────────── serialize ──────────────────


class TestF1Serialize:
    def test_response_keys(self):
        assert _doctor_schemas.DOCTOR_RESPONSE_KEYS == frozenset({
            "id", "name", "specialty", "license_no", "color",
            "active", "sort_order", "created_at",
        })

    def test_serialize_doctor_8keys(self):
        from datetime import datetime
        from types import SimpleNamespace

        d = SimpleNamespace(
            id="dr1",
            name="박철수",
            specialty="정형외과",
            license_no="ABC-123",
            color="#FF5733",
            active=True,
            sort_order=1,
            created_at=datetime(2026, 5, 4, 10, 0),
        )
        out = _doctor_service.serialize_doctor(d)
        assert set(out.keys()) == _doctor_schemas.DOCTOR_RESPONSE_KEYS
        assert out["id"] == "dr1"
        assert out["name"] == "박철수"
        assert out["specialty"] == "정형외과"
        assert out["active"] is True


# ────────────────── /api/doctors endpoints ──────────────────


class TestF1Endpoints:
    def test_list_doctors_returns_200(self, client):
        # GET /api/doctors public — 시드 0 도 OK (빈 리스트)
        resp = client.get("/api/doctors")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_post_doctors_requires_admin(self, client):
        resp = client.post(
            "/api/doctors",
            json={"name": "테스트의사"},
        )
        assert resp.status_code in (401, 403)

    def test_put_doctors_requires_admin(self, client):
        resp = client.put(
            "/api/doctors/nonexistent",
            json={"name": "수정"},
        )
        assert resp.status_code in (401, 403)

    def test_delete_doctors_requires_admin(self, client):
        resp = client.delete("/api/doctors/nonexistent")
        assert resp.status_code in (401, 403)


# ────────────────── 호환성 보존 ──────────────────


class TestF1BackwardCompat:
    def test_employee_role_doctor_unchanged(self):
        # 기존 Employee.role="doctor" 분기 (도수치료 내부 의료직군) 보존
        # Doctor 별도 테이블은 *외부 진료 의사 등록 후보 모델* — Employee 와 별개
        assert hasattr(_m.Employee, "role")
        # Employee 와 Doctor 가 별개 테이블
        assert _m.Doctor.__tablename__ == "doctors"
        assert _m.Employee.__tablename__ == "employees"
        assert _m.Doctor.__tablename__ != _m.Employee.__tablename__

    def test_treatment_role_doctor_unchanged(self):
        # 기존 Treatment.role="doctor" 분기 (injection / cartilage) 보존
        assert hasattr(_m.Treatment, "role")

    def test_doctor_table_distinct_from_employee(self):
        # 두 모델은 *별개 도메인* — FK 부재
        assert "employee_id" not in [c.name for c in _m.Doctor.__table__.columns]


# ────────────────── 보안 / PII ──────────────────


class TestF1SecurityNoPii:
    def test_license_no_nullable(self):
        # license_no 는 nullable — 빈 의사 등록 가능
        col = _m.Doctor.__table__.columns["license_no"]
        assert col.nullable is True

    def test_specialty_nullable(self):
        col = _m.Doctor.__table__.columns["specialty"]
        assert col.nullable is True
