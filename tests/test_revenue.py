from __future__ import annotations

import io
import uuid

import openpyxl


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _admin_headers(client) -> dict:
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    assert resp.status_code == 200, resp.text
    return {"X-Admin-Token": resp.json()["token"]}


def _make_category(client, prefix: str = "revenue-cat") -> dict:
    resp = client.post("/api/employee-categories", json={
        "name": _unique(prefix),
        "color": "#0EA5E9",
        "active": True,
        "sort_order": 75,
        "default_can_doctor_treatment": False,
        "default_can_manual": True,
        "default_can_eswt": False,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_treatment(client, headers: dict, category_id: str, *, short: str, price: int) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post("/api/treatments", json={
        "name": f"revenue-treatment-{suffix}",
        "short": f"{short}{suffix[:4]}",
        "category_id": category_id,
        "default_minutes": 30,
        "role": "therapist",
        "count_increment": 1,
        "show_in_patient": False,
        "active": True,
        "sort_order": 10,
        "code": f"revenue_{suffix}",
        "price": price,
        "incentive_pct": None,
        "incentive_amount": 0,
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _make_employee(client, category_id: str, treatment_ids: list[str]) -> dict:
    resp = client.post("/api/employees", json={
        "name": _unique("revenue-employee"),
        "category_id": category_id,
        "color": "#10B981",
        "active": True,
        "treatment_override_enabled": True,
        "treatment_ids": treatment_ids,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_revenue_records_grid_stats_and_delete(client):
    headers = _admin_headers(client)
    category = _make_category(client)
    payload = {
        "date_from": "2099-09-01",
        "date_to": "2099-09-02",
        "category_id": category["id"],
        "entries": [
            {
                "record_date": "2099-09-01",
                "category_id": category["id"],
                "cash_amount": 1000,
                "card_amount": 2000,
                "transfer_amount": 3000,
                "other_amount": 4000,
                "memo": "첫 매출",
            },
            {
                "record_date": "2099-09-02",
                "category_id": category["id"],
                "cash_amount": 0,
                "card_amount": 0,
                "transfer_amount": 0,
                "other_amount": 0,
                "memo": "",
            },
        ],
    }

    saved = client.post("/api/revenue/records/grid", json=payload, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["changed"] == {"upserted": 1, "deleted": 0}

    listed = client.get(
        f"/api/revenue/records?date_from=2099-09-01&date_to=2099-09-02&category_id={category['id']}",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    records = listed.json()["records"]
    assert [r["record_date"] for r in records] == ["2099-09-01", "2099-09-02"]
    assert records[0]["total_amount"] == 10000
    assert records[0]["memo"] == "첫 매출"
    assert records[1]["total_amount"] == 0

    stats = client.get(
        f"/api/revenue/stats?date_from=2099-09-01&date_to=2099-09-02&category_id={category['id']}",
        headers=headers,
    )
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert body["current"]["revenue_total"] == 10000
    assert body["current"]["record_count"] == 1
    assert body["previous"]["revenue_total"] == 0
    assert body["delta"]["revenue_total"] == {"amount": 10000, "pct": None}
    by_payment = {row["key"]: row["amount"] for row in body["current"]["by_payment"]}
    assert by_payment == {
        "cash_amount": 1000,
        "card_amount": 2000,
        "transfer_amount": 3000,
        "unpaid_amount": 0,
        "health_living_fee": 0,
        "disability_fund": 0,
        "other_amount": 4000,
    }
    assert body["settlement"]["price_total"] == 0
    assert body["settlement"]["revenue_minus_settlement_price"] == 10000
    assert body["settlement"]["revenue_after_incentive"] == 10000

    payload["entries"][0].update({
        "cash_amount": 0,
        "card_amount": 0,
        "transfer_amount": 0,
        "unpaid_amount": 0,
        "other_amount": 0,
        "memo": "",
    })
    deleted = client.post("/api/revenue/records/grid", json=payload, headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["changed"] == {"upserted": 0, "deleted": 1}

    after_delete = client.get(
        f"/api/revenue/stats?date_from=2099-09-01&date_to=2099-09-02&category_id={category['id']}",
        headers=headers,
    )
    assert after_delete.status_code == 200, after_delete.text
    assert after_delete.json()["current"]["revenue_total"] == 0


def test_revenue_records_allow_unpaid_and_negative_amounts(client):
    headers = _admin_headers(client)
    category = _make_category(client, "revenue-signed-cat")
    payload = {
        "date_from": "2099-09-04",
        "date_to": "2099-09-05",
        "category_id": category["id"],
        "entries": [
            {
                "record_date": "2099-09-04",
                "category_id": category["id"],
                "cash_amount": 10000,
                "card_amount": -2000,
                "transfer_amount": 3000,
                "unpaid_amount": -5000,
                "health_living_fee": -700,
                "disability_fund": -300,
                "other_amount": -1000,
                "memo": "음수 포함",
            },
            {
                "record_date": "2099-09-05",
                "category_id": category["id"],
                "cash_amount": 1000,
                "card_amount": -1000,
                "transfer_amount": 0,
                "unpaid_amount": 0,
                "other_amount": 0,
                "memo": "",
            },
        ],
    }
    saved = client.post("/api/revenue/records/grid", json=payload, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["changed"] == {"upserted": 2, "deleted": 0}

    listed = client.get(
        f"/api/revenue/records?date_from=2099-09-04&date_to=2099-09-05&category_id={category['id']}",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    first, second = listed.json()["records"]
    assert first["total_amount"] == 4000
    assert first["card_amount"] == -2000
    assert first["unpaid_amount"] == -5000
    assert first["unpaid_applied_amount"] == -5000
    assert first["health_living_fee"] == -700
    assert first["disability_fund"] == -300
    assert first["other_amount"] == -1000
    assert second["total_amount"] == 0
    assert second["cash_amount"] == 1000
    assert second["card_amount"] == -1000

    stats = client.get(
        f"/api/revenue/stats?date_from=2099-09-04&date_to=2099-09-05&category_id={category['id']}",
        headers=headers,
    )
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert body["current"]["revenue_total"] == 4000
    by_payment = {row["key"]: row["amount"] for row in body["current"]["by_payment"]}
    assert by_payment["cash_amount"] == 11000
    assert by_payment["card_amount"] == -3000
    assert by_payment["transfer_amount"] == 3000
    assert by_payment["unpaid_amount"] == -5000
    assert by_payment["health_living_fee"] == -700
    assert by_payment["disability_fund"] == -300
    assert by_payment["other_amount"] == -1000


def test_revenue_cash_counts_calculate_cash_amount(client):
    headers = _admin_headers(client)
    category = _make_category(client, "revenue-cash-count-cat")
    cash_counts = {
        "50000": 1,
        "10000": 2,
        "5000": 1,
        "1000": 3,
        "500": 4,
        "100": 5,
        "10": 6,
    }
    saved = client.post("/api/revenue/records/grid", json={
        "date_from": "2099-09-03",
        "date_to": "2099-09-03",
        "category_id": category["id"],
        "entries": [{
            "record_date": "2099-09-03",
            "category_id": category["id"],
            "cash_amount": 123,
            "cash_counts": cash_counts,
            "card_amount": 940,
            "transfer_amount": 0,
            "other_amount": 0,
            "memo": "현금 단위별 입력",
        }],
    }, headers=headers)
    assert saved.status_code == 200, saved.text

    listed = client.get(
        f"/api/revenue/records?date_from=2099-09-03&date_to=2099-09-03&category_id={category['id']}",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    record = listed.json()["records"][0]
    assert record["cash_amount"] == 80560
    assert record["cash_counts"] == cash_counts
    assert record["total_amount"] == 81500


def test_revenue_stats_settlement_by_treatment(client):
    headers = _admin_headers(client)
    category = _make_category(client, "revenue-settle-cat")
    treatment_a = _make_treatment(client, headers, category["id"], short="RA", price=50000)
    treatment_b = _make_treatment(client, headers, category["id"], short="RB", price=70000)
    employee = _make_employee(client, category["id"], [treatment_a["id"], treatment_b["id"]])

    saved = client.post("/api/settlement/records/grid", json={
        "date_from": "2099-09-10",
        "date_to": "2099-09-10",
        "category_id": category["id"],
        "entries": [
            {
                "performed_on": "2099-09-10",
                "employee_id": employee["id"],
                "treatment_id": treatment_a["id"],
                "quantity": 2,
            },
            {
                "performed_on": "2099-09-10",
                "employee_id": employee["id"],
                "treatment_id": treatment_b["id"],
                "quantity": 1,
            },
        ],
    }, headers=headers)
    assert saved.status_code == 200, saved.text

    stats = client.get(
        f"/api/revenue/stats?date_from=2099-09-10&date_to=2099-09-10&category_id={category['id']}",
        headers=headers,
    )
    assert stats.status_code == 200, stats.text
    by_treatment = {
        row["treatment_id"]: row
        for row in stats.json()["settlement"]["by_treatment"]
    }
    assert by_treatment[treatment_a["id"]]["quantity_total"] == 2
    assert by_treatment[treatment_a["id"]]["price_total"] == 100000
    assert by_treatment[treatment_b["id"]]["quantity_total"] == 1
    assert by_treatment[treatment_b["id"]]["price_total"] == 70000


def test_revenue_writes_require_admin(client):
    resp = client.post("/api/revenue/records/grid", json={
        "date_from": "2099-09-01",
        "date_to": "2099-09-01",
        "entries": [],
    })
    assert resp.status_code == 401


def test_daily_work_report_save_get_auto_summary_and_delete(client):
    headers = _admin_headers(client)
    category = _make_category(client, "daily-report-cat")
    treatment_a = _make_treatment(client, headers, category["id"], short="DRA", price=50000)
    treatment_b = _make_treatment(client, headers, category["id"], short="DRB", price=70000)
    employee = _make_employee(client, category["id"], [treatment_a["id"], treatment_b["id"]])

    saved_revenue = client.post("/api/revenue/records/grid", json={
        "date_from": "2099-10-01",
        "date_to": "2099-10-01",
        "category_id": "",
        "entries": [
            {
                "record_date": "2099-10-01",
                "cash_amount": 1000,
                "card_amount": 2000,
                "transfer_amount": 3000,
                "unpaid_amount": -500,
                "health_living_fee": -120,
                "disability_fund": -30,
                "other_amount": 4000,
                "memo": "일일 보고 매출",
            },
        ],
    }, headers=headers)
    assert saved_revenue.status_code == 200, saved_revenue.text

    saved_settlement = client.post("/api/settlement/records/grid", json={
        "date_from": "2099-10-01",
        "date_to": "2099-10-01",
        "category_id": category["id"],
        "entries": [
            {
                "performed_on": "2099-10-01",
                "employee_id": employee["id"],
                "treatment_id": treatment_a["id"],
                "quantity": 2,
            },
            {
                "performed_on": "2099-10-01",
                "employee_id": employee["id"],
                "treatment_id": treatment_b["id"],
                "quantity": 1,
            },
        ],
    }, headers=headers)
    assert saved_settlement.status_code == 200, saved_settlement.text

    initial = client.get("/api/revenue/daily-report?date=2099-10-01", headers=headers)
    assert initial.status_code == 200, initial.text
    initial_body = initial.json()
    assert initial_body["exists"] is False
    assert initial_body["revenue_record"]["exists"] is True
    assert initial_body["revenue_record"]["category_id"] == ""
    assert initial_body["revenue_record"]["category_name"] == "전체"
    assert initial_body["revenue_record"]["total_amount"] == 9350
    assert initial_body["revenue_record"]["cash_amount"] == 1000
    assert initial_body["revenue_record"]["card_amount"] == 2000
    assert initial_body["revenue_record"]["transfer_amount"] == 3000
    assert initial_body["revenue_record"]["unpaid_amount"] == -500
    assert initial_body["revenue_record"]["unpaid_applied_amount"] == -500
    assert initial_body["revenue_record"]["health_living_fee"] == -120
    assert initial_body["revenue_record"]["disability_fund"] == -30
    assert initial_body["revenue_record"]["other_amount"] == 4000
    assert initial_body["revenue_record"]["memo"] == "일일 보고 매출"
    journal_lines = {row["key"]: row for row in initial_body["journal"]["revenue_lines"]}
    assert journal_lines["total_amount"]["amount"] == 9350
    assert journal_lines["unpaid_amount"]["amount"] == -500
    assert journal_lines["health_living_fee"]["amount"] == -120
    assert journal_lines["disability_fund"]["amount"] == -30
    assert "cash_ledger_total" not in journal_lines
    assert initial_body["journal"]["totals"]["quantity_total"] == 3
    assert initial_body["journal"]["totals"]["price_total"] == 170000
    assert set(initial_body["selected_treatment_codes"]) == {treatment_a["code"], treatment_b["code"]}
    assert initial_body["auto"]["totals"]["quantity_total"] == 3
    assert initial_body["auto"]["totals"]["price_total"] == 170000
    assert initial_body["auto"]["totals"]["net_total"] == 170000

    payload = {
        "report_date": "2099-10-01",
        "selected_treatment_codes": [treatment_a["code"]],
        "custom_fields": [
            {"id": "summary", "label": "요약", "type": "short_text", "value": "정상 운영"},
            {"id": "issue", "label": "특이사항", "type": "long_text", "value": "오전 집중"},
            {"id": "count", "label": "추가 건수", "type": "number", "value": 5},
            {"id": "done", "label": "마감 확인", "type": "checkbox", "value": True},
        ],
    }
    saved = client.post("/api/revenue/daily-report", json=payload, headers=headers)
    assert saved.status_code == 200, saved.text
    saved_body = saved.json()
    assert saved_body["changed"] == {"upserted": 1, "deleted": 0}
    assert saved_body["exists"] is True
    assert saved_body["revenue_record"]["total_amount"] == 9350
    assert saved_body["selected_treatment_codes"] == [treatment_a["code"]]
    assert saved_body["auto"]["totals"]["quantity_total"] == 2
    assert saved_body["auto"]["totals"]["price_total"] == 100000
    fields = {row["id"]: row for row in saved_body["custom_fields"]}
    assert fields["summary"]["value"] == "정상 운영"
    assert fields["count"]["value"] == 5
    assert fields["done"]["value"] is True

    fetched = client.get("/api/revenue/daily-report?date=2099-10-01", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["custom_fields"] == saved_body["custom_fields"]

    deleted = client.post("/api/revenue/daily-report", json={
        "report_date": "2099-10-01",
        "selected_treatment_codes": [],
        "custom_fields": [],
    }, headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["changed"] == {"upserted": 0, "deleted": 1}
    after_delete = client.get("/api/revenue/daily-report?date=2099-10-01", headers=headers)
    assert after_delete.status_code == 200, after_delete.text
    assert after_delete.json()["exists"] is False
    assert after_delete.json()["revenue_record"]["exists"] is True
    assert after_delete.json()["revenue_record"]["total_amount"] == 9350

    revenue_after_delete = client.get(
        "/api/revenue/records?date_from=2099-10-01&date_to=2099-10-01",
        headers=headers,
    )
    assert revenue_after_delete.status_code == 200, revenue_after_delete.text
    assert revenue_after_delete.json()["records"][0]["total_amount"] == 9350

    no_revenue = client.get("/api/revenue/daily-report?date=2099-10-03", headers=headers)
    assert no_revenue.status_code == 200, no_revenue.text
    no_revenue_record = no_revenue.json()["revenue_record"]
    assert no_revenue_record["exists"] is False
    assert no_revenue_record["total_amount"] == 0
    assert no_revenue_record["memo"] == ""


def test_daily_medical_summary_excel_import_reflects_daily_report(client):
    headers = _admin_headers(client)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([
        "날짜",
        "인원합계",
        "총진료비",
        "공단부담총액",
        "본인부담총액",
        "급여총액",
        "비급여총액",
        "검진청구예정액",
        "수납(현금)",
        "수납(카드)",
        "미수",
    ])
    ws.append([
        "2099/11/01",
        "41",
        "100,000원",
        "40,000",
        "60,000",
        "80,000",
        "20,000",
        0,
        53700,
        1264970,
        0,
    ])
    ws.append(["2099/11/02", "3", 200000, 70000, 130000, 150000, 50000, 0, 0, 0, 0])
    ws.append(["2099-11-02", "1", 1000, 200, 800, 900, 100, 0, 0, 0, 0])
    ws.append([
        None,
        45,
        301000,
        110200,
        190800,
        230900,
        70100,
        0,
        53700,
        1264970,
        0,
    ])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    imported = client.post(
        "/api/revenue/daily-medical-summary/import",
        files={
            "file": (
                "period-data.xlsx",
                bio.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=headers,
    )
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["ok"] is True
    assert body["changed"] == {"upserted": 2}
    assert body["imported"] == 2
    assert body["skipped"] == 0
    assert body["date_from"] == "2099-11-01"
    assert body["date_to"] == "2099-11-02"

    first = client.get("/api/revenue/daily-report?date=2099-11-01", headers=headers)
    assert first.status_code == 200, first.text
    first_summary = first.json()["medical_summary"]
    assert first_summary["exists"] is True
    assert first_summary["total_medical_fee"] == 100000
    assert first_summary["nhis_burden_total"] == 40000
    assert first_summary["patient_burden_total"] == 60000
    assert first_summary["covered_total"] == 80000
    assert first_summary["uncovered_total"] == 20000
    assert first_summary["source_filename"] == "period-data.xlsx"
    medical_lines = {row["key"]: row for row in first.json()["journal"]["medical_lines"]}
    assert medical_lines["total_medical_fee"]["label"] == "총진료비"
    assert medical_lines["total_medical_fee"]["amount"] == 100000
    assert medical_lines["uncovered_total"]["amount"] == 20000

    second = client.get("/api/revenue/daily-report?date=2099-11-02", headers=headers)
    assert second.status_code == 200, second.text
    second_summary = second.json()["medical_summary"]
    assert second_summary["total_medical_fee"] == 201000
    assert second_summary["nhis_burden_total"] == 70200
    assert second_summary["patient_burden_total"] == 130800
    assert second_summary["covered_total"] == 150900
    assert second_summary["uncovered_total"] == 50100


def test_daily_work_report_validation_errors(client):
    headers = _admin_headers(client)
    missing_treatment = client.post("/api/revenue/daily-report", json={
        "report_date": "2099-10-02",
        "selected_treatment_codes": ["missing-code"],
        "custom_fields": [],
    }, headers=headers)
    assert missing_treatment.status_code == 400

    bad_field_type = client.post("/api/revenue/daily-report", json={
        "report_date": "2099-10-02",
        "selected_treatment_codes": [],
        "custom_fields": [{"label": "잘못된 칸", "type": "unknown", "value": ""}],
    }, headers=headers)
    assert bad_field_type.status_code == 400

    bad_date = client.get("/api/revenue/daily-report?date=2099-99-99", headers=headers)
    assert bad_date.status_code == 400


def test_daily_work_report_requires_admin(client):
    get_resp = client.get("/api/revenue/daily-report?date=2099-10-01")
    assert get_resp.status_code == 401
    post_resp = client.post("/api/revenue/daily-report", json={
        "report_date": "2099-10-01",
        "selected_treatment_codes": [],
        "custom_fields": [],
    })
    assert post_resp.status_code == 401
    import_resp = client.post(
        "/api/revenue/daily-medical-summary/import",
        files={"file": ("empty.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert import_resp.status_code == 401
