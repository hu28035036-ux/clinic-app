# 18 AI/RAG 알려진 위험 / 후속 개선 / 운영 주의점

> v1.4.0 배포 시점에 인지된 위험 + 운영자가 알아야 할 모드별 주의점.
> 본 문서의 위험은 코드 결함이 아니라 "현재 미구현 + 운영 결정 필요" 항목.

## 1. 남은 위험 요소 (배포 직전)

### 1-1. 미구현 — 우선순위 LOW (별도 후속 세션)

| 항목 | 영향 | 우회 방법 |
|---|---|---|
| 외부 OpenAIEmbeddingProvider 실제 구현 | vector path 가 운영에서 활성화 안 됨 (slot 만 존재) | keyword RAG 만 사용 (현재 default 동작) |
| m014 (`AiSetting.AI_RAG_HYBRID_ENABLED` / `ai_mode` / `alpha` / `beta` 컬럼) | 관리자가 hybrid/모드 운영 토글 불가 | 코드 default 값 (hybrid_enabled=False, mode 자동 파생) 으로 운영 |
| `pipeline.run_manual_ask` 의 `hybrid_retrieve` 통합 | 운영 manual/ask 가 keyword 단독 모드 (v1.3.3 동작 그대로) | 의도된 보수적 default — 사용자 결정으로 별도 세션 |
| 응답 optional 5키 (`reason_code`/`llm_called`/`embedding_called`/`ai_mode`/`prompt_version`) 노출 | 프론트가 reason_code 기반 분기 못 함 | 기존 `blocked_reason` 문자열 분기로 충분 (v1.3.3 패턴) |
| `main.html` 관리자 UI 통합 (Reindex 버튼 / vector 토글) | 관리자가 GUI 로 reindex/토글 못 함 | `/api/ai/status` API 직접 호출 (Postman/curl) |
| circuit breaker (5분 차단) | vector provider 일시 장애 시 즉시 fallback 만, 후속 호출 차단 안 됨 | 18-6 hybrid_retrieve 가 catch 후 keyword fallback (검색 중단 0) |

### 1-2. 환경 의존 / Codex 환경 한정

| 항목 | 상태 |
|---|---|
| Codex 환경 tmp_path 권한 이슈 (5 errors) | Claude Code 환경에서는 100% 통과 — 환경 차이 |
| Codex 환경 venv launcher 깨짐 | `python -m PyInstaller` 우회로 빌드 가능 (18-8 적용) |

### 1-3. 작업트리 정리 (Git 운영)

- 18-0~18-8 누적 변경이 단일 워킹트리에 섞여 있음 (Codex 18-7/18-8 권고).
- 사용자 결정: 옵션 A (세션별 커밋) vs 옵션 B (단일 release commit).

## 2. 후속 개선 후보 (우선순위 순)

### 2-1. v1.4.x 패치 후보
1. **m014 + 라우터 wire-in**: `AiSetting.AI_RAG_HYBRID_ENABLED` / `ai_mode` 컬럼 추가 + `pipeline.run_manual_ask` 가 `hybrid_retrieve` 사용. 응답 optional 5키 노출.
2. **외부 OpenAIEmbeddingProvider 실제 구현**: `app/services/ai/vector/embeddings.py` 의 NotImplementedError slot 채우기. 비용 모니터링 + max_tokens 제한.
3. **관리자 UI 통합**: main.html 에 `/api/ai/status` 호출 + 표시 + Reindex 버튼.

### 2-2. v1.5.x 후보
1. **Cache (rag/cache.py)**: PII 미포함 + DB 상태성 아닌 query 캐시 (TTL + prompt_version key).
2. **circuit breaker**: vector provider 5분 차단 후 자동 복구.
3. **AiUsageLog 신규 컬럼** (m015): `ai_mode` / `llm_called` / `embedding_called` / `reason_code` / `local_answer_type` / `skipped_llm_reason` / `skipped_embedding_reason` / `prompt_version` 기록.
4. **Local Answer Composer 강화**: 단순 keyword passage 외 db_query / rule_based 모드 추가.

### 2-3. v1.6.x+ 후보
1. **eval set 정식 측정**: `docs/ai_rag_quality_eval_plan.md` §5 기준 합격 비교 (hybrid ON vs OFF).
2. **prompt_version A/B**: PROMPTS dict 에 v2 추가 + AiSetting 으로 운영 토글.
3. **Anthropic Claude 통합 검증**: 현재 코드 path 는 있으나 운영 검증 부재.

## 3. 모드별 운영 주의점

### 3-1. local_only 모드

**용도**: 외부 API 호출 절대 차단 (보안/비용 강화 환경).

**동작**:
- `derive_ai_mode` 가 enabled=False / api_key 없음 / model 없음 중 하나면 자동 `local_only` 파생.
- 명시적 컬럼은 m014 미도입 → 18-8 시점은 자동 파생만.
- LLM 호출 0 (`should_call_llm` 의 우선순위 3).
- Embedding factory 차단 (`get_embedding_provider(mode="local_only")` → `EmbeddingUnavailable("local_only")` raise).
- vector_status: `enabled=False, available=False, reason="vector_disabled"`.

**주의**:
- ⚠️ AI 자체가 비활성화된 상태로 보임 (UI 에 "AI 기능 꺼짐" 표시).
- ⚠️ manual/search 는 keyword RAG 로 정상 동작 (LLM 미사용이라 영향 0).
- ⚠️ manual/ask 는 503 ("AI 기능이 꺼져 있습니다.") — v1.3.3 동작 그대로.

### 3-2. local_first 모드 (기본값)

**용도**: 가능하면 LLM 미사용 + 게이트 통과 시에만 LLM 1회.

**동작**:
- `enabled=True` + `api_key` 있음 + `model` 있음 → 자동 `local_first` 파생.
- LLM 호출 가능 (단 다층 게이트 통과 필요).
- 게이트 우선순위: provider_disabled > pii > local_only > no_sources > low_confidence.
- `top_score >= 2` (manual_qa LOW_SCORE_THRESHOLD) + `final_score >= 0.3` (hybrid LLM_CALL_THRESHOLD) 양쪽 통과 시 LLM 1회.

**주의**:
- ⚠️ 매뉴얼에 없는 질문 → not_found + LLM 호출 0 (비용 절감).
- ⚠️ PII 가 입력에 섞이면 마스킹 후 검색 (LLM 전송 시 추가 검사).
- ⚠️ 운영 모니터링: `/api/ai/status` 의 `recent_ai_logs.by_outcome` 에서 success / blocked / warning 비율 확인.

### 3-3. ai_assist 모드 (선택)

**용도**: 외부 API 적극 사용 (응답 품질 우선 + 비용 감수).

**동작**:
- 18-8 시점은 자동 파생 X — 명시적 운영자 토글 필요 (m014 도입 후).
- 게이트는 동일 (local_first 와 동일 레벨의 보호).
- 차이: Local Composer 우선순위 ↓, LLM 호출 빈도 ↑ (별도 세션에서 정의).

**주의**:
- ⚠️ 18-8 시점은 `ai_assist` 모드 자동 진입 X — `should_call_llm` 의 mode 인자 명시 시에만 동작.
- ⚠️ m014 + 운영자 토글 후 활성화 시 비용 모니터링 필수.

## 4. Vector / Hybrid 사용 시 주의점

### 4-1. 18-8 시점 — 항상 disabled

- `vector_status.enabled = False`
- `vector_status.available = False`
- `vector_status.reason = "vector_disabled"`
- `pipeline.run_manual_ask` 가 `hybrid_retrieve` 미사용 → manual/ask 응답에 vector 영향 0.
- knowledge_vectors 테이블은 빈 상태 (chunk indexer 가 `embedding_provider=None` default).

### 4-2. 미래 활성화 시 (m014 + 라우터 wire-in 후)

**전제 조건**:
- 외부 OpenAIEmbeddingProvider 실제 구현 완료 (현재 slot 만)
- `AI_EXTERNAL_EMBEDDING_ENABLED` flag 컬럼 추가 (m014)
- API key 등록 + 외부 호출 비용 사용자 동의

**reindex 절차**:
1. `/api/ai/reindex` POST (admin) — 신규 엔드포인트 도입 후
2. indexer 가 chunk 생성 + embedding_provider 호출 (배치)
3. `knowledge_vectors` 테이블에 upsert (content_hash skip)
4. 이후 `/api/ai/manual/ask` 가 `hybrid_retrieve` 호출 → keyword + vector 결합

**비용 / 호출 관찰**:
- `/api/ai/status.recent_ai_logs.by_feature` 에 manual_ask 호출 수 확인
- `/api/ai/status.knowledge.vectors` 카운트가 chunks 와 일치하는지 확인
- AiUsageLog 의 `embedding_tokens` (m015 후) 합계 추적

**fallback**:
- vector 실패 → keyword 단독 (검색 중단 0)
- reason_code: `vector_disabled` / `provider_error`

## 5. 실제 외부 API 연동 시 추가 검증 (현재 미실시)

### 5-1. OpenAI / Anthropic LLM 실제 호출 활성화 시
- [ ] API key 등록 후 manual/ask 1회 호출 → 200 응답 + `len(provider.calls) == 1` 확인 (테스트)
- [ ] 응답에 출처 매뉴얼 파일명 포함 확인 (할루시네이션 방지 1차 검증)
- [ ] PII 차단 동작 확인 — "010-1234-5678 환자" 같은 입력 → `AiPiiBlocked` 400
- [ ] AI 응답에서 의료 단정 / 실행 완료 표현 → `validate_answer` 가 차단
- [ ] 비용 모니터링: AiUsageLog 의 `prompt_tokens` / `completion_tokens` 합계 추적
- [ ] timeout (8s) 동작 확인

### 5-2. OpenAI Embedding 실제 호출 활성화 시
- [ ] OpenAIEmbeddingProvider 실제 구현 (현재 slot 만)
- [ ] dimension mismatch 검증 (text-embedding-3-small = 1536)
- [ ] `embedding_blob` 컬럼 활성화 (현재 JSON 만)
- [ ] reindex 후 `knowledge_vectors` 카운트 = chunks 카운트 확인
- [ ] content_hash 같은 chunk 재인덱싱 시 호출 0 (skip 입증)
- [ ] query embedding cost 추적

### 5-3. m014 도입 + hybrid 활성 시
- [ ] AiSetting `AI_RAG_HYBRID_ENABLED=True` + `alpha=0.6` + `beta=0.4` 설정 후 manual/ask
- [ ] 응답에 `search_mode="hybrid"` 노출 확인 (응답 optional 키 도입 후)
- [ ] dedup 동작 — 같은 path 가 keyword + vector 양쪽 hit → 1건만 sources 에 포함
- [ ] vector 실패 catastrophic 시 keyword fallback 발생 확인

## 6. 운영 환경에서 인지해야 할 트레이드오프

### 6-1. local_only vs local_first
- local_only: 외부 비용 0, 답변 품질 ↓ (검색 결과 직접 표시)
- local_first: 외부 비용 = 게이트 통과 케이스 × 호출당 비용, 답변 품질 ↑

### 6-2. keyword vs hybrid
- keyword: 정확 매칭 강함, 동의어 약함 (예: "휴무" 검색 시 "연차" 매뉴얼 안 잡힘)
- hybrid: 의미 매칭 강함, 정규화 가중합으로 균형. 단 vector cost 추가.

### 6-3. AI 비활성 vs 활성
- 비활성: AI 기능 0, 매뉴얼 키워드 검색 만 동작.
- 활성: 매뉴얼 Q&A + SMS draft + 휴무 자연어 등록 가능.

## 7. 모니터링 권장 (배포 후)

| 지표 | 출처 | 임계 |
|---|---|---|
| LLM 호출 수 (24h) | `/api/ai/status.recent_ai_logs.by_outcome.success` | 비용 한도 (사용자 결정) |
| 차단 비율 | `/api/ai/status.recent_ai_logs.by_outcome.blocked / total` | 5% 초과 시 PII/할루시네이션 가드 작동 확인 |
| reindex 실패 | `/api/ai/status.knowledge.last_reindex.status` | partial / failed 면 failed_paths 확인 |
| chunk/vector 카운트 불일치 | `chunks` vs `vectors` (vector 활성 시) | dimension mismatch 또는 same_hash skip 확인 |
| API key 만료 | sdk_errors 누적 | 401/403 반환 시 키 갱신 |

## 8. 사고 대응

### 8-1. 운영 LLM 비용 폭증
1. 즉시: `/api/ai/settings` PUT `enabled=False` (전체 차단)
2. 다음: `recent_ai_logs.by_feature` 분석 → 어느 feature 가 호출 폭증?
3. 영구: m014 의 `AI_EXTERNAL_LLM_ENABLED=False` 또는 `local_only` 모드로 전환

### 8-2. PII 누출 의심
1. 즉시: AiUsageLog 직접 조회 — `prompt_hash` / `response_hash` 만 있는지 확인
2. `/api/ai/status.recent_ai_logs.recent[].error_detail` 에 PII 패턴 (전화/RRN) 검색
3. `_safe_error_detail` 마스킹 동작 확인 (`test_get_recent_logs_masks_pii_in_error_detail`)
4. 영구: pii.py 의 정규식 강화 + 추가 PII 패턴 추가

### 8-3. 매뉴얼 검색 결과 0건 폭증
1. `knowledge/manuals/` 동봉 확인 (`_internal/knowledge/manuals/*.md` 6개)
2. loader 캐시 reset (`/api/ai/reindex` 후속 도입 후)
3. 임시 회피: 사용자에게 매뉴얼 파일명 직접 안내

### 8-4. 빌드 깨짐 (다음 빌드 시도 시)
1. 사전 검증: `pytest tests/test_pyinstaller_hidden_imports.py` 53 tests 통과 확인
2. spec hidden imports 누락 — 본 문서 §1-1 의 18-1~18-7 신규 모듈 19개 spec 등록 확인
3. SDK 미설치 — `pip install -r requirements.txt`

## 9. 종합

✅ **18-0~18-8 코드 + 테스트 + 빌드 + smoke 모두 검증 완료**.

⚠️ **남은 위험은 모두 "미구현" 또는 "운영 결정 필요"** — 코드 결함 0.

⏳ **외부 API 실제 연동은 사용자 환경에서 별도 검증 필요** (5절 참조).
