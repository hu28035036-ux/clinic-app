# AI/RAG 에러·차단 reason_code 표준 (ai_rag_error_codes)

> 모든 RAG/AI 응답·로그에 일관된 `reason_code`를 사용한다.
> reason_code는 응답 JSON(optional 필드)과 `AiUsageLog`에 동시에 기록된다.
> 본 문서는 코드 사전 + 발생 조건 + LLM/Embedding 호출 여부 + 사용자 메시지 + 로그 필드 + 테스트 + fallback 정책을 정의한다.

---

## 0. 표 컬럼 정의

| 컬럼 | 의미 |
|---|---|
| code | reason_code 문자열 (snake_case) |
| 발생 조건 | 어떤 상황에서 발급되는가 |
| LLM 호출 | 발급 시 외부 LLM 호출이 일어났는가 |
| Embed 호출 | 발급 시 외부 Embedding 호출이 일어났는가 |
| 사용자 메시지 | UI 노출용 한국어 안내 (응답 `answer`/안내 영역) |
| 로그 필드 | `AiUsageLog`에 추가 기록할 필드값 |
| 테스트 필요 | 단위/통합 테스트로 검증 필수 여부 |
| Fallback | 차단 후 어떻게 응답을 만드는가 |

---

## 1. 기본 reason_code (RAG / Safety / Provider 공통)

### 1-1. `no_sources`
- 발생 조건: RAG 검색 결과 0건
- LLM 호출: ❌
- Embed 호출: ❌
- 사용자 메시지: "매뉴얼에서 답을 찾지 못했습니다. 관리자에게 확인해주세요."
- 로그 필드: `outcome="warning"`, `reason_code="no_sources"`, `local_answer_type="safety_block"`
- 테스트: ✅ (현행 `manual_qa.py:211-222` 동작 보존)
- Fallback: 안전 안내 응답 + `not_found=true`, `sources=[]`

### 1-2. `low_confidence`
- 발생 조건: top_score < `LOW_SCORE_THRESHOLD` (현재 2)
- LLM 호출: ❌
- Embed 호출: ❌ (옵션: keyword 결과만으로 판단)
- 사용자 메시지: "매뉴얼에서 답을 찾지 못했습니다. 관리자에게 확인해주세요."
- 로그 필드: `outcome="warning"`, `reason_code="low_confidence"`, 기존 `blocked_reason="low rag confidence"` 호환
- 테스트: ✅ (현행 `manual_qa.py:225-236`)
- Fallback: sources 채워서 표시 + `not_found=true`

### 1-3. `pii_detected`
- 발생 조건: 입력 또는 출력에 PII 패턴 감지 (`pii.scan().has_blocking`)
- LLM 호출: ❌ (외부 전송 직전 차단)
- Embed 호출: ❌
- 사용자 메시지: "개인정보가 포함된 질문은 처리할 수 없습니다."
- 로그 필드: `outcome="blocked"`, `reason_code="pii_detected"`, `pii_filter_hits=N`
- 테스트: ✅
- Fallback: 안전 안내 + 마스킹된 입력 표시 (원문 저장 금지)

### 1-4. `unsupported_question`
- **단일 표준 코드** — 추측/단정 응답 차단의 유일한 reason_code (다른 별칭 사용 금지).
- 발생 조건: 다음 중 하나로 `answer_validator`가 차단:
  - LLM 응답에 의료 단정 표현 (`_RE_MEDICAL_CLAIM`: 완치/반드시 치료/확실히 효과/...)
  - LLM 응답에 실행 완료 오인 표현 (`_RE_EXECUTION_CLAIM`: 문자 발송했/예약 변경했/...)
  - 출처 없는데 단정 표현(반드시/무조건/확실히/항상)
  - 사용자 질문이 추측을 유도 ("근거 없어도 대충 알려줘" 등)
- LLM 호출: 가능 (응답 후 차단) 또는 사전 차단(질문 단계)
- Embed 호출: ❌
- 사용자 메시지: "답변을 생성했지만 검증 단계에서 차단되었습니다. 관리자에게 확인해주세요."
- 로그 필드: `outcome="blocked"`, `reason_code="unsupported_question"`, `hallucination_guard_hits=N`, `blocked_reason ∈ {"unsafe medical advice","execution claim blocked","unsupported claim"}`
- 테스트: ✅ (현행 `manual_qa.validate_answer` + `safety_harness`/`rag_harness`)
- Fallback: `_BLOCKED_ANSWER` 안내문

### 1-5. `unknown_feature`
- 발생 조건: 시스템에 없는 기능/메뉴/설정에 대한 질문 (intent_router 분기)
- LLM 호출: ❌
- Embed 호출: ❌
- 사용자 메시지: "이 시스템에 없는 기능에 대한 질문입니다."
- 로그 필드: `outcome="blocked"`, `reason_code="unknown_feature"`
- 테스트: ✅
- Fallback: 안전 안내

### 1-6. `provider_disabled`
- 발생 조건: `AiSetting.enabled == False`
- LLM 호출: ❌
- Embed 호출: ❌
- 사용자 메시지: "AI 기능이 꺼져 있습니다. 관리자 → AI 설정에서 활성화해 주세요."
- HTTP: 503 (현행 라우터 동작 유지)
- 로그 필드: `outcome="blocked"`, `reason_code="provider_disabled"`
- 테스트: ✅ (현행)
- Fallback: 503 + 메시지 (검색은 별도 엔드포인트로 가능)

### 1-7. `provider_error`
- 발생 조건: LLM provider 호출 도중 예외 (`AiUnavailable` 외 일반 오류, 5xx)
- LLM 호출: ✅ (시도)
- Embed 호출: ❌
- 사용자 메시지: "AI 호출 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
- HTTP: 503
- 로그 필드: `outcome="error"`, `reason_code="provider_error"`, `error_kind=...`
- 테스트: ✅
- Fallback: Local Composer 결과로 응답 (모드가 local_first/ai_assist일 때) 또는 503

### 1-8. `vector_disabled`
- 발생 조건: vector 검색 시도했으나 `AI_RAG_VECTOR_ENABLED=false` 또는 API key 없음
- LLM 호출: ❌
- Embed 호출: ❌
- 사용자 메시지: (사용자에 별도 노출 X — 내부 로깅)
- 로그 필드: `reason_code="vector_disabled"`, `embedding_called=false`
- 테스트: ✅
- Fallback: keyword 검색으로 자동 진행

### 1-9. `reindex_in_progress`
- 발생 조건: reindex가 lock 잡고 있는 동안 또 다른 reindex 요청
- LLM 호출: ❌
- Embed 호출: ❌
- 사용자 메시지: "재인덱싱이 진행 중입니다. 잠시 후 다시 시도해 주세요."
- HTTP: 409 (Conflict)
- 로그 필드: `reason_code="reindex_in_progress"`
- 테스트: ✅
- Fallback: 일반 질의는 기존 인덱스로 정상 동작 (별도 코드 아님)

### 1-10. `invalid_query`
- 발생 조건: 빈 질문 / 너무 짧음 (1자 등) / 의미 없는 문자열
- LLM 호출: ❌
- Embed 호출: ❌
- 사용자 메시지: "질문을 입력해주세요."
- HTTP: 400 (현행 동작 유지)
- 로그 필드: `outcome="warning"`, `reason_code="invalid_query"`
- 테스트: ✅
- Fallback: 400

### 1-11. `timeout`
- 발생 조건: LLM 또는 Embedding 호출 timeout (기본 LLM 8s, Embed 4s)
- LLM 호출: ✅ (시도)
- Embed 호출: ✅/❌ (해당 호출에서)
- 사용자 메시지: "응답이 지연되어 안전 모드로 답변합니다."
- 로그 필드: `outcome="warning"`, `reason_code="timeout"`, `latency_ms=...`
- 테스트: ✅
- Fallback: Local Composer 결과로 대체

### 1-12. `internal_error`
- 발생 조건: 그 외 예기치 않은 예외
- LLM 호출: 케이스에 따라
- Embed 호출: 케이스에 따라
- 사용자 메시지: "AI 처리 중 오류가 발생했습니다."
- HTTP: 500
- 로그 필드: `outcome="error"`, `reason_code="internal_error"`, `error_kind=type(e).__name__`
- 테스트: ✅ (예외 핸들러)
- Fallback: 안전 안내, 원문 traceback 비노출

---

## 2. LLM 호출 skip reason_code

LLM 호출이 가능했지만 게이트가 차단한 경우. 응답 메시지는 케이스별, 로그에는 항상 기록.

### 2-1. `llm_skipped_local_only`
- 발생 조건: 모드가 `local_only`
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="local_only"`, `ai_mode="local_only"`
- 테스트: ✅ (`len(provider.calls) == 0`)
- Fallback: Local Composer

### 2-2. `llm_skipped_local_answer`
- 발생 조건: Local Composer가 충분한 답변을 생성함
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="local_answer"`, `local_answer_used=true`, `local_answer_type="..."`
- 테스트: ✅
- Fallback: Local 답변 그대로

### 2-3. `llm_skipped_keyword_only`
- 발생 조건: keyword 결과만 표시하면 충분한 의도 (사용자가 "검색해줘" 등)
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="keyword_only"`, `local_answer_type="keyword_search"`
- 테스트: ✅
- Fallback: 검색 결과 리스트

### 2-4. `llm_skipped_db_answer`
- 발생 조건: 내부 DB 조회로 답이 결정됨 ("오늘 예약 몇 건?" 등)
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="db_answer"`, `local_answer_type="db_query"`
- 테스트: ✅
- Fallback: DB 결과 포맷팅

### 2-5. `llm_skipped_rule_based`
- 발생 조건: 규칙 매칭(date_resolver 등)으로 답이 결정됨
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="rule_based"`, `local_answer_type="rule_based"`
- 테스트: ✅
- Fallback: 규칙 결과

### 2-6. `llm_skipped_no_sources`
- 발생 조건: sources 0건이라 LLM 호출하면 할루시네이션 위험
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="no_sources"`
- 테스트: ✅
- Fallback: `no_sources` 응답 (1-1과 동시 발급)

### 2-7. `llm_skipped_low_confidence`
- 발생 조건: confidence가 unknown/low
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="low_confidence"`
- 테스트: ✅
- Fallback: `low_confidence` 응답 (1-2와 동시 발급)

### 2-8. `llm_skipped_pii`
- 발생 조건: PII 위험으로 외부 전송 차단
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="pii"`
- 테스트: ✅
- Fallback: `pii_detected` 응답 (1-3과 동시 발급)

### 2-9. `llm_skipped_unknown_feature`
- 발생 조건: intent_router가 unknown_feature 분기
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="unknown_feature"`
- 테스트: ✅
- Fallback: `unknown_feature` 응답 (1-5와 동시)

### 2-10. `llm_skipped_invalid_query`
- 발생 조건: invalid_query 단계 차단
- LLM 호출: ❌
- 로그 필드: `skipped_llm_reason="invalid_query"`
- 테스트: ✅
- Fallback: 400

---

## 3. Embedding 호출 skip reason_code

### 3-1. `embedding_skipped_local_only`
- 발생 조건: 모드가 `local_only`
- Embed 호출: ❌
- 로그 필드: `skipped_embedding_reason="local_only"`, `embedding_called=false`
- 테스트: ✅ (`len(embedding_provider.calls) == 0`)
- Fallback: keyword 검색

### 3-2. `embedding_skipped_same_hash`
- 발생 조건: chunk의 `content_hash`가 기존 vector와 동일 → 재생성 불필요
- Embed 호출: ❌
- 로그 필드: `skipped_embedding_reason="same_hash"`
- 테스트: ✅ (idempotent reindex)
- Fallback: 기존 vector 사용

### 3-3. `embedding_skipped_short_query`
- 발생 조건: query 길이가 임계 미만 → 임베딩 가치 낮음
- Embed 호출: ❌
- 로그 필드: `skipped_embedding_reason="short_query"`
- 테스트: ✅
- Fallback: keyword 검색

### 3-4. `embedding_skipped_disabled`
- 발생 조건: `AI_EXTERNAL_EMBEDDING_ENABLED=false`
- Embed 호출: ❌
- 로그 필드: `skipped_embedding_reason="disabled"`
- 테스트: ✅
- Fallback: keyword 검색

### 3-5. `embedding_skipped_api_key_missing`
- 발생 조건: api_key 미설정
- Embed 호출: ❌
- 로그 필드: `skipped_embedding_reason="api_key_missing"`
- 테스트: ✅
- Fallback: keyword 검색

---

## 4. Provider reason_code

### 4-1. `provider_api_key_missing`
- 발생 조건: `AiSetting.api_key`가 비어 있음
- LLM 호출: ❌
- 사용자 메시지: "AI API key 가 설정되지 않았습니다. 관리자 → AI 설정에서 입력해 주세요."
- HTTP: 503 (현행)
- 로그 필드: `outcome="blocked"`, `reason_code="provider_api_key_missing"`
- 테스트: ✅ (현행)
- Fallback: 503 (manual/search는 가능)

### 4-2. `provider_disabled`
- (1-6과 동일 — 동의어, 같은 코드 사용)

### 4-3. `provider_error`
- (1-7과 동일)

### 4-4. `external_api_not_allowed`
- 발생 조건: `AI_EXTERNAL_LLM_ENABLED=false` 또는 모드가 `local_only`
- LLM 호출: ❌
- 사용자 메시지: 일반적으로 미노출 (Local Composer로 응답)
- 로그 필드: `reason_code="external_api_not_allowed"`, `external_api_allowed=false`
- 테스트: ✅
- Fallback: Local Composer

---

## 5. 우선순위 / 동시 발급 규칙

여러 reason_code가 동시에 해당될 수 있다. 우선순위 (위가 높음):

1. `invalid_query`
2. `pii_detected`
3. `provider_disabled` / `provider_api_key_missing`
4. `reindex_in_progress`
5. `unknown_feature`
6. `no_sources`
7. `low_confidence`
8. `unsupported_question` (LLM 응답 후 검증)
9. `timeout`
10. `provider_error` / `internal_error`

응답의 `reason_code`는 가장 높은 우선순위 1개. 로그에는 부가 reason도 기록 가능 (`secondary_reason_codes` 컬럼 — 18-7 시점 결정).

---

## 6. 응답 JSON 매핑 (현행 키와의 호환)

응답 추가 필드(모두 optional):
```json
{
  "answer": "...",
  "sources": [...],
  "confidence": "high|low|unknown",
  "not_found": false,
  "blocked": false,
  "blocked_reason": "no rag hit | low rag confidence | ...",
  "guard_hits": 0,
  "top_score": 0,
  "masked_question": "...",

  "reason_code": "no_sources",            // NEW (optional)
  "llm_called": false,                    // NEW (optional)
  "embedding_called": false,              // NEW (optional)
  "ai_mode": "local_first",               // NEW (optional)
  "prompt_version": "manual_qa.system.v1" // NEW (optional)
}
```

기존 `blocked_reason` 문자열 값(`"no rag hit"`, `"low rag confidence"`, `"no provider"`)은 그대로 유지하면서 신규 `reason_code`를 병행. 프론트는 점진적으로 `reason_code` 사용으로 전환.

---

## 7. 테스트 매핑 (요약)

각 reason_code별 테스트 명: `test_reason_code_<name>` (테스트 모듈은 `tests/test_rag_reason_codes.py`).

테스트 구성:
- 발생 조건 fixture
- 응답에 정확한 `reason_code` 1개 발급 단언
- provider call count / embedding provider call count 기대값 (`len(provider.calls)` / `len(embedding_provider.calls)`)
- 로그 필드 (`AiUsageLog`)에 정확히 기록 단언
- fallback 동작 단언 (응답 키 / 메시지 형태)

---

## 8. 신규 reason_code 추가 절차

1. 본 문서에 행 추가 (조건/호출 여부/메시지/로그/테스트/fallback)
2. `app/services/ai/rag/schemas.py`에 상수 추가
3. `tests/test_rag_reason_codes.py`에 케이스 추가
4. 발급 위치 코드 수정 + 테스트 통과
5. `latest_codex_review_request.md`에 "신규 reason_code 추가" 명시
