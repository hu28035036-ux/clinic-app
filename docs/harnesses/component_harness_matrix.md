# Component × Harness Matrix (component_harness_matrix)

> 세부 RAG 구성요소를 개별 하네스 문서로 쪼개지 않고 표 한 장으로 관리한다.
> 새 컴포넌트가 등장하면 본 표에 행을 추가하고 어느 하네스로 검증할지 즉시 결정한다.

---

## 0. 표 컬럼 정의

| 컬럼 | 의미 |
|---|---|
| Component | 구성요소 이름 |
| Harness | 1차 책임 하네스 (보조 ●로 표기) |
| Start Session | 첫 구현/검증 세션 |
| Ext LLM Allowed | 외부 LLM 호출 허용 여부 |
| Ext Embed Allowed | 외부 Embedding 호출 허용 여부 |
| Fake Required | 필수 Fake 객체 |
| DB Required | 격리 DB 필요 여부 |
| Block Hallucination | 할루시네이션 차단 책임 |
| Block PII | PII 차단 책임 |
| Key Tests | 핵심 테스트 시나리오 (요약) |
| Expected reason_code | 발급/검증할 reason_code |
| Expected log fields | 검증할 AiUsageLog 필드 |
| Completion Criteria | 완료 조건 |

---

## 1. 컴포넌트 매트릭스

### 1-0. Safety Guard (`rag/safety.py`, `manual_qa.validate_answer`, `pii.scan`)
- **Harness**: safety (1차) / rag (●)
- **Start Session**: 18-0
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: FakeProvider (위험 응답 주입용)
- **DB**: Test DB only (격리)
- **Block Hallucination**: ✅ Yes (의료 단정/실행 오인/출처 없는 단정)
- **Block PII**: ✅ Yes (전화/주민번호/환자명/차트번호 마스킹·차단)
- **Key Tests**:
  - PII 차단/마스킹
  - 없는 기능 생성 금지
  - 근거 없는 환자/예약/휴무 단정 금지
  - sources 없음 시 LLM 호출 금지
  - 추측 유도 질문 거절
- **Expected reason_code**: `pii_detected`, `unknown_feature`, `unsupported_question`, `llm_skipped_pii`, `llm_skipped_unknown_feature`
- **Expected log fields**:
  - **18-0 핵심 (이미 존재 또는 우선순위 높음)**: `reason_code` (신규 후보 — `error_codes.md` §6에서 응답에는 추가, 로그 컬럼 추가는 별도 마이그레이션), `blocked_reason` (응답 키로 존재), `pii_filter_hits` (`AiUsageLog` 기존 컬럼, `models.py:340`), `hallucination_guard_hits` (기존 `models.py:341`), `masked_question` (응답 키로 존재)
  - **신규 후보 (후속 확장 — 18-0 필수 아님)**: `safety_status`, `llm_called`, `embedding_called`, `local_answer_used`, `local_answer_type`, `skipped_llm_reason`, `skipped_embedding_reason`, `ai_mode`, `prompt_version` — `architecture_plan.md` §17 신규 컬럼 후보. m012 또는 m015에서 추가 결정.

> 18-0에서는 기존 컬럼(`pii_filter_hits`, `hallucination_guard_hits`, `outcome`, `error_detail`, `prompt_hash`, `response_hash`)과 응답 키(`blocked_reason`, `masked_question`, 신규 optional `reason_code`)로 우선 검증. `safety_status`를 18-0 필수 구현 요구로 쓰지 않는다.
- **완료 조건**: 위 5개 Key Tests 통과 + provider/embedding 호출 카운트 단언 + 응답·로그에 원문 PII 부재

### 1-1. Query Harness (`rag/query_normalizer.py`, `rag/query_parser.py`)
- **Harness**: rag (1차) / safety (●)
- **Start Session**: 18-1
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: 불필요 (외부 호출 0)
- **DB**: ❌
- **Block Hallucination**: 보조 (의도/엔티티 추출 결과만)
- **Block PII**: 1차 (입력 마스킹 + invalid_query)
- **Key Tests**: 날짜 정규화, 치료사명 후보 추출, 동의어 처리, NFC 정규화, invalid_query 처리
- **reason_code**: `invalid_query`, `pii_detected`
- **로그**: `prompt_text` (마스킹), `reason_code`
- **완료 조건**: 12개 입력 정규화 케이스 통과 + 외부 호출 0 단언

### 1-2. Intent Router Harness (`rag/intent_router.py`)
- **Harness**: rag (1차) / safety (●)
- **Start Session**: 18-1
- **Ext LLM**: ❌ (분기 결정만)
- **Ext Embed**: ❌
- **Fake**: 불필요
- **DB**: ❌
- **Block Hallucination**: 분기로 회피
- **Block PII**: 1차 (PII 감지 시 즉시 분기)
- **Key Tests**: manual_rag / db_query / rule_based_action / safety_block / pii_block / unknown_feature 분기
- **reason_code**: `pii_detected`, `unknown_feature`, `invalid_query`
- **로그**: `local_answer_type` ∈ `{rule_based, db_query, safety_block, status_query}`
- **완료 조건**: 6개 분기 모두 단언 + 우선순위 규칙(`error_codes` §5) 준수

### 1-3. Knowledge Harness (`knowledge/loader.py`, `knowledge/normalizer.py`, `knowledge/synonyms.py`)
- **Harness**: chunk (1차)
- **Start Session**: 18-3
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: 불필요
- **DB**: ❌
- **Block Hallucination**: 보조 (출처 메타 보존)
- **Block PII**: ❌ (knowledge는 공식 매뉴얼만)
- **Key Tests**: 문서 로딩, heading 추출, 동의어 검색
- **reason_code**: 직접 발급 없음 (indexer가 사용)
- **로그**: `knowledge_index_runs.{total_docs, succeeded_docs}`
- **완료 조건**: 한국어 normalize + heading 트리 정확

### 1-4. Retrieval Harness (`rag/retriever.py`, `rag/reranker.py`)
- **Harness**: rag (1차) / hybrid (●) / vector (●)
- **Start Session**: 18-2 (keyword) → 18-5 (vector) → 18-6 (hybrid)
- **Ext LLM**: ❌
- **Ext Embed**: 조건부 ✅ (Fake만)
- **Fake**: FakeEmbeddingProvider (vector 경로)
- **DB**: ✅ (chunks/vectors)
- **Block Hallucination**: 보조 (출처 ≥1 보장)
- **Block PII**: ❌
- **Key Tests**: keyword/synonym/heading/title/category 가중치, top_k, no_sources 처리, dedup
- **reason_code**: `no_sources`, `vector_disabled`
- **로그**: `search_mode`, `embedding_called`
- **완료 조건**: 결정성 + dedup + α/β 정규화 합산

### 1-5. Confidence Harness (`rag/confidence.py`)
- **Harness**: rag (1차) / hybrid (●)
- **Start Session**: 18-2
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: 불필요
- **DB**: ❌
- **Block Hallucination**: 1차 (저신뢰 → LLM 차단)
- **Block PII**: ❌
- **Key Tests**: sources 없음 / low_confidence / 임계 boundary
- **reason_code**: `low_confidence`, `llm_skipped_low_confidence`, `no_sources`, `llm_skipped_no_sources`
- **로그**: `confidence`, `top_score`, `reason_code`
- **완료 조건**: 임계값 단일 정의 + 모든 모드 동일 적용

### 1-6. Local Answer Harness (`rag/answer_composer.py`)
- **Harness**: rag (1차) / safety (●)
- **Start Session**: 18-2 (min) → 18-4 (full)
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: 불필요 (LLM 호출 없음)
- **DB**: ✅ (db_query 모드 시)
- **Block Hallucination**: 1차 (출처 누락 시 답변 거부)
- **Block PII**: ❌ (입력은 이미 마스킹된 상태)
- **Key Tests**: 템플릿 답변, 출처 포함, `len(provider.calls) == 0`, db_answer/keyword_passage/template/rule_based 모드
- **reason_code**: `llm_skipped_local_answer`, `llm_skipped_keyword_only`, `llm_skipped_db_answer`, `llm_skipped_rule_based`
- **로그**: `local_answer_used=true`, `local_answer_type`
- **완료 조건**: 4개 모드 모두 외부 호출 0 단언 통과

### 1-7. Source/Citation Harness (`rag/source_builder.py`)
- **Harness**: rag (1차) / API contract (●)
- **Start Session**: 18-1
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: 불필요
- **DB**: ❌
- **Block Hallucination**: 1차 (UI 노출 메타 보존)
- **Block PII**: ❌
- **Key Tests**: source_path / title / heading / chunk_index / score / search_mode 유지, `_format_sources` 후방호환
- **reason_code**: 없음
- **로그**: 없음 (sources는 응답에만)
- **완료 조건**: v1.3.3 응답 키 (`title/path/snippet`) 그대로 + 신규 optional 필드만 추가

### 1-8. Cache Harness (`rag/cache.py`)
- **Harness**: rag (1차) / safety (●)
- **Start Session**: 18-4 이후 (선택)
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: 불필요
- **DB**: ❌ (in-memory)
- **Block Hallucination**: 보조 (TTL로 stale 방지)
- **Block PII**: 1차 (PII 포함 query/응답 cache 금지)
- **Key Tests**: 개인정보 질문 cache 금지, DB 상태성 answer cache 금지, TTL 만료, prompt_version/index_version key 포함
- **reason_code**: 없음 (cache hit/miss는 로그 metric)
- **로그**: `cache_hit` (boolean, 신규 — 18-4 시점 결정)
- **완료 조건**: PII 입력은 cache 절대 미저장 단언

### 1-9. Observability/Log Harness (`ai_logging.py`)
- **Harness**: full (1차) / safety (●)
- **Start Session**: 18-2 이후 점진 확장
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: 불필요
- **DB**: ✅ (AiUsageLog)
- **Block Hallucination**: 보조 (검증 결과 기록)
- **Block PII**: 1차 (저장 직전 마스킹)
- **Key Tests**: ai_mode, llm_called, embedding_called, reason_code, skipped_llm_reason, skipped_embedding_reason 기록
- **reason_code**: 모든 reason_code 기록 가능
- **로그**: 위 모든 신규 컬럼
- **완료 조건**: 신규 컬럼 추가 마이그레이션(m012 또는 m014) idempotent + 기존 컬럼 유지

### 1-10. API Contract Harness (계약 테스트)
- **Harness**: rag (1차) / full (●)
- **Start Session**: 18-0 (smoke) → 18-7 (전체)
- **Ext LLM**: ❌
- **Ext Embed**: ❌
- **Fake**: FakeProvider, FakeEmbeddingProvider
- **DB**: ✅
- **Block Hallucination**: 보조 (응답 키 보존)
- **Block PII**: 보조 (응답 마스킹 확인)
- **Key Tests**: success / no_result / safety / error 4가지 응답 모양에서 키 셋이 v1.3.3과 동일
- **reason_code**: 응답 optional `reason_code` 키 동작 검증
- **로그**: 없음
- **완료 조건**: `manual/{search,ask}` 응답 9개 키 그대로 + 신규 필드 모두 optional

---

## 1-bis. 공통 — 외부 API 차단 정책 (모든 하네스 공통)

본 매트릭스의 모든 컴포넌트는 다음 정책을 공유한다(상세 단계는 `ai_harness_overview.md` §4):
- 18-0 ~ 18-4: FakeProvider/FakeEmbeddingProvider + SDK monkeypatch. 실제 외부 호출 발생 시 테스트 실패.
- **18-5 vector 구현 직전**: 네트워크 차단 도구 도입 (pytest-socket 등) — 별도 ADR로 확정.
- 18-8: 최종 확인.
- 위반 시 머지 금지.

---

## 2. 새 컴포넌트 추가 절차

1. 본 표에 새 행 추가 (1차 Harness + 시작 세션 명시)
2. 1차 Harness의 `*_harness_plan.md` §4(테스트 대상 모듈)에 추가
3. 보조 ●로 표시한 다른 하네스에 fixture 의존성 명시
4. 첫 사용 세션의 체크리스트(`docs/checklists/18-X_*.md`)에 검증 항목 추가
5. `docs/ai_rag_test_plan.md` §6 component_harness_matrix 표와 동기화
6. `docs/ai_docs_index.md` §1-4에 보강 (필요 시)

---

## 3. 본 표를 갱신하는 시점

- 새 RAG 구성요소를 코드에 추가하기 직전
- 기존 컴포넌트의 책임 분기가 바뀔 때
- 새 reason_code 도입 시 (관련 행에 추가)
- Codex가 "어느 하네스에서 검증되는지 불명확" 지적 시
