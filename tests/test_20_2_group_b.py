"""20-2 그룹 B — F-13 /api/health + F-12 modules/notes/service + F-14 calendar 회귀.

검증 범위 (20-P-1 §4-B 사용자 결정값 정합):
  1. F-13 /api/health 신설 — 6개 키 (db_ok / migration_version / backup_age /
     disk_free / version / uptime).
  2. F-13 health TestClient 호출 회귀 — 200 + 응답 dict 키 셋 정합.
  3. F-12 modules/notes/service.py — Patient.memo / Appointment.memo read/write 헬퍼.
  4. F-14 modules/calendar/view_models — 19-3 helper 회귀 (FullCalendar event /
     therapist color / status opacity / leave 표시).
  5. 본 20-2 모듈은 외부 API 호출 / 실제 문자 발송 / 운영 DB 접근 ⊥.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.calendar import view_models as _cal
from app.modules.health import service as _health_service
from app.modules.notes import rules as _notes_rules
from app.modules.notes import service as _notes_service

# ────────────────── F-13 — health snapshot ──────────────────


class TestF13HealthSnapshot:
    def test_keys_set_matches_user_decision(self):
        # 사용자 §4-B 권장값 — 6개 키
        assert _health_service.HEALTH_SNAPSHOT_KEYS == frozenset({
            "db_ok",
            "migration_version",
            "backup_age",
            "disk_free",
            "version",
            "uptime",
        })

    def test_collect_health_snapshot_returns_six_keys(self):
        snap = _health_service.collect_health_snapshot()
        assert set(snap.keys()) == _health_service.HEALTH_SNAPSHOT_KEYS

    def test_db_ok_is_bool(self):
        snap = _health_service.collect_health_snapshot()
        assert isinstance(snap["db_ok"], bool)

    def test_migration_version_is_int(self):
        snap = _health_service.collect_health_snapshot()
        assert isinstance(snap["migration_version"], int)
        assert snap["migration_version"] >= 1

    def test_version_is_string(self):
        from app.config import APP_VERSION

        snap = _health_service.collect_health_snapshot()
        assert snap["version"] == APP_VERSION

    def test_uptime_is_int(self):
        snap = _health_service.collect_health_snapshot()
        assert isinstance(snap["uptime"], int)
        assert snap["uptime"] >= 0

    def test_uptime_increments_after_set_startup_time(self):
        import time

        _health_service.set_startup_time(time.time() - 10)
        snap = _health_service.collect_health_snapshot()
        assert snap["uptime"] >= 9


class TestF13HealthEndpoint:
    def test_get_health_returns_200_and_six_keys(self, client):
        # SAFETY: /api/health 는 인증 ⊥ public — 외부 모니터링 호환
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == _health_service.HEALTH_SNAPSHOT_KEYS

    def test_get_health_no_pii_in_response(self, client):
        # SAFETY: 응답에 API key / PII 원문 부재
        resp = client.get("/api/health")
        text = resp.text.lower()
        assert "api_key" not in text
        assert "password" not in text
        assert "phone" not in text


# ────────────────── F-12 — notes service ──────────────────


class TestF12NotesService:
    def test_get_patient_memo_returns_none_for_missing(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            assert _notes_service.get_patient_memo(db, "nonexistent_id") is None
        finally:
            db.close()

    def test_update_patient_memo_returns_false_for_missing(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            assert _notes_service.update_patient_memo(
                db, "nonexistent_id", "memo"
            ) is False
        finally:
            db.close()

    def test_update_and_get_patient_memo(self):
        from app.database import SessionLocal
        from app.models import models as _m

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_2_test_patient", phone="010-0000-0000",
                birth_date="1990-01-01", chart_no="C-20-2",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.commit()
            pid = patient.id

            ok = _notes_service.update_patient_memo(db, pid, "테스트 메모 내용")
            assert ok is True

            memo = _notes_service.get_patient_memo(db, pid)
            assert memo == "테스트 메모 내용"
        finally:
            db.rollback()
            db.close()

    def test_apply_cancel_memo_prefix(self):
        from app.database import SessionLocal
        from app.models import models as _m

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_2_test_cancel", phone="010-1111-1111",
                birth_date="1991-01-01", chart_no="C-20-2-CANCEL",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            appt = _m.Appointment(
                patient_id=patient.id,
                start_at=datetime.utcnow(),
                end_at=datetime.utcnow() + timedelta(minutes=30),
                duration_min=30,
                memo="기존 메모",
            )
            db.add(appt)
            db.commit()
            aid = appt.id

            ok = _notes_service.apply_cancel_memo_prefix(db, aid, "환자 요청")
            assert ok is True

            memo = _notes_service.get_appointment_memo(db, aid)
            assert "기존 메모" in memo
            assert "[취소] 환자 요청" in memo
        finally:
            db.rollback()
            db.close()

    def test_get_memo_by_kind_dispatches(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            # NOTE_KIND 분기 — 부재 entity 는 None
            assert _notes_service.get_memo_by_kind(
                db, note_kind=_notes_rules.NOTE_KIND_PATIENT,
                entity_id="nonexistent",
            ) is None
            assert _notes_service.get_memo_by_kind(
                db, note_kind=_notes_rules.NOTE_KIND_APPOINTMENT,
                entity_id="nonexistent",
            ) is None
            # 미지원 kind → None
            assert _notes_service.get_memo_by_kind(
                db, note_kind="unknown_kind",
                entity_id="any",
            ) is None
        finally:
            db.close()


# ────────────────── F-14 — calendar view-model 회귀 ──────────────────


class TestF14CalendarViewModelRegression:
    """COMPAT: 19-3 view_models.py 의 helper 가 본 20-2 시점에도 보존."""

    def test_unassigned_therapist_color_constant(self):
        assert _cal.UNASSIGNED_THERAPIST_COLOR == "#9CA3AF"

    def test_status_opacity_constants(self):
        assert _cal.STATUS_OPACITY["reserved"] == 1.0
        assert _cal.STATUS_OPACITY["approved"] == 1.0
        assert _cal.STATUS_OPACITY["canceled"] == 0.3

    def test_status_to_opacity_dispatches(self):
        assert _cal.status_to_opacity("reserved") == 1.0
        assert _cal.status_to_opacity("canceled") == 0.3
        assert _cal.status_to_opacity(None) == _cal.DEFAULT_OPACITY

    def test_therapist_color_returns_unassigned_when_none(self):
        assert _cal.therapist_color(None) == _cal.UNASSIGNED_THERAPIST_COLOR
        assert _cal.therapist_color("") == _cal.UNASSIGNED_THERAPIST_COLOR

    def test_therapist_color_passthrough(self):
        assert _cal.therapist_color("#ABCDEF") == "#ABCDEF"

    def test_leave_type_labels_present(self):
        assert "full" in _cal.LEAVE_TYPE_LABELS
        assert "am" in _cal.LEAVE_TYPE_LABELS
        assert "pm" in _cal.LEAVE_TYPE_LABELS

    def test_leave_kind_labels_present(self):
        assert "annual" in _cal.LEAVE_KIND_LABELS
        assert "monthly" in _cal.LEAVE_KIND_LABELS

    def test_helpers_callable(self):
        # 19-3 contract — 주요 helper 가 callable 보존
        assert callable(_cal.appointment_to_calendar_event)
        assert callable(_cal.employee_to_resource_view)
        assert callable(_cal.leave_to_display)
        assert callable(_cal.lighten_hex)
        assert callable(_cal.is_past_appointment)


# ────────────────── 보안 회귀 ──────────────────


class TestSecurityNoRegressions:
    def test_health_response_no_api_key_substring(self, client):
        resp = client.get("/api/health")
        body = resp.text
        assert "sk-" not in body  # OpenAI API key prefix
        assert "api_key" not in body.lower()

    def test_notes_service_does_not_log_pii(self):
        # SAFETY: 본 service 는 평문 메모 read/write 만 — 로그 출력 ⊥.
        # mask_memo_for_log 는 별도 호출 (rules.py).
        masked = _notes_rules.mask_memo_for_log("환자 010-1234-5678 호출")
        assert "010-1234-5678" not in masked
