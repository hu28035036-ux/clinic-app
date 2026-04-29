"""치료항목 관련 상수 (역할 등 불변값) + 시드 데이터.

이전 버전: 치료항목 5개 하드코딩
현재 버전: 치료항목은 DB(Treatment 테이블)에서 관리.
이 파일은 시드 기본값 + 역할 상수만 보유.
"""

# 직원 역할
ROLE_DOCTOR = "doctor"
ROLE_THERAPIST = "therapist"
ROLES = [ROLE_DOCTOR, ROLE_THERAPIST]

# 시드 치료항목 (첫 실행 시 자동 등록)
SEED_TREATMENTS = [
    # code, name, short, default_minutes, role, count_increment, show_in_patient
    ("injection", "주사",         "주",     10, "doctor",    1, True),
    ("cartilage", "연골주사",      "연골",   10, "doctor",    1, True),
    ("eswt",      "체외충격파",    "충",     10, "therapist", 1, True),
    ("manual30",  "도수치료30분",  "도수6",  30, "therapist", 1, True),
    ("manual60",  "도수치료60분",  "도수12", 60, "therapist", 1, True),
]

# 체외충격파 코드 (공용 열 분기 — 하드코딩 예외)
ESWT_CODE = "eswt"
