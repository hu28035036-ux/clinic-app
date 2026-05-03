# 18-6 Codex 검증 요청서

## 1. 세션 이름

**18-6_hybrid_retriever** — keyword + vector 결합 retriever / reranker / confidence
구현 + LLM 호출 게이트 + local_only/local_first/ai_assist 모드 안전 처리.

## 2. 작업 목표

- keyword + vector 결과를 결합하는 hybrid retriever 구현 (`hybrid_retrieve`)
- α/β 정규화 가중 결합 (`reranker.combine`)
- chunk_id / source_path 기준 dedup
- `should_call_llm` 게이트 — final_score 임계 미만 / no_sources / local_only / pii / provider_disabled 시 LLM 호출 차단
- vector disabled / provider error 시 keyword fallback
- local_only / local_first / ai_assist 모드별 안전 처리
- 기존 manual RAG / safety / full / chunker / reindex / vector 하네스 회귀 0
- AI_RAG_HYBRID_ENABLED 기본 OFF (사용자 명시 금지: hybrid 기본 ON 출시 X)

## 3. 변경 파일 목록

### 신규 (5 코드 + 3 리포트)
- `app/services/ai/rag/reranker.py` (~245줄) — α/β + dedup + 정규화
- `app/services/ai/rag/confidence.py` (~230줄) — should_call_llm + 우선순위
- `tests/harness/hybrid_harness.py` (~265줄) — fixture + 단언 helper
- `tests/test_hybrid_retriever.py` (~580줄, 46 tests)
- `tests/test_ai_assist_mode.py` (~290줄, 15 tests)
- `reports/ai_dev_loop/18-6_test_report.md`
- `reports/ai_dev_loop/18-6_fix_summary.md`
- `reports/ai_dev_loop/18-6_codex_review_request.md` (본 파일)

### 수정 (1)
- `app/services/ai/rag/retriever.py` — `hybrid_retrieve()` + `HybridResult`
  추가 (~210줄). 기존 함수/stub 무수정 (회귀 0).

### 무수정 (회귀 보호)
- `app/services/ai/manual_qa.py`
- `app/services/ai/rag/{pipeline,prompts,safety,schemas}.py`
- `app/services/ai/{provider,pii,sms_draft,action_leave}.py`
- `app/services/ai/vector/{embeddings,store,similarity,__init__}.py`
- `app/services/ai/knowledge/{indexer,chunker,loader,normalizer,keyword_index}.py`
- `app/routers/ai.py`
- `app/migrations/m001~m013.py` (m014 미생성)
- `app/models/models.py`
- `tests/conftest.py`
- `pyproject.toml`, `requirements.txt`, `dosu_clinic.spec`

## 4. 변경 요약

| 모듈 | 책임 | 핵심 함수 |
|---|---|---|
| `rag/reranker.py` | α/β 가중 결합 + dedup + 정규화 | `combine`, `combine_with_stats`, `HybridHit` |
| `rag/confidence.py` | LLM 호출 게이트 + reason_code 우선순위 | `should_call_llm`, `compute_confidence`, `primary_reason_code`, `normalize_mode`, `blocked_reason_for` |
| `rag/retriever.py` (수정) | hybrid 진입점 + keyword/vector 결합 + fallback | `hybrid_retrieve`, `HybridResult` (기존 `keyword_retrieve` / `to_sources` / `retrieve` stub 무수정) |

알고리즘 핵심:
1. **정규화**: keyword (token-intersection) 와 vector (cosine) 를 max-normalize 로
   각각 [0, 1] 동일 척도화 후 가중합 — raw score 직결합 금지.
2. **dedup key**: chunk_id 우선, 없으면 source_path. 같은 path 가 keyword +
   vector 양쪽에서 hit → 1건으로 merge (vector 의 chunk_id/heading 더 구체적).
3. **fallback**: vector 단계 어떤 실패든 catch → keyword 결과로 fallback.
   reason_code 만 표시, 검색 자체 중단 0.
4. **local_only**: factory 차단 + retriever 차단 이중 보호 — embedding 호출 0.

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)

- `/api/ai/manual/{search,ask}` 응답 9키 / 3키 후방호환 → 라우터/manual_qa/pipeline 무수정
- `manual_qa.ask_manual_question(provider_override=)` 시그니처
- `pii.scan(text)` 반환형
- `AiSetting`/`AiUsageLog` 기존 컬럼
- `app/migrations/m001~m013` diff 0
- `tests/conftest.py` 격리/SDK 차단 약화 X
- 18-0 safety / 18-3 chunker / 18-4 reindex / 18-5 vector tests 100% 통과

→ **회귀 결과**: 18-5 baseline 349 passed → 18-6 410 passed (+61, 회귀 0).

## 6. 실행한 테스트 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_hybrid_retriever.py tests/test_ai_assist_mode.py -v
venv/Scripts/python.exe -m pytest tests/test_hybrid_retriever.py tests/test_ai_assist_mode.py tests/test_local_only_mode.py tests/test_full_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py tests/test_ai_full_harness.py tests/test_rag_pipeline.py tests/test_rag_safety.py tests/test_ai_chunker_harness.py tests/test_ai_reindex_harness.py tests/test_ai_vector_harness.py -q
venv/Scripts/python.exe -m pytest tests --tb=short -q
venv/Scripts/python.exe -m ruff check app tests scripts
venv/Scripts/python.exe scripts/check_db_path.py
```

## 7. 테스트 결과 요약

| 묶음 | 결과 |
|---|---|
| `test_hybrid_retriever.py` (신규 18-6) | **46 passed** |
| `test_ai_assist_mode.py` (신규 18-6) | **15 passed** |
| 18-0~18-5 회귀 묶음 (12 파일) | **166 passed** |
| **전체 tests** | **410 passed, 1 skipped, 7 xfailed, 27 warnings** |
| ruff (`app tests scripts`) | **All checks passed!** |
| check_db_path | OK (테스트 중 격리, 단독 실행 INFO 의도) |

baseline:
- 18-5: 349 passed, 1 skipped, 7 xfailed
- 18-6: 410 passed (+61), 1 skipped, 7 xfailed

## 8. 자동 수정 루프 횟수

**1/5 회차** — 1회차에 모든 테스트 통과.

1회차 사이클:
- 코드 작성 → 신규 61 tests 100% 통과 (failure 0)
- ruff 9 errors (모두 자동 fix: 미사용 import + import 정렬) → `--fix` → 통과
- 회귀 묶음 227 tests 100% 통과
- 전체 410 tests 100% 통과

## 9. 5회 실패 여부

**아니오.** 1회차 통과.

## 10. 운영 DB 보호 검사 결과

```
$ venv/Scripts/python.exe scripts/check_db_path.py
DOSU_DB_PATH 환경변수 : (없음)
APPDATA 환경변수      : C:\Users\user\AppData\Roaming
결정된 DB 경로        : C:\Users\user\AppData\Roaming\도수치료예약\clinic.db

[INFO] 운영 DB 경로가 감지되었습니다.
       (테스트 중에는 이 경로가 보이면 안 됩니다 — conftest.py 를 확인하세요.)
```

- 단독 실행 시 운영 경로 표시 (의도된 INFO).
- 테스트 중 격리는 `tests/conftest.py` 4단계 격리 + `test_hybrid_does_not_use_operational_db` 통과로 입증.

## 11. RAG 하네스 결과

| 하네스 | 결과 |
|---|---|
| 18-0 RAG harness (full/safety/contract/manual_rag) | 통과 |
| 18-2 manual RAG (18 tests) | 통과 |
| 18-3 chunker harness (35 tests) | 통과 |
| 18-4 reindex harness (24 tests) | 통과 |
| 18-5 vector harness (36 tests) | 통과 |
| 18-6 hybrid harness (46 tests) | **통과 (신규)** |
| 18-6 ai_assist mode (15 tests) | **통과 (신규)** |

## 12. API 계약 테스트 결과 (응답 스키마 회귀)

`test_ai_manual_rag_contract.py` 9 passed. v1.3.3 응답 9키 / 3키 보존 — 라우터 / manual_qa / pipeline 모두 무수정.

## 13. 할루시네이션 금지 테스트 결과

`test_ai_safety_harness.py` 12 passed + `test_ai_hallucination.py` /
`test_ai_sms_draft_hallucination.py` 통과 (전체 410 passed 에 포함).

## 14. PII 보호 테스트 결과

- PII 관련 단언 통과.
- hybrid_retrieve / reranker / confidence 모듈은 PII 비의존 (검색만, 외부 전송 X).
- 예외 catch 시 메시지/traceback 어떤 응답에도 노출 안 함.
- API key 변수 reference 0건 (`grep -rE "api_key" app/services/ai/rag/` 0).

## 15. 기존 SMS AI 회귀 테스트 결과

`test_ai_sms_draft.py` / `test_ai_sms_validate.py` / `test_ai_sms_draft_hallucination.py` 통과 (전체 410 passed 포함).

## 16. 기존 휴무 AI 회귀 테스트 결과

`test_ai_action_leave.py` 통과 (전체 410 passed 포함).

## 17. 남은 위험 요소

1. **AiSetting 컬럼 `AI_RAG_HYBRID_ENABLED` / `alpha` / `beta` 미반영** — 본 세션은 함수 인자로만. 18-7 m014 시점에 컬럼 + admin UI.
2. **응답 노출 미통합** — `reason_code` / `embedding_called` / `ai_mode` / `prompt_version` 응답 키 추가는 18-7. 본 세션은 retriever HybridResult 내부에서만.
3. **manual_qa / pipeline 미통합** — `pipeline.run_manual_ask` 가 아직 keyword 만 사용 (18-2 동작 그대로). 18-7 에서 hybrid_retrieve 로 전환 결정.
4. **circuit breaker 미구현** — 일시 vector 장애가 이후 호출까지 5분 차단하는 로직 18-7.
5. **eval 점수 표 미측정** — hybrid ON vs vector ON vs keyword-only 비교는 18-7 머지 직전.
6. **PyInstaller spec hidden import 미추가** — 사용자 본 세션 명시 금지. `app.services.ai.rag.reranker` / `confidence` 두 신규 모듈 hidden import 추가는 18-7/18-8 또는 사용자 승인된 빌드 세션.
7. **m014 미생성** — `AiSetting` α/β/flag 컬럼 + `AiUsageLog.search_mode` / `embedding_called` 컬럼 추가는 18-7.

## 18. Codex가 집중 검토할 파일

| 파일 | 이유 |
|---|---|
| `app/services/ai/rag/reranker.py:combine` | α/β 정규화 알고리즘 정확성 (raw score 직결합 금지 / chunk_id+path dedup / 음수 cosine clamp) |
| `app/services/ai/rag/confidence.py:should_call_llm` | LLM 차단 게이트 우선순위 — provider_disabled > pii > local_only > no_sources > low_confidence |
| `app/services/ai/rag/confidence.py:primary_reason_code` | docs/ai_rag_error_codes.md §5 우선순위 표 정합성 |
| `app/services/ai/rag/retriever.py:hybrid_retrieve` | hybrid OFF=keyword 동등 / vector 실패 fallback / local_only 차단 / 결정성 |
| `app/services/ai/rag/retriever.py:_vector_path` | embedding 호출 → vector_store → similarity 흐름 / 예외 catch 정확성 |
| `tests/test_hybrid_retriever.py` | 46개 단언이 의도한 위반 케이스를 잡는지 |
| `tests/test_ai_assist_mode.py` | 15개 모드별 호출 카운트 단언이 외부 호출 0 정확 입증 |
| `tests/harness/hybrid_harness.py:seed_chunk_with_vector` | chunk + vector 동시 INSERT 가 KnowledgeChunk/KnowledgeVector 정합성 보존 |

## 19. Codex가 반드시 확인할 체크리스트

- [ ] `reranker.combine` 이 raw score 직결합이 아닌 max-normalize 후 결합하는지
      (`test_reranker_combine_alpha_beta_weighted` 가 정확히 0.8 / 0.7 단언)
- [ ] dedup key = chunk_id 우선, source_path fallback 구현 정합 (test_reranker_dedup_by_*)
- [ ] hybrid OFF (`hybrid_enabled=False`) → keyword-only 와 결과 동등
      (`test_hybrid_disabled_equals_keyword_only` 가 raw_paths == hybrid_paths 단언)
- [ ] vector 실패 시 keyword fallback (`test_hybrid_provider_error_falls_back_to_keyword` 가
      `vector_failed=True` + `effective_mode="keyword"` + hits>=1 단언)
- [ ] `local_only` 에서 retriever 가 vector 경로 시도 0
      (`test_hybrid_local_only_blocks_vector_path` + `raise_on_call=True` FakeEmbeddingProvider 가 raise 안 함 입증)
- [ ] `should_call_llm` 우선순위가 docs/ai_rag_error_codes.md §5 표와 동일
      (`test_confidence_priority_provider_disabled_over_pii` 등)
- [ ] final_score 임계와 confidence 모듈 임계 일관 정의
      (`LLM_CALL_THRESHOLD == LOW_THRESHOLD` 단일 값)
- [ ] `hybrid_retrieve` 가 어떤 분기에서도 외부 LLM 호출 0
      (`test_hybrid_does_not_call_llm_provider` 가 FakeProvider 호출 0 단언)
- [ ] 응답 키 후방호환 — `app/routers/ai.py` / `app/services/ai/manual_qa.py` /
      `app/services/ai/rag/pipeline.py` diff 0 (`git diff` 확인)
- [ ] `pyproject.toml` 무수정
- [ ] `requirements.txt` 무수정
- [ ] **`dosu_clinic.spec` 무수정** (`git diff dosu_clinic.spec` 0)
- [ ] m001~m013 무수정 (`git diff app/migrations/m0*.py` 0)
- [ ] eval 점수 표 (hybrid ON/OFF) — 본 세션 범위는 단위 검증만, eval 측정은 18-7 머지 직전 결정 (18-6 통과 OK)

## 20. 다음 세션으로 넘어가도 되는지 자체 판단

**yes** — 18-7 (admin/router 통합) 진입 OK.

근거:
1. 신규 61 tests + 18-5 baseline 349 = 410 passed (회귀 0)
2. ruff 0 error, check_db_path 통과
3. α/β 정규화 / chunk_id+path dedup / vector fallback / local_only 차단 / 결정성 / LLM 호출 차단 모두 단언 통과
4. v1.3.3 응답 9키 후방호환 보존 (라우터/manual_qa/pipeline 무수정)
5. 외부 LLM/Embedding 실제 호출 0 (FakeProvider/FakeEmbeddingProvider + SDK 차단 + raise_on_call=True 입증)
6. 1회차 통과 (5회 미만)
7. 사용자 명시 금지 13 항목 0 위반 (외부 API/UI/reindex 버튼/migration/requirements/spec/응답 키/하네스 약화/운영 DB/SMS·휴무 AI 변경)

위험 요소(§17) 7개 중:
- 1~5 는 18-7 admin/router 시점 처리 — 본 세션 범위가 의도적으로 좁게 설계됨
- **6 (spec hidden import)** 는 사용자 본 세션 명시 금지. 18-7/18-8 또는 사용자 승인된 빌드 세션에서 `app.services.ai.rag.reranker` + `app.services.ai.rag.confidence` 두 모듈 명시 추가 필요. m014 도 동일.
- **7 (m014 미생성)** 는 본 세션 명시 금지 — 18-7 admin/router 에서 추가.

미해결 잔여:
- `tests/test_ai_sms_validate.py` 의 tuple return 27개 warning (18-4/18-5 baseline 그대로, 18-6 무관)
- Codex 1회차 환경에서 pytest tmp_path 권한 에러 (18-5 Codex 보고된 환경 이슈) — Claude Code 환경에서는 410 passed 완주 확인.
