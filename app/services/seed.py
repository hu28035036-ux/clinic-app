"""초기 시드 (단계 A: 치료항목 동적화).

- Treatment 테이블에 기본 5개 시드 자동 등록
- SystemSetting 단일 행 보장
- SmsSetting 단일 행 보장
- SmsTemplate 기본 1개 시드 (단계 F)
"""
from datetime import datetime, timedelta
import json
from ..models.models import (SystemSetting, SmsSetting, Treatment, SmsTemplate,
                              Employee, Patient, Appointment)
from ..modules.treatments.defaults import load_default_treatments


def seed_defaults(db):
    """앱 시작 시 호출 — 멱등."""
    _seed_employee_categories(db)
    _seed_treatments(db)
    _seed_system_setting(db)
    _seed_sms_setting(db)
    _seed_sms_template(db)
# _seed_demo_data(db)  # 배포용: 샘플 환자/직원/예약 자동 생성 차단

# Employee categories are intentionally not seeded. Clinics create their own
# departments from the employee management screen.
DEFAULT_EMPLOYEE_CATEGORIES = ()


def _seed_employee_categories(db):
    for item in DEFAULT_EMPLOYEE_CATEGORIES:
        exists = db.query(EmployeeCategory).filter_by(name=item["name"]).first()
        if exists:
            continue
        db.add(EmployeeCategory(active=True, **item))


def _seed_treatments(db):
    """치료항목 기본 JSON 기준으로 누락 항목만 자동 등록."""
    for idx, item in enumerate(load_default_treatments()):
        code = item["code"]
        exists = db.query(Treatment).filter_by(code=code).first()
        if exists:
            continue
        db.add(Treatment(
            code=code,
            name=item["name"],
            short=item["short"],
            category_id=None,
            default_minutes=item["default_minutes"],
            role=item["role"],
            count_increment=item["count_increment"],
            show_in_patient=item["show_in_patient"],
            active=item["active"],
            sort_order=item.get("sort_order") or (idx + 1),
        ))


def _seed_system_setting(db):
    ss = db.query(SystemSetting).first()
    if not ss:
        ss = SystemSetting(
            id=1,
            manual_slot_limit=None,
            sms_template=_default_sms_template(),
            auto_backup_enabled=True,
            auto_backup_interval_min=60,
            auto_backup_keep_count=30,
        )
        db.add(ss)


def _seed_sms_setting(db):
    sms = db.query(SmsSetting).first()
    if not sms:
        sms = SmsSetting(id=1)
        db.add(sms)


def _seed_sms_template(db):
    """단계 F #15: 기본 템플릿 1개 자동 시드."""
    if db.query(SmsTemplate).count() == 0:
        db.add(SmsTemplate(
            name="기본 안내",
            body=_default_sms_template(),
            sort_order=1,
            active=True,
        ))


def _default_sms_template() -> str:
    return (
        "{환자명}님, {병원명}입니다.\n"
        "다음 예약 안내드립니다.\n"
        "일시: {다음예약날짜} {다음예약시간}\n"
        "항목: {다음예약항목}\n"
        "문의: {병원전화}"
    )


# 하위 호환
def seed_treatments(db):
    _seed_treatments(db)

def _seed_demo_data(db):
    """테스트용 기본 데이터 — 환자/직원/예약이 하나도 없을 때만 실행 (중복 방지)."""

    # 이미 환자나 직원 데이터가 있으면 아무것도 하지 않음
    if db.query(Patient).count() > 0:
        return
    if db.query(Employee).count() > 0:
        return

    # ── 1. 의사 등록 ──────────────────────────────────────────
    doctors = [
        Employee(name="김태훈", role="doctor",    color="#3B82F6", active=True,
                 phone="010-1000-2000"),
        Employee(name="이수진", role="doctor",    color="#8B5CF6", active=True,
                 phone="010-1001-2001"),
    ]
    for e in doctors:
        db.add(e)

    # ── 2. 치료사 등록 ─────────────────────────────────────────
    therapists = [
        Employee(name="박성민", role="therapist", color="#10B981", active=True,
                 phone="010-2000-3000"),
        Employee(name="최지영", role="therapist", color="#F59E0B", active=True,
                 phone="010-2001-3001"),
        Employee(name="정현우", role="therapist", color="#EF4444", active=True,
                 phone="010-2002-3002"),
    ]
    for e in therapists:
        db.add(e)

    db.flush()  # id 확정

    # ── 3. 환자 등록 ──────────────────────────────────────────
    patients = [
        Patient(name="김민수", birth_date="1985-03-12", phone="010-3100-0001",
                chart_no="P001", memo=""),
        Patient(name="이서연", birth_date="1991-07-22", phone="010-3100-0002",
                chart_no="P002", memo=""),
        Patient(name="박지훈", birth_date="1978-11-05", phone="010-3100-0003",
                chart_no="P003", memo=""),
        Patient(name="최유진", birth_date="1995-02-18", phone="010-3100-0004",
                chart_no="P004", memo=""),
        Patient(name="정다은", birth_date="1983-09-30", phone="010-3100-0005",
                chart_no="P005", memo=""),
        Patient(name="강준호", birth_date="1969-05-14", phone="010-3100-0006",
                chart_no="P006", memo=""),
        Patient(name="윤소희", birth_date="1999-12-01", phone="010-3100-0007",
                chart_no="P007", memo=""),
        Patient(name="임재원", birth_date="1973-04-25", phone="010-3100-0008",
                chart_no="P008", memo=""),
        Patient(name="한미래", birth_date="1988-08-08", phone="010-3100-0009",
                chart_no="P009", memo=""),
        Patient(name="오현준", birth_date="1962-01-17", phone="010-3100-0010",
                chart_no="P010", memo=""),
        Patient(name="신지수", birth_date="1993-06-20", phone="010-3100-0011",
                chart_no="P011", memo=""),
        Patient(name="권태양", birth_date="1980-10-09", phone="010-3100-0012",
                chart_no="P012", memo=""),
    ]
    for p in patients:
        db.add(p)

    db.flush()  # id 확정

    # ── 4. 예약 등록 ──────────────────────────────────────────
    today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

    def _a(pat_i, th_i, day_offset, hour, minute, dur, codes, status):
        """예약 1건 생성 헬퍼."""
        start = (today + timedelta(days=day_offset)).replace(
            hour=hour, minute=minute, second=0, microsecond=0)
        end = start + timedelta(minutes=dur)
        return Appointment(
            patient_id=patients[pat_i].id,
            therapist_id=therapists[th_i].id,
            start_at=start,
            end_at=end,
            duration_min=dur,
            treatment_codes=json.dumps(codes),
            status=status,
        )

    # pat_i(0~11), th_i(0~2), 날짜오프셋, 시, 분, 소요분, 치료코드, 상태
    # 상태: "approved"=완료, "canceled"=취소, "reserved"=예약
    appts = [
        # ── 2주 전 ───────────────────────────────────────────
        _a( 0, 0, -14,  9,  0, 30, ["manual30"],         "approved"),
        _a( 1, 1, -14, 14,  0, 30, ["eswt"],             "approved"),
        _a( 2, 2, -13, 10,  0, 60, ["manual60"],         "approved"),
        _a( 3, 0, -13, 15,  0, 10, ["injection"],        "canceled"),
        _a( 4, 1, -12,  9,  0, 30, ["manual30"],         "approved"),
        _a( 5, 2, -12, 14, 30, 30, ["manual30", "eswt"], "approved"),
        _a( 6, 0, -11, 10, 30, 30, ["manual30"],         "canceled"),
        _a( 7, 1, -11, 16,  0, 30, ["eswt"],             "approved"),
        # ── 1주 전 ───────────────────────────────────────────
        _a( 8, 2, -10,  9,  0, 60, ["manual60"],         "approved"),
        _a( 9, 0, -10, 11,  0, 10, ["cartilage"],        "approved"),
        _a(10, 1,  -9, 14,  0, 30, ["manual30"],         "approved"),
        _a(11, 2,  -9, 15, 30, 30, ["eswt"],             "canceled"),
        _a( 0, 0,  -8,  9, 30, 30, ["manual30"],         "approved"),
        _a( 1, 1,  -8, 13,  0, 60, ["manual60"],         "approved"),
        _a( 2, 2,  -7, 10,  0, 30, ["manual30"],         "approved"),
        _a( 3, 0,  -6,  9,  0, 10, ["injection"],        "approved"),
        _a( 4, 1,  -5, 14,  0, 30, ["manual30"],         "approved"),
        _a( 5, 2,  -4, 15,  0, 30, ["eswt"],             "canceled"),
        _a( 6, 0,  -3, 10,  0, 30, ["manual30"],         "approved"),
        _a( 7, 1,  -2,  9,  0, 60, ["manual60"],         "approved"),
        _a( 8, 2,  -1, 14,  0, 30, ["manual30"],         "approved"),
        # ── 오늘 ─────────────────────────────────────────────
        _a( 9, 0,   0,  9,  0, 30, ["manual30"],         "reserved"),
        _a(10, 1,   0, 10, 30, 30, ["eswt"],             "reserved"),
        _a(11, 2,   0, 14,  0, 30, ["manual30"],         "reserved"),
        # ── 이후 ─────────────────────────────────────────────
        _a( 0, 0,   1, 11,  0, 60, ["manual60"],         "reserved"),
        _a( 1, 1,   2, 14, 30, 10, ["cartilage"],        "reserved"),
        _a( 2, 2,   3, 15,  0, 30, ["manual30"],         "reserved"),
        _a( 3, 0,   5, 10,  0, 30, ["eswt"],             "reserved"),
        _a( 4, 1,   7,  9,  0, 30, ["manual30"],         "reserved"),
    ]
    for a in appts:
        db.add(a)
