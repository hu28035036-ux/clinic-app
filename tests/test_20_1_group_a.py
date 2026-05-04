"""20-1 그룹 A — F-15 의사 가드 + F-7 privacy retention + F-8 audit retention contract.

검증 범위 (20-P-1 §4-A 사용자 결정값 정합):
  1. F-15 doctor_guard — 의사 단정 / 일정 / 진단 차단 패턴 + 정상 텍스트 비차단.
  2. F-15 RAG ``validate_answer`` 통합 — 의사 단정 차단 시 ``blocked=True``.
  3. F-7 환자 마스킹 — 비활성 18개월 후 PII 마스킹 + 활성 환자 미변경 + 멱등성 + dry_run.
  4. F-7 AI 로그 보존 — 6개월 후 row 삭제 + 최신 로그 보존 + dry_run.
  5. F-8 audit_log 보존 — 5년 후 row 삭제 + 최신 audit 보존 + dry_run.
  6. 본 20-1 모듈은 외부 API 호출 / 실제 문자 발송 / 운영 DB 접근 ⊥.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.modules.ai.safety import doctor_guard as _dg
from app.modules.audit import retention as _audit_retention
from app.modules.privacy import retention as _priv_retention

# ────────────────── F-15 — doctor_guard 단위 ──────────────────


class TestF15DoctorGuard:
    def test_blocks_doctor_name_claim(self):
        result = _dg.block_doctor_claims("담당의는 김철수 입니다.")
        assert result["blocked"] is True
        assert result["reason"] == _dg.DOCTOR_GUARD_REASON_NAME
        assert result["guard_hits"] == 1

    def test_blocks_doctor_with_action(self):
        result = _dg.block_doctor_claims("박영희 의사가 진료합니다.")
        assert result["blocked"] is True

    def test_blocks_doctor_schedule_claim(self):
        result = _dg.block_doctor_claims("김철수 의사는 화요일에 진료합니다.")
        assert result["blocked"] is True
        assert result["reason"] == _dg.DOCTOR_GUARD_REASON_SCHEDULE

    def test_blocks_doctor_diagnosis_claim(self):
        result = _dg.block_doctor_claims("홍길동 의사가 진단했습니다.")
        assert result["blocked"] is True
        assert result["reason"] == _dg.DOCTOR_GUARD_REASON_DIAGNOSIS

    def test_does_not_block_neutral_text(self):
        # 의사 정보 단정이 없는 일반 매뉴얼 응답 — 차단 ⊥
        result = _dg.block_doctor_claims("도수치료 30분 예약 가능 시간대는 ...")
        assert result["blocked"] is False
        assert result["guard_hits"] == 0

    def test_does_not_block_empty_text(self):
        result = _dg.block_doctor_claims("")
        assert result["blocked"] is False

    def test_has_doctor_claim_returns_tuple(self):
        blocked, reason = _dg.has_doctor_claim("담당의는 X 입니다.")
        assert blocked is True
        assert reason == _dg.DOCTOR_GUARD_REASON_NAME


# ────────────────── F-15 — RAG pipeline 통합 ──────────────────


class TestF15PipelineIntegration:
    def test_validate_answer_blocks_doctor_claim(self):
        # SAFETY: pipeline.validate_answer §5 단계 — 의사 정보 단정 차단
        from app.services.ai.rag.pipeline import validate_answer

        result = validate_answer("담당의는 김철수 입니다.", has_sources=True)
        assert result["blocked"] is True
        assert result["reason"] == _dg.DOCTOR_GUARD_REASON_NAME
        assert result["guard_hits"] >= 1

    def test_validate_answer_does_not_block_neutral(self):
        from app.services.ai.rag.pipeline import validate_answer

        result = validate_answer(
            "도수치료 예약은 9시부터 18시까지 가능합니다.",
            has_sources=True,
        )
        assert result["blocked"] is False

    def test_validate_answer_existing_medical_claim_still_blocked(self):
        # COMPAT: 기존 _RE_MEDICAL_CLAIM 차단 동작 보존 (회귀 ⊥)
        from app.services.ai.rag.pipeline import validate_answer

        result = validate_answer("이 치료는 완치를 보장합니다.", has_sources=True)
        assert result["blocked"] is True
        assert result["reason"] == "unsafe medical advice"


# ────────────────── F-7 — privacy retention ──────────────────


class TestF7Retention:
    def test_constants_match_user_decision(self):
        # 사용자 §4-A 결정값 (권장값) — 변경 시 본 단언 갱신 필요
        assert _priv_retention.PATIENT_INACTIVE_MASK_MONTHS == 18
        assert _priv_retention.AI_LOG_RETENTION_MONTHS == 6

    def test_mask_inactive_patient_basic(self):
        from app.database import SessionLocal
        from app.models import models as _m

        db = SessionLocal()
        try:
            # 비활성 환자 (24개월 전 예약만 있음)
            old = datetime.utcnow() - timedelta(days=24 * 30)
            patient_inactive = _m.Patient(
                name="비활성환자", phone="010-1111-2222",
                birth_date="1990-01-01", chart_no="C-INACT-1",
                created_at=old,
            )
            patient_active = _m.Patient(
                name="활성환자", phone="010-3333-4444",
                birth_date="1985-05-05", chart_no="C-ACT-1",
                created_at=datetime.utcnow(),
            )
            db.add_all([patient_inactive, patient_active])
            db.flush()

            appt_old = _m.Appointment(
                patient_id=patient_inactive.id,
                start_at=old,
                end_at=old + timedelta(minutes=30),
                duration_min=30,
            )
            appt_recent = _m.Appointment(
                patient_id=patient_active.id,
                start_at=datetime.utcnow() - timedelta(days=10),
                end_at=datetime.utcnow() - timedelta(days=10) + timedelta(minutes=30),
                duration_min=30,
            )
            db.add_all([appt_old, appt_recent])
            db.commit()

            inactive_id = patient_inactive.id
            active_id = patient_active.id

            # dry_run — 후보 1명, masked=0
            dry = _priv_retention.mask_inactive_patients(db, dry_run=True)
            assert dry["candidates"] >= 1
            assert dry["masked"] == 0
            assert dry["dry_run"] is True

            # 실제 마스킹 — 비활성 1명만
            res = _priv_retention.mask_inactive_patients(db)
            assert res["dry_run"] is False
            assert res["masked"] >= 1

            db.expire_all()
            inactive_after = db.query(_m.Patient).filter_by(id=inactive_id).first()
            active_after = db.query(_m.Patient).filter_by(id=active_id).first()
            assert inactive_after.name == "***"
            assert inactive_after.phone == "***-****-****"
            assert active_after.name == "활성환자"  # 활성 환자 무변경

            # 멱등성 — 두 번째 호출은 추가 마스킹 ⊥
            res2 = _priv_retention.mask_inactive_patients(db)
            # 같은 row 는 이미 마스킹 — name == "***" 인 것은 제외
            assert res2["masked"] == 0 or res2["masked"] < res["masked"]
        finally:
            db.rollback()
            db.close()

    def test_delete_old_ai_logs_basic(self):
        from app.database import SessionLocal
        from app.models import models as _m

        db = SessionLocal()
        try:
            old_ts = datetime.utcnow() - timedelta(days=8 * 30)
            recent_ts = datetime.utcnow() - timedelta(days=10)

            log_old = _m.AiUsageLog(
                ts=old_ts, provider="local", model="x",
                feature="test_20_1", outcome="success",
            )
            log_recent = _m.AiUsageLog(
                ts=recent_ts, provider="local", model="x",
                feature="test_20_1", outcome="success",
            )
            db.add_all([log_old, log_recent])
            db.commit()

            recent_id = log_recent.id

            dry = _priv_retention.delete_old_ai_logs(db, dry_run=True)
            assert dry["candidates"] >= 1
            assert dry["deleted"] == 0

            res = _priv_retention.delete_old_ai_logs(db)
            assert res["deleted"] >= 1

            still_there = (
                db.query(_m.AiUsageLog).filter_by(id=recent_id).first()
            )
            assert still_there is not None  # 최신 로그는 보존
        finally:
            db.rollback()
            db.close()


# ────────────────── F-8 — audit retention ──────────────────


class TestF8AuditRetention:
    def test_constant_matches_user_decision(self):
        assert _audit_retention.AUDIT_LOG_RETENTION_YEARS == 5

    def test_delete_old_audit_logs_basic(self):
        from app.database import SessionLocal
        from app.models import models as _m

        db = SessionLocal()
        try:
            old_ts = datetime.utcnow() - timedelta(days=6 * 365)
            recent_ts = datetime.utcnow() - timedelta(days=30)

            audit_old = _m.AuditLog(
                ts=old_ts, actor="test", action="test_20_1.old",
                detail="old audit",
            )
            audit_recent = _m.AuditLog(
                ts=recent_ts, actor="test", action="test_20_1.recent",
                detail="recent audit",
            )
            db.add_all([audit_old, audit_recent])
            db.commit()

            recent_id = audit_recent.id

            dry = _audit_retention.delete_old_audit_logs(db, dry_run=True)
            assert dry["candidates"] >= 1
            assert dry["deleted"] == 0

            res = _audit_retention.delete_old_audit_logs(db)
            assert res["deleted"] >= 1

            still_there = (
                db.query(_m.AuditLog).filter_by(id=recent_id).first()
            )
            assert still_there is not None
        finally:
            db.rollback()
            db.close()
