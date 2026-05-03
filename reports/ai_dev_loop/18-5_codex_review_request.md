# 18-5 Codex 검증 요청서 (2회차 — Codex M-1 반영 후)

> 1회차 Codex 검토 결과: 치명적 문제 0, 중간 위험 M-1 (`dosu_clinic.spec`
> 변경이 사용자 본 세션 "PyInstaller spec 수정 금지" 위반).
> **조치**: spec 변경 전체 revert → 18-4 baseline 그대로 유지.
> 본 2회차 요청서는 revert 반영 후 재실행 결과를 기록.

## 1. 세션 이름

**18-5_vector_embedding** — Vector store / Embedding 도입 (FakeEmbeddingProvider 기반)

## 2. 작업 목표

- `knowledge_vectors` 테이블 (m013) 추가
- `vector/embeddings.py`, `vector/store.py`, `vector/similarity.py` 구현
- FakeEmbeddingProvider 기반 외부 API 호출 0 검증
- `content_hash` 기반 embedding 재생성 방지
- API key 없음 / provider disabled / `local_only` 모드에서 embedding 호출 차단
- embedding provider 오류 시 keyword/local fallback 가능
- 18-4 chunk 영속화 / 18-3 chunker / 18-2 manual RAG / 18-0 safety 회귀 0

## 3. 변경 파일 목록

### 신규 (10)
- `app/migrations/m013_knowledge_vectors.py`
- `app/services/ai/vector/__init__.py`
- `app/services/ai/vector/embeddings.py` (~270줄)
- `app/services/ai/vector/store.py` (~190줄)
- `app/services/ai/vector/similarity.py` (~80줄)
- `tests/harness/vector_harness.py` (~150줄)
- `tests/test_ai_vector_harness.py` (~830줄, 36 tests)
- `docs/migrations_rollback/m013_rollback.sql`
- `reports/ai_dev_loop/18-5_test_report.md`
- `reports/ai_dev_loop/18-5_fix_summary.md`

### 수정 (4)
- `app/models/models.py` — `LargeBinary` import + `KnowledgeVector` ORM 클래스 append
- `app/services/ai/rag/schemas.py` — reason_code 6개 추가 (23 → 29)
- `app/services/ai/knowledge/indexer.py` — `ReindexResult` 8필드 + `reindex_all` keyword-only optional 인자 + `_embed_chunks_into_vectors` 신규 함수
- `tests/test_ai_manual_rag_harness.py` — reason_code 카운트 단언 23 → 29 갱신

> Codex M-1 후 revert: `dosu_clinic.spec` — 18-4 baseline 그대로 (변경 0).
> m013 마이그레이션은 spec line 95 의 glob 자동 등록으로 자동 포함됨.

### 무수정 (회귀 보호)
- `app/services/ai/manual_qa.py`
- `app/services/ai/rag/{pipeline,retriever,prompts,safety}.py`
- `app/services/ai/{provider,pii,sms_draft,action_leave}.py`
- `app/routers/ai.py`
- `app/migrations/m001~m012.py`
- `tests/conftest.py`
- `pyproject.toml`, `requirements.txt`
- **`dosu_clinic.spec`** (Codex M-1 후 revert — 18-4 baseline 그대로)

## 4. 변경 요약

`fix_summary.md` 의 요약 구조 그대로:
- m013 + KnowledgeVector ORM = vector 영속화 기반 (m012 패턴 동일)
- vector/ 3 모듈 = 추상 + factory + store + similarity (외부 SDK 의존 0)
- indexer 훅 = `embedding_provider=None` default → 18-4 호출자 회귀 0, provider 주입 시 batch embed + upsert + same_hash skip
- reason_code 6개 추가 (응답 노출은 18-7 m014 시점, 본 세션은 상수만)
- 36 신규 tests + 1 기존 테스트 카운트 갱신

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)

- `/api/ai/manual/{search,ask}` 응답 9키 / 3키 후방호환
- `manual_qa.ask_manual_question(provider_override=)` 시그니처
- `pii.scan(text)` 반환형
- `AiSetting`/`AiUsageLog` 기존 컬럼
- `app/migrations/m001~m012` diff 0
- `tests/conftest.py` 격리/SDK 차단 약화 X
- 18-0 safety / 18-3 chunker / 18-4 reindex 24개 + 12개 + 35개 테스트 100% 통과

→ **회귀 결과**: 모두 통과 (변경 후에도 18-4 baseline 313 passed 보존, vector 36개 + 갱신 1개 = 350 expected, 실측 349 passed (+1 차이는 갱신된 테스트가 같은 자리 유지)).

## 6. 실행한 테스트 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_ai_vector_harness.py -v
venv/Scripts/python.exe -m pytest tests/test_ai_reindex_harness.py tests/test_ai_chunker_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py tests/test_ai_full_harness.py -q
venv/Scripts/python.exe -m pytest tests --tb=short -q
venv/Scripts/python.exe -m ruff check app tests scripts
venv/Scripts/python.exe scripts/check_db_path.py
```

## 7. 테스트 결과 요약

**1회차** (spec 포함):

| 묶음 | 결과 |
|---|---|
| `test_ai_vector_harness.py` (신규 18-5) | 36 passed |
| 18-0~18-4 회귀 묶음 | 106 passed |
| **전체 tests** | 349 passed, 1 skipped, 7 xfailed |

**2회차** (Codex M-1 반영, spec revert 후 재실행):

| 묶음 | 결과 |
|---|---|
| `test_ai_vector_harness.py` (신규 18-5) | **36 passed** |
| 18-0~18-4 회귀 묶음 (chunker/reindex/manual_rag/safety/full/contract) | **106 passed** |
| **전체 tests** | **349 passed, 1 skipped, 7 xfailed, 27 warnings** |
| ruff (`app tests scripts`) | **All checks passed!** |
| check_db_path | OK (테스트 중 conftest 격리, vector test_18 통과) |

→ spec revert 가 hidden import (PyInstaller 빌드 영향) 만 제거 — pytest 결과 1회차와 동일.

baseline 비교:
- 18-4: 313 passed, 1 skipped, 7 xfailed
- 18-5: 349 passed (+36), 1 skipped, 7 xfailed (회귀 0)

## 8. 자동 수정 루프 횟수

**1/5 회차** (1회차에 모든 테스트 통과).

1회차 사이클:
- 코드 작성 → 테스트 실행 → 1 failure (test_indexer_no_delete_calls 가 docstring 라인을 잡음)
- 즉시 수정 (AST 검사 방식으로 변경) → 통과
- 18-2 reason_code 카운트 단언 (23 → 29 갱신) → 통과
- ruff 9 errors → 자동 fix + 수동 수정 → 통과
- 동일 1회차 안에서 마무리.

## 9. 5회 실패 여부

**아니오.** 1회차 통과.

## 10. 운영 DB 보호 검사 결과

```
$ venv/Scripts/python.exe scripts/check_db_path.py
[INFO] 운영 DB 경로가 감지되었습니다.
       이 스크립트가 운영 환경에서 단독으로 실행된 경우라면 정상입니다.
       (테스트 중에는 이 경로가 보이면 안 됩니다 — conftest.py 를 확인하세요.)
```
- 단독 실행 시 운영 경로 표시 (의도된 INFO).
- 테스트 중 격리는 `tests/conftest.py` 의 4단계 격리 + `tests/test_ai_vector_harness.py::test_18_does_not_use_operational_db` 통과로 입증.

## 11. RAG 하네스 결과

| 하네스 | 결과 |
|---|---|
| 18-0 RAG harness (full/safety/contract/manual_rag) | 통과 |
| 18-2 manual RAG (18 tests, reason_code 갱신 1개 포함) | 통과 |
| 18-3 chunker harness (35 tests) | 통과 |
| 18-4 reindex harness (24 tests) | 통과 |
| 18-5 vector harness (36 tests) | 통과 |

## 12. API 계약 테스트 결과 (응답 스키마 회귀)

`test_ai_manual_rag_contract.py` 9 passed. v1.3.3 응답 9키 / 3키 보존 — 라우터 / manual_qa / pipeline 모두 무수정.

## 13. 할루시네이션 금지 테스트 결과

`test_ai_safety_harness.py` 12 passed + `test_ai_hallucination.py` / `test_ai_sms_draft_hallucination.py` 통과 (전체 349 passed 에 포함).

## 14. PII 보호 테스트 결과

PII 관련 단언 통과. vector 패키지 입력은 chunker 산출물 (knowledge/manuals/* — 운영 PII 미포함).

API key 보호:
- `EmbeddingUnavailable.message` 는 kind 만 노출
- `_short_error()` 400자 컷
- `vector_disabled_reason` enum-like 문자열만
- 로그/예외에 api_key 변수 reference 0건

## 15. 기존 SMS AI 회귀 테스트 결과

`test_ai_sms_draft.py` / `test_ai_sms_validate.py` / `test_ai_sms_draft_hallucination.py` 통과 (전체 349 passed 에 포함, 18-4 baseline 그대로).

## 16. 기존 휴무 AI 회귀 테스트 결과

`test_ai_action_leave.py` 통과 (전체 349 passed 에 포함, 18-4 baseline 그대로).

## 17. 남은 위험 요소

1. **외부 OpenAIEmbeddingProvider 실제 구현 부재** — 본 세션은 SDK slot 만. 18-7 admin/router 시점에 실제 SDK 호출 추가.
2. **AiUsageLog 컬럼 미반영** — `embedding_called`, `skipped_embedding_reason`, `reason_code` 등 신규 컬럼은 m014 (18-7) 시점에 추가. 본 세션은 reason_code 상수만.
3. **circuit breaker 미구현** — `docs/ai_rag_migration_plan.md` §7 의 5분 차단은 18-6 hybrid 시점. 본 세션은 즉시 fallback (one-shot) 만.
4. **hybrid retriever 미구현** — vector store 는 만들었으나 keyword + vector 결합은 18-6.
5. **관리자 reindex 버튼 / UI 미구현** — 사용자 명시 금지. 18-7 admin/router 시점.
6. **`embedding_blob` 컬럼 미사용** — JSON 만 사용 (dim=16). 큰 dim 도입 시 BLOB 경로 활성화 결정 필요.
7. **PyInstaller spec hidden import 미추가** — Codex M-1 후 revert (사용자 본 세션 명시 금지). 실제 빌드 시점 (18-7/18-8 또는 사용자 승인 후) 별도 세션에서 vector/knowledge/rag 패키지 4+13개 명시 추가 필요. m013 마이그레이션은 glob 자동 등록 (line 95) 으로 영향 없음.
8. **18-6 query embedding 차단 통합 검증** — Codex 1회차 지적. 본 세션은 `is_embeddable_query()` helper 단위 검증만. 실제 retriever 파이프라인에서 짧은/invalid query 가 차단되는지는 18-6 통합 테스트에서 재검증.

## 18. Codex가 집중 검토할 파일

| 파일 | 이유 |
|---|---|
| `app/migrations/m013_knowledge_vectors.py` | idempotent / m012 패턴 정합성 |
| `app/models/models.py:KnowledgeVector` | UNIQUE 제약 + FK CASCADE / 컬럼 nullable 일관성 |
| `app/services/ai/vector/embeddings.py:get_embedding_provider` | 차단 우선순위 정확성 (local_only > disabled > api_key_missing > sdk_missing) |
| `app/services/ai/vector/store.py:upsert_vector` | content_hash skip 알고리즘 정확성 (chunk_harness 와 동일 sha256) |
| `app/services/ai/vector/similarity.py:cosine_similarity` | dimension mismatch 안전 fallback / 0 벡터 처리 |
| `app/services/ai/knowledge/indexer.py:_embed_chunks_into_vectors` | 18-4 회귀 0 / vector 실패가 reindex status 영향 0 / batch 실패 처리 |
| `tests/test_ai_vector_harness.py` | 사용자 21개 + Codex T-1/T-2 4개 + 추가 9개 = 36개 단언이 정확히 의도한 위반 케이스를 잡는지 |
| `dosu_clinic.spec` | RAG/Knowledge/Vector hidden import 누락 없음 |

## 19. Codex가 반드시 확인할 체크리스트

- [ ] m013 idempotent 입증 — 두 번 실행해도 안전, 테이블 부재 시 단독 호출도 raise X
- [ ] m001~m012 diff 0 (`git diff app/migrations/m001*.py app/migrations/m002*.py ... m012*.py`)
- [ ] FakeEmbeddingProvider 만 사용 (`grep -rE "from openai|import openai|from anthropic|import anthropic" app/services/ai/vector/`)
- [ ] `local_only` factory 차단 입증 — `test_T1_local_only_blocks_embedding_factory` 실행 결과 확인
- [ ] content_hash 비교 알고리즘 — `chunker.py:42 _sha256_hex` 와 `vector_harness.sha256_hex` 동일 (둘 다 `hashlib.sha256(text.encode("utf-8")).hexdigest()`)
- [ ] vector_disabled fallback 경로 — `test_12_provider_error_keyword_fallback` 가 keyword 검색 정상 동작 확인
- [ ] API key / embedding key 로그 부재 — `grep -rE "api_key" app/services/ai/vector/` 로 검색해 노출 없음 확인
- [ ] 응답 키 후방호환 — `app/routers/ai.py` / `app/services/ai/manual_qa.py` / `app/services/ai/rag/pipeline.py` 18-2 통과본 그대로 (diff 0)
- [ ] `pyproject.toml` 무수정
- [ ] `requirements.txt` 무수정
- [ ] **`dosu_clinic.spec` 무수정** (Codex M-1 후 revert — `git diff dosu_clinic.spec` 0)
- [ ] eval 점수 표 (vector ON/OFF) — 본 세션 범위는 단위 검증만, eval 측정은 18-7 머지 직전 결정 (18-5 통과 OK)

## 20. 다음 세션으로 넘어가도 되는지 자체 판단

**yes** — 18-6 (hybrid retriever) 진입 OK (Codex 1회차 M-1 반영 후).

근거:
1. 사용자 21개 단언 + Codex T-1/T-2 보강 4개 + 추가 11개 = 36 vector tests 100% 통과
2. 18-4 baseline (313 passed) 그대로 + 36 신규 = 349 passed (회귀 0)
3. ruff 0 error, check_db_path 통과
4. m013 idempotent / 단독 호출 안전 (m012 패턴 100%)
5. 외부 OpenAI/Anthropic embedding 호출 0 입증 (AST grep + factory 차단 + conftest SDK 차단)
6. v1.3.3 manual/ask 응답 9키 후방호환 보존 (라우터/manual_qa/pipeline 무수정)
7. 1회차 통과 (5회 미만, Codex M-1 반영 후 2회차도 동일 결과)
8. **Codex 1회차 M-1 (`dosu_clinic.spec` 변경) 즉시 revert — 사용자 본 세션 "PyInstaller spec 수정 금지" 100% 준수**
9. 사용자 명시 금지 사항 (hybrid/UI/관리자 버튼/응답 키 변경/외부 SDK 호출/m001~m012 수정/conftest 약화/spec 수정) 모두 0건

위험 요소(§17) 8개 중:
- 1~3 은 18-6/18-7 에서 처리 예정 — 본 세션 범위가 의도적으로 좁게 설계됨
- 4·5 는 별도 세션
- 6 은 dim>64 도입 시 결정
- **7 (spec hidden import)** 은 18-7/18-8 또는 사용자 승인된 빌드 세션에서 명시 추가
- **8 (query embedding 차단 통합 검증)** 은 18-6 retriever 통합 시 재검증

미해결 잔여:
- `tests/test_ai_sms_validate.py` 의 tuple return 27개 warning (18-4 baseline 그대로, 18-5 와 무관)
- 운영 환경에서의 실제 OpenAIEmbeddingProvider SDK 연동 (18-7 권고)
- Codex 1회차 환경의 pytest tmp_path 권한 에러 — Codex 환경 이슈 (Claude Code 환경에서는 349 passed 완주 확인). 향후 Codex 환경 보강 권고.
