"""ai_audit — AI 명령 로그 저장 (Phase 1).

역할:
- ai_command_logs 테이블에 AI 명령 처리 과정 기록.
- 원본 명령 / AI 파싱 결과 / DB 매칭 / 검증 / 사용자 선택 / 승인 / 실행 결과 / 오류.
- 신환 등록과 예약 등록은 **각각 별도 로그** 로 남김.

주의:
- 본 모듈은 DB 직접 raw SQL 호출이 아니라 sqlite3 connection 을 받아 처리.
- Phase 5 이후 ai_executor 가 본 모듈을 호출해 로그 저장.
- 외부 AI API 호출 안 함 / 환자 PII 외부 전송 안 함.

cross-reference:
- AI_COMMAND_ARCHITECTURE.md § 2.8 / § 5.1 (17 필드)
- AI_FEATURE_MASTER_PLAN.md § 10.2 (신환 / 예약 별도 로그)
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def write_log(
    conn: sqlite3.Connection,
    *,
    user_id: str | None,
    raw_text: str,
    intent: str | None = None,
    status: str = "received",
    parsed_json: dict[str, Any] | None = None,
    resolved_json: dict[str, Any] | None = None,
    validation_result: dict[str, Any] | None = None,
    preview_json: dict[str, Any] | None = None,
    selected_patient_id: int | None = None,
    selected_treatment_items_json: list[dict[str, Any]] | None = None,
    approved_by: str | None = None,
    executed_result: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> int:
    """ai_command_logs 한 줄 INSERT — 새 command_id (lastrowid) 반환.

    JSON 필드는 dict / list 를 받아 json.dumps 로 직렬화. None 은 NULL.
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ai_command_logs (
            user_id, raw_text, intent, status,
            parsed_json, resolved_json, validation_result, preview_json,
            selected_patient_id, selected_treatment_items_json,
            approved_by, executed_result, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            raw_text,
            intent,
            status,
            _to_json(parsed_json),
            _to_json(resolved_json),
            _to_json(validation_result),
            _to_json(preview_json),
            selected_patient_id,
            _to_json(selected_treatment_items_json),
            approved_by,
            _to_json(executed_result),
            error_message,
        ),
    )
    conn.commit()
    return cur.lastrowid or 0


def update_log(
    conn: sqlite3.Connection,
    command_id: int,
    *,
    status: str | None = None,
    resolved_json: dict[str, Any] | None = None,
    validation_result: dict[str, Any] | None = None,
    preview_json: dict[str, Any] | None = None,
    selected_patient_id: int | None = None,
    selected_treatment_items_json: list[dict[str, Any]] | None = None,
    approved_by: str | None = None,
    executed_result: dict[str, Any] | None = None,
    error_message: str | None = None,
    executed_at_now: bool = False,
) -> None:
    """기존 명령 로그 갱신 — 전달된 필드만 SET. updated_at 은 trigger 또는 수동.

    executed_at_now=True 시 executed_at = CURRENT_TIMESTAMP.
    """
    sets: list[str] = []
    args: list[Any] = []
    if status is not None:
        sets.append("status = ?")
        args.append(status)
    if resolved_json is not None:
        sets.append("resolved_json = ?")
        args.append(_to_json(resolved_json))
    if validation_result is not None:
        sets.append("validation_result = ?")
        args.append(_to_json(validation_result))
    if preview_json is not None:
        sets.append("preview_json = ?")
        args.append(_to_json(preview_json))
    if selected_patient_id is not None:
        sets.append("selected_patient_id = ?")
        args.append(selected_patient_id)
    if selected_treatment_items_json is not None:
        sets.append("selected_treatment_items_json = ?")
        args.append(_to_json(selected_treatment_items_json))
    if approved_by is not None:
        sets.append("approved_by = ?")
        args.append(approved_by)
    if executed_result is not None:
        sets.append("executed_result = ?")
        args.append(_to_json(executed_result))
    if error_message is not None:
        sets.append("error_message = ?")
        args.append(error_message)
    if executed_at_now:
        sets.append("executed_at = CURRENT_TIMESTAMP")

    sets.append("updated_at = CURRENT_TIMESTAMP")
    if not sets:
        return

    args.append(command_id)
    cur = conn.cursor()
    cur.execute(
        f"UPDATE ai_command_logs SET {', '.join(sets)} WHERE id = ?",  # noqa: S608
        args,
    )
    conn.commit()


def list_logs(
    conn: sqlite3.Connection,
    *,
    user_id: str | None = None,
    intent: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """ai_command_logs 최근 로그 조회 (최신순). JSON 필드 자동 deserialize."""
    where: list[str] = []
    args: list[Any] = []
    if user_id is not None:
        where.append("user_id = ?")
        args.append(user_id)
    if intent is not None:
        where.append("intent = ?")
        args.append(intent)
    if status is not None:
        where.append("status = ?")
        args.append(status)
    where_clause = ("WHERE " + " AND ".join(where)) if where else ""
    args.extend([int(limit), int(offset)])
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM ai_command_logs {where_clause} "  # noqa: S608
        f"ORDER BY id DESC LIMIT ? OFFSET ?",
        args,
    )
    rows = cur.fetchall()
    cols = [c[0] for c in cur.description] if cur.description else []
    out: list[dict[str, Any]] = []
    for row in rows:
        result = dict(zip(cols, row, strict=False))
        for k in (
            "parsed_json",
            "resolved_json",
            "validation_result",
            "preview_json",
            "selected_treatment_items_json",
            "executed_result",
        ):
            if result.get(k):
                try:
                    result[k] = json.loads(result[k])
                except (json.JSONDecodeError, TypeError):
                    pass
        out.append(result)
    return out


def get_log(conn: sqlite3.Connection, command_id: int) -> dict[str, Any] | None:
    """특정 명령 로그 조회 — JSON 필드는 자동 deserialize."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM ai_command_logs WHERE id = ?", (command_id,))
    row = cur.fetchone()
    if row is None:
        return None
    cols = [c[0] for c in cur.description]
    result = dict(zip(cols, row, strict=False))
    for k in (
        "parsed_json",
        "resolved_json",
        "validation_result",
        "preview_json",
        "selected_treatment_items_json",
        "executed_result",
    ):
        if result.get(k):
            try:
                result[k] = json.loads(result[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return result


def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)
