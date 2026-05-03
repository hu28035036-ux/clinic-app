# AI/RAG 테스트 계획 (ai_rag_test_plan)

> RAG 구조 변경, chunker, vector, hybrid 도입 전후 테스트 전략.
> 본 문서는 **테스트 매트릭스/시나리오/필수 기준**을 정의한다.
> 도메인별 하네스 상세는 `docs/harnesses/{rag,safety,chunk,vector}_harness_plan.md`,
> 절차는 `ai_code_session_protocol.md`, 에러 코드는 `ai_rag_error_codes.md` 참조.

---

## 0-0. Provider call count — 표준 표현

> 본 표준은 호출 카운트를 다루는 모든 docs/하네스/체크리스트에 동일 적용.

- **개념명**: provider call count
- **현재 구현 확인 방식**: `len(provider.calls)` (`tests/conftest.py:122` `self.calls: list`)
- **표기 컨벤션**: 본 docs 어디든 "provider call count == 0/1/≥1"는 코드 단언 시 `len(provider.calls) == 0/1/≥1`로 그대로 적는다.
- **향후 옵션**: FakeProvider helper에 `call_count` property를 추가할 수는 있지만, 추가 시 반드시 `len(provider.calls)`와 동일 값을 반환해야 하며, 기존 `self.calls` 구조를 깨면 안 된다.
- **embedding_provider**: 18-5에서 신규 작성될 `FakeEmbeddingProvider`도 동일 컨벤션(`len(embedding_provider.calls)`) 사용. 18-0~18-4까지는 호출되면 fail이 정책이라 카운트 단언은 0으로만 사용.

---

## 0-1. provider call count 단언 — 두 모드 분리 (필수 규칙)

테스트는 두 종류의 호출 카운트를 단언한다. 두 모드를 섞지 않고 케이스별로 명시.

### A. 현행 회귀 모드 (v1.3.3 동작 보존)
- `manual/ask` 정상 경로(sources≥1 + top_score≥2 + AI enabled + key 있음): **`len(provider.calls) == 1`**
- `manual/ask` 차단/오류 경로(disabled/no_key/no_model/no_sources/low_confidence): **`== 0`**
- `manual/search` 모든 경로: **`== 0`**

### B. 목표 local-first 모드 (18-2 이후)
- `local_only` 모든 입력: **`== 0`** (provider/embedding 둘 다)
- `local_first` + Local Composer 응답: **`== 0`**
- `local_first` + 자연어 합성 의도: **`== 1`**
- `ai_assist` + sources 충분 + 외부 AI 허용 + 합성 필요: **`>= 1` 가능**
- 모든 모드 공통: no_sources / low_confidence / pii_detected / unknown_feature → **`== 0`**

> 모드 단언이 필요한 모든 신규 테스트는 모드를 명시한다 (예: `test_local_only_*`, `test_local_first_*`, `test_ai_assist_*`). 회귀 테스트(`test_ai_manual_qa.py` 등)는 (A) 기준만.
> 측정은 `len(provider.calls)` (`tests/conftest.py:122` `self.calls: list`).

---

## 0. 절대 기준 (모든 세션 머지 전 통과)

- [ ] `pytest tests -v` 전체 통과
- [ ] `ruff check app tests scripts` 통과
- [ ] `python scripts/check_db_path.py` 통과
- [ ] 기존 SMS AI 테스트 전체 통과 (`test_ai_sms_*`)
- [ ] 기존 휴무 AI 테스트 전체 통과 (`test_ai_action_leave`)
- [ ] `/api/ai/manual/search` 응답 키 계약 유지 (계약 테스트)
- [ ] `/api/ai/manual/ask` 응답 키 계약 유지 (계약 테스트)
- [ ] provider call count 검증 통과 (모드별 0 또는 ≥1, `len(provider.calls)`)
- [ ] embedding provider call count 검증 통과 (`len(embedding_provider.calls)`)
- [ ] **개인정보 원문 prompt 전달 금지** 테스트 통과
- [ ] **sources 없는 상태에서 LLM 호출 금지** 테스트 통과
- [ ] **`local_only`에서 모든 provider 호출 금지** 테스트 통과
- [ ] PyInstaller 검증 (18-8) — hidden import 누락 없음

> 답변 문장 전체 snapshot은 금지 (LLM 출력은 비결정적 — 키/구조/제약/카운트만 단언).

---

## 1. pytest 테스트 구조

```
tests/
  conftest.py                   # 4단계 격리 (현행 유지·확장)
  harness/
    db_guard.py                 # 운영 DB 경로 가드 (현행)
    seed_data.py                # 테스트 데이터 시드 (현행)
    helpers.py                  # 공용 헬퍼 (현행)
    rag_harness.py              # NEW — knowledge fixture, chunk fixture, retriever fixture
    safety_harness.py           # NEW — PII 케이스, 위험 표현 케이스, API key 가드
    chunk_harness.py            # NEW — chunker 결정성/경계 fixture
    vector_harness.py           # NEW — FakeEmbeddingProvider, vector store fixture
    hybrid_harness.py           # NEW — keyword+vector 통합 시나리오
    fake_provider.py            # NEW — FakeProvider/FakeEmbeddingProvider with call_count
    contract.py                 # NEW — manual/search, manual/ask 응답 키 계약 단언

  # 기존 (회귀 보호)
  test_ai_sms_draft.py
  test_ai_sms_validate.py
  test_ai_sms_draft_hallucination.py
  test_ai_action_leave.py
  test_ai_manual_qa.py
  test_ai_health_public.py
  test_ai_hallucination.py
  test_ai_logging.py

  # 신규 (단계별 추가)
  test_rag_pipeline.py          # 18-2~
  test_rag_safety.py            # 18-2
  test_rag_intent_router.py     # 18-2
  test_rag_answer_composer.py   # 18-4
  test_rag_answer_validator.py  # 18-2
  test_chunker.py               # 18-3
  test_knowledge_indexer.py     # 18-4
  test_knowledge_chunks_db.py   # 18-4 (m012)
  test_vector_embeddings.py     # 18-5
  test_vector_store.py          # 18-5 (m013)
  test_hybrid_retriever.py      # 18-6
  test_local_only_mode.py       # 18-2~ (모드 단언)
  test_local_first_mode.py      # 18-2~
  test_ai_assist_mode.py        # 18-6~
  test_ai_contract_manual.py    # 18-7
  test_ai_health_status.py      # 18-7 (chunk/vector count)
  test_ai_reindex.py            # 18-4
  test_pyinstaller_hidden_imports.py  # 18-8 (import 시도)
```

---

## 2. 하네스별 책임

### 2-1. 전체 하네스 (`tests/conftest.py` + `tests/harness/*`)
- `client` (FastAPI TestClient)
- `db_path` (격리 임시 경로)
- DB seed: 직원, 휴무유형, 환자 샘플
- FakeProvider 자동 주입 시드
- 백그라운드 워커 무력화
- knowledge fixture (테스트 전용 마크다운)
- chunk index in-memory 빌드

### 2-2. RAG 하네스 (`harness/rag_harness.py`)
- 입력: 테스트 전용 markdown 셋
- 제공:
  - `rag_pipeline(mode="local_only|local_first|ai_assist")` fixture
  - 결과 dataclass (sources/confidence/reason_code/llm_called/embedding_called)
- 시나리오 헬퍼: `expect_no_external_call(provider, embedding_provider)`

### 2-3. Safety 하네스 (`harness/safety_harness.py`)
- PII 입력 케이스 (전화/주민/이름/차트번호)
- 위험 표현 케이스 (의료 단정/실행 오인)
- API key 미설정 케이스
- `local_only` 모드 강제
- 헬퍼: `assert_no_pii_in_payload(payload)`, `assert_no_api_key_in_log(log_text)`

### 2-4. Chunk 하네스 (`harness/chunk_harness.py`)
- 동일 입력 → 동일 chunk 결과 (결정성)
- heading 경계, 코드블록 보호, 빈 섹션
- `content_hash` 안정성

### 2-5. Vector 하네스 (`harness/vector_harness.py`)
- `FakeEmbeddingProvider` (결정적 hash → 벡터)
- `vector_store` fixture (격리 DB)
- 차원 불일치 / API 실패 / `local_only` 차단

### 2-6. Hybrid 하네스 (`harness/hybrid_harness.py`)
- keyword 단독, vector 단독, 결합 점수
- vector 비활성 시 자동 keyword fallback
- α/β 가중 변경 시 순위 변화

### 2-7. component_harness_matrix
- 각 RAG 구성요소 × 하네스 매핑 표 (본 문서 §6 참조)

---

## 3. 시나리오 매트릭스

### 3-1. RAG 정상 경로
| 케이스 | 입력 | 모드 | LLM 호출 | Embed 호출 | 기대 응답 |
|---|---|---|:---:|:---:|---|
| keyword 충분 | "백업 어떻게?" | local_first | ❌ | ❌ | answer + sources, reason=local_answer_used |
| chunk 충분 | "예약 문자 톤" | local_first | ❌ | ❌ | chunk passage |
| LLM 보조 | "이 절차 요약해줘" | ai_assist | ✅ | ❌ | LLM 답변 + sources |
| vector 검색 | "휴무 신청은?" (동의어) | local_first + vector_on | ❌ | ✅ | answer + sources |
| hybrid | "노쇼 후속 안내" | local_first + hybrid_on | ❌ | ✅ | answer + sources |

### 3-2. 안전 차단 경로
| 케이스 | 입력 | reason_code | 응답 |
|---|---|---|---|
| 결과 없음 | "주식 추천" | no_sources | not_found, blocked_reason 채움 |
| 저신뢰 | 모호한 단어 | low_confidence | not_found, sources 채움 |
| PII | "010-1234-5678 김철수 예약" | pii_detected | masked + 차단 |
| 없는 기능 | "환자 강제 삭제 매크로" | unknown_feature | safety block |
| 너무 짧음 | "?" | invalid_query | 400 또는 not_found |
| 위험 단정 LLM 출력 | LLM이 "확실히 효과" | unsupported_question | blocked=true |

### 3-3. local_only 모드
- 모든 분기에서 `len(provider.calls) == 0`
- 모든 분기에서 `len(embedding_provider.calls) == 0`
- API key 없어도 정상 응답
- vector_search 분기 시 keyword fallback

### 3-4. local_first 모드 (기본)
- sources 충분 + 의도 not "문장 다듬기" → LLM 미호출
- sources 부족 → LLM 미호출 (`no_sources`)
- 신뢰도 낮음 → LLM 미호출 (`low_confidence`)
- PII 위험 → LLM 미호출 (`pii_detected`)
- 명시적 자연어 합성 의도 → LLM 호출

### 3-5. ai_assist 모드
- sources 있음 + flag on → LLM 호출
- sources 없음 → LLM 호출 금지
- LLM 응답이 출처와 불일치 → blocked

### 3-6. degrade-gracefully
- vector backend down → keyword fallback 정상
- LLM provider 5xx → Local Composer 결과 반환 (사용자에 일관 응답)
- chunk DB 손상 → 마지막 인덱스 사용
- reindex 진행 중 질의 → 기존 인덱스 사용

### 3-7. PII 시나리오
- 입력 PII가 LLM prompt에 도달 금지 (FakeProvider가 받은 prompt에 원문 PII 부재)
- LLM 응답에 PII 들어오면 마스킹
- 로그에 원문 PII 부재 (sha256/마스킹만)
- API key가 어떤 로그에도 부재

### 3-8. 외부 API 미호출 보장 — **단계별 정책**
- **18-0 (현재)**: FakeProvider + (도입 예정) FakeEmbeddingProvider + `conftest.py` monkeypatch로 실제 OpenAI/Anthropic SDK 호출 즉시 fail. 실제 외부 API 호출이 발생하면 **테스트 실패로 본다**.
- **18-1~18-4**: 동일 정책 유지. 신규 모듈도 monkeypatch 그물에 포함.
- **18-5 vector/embedding 구현 직전**: 외부 API 호출 0 보장을 강화하는 시점. 다음 중 하나를 채택:
  - (a) `pytest-socket` 도입 — `disable_socket()` autouse fixture로 모든 네트워크 차단
  - (b) `httpx`/`requests` 레벨 monkeypatch 확대
  - (c) 환경변수 `AI_TEST_BLOCK_NETWORK=1` + provider/embedding factory에서 명시적 RuntimeError
  - **선택은 18-5 직전 별도 ADR로 확정** (현재는 보류 항목으로 명시).
- **18-8 PyInstaller 검증**: 네트워크 차단 도구 도입 여부 최종 확인.

---

## 4. 회귀 방지 — 기존 테스트

### 4-1. SMS AI
- `test_ai_sms_validate.py`, `test_ai_sms_draft.py`, `test_ai_sms_draft_hallucination.py`
- 변경 후 100% 통과 필수
- `ai_provider` 시그니처 / 응답 형 / PII 가드 변경 금지

### 4-2. 휴무 AI
- `test_ai_action_leave.py`
- parse/preview/execute 분기 + HMAC 토큰 정책 유지

### 4-3. 매뉴얼 Q&A
- `test_ai_manual_qa.py`, `test_ai_hallucination.py`
- 응답 9개 키 + LOW_SCORE_THRESHOLD 동작 + validate_answer 분기

### 4-4. 헬스/로깅
- `test_ai_health_public.py` — public/admin 권한 분리
- `test_ai_logging.py` — PII 마스킹/sha256 정책

---

## 5. 운영 DB 경로 안전검사

- 모든 conftest는 `assert_safe_db_path()` 통과
- `scripts/check_db_path.py`는 `run_check.bat`에서 매번 실행
- 프로덕션 경로(`%APPDATA%\도수치료예약\clinic.db`)가 보이면 즉시 fail

---

## 6. component_harness_matrix (요약)

| 구성요소 | rag_harness | safety_harness | chunk_harness | vector_harness | hybrid_harness | contract |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| safety | | ● | | | | |
| query_normalizer/parser | ● | | | | | |
| intent_router | ● | ● | | | | |
| retriever | ● | | | ● (옵션) | ● | |
| reranker | ● | | | | ● | |
| confidence | ● | | | | | |
| answer_composer | ● | ● | | | | |
| answer_validator | ● | ● | | | | |
| source_builder | ● | | | | | ● |
| pipeline | ● | ● | | | ● | ● |
| loader/normalizer | | | ● | | | |
| chunker | | | ● | | | |
| keyword_index | ● | | ● | | | |
| indexer | | | ● | ● | | |
| embeddings | | ● | | ● | | |
| store | | | | ● | | |
| similarity | | | | ● | ● | |

---

## 7. Prompt 버전 검증

- `prompt_version` 필드가 응답/로그에 포함
- 동일 버전 / 동일 입력 / 동일 fixture → 동일 prompt 문자열 생성 (snapshot)
- 새 prompt 버전 추가 시 기존 버전 삭제 금지 테스트

---

## 8. AI 로그 검증

- `AiUsageLog`에 다음 필드가 채워짐:
  - `feature`, `outcome`, `provider`, `model`, `latency_ms`
  - `ai_mode`, `llm_called`, `embedding_called`
  - `local_answer_used`, `local_answer_type`
  - `skipped_llm_reason`, `skipped_embedding_reason`
  - `reason_code`, `prompt_version`, `pii_filter_hits`, `hallucination_guard_hits`
- 원문 PII 부재 (`prompt_text`/`response_text`는 마스킹된 형태)
- API key 부재

---

## 9. reason_code 테스트

`docs/ai_rag_error_codes.md`의 모든 코드별:
- 발생 조건 케이스로 reason_code 정확히 반환
- LLM/embedding 호출 카운트 단언

테스트 명: `test_reason_code_<name>`

---

## 10. timeout / fallback 테스트

- LLM provider가 timeout 발생하도록 FakeProvider 설정 → Local Composer fallback
- Embedding provider가 timeout → keyword fallback
- 모두 사용자 응답은 200 + 안전 문구 + reason_code
- 로그에 `timeout` reason 기록

---

## 11. local_only / local_first / ai_assist 모드별 테스트

각 모드에 대해 동일 fixture로:
- 응답 키 계약 일치
- provider/embedding call count 단언값 일치 (`len(provider.calls)` / `len(embedding_provider.calls)`)
- 응답 reason_code가 모드 정책에 맞음
- 응답에 출처 포함 여부 일관

---

## 12. 외부 API 미호출 테스트

- conftest 자동 fixture가 `openai.OpenAI`, `anthropic.Anthropic` 등을 fail로 patch
- FakeProvider/FakeEmbeddingProvider만 정상 동작
- 위반 시 즉시 RuntimeError → 테스트 fail

---

## 13. FakeProvider / FakeEmbeddingProvider 사용 원칙

- 모든 단위/통합 테스트는 Fake만 사용
- `call_count`, `last_prompt`, `last_system`, `responses_queue` 노출
- `responses_queue`가 비어 있으면 fail (의도 명확화)
- 실제 SDK 호출은 18-8 PyInstaller 통합 검증에서만 (선택, 환경 변수 명시 필요)

---

## 14. PyInstaller 전 검증 (18-8)

- `test_pyinstaller_hidden_imports.py` — spec의 hiddenimports 모듈 모두 import 시도
- knowledge/ 동봉 확인 (`_MEIPASS/knowledge/`)
- 마이그레이션 파일 모두 import 가능

---

## 15. 답변 문장 전체 snapshot 금지

- LLM 응답은 비결정적 → snapshot 금지
- 검증 대상: 키 존재 여부, 응답 길이 범위, 위험 표현 부재, 출처 포함, reason_code
- Local Composer 출력은 결정적이므로 부분 snapshot 허용 (단, 환경 의존 필드 제외)
