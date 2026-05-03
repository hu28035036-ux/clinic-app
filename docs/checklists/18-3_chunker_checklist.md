# 18-3 체크리스트 — Chunker 구현

> 이 문서는 해당 세션에서 반드시 확인해야 하는 실행 체크리스트다.
> 공통 규칙은 `docs/AI_WORKING_RULES.md`와 `docs/ai_code_session_protocol.md`를 먼저 확인한다.
> 상세 설계는 관련 ai_rag 문서를 참조한다.

**메타**: 목적=18-3 실행 가이드 · 시점=18-3 시작 시 · 독자=Claude Code/Codex/사용자 · 관련=`harnesses/chunk_harness_plan.md`, `ai_rag_architecture_plan.md`, `ai_rag_migration_plan.md` · 결정=loader/normalizer/chunker 인터페이스와 결정성 · 비결정=DB 영속화(18-4)·vector(18-5).

## 세션 목표
마크다운 → 결정적 chunk 분리. **in-memory만**, DB 영속화는 18-4. 표/코드블록/목록 보호, content_hash 안정성, heading 기반 분리 + 짧은 chunk 병합 + 긴 chunk 분리 + overlap.

## 수정 가능 범위
`app/services/ai/knowledge/{loader,normalizer,chunker}.py` · `app/services/ai/knowledge/synonyms.py` 보강 · `tests/harness/chunk_harness.py` 신규 · `tests/test_chunker.py`/`test_knowledge_loader.py` 신규 · `dosu_clinic.spec` hidden import.

## 수정 금지 범위
DB 마이그레이션 · requirements.txt · 라우터 · `manual_qa` wrapper · 응답 키 · vector/embedding 코드.

## 반드시 지킬 안전 원칙
청킹 결정성(랜덤성/시간 의존 0) · 표/목록/코드블록 절단 금지 · content_hash 입력에 콘텐츠 외 메타 미포함 · 운영 DB 미접근 · 외부 호출 0.

## 외부 API 호출 가능/불가능 여부
**불가능.** chunker는 순수 텍스트 처리.

## FakeProvider / FakeEmbeddingProvider 필요 여부
**불필요.** 호출되면 fail하도록 conftest 기본 시드만.

## 반드시 실행할 테스트
```
run_check.bat
venv\Scripts\python.exe -m pytest tests/test_chunker.py tests/test_knowledge_loader.py tests/test_full_harness.py tests/test_ai_manual_qa.py -v
```

## 완료 조건
- [ ] `run_check.bat` 통과
- [ ] 기존 모든 테스트 100% 통과
- [ ] 동일 입력 → 동일 chunks/순서 (결정성)
- [ ] 표/코드블록/목록 보호 단언 통과
- [ ] content_hash 안정성 (1글자 변경 시 영향 chunk만 hash 변경)
- [ ] provider/embedding call count 모두 0 (`len(provider.calls) == 0`, `len(embedding_provider.calls) == 0`)
- [ ] 5회 이내 통과
- [ ] `latest_*_report.md` 3종 작성

## Codex 검증 요청 문서에 꼭 적을 내용
chunker 결정성 입증 방법, content_hash 알고리즘, normalizer heading 추출 규칙, 한국어 token_count 정의, 18-2 keyword 결과 회귀 0(eval) 입증, 다음 세션(18-4) 진입 yes/no.

## 참조해야 할 상세 문서 목록
**공통 베이스 5개**(`AI_WORKING_RULES`, `ai_code_session_protocol`, `ai_docs_index`, `ai_rag_current_state`, 본 체크리스트).
**18-3 추가 참조**: `docs/ai_rag_architecture_plan.md` §3-1~3-4 · `docs/ai_rag_migration_plan.md` (chunk 스키마 사전 참고) · `docs/harnesses/chunk_harness_plan.md`.
