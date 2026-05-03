# RAG Harness 설계 (rag_harness_plan)

> 매뉴얼 RAG 검색/답변 흐름, sources, LLM 호출 조건, API 계약 검증.

---

## 1. Harness Name
`rag_harness`

## 2. 목적
매뉴얼 Q&A 파이프라인 전체(검색→sources→confidence→LLM 게이트→답변)가 local-first 정책대로 동작하는지 검증한다. v1.3.3 응답 키 계약을 깨지 않으면서 신규 reason_code/모드별 호출 카운트를 단언한다.

## 3. 시작 구현 세션
- **18-0**

## 4. 테스트 대상 모듈
- `app/services/ai/manual_qa.py` (현행) → 추후 `app/services/ai/rag/pipeline.py`로 위임
- `app/services/rag/search.py` (현행) → 추후 `app/services/ai/rag/retriever.py`
- `app/services/ai/rag/confidence.py` (신설)
- `app/services/ai/rag/answer_composer.py` (신설)
- `app/routers/ai.py:567-750` (manual/search, manual/ask)

## 5. 입력 케이스
1. 매뉴얼 키워드 포함 질문 ("백업 방법 알려줘") → 결과 1개 이상
2. 매뉴얼 키워드 + 동의어 ("연차" → "휴무" 매뉴얼 매칭)
3. 매뉴얼 외 질문 ("주식 추천해줘") → 안전 거절
4. 빈/너무 짧은 질문
5. 모호한 1단어 ("백업") → low_confidence 또는 결과
6. `local_only` 모드에서 같은 입력
7. `local_first` 모드에서 keyword로 충분한 입력
8. `ai_assist` 모드에서 sources 없음
9. AI disabled / API key 없음 상태
10. FakeProvider가 `_NOT_FOUND_ANSWER` 반환

## 6. 기대 출력
- `manual/search`: `{sources[], masked_question, top_score}` — 9개 키 동일
- `manual/ask`: `{answer, sources[], confidence, not_found, blocked, blocked_reason, guard_hits, top_score, masked_question}` 9개 키 + optional `reason_code`/`llm_called`/`embedding_called`/`ai_mode`/`prompt_version`
- `sources[]` 항목 키: `title`, `path`(=source_path 호환), `snippet` — UI 후방호환. 신규로 `heading`/`chunk_index`/`score`/`search_mode` optional 추가 가능.

## 7. 외부 LLM 호출 허용 여부
❌ 금지. FakeProvider만.

## 8. 외부 Embedding 호출 허용 여부
❌ 금지 (RAG Harness 단위에서는). vector 검증은 vector_harness 책임.

## 9. Provider call count 기대값 — **두 모드 분리** (측정: `len(provider.calls)`)

### A. 현행 회귀 모드 (v1.3.3 동작 보존, 18-0~18-1 적용)
- 매뉴얼에 있는 질문 + sources≥1 + top_score≥2 + AI enabled + key 있음: **`call_count == 1`**
- no_sources / low_confidence / AI disabled / API key 없음: **`call_count == 0`**
- `manual/search`: 항상 **`call_count == 0`**

### B. 목표 local-first 모드 (18-2 이후 점진 도입)
- `local_only`: 모든 입력 **`call_count == 0`**
- `local_first`(기본) + sources 충분 + Local Composer로 답변 가능: **`call_count == 0`**
- `local_first` + 사용자 의도 "요약/문장 다듬기/자연어 합성": **`call_count == 1`**
- `ai_assist` + sources 충분 + 외부 AI 허용: **`call_count >= 1` 가능**
- 모든 모드 공통: no_sources / low_confidence / pii_detected / unknown_feature → **`call_count == 0`**
- 측정 방법: `len(provider.calls)` (`tests/conftest.py:122` `self.calls: list`).

## 10. Embedding provider call count 기대값 (측정: `len(embedding_provider.calls)`)
- RAG Harness 단위: 0 (vector_harness에서 검증)
- `local_only`에서 embedding factory 인스턴스화 시도 자체 차단

## 11. 사용할 Fake 객체
- `FakeProvider` (responses_queue + call_count)
- `FakeEmbeddingProvider` (호출되면 fail — RAG 단위에서는 금지)

## 12. 운영 DB 사용 여부
❌ 금지. 격리 DB만.

## 13. 사용해야 하는 테스트 DB 또는 fixture
- Full Harness `client`, `db_path`
- `tests/harness/rag_harness.py`:
  - `rag_pipeline(mode)` fixture
  - `knowledge_fixture` (테스트 전용 markdown 작은 셋)
  - `expect_no_external_call(provider, embedding_provider)` 헬퍼

## 14. 반드시 검증할 reason_code
- `no_sources`
- `low_confidence`
- `llm_skipped_no_sources`
- `llm_skipped_low_confidence`
- `llm_skipped_keyword_only`
- `llm_skipped_local_answer`
- (보조) `llm_skipped_local_only`, `external_api_not_allowed`

## 15. 반드시 검증할 로그 필드
- `feature` ∈ `{manual_search, manual_ask}`
- `outcome` ∈ `{success, warning, blocked}`
- `reason_code`
- `prompt_text` (마스킹된 형태, 원문 PII 부재)
- `latency_ms`
- `provider`, `model` (호출 시에만 채움)
- `llm_called`, `embedding_called`, `ai_mode`, `prompt_version` (신규 컬럼 도입 후)

## 16. fallback 기대 동작
- 검색 0건 → `_NOT_FOUND_PROMPT` + `not_found=true`, sources=[]
- 저신뢰 → `_NOT_FOUND_PROMPT` + sources 채움 + `not_found=true`
- LLM 호출 차단 → Local Composer 결과 또는 안전 안내
- LLM 호출 실패 (provider_error) → 503 (현행) 또는 Local Composer (18-4 이후)

## 17. 실패하면 막아야 하는 회귀
- `manual/search` 응답 키 9개 변경
- `manual/ask` 응답 키 9개 변경 또는 새 key 도입 시 후방호환 깨짐 (필드 제거/이름 변경/타입 변경)
- `LOW_SCORE_THRESHOLD` 정책 임의 변경
- `_NOT_FOUND_ANSWER` / `_NOT_FOUND_PROMPT` / `_BLOCKED_ANSWER` 문구 임의 변경
- `category="manuals"` 단일 검색 정책 변경

## 18. 실행 명령 후보
- `venv\Scripts\python.exe -m pytest tests/test_rag_pipeline.py tests/test_ai_manual_qa.py -v`
- `venv\Scripts\python.exe -m pytest tests -k rag -v`

## 19. 완료 조건
- [ ] §5 모든 입력 케이스 통과
- [ ] §9 provider call count 기대값 단언 통과 (`len(provider.calls)`)
- [ ] §14 모든 reason_code 케이스 발급 단언 통과
- [ ] §17 모든 회귀 0건
- [ ] 기존 `test_ai_manual_qa.py` / `test_ai_hallucination.py` 100% 통과

## 20. Codex 검증 시 집중 확인 항목
- 응답 9개 키가 그대로 보존되는가 (`Source.title/path/snippet`)
- 신규 reason_code 추가 시 응답에 정확히 1개만 발급되는가 (우선순위 규칙 §5)
- LLM 호출 게이트 (sources≥1, confidence≥임계, PII 없음, 모드)에 누수가 없는가
- `manual/search`는 LLM 호출 없이 200, AI disabled에서도 정상인가
- `expect_no_external_call`이 우회되지 않았는가
