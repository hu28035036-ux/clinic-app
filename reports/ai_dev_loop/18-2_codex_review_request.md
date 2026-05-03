# 18-2 keyword RAG 분리 — Codex 검증 요청 (스코프 엄격화 후)

세션: 18-2
브랜치: ai-rag-v1-integration
선행 세션: 18-0 (하네스), 18-1 (구조 골격)
다음 세션 후보: 18-3 (Local Answer Composer + confidence)

## 0. 1차 Codex 검증 후 추가 정리

1차 검증에서 다음 항목이 18-2 범위 초과로 지적됨:
- `app/services/ai/vector/` 디렉토리 (untracked, 4개 stub)
- `rag/schemas.py` 의 chunk/vector/embedding 관련 정의 (Chunk dataclass, embedding_called, REASON_VECTOR_DISABLED, REASON_EMBEDDING_SKIPPED_* 5개)
- `tests/test_ai_full_harness.py::test_vector_package_importable` 등 vector import 단언

본 PR/세션의 최종 상태는 위 항목을 모두 제거한 엄격 18-2 (keyword 분리만) 형태.

## 1. 검증 요청 요지

기존 keyword 기반 manual RAG 의 검색·답변 조립 로직을 신규 모듈(`app/services/ai/{knowledge,rag}/`)로 분리. **외형 동작·응답 키·import 경로·하네스 결과는 v1.3.3과 100% 동일**. 18-2 범위 밖 항목 (chunk/vector/embedding/hybrid/DB migration/spec/UI) 미포함.

## 2. 분리 매핑 표

| from | to |
|---|---|
| `rag/search.py` 토큰화·inverted index·스코어링 | `knowledge/keyword_index.py::search_documents` |
| `rag/search.py::_load_index` / `_build_runtime_index` | `knowledge/loader.py::get_raw_documents`, `load_documents` |
| `manual_qa.manual_search` 검색 단계 | `rag/retriever.py::keyword_retrieve` |
| `manual_qa.ask_manual_question` 전체 흐름 | `rag/pipeline.py::run_manual_ask` |
| `manual_qa.validate_answer` | `rag/pipeline.py::validate_answer` |

기존 `app/services/rag/search.py` 는 **그대로 둠**.

## 3. manual_qa wrapper diff 요약

281줄 → 약 80줄 wrapper. 모든 공개 함수가 `rag.pipeline` 위임. `LOW_SCORE_THRESHOLD = 2`, `_MANUAL_SYSTEM_PROMPT` 재노출.

## 4. 응답 키 회귀 0 입증

`tests/test_ai_manual_rag_contract.py` 9개 테스트 전부 통과. 9 필수 키 + 3 sources 키 + 4 optional 키 (embedding_called 제거 후) 모두 단언 통과.

## 5. FakeProvider prompt 동등성 입증

`run_manual_ask` 가 FakeProvider 에 보내는 `(prompt, system)` 가 v1.3.3 동등:
- `_build_user_prompt(cleaned, results)` 텍스트 템플릿 1:1 일치
- `system = get_prompt("manual_qa.system", "v1")` 가 v1.3.3 `manual_qa._MANUAL_SYSTEM_PROMPT` 와 동일 문자열 (`test_prompts_v1_matches_current_manual_qa_system` 통과)

## 6. local-first 게이트 입증

3단계 게이트 (sources 0 / top_score<2 / provider 부재) 모두 provider 호출 0. PII 마스킹 → retriever 호출 전 수행.

## 7. 18-1 stub 단언 보존

`rag.pipeline.run_manual_qa` / `rag.retriever.retrieve` 는 NotImplementedError 그대로. 18-2 정식 진입점은 별도 함수명 (`run_manual_ask`, `keyword_retrieve`).

## 8. 스코프 엄격화 — 18-2 범위 외 항목 정리

| 항목 | 처리 |
|---|---|
| `app/services/ai/vector/__init__.py` | 삭제 |
| `app/services/ai/vector/embeddings.py` | 삭제 |
| `app/services/ai/vector/similarity.py` | 삭제 |
| `app/services/ai/vector/store.py` | 삭제 |
| `rag/schemas.py::Chunk` dataclass | 제거 |
| `rag/schemas.py::Answer.embedding_called` | 제거 |
| `rag/schemas.py::REASON_VECTOR_DISABLED` | 제거 |
| `rag/schemas.py::REASON_EMBEDDING_SKIPPED_*` (5) | 제거 |
| `test_ai_full_harness.py::test_vector_package_importable` | 제거 |
| `test_ai_full_harness.py::test_no_circular_import_*` | vector 4개 항목 제거 |
| `test_ai_manual_rag_harness.py::test_schemas_optional_5_keys_present` | optional_4 로 갱신 |
| `test_ai_manual_rag_harness.py::test_schemas_reason_codes_29_defined` | 23 으로 갱신 |
| `test_ai_manual_rag_contract.py::test_contract_optional_keys_*` | embedding_called 제거 |
| `tests/harness/contract.py::OPTIONAL_KEYS` | embedding_called 제거 |

각 정리 항목은 18-5 (chunk + vector 도입) 시점에 다시 추가될 예정. 본 18-2 변경에서는 keyword 분리에만 집중.

## 9. 금지 사항 점검

- ❌ chunker / vector / hybrid / DB migration / requirements / spec / UI / 라우터 응답 키 변경 없음.
- ❌ 하네스/테스트 약화 없음 (skip/xfail 추가 없음, 단언 약화 없음).
- ❌ 운영 DB 접근 없음 (`scripts/check_db_path.py` exit 0).
- ❌ 실제 외부 LLM/Embedding 호출 없음.

## 10. 테스트 결과 (스코프 엄격화 후)

- `tests/test_ai_manual_rag_harness.py`: 18 passed
- `tests/test_ai_manual_rag_contract.py`: 9 passed
- `tests/test_ai_safety_harness.py`: 12 passed
- `tests/test_ai_full_harness.py`: 8 passed (이전 9개 → vector_package_importable 제거)
- `pytest tests`: 254 passed, 1 skipped, 7 xfailed (이전 255 → vector_package_importable 1개 제거)
- `ruff check app tests scripts`: All checks passed!
- `python scripts/check_db_path.py`: exit 0

수정 루프: 1회 (import depth 1건). 스코프 엄격화는 추가 결함 0.

## 11. Codex 가 직접 확인할 항목

1. 분리된 모듈/책임 매핑이 §2 표와 코드 일치.
2. `manual_qa.py` 공개 심볼이 v1.3.3과 동일 (`ask_manual_question`, `manual_search`, `validate_answer`, `LOW_SCORE_THRESHOLD`, `_MANUAL_SYSTEM_PROMPT`).
3. 라우터 `app/routers/ai.py:38, 567-600, 603-750` 가 wrapper 호출만 하고 응답 키 변경 없음.
4. `rag.pipeline.run_manual_ask` 의 게이트/정책 상수/검증 정규식이 v1.3.3 `manual_qa.ask_manual_question` 와 1:1.
5. `knowledge.keyword_index.search_documents` 알고리즘이 v1.3.3 `app.services.rag.search.search` 와 1:1 (토큰화 정규식, 점수 계산식, name 보너스 +5, snippet 자르기 300자).
6. **`app/services/ai/vector/` 디렉토리 부재 확인** (이번 정리에서 삭제).
7. **`rag/schemas.py` 에 chunk/vector/embedding 관련 정의 부재 확인**.
8. 신규 모듈이 `app.services.ai.manual_qa` 를 import 하지 않음 (역의존 회피).

## 12. 다음 세션(18-3) 진입 yes/no 자체 판단

**yes**.
- 응답 키 회귀 0, 외부 호출 0, PII 마스킹·할루시네이션 가드 위치 불변.
- 18-2 스코프 엄격 준수 (chunk/vector/embedding/hybrid 모두 부재).
- 18-1 stub 단언 보존 (`run_manual_qa`/`retrieve` NotImplementedError) — 18-5 흡수 가능.

## 13. 다음 세션 진입 시 주의

- 18-3 Local Answer Composer 도입 시 `provider_override is None` 분기에서 단순 `_NOT_FOUND_ANSWER` 가 아니라 매뉴얼 요약을 반환. 응답 키는 그대로 유지.
- 18-3 에서 `reason_code` optional 필드 도입 검토 (현재 응답에 0개).
- 18-5 chunk + vector 도입 시점에 `Chunk` dataclass / `embedding_called` / vector·embedding reason codes / vector 패키지를 다시 추가.
