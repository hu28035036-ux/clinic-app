# 18-7 Codex 검증 요청서

## 1. 세션 이름

**18-7_admin_ui** — 관리자 AI/RAG 상태 조회 API (`/api/ai/status`) + read-only
집계 모듈 (`app/services/ai/health.py`) + manual/* 응답 키 회귀 테스트.

## 2. 작업 목표

- 관리자에서 AI/RAG 상태 확인 가능한 API 구현 (사용자 18-7 지시문: "화면 또는 상태 API")
- AI 모드 / 검색 모드 / Knowledge 카운트 / 마지막 reindex / vector·외부 API 가용성 /
  prompt_version / 최근 AI 로그 요약 노출
- 기존 manual RAG / safety / full / chunker / reindex / vector / hybrid 하네스 100% 유지
- API key / PII / hash 노출 0
- 외부 LLM/Embedding 호출 0 (read-only 집계)

## 3. 변경 파일 목록

### 신규 (4 코드 + 3 리포트)
- `app/services/ai/health.py` (~340줄) — read-only 상태 집계 모듈
- `tests/test_ai_health_status.py` (~360줄, 37 tests)
- `tests/test_ai_contract_manual.py` (~180줄, 9 tests — manual/* 응답 키 회귀)
- `tests/test_admin_ui_smoke.py` (~200줄, 14 tests — 라우트/권한/UI 정책)
- `reports/ai_dev_loop/18-7_test_report.md`
- `reports/ai_dev_loop/18-7_fix_summary.md`
- `reports/ai_dev_loop/18-7_codex_review_request.md` (본 파일)

### 수정 (1)
- `app/routers/ai.py` — import 1줄 (`from ..services.ai import health as ai_status_mod`)
  + `@router.get("/status")` 1개 (~40줄). 기존 라우트/함수/응답 무수정.

### 무수정 (회귀 보호)
- `app/services/ai/manual_qa.py`
- `app/services/ai/rag/{pipeline,prompts,safety,schemas,reranker,confidence,retriever}.py`
- `app/services/ai/{provider,pii,sms_draft,action_leave,ai_logging}.py`
- `app/services/ai/vector/{embeddings,store,similarity,__init__}.py`
- `app/services/ai/knowledge/{indexer,chunker,loader,normalizer,keyword_index}.py`
- `app/migrations/m001~m013.py` (m014 미생성)
- `app/models/models.py`
- `app/templates/main.html` (사용자 18-7 정책: API 만 구현)
- `tests/conftest.py`
- `pyproject.toml`, `requirements.txt`, `dosu_clinic.spec`

## 4. 변경 요약

| 모듈 | 책임 | 핵심 함수 |
|---|---|---|
| `app/services/ai/health.py` | read-only 상태 집계 | `build_admin_status` (단일 진입점), `derive_ai_mode`, `derive_search_mode`, `derive_vector_status`, `derive_external_api_status`, `count_documents`, `count_chunks`, `count_vectors`, `get_last_reindex`, `get_recent_logs`, `get_prompt_versions` |
| `app/routers/ai.py` (+40줄) | `/api/ai/status` admin 엔드포인트 | `ai_status` (require_admin) — health 모듈 위임 |

핵심 정책:
1. **API key 평문 + 마스킹 모두 비노출** — `api_key_set` boolean 만 (`api_key_masked` 키조차 부재).
2. **prompt/response hash 비노출** — recent[] 항목은 9키만 (`ts/feature/outcome/provider/model/latency_ms/pii_filter_hits/hallucination_guard_hits/error_detail`).
3. **error_detail 200자 cap** — DB 컬럼 500자 → UI 노출 200자 (PII 누출 영향 최소화).
4. **/api/ai/status 가 AiUsageLog 안 남김** — polling 안전 (health/health/public 와 동일 정책).
5. **read-only 집계** — caller 가 주입한 SQLAlchemy Session 만 사용. 외부 LLM/Embedding 호출 0.

## 5. 절대 바뀌면 안 되는 기능 (회귀 보호 대상)

- `/api/ai/manual/{search,ask}` 응답 9키 / 3키 후방호환 → 라우터/manual_qa/pipeline 무수정
- `/api/ai/health` admin 9키 / `/api/ai/health/public` 4키 후방호환 → 무수정
- `manual_qa.ask_manual_question(provider_override=)` 시그니처
- `pii.scan(text)` 반환형
- `AiSetting`/`AiUsageLog` 기존 컬럼
- `app/migrations/m001~m013` diff 0
- `tests/conftest.py` 격리/SDK 차단 약화 X
- 18-0 safety / 18-3 chunker / 18-4 reindex / 18-5 vector / 18-6 hybrid tests 100% 통과

→ **회귀 결과**: 18-6 baseline 410 passed → 18-7 470 passed (+60, 회귀 0).

## 6. 실행한 테스트 명령

```bash
venv/Scripts/python.exe -m pytest tests/test_ai_health_status.py tests/test_ai_contract_manual.py tests/test_admin_ui_smoke.py -v
venv/Scripts/python.exe -m pytest tests --tb=short -q
venv/Scripts/python.exe -m ruff check app tests scripts
venv/Scripts/python.exe scripts/check_db_path.py
```

## 7. 테스트 결과 요약

| 묶음 | 결과 |
|---|---|
| `test_ai_health_status.py` (신규 18-7) | **37 passed** |
| `test_ai_contract_manual.py` (신규 18-7 회귀) | **9 passed** |
| `test_admin_ui_smoke.py` (신규 18-7 smoke) | **14 passed** |
| 18-0~18-6 회귀 묶음 (전체) | **410 passed** |
| **전체 tests** | **470 passed, 1 skipped, 7 xfailed, 27 warnings** |
| ruff (`app tests scripts`) | **All checks passed!** |
| check_db_path | OK (테스트 중 격리, 단독 실행 INFO 의도) |

baseline:
- 18-6: 410 passed, 1 skipped, 7 xfailed
- 18-7: 470 passed (+60), 1 skipped, 7 xfailed

## 8. 자동 수정 루프 횟수

**1/5 회차** — 1회차에 모든 테스트 통과.

1회차 사이클:
- 코드 작성 → 신규 60 tests 14 failed (alias shadowing: import alias `ai_health` 가
  router 의 `def ai_health(...)` 함수와 충돌 → `'function' object has no attribute
  'build_admin_status'` AttributeError)
- 즉시 수정: import alias `ai_health` → `ai_status_mod` 변경 → 60/60 통과
- 회귀 묶음 410 passed (회귀 0)
- ruff 2 import-order 경고 → `--fix` 자동 정리 → 통과
- 전체 470 passed
- 동일 1회차 안에서 마무리.

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
- 테스트 중 격리는 `tests/conftest.py` 4단계 격리 +
  `test_status_does_not_use_operational_db` + `test_status_endpoint_does_not_use_operational_db` 통과.

## 11. RAG 하네스 결과

| 하네스 | 결과 |
|---|---|
| 18-0 RAG harness | 통과 |
| 18-2 manual RAG (18 tests) | 통과 |
| 18-3 chunker harness (35 tests) | 통과 |
| 18-4 reindex harness (24 tests) | 통과 |
| 18-5 vector harness (36 tests) | 통과 |
| 18-6 hybrid harness (46 tests) + ai_assist mode (15 tests) | 통과 |
| 18-7 health_status (37 tests) + contract_manual (9 tests) + admin_ui_smoke (14 tests) | **통과 (신규)** |

## 12. API 계약 테스트 결과 (응답 스키마 회귀)

- `test_ai_manual_rag_contract.py` 9 passed (18-1) — manual/{search,ask} 9키/3키 보존.
- `test_ai_contract_manual.py` 9 passed (18-7 신규) — `/api/ai/status` 추가 후에도
  manual/* 응답 키 동일 입증 + 신규 optional 키 (reason_code/llm_called/embedding_called/ai_mode/prompt_version) 부재 단언.
- `test_ai_health_public.py` 4 passed — `/api/ai/health/public` 4키 / `/api/ai/health` 9키 보존.
- `test_admin_ui_smoke.py` 14 passed — 라우트 등록 / 권한 일관성 / 응답 sanity.

## 13. 할루시네이션 금지 테스트 결과

`test_ai_safety_harness.py` 12 passed + `test_ai_hallucination.py` /
`test_ai_sms_draft_hallucination.py` 통과 (전체 470 passed 에 포함).

본 세션은 LLM 호출 0 (read-only 집계) 이라 할루시네이션 자체 발생 가능성 0.

## 14. PII 보호 테스트 결과

- `test_get_recent_logs_recent_entries_no_pii` — recent[] 항목 9키만 노출, prompt_hash/response_hash 부재.
- `test_status_endpoint_does_not_leak_prompt_or_response_hash` — 라우터 통합 단언.
- `test_build_admin_status_no_api_key_in_response` — API key 평문 부재.
- `test_status_response_does_not_contain_api_key` — 마스킹 형식 (`test****`) 도 부재 +
  `api_key_masked` 키 자체 부재 + `api_key` 키 자체 부재.
- error_detail 200자 cap 검증.
- `recent[].error_detail` 가 ai_logging.py insert 시 이미 PII/원문 금지 + 500자 cap 적용된 값을 추가 200자 cap.

## 15. 기존 SMS AI 회귀 테스트 결과

`test_ai_sms_draft.py` / `test_ai_sms_validate.py` / `test_ai_sms_draft_hallucination.py`
통과 (전체 470 passed 에 포함). sms_draft / sms_validate 라우트 무수정.

## 16. 기존 휴무 AI 회귀 테스트 결과

`test_ai_action_leave.py` 통과 (전체 470 passed 에 포함). action_leave 라우트 무수정.

## 17. 남은 위험 요소

1. **main.html UI 통합 미구현** — 사용자 18-7 정책 (API 만 구현). UI 통합은 18-8
   또는 별도 UI 세션에서 처리. 현재 상태 API 는 admin 도구/Postman 으로 호출 가능.
2. **`/api/ai/reindex` POST 엔드포인트 미구현** — 사용자 18-7 지시문 "새 AI 기능 범위
   확장 금지" 보수 해석. 18-8 또는 별도 세션 결정.
3. **AiSetting `ai_mode` / `AI_RAG_VECTOR_ENABLED` / `AI_RAG_HYBRID_ENABLED` /
   `alpha`/`beta` 컬럼 미도입 (m014 미생성)** — 사용자 명시 금지. 따라서 derive_ai_mode 는
   enabled/api_key/model 조합으로 자동 파생, derive_vector_status 는 항상 disabled 반환.
4. **응답 optional 키 (reason_code/llm_called/embedding_called/ai_mode/prompt_version) 미노출**
   — 18-7 체크리스트의 "신규 optional 키 5개 추가" 미수행. 사용자 명시 금지 "기존 API
   응답 key 변경 금지" 의 보수 해석. 18-8 에서 결정.
5. **pipeline 의 hybrid_retrieve 통합 미수행** — pipeline.run_manual_ask 가 여전히
   keyword_retrieve 만 사용. 18-7 지시문 "vector/hybrid 로직 재작성 금지" 준수.
6. **PyInstaller spec hidden import 미추가** — 사용자 본 세션 명시 금지.
   `app.services.ai.health` hidden import 추가는 사용자 승인된 빌드 세션에서.
7. **LLM 호출 수 today/week 집계 미구현 (rollout_plan §7)** — 현재는 lookback 24h
   카운트로 갈음. by_outcome["success"] 카운트가 LLM 호출 수의 proxy.
8. **권한 체계 미확장** — 사용자 18-7 정책 "권한 구조가 이미 없다면 무리하게 대규모
   권한 시스템을 만들지 말고 관리자 영역 내 표시로 제한". `require_admin` 단일 게이트만 사용.

## 18. Codex가 집중 검토할 파일

| 파일 | 이유 |
|---|---|
| `app/services/ai/health.py:build_admin_status` | 단일 진입점 — top-level 키 9개 / api_key 평문 부재 / hash 부재 / read-only 집계 정합 |
| `app/services/ai/health.py:derive_ai_mode` | 18-7 시점 자동 파생 룰 (enabled/key/model 조합) — m014 도입 후 호환 정책 |
| `app/services/ai/health.py:derive_vector_status` | m014 미도입 시 항상 disabled 반환 + 미래 확장 자리 |
| `app/services/ai/health.py:get_recent_logs` | recent[] 9키 제한 + error_detail 200자 cap + lookback 윈도우 정확성 |
| `app/services/ai/health.py:_serialize_log_row` | prompt_hash/response_hash 노출 0 입증 |
| `app/routers/ai.py:ai_status` | require_admin gate + setting 로드 + sdk_installed 주입 + 응답 직렬화 정확 |
| `tests/test_ai_health_status.py` | 37개 단언이 의도한 보호를 정확히 검증 |
| `tests/test_ai_contract_manual.py` | 9개 단언이 manual/* 응답 회귀 0 + 신규 optional 키 부재 입증 |
| `tests/test_admin_ui_smoke.py` | 14개 단언이 라우트/권한/UI 정책 sanity |

## 19. Codex가 반드시 확인할 체크리스트

- [ ] `/api/ai/status` 응답에 `api_key` / `api_key_masked` 키 부재
      (`test_status_response_does_not_contain_api_key` 가 단언)
- [ ] fixture `test-fake-key` 평문 + 마스킹 (`test****`) 모두 응답 본문 부재
- [ ] `recent[]` 항목에 `prompt_hash` / `response_hash` 키 부재
      (`test_status_endpoint_does_not_leak_prompt_or_response_hash`)
- [ ] `error_detail` 200자 cap 동작 (`test_get_recent_logs_recent_entries_no_pii`)
- [ ] `/api/ai/status` 호출이 AiUsageLog 행을 추가하지 않음 (polling 안전)
- [ ] `/api/ai/manual/{search,ask}` 응답 9키/3키 정확히 보존 + 신규 키 부재
- [ ] `/api/ai/health` admin 9키 / `/api/ai/health/public` 4키 보존
- [ ] `/api/ai/status` admin 토큰 강제 (토큰 없으면 401)
- [ ] hybrid retriever / reranker / confidence 모듈 무수정 (`git diff app/services/ai/rag/`)
- [ ] vector 모듈 무수정 (`git diff app/services/ai/vector/`)
- [ ] `app/migrations/m001~m013` 무수정
- [ ] `app/templates/main.html` 무수정 (`git diff app/templates/main.html`)
- [ ] `pyproject.toml` 무수정
- [ ] `requirements.txt` 무수정
- [ ] **`dosu_clinic.spec` 무수정** (`git diff dosu_clinic.spec`)
- [ ] `tests/conftest.py` 무수정
- [ ] derive_ai_mode 자동 파생 룰 정합 (enabled+key+model → local_first, 그 외 → local_only)
- [ ] derive_vector_status 가 18-7 시점 항상 disabled 반환 (m014 미도입 정책)
- [ ] derive_search_mode 가 18-7 시점 항상 keyword 반환 (pipeline 미통합 정책)
- [ ] `build_admin_status` 호출이 LLM/Embedding provider 인스턴스화 0
- [ ] /api/ai/status 가 conftest 격리 DB 만 사용

## 20. 다음 세션으로 넘어가도 되는지 자체 판단

**yes** — 18-8 (final release / PyInstaller 검증) 또는 별도 UI 통합 세션 진입 OK.

근거:
1. 신규 60 tests + 18-6 baseline 410 = 470 passed (회귀 0)
2. ruff 0 error, check_db_path 통과
3. 사용자 18-7 지시문 13개 금지 항목 100% 준수
4. v1.3.3 응답 9키/3키/4키/9키 후방호환 완전 보존
5. API key / PII / hash 노출 0 입증 (보호 단언 통과)
6. 외부 LLM/Embedding 호출 0 (read-only 집계)
7. 1회차 통과 (5회 미만, alias shadowing 1번 즉시 수정)
8. 모든 18-0~18-6 하네스 100% 통과 유지

위험 요소(§17) 8개 중:
- 1, 2, 4: 사용자 18-7 정책 준수 결과 (UI 통합 / reindex 버튼 / optional 키 노출은 별도 세션 결정).
- 3, 5: 사용자 명시 금지 (m014 미생성 / hybrid 재통합 X) 준수 결과.
- 6: 사용자 본 세션 명시 금지 (spec 수정 X) 준수 — 빌드 세션에서 별도 처리.
- 7: 18-8 에서 추가 가능 (현재는 lookback 24h 카운트로 갈음).
- 8: 사용자 18-7 정책 명시 (대규모 권한 시스템 만들지 말 것) 준수.

미해결 잔여:
- `tests/test_ai_sms_validate.py` 의 tuple return 27개 warning (18-4 baseline 그대로, 18-7 무관)
- main.html UI 통합 (별도 UI 세션)
- m014 (사용자 명시 금지)
