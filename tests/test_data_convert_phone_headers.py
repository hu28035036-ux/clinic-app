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


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


def test_data_convert_preview_lists_overlapping_patients(client):
    """미리보기 겹침 내역 (v1.3.51+): 기존 DB 환자와 겹치는 엑셀 행은
    existing_patients 에 어떤 환자와 왜 겹쳤는지(matched_by)와 함께 내려온다."""
    import uuid

    headers = _admin_headers(client)
    suffix = uuid.uuid4().hex[:8]
    chart = f"DCOV{suffix}"
    name_chart = f"겹침차트환자{suffix}"
    name_key = f"겹침이름환자{suffix}"
    name_new = f"신규환자{suffix}"

    # 기존 환자 2명: 차트번호 매칭용 / 이름+생년월일 매칭용.
    r1 = client.post("/api/patients", json={
        "name": name_chart, "chart_no": chart, "birth_date": "1980-01-01"})
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/patients", json={
        "name": name_key, "birth_date": "1990-02-02"})
    assert r2.status_code == 200, r2.text

    # 엑셀: 차트 겹침 1행 + 이름+생일 겹침 1행 + 파일 내부 중복 1행 + 신규 1행.
    content = _workbook_bytes([
        ["환자명", "차트번호", "생년월일"],
        ["다른이름", chart, "1970-03-03"],          # 차트번호로 기존과 겹침
        [name_key, "", "1990-02-02"],               # 이름+생년월일로 겹침
        [name_key, "", "1990-02-02"],               # 파일 내부 중복
        [name_new, "", "2000-04-04"],               # 신규
    ])
    resp = client.post(
        "/api/data-convert/preview",
        files={"file": ("patients.xlsx", content,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["existing_count"] == 3          # DB 겹침 2 + 파일 내부 중복 1
    assert data["dup_in_file_count"] == 1
    assert data["new_count"] == 1
    assert data["new_patients"][0]["name"] == name_new

    ex = {x["matched_by"]: x for x in data["existing_patients"]}
    assert len(data["existing_patients"]) == 2
    assert ex["차트번호"]["chart_no"] == chart
    assert ex["차트번호"]["db_name"] == name_chart
    assert ex["차트번호"]["db_chart_no"] == chart
    assert ex["이름+생년월일"]["name"] == name_key
    assert ex["이름+생년월일"]["db_name"] == name_key
    assert ex["이름+생년월일"]["db_birth_date"] == "1990-02-02"
