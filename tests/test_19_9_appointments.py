"""19-9 appointments 예약 service / repository 분리 contract.

검증 범위 (19-9 세션 지시문 정합):
  1. ``app.modules.appointments.rules`` 의 상태 상수가 ``app.models.models.APPT_STATUSES``
     와 byte-equivalent.
  2. 상태 전이 판정 helper (``is_editable_status`` / ``is_approvable_status`` /
     ``is_revertable_status`` / ``is_cancelable_status`` / ``is_already_approved`` /
     ``is_canceled``) 가 라우터 인라인 분기 정합.
  3. 취소 메모 포맷 (``append_cancel_memo``) 이 ``api.py:cancel_appointment``
     line 2016 인라인 패턴과 byte-equivalent.
  4. 승인자 정규화 (``normalize_approved_by``) 가 ``api.py:approve_appointment``
     line 1970 정합.
  5. 카운트 clamp (``clamp_count_at_zero``) 가 ``api.py:_bump_patient_count``
     line 1946 / 1952 정합.
  6. ``appointments.repository`` read-only helper 가 ``api.py`` query 패턴과 동등.
  7. ``appointments.service`` 의 모든 응답 빌더가 ``api.py`` 응답 dict 와 byte-equivalent.
  8. ``appointments.schemas`` 의 contract 상수가 실제 라우터 응답 dict 의 키 셋과 일치 —
     **응답 키 회귀 보호** (UI / SMS / 통계 / AI 의존).
  9. modules.appointments 가 ``app.routers`` 미참조 — 단방향 경계 (D-4).
 10. 라우터 핸들러 시그니처 무수정 (예약 CRUD 본체 보존).
 11. 기존 예약 / 환자 이력 / SMS / 통계 / AI 흐름 영향 없음.
"""
from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path

import pytest

from app.models import models as _models
from app.modules.appointments import availability as _av
from app.modules.appointments import repository as _repo
from app.modules.appointments import rules as _rules
from app.modules.appointments import schemas as _schemas
from app.modules.appointments import service as _service

# ──────────────────────── 1. 상태 상수 정합 ────────────────────────


def test_appt_status_constants_match_models():
    """COMPAT: ``app.models.models.APPT_STATUSES`` 와 byte-equivalent."""
    assert _rules.APPT_STATUS_RESERVED == "reserved"
    assert _rules.APPT_STATUS_APPROVED == "approved"
    assert _rules.APPT_STATUS_CANCELED == "canceled"
    assert set(_rules.APPT_STATUSES) == set(_models.APPT_STATUSES)


def test_appt_statuses_tuple_is_immutable():
    """APPT_STATUSES 는 ``tuple`` 로 노출 — 외부 수정 ⊥."""
    assert isinstance(_rules.APPT_STATUSES, tuple)


# ──────────────────────── 2. 상태 전이 판정 ────────────────────────


@pytest.mark.parametrize(
    "status,editable,approvable,revertable,cancelable",
    [
        # reserved → 수정/승인/취소 OK, 되돌림 ⊥.
        ("reserved", True, True, False, True),
        # approved → 수정/승인 ⊥, 되돌림 OK, 취소 ⊥.
        ("approved", False, False, True, False),
        # canceled → 수정/승인 ⊥, 되돌림 ⊥, 취소 OK (라우터 분기 정합 — 메모 누적).
        ("canceled", False, False, False, True),
        # None / 빈 / 알 수 없음 → 수정/승인 OK (보수 fallback), 되돌림 ⊥, 취소 OK.
        (None, True, True, False, True),
        ("", True, True, False, True),
        ("treated", True, True, False, True),
    ],
)
def test_status_transition_predicates(
    status, editable, approvable, revertable, cancelable
):
    """COMPAT: ``api.py`` 의 ``status in/== ...`` 인라인 분기 정합."""
    assert _rules.is_editable_status(status) is editable
    assert _rules.is_approvable_status(status) is approvable
    assert _rules.is_revertable_status(status) is revertable
    assert _rules.is_cancelable_status(status) is cancelable


@pytest.mark.parametrize(
    "status,is_appr,is_canc",
    [
        ("approved", True, False),
        ("canceled", False, True),
        ("reserved", False, False),
        (None, False, False),
    ],
)
def test_status_state_predicates(status, is_appr, is_canc):
    assert _rules.is_already_approved(status) is is_appr
    assert _rules.is_canceled(status) is is_canc


# ──────────────────────── 3. 취소 메모 포맷 ────────────────────────


@pytest.mark.parametrize(
    "existing,new_memo,expected",
    [
        # 기존 메모 없음 + 사용자 사유 없음 → 단순 prefix.
        (None, None, "\n[취소]"),
        ("", None, "\n[취소]"),
        (None, "", "\n[취소]"),  # falsy new_memo → prefix only
        # 기존 메모 없음 + 사용자 사유 있음.
        (None, "환자 사정", "\n[취소] 환자 사정"),
        ("", "no-show", "\n[취소] no-show"),
        # 기존 메모 있음 + 사용자 사유 없음.
        ("기존 메모", None, "기존 메모\n[취소]"),
        ("first line", "", "first line\n[취소]"),
        # 기존 메모 있음 + 사용자 사유 있음.
        ("초진", "재방문", "초진\n[취소] 재방문"),
    ],
)
def test_append_cancel_memo_byte_equivalent_with_api(existing, new_memo, expected):
    """COMPAT: ``api.py:cancel_appointment`` (line 2016) 인라인 패턴 정합."""
    assert _rules.append_cancel_memo(existing, new_memo) == expected
    # service.append_cancel_memo 도 같은 결과 (re-export).
    assert _service.append_cancel_memo(existing, new_memo) == expected


# ──────────────────────── 4. 승인자 정규화 ────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, "원무과"),
        ("", "원무과"),
        ("   ", "원무과"),
        ("원무과", "원무과"),
        ("김원장", "김원장"),
        ("  공백있는이름  ", "공백있는이름"),
    ],
)
def test_normalize_approved_by(raw, expected):
    """COMPAT: ``api.py:approve_appointment`` line 1970 정합."""
    assert _rules.normalize_approved_by(raw) == expected


# ──────────────────────── 5. 카운트 clamp ────────────────────────


@pytest.mark.parametrize(
    "current,delta,expected",
    [
        (0, 1, 1),
        (5, 1, 6),
        (5, -1, 4),
        (1, -5, 0),
        (None, 1, 1),
        (None, -3, 0),
        (None, 0, 0),
    ],
)
def test_clamp_count_at_zero(current, delta, expected):
    """COMPAT: ``api.py:_bump_patient_count`` line 1946 / 1952 정합."""
    assert _rules.clamp_count_at_zero(current, delta) == expected


# ──────────────────────── 6. repository — DB 격리 fixture ────────────────────


def test_get_appointment_by_id_round_trip(client):
    """COMPAT: ``db.get(Appointment, aid)`` 정합 — 시드된 환자 사용해 직접 row 생성."""
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("홍길동테스트")
    tid = get_test_therapist_id("김테스트치료사")

    db = SessionLocal()
    try:
        # 직접 Appointment row 생성.
        obj = _m.Appointment(
            patient_id=pid,
            therapist_id=tid,
            start_at=datetime(2099, 7, 15, 10, 0),
            end_at=datetime(2099, 7, 15, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="reserved",
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        appt_id = obj.id

        # repository helper 로 round-trip.
        fetched = _repo.get_appointment_by_id(db, appt_id)
        assert fetched is not None
        assert fetched.id == appt_id

        # 미존재 ID → None.
        assert _repo.get_appointment_by_id(db, "non-existent") is None

        # cleanup.
        db.delete(fetched)
        db.commit()
    finally:
        db.close()


def test_list_appointments_in_range_byte_equivalent_with_api(client):
    """COMPAT: ``api.py:list_appointments`` (line 1615~1617) 와 동일 결과."""
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("홍길동테스트")
    tid = get_test_therapist_id("김테스트치료사")

    db = SessionLocal()
    try:
        # 같은 날 두 시간대 예약 생성.
        appts = []
        for hour in (10, 14):
            obj = _m.Appointment(
                patient_id=pid, therapist_id=tid,
                start_at=datetime(2099, 7, 16, hour, 0),
                end_at=datetime(2099, 7, 16, hour, 30),
                duration_min=30,
                treatment_codes='["manual30"]',
                status="reserved",
            )
            db.add(obj)
            appts.append(obj)
        db.commit()
        for a in appts:
            db.refresh(a)

        ts = datetime(2099, 7, 16, 0, 0)
        te = datetime(2099, 7, 17, 0, 0)

        # repository
        repo_rows = _repo.list_appointments_in_range(
            db, start_naive=ts, end_naive=te,
        )
        # api.py 인라인 query (byte-equivalent 비교).
        api_rows = (
            db.query(_m.Appointment)
            .filter(_m.Appointment.start_at >= ts, _m.Appointment.start_at < te)
            .all()
        )

        repo_ids = sorted(a.id for a in repo_rows)
        api_ids = sorted(a.id for a in api_rows)
        assert repo_ids == api_ids
        assert len(repo_rows) >= 2  # 최소 우리가 만든 2건

        # cleanup.
        for a in appts:
            db.delete(a)
        db.commit()
    finally:
        db.close()


def test_list_active_appointments_for_patient(client):
    """COMPAT: ``api.py:patient_manual_history_summary`` query 정합."""
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("김영희테스트")
    tid = get_test_therapist_id("김테스트치료사")

    db = SessionLocal()
    try:
        # reserved + canceled 1건씩.
        a1 = _m.Appointment(
            patient_id=pid, therapist_id=tid,
            start_at=datetime(2099, 7, 17, 10, 0),
            end_at=datetime(2099, 7, 17, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="reserved",
        )
        a2 = _m.Appointment(
            patient_id=pid, therapist_id=tid,
            start_at=datetime(2099, 7, 17, 11, 0),
            end_at=datetime(2099, 7, 17, 11, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="canceled",
        )
        db.add(a1)
        db.add(a2)
        db.commit()
        db.refresh(a1)
        db.refresh(a2)

        rows = _repo.list_active_appointments_for_patient(db, pid)
        ids = {a.id for a in rows}
        assert a1.id in ids  # reserved
        assert a2.id not in ids  # canceled 제외

        # cleanup.
        db.delete(a1)
        db.delete(a2)
        db.commit()
    finally:
        db.close()


def test_list_approved_appointments_for_patient_desc(client):
    """COMPAT: ``api.py:patient_history`` (line 1538~1542) query 정합."""
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("박철수테스트")
    tid = get_test_therapist_id("김테스트치료사")

    db = SessionLocal()
    try:
        # approved 2건 (날짜 다름) + reserved 1건.
        a1 = _m.Appointment(
            patient_id=pid, therapist_id=tid,
            start_at=datetime(2099, 7, 18, 10, 0),
            end_at=datetime(2099, 7, 18, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="approved",
        )
        a2 = _m.Appointment(
            patient_id=pid, therapist_id=tid,
            start_at=datetime(2099, 7, 19, 10, 0),
            end_at=datetime(2099, 7, 19, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="approved",
        )
        a3 = _m.Appointment(
            patient_id=pid, therapist_id=tid,
            start_at=datetime(2099, 7, 20, 10, 0),
            end_at=datetime(2099, 7, 20, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="reserved",
        )
        for a in (a1, a2, a3):
            db.add(a)
        db.commit()
        for a in (a1, a2, a3):
            db.refresh(a)

        rows = _repo.list_approved_appointments_for_patient_desc(db, pid)
        ids = [a.id for a in rows]
        # approved 만, 최신순 (a2 > a1).
        assert a3.id not in ids  # reserved 제외
        assert a1.id in ids
        assert a2.id in ids
        assert ids.index(a2.id) < ids.index(a1.id)  # desc 정렬

        # cleanup.
        for a in (a1, a2, a3):
            db.delete(a)
        db.commit()
    finally:
        db.close()


def test_last_appointment_per_patient_excludes_canceled(client):
    """COMPAT: ``api.py:last_appointments`` (line 1489~1494) query 정합.

    검증 방식: 사전 ``last`` 값을 캡처한 뒤 *더 미래* 의 ``canceled`` 를 추가하고,
    ``last`` 가 변하지 않음을 확인 — ``canceled`` 가 group_by max 에서 제외됨을
    *상대적* 으로 검증 (다른 테스트가 남긴 시드 영향 ⊥).
    """
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("홍길동테스트")
    tid = get_test_therapist_id("이테스트치료사")

    db = SessionLocal()
    try:
        # 사전 ``last`` 캡처 (다른 테스트가 만든 reserved 시각 포함 가능).
        before_rows = _repo.last_appointment_per_patient(db)
        before_last = {p: lst for p, lst in before_rows}.get(pid)

        # 사전 last 보다 *확실히 미래* 인 canceled 추가 (2099-12-31).
        canceled_dt = datetime(2099, 12, 31, 10, 0)
        a_canceled = _m.Appointment(
            patient_id=pid, therapist_id=tid,
            start_at=canceled_dt,
            end_at=datetime(2099, 12, 31, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="canceled",
        )
        db.add(a_canceled)
        db.commit()
        db.refresh(a_canceled)

        # canceled 추가 후 ``last`` 가 변하지 않아야 함 (group_by max 가 canceled 제외).
        after_rows = _repo.last_appointment_per_patient(db)
        after_last = {p: lst for p, lst in after_rows}.get(pid)
        assert after_last == before_last
        # 만약 last 가 존재한다면 canceled_dt 보다 작아야 (canceled 미반영 검증).
        if after_last is not None:
            assert after_last < canceled_dt

        # cleanup.
        db.delete(a_canceled)
        db.commit()
    finally:
        db.close()


def test_find_assignment_for_code_returns_match(client):
    """COMPAT: ``api.py:change_assignment`` line 1778 정합."""
    from app.database import SessionLocal
    from app.models import models as _m
    from tests.harness.seed_data import get_test_patient_id

    pid = get_test_patient_id("홍길동테스트")

    db = SessionLocal()
    try:
        appt = _m.Appointment(
            patient_id=pid, therapist_id=None,
            start_at=datetime(2099, 7, 22, 10, 0),
            end_at=datetime(2099, 7, 22, 10, 10),
            duration_min=10,
            treatment_codes='["injection"]',
            status="reserved",
        )
        db.add(appt)
        db.flush()
        asn = _m.TreatmentAssignment(
            appointment_id=appt.id,
            treatment_code="injection",
            handler_id=None,
        )
        db.add(asn)
        db.commit()
        db.refresh(appt)

        match = _repo.find_assignment_for_code(appt, treatment_code="injection")
        assert match is not None
        assert match.treatment_code == "injection"

        # 미매칭 코드 → None.
        assert _repo.find_assignment_for_code(appt, treatment_code="manual30") is None
        # appointment None → None.
        assert _repo.find_assignment_for_code(None, treatment_code="injection") is None

        # cleanup.
        db.delete(appt)
        db.commit()
    finally:
        db.close()


def test_find_treatment_by_code(client):
    """COMPAT: ``api.py:_bump_patient_count`` (line 1938) 정합."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        # 시드된 manual30 존재.
        t = _repo.find_treatment_by_code(db, "manual30")
        assert t is not None
        assert t.code == "manual30"
        assert _repo.find_treatment_by_code(db, "non-existent") is None
    finally:
        db.close()


# ──────────────────────── 7. service — 응답 빌더 byte-equivalent ─────────────


def test_build_create_response():
    """COMPAT: ``api.py:create_appointment`` (line 1661) 정합."""
    out = _service.build_create_response(appointment_id="abc123", status="reserved")
    assert out == {"id": "abc123", "status": "reserved"}
    assert set(out.keys()) == _schemas.CREATE_RESPONSE_KEYS


def test_build_update_response_versions():
    """COMPAT: ``api.py:update_appointment`` (line 1744) 정합."""
    assert _service.build_update_response(version=5) == {"ok": True, "version": 5}
    assert _service.build_update_response(version=0) == {"ok": True, "version": 0}
    assert _service.build_update_response(version=None) == {"ok": True, "version": 0}


def test_build_approve_response():
    """COMPAT: ``api.py:approve_appointment`` (line 1979) 정합."""
    out = _service.build_approve_response(status="approved", version=3)
    assert out == {"ok": True, "status": "approved", "version": 3}
    assert set(out.keys()) == _schemas.APPROVE_RESPONSE_KEYS


def test_build_revert_response():
    """COMPAT: ``api.py:revert_approve`` (line 2003) 정합."""
    out = _service.build_revert_response(version=2)
    assert out == {"ok": True, "version": 2}
    assert set(out.keys()) == _schemas.REVERT_RESPONSE_KEYS


def test_build_cancel_response():
    """COMPAT: ``api.py:cancel_appointment`` (line 2089) 정합.

    20-3-1 (post-19-P / F-10): ``no_show`` 키 추가 — 3키 응답.
    """
    out = _service.build_cancel_response(version=4, no_show=False)
    assert out == {"ok": True, "version": 4, "no_show": False}
    assert set(out.keys()) == _schemas.CANCEL_RESPONSE_KEYS

    # 20-3-1 (post-19-P / F-10): 노쇼 동시 적용 분기
    out2 = _service.build_cancel_response(version=5, no_show=True)
    assert out2 == {"ok": True, "version": 5, "no_show": True}
    assert set(out2.keys()) == _schemas.CANCEL_RESPONSE_KEYS


def test_build_delete_response():
    """COMPAT: ``api.py:delete_appointment`` (line 2038) 정합."""
    out = _service.build_delete_response()
    assert out == {"ok": True}
    assert set(out.keys()) == _schemas.DELETE_RESPONSE_KEYS


def test_build_split_no_split_response():
    """COMPAT: ``api.py:split_appointment_code`` (line 1877) 정합."""
    out = _service.build_split_no_split_response(appointment_id="orig", version=1)
    assert out == {"ok": True, "split": False, "id": "orig", "version": 1}
    assert set(out.keys()) == _schemas.SPLIT_NO_SPLIT_RESPONSE_KEYS


def test_build_split_real_response():
    """COMPAT: ``api.py:split_appointment_code`` (line 1925~1931) 정합."""
    out = _service.build_split_real_response(
        original_id="orig", new_id="new", version=2,
    )
    assert out == {
        "ok": True, "split": True,
        "original_id": "orig", "new_id": "new", "version": 2,
    }
    assert set(out.keys()) == _schemas.SPLIT_REAL_RESPONSE_KEYS


def test_build_last_appointments_response():
    """COMPAT: ``api.py:last_appointments`` (line 1495) 정합."""
    rows = [
        ("pid1", datetime(2099, 7, 15, 10, 0)),
        ("pid2", None),  # group max 가 None 인 케이스 (이론상 없지만 guard).
    ]
    out = _service.build_last_appointments_response(rows)
    assert out == {
        "pid1": "2099-07-15T10:00:00",
        "pid2": None,
    }


def test_build_manual_history_summary():
    """COMPAT: ``api.py:patient_manual_history_summary`` (line 1516~1522) 정합."""
    out = _service.build_manual_history_summary(
        patient_id="p1",
        manual_appointment_ids=["a1", "a2"],
        has_new_patient_flag=True,
    )
    assert out == {
        "patient_id": "p1",
        "has_manual_history": True,
        "manual_count": 2,
        "has_new_patient_flag": True,
        "manual_appointment_ids": ["a1", "a2"],
    }
    assert set(out.keys()) == _schemas.MANUAL_HISTORY_SUMMARY_KEYS

    # 빈 manual_appointment_ids → has_manual_history=False, count=0.
    out2 = _service.build_manual_history_summary(
        patient_id="p2", manual_appointment_ids=[], has_new_patient_flag=False,
    )
    assert out2["has_manual_history"] is False
    assert out2["manual_count"] == 0


def test_build_patient_history_envelope():
    """COMPAT: ``api.py:patient_history`` (line 1597~1603) 정합."""
    out = _service.build_patient_history_envelope(
        total_days=3, offset=0, limit=10, days=[], legacy_items=[],
    )
    assert set(out.keys()) == _schemas.PATIENT_HISTORY_ENVELOPE_KEYS
    assert out["total"] == 3
    assert out["offset"] == 0
    assert out["limit"] == 10
    assert out["days"] == []
    assert out["items"] == []


# ──────────────────────── 8. schemas — contract 회귀 보호 ────────────────────


def test_create_response_keys_contract():
    """``schemas.CREATE_RESPONSE_KEYS`` 가 ``service.build_create_response`` 키와 일치."""
    out = _service.build_create_response(appointment_id="x", status="reserved")
    assert set(out.keys()) == _schemas.CREATE_RESPONSE_KEYS


def test_update_response_keys_contract():
    out = _service.build_update_response(version=1)
    assert set(out.keys()) == _schemas.UPDATE_RESPONSE_KEYS


def test_assign_response_keys_contract():
    """``ASSIGN_RESPONSE_KEYS`` == ``UPDATE_RESPONSE_KEYS`` (api.py:1791 정합)."""
    # change_assignment 도 update 와 동일 응답 dict 반환.
    out = _service.build_update_response(version=2)
    assert set(out.keys()) == _schemas.ASSIGN_RESPONSE_KEYS


def test_appointment_extended_props_keys_match_serializer(client):
    """``api.py:_serialize_appointment`` 의 extendedProps 키가 contract 정합."""
    from app.database import SessionLocal
    from app.models import models as _m
    from app.routers.api import _serialize_appointment
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("홍길동테스트")
    tid = get_test_therapist_id("김테스트치료사")

    db = SessionLocal()
    try:
        appt = _m.Appointment(
            patient_id=pid, therapist_id=tid,
            start_at=datetime(2099, 7, 23, 10, 0),
            end_at=datetime(2099, 7, 23, 10, 30),
            duration_min=30,
            treatment_codes='["manual30"]',
            status="reserved",
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)

        result = _serialize_appointment(appt)
        # top-level 6키 (id/start/end/color/textColor/extendedProps).
        assert set(result.keys()) == _schemas.APPOINTMENT_SERIALIZE_TOP_KEYS
        # extendedProps 17키 (16 + opacity 같은 식 등 — 실제 키 확인).
        assert set(result["extendedProps"].keys()) == _schemas.APPOINTMENT_EXTENDED_PROPS_KEYS

        # cleanup.
        db.delete(appt)
        db.commit()
    finally:
        db.close()


# ──────────────────────── 9. 단방향 경계 (D-4) ────────────────────────


def test_rules_does_not_import_routers():
    """rules.py 가 ``app.routers`` 미참조 — 단방향 경계."""
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src
    assert "from app.routers" not in src


def test_rules_does_not_import_orm_models():
    """rules.py 가 ORM 테이블 클래스 미참조 — 순수 helper."""
    src = Path(_rules.__file__).read_text(encoding="utf-8")
    # constants 만 허용 — models import ⊥.
    assert "from app.models.models" not in src
    assert "import app.models.models" not in src
    assert "from app.database" not in src
    assert "sqlalchemy" not in src.lower()


def test_repository_does_not_import_routers():
    src = Path(_repo.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_service_does_not_import_routers():
    src = Path(_service.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_schemas_does_not_import_routers():
    src = Path(_schemas.__file__).read_text(encoding="utf-8")
    assert "app.routers" not in src


def test_repository_uses_lazy_import_for_models():
    """repository.py 가 ``app.models`` 을 함수 안 lazy import — 순환참조 회피."""
    src = Path(_repo.__file__).read_text(encoding="utf-8")
    for line in src.splitlines():
        if line.startswith("from app.models"):
            pytest.fail(f"top-level app.models import 발견: {line}")
        if line.startswith("from sqlalchemy"):
            pytest.fail(f"top-level sqlalchemy import 발견: {line}")


def test_modules_appointments_importable():
    """app.modules.appointments 패키지 import 가능."""
    import app.modules.appointments  # noqa: F401
    import app.modules.appointments.availability  # noqa: F401
    import app.modules.appointments.repository  # noqa: F401
    import app.modules.appointments.rules  # noqa: F401
    import app.modules.appointments.schemas  # noqa: F401
    import app.modules.appointments.service  # noqa: F401


# ──────────────────────── 10. 라우터 시그니처 무수정 ────────────────────────


def test_create_appointment_router_signature_unchanged():
    """``api.py:create_appointment`` 시그니처 유지."""
    from app.routers.api import create_appointment

    sig = inspect.signature(create_appointment)
    assert "p" in sig.parameters
    assert "db" in sig.parameters


def test_update_appointment_router_signature_unchanged():
    from app.routers.api import update_appointment

    sig = inspect.signature(update_appointment)
    assert "aid" in sig.parameters
    assert "p" in sig.parameters
    assert "db" in sig.parameters


def test_approve_appointment_router_signature_unchanged():
    from app.routers.api import approve_appointment

    sig = inspect.signature(approve_appointment)
    assert "aid" in sig.parameters
    assert "p" in sig.parameters
    assert "db" in sig.parameters


def test_cancel_appointment_router_signature_unchanged():
    from app.routers.api import cancel_appointment

    sig = inspect.signature(cancel_appointment)
    assert "aid" in sig.parameters
    assert "p" in sig.parameters


def test_revert_approve_router_signature_unchanged():
    from app.routers.api import revert_approve

    sig = inspect.signature(revert_approve)
    assert "aid" in sig.parameters


def test_delete_appointment_router_signature_unchanged():
    from app.routers.api import delete_appointment

    sig = inspect.signature(delete_appointment)
    assert "aid" in sig.parameters
    assert "db" in sig.parameters


def test_change_assignment_router_signature_unchanged():
    from app.routers.api import change_assignment

    sig = inspect.signature(change_assignment)
    assert "aid" in sig.parameters
    assert "p" in sig.parameters


def test_split_appointment_code_router_signature_unchanged():
    from app.routers.api import split_appointment_code

    sig = inspect.signature(split_appointment_code)
    assert "aid" in sig.parameters
    assert "payload" in sig.parameters


def test_list_appointments_router_signature_unchanged():
    from app.routers.api import list_appointments

    sig = inspect.signature(list_appointments)
    assert "start" in sig.parameters
    assert "end" in sig.parameters


def test_last_appointments_router_signature_unchanged():
    from app.routers.api import last_appointments

    sig = inspect.signature(last_appointments)
    assert "db" in sig.parameters


def test_patient_manual_history_summary_router_signature_unchanged():
    from app.routers.api import patient_manual_history_summary

    sig = inspect.signature(patient_manual_history_summary)
    assert "pid" in sig.parameters


def test_patient_history_router_signature_unchanged():
    from app.routers.api import patient_history

    sig = inspect.signature(patient_history)
    assert "pid" in sig.parameters
    assert "offset" in sig.parameters
    assert "limit" in sig.parameters


def test_serialize_appointment_router_signature_unchanged():
    """``api.py:_serialize_appointment`` 의 시그니처 유지."""
    from app.routers.api import _serialize_appointment

    sig = inspect.signature(_serialize_appointment)
    assert list(sig.parameters.keys()) == ["a"]


# ──────────────────────── 11. 기존 흐름 영향 없음 (계약 회귀 보호) ────────────


def test_create_appointment_endpoint_keys_match_contract(client):
    """API 계약: ``POST /appointments`` 응답 키 = ``CREATE_RESPONSE_KEYS``."""
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("홍길동테스트")
    tid = get_test_therapist_id("김테스트치료사")

    payload = {
        "patient_id": pid,
        "therapist_id": tid,
        "treatment_codes": ["manual30"],
        "start_at": "2099-07-24T10:00:00",
        "duration_min": 30,
        "memo": "",
        "assignments": [],
    }
    r = client.post("/api/appointments", json=payload)
    assert r.status_code == 200
    assert set(r.json().keys()) == _schemas.CREATE_RESPONSE_KEYS

    # cleanup — 직접 DB 에서 삭제.
    appt_id = r.json()["id"]
    from app.database import SessionLocal
    from app.models import models as _m
    db = SessionLocal()
    try:
        appt = db.get(_m.Appointment, appt_id)
        if appt:
            db.delete(appt)
            db.commit()
    finally:
        db.close()


def test_list_appointments_endpoint_returns_serialize_top_keys(client):
    """``GET /appointments`` 의 항목별 키가 contract 정합."""
    from tests.harness.seed_data import get_test_patient_id, get_test_therapist_id

    pid = get_test_patient_id("홍길동테스트")
    tid = get_test_therapist_id("김테스트치료사")

    create_payload = {
        "patient_id": pid,
        "therapist_id": tid,
        "treatment_codes": ["manual30"],
        "start_at": "2099-07-25T10:00:00",
        "duration_min": 30,
        "memo": "",
        "assignments": [],
    }
    r = client.post("/api/appointments", json=create_payload)
    assert r.status_code == 200
    appt_id = r.json()["id"]

    try:
        list_r = client.get(
            "/api/appointments?start=2099-07-25T00:00:00&end=2099-07-26T00:00:00"
        )
        assert list_r.status_code == 200
        items = list_r.json()
        assert len(items) >= 1
        for item in items:
            # top-level 6키 contract.
            assert set(item.keys()) == _schemas.APPOINTMENT_SERIALIZE_TOP_KEYS
            assert set(item["extendedProps"].keys()) == _schemas.APPOINTMENT_EXTENDED_PROPS_KEYS
    finally:
        # cleanup.
        from app.database import SessionLocal
        from app.models import models as _m
        db = SessionLocal()
        try:
            appt = db.get(_m.Appointment, appt_id)
            if appt:
                db.delete(appt)
                db.commit()
        finally:
            db.close()


def test_last_appointments_handler_directly_callable(client):
    """``last_appointments`` 핸들러 직접 호출이 정상 — repository helper 와 동등.

    NOTE: ``GET /api/patients/last-appointments`` URL 은 라우터 선언 순서상
    ``GET /api/patients/{pid}`` (api.py:1348, line 1487 보다 먼저) 와 충돌해
    *기존 동작* 으로 ``{pid}`` 로 매치됨 — 프론트 (main.html:3421) 의 ``try/catch``
    가 실패를 무음 처리. 본 테스트는 *핸들러 자체* 의 동작을 검증 (라우팅 충돌은
    19-9 범위 *외* — 기존 동작 보존).
    """
    from app.database import SessionLocal
    from app.routers.api import last_appointments

    db = SessionLocal()
    try:
        result = last_appointments(db=db)
        assert isinstance(result, dict)
        # 모든 값은 ISO8601 또는 None.
        for v in result.values():
            assert v is None or isinstance(v, str)
    finally:
        db.close()


def test_patient_manual_history_summary_endpoint_keys(client):
    """``GET /patients/{pid}/manual-history-summary`` 응답 키 contract."""
    from tests.harness.seed_data import get_test_patient_id

    pid = get_test_patient_id("홍길동테스트")
    r = client.get(f"/api/patients/{pid}/manual-history-summary")
    assert r.status_code == 200
    assert set(r.json().keys()) == _schemas.MANUAL_HISTORY_SUMMARY_KEYS


def test_patient_history_endpoint_envelope_keys(client):
    """``GET /patients/{pid}/history`` envelope 키 contract."""
    from tests.harness.seed_data import get_test_patient_id

    pid = get_test_patient_id("홍길동테스트")
    r = client.get(f"/api/patients/{pid}/history")
    assert r.status_code == 200
    assert set(r.json().keys()) == _schemas.PATIENT_HISTORY_ENVELOPE_KEYS


# ──────────────────────── 12. availability helper 무수정 (19-4 보존) ─────────


def test_availability_module_unchanged():
    """19-4 availability 의 핵심 helper 가 그대로 노출."""
    # 19-4 가 노출한 helper 가 그대로 import 가능.
    assert callable(_av.parse_lunch_window)
    assert callable(_av.overlaps_lunch_window)
    assert callable(_av.is_version_conflict)
    assert callable(_av.next_version)
    assert callable(_av.is_leave_blocking)
