# Full Harness 설계 (full_harness_plan)

> 전체 AI 기능이 크게 깨졌는지 빠르게 확인하는 회귀 하네스.
> 모든 AI/RAG 코드 세션의 마지막 안전망.

---

## 1. Harness Name
`full_harness`

## 2. 목적
앱 전체(라우터·DB·AI 서비스·RAG·로깅·권한)가 함께 동작했을 때 v1.3.3 동작이 깨지지 않았는지를 빠르게 확인하는 회귀 하네스. 단일 도메인 단위 테스트가 잡지 못하는 통합 깨짐을 잡는다.

## 3. 시작 구현 세션
- **18-0**에서 최소 버전 시작 (라우터 smoke + 기존 회귀 테스트 묶음)
- **18-8**에서 전체 통합 실행 (PyInstaller 직전)

## 4. 테스트 대상 모듈
- `app/main.py` — 앱 부팅
- `app/routers/ai.py` — AI 라우터 전 엔드포인트
- `app/services/ai/manual_qa.py`, `sms_draft.py`, `action_leave.py`
- `app/services/rag/search.py` (또는 후속 `app/services/ai/rag/pipeline.py`)
- `app/migrations/m007_ai_settings.py` ~ `m011` (그리고 추가될 m012/m013)
- `tests/conftest.py` 4단계 격리

## 5. 입력 케이스
1. `POST /api/ai/manual/search`에 정상 질문 (매뉴얼 키워드 포함)
2. `POST /api/ai/manual/ask`에 정상 질문 (FakeProvider 응답 큐 주입)
3. `POST /api/ai/manual/ask` 빈 질문 → 400
4. AI disabled 상태에서 `manual/ask` → 503
5. API key 없는 상태에서 `manual/ask` → 503, `manual/search`는 200
6. 운영 DB 경로 검사
7. SMS validate / draft 정상 호출
8. action_leave parse / preview / execute 흐름
9. health public / admin 권한 분리
10. 백그라운드 워커 무력화 확인

## 6. 기대 출력
- 모든 정상 케이스 200, 응답 키 v1.3.3과 동일
- 차단/오류 케이스에 정확한 HTTP status + 안내 문구
- AiUsageLog에 PII 마스킹 후 기록
- 어떤 로그에도 API key 부재
- provider/embedding call count 모드별 정확히 일치 (`len(provider.calls)` / `len(embedding_provider.calls)`)

## 7. 외부 LLM 호출 허용 여부
❌ 금지. 모든 시나리오에서 FakeProvider만 사용.

## 8. 외부 Embedding 호출 허용 여부
❌ 금지. 모든 시나리오에서 FakeEmbeddingProvider만 사용.

## 9. Provider call count 기대값 — **두 모드 분리** (측정: `len(provider.calls)`)

> 호출 카운트 단언은 모드별로 두 종류로 나눠 적용한다.
> 18-0~18-1은 (A) 회귀 모드만. 18-2부터는 (A)+(B) 함께 단언.

### A. 현행 회귀 모드 (v1.3.3 동작 보존)
v1.3.3 manual/ask는 RAG 결과가 있고 `top_score >= LOW_SCORE_THRESHOLD(2)`이면 LLM을 호출하므로:
- `manual/ask` AI enabled + key 있음 + sources≥1 + top_score≥2: **`call_count == 1`** (현행 동작 유지 — 회귀 0 보장용)
- `manual/ask` AI disabled / API key 없음 / model 없음 / no_sources / low_confidence: **`call_count == 0`**
- `manual/search` 모든 케이스: **`call_count == 0`**

### B. 목표 local-first 모드 (18-2 이후 점진 도입)
- `local_only`: 모든 케이스 **`len(provider.calls) == 0`**, `len(embedding_provider.calls) == 0`
- `local_first`(기본): keyword/chunk/Local Composer로 충분한 의도 → **`call_count == 0`**. 사용자가 자연어 합성을 요청한 경우만 `call_count == 1`
- `ai_assist`: sources 충분 + 외부 AI 허용 + 문장 생성 필요 시에만 **`call_count >= 1` 가능**
- 모든 모드 공통: no_sources / low_confidence / pii_detected / unknown_feature → **`call_count == 0`**
- 측정 방법: 현재 FakeProvider는 `self.calls: list` 사용 → `len(provider.calls)`로 단언 (18-0 TODO §14 참조).

## 10. Embedding provider call count 기대값 (측정: `len(embedding_provider.calls)`)
- 모든 시나리오 (Full Harness 범위): 0 (vector는 18-5 이후 vector_harness 책임)

## 11. 사용할 Fake 객체
- `FakeProvider` (responses_queue 주입)
- `FakeEmbeddingProvider` (호출되면 실패하도록 설정 — Full Harness는 vector 검증 안함)

## 12. 운영 DB 사용 여부
❌ 절대 금지. `tests/conftest.py` 격리 DB만.

## 13. 사용해야 하는 테스트 DB 또는 fixture
- `tests/conftest.py`의 `client`, `db_path` fixture
- `tests/harness/db_guard.assert_safe_db_path()`
- `tests/harness/seed_data` (직원/휴무유형/환자 샘플)

## 14. 반드시 검증할 reason_code
- `provider_disabled`
- `provider_api_key_missing`
- `invalid_query`
- `no_sources`
- `low_confidence`
- `pii_detected`

## 15. 반드시 검증할 로그 필드
- `AiUsageLog.feature` (manual_search/manual_ask/sms_*/action_*)
- `AiUsageLog.outcome` (success/warning/blocked/error)
- `AiUsageLog.reason_code`
- `AiUsageLog.prompt_text` (마스킹 확인 — 원문 PII 부재)
- `AiUsageLog.response_text` (마스킹 확인)
- `AiUsageLog.provider`, `model`
- 어떤 로그에도 `api_key` 값 부재

## 16. fallback 기대 동작
- AI disabled → `manual/ask` 503, `manual/search` 정상
- API key 없음 → 동일
- 검색 0건 → 안전 안내 + `not_found=true`
- LLM provider 호출 실패 → 503 (현행) 또는 Local Composer (18-4 이후)

## 17. 실패하면 막아야 하는 회귀
- `/api/ai/manual/{search,ask}` 응답 키 변경
- HTTP status 정책 변경 (400/503/200)
- AiSetting 컬럼 변경
- AiUsageLog 컬럼 제거
- SMS AI / 휴무 AI 동작 변경
- 운영 DB 경로 누출
- API key 로그 노출

## 18. 실행 명령 후보
- `run_check.bat`
- `venv\Scripts\python.exe -m pytest tests -v -m full_harness`
- `venv\Scripts\python.exe -m pytest tests/test_ai_*.py tests/test_full_harness.py -v`

## 19. 완료 조건
- [ ] 위 §5 모든 입력 케이스 통과
- [ ] §17 모든 회귀 0건
- [ ] `scripts/check_db_path.py` 통과
- [ ] 기존 `test_ai_sms_*` / `test_ai_action_leave` / `test_ai_manual_qa` 100% 통과
- [ ] provider/embedding call count 단언 통과 (`len(provider.calls)` / `len(embedding_provider.calls)`)

## 20. Codex 검증 시 집중 확인 항목
- Full Harness 자체가 우회되거나 약화되지 않았는가
- 신규 모듈이 추가되었을 때 Full Harness에 회귀 케이스가 추가되었는가
- AI/RAG 외 라우터(예약/통계/직원)에 의도치 않은 영향이 없는가
- conftest 4단계 격리(APPDATA/DB/워커/시드)의 우회 패치가 없는가
- `responses_queue`가 빈 채로 LLM 호출되어 에러가 발생하지 않는가
