# 18-6 Test Report — Hybrid Retriever (α/β + cache 게이트)

## 1. 세션 이름

**18-6_hybrid_retriever** — keyword + vector 결합 retriever / reranker / confidence
구현 + LLM 호출 게이트 + local_only/local_first/ai_assist 모드 안전 처리.

## 2. 환경

- 작업 디렉토리: `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리`
- 브랜치: `ai-rag-v1-integration`
- Python: 3.12.10 (`venv\Scripts\python.exe`)
- pytest: 8.4.2
- ruff: latest
- 격리 DB: `tests/temp/test_clinic_<uuid>.db` (운영 DB 미사용)

## 3. 실행 명령

```
venv\Scripts\python.exe -m pytest tests/test_hybrid_retriever.py tests/test_ai_assist_mode.py -v
venv\Scripts\python.exe -m pytest tests/test_hybrid_retriever.py tests/test_ai_assist_mode.py tests/test_local_only_mode.py tests/test_full_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py tests/test_ai_full_harness.py tests/test_rag_pipeline.py tests/test_rag_safety.py tests/test_ai_chunker_harness.py tests/test_ai_reindex_harness.py tests/test_ai_vector_harness.py -q
venv\Scripts\python.exe -m pytest tests --tb=short -q
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
```

## 4. 결과 요약

| 묶음 | 결과 |
|---|---|
| `test_hybrid_retriever.py` (신규 18-6) | **46 passed** |
| `test_ai_assist_mode.py` (신규 18-6) | **15 passed** |
| 18-0~18-5 회귀 묶음 (12 파일, 166 테스트) | **166 passed** |
| **전체 tests** | **410 passed, 1 skipped, 7 xfailed, 27 warnings** |
| ruff (`app tests scripts`) | **All checks passed!** |
| check_db_path | OK (테스트 중 격리, 단독 실행은 의도된 INFO) |

baseline 비교:
- 18-5: 349 passed, 1 skipped, 7 xfailed
- 18-6: 410 passed (+61), 1 skipped, 7 xfailed (회귀 0)

## 5. 신규 테스트 분류 (61개)

### 5-1. `test_hybrid_retriever.py` (46 tests)

#### reranker 단위 (11 tests)
- combine — keyword only / vector only / α-β 가중합
- dedup — chunk_id / source_path / keyword 내 중복 / chunk_id 내 중복
- 음의 cosine score clamp
- 모든 score=0 division-by-zero 회피
- α/β 변경 시 순위 변화 결정성
- combine_with_stats collision 카운트
- 빈 입력

#### confidence 단위 (13 tests)
- compute_confidence — high/low/unknown 임계
- should_call_llm — no_sources / low_confidence / local_only /
  provider_disabled / pii / pass / local_first default / 우선순위
- normalize_mode / is_valid_mode
- primary_reason_code 우선순위
- blocked_reason_for v1.3.3 호환

#### hybrid_retrieve 통합 (16 tests)
- hybrid_disabled = keyword-only 동등 (회귀 0)
- hybrid_disabled + embedding_provider 주입 — 호출 0
- embedding_provider=None / db=None — vector_disabled fallback
- vector path 활성 — hybrid 결과 + dedup
- vector only hit — keyword 0건 케이스
- dedup chunk_id 누락 0
- local_only — vector 경로 차단
- provider_error — keyword fallback + reason='provider_error'
- 짧은 query / 빈 query
- 결정성 (3 runs 동일)
- α/β 변경 결정적
- LLM provider 호출 0 (모든 경로)
- 기존 manual_qa 회귀 0
- keyword_retrieve 회귀 0
- 운영 DB 미사용

#### reason_code 우선순위 (2 tests)
- invalid_query > pii > provider_disabled > ... > vector_disabled
- 미지정 코드 fallback

#### Low confidence → LLM 차단 (2 tests)
- final_score < threshold → should_call_llm=False
- final_score >= threshold → should_call_llm=True

### 5-2. `test_ai_assist_mode.py` (15 tests)

- local_only — embedding 호출 0 / LLM 호출 0 / keyword 경로만 동작
- local_first — high score allows LLM, low score blocks, vector path active
- ai_assist — high allows LLM, no_sources blocks, low_score blocks,
  provider_disabled blocks
- 모드 무관 hybrid OFF 동작 동일
- local_only reason_code = embedding_skipped_local_only
- 3 모드 retriever LLM 호출 0
- 기존 manual_qa 회귀 0 (모드 모듈 import 무영향)
- local_only 라도 manual_search 정상

## 6. 변경 파일 목록

### 신규 (5)
- `app/services/ai/rag/reranker.py` (~245줄) — α/β + dedup + 정규화
- `app/services/ai/rag/confidence.py` (~230줄) — should_call_llm + 우선순위
- `tests/harness/hybrid_harness.py` (~265줄) — fixture + factory + 단언 helper
- `tests/test_hybrid_retriever.py` (~580줄, 46 tests)
- `tests/test_ai_assist_mode.py` (~290줄, 15 tests)
- `reports/ai_dev_loop/18-6_test_report.md` (본 파일)
- `reports/ai_dev_loop/18-6_fix_summary.md`
- `reports/ai_dev_loop/18-6_codex_review_request.md`

### 수정 (1)
- `app/services/ai/rag/retriever.py` — `hybrid_retrieve()` + `HybridResult` /
  `HybridHit` re-export 추가. 기존 `keyword_retrieve` / `to_sources` /
  `retrieve` (stub) 무수정 (회귀 0).

### 무수정 (회귀 보호)
- `app/services/ai/manual_qa.py`
- `app/services/ai/rag/{pipeline,prompts,safety,schemas}.py`
- `app/services/ai/{provider,pii,sms_draft,action_leave}.py`
- `app/services/ai/vector/{__init__,embeddings,store,similarity}.py`
- `app/services/ai/knowledge/{indexer,chunker,loader,normalizer,keyword_index}.py`
- `app/routers/ai.py`
- `app/migrations/m001~m013.py`
- `app/models/models.py`
- `tests/conftest.py`
- `tests/harness/{fake_provider,rag_harness,vector_harness,reindex_harness,safety_harness,contract,db_guard,seed_data,helpers}.py`
- `pyproject.toml`, `requirements.txt`, `dosu_clinic.spec`

## 7. 자동 수정 루프 횟수

**1/5 회차** — 1회차에 모든 테스트 통과.

1회차 사이클:
- 코드 작성 → 신규 61 tests 100% 통과 (failure 0)
- ruff 9 errors (모두 자동 fix 가능: 미사용 import, import 정렬) → `--fix` 자동 정리 → 통과
- 회귀 묶음 227 tests 100% 통과
- 전체 410 tests 100% 통과 (1 skipped, 7 xfailed 18-5 baseline 그대로)

## 8. 5회 실패 여부

**아니오.** 1회차 통과.

## 9. 운영 DB 보호 검사 결과

```
$ venv/Scripts/python.exe scripts/check_db_path.py
DOSU_DB_PATH 환경변수 : (없음)
APPDATA 환경변수      : C:\Users\user\AppData\Roaming
결정된 DB 경로        : C:\Users\user\AppData\Roaming\도수치료예약\clinic.db

[INFO] 운영 DB 경로가 감지되었습니다.
       이 스크립트가 운영 환경에서 단독으로 실행된 경우라면 정상입니다.
       (테스트 중에는 이 경로가 보이면 안 됩니다 — conftest.py 를 확인하세요.)
```

- 단독 실행 시 운영 경로 표시 (의도된 INFO).
- 테스트 중 격리는 `tests/conftest.py` 의 4단계 격리 + `test_hybrid_does_not_use_operational_db` 통과로 입증.

## 10. 핵심 단언 결과

| 항목 | 결과 |
|---|---|
| α/β 변경 시 순위 변화 결정적 | ✅ test_reranker_alpha_beta_change_changes_ranking |
| dedup 누락 0 (chunk_id / source_path) | ✅ test_reranker_dedup_by_chunk_id / _by_source_path |
| hybrid OFF = keyword-only 회귀 0 | ✅ test_hybrid_disabled_equals_keyword_only |
| vector 실패 → keyword fallback | ✅ test_hybrid_provider_error_falls_back_to_keyword |
| local_only → embedding 호출 0 | ✅ test_local_only_blocks_embedding_factory |
| final_score 임계 미만 → LLM 차단 | ✅ test_hybrid_low_final_score_should_not_call_llm |
| 결정성 (3 runs 동일) | ✅ test_hybrid_deterministic_same_query_same_result |
| 외부 LLM 호출 0 | ✅ test_hybrid_does_not_call_llm_provider |
| 외부 Embedding 호출 0 (local_only/disabled/short query) | ✅ assert_no_embedding_call 단언 통과 |
| 응답 키 후방호환 | ✅ test_existing_manual_qa_unaffected_by_hybrid_module |

## 11. 외부 API 호출 차단 검증

- 본 세션의 모든 vector 경로는 FakeEmbeddingProvider 만 사용.
- LLM provider 는 모든 hybrid_retrieve 호출에서 `len(provider.calls) == 0`.
- conftest `_block_sdk_modules` 가 openai/anthropic SDK 클래스를 raise stub 으로
  교체 — 실수 호출 시도 자체가 RuntimeError.
- `raise_on_call=True` FakeEmbeddingProvider 로 호출 시 RuntimeError —
  local_only / hybrid OFF 케이스에서 실제로 호출되지 않음 입증.

## 12. PII / API key 보호

- hybrid_retrieve / reranker / confidence 모듈은 PII 비의존 (검색만, 외부 전송 X).
- 예외 catch 시 메시지/traceback 어떤 응답에도 노출 안 함 (vector 실패 시
  `_ = e` 로 의도적 무시 — caller 가 별도 로깅).
- API key 변수 reference 0건 (`grep -rE "api_key" app/services/ai/rag/` —
  reranker.py / confidence.py / retriever.py 모두 0).

## 13. 아직 후속 세션에 남기는 것

| 항목 | 시점 |
|---|---|
| `AI_RAG_HYBRID_ENABLED` AiSetting 컬럼 (m014) | 18-7 admin/router |
| 응답에 `reason_code` / `embedding_called` / `ai_mode` / `prompt_version` 노출 | 18-7 admin/router |
| 관리자 UI 검색 모드 표시 / α/β 토글 | 18-7 admin/router |
| `pipeline.run_manual_ask` 가 `hybrid_retrieve` 사용하도록 통합 | 18-7 admin/router |
| circuit breaker (5분 차단) | 18-7 |
| eval set 비교 (hybrid ON vs OFF) | 18-7 머지 직전 |
| 실제 OpenAIEmbeddingProvider SDK 구현 | 18-7+ |
| PyInstaller spec hidden import (rag/reranker, rag/confidence) | 18-7/18-8 또는 사용자 승인된 빌드 세션 |
