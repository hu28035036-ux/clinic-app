"""예약문자 발송 전 검증 — LLM 미사용.

⚠ 이 모듈은 OpenAI / Anthropic 등 외부 LLM API 를 절대 호출하지 않는다.
  오직 DB 조회 + 문자열·인코딩 검증만 수행하는 결정론적 로직이다.

체크 항목:
  blocker  = 발송 차단
    - APPT_NOT_FOUND       : 예약 ID 가 DB 에 없음
    - NO_PHONE             : 전화번호 없음 / 형식 오류
    - NO_APPT_TIME         : 예약 시간 없음
    - NO_TREATMENT         : 치료항목 비어있음
    - EMPTY_BODY           : 본문 공백
    - CANCELLED_PATIENT    : 예약 상태가 canceled
    - UNRESOLVED_VAR       : {환자명} 처럼 미치환 변수가 본문에 남아있음
    - CP949_ENCODING_ERROR : 문자나라(CP949) 발송 시 깨질 문자 포함
  warning  = 사용자 확인 필요 (발송 자체는 가능)
    - NO_THERAPIST     : 담당 치료사 미배정
    - DUPLICATE_RECENT : 동일 본문이 같은 번호/환자에게 최근 N분 이내 발송 이력
"""
import json
import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ...models import models


BLOCKER_CODES = (
    "APPT_NOT_FOUND",
    "NO_PHONE",
    "NO_APPT_TIME",
    "NO_TREATMENT",
    "EMPTY_BODY",
    "CANCELLED_PATIENT",
    "UNRESOLVED_VAR",
    "CP949_ENCODING_ERROR",
)
WARNING_CODES = (
    "NO_THERAPIST",
    "DUPLICATE_RECENT",
)

DEFAULT_DUP_WINDOW_MIN = 10


def _phone_digits(raw) -> str:
    if not raw:
        return ""
    return re.sub(r"[^0-9]", "", str(raw))


def _is_valid_kr_phone(digits: str) -> bool:
    if not digits:
        return False
    if digits.startswith("010") and len(digits) == 11:
        return True
    if digits.startswith(("011", "016", "017", "018", "019")) and len(digits) in (10, 11):
        return True
    if digits.startswith("02") and len(digits) in (9, 10):
        return True
    if len(digits) in (10, 11) and digits[0] == "0":
        return True
    return False


def _cp949_bad_chars(text: str) -> list:
    if not text:
        return []
    seen = set()
    bad = []
    for ch in text:
        if ch in seen:
            continue
        try:
            ch.encode("cp949")
        except UnicodeEncodeError:
            seen.add(ch)
            bad.append(ch)
    return bad


_VAR_PATTERN = re.compile(r"\{[^{}\n]{1,40}\}")


def _unresolved_vars(text: str) -> list:
    if not text:
        return []
    return _VAR_PATTERN.findall(text)


def _parse_codes(codes_json) -> list:
    try:
        v = json.loads(codes_json or "[]")
        return v if isinstance(v, list) else []
    except Exception:
        return []


def _find_recent_duplicate(
    db: Session,
    *,
    phone: str,
    body: str,
    patient_id: Optional[str],
    window_minutes: int,
) -> Optional[datetime]:
    if not (body or "").strip():
        return None
    cutoff = datetime.utcnow() - timedelta(minutes=max(1, window_minutes))
    rows = (
        db.query(models.SmsLog)
        .filter(models.SmsLog.sent_at >= cutoff, models.SmsLog.body == body)
        .all()
    )
    digits = _phone_digits(phone)
    latest = None
    for log in rows:
        same_patient = bool(patient_id) and log.patient_id == patient_id
        same_phone = bool(digits) and _phone_digits(log.phone or "") == digits
        if not (same_patient or same_phone):
            continue
        if latest is None or (log.sent_at and log.sent_at > latest):
            latest = log.sent_at
    return latest


def _entry(code: str, message: str, **extra) -> dict:
    d = {"code": code, "message": message}
    if extra:
        d.update(extra)
    return d


def validate_sms_item(
    db: Session,
    *,
    appointment_id: Optional[str] = None,
    body: str = "",
    phone: Optional[str] = None,
    patient_id: Optional[str] = None,
    dup_window_minutes: int = DEFAULT_DUP_WINDOW_MIN,
) -> dict:
    """SMS 1건 검증.

    인자
      appointment_id : 있으면 DB 에서 예약·환자·치료사 로딩
      body           : SMS 본문
      phone          : 명시 번호 (없으면 환자 phone 사용)
      patient_id     : 명시 환자 ID (없으면 예약의 patient_id 사용)

    반환
      {
        "appointment_id": <echo>,
        "blockers": [{"code":..., "message":..., ...}, ...],
        "warnings": [{"code":..., "message":..., ...}, ...],
      }
    """
    blockers: list = []
    warnings: list = []

    appt = None
    patient = None
    therapist_id = None
    status = None
    treatment_codes: list = []
    start_at = None
    eff_patient_id = patient_id

    if appointment_id:
        appt = (
            db.query(models.Appointment)
            .filter(models.Appointment.id == str(appointment_id))
            .first()
        )
        if appt is None:
            blockers.append(_entry(
                "APPT_NOT_FOUND",
                f"예약을 찾을 수 없습니다 (id={appointment_id}).",
            ))
        else:
            patient = appt.patient
            therapist_id = appt.therapist_id
            status = appt.status
            treatment_codes = _parse_codes(appt.treatment_codes)
            start_at = appt.start_at
            if not eff_patient_id:
                eff_patient_id = appt.patient_id

    eff_phone = phone if phone is not None else (patient.phone if patient else None)
    digits = _phone_digits(eff_phone)

    # 1) NO_PHONE
    if not digits:
        blockers.append(_entry("NO_PHONE", "전화번호가 등록되어 있지 않습니다."))
    elif not _is_valid_kr_phone(digits):
        blockers.append(_entry(
            "NO_PHONE",
            "전화번호 형식이 올바르지 않습니다 (예: 010-1234-5678).",
            digits=digits,
        ))

    # 2) NO_APPT_TIME — 예약을 로딩한 경우에만 의미
    if appt is not None and start_at is None:
        blockers.append(_entry("NO_APPT_TIME", "예약 시간이 지정되지 않았습니다."))

    # 3) NO_TREATMENT
    if appt is not None and not treatment_codes:
        blockers.append(_entry("NO_TREATMENT", "치료항목이 지정되지 않았습니다."))

    # 4) NO_THERAPIST — warning
    if appt is not None and not therapist_id:
        warnings.append(_entry("NO_THERAPIST", "담당 치료사가 배정되지 않았습니다."))

    # 5) EMPTY_BODY
    if not (body or "").strip():
        blockers.append(_entry("EMPTY_BODY", "문자 본문이 비어 있습니다."))

    # 7) CANCELLED_PATIENT
    if status == "canceled":
        blockers.append(_entry(
            "CANCELLED_PATIENT",
            "취소된 예약입니다. 일반 예약 안내문자를 보낼 수 없습니다.",
        ))

    # 8) UNRESOLVED_VAR
    unresolved = _unresolved_vars(body or "")
    if unresolved:
        blockers.append(_entry(
            "UNRESOLVED_VAR",
            f"치환되지 않은 변수가 있습니다: {', '.join(unresolved)}",
            tokens=unresolved,
        ))

    # 9) CP949_ENCODING_ERROR
    bad = _cp949_bad_chars(body or "")
    if bad:
        sample = "".join(bad[:10])
        blockers.append(_entry(
            "CP949_ENCODING_ERROR",
            f"문자나라(CP949) 발송 시 깨질 수 있는 문자가 포함되어 있습니다: {sample}",
            chars=bad,
        ))

    # 6) DUPLICATE_RECENT — body 가 비어있지 않고 식별자(번호 또는 환자)가 있을 때만
    if (body or "").strip() and (digits or eff_patient_id):
        last_at = _find_recent_duplicate(
            db,
            phone=eff_phone or "",
            body=body or "",
            patient_id=eff_patient_id,
            window_minutes=dup_window_minutes,
        )
        if last_at is not None:
            warnings.append(_entry(
                "DUPLICATE_RECENT",
                f"동일한 문자가 최근 {dup_window_minutes}분 이내에 발송된 이력이 있습니다.",
                last_sent_at=last_at.isoformat(),
            ))

    return {
        "appointment_id": appointment_id,
        "blockers": blockers,
        "warnings": warnings,
    }


def validate_sms_batch(
    db: Session,
    items: list,
    *,
    dup_window_minutes: int = DEFAULT_DUP_WINDOW_MIN,
) -> list:
    out = []
    for it in items or []:
        out.append(validate_sms_item(
            db,
            appointment_id=it.get("appointment_id"),
            body=it.get("body", "") or "",
            phone=it.get("phone"),
            patient_id=it.get("patient_id"),
            dup_window_minutes=dup_window_minutes,
        ))
    return out
