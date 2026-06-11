from __future__ import annotations

import io

import openpyxl

from app.routers.api import _dc_parse_excel


def _workbook_bytes(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    bio = io.BytesIO()
    wb.save(bio)
    wb.close()
    return bio.getvalue()


def test_data_convert_uses_mobile_column_when_phone_column_is_landline():
    content = _workbook_bytes([
        ["환자번호", "환자명", "전화번호", "휴대폰"],
        ["1", "샘플환자", "02-1234-5678", "010-1234-5678"],
    ])

    entries, _errors, _header, _parse_info = _dc_parse_excel(content)

    assert entries[0]["phone"] == "010-1234-5678"
    assert entries[0]["landlines"] == ["02-1234-5678"]
    assert entries[0]["extra_phones"] == ["02-1234-5678"]


def test_data_convert_prefers_mobile_header_over_generic_phone_header():
    content = _workbook_bytes([
        ["환자번호", "환자명", "전화번호", "휴대폰"],
        ["1", "샘플환자", "010-1111-1111", "010-2222-2222"],
    ])

    entries, _errors, _header, _parse_info = _dc_parse_excel(content)

    assert entries[0]["phone"] == "010-2222-2222"
    assert entries[0]["extra_mobiles"] == ["010-1111-1111"]


def test_data_convert_recognizes_spaced_mobile_phone_header():
    content = _workbook_bytes([
        ["환자명", "전화 번호", "휴대폰 번호"],
        ["샘플환자", "02-1234-5678", "010-3333-4444"],
    ])

    entries, _errors, _header, _parse_info = _dc_parse_excel(content)

    assert entries[0]["phone"] == "010-3333-4444"
    assert entries[0]["extra_phones"] == ["02-1234-5678"]
