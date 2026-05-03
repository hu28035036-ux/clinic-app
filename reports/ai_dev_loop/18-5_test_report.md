# 18-5 Vector / Embedding 테스트 리포트

## 메타

- **세션 이름**: 18-5_vector_embedding
- **작성일**: 2026-05-02 (1회차) → 2026-05-02 (2회차, Codex M-1 반영)
- **기준 브랜치**: ai-rag-v1-integration
- **베이스라인**: 18-4 통과 (313 passed, 1 skipped, 7 xfailed) — Codex 4회차 통과
- **루프 회차**: 1/5 (1회차 통과 후 Codex 1회차 검토 → M-1 반영하여 spec revert → 재실행 동일 결과)

## 실행 환경

- OS: Windows 11 Home (cp949 콘솔)
- Python: 3.12.10 (venv)
- pytest: 8.4.2
- ruff: 최신 (project pyproject.toml 기준)

## 실행 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_ai_vector_harness.py -v
venv/Scripts/python.exe -m pytest tests/test_ai_reindex_harness.py tests/test_ai_chunker_harness.py tests/test_ai_manual_rag_harness.py tests/test_ai_manual_rag_contract.py tests/test_ai_safety_harness.py tests/test_ai_full_harness.py -q
venv/Scripts/python.exe -m pytest tests --tb=short -q
venv/Scripts/python.exe -m ruff check app tests scripts
venv/Scripts/python.exe scripts/check_db_path.py
```

## 결과 요약

| 묶음 | 결과 |
|---|---|
| `test_ai_vector_harness.py` (신규 18-5) | **36 passed** |
| `test_ai_reindex_harness.py` (18-4 회귀) | **24 passed** |
| `test_ai_chunker_harness.py` (18-3 회귀) | **35 passed** |
| `test_ai_manual_rag_harness.py` (18-2 회귀) | **18 passed** (reason_code 카운트 23→29 갱신) |
| `test_ai_manual_rag_contract.py` (18-2) | **9 passed** |
| `test_ai_safety_harness.py` (18-0) | **12 passed** |
| `test_ai_full_harness.py` (18-0) | **8 passed** |
| **신규 vector + 18-0~18-4 회귀 묶음 합계** | **142 passed** |
| **전체 tests (모든 회귀 포함)** | **349 passed, 1 skipped, 7 xfailed, 27 warnings** |
| ruff (`app tests scripts`) | **All checks passed!** |
| check_db_path.py | 정상 (단독 실행 시 운영 경로 INFO 출력 — 테스트 중에는 conftest 격리, vector 테스트의 `test_18_does_not_use_operational_db` 통과) |

## 18-4 baseline 대비 비교

| 항목 | 18-4 baseline | 18-5 결과 | Δ |
|---|---|---|---|
| passed | 313 | 349 | **+36** (vector 신규) |
| skipped | 1 | 1 | 0 |
| xfailed | 7 | 7 | 0 |
| ruff | All clean | All clean | 0 |
| 외부 LLM 호출 | 0 | 0 | 0 |
| 외부 Embedding 호출 | 0 | 0 | 0 |

회귀 0 — 기존 313 통과는 모두 보존, 신규 vector 36개만 추가.

## 사용자 요구 21개 단언 — 매핑

| # | 사용자 요구 | 테스트 함수 | 결과 |
|---|---|---|---|
| 1 | FakeEmbeddingProvider 사용 | `test_1_fake_embedding_provider_only` | ✅ |
| 2 | 외부 embedding API 호출 0 | `test_2_no_external_embedding_call` (+ AST grep) | ✅ |
| 3 | knowledge_vectors 테이블 생성 | `test_3_*` (3개) | ✅ |
| 4 | chunk embedding 저장 | `test_4_upsert_vector_persists` | ✅ |
| 5 | embedding 조회 | `test_5_find_vector_returns_row` | ✅ |
| 6 | content_hash 같으면 재생성 X | `test_6_same_hash_skips_embedding` | ✅ |
| 7 | content_hash 변경 → 재생성 대상 | `test_7_changed_hash_re_embeds` | ✅ |
| 8 | API key 없음 → vector_disabled | `test_8_*` (2개) | ✅ |
| 9 | local_only 호출 0 | `test_9_*` (2개) | ✅ |
| 10 | 짧은 query → 생성 X | `test_10_short_query_skipped` | ✅ |
| 11 | invalid_query → 생성 X | `test_11_invalid_query_skipped` | ✅ |
| 12 | provider 오류 → keyword fallback | `test_12_provider_error_keyword_fallback` | ✅ |
| 13 | dimension mismatch | `test_13_dimension_mismatch_safe` | ✅ |
| 14 | cosine 안정 계산 | `test_14_cosine_known_vectors` | ✅ |
| 15 | top_k 동작 | `test_15_top_k_search` | ✅ |
| 16 | metadata 연결 | `test_16_vector_results_carry_metadata` | ✅ |
| 17 | vector disabled에서 keyword OK | `test_17_vector_disabled_keyword_works` | ✅ |
| 18 | 운영 DB 미사용 | `test_18_does_not_use_operational_db` | ✅ |
| 19 | manual RAG 회귀 | `test_19_manual_rag_baseline_unchanged` | ✅ |
| 20 | safety 회귀 | `test_20_safety_harness_smoke` | ✅ |
| 21 | chunker/reindex 회귀 | `test_21_reindex_harness_smoke` | ✅ |

## Codex T-1/T-2 보강 4개

| Codex 권고 | 테스트 함수 | 결과 |
|---|---|---|
| T-1a embedding_provider=None → factory 호출 0 | `test_T1_indexer_does_not_call_embedding_factory_when_none` | ✅ |
| T-1b local_only → factory raise | `test_T1_local_only_blocks_embedding_factory` | ✅ |
| T-2a m013 단독 호출 안전 skip | `test_T2_m013_alone_skips_when_table_absent` | ✅ |
| T-2b init_db() 후 테이블 자동 생성 | `test_T2_init_db_creates_knowledge_vectors_table` | ✅ |

## 추가 회귀 보호 단언

| 단언 | 결과 |
|---|---|
| `test_external_provider_no_api_call` (api_key 없음 / 있음 모두 차단) | ✅ |
| `test_provider_call_count_via_calls_attr` | ✅ |
| `test_full_external_call_blocking_smoke` | ✅ |
| `test_reason_codes_defined` (6개 신규 + ALL/__all__) | ✅ |
| `test_indexer_no_delete_calls` (AST 검사 — db.delete 부재) | ✅ |
| `test_encode_decode_roundtrip` | ✅ |
| `test_vector_disabled_reason_records_correctly` | ✅ |

## 외부 호출 0 입증 (사용자 요구 #2)

1. `tests/conftest.py:_block_sdk_modules` — openai/anthropic SDK 클래스를 RuntimeError stub 으로 교체. 인스턴스화 시도 시 즉시 실패.
2. `app/services/ai/vector/*.py` 의 source 에 `import openai` / `from openai` / `import anthropic` / `from anthropic` 부재 (test_2 가 grep 검증).
3. `factory get_embedding_provider` 가 `provider == "openai"|"anthropic"` 분기에서 `EmbeddingUnavailable(kind="sdk_missing")` 즉시 raise — 실제 SDK 코드 호출 경로 부재.
4. 모든 단위 테스트의 `embedding_provider` 는 `FakeEmbeddingProvider` 또는 `None` — `assert_no_embedding_call` / `assert_no_external_calls_full` 단언 통과.
5. `len(fake_embedding_provider.calls)` 카운트가 의도한 호출 수와 정확히 일치 — same_hash skip 케이스에서 0, 신규 임베딩 케이스에서 ≥1.

## m013 idempotent / 안전성 입증

- `test_T2_m013_alone_skips_when_table_absent` — 테이블 부재 시 m013 단독 호출 → 인덱스 생성 0건 (raise 없이 안전 skip). m012 와 동일 패턴.
- `test_T2_init_db_creates_knowledge_vectors_table` — init_db() 후 ORM `Base.metadata.create_all` 이 테이블 생성 + m013 인덱스 보강.
- 두 번 실행 안전성 — `CREATE * IF NOT EXISTS` 사용으로 보장 (m012 와 동일 패턴).

## API key / PII 보호 입증

- `EmbeddingUnavailable.message` 는 kind 만 노출 — api_key 값 미노출.
- `_short_error()` 가 vector 단계 예외 메시지를 400자 컷.
- `result.vector_disabled_reason` 은 enum-like 문자열 ("local_only" 등) — 비밀값 미포함.
- chunker 산출물 (knowledge/manuals/) 은 PII 미포함 (운영 환자 데이터 부재).
- FakeEmbeddingProvider.calls 는 테스트 입력만 보존 — 운영 경로에서 사용 X.

## warning 27개

`tests/test_ai_sms_validate.py` 의 8개 테스트 함수가 tuple return — pytest 8+ 권장은 `assert`. **18-4 와 동일** (18-5 와 무관). 18-4 Codex 응답 §S-3 에 기록된 기존 이슈.

## Codex 1회차 검토 결과 + 조치

| 항목 | Codex 결과 | 조치 |
|---|---|---|
| 치명적 문제 | 없음 | — |
| M-1 `dosu_clinic.spec` 수정이 사용자 "PyInstaller spec 수정 금지" 위반 | 위반 | **즉시 revert — 18-4 baseline 그대로** |
| M-2 m013 이 ORM `create_all` 의존 | 약점 (m012 패턴 동일, 의도된 설계) | 변경 없음 (m012 와 일관 유지) |
| 사소한 문제 (Codex 환경 tmp_path 권한 에러) | Codex 환경 이슈 | Claude Code 환경에서 349 passed 완주 재확인 |
| 18-6 query embedding 차단 통합 검증 부족 | 본 세션 범위 외 | 18-6 retriever 통합 시 재검증 (남은 위험 §8) |

## 자체 판정

| 항목 | 결과 |
|---|---|
| 21개 사용자 요구 단언 통과 | ✅ |
| Codex T-1/T-2 보강 4개 통과 | ✅ |
| 18-4 baseline 313 passed 보존 | ✅ |
| ruff 0 error | ✅ (1회차/2회차 동일) |
| check_db_path 통과 | ✅ |
| m013 idempotent | ✅ |
| 외부 OpenAI/Anthropic embedding 호출 0 | ✅ |
| FakeEmbeddingProvider만 사용 | ✅ |
| manual RAG / safety / chunker / reindex 4개 하네스 통과 | ✅ |
| manual/ask 응답 9키 변경 0 | ✅ (라우터/manual_qa/pipeline 무수정) |
| **`dosu_clinic.spec` 무수정** | ✅ (Codex M-1 후 revert 완료) |
| 5회 이내 통과 | ✅ (1회차) |

→ **자체 판정: 18-6 진입 OK** (Codex 2회차 검증 통과 시).
