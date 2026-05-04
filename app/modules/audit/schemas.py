"""감사 로그 (AuditLog) API 응답 키 contract 상수 (19-12 신규).

frozenset 으로 응답 key 셋 보존. contract 테스트가 인라인 응답 dict 와 본 상수의
key 셋 비교 → 임의 변경 검출.

# COMPAT: 본 frozenset 상수의 *원소 변경 ⊥* — 관리자탭 audit 표시 의존.
#         contract 테스트가 회귀 검출.

# SAFETY: 응답 row 의 ``detail`` 은 ``AUDIT_DETAIL_CAP`` (500자) 로 cap 됨 —
#         PII / payload 폭주 방지. 본 19-12 가 *변경 ⊥*.

# SAFETY: 응답에 *환자 PII 원문 부재 보장* — ``actor`` 는 ``"system"`` / ``"admin"``
#         만, ``entity_id`` 는 ID 문자열만, ``detail`` 은 카운트 / 액션 메타만.
"""
from __future__ import annotations


# ──────────────── /api/audit-logs (행 단위 응답) ────────────────

# GET /api/audit-logs 응답 row dict key 7개.
# COMPAT: ``app/routers/api.py:list_audit_logs`` 의 dict 와 byte-equivalent.
AUDIT_LOG_ROW_KEYS: frozenset[str] = frozenset({
    "id",
    "ts",
    "node_id",
    "actor",
    "action",
    "entity_id",
    "detail",
})


# ──────────────── ``audit()`` 함수 시그니처 / 정책 상수 ────────────────

# RISK: ``app/routers/api.py:audit`` 의 ``detail[:500]`` 와 byte-equivalent.
#       본 19-12 가 *변경 ⊥* — PII / payload 폭주 회귀 방지.
AUDIT_DETAIL_CAP: int = 500

# NOTE: ``audit()`` 의 ``actor`` 기본값.
AUDIT_DEFAULT_ACTOR: str = "system"

# 허용된 actor 값 셋 (현재 정책 — 직원/관리자 분리는 후속 검토).
AUDIT_KNOWN_ACTORS: frozenset[str] = frozenset({
    "system",
    "admin",
})


# ──────────────── audit action prefix 정책 (참고용 — *제약 ⊥*) ────────────────

# NOTE: 현재 코드베이스에서 사용되는 audit action prefix. 본 19-12 가 새 action
#       추가 / 제거 ⊥ — 참고용.
AUDIT_KNOWN_ACTION_PREFIXES: frozenset[str] = frozenset({
    "admin.",                # admin.password_change
    "appointment.",          # appointment.create / update / delete / cancel
    "patient.",              # patient.create / update / delete / bulk_import
    "treatment.",            # treatment.create / update / delete
    "employee.",             # employee.create / update / delete
    "leave.",                # leave.create / delete
    "config.",               # config.update
    "system_setting.",       # system_setting.update
    "backup.",               # backup.manual / restore_latest / restore_by_name
    "db.",                   # db.restore
    "sms.",                  # sms.send
    "ai.",                   # ai.settings_update
    "manual_count.",         # manual_count.upsert
})


# ──────────────── 모든 audit contract 셋 (cross-check 용) ────────────────

AUDIT_ALL_CONTRACT_SETS: dict[str, frozenset[str]] = {
    "audit_log_row": AUDIT_LOG_ROW_KEYS,
    "audit_known_actors": AUDIT_KNOWN_ACTORS,
    "audit_known_action_prefixes": AUDIT_KNOWN_ACTION_PREFIXES,
}
