"""세션 09 검증 — AiUsageLog / AuditLog 로깅 + PII 비저장.

검증:
  ① sms_validate 호출 시 AiUsageLog 생성
  ② manual_search 호출 시 AiUsageLog 생성 + hits 정보 기록
  ③ PUT /api/ai/settings 시 AuditLog 생성 (api_key 원문 미저장)
  ④ AI 비활성 상태에서 sms_draft → AiUsageLog outcome=blocked + AuditLog
  ⑤ AiUsageLog/AuditLog 어디에도 prompt/response 원문 없음 (해시만)
  ⑥ 전화/생년월일/차트번호 패턴이 로그 어떤 컬럼에도 없음

실행:
    venv/Scripts/python.exe -m pytest tests/test_ai_logging.py -v
"""
from __future__ import annotations

import sqlite3

from app.config import get_db_path


def _rows(table: str, columns: str = "*") -> list[tuple]:
    """현재 테스트 DB 에서 직접 조회 (ORM 안 거치고 raw)."""
    conn = sqlite3.connect(str(get_db_path()))
    try:
        cur = conn.cursor()
        return cur.execute(f"SELECT {columns} FROM {table} ORDER BY ts DESC").fetchall()
    finally:
        conn.close()


def _count_before(table: str) -> int:
    conn = sqlite3.connect(str(get_db_path()))
    try:
        cur = conn.cursor()
        return cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def _admin_token(client) -> str:
    """관리자 로그인 토큰 — conftest 시드의 기본 비번 사용."""
    resp = client.post("/api/admin/login", json={"password": "admin1234"})
    if resp.status_code != 200:
        raise RuntimeError(f"admin login failed: {resp.status_code} {resp.text}")
    return resp.json().get("token", "")


# ─────────── ① sms_validate → AiUsageLog ───────────

def test_sms_validate_creates_ai_usage_log(client):
    before = _count_before("ai_usage_logs")
    resp = client.post(
        "/api/ai/sms/validate",
        json={"items": [{"appointment_id": "x", "body": "안녕하세요"}]},
    )
    assert resp.status_code == 200, resp.text
    after = _count_before("ai_usage_logs")
    assert after == before + 1, (before, after)

    rows = _rows("ai_usage_logs", "feature, outcome")
    feature, outcome = rows[0]
    assert feature == "sms_validate"
    assert outcome in ("success", "warning", "error")


# ─────────── ② manual_search → AiUsageLog ───────────

def test_manual_search_creates_ai_usage_log(client):
    before = _count_before("ai_usage_logs")
    resp = client.post(
        "/api/ai/manual/search",
        json={"question": "예약문자 작성"},
    )
    assert resp.status_code == 200, resp.text
    after = _count_before("ai_usage_logs")
    assert after == before + 1, (before, after)

    rows = _rows("ai_usage_logs", "feature, outcome, error_detail")
    feature, outcome, error_detail = rows[0]
    assert feature == "manual_search"
    assert outcome in ("success", "warning")
    # hits/top_score 가 error_detail 에 인코딩됨 — 원문은 없음
    assert "hits=" in (error_detail or "")


# ─────────── ③ PUT /api/ai/settings → AuditLog (api_key 원문 미저장) ───────────

def test_put_settings_creates_audit_log_no_key_leak(client):
    token = _admin_token(client)
    secret_key = "sk-very-secret-test-key-1234567890abcdef"
    before = _count_before("audit_logs")
    resp = client.put(
        "/api/ai/settings",
        headers={"x-admin-token": token},
        json={
            "enabled": False,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": secret_key,
            "max_tokens": 256,
            "temperature": 0.4,
        },
    )
    assert resp.status_code == 200, resp.text
    after = _count_before("audit_logs")
    assert after >= before + 1

    # 모든 audit_logs detail 에 api_key 원문이 절대 들어가지 않아야 함
    conn = sqlite3.connect(str(get_db_path()))
    try:
        cur = conn.cursor()
        all_details = cur.execute("SELECT detail FROM audit_logs").fetchall()
    finally:
        conn.close()
    for (d,) in all_details:
        assert secret_key not in (d or ""), f"api_key leaked into audit_logs: {d!r}"


# ─────────── ④ AI 비활성 → sms_draft 차단 시 AiUsageLog blocked ───────────

def test_sms_draft_disabled_logs_blocked(client):
    # conftest 가 AI 비활성 상태로 시드 (enabled=0). 만약 다른 테스트가 켰을 수
    # 있으니 여기서 명시적으로 disable.
    token = _admin_token(client)
    client.put(
        "/api/ai/settings",
        headers={"x-admin-token": token},
        json={"enabled": False},
    )
    before_usage = _count_before("ai_usage_logs")
    before_audit = _count_before("audit_logs")
    resp = client.post(
        "/api/ai/sms/draft",
        json={"appointment_id": "any-id", "tone": "friendly"},
    )
    assert resp.status_code == 503, resp.text
    after_usage = _count_before("ai_usage_logs")
    after_audit = _count_before("audit_logs")
    assert after_usage >= before_usage + 1
    assert after_audit >= before_audit + 1

    rows = _rows("ai_usage_logs", "feature, outcome, error_detail")
    feature, outcome, error_detail = rows[0]
    assert feature == "sms_draft"
    assert outcome == "blocked"
    assert "ai disabled" in (error_detail or "")


# ─────────── ⑤ 로그 어디에도 prompt/response 원문 없음 ───────────

def test_no_raw_prompt_in_logs(client):
    """질문에 명시적 마커를 넣어, 로그 컬럼 어디에도 안 들어갔는지 확인."""
    marker = "MAGIC_MARKER_8729413"
    resp = client.post(
        "/api/ai/manual/search",
        json={"question": f"예약문자 작성 {marker}"},
    )
    assert resp.status_code == 200, resp.text

    conn = sqlite3.connect(str(get_db_path()))
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT prompt_hash, response_hash, error_detail "
            "FROM ai_usage_logs ORDER BY ts DESC LIMIT 5"
        ).fetchall()
        # AuditLog detail 에도 안 남아야 함
        det = cur.execute(
            "SELECT detail FROM audit_logs ORDER BY ts DESC LIMIT 20"
        ).fetchall()
    finally:
        conn.close()

    for ph, rh, ed in rows:
        for col in (ph, rh, ed):
            assert marker not in (col or ""), f"marker leaked: {col!r}"
    for (d,) in det:
        assert marker not in (d or ""), f"marker leaked into audit: {d!r}"


# ─────────── ⑥ 전화/생년월일/차트 패턴이 로그에 안 들어감 ───────────

def test_no_pii_in_logs(client):
    phone = "010-1234-5678"
    birth = "1990-05-15"
    chart = "9876543210"
    resp = client.post(
        "/api/ai/manual/search",
        json={"question": f"환자 {phone} {birth} {chart} 매뉴얼"},
    )
    assert resp.status_code == 200, resp.text

    conn = sqlite3.connect(str(get_db_path()))
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT prompt_hash, response_hash, error_detail, error_kind "
            "FROM ai_usage_logs ORDER BY ts DESC LIMIT 5"
        ).fetchall()
        det = cur.execute(
            "SELECT detail FROM audit_logs ORDER BY ts DESC LIMIT 20"
        ).fetchall()
    finally:
        conn.close()

    for ph, rh, ed, ek in rows:
        for col in (ph, rh, ed, ek):
            text = col or ""
            assert phone not in text and "01012345678" not in text
            assert birth not in text and "19900515" not in text
            assert chart not in text
    for (d,) in det:
        text = d or ""
        assert phone not in text and "01012345678" not in text
        assert birth not in text and "19900515" not in text
        assert chart not in text
