# 18-6 Fix Summary — Hybrid Retriever (α/β + cache 게이트)

## 작업 목표 (사용자 지시문 그대로)

- keyword search 결과와 vector search 결과를 결합하는 hybrid retriever 구현
- 중복 chunk 제거
- keyword_score, vector_score, final_score 계산
- low_confidence 판단 시 LLM 호출 차단
- vector disabled / provider error 시 keyword fallback
- local_only / local_first / ai_assist 모드별 안전 처리
- 기존 manual RAG / safety / full / chunker / reindex / vector 하네스 유지

## 변경 파일 목록

### 신규 (5 코드 + 3 리포트)

| 파일 | 줄 | 역할 |
|---|---|---|
| `app/services/ai/rag/reranker.py` | ~245 | α/β 가중 결합 + max-normalize + chunk_id/path dedup + 정렬 |
| `app/services/ai/rag/confidence.py` | ~230 | should_call_llm 게이트 + reason_code 우선순위 + confidence 매핑 |
| `tests/harness/hybrid_harness.py` | ~265 | factory + seed_chunk_with_vector + 단언 helper + 결정성 단언 |
| `tests/test_hybrid_retriever.py` | ~580 | reranker 11 + confidence 13 + integration 16 + 우선순위 2 + LLM 차단 4 = **46 tests** |
| `tests/test_ai_assist_mode.py` | ~290 | local_only/local_first/ai_assist 모드별 호출 카운트 = **15 tests** |
| `reports/ai_dev_loop/18-6_test_report.md` | — | 테스트 결과 보고 |
| `reports/ai_dev_loop/18-6_fix_summary.md` | — | 본 파일 |
| `reports/ai_dev_loop/18-6_codex_review_request.md` | — | Codex 검증 요청서 |

### 수정 (1)

| 파일 | 변경 내용 |
|---|---|
| `app/services/ai/rag/retriever.py` | `hybrid_retrieve()` + `HybridResult` dataclass 추가 (~210줄). 기존 `keyword_retrieve` / `to_sources` / `retrieve` (stub) 무수정 — 회귀 0. |

### 무수정 (회귀 보호 — diff 0)

- `app/services/ai/manual_qa.py`
- `app/services/ai/rag/{pipeline,prompts,safety,schemas}.py` (schemas reason_code 29개 그대로)
- `app/services/ai/{provider,pii,sms_draft,action_leave,ai_logging,date_resolver,validators}.py`
- `app/services/ai/vector/{__init__,embeddings,store,similarity}.py` (18-5 무수정)
- `app/services/ai/knowledge/{indexer,chunker,loader,normalizer,keyword_index,__init__}.py`
- `app/routers/ai.py`
- `app/migrations/m001~m013.py` (신규 m014 미생성 — 본 세션 명시 금지)
- `app/models/models.py` (KnowledgeChunk/KnowledgeVector 그대로, AiSetting 컬럼 추가 X)
- `tests/conftest.py` (격리 / FakeProvider / SDK 차단 무수정)
- `tests/harness/{fake_provider,rag_harness,vector_harness,reindex_harness,safety_harness,contract,db_guard,seed_data,helpers}.py`
- `pyproject.toml`, `requirements.txt`, `dosu_clinic.spec`, `pytest.ini`

## 의도/이유

### 1. reranker — α/β 정규화 가중 결합

**왜 max-normalize?**
- raw 점수: keyword token-intersection (0~10), vector cosine (-1~1).
- 단순 가중합 시 keyword 값이 항상 vector 값을 압도 (스케일 불일치).
- max-normalize 로 둘 다 [0, 1] 동일 척도화 후 가중합 → α/β 가 의미 있는 튜닝 변수.

**왜 chunk_id 우선 dedup?**
- vector hit 은 항상 KnowledgeChunk.id 보유.
- keyword hit 은 document 단위 → chunk_id 부재 → source_path 로 dedup.
- 같은 path 가 keyword + vector 양쪽에서 hit → 1건으로 merge,
  vector 의 chunk_id/heading/chunk_index 가 더 구체적이라 채워짐.
- search_mode "hybrid" 표시.

**왜 음의 cosine clamp?**
- 음의 유사도는 "무관" 또는 "반대" 의미 — 결과로 노출할 가치 없음.
- 0 으로 clamp 후 정규화 — UI/응답에서 음수 final_score 절대 부재.

### 2. confidence — should_call_llm 단일 진실원천

**왜 단일 진실원천?**
- LLM 호출 차단 게이트가 manual_qa.py / pipeline.py / hybrid_retrieve 여러 곳에
  분산되면 누수 위험. 하나의 함수가 모든 차단 케이스 + 우선순위 매핑.
- 18-7 admin/router 통합 시 같은 게이트 사용 → 일관성.

**왜 우선순위 명시?**
- docs/ai_rag_error_codes.md §5 표 그대로 코드화.
- 동시 발급 시 응답 reason_code 1개만 노출 — 우선순위 표가 자명.
- primary_reason_code() 함수가 표를 source of truth 로 사용.

**왜 LLM_CALL_THRESHOLD = LOW_THRESHOLD?**
- 두 임계가 다르면 디버깅 어려움 ("low confidence 인데 LLM 호출됐다?").
- "confidence unknown 이면 LLM 차단" 단일 룰.
- 운영 튜닝은 두 임계 동시 조정 (LOW_THRESHOLD = LLM_CALL_THRESHOLD).

### 3. hybrid_retrieve — 항상 keyword 먼저, vector 는 옵션

**왜 keyword 먼저?**
- 회귀 보호: hybrid OFF / vector 부재 / vector 실패 시 keyword 단독 결과 보장.
- vector 단계에서 어떤 예외든 catch → keyword 결과로 fallback.
- 검색이 "전체 중단" 되는 분기 0.

**왜 hybrid_enabled 기본 OFF?**
- 사용자 명시 금지: "hybrid 기본 ON 출시 금지".
- 18-7 m014 에서 AiSetting 컬럼으로 운영 토글.
- 18-6 시점은 코드 path 만 — 라우터 통합 X.

**왜 local_only 사전 차단?**
- 사용자 요구: "local_only → vector/LLM 호출 0".
- factory 차단 (vector 패키지의 get_embedding_provider) + retriever 차단
  (본 모듈) — 이중 보호.
- raise_on_call=True FakeEmbeddingProvider 로 실수 호출 시 RuntimeError 단언.

### 4. tests/harness/hybrid_harness.py

**왜 별도 harness?**
- 다른 RAG harness (rag_harness, vector_harness) 와 분리 — 18-6 책임 명확.
- factory + seed helper + 단언 helper 한 곳에 집약 — 재사용성.
- assert_retriever_deterministic — 같은 query 두/세 번 호출해 결과 동일성 단언.

**왜 seed_chunk_with_vector?**
- vector_harness.seed_chunks_for_vector_test 와 유사하지만, embedding_provider
  주입 시 KnowledgeChunk + KnowledgeVector 동시 INSERT.
- chunker 호출 0 (test 격리).
- 테스트가 "chunk + vector 가 있는 상태" 를 1줄로 시드 가능.

## 테스트 통과 요약

```
tests/test_hybrid_retriever.py    : 46 passed
tests/test_ai_assist_mode.py      : 15 passed
회귀 묶음 (12 파일)               : 166 passed
전체 tests                        : 410 passed, 1 skipped, 7 xfailed, 27 warnings
ruff (app tests scripts)         : All checks passed!
check_db_path                    : OK (테스트 중 격리, 단독 실행은 의도된 INFO)
```

baseline:
- 18-5: 349 passed
- 18-6: 410 passed (+61, 회귀 0)

## 사용자 명시 금지 준수 (모두 0건)

| 금지 | 위반 0 |
|---|---|
| 실제 외부 LLM API 연동 | ✅ 0 |
| 실제 외부 embedding API 연동 | ✅ 0 (FakeEmbeddingProvider 만) |
| 관리자 UI 구현 | ✅ 0 |
| reindex 버튼 구현 | ✅ 0 |
| 새 DB 테이블 또는 migration 생성 | ✅ 0 (m013 까지 그대로) |
| requirements.txt 수정 | ✅ 0 |
| PyInstaller spec 수정 | ✅ 0 |
| 기존 API 응답 key 변경 | ✅ 0 (응답 9키 + 3키 그대로) |
| 하네스/테스트 약화 | ✅ 0 |
| 운영 DB 접근 | ✅ 0 (격리 DB) |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 0 (action_leave / sms_draft 무수정) |
| `manual60` count_increment 되돌리기 | ✅ 0 (해당 없음) |
| `pyproject.toml` per-file-ignores 풀기 | ✅ 0 |

## 자체 판단

✅ **다음 세션 (18-7 admin/router) 진입 OK** — Codex 검증 후 진입.

근거:
1. 신규 61 tests + 18-5 baseline 349 = 410 passed (회귀 0)
2. ruff 0 error, check_db_path 통과
3. 결정성 / 정규화 / dedup / fallback / mode gate 모두 단언 통과
4. v1.3.3 응답 9키 후방호환 보존 (manual_qa / pipeline / 라우터 무수정)
5. 외부 LLM/Embedding 실제 호출 0 (FakeProvider/FakeEmbeddingProvider + SDK 차단)
6. 사용자 명시 금지 13 항목 0 위반
7. 1회차 통과 (5회 미만)
