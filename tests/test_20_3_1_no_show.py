"""20-3-1 F-10 노쇼 별도 필드 contract.

검증 범위 (20-P-2 §3 사용자 §3-7 권장값 정합):
  1. m014 마이그레이션 — Appointment.no_show BOOLEAN DEFAULT 0 추가, 기존 row 영향 0.
  2. Appointment 모델에 no_show 컬럼 + 기본값 False.
  3. _serialize_appointment 응답 extendedProps 에 no_show 추가, 기존 16키 보존.
  4. POST /api/appointments/{aid}/cancel 에 no_show 옵션 — true 시 obj.no_show=True.
  5. POST /api/appointments/{aid}/mark-no-show 신설 — no_show=True + status="canceled" 동시.
  6. /api/stats/summary 에 no_show_count 추가 — cancel 의 부분집합 카운트.
  7. SUMMARY_RESPONSE_KEYS frozenset 에 no_show_count 추가 (19-11 contract).
  8. 본 20-3-1 모듈은 외부 API 호출 / 실제 문자 발송 / 운영 DB 접근 ⊥.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.models import models as _m
from app.modules.stats import aggregators as _agg
from app.modules.stats import schemas as _stats_schemas

# ────────────────── m014 + 모델 ──────────────────


class TestF10Migration:
    def test_no_show_column_exists_in_model(self):
        assert hasattr(_m.Appointment, "no_show")

    def test_no_show_default_false(self):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_1_default", phone="010-0000-0000",
                birth_date="1990-01-01", chart_no="C-2031-D",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            appt = _m.Appointment(
                patient_id=patient.id,
                start_at=datetime.utcnow(),
                end_at=datetime.utcnow() + timedelta(minutes=30),
                duration_min=30,
            )
            db.add(appt)
            db.flush()
            # 기본값 = False
            assert appt.no_show is False or appt.no_show == 0
        finally:
            db.rollback()
            db.close()


# ────────────────── _serialize_appointment ──────────────────


class TestF10SerializeAppointment:
    def test_extendedprops_contains_no_show(self, client):
        # 응답 dict 에 no_show 가 포함되는지 — TestClient endpoint 호출
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_1_serialize", phone="010-1111-2222",
                birth_date="1991-01-01", chart_no="C-2031-S",
                created_at=datetime.utcnow(),
            )
            db.add(patient)
            db.flush()
            ts = datetime(2099, 11, 1, 10, 0)
            appt = _m.Appointment(
                patient_id=patient.id,
                start_at=ts,
                end_at=ts + timedelta(minutes=30),
                duration_min=30,
                treatment_codes='["manual30"]',
            )
            db.add(appt)
            db.commit()
            aid = appt.id

            # GET /api/appointments?range=...
            te = ts + timedelta(days=1)
            resp = client.get(
                "/api/appointments",
                params={
                    "start": ts.strftime("%Y-%m-%d"),
                    "end": te.strftime("%Y-%m-%d"),
                },
            )
            assert resp.status_code == 200
            events = resp.json()
            target = next((e for e in events if e["id"] == aid), None)
            assert target is not None
            assert "extendedProps" in target
            assert "no_show" in target["extendedProps"]
            assert target["extendedProps"]["no_show"] is False  # 기본값
        finally:
            db.rollback()
            db.close()


# ────────────────── cancel + mark-no-show ──────────────────


class TestF10CancelWithNoShow:
    def test_cancel_with_no_show_true(self, client):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_1_cancel", phone="010-3333-4444",
                birth_date="1992-02-02", chart_no="C-2031-C",
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
                version=1,
            )
            db.add(appt)
            db.commit()
            aid = appt.id

            resp = client.post(
                f"/api/appointments/{aid}/cancel",
                json={"memo": "환자 노쇼", "version": 1, "no_show": True},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["no_show"] is True

            # DB 확인
            db.expire_all()
            after = db.query(_m.Appointment).filter_by(id=aid).first()
            assert after.no_show is True
            assert after.status == "canceled"
        finally:
            db.rollback()
            db.close()


class TestF10MarkNoShowEndpoint:
    def test_mark_no_show_sets_both_flags(self, client):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_1_mark", phone="010-5555-6666",
                birth_date="1993-03-03", chart_no="C-2031-M",
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
            db.commit()
            aid = appt.id

            resp = client.post(f"/api/appointments/{aid}/mark-no-show")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["no_show"] is True
            assert data["status"] == "canceled"

            db.expire_all()
            after = db.query(_m.Appointment).filter_by(id=aid).first()
            assert after.no_show is True
            assert after.status == "canceled"
            assert "[노쇼]" in (after.memo or "")
        finally:
            db.rollback()
            db.close()

    def test_mark_no_show_blocks_approved(self, client):
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            patient = _m.Patient(
                name="20_3_1_approved", phone="010-7777-8888",
                birth_date="1994-04-04", chart_no="C-2031-A",
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
                status="approved",
            )
            db.add(appt)
            db.commit()
            aid = appt.id

            resp = client.post(f"/api/appointments/{aid}/mark-no-show")
            assert resp.status_code == 400
        finally:
            db.rollback()
            db.close()


# ────────────────── stats no_show_count ──────────────────


class TestF10StatsAggregator:
    def test_aggregate_summary_includes_no_show_count(self):
        # SimpleNamespace 로 row mock
        from types import SimpleNamespace

        rows = [
            SimpleNamespace(
                treatment_codes='["manual30"]',
                status="canceled",
                no_show=True,
            ),
            SimpleNamespace(
                treatment_codes='["manual30"]',
                status="canceled",
                no_show=False,
            ),
            SimpleNamespace(
                treatment_codes='["manual30"]',
                status="approved",
                no_show=False,
            ),
        ]

        def parse(c):
            import json
            return json.loads(c) if c else []

        result = _agg.aggregate_summary(
            rows=rows,
            manual_codes_set={"manual30"},
            treatment_code=None,
            parse_codes=parse,
        )
        assert "no_show_count" in result
        # 노쇼 1건 (cancel + no_show=True)
        assert result["no_show_count"] == 1
        # canceled 카운트 = 노쇼 포함 (cancel 의 부분집합 정책)
        assert result["canceled"] == 2

    def test_summary_response_keys_include_no_show_count(self):
        assert "no_show_count" in _stats_schemas.SUMMARY_RESPONSE_KEYS

    def test_stats_summary_endpoint_returns_no_show_count(self, client):
        resp = client.get("/api/stats/summary", params={"year": 2099, "month": 11})
        assert resp.status_code == 200
        data = resp.json()
        assert "no_show_count" in data
        assert isinstance(data["no_show_count"], int)
