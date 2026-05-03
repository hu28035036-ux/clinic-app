# 18-4 Codex 검증 결과 (응답) — 4회차 (최종)

## 최종 판정 (4회차)

**Codex 4회차 결론**: "18-5 로 넘어가도 됩니다. 18-4 knowledge_chunks DB / reindex 구현은 현재 기준 통과입니다."

추가 기록 요청: manual_qa.py / conftest.py 변경이 이전 세션 (18-2 / 18-0) 산출물이라는 점을 명시 → 본 응답 §A 에 기록.

---

## §A. 작업트리 변경 출처 명시 (M-1 정리 — 18-5 리뷰 헷갈림 방지)

`git status` 의 modified/untracked 항목을 세션별로 분류:

| 파일 | 출처 세션 | 통과 baseline 리포트 | 18-4 수정 여부 |
|---|---|---|---|
| `app/services/ai/manual_qa.py` | **18-2** (keyword RAG 분리, wrapper 화) | `reports/ai_dev_loop/18-2_codex_review_request.md` | ❌ (변경 0) |
| `tests/conftest.py` | **18-0** (RAG/Safety 하네스 + AI fixture) | `reports/ai_dev_loop/18-0_rag_harness_codex_review_request.md` | ❌ (변경 0) |
| `.gitignore` | **로컬 정리** (venv_broken*/) — 세션 외 | (해당 없음) | ❌ (변경 0) |
| `app/services/ai/knowledge/` (folder) | **18-1/18-2/18-3** (구조 + loader/normalizer/chunker) | 18-1, 18-2, 18-3 codex_review_request | 18-4 추가: `indexer.py` 신규만 |
| `app/services/ai/rag/` (folder) | **18-1/18-2** (schemas/safety/prompts/retriever/pipeline) | 18-1, 18-2 codex_review_request | ❌ (18-4 변경 0) |
| `docs/AI_WORKING_RULES.md` 외 docs/ | **18-0~18-3** | 각 세션 리포트 | 18-4 추가: `migrations_rollback/m012_rollback.sql` 신규만 |
| `tests/harness/{rag,safety,chunk,fake_provider,contract}.py` | **18-0~18-3** | 각 세션 리포트 | 18-4 추가: `reindex_harness.py` 신규만 |
| `tests/test_ai_{manual_rag,safety,full,chunker,...}_harness.py` | **18-0~18-3** | 각 세션 리포트 | 18-4 추가: `test_ai_reindex_harness.py` 신규만 |
| `tests/test_rag_pipeline.py` / `test_rag_safety.py` / `test_local_only_mode.py` | **18-0~18-2** | 각 세션 리포트 | ❌ (18-4 변경 0) |
| `reports/` | **18-0~18-3** 누적 | 각 세션 리포트 | 18-4 추가: `18-4_*.md` + `latest_*.md` overwrite |

**18-4 순수 기여 파일 (8 신규 + 1 수정)**:
- 신규: `app/migrations/m012_knowledge_chunks.py`, `app/services/ai/knowledge/indexer.py`, `tests/harness/reindex_harness.py`, `tests/test_ai_reindex_harness.py`, `docs/migrations_rollback/m012_rollback.sql`, `reports/ai_dev_loop/18-4_{test_report,fix_summary,codex_review_request,codex_review_response}.md`
- 수정: `app/models/models.py` (끝에 `KnowledgeChunk`, `KnowledgeIndexRun` 두 클래스 append) + `reports/ai_dev_loop/latest_{test_report,fix_summary,codex_review_request,codex_review_response}.md` overwrite

---

# 18-4 Codex 검증 결과 (응답) — 3회차 갱신

## 판정 요약 (3회차)

- **치명적 문제**: 없음 (Codex 가 의심한 한글 주석 표시 문제는 콘솔 인코딩 — 실제 파일 정상)
- **범위 초과**: 없음 (indexer.py 에 vector/embedding/hybrid/UI/관리자 화면/외부 호출 0)
- **테스트** (Codex 3회차 보강 — Codex 측 venv 깨짐 → Claude Code 환경 대신 실행):
  - reindex 하네스: **24 passed**
  - chunker/manual/contract/safety/full 묶음: **82 passed**
  - **SMS/휴무 AI + manual_qa + hallucination + logging + health 묶음: 98 passed** (3회차 신규 재실행)
  - **전체: 313 passed, 1 skipped, 7 xfailed** (3회차 재실행 — 1·2회차 baseline 과 동일)
  - ruff: **All checks passed!**

## 중간 위험 문제

### M-1. 작업트리에 18-0~18-3 변경이 untracked/modified 로 공존

**현황**: `git status` 에 `app/services/ai/manual_qa.py` (18-2 wrapper 분리), `tests/conftest.py` (18-0 fixture 추가), `.gitignore` (이전 세션 로컬 정리) 가 modified 로 남음.

**평가**:
- `manual_qa.py` — 18-2 통과본 (`reports/ai_dev_loop/18-2_codex_review_request.md` baseline). 18-4 미수정 확인.
- `conftest.py` — 18-0 통과본 (`reports/ai_dev_loop/18-0_rag_harness_codex_review_request.md` baseline). 18-4 미수정 확인.
- `.gitignore` — venv_broken*/ 로컬 정리. 제품 동작 영향 0.

**조치 권고**: 18-4 PR 분리 시점에 git 로 변경 출처 명시. 본 세션은 정책상 단일 브랜치 운영이라 누적 diff 정상.

### M-2. m012 가 ORM `create_all` 후 인덱스 보강만 수행

**현황**: m012 가 `_table_exists` 가드로 테이블 존재 시에만 인덱스 생성. 테이블 자체는 `Base.metadata.create_all` 책임.

**위험 발생 조건**: `init_db()` 를 거치지 않고 마이그레이션만 단독 실행하는 경로 (외부 도구 등) — **현재 코드 호출 그래프에서는 발생 불가** (`app/database.py:123-148` 의 `init_db()` 가 단독 진입점).

**일관성 평가**: m007 (`ai_settings`), m008 (`ai_usage_logs`) 모두 동일 패턴 — "ORM create_all + 마이그레이션이 시드/인덱스 보강". m012 는 기존 패턴 유지.

**완화 옵션**:
- (A) **현재 유지** + m012 docstring 에 "init_db 진입 가정" 명시 (1줄 문서 변경)
- (B) m012 에 raw `CREATE TABLE IF NOT EXISTS` 추가 → 자체 충족. 단, ORM 정의와 SQL 중복 → 향후 컬럼 추가 시 두 곳 동기화 필수.

권고: **(A)** — m007/m008 패턴 일관성 유지, 미래 ORM 컬럼 변경 시 SQL 중복 부담 회피.

## 사소한 개선

### S-1. content_hash 중복 방지 의미 해석 차이

**현재 구현**: `(doc_id, chunk_index)` 위치 키 + 동일 hash → skip. **전역 content_hash UNIQUE 는 의도적 미적용**.

**근거** (`docs/ai_rag_migration_plan.md` §2):
> `content_hash` UNIQUE는 걸지 않음 (서로 다른 문서가 동일 텍스트일 수 있음). 중복 방지는 `(doc_id, chunk_index)` UNIQUE로.

→ **버그 아님**. 설계 결정 그대로. 만약 사용자가 "전역 UNIQUE" 의미였다면 별도 결정 필요.

### S-2. `.gitignore` 변경 (M-1 과 중복)

18-4 와 무관 (이전 세션 로컬 정리). 제품 동작 영향 0.

### S-3. pytest warning 27 개

`tests/test_ai_sms_validate.py` 의 test 함수가 tuple return — pytest 8+ 권장은 assert. 18-4 와 무관 (기존 코드).

### S-4. `app/models/__init__.py` 신규 클래스 export 미추가

현재 코드는 직접 경로 (`from app.models.models import KnowledgeChunk`) 사용 → 문제 없음. 18-7 에서 라우터가 패키지 레벨 import 시 보강.

### S-5. `check_db_path.py` 단독 실행 시 운영 경로 표시

설계 의도. pytest 중에는 conftest 가 격리 DB 사용 — `test_12_does_not_use_operational_db` 통과로 입증.

## 테스트가 부족한 부분 (Codex 2회차 신규 지적)

### T-1. embedding provider 차단이 mock object 수준

**현황**: `test_11_no_embedding_provider_call` 이 단순 `_MockEmbedding.calls == 0` 단언 — 실제 embedding factory/client 경로 차단은 검증 안 함.

**평가**: 18-4 시점에 embedding 코드가 부재 (사용자 명시 금지) → factory/client 자체가 없음. 18-4 단언 대상은 "indexer 가 어떤 embedding 코드도 import/호출하지 않음" 이고 이는 `test_19_indexer_import_graph_safe` 의 AST 검사로 보강됨.

**18-5 권고**: 18-5 시점에 embedding factory 도입 시 다음 단언 추가:
- `test_indexer_does_not_call_embedding_factory` — `vector.embeddings.get_provider` monkeypatch 후 `len(factory.calls) == 0` 단언
- `test_local_only_blocks_embedding_factory` — `local_only` 모드에서 factory 호출 자체가 RuntimeError 단언

본 세션 범위 외 — 18-5 체크리스트에 추가 권고.

### T-2. m012 단독 실행만으로 테이블 생성 검증 약함

**현황**: M-2 와 동일 원인. m012 단독 실행 시 `_table_exists` false → 인덱스 생성 skip. 테이블 자체도 ORM create_all 미호출 시 부재.

**평가**: 현재 호출 그래프에서 발생 불가. 검증을 강화하려면 추가 테스트 가능:
- `test_init_db_creates_knowledge_tables` — `init_db()` 호출 직후 두 테이블 존재 단언 (간접 검증)
- `test_m012_alone_skips_when_tables_absent` — m012 단독 호출이 tables 부재 시 안전 skip 단언 (M-2 의도된 동작 검증)

본 세션 24 tests 안에 `test_1_*` (테이블 생성) 와 `test_22_m012_idempotent` (멱등) 가 일부 cover. 단독 실행 시나리오는 의도적 미커버 (실제 발생 불가 경로).

**18-5 권고**: 18-5 시 vector store schema 추가 m013 도 동일 패턴이면 단독 실행 검증 테스트 1개 추가 권장.

## 사용자 요구 15개 단언 매핑 재확인

| # | 사용자 요구 | 본 세션 단언 | 통과 |
|---|---|---|---|
| 5 | content_hash 같으면 skip | `test_5_same_hash_skipped` ((doc_id, chunk_index) 위치별) | ✅ |

→ 사용자 메시지의 "content_hash 기반 중복 방지" 는 (doc_id, chunk_index) 위치별로 해석함 (설계 plan §2 와 정합). 만약 "전역 UNIQUE" 의도였다면 사용자 확인 필요.

## 추가 액션 (Claude Code 자체 판단)

| 액션 | 권고 | 사유 |
|---|---|---|
| 18-5 (vector/embedding) 진입 | **OK (사용자 승인 후)** | 치명/회귀 0, 사용자 금지 사항 100% 준수 |
| M-2 보강 (docstring 1줄) | **선택 사항** | 현재 호출 그래프에서 발생 불가, 패턴 일관성 |
| S-1 (전역 content_hash 중복 의도 확인) | **사용자 확인 필요** | 설계 plan 기준은 "위치별" 이지만 사용자 메시지 해석 차이 가능 |
| T-1/T-2 | **18-5 체크리스트로 이관** | 18-5 vector store 도입 시 함께 처리 |

## 다음 단계 제안

1. **이대로 마무리** → 18-5 진입 (사용자 승인 시) — 기본 권고
2. **M-2 docstring 추가** → 1줄 변경 (코드 동작 영향 0)
3. **전역 content_hash UNIQUE 도입** → S-1 의도가 그쪽이라면 m012/모델 수정. 단, 설계 plan 변경 필요
4. **모든 사소한 개선까지 처리** → 별도 정리 세션 권장

## 3회차 재실행 보강 (Codex 측 venv 실패 대응)

Codex 3회차 검증 시 `python.exe` 경로 깨짐으로 SMS/휴무 AI 묶음과 전체 테스트 재실행이 미완료. Claude Code 환경에서 동일 테스트를 재실행하여 보강:

```
$ venv/Scripts/python.exe -m pytest tests/test_ai_sms_draft.py tests/test_ai_sms_validate.py tests/test_ai_sms_draft_hallucination.py tests/test_ai_action_leave.py tests/test_ai_hallucination.py tests/test_ai_logging.py tests/test_ai_manual_qa.py tests/test_ai_health_public.py -v
======================= 98 passed, 27 warnings in 3.05s =======================

$ venv/Scripts/python.exe -m pytest tests -v --tb=no -q
=========== 313 passed, 1 skipped, 7 xfailed, 27 warnings in 6.63s ============
```

→ 3회차 baseline 으로 SMS/휴무 AI 회귀 0 + 전체 회귀 0 확인.
- 18-4 코드 변경 (indexer/m012/모델/테스트/롤백 SQL/리포트) 이후 추가 코드 수정 없음 — 1·2회차 결과와 동일 baseline.
- 27 warning 은 기존 `tests/test_ai_sms_validate.py` 의 tuple return 패턴 (S-3, 18-4 무관).
