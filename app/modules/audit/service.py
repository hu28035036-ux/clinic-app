"""감사 로그 (AuditLog) 직렬화 + 정책 helper (19-12 신규).

19-11 stats.service / 19-10 sms.service 와 동일 패턴 — *byte-equivalent helper*.
``audit()`` 호출 본체 + ``list_audit_logs`` 핸들러는 ``app/routers/api.py`` 가
그대로 보유. 라우터 무수정.

# COMPAT: ``serialize_audit_log_row`` 는 ``app/routers/api.py:list_audit_logs`` 의
#         인라인 dict 와 *byte-equivalent*. 응답 key 7개 / 타입 보존.

# SAFETY: ``cap_detail`` 은 PII / payload 폭주 방지 — ``app/routers/api.py:audit`` 의
#         ``detail[:500]`` 와 byte-equivalent. 본 19-12 가 *변경 ⊥*.

# SAFETY: 본 모듈은 *읽기 / 응답 dict 조립 / 길이 cap* 만 — DB 변경 ⊥, 로그
#         생성 ⊥. 실제 AuditLog row 추가는 ``app/routers/api.py:audit`` 가
#         단일 원천.

# RISK: ``actor`` 는 caller 가 명시적 주입 — 빈값 / 임의 문자열 허용 ⊥. 정상
#       값은 ``"system"`` / ``"admin"`` 만 (``schemas.AUDIT_KNOWN_ACTORS``).

# NOTE: ``ts`` (datetime) 는 ISO 문자열로 직렬화 — UI 가 그대로 표시.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .schemas import AUDIT_DETAIL_CAP


def cap_detail(detail: str | None) -> str:
    """audit detail 길이 cap helper (500자) — ``app/routers/api.py:audit`` byte-equivalent.

    SAFETY: PII / payload 폭주 방지 — 호출자가 detail 에 환자명 / 차트번호 / 전화번호
    원문을 넣지 *않는* 책임은 호출지가 보유. 본 cap 은 *2차 가드*.
    """
    if detail is None:
        return ""
    return str(detail)[:AUDIT_DETAIL_CAP]


def serialize_audit_log_row(row: Any) -> dict[str, Any]:
    """``GET /api/audit-logs`` 응답 row dict 빌더 — ``app/routers/api.py:
    list_audit_logs`` 의 인라인 dict 와 byte-equivalent.

    매개변수 ``row`` 는 ``models.AuditLog`` 인스턴스 (또는 동일 속성을 가진 객체).
    ``row.ts`` 가 datetime 이면 ``isoformat()``, 문자열이면 그대로.

    응답 key 7개 (frozenset 와 정합).
    """
    ts = row.ts
    if isinstance(ts, datetime):
        ts_str: str = ts.isoformat()
    else:
        ts_str = str(ts) if ts is not None else ""

    return {
        "id": row.id,
        "ts": ts_str,
        "node_id": row.node_id,
        "actor": row.actor,
        "action": row.action,
        "entity_id": row.entity_id,
        "detail": row.detail,
    }


def serialize_audit_log_rows(rows: list[Any]) -> list[dict[str, Any]]:
    """``serialize_audit_log_row`` 의 리스트 변형 — ``list_audit_logs`` byte-equivalent.

    NOTE: caller 가 정렬 / limit 적용 후 전달. 본 helper 는 직렬화만.
    """
    return [serialize_audit_log_row(r) for r in rows]


def normalize_actor(actor: str | None) -> str:
    """``audit()`` 호출 시 actor 정규화 — 빈값 → ``"system"``.

    NOTE: ``app/routers/api.py:audit`` 의 ``actor: str = "system"`` 기본값 정책과
    정합.
    """
    if actor is None or not str(actor).strip():
        return "system"
    return str(actor).strip()


def normalize_action(action: str | None) -> str:
    """``audit()`` 호출 시 action 정규화 — 빈값 가드.

    NOTE: action 은 caller 가 명시 — ``"admin.password_change"`` / ``"backup.manual"``
    등 prefix 규약 (``schemas.AUDIT_KNOWN_ACTION_PREFIXES`` 참고).
    """
    if action is None:
        return ""
    return str(action).strip()


def normalize_entity_id(entity_id: str | None) -> str:
    """``audit()`` 호출 시 entity_id 정규화 — 빈값 → ``""``."""
    if entity_id is None:
        return ""
    return str(entity_id)
