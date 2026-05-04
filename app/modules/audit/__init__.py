"""modules.audit — 감사 로그 (AuditLog) 도메인 후보 구조 (19-12 신규).

19-12 본 세션 범위:
  - **service.py** : ``AuditLog`` row → 응답 dict serializer + ``detail`` 500자 cap
    helper + PII 원문 비저장 정책 가드. ``app/routers/api.py:audit`` /
    ``list_audit_logs`` 와 byte-equivalent.
  - **schemas.py** : ``/api/audit-logs`` 응답 row key contract 상수 (frozenset).

19-12 본 세션 범위 *외* (audit 본체 / CUD 호출지 무수정):
  - ``app/routers/api.py`` 의 ``audit()`` / ``_log()`` (sync 위임) +
    ``list_audit_logs`` 핸들러 *완전 무수정* — 본 패키지는 *helper 만* 제공.
  - 모든 CUD 호출지의 ``audit(db, action, entity_id, detail)`` 시그니처 *완전 무수정*.
  - ``app/services/ai/ai_logging.py`` 의 ``AiUsageLog`` / ``AiSetting`` audit 로깅
    *완전 무수정* (AI 전용 — 별도 모듈).
  - DB schema / migration *완전 무수정* — ``AuditLog`` 컬럼 그대로.
  - UI / API URL / 응답 key *완전 무수정*.

# COMPAT: 기존 ``audit(db, action, entity_id, detail, actor)`` 시그니처 *완전 무수정*
#         — 모든 CUD 호출지가 의존. 본 패키지는 응답 직렬화 + cap helper 만 제공.
#         라우터 채택 ⊥. 19-12 contract 테스트가 인라인 동작과 본 helper 결과의
#         byte-equivalent 검증.

# COMPAT: ``GET /api/audit-logs`` 응답 row key 7개 (``id`` / ``ts`` / ``node_id`` /
#         ``actor`` / ``action`` / ``entity_id`` / ``detail``) — 관리자탭 audit 표시
#         의존. 본 19-12 가 key 변경 ⊥.

# SAFETY: ``AuditLog.detail`` 컬럼은 PII 원문 / API key 원문 / 비밀번호 원문 *부재
#         보장* — ``app/routers/api.py:audit`` / 호출지 (예: ``patient.bulk_import``
#         의 detail 은 *환자명 / 차트번호 / 전화번호 부재*, 카운트만) 가 정책 단일 원천.
#         본 19-12 가 *변경 ⊥*.

# SAFETY: ``detail[:500]`` cap 정책 (``app/routers/api.py:audit``) 은 PII 폭주 /
#         payload 폭주 방지. 본 ``AUDIT_DETAIL_CAP = 500`` 이 정책 단일 원천 —
#         ``app/modules/admin/service.py:audit_detail_cap`` 와 정합.

# SAFETY: ``AuditLog.actor`` 는 ``"system"`` (기본) / ``"admin"`` 만 — 사용자명 /
#         이메일 *부재 보장*. 본 19-12 가 *변경 ⊥*.

# RISK: ``audit()`` 호출 후 ``db.commit()`` 시점은 호출지가 보유 — ``audit()`` 자체는
#       ``db.add(...)`` 만 수행. 본 19-12 가 commit 시점 정책 변경 ⊥.

# NOTE: ``/api/restore`` 직후 audit 호출은 *새 SessionLocal()* 로 새로 열린 (복원된)
#       DB 에 기록. 실패 시 백업 폴더의 ``restore_audit.log`` 에 폴백 기록.
#       본 19-12 가 폴백 정책 변경 ⊥.

# NOTE: AI 전용 사용 로그 (``AiUsageLog``) 는 ``app/services/ai/ai_logging.py``
#       단일 원천 — 본 audit 모듈은 *재정의 ⊥*. AI 모듈 분리 (post-19-12) 시
#       별도 처리.

# TODO(후속 검토): ``AuditLog`` retention 정책 (예: 90일 자동 정리) 은 *현재 미구현*
#                  — 19-12 범위 외. 후속 19-x 에서 검토.
"""
