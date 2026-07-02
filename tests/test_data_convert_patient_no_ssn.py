from __future__ import annotations

import io

import openpyxl

from app.routers.api import (
    _dc_birth_from_ssn,
    _dc_is_duplicate_in_db,
    _dc_parse_excel,
)


def _workbook_bytes(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    bio = io.BytesIO()
    wb.save(bio)
    wb.close()
    return bio.getvalue()


def test_patient_no_header_is_recognized_as_chart_no():
    """'환자번호' 컬럼이 차트번호로 인식된다 (실파일 헤더 기준)."""
    content = _workbook_bytes([
        ["환자번호", "환자명", "주민번호", "성별", "휴대폰"],
        ["7", "홍길동", "9001011234567", "M", "010-1111-2222"],
    ])

    entries, _errors, _header, _info = _dc_parse_excel(content)

    assert entries[0]["chart_no"] == "7"


def test_birth_date_derived_from_ssn_first_six_digits():
    """생년월일 컬럼이 없으면 주민번호 앞 6자리 + 세기코드로 채운다."""
    content = _workbook_bytes([
        ["환자번호", "환자명", "주민번호"],
        ["1", "이천년", "0001063696212"],   # 7번째 '3' → 2000년대
        ["2", "구공년", "9108181831013"],   # 7번째 '1' → 1900년대
    ])

    entries, _errors, _header, _info = _dc_parse_excel(content)

    assert entries[0]["birth_date"] == "2000-01-06"
    assert entries[1]["birth_date"] == "1991-08-18"


def test_explicit_birth_column_takes_priority_over_ssn():
    """생년월일 컬럼이 있으면 그 값을 쓰고 주민번호로 덮어쓰지 않는다."""
    content = _workbook_bytes([
        ["환자번호", "환자명", "생년월일", "주민번호"],
        ["1", "홍길동", "1990-03-15", "0001011234567"],
    ])

    entries, _errors, _header, _info = _dc_parse_excel(content)

    assert entries[0]["birth_date"] == "1990-03-15"


def test_birth_from_ssn_century_rules():
    assert _dc_birth_from_ssn("9001011234567") == "1990-01-01"  # 1,2 → 1900년대
    assert _dc_birth_from_ssn("0512313234567") == "2005-12-31"  # 3,4 → 2000년대
    assert _dc_birth_from_ssn("450101-9123456") == "1845-01-01"  # 9,0 → 1800년대, '-' 무관
    assert _dc_birth_from_ssn("991301") is None                  # 잘못된 월 → None
    assert _dc_birth_from_ssn("") is None
    assert _dc_birth_from_ssn(None) is None


def test_duplicate_by_chart_no():
    e = {"name": "홍길동", "chart_no": "7", "birth_date": "1990-01-01"}
    assert _dc_is_duplicate_in_db(e, {"7"}, set()) is True
    assert _dc_is_duplicate_in_db(e, {"8"}, set()) is False


def test_duplicate_by_name_and_birth_without_chart():
    e = {"name": "홍길동", "chart_no": None, "birth_date": "1990-01-01"}
    key_set = {("홍길동", "1990-01-01")}
    assert _dc_is_duplicate_in_db(e, set(), key_set) is True
    # 같은 이름·다른 생일은 중복 아님 (동명이인 보호)
    other = {"name": "홍길동", "chart_no": None, "birth_date": "1985-05-05"}
    assert _dc_is_duplicate_in_db(other, set(), key_set) is False
