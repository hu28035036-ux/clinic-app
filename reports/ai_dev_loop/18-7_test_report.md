# 18-7 Test Report — UI / 관리자 상태 화면 구현 (상태 API)

## 1. 세션 이름

**18-7_admin_ui** — 관리자 AI/RAG 상태 조회 API (`/api/ai/status`) + read-only 집계 모듈
(`app/services/ai/health.py`) + 계약 회귀 테스트.

## 2. 환경

- 작업 디렉토리: `C:\Users\user\Desktop\새 폴더\병원예약관리\병원예약관리`
- 브랜치: `ai-rag-v1-integration`
- Python: 3.12.10 (`venv\Scripts\python.exe`)
- pytest: 8.4.2
- ruff: latest
- 격리 DB: `tests/temp/test_clinic_<uuid>.db` (운영 DB 미사용)

## 3. 실행 명령

```
venv\Scripts\python.exe -m pytest tests/test_ai_health_status.py tests/test_ai_contract_manual.py tests/test_admin_ui_smoke.py -v
venv\Scripts\python.exe -m pytest tests --tb=short -q
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
```

## 4. 결과 요약

| 묶음 | 결과 |
|---|---|
| `test_ai_health_status.py` (신규 18-7) | **37 passed** |
| `test_ai_contract_manual.py` (신규 18-7 회귀) | **9 passed** |
| `test_admin_ui_smoke.py` (신규 18-7 smoke) | **14 passed** |
| 18-0~18-6 회귀 묶음 (전체) | **410 passed** |
| **전체 tests** | **470 passed, 1 skipped, 7 xfailed, 27 warnings** |
| ruff (`app tests scripts`) | **All checks passed!** |
| check_db_path | OK (테스트 중 격리, 단독 실행 INFO 의도) |

baseline 비교:
- 18-6: 410 passed, 1 skipped, 7 xfailed
- 18-7: 470 passed (+60), 1 skipped, 7 xfailed (회귀 0)

## 5. 신규 테스트 분류 (60개)

### 5-1. `test_ai_health_status.py` (37 tests)

#### derive_ai_mode 단위 (4 tests)
- disabled / no api_key / no model → "local_only"
- 모두 충족 → "local_first"

#### derive_search_mode (1 test)
- 18-7 시점 — pipeline 미통합 → 항상 "keyword"

#### derive_vector_status (2 tests)
- m014 미도입 → enabled=False, available=False, reason="vector_disabled"

#### derive_external_api_status (4 tests)
- disabled / full setup / no sdk / unknown provider 4개 케이스

#### count_documents / chunks / vectors (3 tests)
- 모두 int + non-negative

#### get_last_reindex (3 tests)
- 행 부재 → id=None
- 최신 행 반환 — id/status/카운터/failed_paths/errors_count
- failed_paths max 절단

#### get_recent_logs (5 tests)
- 빈 상태 / outcome+feature 집계 / recent[] PII 부재 / limit cap / lookback 윈도우

#### get_prompt_versions (2 tests)
- dict 반환 / copy 반환 (외부 변경 무영향)

#### build_admin_status 통합 (6 tests)
- 8개 최상위 키 / api_key 평문 부재 / disabled→local_only / enabled→local_first /
  knowledge 카운트 int / LLM 호출 0

#### 라우터 통합 (7 tests)
- admin 토큰 필수 / 200 + 키 / api_key 부재 / hash 부재 / polling 안전 /
  운영 DB 미사용 / 상수 sane

### 5-2. `test_ai_contract_manual.py` (9 tests)

- manual/search 응답 3키 보존 + 신규 키 추가 0 입증
- manual/ask 응답 9키 보존 + 신규 키 추가 0 입증
- 신규 optional 키 (reason_code/llm_called/embedding_called/ai_mode/prompt_version) 부재 단언
- sources[] 항목 3키 보존
- /api/ai/status 호출 후 manual/ask 응답 영향 0
- /api/ai/status 호출 후 manual/search 응답 영향 0
- /api/ai/health/public 4키 보존
- /api/ai/health admin 9키 보존

### 5-3. `test_admin_ui_smoke.py` (14 tests)

- /api/ai/status 라우트 등록 검증
- 기존 9개 AI 라우트 그대로 등록
- 권한 일관성 (status / health admin = 401, public 200)
- top-level 9키 sanity
- ai_mode 표준 3개 모드 중 하나
- search_mode = keyword (18-7 시점)
- knowledge counts int
- vector_status disabled (m014 미도입)
- prompt_versions["manual_qa.system"] = "v1"
- recent_ai_logs 구조 (lookback/total/by_outcome/by_feature/recent)
- API key 평문 + 마스킹 (`test****`) 모두 부재 + `api_key_masked` 키 부재
- 운영 DB 미사용
- main.html 무수정 (18-7 정책)

## 6. 변경 파일 목록

### 신규 (4 코드 + 3 리포트)
- `app/services/ai/health.py` (~340줄) — read-only 상태 집계 모듈
- `tests/test_ai_health_status.py` (~360줄, 37 tests)
- `tests/test_ai_contract_manual.py` (~180줄, 9 tests)
- `tests/test_admin_ui_smoke.py` (~200줄, 14 tests)
- `reports/ai_dev_loop/18-7_test_report.md` (본 파일)
- `reports/ai_dev_loop/18-7_fix_summary.md`
- `reports/ai_dev_loop/18-7_codex_review_request.md`

### 수정 (1)
- `app/routers/ai.py` — import 추가 (`from ..services.ai import health as ai_status_mod`)
  + `@router.get("/status")` 엔드포인트 (~40줄). 기존 라우트 / 함수 무수정.

### 무수정 (회귀 보호)
- `app/services/ai/manual_qa.py`
- `app/services/ai/rag/{pipeline,prompts,safety,schemas,reranker,confidence,retriever}.py`
- `app/services/ai/{provider,pii,sms_draft,action_leave,ai_logging}.py`
- `app/services/ai/vector/{embeddings,store,similarity}.py`
- `app/services/ai/knowledge/{indexer,chunker,loader,normalizer,keyword_index}.py`
- `app/migrations/m001~m013.py` (m014 미생성 — 사용자 명시 금지)
- `app/models/models.py`
- `app/templates/main.html` (사용자 18-7 정책: API 만 구현, UI 통합은 별도 세션)
- `app/static/css/app.css`
- `tests/conftest.py`, `tests/harness/*.py`
- `pyproject.toml`, `requirements.txt`, `dosu_clinic.spec`

## 7. 자동 수정 루프 횟수

**1/5 회차** — 1회차에 모든 테스트 통과.

1회차 사이클:
- 코드 작성 → 신규 60 tests 14 failed (import alias 충돌: `ai_health` 이름이 라우터의 `def ai_health(...)` 함수와 shadowing)
- 즉시 수정: import alias `ai_health` → `ai_status_mod` 변경 → 60/60 통과
- 회귀 묶음 410 passed (회귀 0)
- ruff 2 import-order 경고 → `--fix` 자동 정리 → 통과
- 전체 470 passed
- 동일 1회차 안에서 마무리.

## 8. 5회 실패 여부

**아니오.** 1회차 통과 (alias shadowing 1번 즉시 수정).

## 9. 운영 DB 보호 검사 결과

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

## 10. 핵심 단언 결과

| 항목 | 결과 |
|---|---|
| /api/ai/status 라우트 등록 | ✅ test_status_route_registered_in_app |
| admin 토큰 강제 | ✅ test_status_endpoint_requires_admin_token |
| API key 평문 노출 0 | ✅ test_build_admin_status_no_api_key_in_response, test_status_response_does_not_contain_api_key |
| API key 마스킹 형식조차 노출 0 | ✅ test_status_response_does_not_contain_api_key (`test****` 없음) |
| prompt/response hash 노출 0 | ✅ test_status_endpoint_does_not_leak_prompt_or_response_hash |
| AiUsageLog 기록 0 (polling 안전) | ✅ test_status_endpoint_polling_safe_no_log_written |
| LLM/Embedding 호출 0 | ✅ test_build_admin_status_does_not_call_llm_provider |
| AI 모드 파생 정확 | ✅ derive_ai_mode 4개 케이스 |
| 검색 모드 = keyword (18-7) | ✅ test_status_search_mode_keyword_in_18_7 |
| vector_status disabled (m014 미도입) | ✅ test_status_vector_status_disabled_in_18_7 |
| knowledge 카운트 정확 | ✅ count_documents/chunks/vectors |
| last_reindex 요약 정확 | ✅ get_last_reindex 3 tests |
| recent_ai_logs 집계 + PII 부재 | ✅ get_recent_logs 5 tests |
| manual/{search,ask} 응답 키 회귀 0 | ✅ test_18_7_manual_*_keys_preserved |
| /api/ai/status 가 manual/* 영향 0 | ✅ test_18_7_status_call_does_not_affect_manual_* |
| /api/ai/health/public 4키 보존 | ✅ test_18_7_health_public_keys_unchanged |
| /api/ai/health admin 9키 보존 | ✅ test_18_7_health_admin_keys_unchanged |
| main.html 무수정 | ✅ test_main_html_unchanged_in_18_7 |
| 기존 9개 AI 라우트 등록 | ✅ test_existing_ai_routes_still_registered |

## 11. 외부 API 호출 차단 검증

- `health.build_admin_status` 는 read-only DB 집계만 — provider/embedding 인스턴스화 0.
- conftest `_block_sdk_modules` 가 openai/anthropic SDK 클래스를 raise stub 으로 교체.
- 모든 status 엔드포인트 호출 테스트에서 외부 호출 발생 0.

## 12. PII / API key 보호

- API key:
  - `ai_settings.api_key_set` boolean 만 노출
  - 평문 (`sk-very-secret-...`) / 마스킹 (`test****`) / 키 자체 (`api_key_masked` / `api_key`) 모두 응답에 부재.
  - `test_status_response_does_not_contain_api_key` 가 fixture 의 `test-fake-key` 부재 단언.
- AI 로그 PII:
  - `recent[]` 항목에 `prompt_hash` / `response_hash` 미노출 (해시지만 진단 가치 0).
  - `error_detail` 200자 cap (DB 컬럼 500자 → 노출 200자).
  - 표시 키 9개로 제한: ts/feature/outcome/provider/model/latency_ms/pii_filter_hits/hallucination_guard_hits/error_detail.
  - `test_get_recent_logs_recent_entries_no_pii` 가 단언.
- `error_detail` 자체는 이미 insert 시 `_truncate(text, 500)` + "PII/원문 금지" 정책.

## 13. 아직 후속 세션에 남기는 것

| 항목 | 시점 |
|---|---|
| main.html 관리자 탭 통합 (status API 호출 + 표시) | 18-8 또는 별도 UI 세션 |
| /api/ai/reindex POST 엔드포인트 (admin) | 18-8 또는 별도 세션 (사용자 18-7 지시문 "새 AI 기능 범위 확장 금지") |
| Reindex 실행 버튼 UI | UI 세션 |
| AiSetting `ai_mode` / `AI_RAG_HYBRID_ENABLED` / `alpha`/`beta` 컬럼 (m014) | 18-8 또는 별도 세션 |
| `pipeline.run_manual_ask` 의 hybrid_retrieve 통합 | 별도 세션 |
| 응답 optional 키 (reason_code/embedding_called/ai_mode/prompt_version) 노출 | 18-8 또는 별도 세션 |
| PyInstaller spec hidden import (`app.services.ai.health`) | 사용자 승인된 빌드 세션 |
| LLM 호출 수 today/week 집계 (rollout_plan §7) | 18-8 (현재는 lookback 24h 카운트로 갈음) |
