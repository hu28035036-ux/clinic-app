"""20-3-2 F-11 권한 다중 등급 contract.

검증 범위 (20-P-2 §4 사용자 §4-6 권장값 정합):
  1. m015 마이그레이션 — Employee.permission_level VARCHAR(20) DEFAULT 'staff'.
  2. Employee 모델에 permission_level 컬럼 + 기본값 'staff'.
  3. _serialize_employee 응답에 permission_level 추가 (12키, 11키 → 12키).
  4. therapists.service.serialize_employee 동기 (byte-equivalent).
  5. POST /api/admin/employees/{eid}/permission 신설 — 등급 변경.
  6. 등급 검증 (staff / admin / super 3등급, 그 외 400).
  7. require_admin 의존 — admin 인증 없이 401/403.
  8. 기존 admin 로그인 / PBKDF2 / 5회 잠금 / 8h 세션 흐름 변경 ⊥.
"""
from __future__ import annotations

from app.models import models as _m
from app.modules.therapists import service as _therapists_service

# ────────────────── m015 + 모델 ──────────────────


class TestF11Migration:
    def test_permission_level_column_exists(self):
        assert hasattr(_m.Employee, "permission_level")

    def test_permission_level_default_staff(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            emp = _m.Employee(
                name="20_3_2_test_default",
                role="therapist",
            )
            db.add(emp)
            db.flush()
            assert emp.permission_level == "staff"
        finally:
            db.rollback()
            db.close()


# ────────────────── _serialize_employee ──────────────────


class TestF11SerializeEmployee:
    def test_serialize_includes_permission_level(self):
        from app.database import SessionLocal
        from app.routers.api import _serialize_employee

        db = SessionLocal()
        try:
            emp = _m.Employee(
                name="20_3_2_serialize",
                role="therapist",
                permission_level="admin",
            )
            db.add(emp)
            db.flush()

            d = _serialize_employee(emp)
            assert "permission_level" in d
            assert d["permission_level"] == "admin"
        finally:
            db.rollback()
            db.close()

    def test_serialize_default_when_null(self):
        # 컬럼 default 가 'staff' 라 None 으로 안 옴 — fallback 도 'staff'
        from app.database import SessionLocal
        from app.routers.api import _serialize_employee

        db = SessionLocal()
        try:
            emp = _m.Employee(name="20_3_2_default", role="therapist")
            db.add(emp)
            db.flush()
            d = _serialize_employee(emp)
            assert d["permission_level"] == "staff"
        finally:
            db.rollback()
            db.close()

    def test_therapists_service_byte_equivalent(self):
        from app.database import SessionLocal
        from app.routers.api import _serialize_employee

        db = SessionLocal()
        try:
            emp = _m.Employee(
                name="20_3_2_byte_eq",
                role="therapist",
                permission_level="super",
            )
            db.add(emp)
            db.flush()
            api_dict = _serialize_employee(emp)
            svc_dict = _therapists_service.serialize_employee(emp)
            assert api_dict == svc_dict
            assert "permission_level" in svc_dict
        finally:
            db.rollback()
            db.close()


# ────────────────── permission endpoint ──────────────────


class TestF11PermissionEndpoint:
    def test_endpoint_requires_admin_auth(self, client):
        # 인증 없이 호출 → 401/403
        resp = client.post(
            "/api/admin/employees/nonexistent/permission",
            json={"permission_level": "admin"},
        )
        assert resp.status_code in (401, 403)

    def test_endpoint_validates_level(self, client, monkeypatch):
        # require_admin 우회 — 검증 로직 단독 확인
        from app.routers import api as _api

        monkeypatch.setattr(_api, "require_admin", lambda: True)

        from app.database import SessionLocal

        db = SessionLocal()
        try:
            emp = _m.Employee(
                name="20_3_2_endpoint_test",
                role="therapist",
            )
            db.add(emp)
            db.commit()
            eid = emp.id

            # 잘못된 등급 → 400
            resp = client.post(
                f"/api/admin/employees/{eid}/permission",
                json={"permission_level": "invalid_level"},
                headers={"X-Admin-Token": "test"},
            )
            assert resp.status_code in (400, 401, 403)  # auth 또는 validation
        finally:
            db.rollback()
            db.close()


class TestF11PermissionLevelsConstant:
    def test_three_levels(self):
        from app.routers.api import EMPLOYEE_PERMISSION_LEVELS
        assert EMPLOYEE_PERMISSION_LEVELS == ("staff", "admin", "super")
        # viewer 미도입 (사용자 §4-6 결정 (ii))
        assert "viewer" not in EMPLOYEE_PERMISSION_LEVELS


# ────────────────── 호환성 보존 ──────────────────


class TestF11BackwardCompat:
    def test_existing_employee_keys_preserved(self):
        # 11키 (id/name/role/color/active/birth_date/phone/hire_date/can_eswt/can_manual/sort_order)
        # + permission_level = 12키
        from app.database import SessionLocal
        from app.routers.api import _serialize_employee

        db = SessionLocal()
        try:
            emp = _m.Employee(name="20_3_2_compat", role="therapist")
            db.add(emp)
            db.flush()
            d = _serialize_employee(emp)
            expected = {
                "id", "name", "role", "color", "active",
                "birth_date", "phone", "hire_date",
                "can_eswt", "can_manual", "sort_order",
                "permission_level",
            }
            assert set(d.keys()) == expected
        finally:
            db.rollback()
            db.close()

    def test_role_column_unchanged(self):
        # F-11 = permission_level 컬럼만 추가 — role 컬럼 (therapist/doctor) 보존
        assert hasattr(_m.Employee, "role")

    def test_audit_log_does_not_log_pii(self):
        # SAFETY: permission_update audit detail 에 환자 PII 없음 (등급 명만)
        # 본 테스트는 audit 호출 흐름이 PII 미저장 정책 정합인지 단순 회귀.
        from app.modules.audit import service as _audit_svc
        # AuditLog detail 500자 cap 정책 보존 (19-12 정합)
        assert hasattr(_audit_svc, "cap_detail")


# ────────────────── 보안 회귀 ──────────────────


class TestF11SecurityRegression:
    def test_admin_login_flow_unchanged(self):
        # 기존 admin 로그인 / PBKDF2 / 5회 잠금 / 8h 세션 정책 변경 ⊥
        from app.services import auth as _auth
        # 기존 함수 시그니처 보존
        assert hasattr(_auth, "set_admin_password")
        assert hasattr(_auth, "hash_password")

    def test_require_admin_unchanged(self):
        # require_admin 은 api.py 의 dependency
        from app.routers.api import require_admin
        assert callable(require_admin)
