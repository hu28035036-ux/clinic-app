# 18-4 체크리스트 — knowledge_chunks DB / reindex (m012)

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-4 실행 가이드 · 시점=18-4 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`ai_rag_migration_plan.md`, `ai_rag_rollout_plan.md`, `harnesses/chunk_harness_plan.md` · 결정=m012 도입과 reindex 운영 정책 · 비결정=vector(18-5)·hybrid(18-6).

## 세션 목표
chunker 출력을 SQLite에 영속화. m012 마이그레이션(`knowledge_chunks` + `knowledge_index_runs`) 도입. reindex 운영(트리거/lock/부분 실패/기존 보존) + 관리자 화면 일부.

## 수정 가능 범위
`app/migrations/m012_knowledge_chunks.py` · `app/services/ai/knowledge/indexer.py` · `app/services/ai/health.py` · 신규 라우트 `/api/ai/reindex`(admin)·`/api/ai/status` · 관리자 UI 일부 · 신규 테스트 (`test_knowledge_chunks_db`, `test_knowledge_indexer`, `test_ai_reindex`) · `dosu_clinic.spec` hidden import · `docs/migrations_rollback/m012_rollback.sql`.

## 수정 금지 범위
기존 m001~m011 수정 · requirements.txt · vector 코드 · 응답 9개 키 변경 · 일반 직원에게 reindex 권한.

## 반드시 지킬 안전 원칙
m012 idempotent · reindex 실패 시 기존 chunk 보존 · content_hash 동일 → upsert skip · 운영 DB 보호(`scripts/check_db_path.py`) · admin 권한 강제 · API key 미노출.

## 외부 API 호출 가능/불가능 여부
**불가능.** indexer는 chunker만 호출. vector 단계는 18-5에서 추가.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**불필요(호출되면 fail).** indexer 단위는 LLM/embedding 무관.

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_knowledge_chunks_db.py tests/test_knowledge_indexer.py tests/test_ai_reindex.py tests/test_ai_health_status.py tests/test_full_harness.py -v
```

## 완료 조건
- [ ] `run_check.bat` 통과 · 기존 모든 테스트 100% 통과
- [ ] m012 두 번 실행 안전(idempotent) · rollback SQL 보관
- [ ] reindex 중복 실행 lock 동작 · 부분 실패 시 기존 chunk 보존
- [ ] `/api/ai/reindex` 일반 직원 403, admin 200
- [ ] 관리자 UI에 chunk 수 / 마지막 reindex / 실패 목록 노출
- [ ] PyInstaller spec에 m012 등록
- [ ] 5회 이내 통과
- [ ] `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
m012 idempotent 입증, m001~m011 diff 0, lock 동시성 차단 입증, 부분 실패 시 기존 인덱스 보존 입증, admin 권한 분리 입증, 운영 DB 미접근, hidden import 등록, 다음 세션(18-5) 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-4 추가 참조**: `docs/ai_rag_migration_plan.md` §2 §4 §6 · `docs/ai_rag_architecture_plan.md` §3-19 · `docs/ai_rag_rollout_plan.md` §7 §8 · `docs/harnesses/chunk_harness_plan.md`.
