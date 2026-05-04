"""Privacy / retention module (post-19-P / 20-1 그룹 A).

F-7 privacy / retention 정책 — 환자 비활성 마스킹 + AI 로그 보존 정책.
schema 변경 ⊥ — 정책 / 헬퍼만 신설.

# SAFETY: 자동 트리거는 본 v1 에서 미설치. 헬퍼 함수만 제공 — 호출은 admin
# endpoint / 백업 시점 / cron 등 별도 결정.
"""

from app.modules.privacy.retention import (
    AI_LOG_RETENTION_MONTHS,
    PATIENT_INACTIVE_MASK_MONTHS,
    delete_old_ai_logs,
    mask_inactive_patients,
)

__all__ = [
    "AI_LOG_RETENTION_MONTHS",
    "PATIENT_INACTIVE_MASK_MONTHS",
    "delete_old_ai_logs",
    "mask_inactive_patients",
]
