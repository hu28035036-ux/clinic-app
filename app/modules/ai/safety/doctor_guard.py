"""F-15 — 의사 정보 임의 생성 차단 (post-19-P / 20-1 그룹 A).

# SAFETY: 도메인 부재 항목 (Doctor / Department / Room / DoctorSchedule) 을
# AI 응답이 *DB 근거 없이* 생성하는 것을 차단.
# 19_refactor_rollout_plan §9 F-15 / M-36 정합. F-1 (doctors 도입) 이전에는
# 의사 정보 자체가 부재 — 의사 단정 표현은 모두 hallucination.

# NOTE: 차단 패턴 3분류 (사용자 §4-A 권장값 정합):
#   (a) 의사 단정 표현 — "담당의는 X" / "Y 의사가 ~"
#   (b) 의사 일정 단정 — "Y 의사는 화요일 ~" / "X 의사 진료 시간 ~"
#   (c) 의사 진단 단정 — "X 의사가 진단 ~" / "Y 의사가 처방 ~"
"""
from __future__ import annotations

import re

# (a) 의사 단정 표현
_RE_DOCTOR_NAME_CLAIM = re.compile(
    r"(담당\s*의[는은]\s*\S+|"
    r"\S+\s*의사(?:[는은]|가|님)\s*(?:진료|담당|시술|치료|처방|진단)|"
    r"\S+\s*원장(?:[는은]|이|님)\s*(?:진료|담당)|"
    r"진료(?:과|실)[는은]?\s*\S+\s*입니다|"
    r"\S+\s*과\s*담당\s*의)"
)

# (b) 의사 일정 단정
_RE_DOCTOR_SCHEDULE_CLAIM = re.compile(
    r"(\S+\s*의사(?:[는은]|가)\s*(?:월|화|수|목|금|토|일)요일|"
    r"\S+\s*원장(?:[는은]|이)\s*(?:월|화|수|목|금|토|일)요일|"
    r"\S+\s*의사\s*진료\s*(?:시간|일정)|"
    r"진료\s*시간\s*[은는]\s*\d{1,2}\s*[:시])"
)

# (c) 의사 진단 단정
_RE_DOCTOR_DIAGNOSIS_CLAIM = re.compile(
    r"(\S+\s*의사(?:[는은]|가)\s*진단했|"
    r"\S+\s*의사(?:[는은]|가)\s*처방했|"
    r"\S+\s*원장(?:[는은]|이)\s*진단했|"
    r"\S+\s*원장(?:[는은]|이)\s*처방했)"
)

DOCTOR_GUARD_REASON_NAME = "doctor_name_claim_blocked"
DOCTOR_GUARD_REASON_SCHEDULE = "doctor_schedule_claim_blocked"
DOCTOR_GUARD_REASON_DIAGNOSIS = "doctor_diagnosis_claim_blocked"


def has_doctor_claim(text: str) -> tuple[bool, str]:
    """텍스트에 의사 정보 단정 표현이 있는지 검사.

    반환: ``(blocked, reason)``. blocked=False 면 reason="".
    """
    if not text:
        return False, ""
    if _RE_DOCTOR_DIAGNOSIS_CLAIM.search(text):
        return True, DOCTOR_GUARD_REASON_DIAGNOSIS
    if _RE_DOCTOR_SCHEDULE_CLAIM.search(text):
        return True, DOCTOR_GUARD_REASON_SCHEDULE
    if _RE_DOCTOR_NAME_CLAIM.search(text):
        return True, DOCTOR_GUARD_REASON_NAME
    return False, ""


def block_doctor_claims(text: str) -> dict:
    """의사 정보 단정 차단 결과 dict.

    기존 ``app/services/ai/rag/pipeline.py:validate_answer`` 와 같은 형식 —
    호출지에서 동일한 ``{"blocked", "reason", "guard_hits"}`` 키로 합칠 수 있음.

    반환:
      ``{"blocked": bool, "reason": str, "guard_hits": int}``
    """
    blocked, reason = has_doctor_claim(text)
    return {
        "blocked": blocked,
        "reason": reason,
        "guard_hits": 1 if blocked else 0,
    }
