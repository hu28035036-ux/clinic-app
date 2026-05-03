# 18-7 Fix Summary — UI / 관리자 상태 화면 구현 (상태 API)

## 작업 목표 (사용자 지시문 그대로)

- 관리자에서 AI/RAG 상태를 확인할 수 있는 화면 또는 상태 API 구현
- AI 모드(local_only / local_first / ai_assist) 표시
- 검색 모드(keyword / vector / hybrid / disabled) 표시
- Knowledge 문서 수, chunk 수, vector 수 표시
- 마지막 reindex 시간/결과 표시
- vector 사용 가능 여부 표시
- 외부 API 사용 가능 여부 표시
- prompt_version 표시
- 최근 AI 상태/차단/오류 요약 표시
- 기존 manual RAG / safety / full / chunker / reindex / vector / hybrid 하네스 유지

## 세션 결정 (사용자 지시문 + 18-7 체크리스트 해석)

**API 만 구현, UI 미터치.** 사용자 지시문 "화면 또는 상태 API" 중 후자 선택. 이유:
1. 사용자 명시 금지 항목이 광범위 (응답 키 변경 / 새 migration / 새 AI 기능 / spec 수정 / requirements 수정).
2. main.html 통합 + Reindex 버튼 추가는 추가 코드 path + 새 엔드포인트 (POST /reindex)
   를 요구 — "새 AI 기능 범위 확장 금지" 와 충돌 가능.
3. 상태 API 만으로 사용자 목표 9개 항목 모두 노출 가능 (테스트로 입증).
4. UI 통합은 18-8 또는 별도 UI 세션에서 안전하게 처리 가능.

## 변경 파일 목록

### 신규 (4 코드 + 3 리포트)

| 파일 | 줄 | 역할 |
|---|---|---|
| `app/services/ai/health.py` | ~340 | read-only 상태 집계 모듈 — `build_admin_status` 단일 진입점 + 7개 도메인 함수 (derive_ai_mode / derive_search_mode / derive_vector_status / derive_external_api_status / count_documents·chunks·vectors / get_last_reindex / get_recent_logs / get_prompt_versions) |
| `tests/test_ai_health_status.py` | ~360 | derive_*/count_*/get_* 단위 + build_admin_status 통합 + 라우터 통합 = **37 tests** |
| `tests/test_ai_contract_manual.py` | ~180 | manual/{search,ask} 응답 9키/3키 + sources[] 3키 보존 + /status 호출 영향 0 = **9 tests** |
| `tests/test_admin_ui_smoke.py` | ~200 | 라우트 등록 / 권한 일관 / 응답 sanity / API key 부재 / main.html 무수정 = **14 tests** |
| `reports/ai_dev_loop/18-7_test_report.md` | — | 테스트 결과 보고 |
| `reports/ai_dev_loop/18-7_fix_summary.md` | — | 본 파일 |
| `reports/ai_dev_loop/18-7_codex_review_request.md` | — | Codex 검증 요청서 |

### 수정 (1)

| 파일 | 변경 내용 |
|---|---|
| `app/routers/ai.py` | import 1줄 추가 (`from ..services.ai import health as ai_status_mod`) + `@router.get("/status")` 엔드포인트 1개 (~40줄). 기존 함수/라우트 무수정. |

> import alias 는 `ai_status_mod` 사용 — `ai_health` 는 라우터에 이미 정의된 `def ai_health(...)` 함수와 shadowing 충돌 발생 (1차 시도 시 14개 테스트 fail → 즉시 alias 변경 후 통과).

### 무수정 — 본 18-7 세션에서 추가 변경 0

> **참고 (Codex 18-7 검토 M-2 응답)**: 작업트리 git diff 에 일부 파일 (`tests/conftest.py`,
> `app/models/models.py`, `app/services/ai/manual_qa.py`, `.gitignore`) 의 누적
> diff 가 보이지만, 이들은 18-0~18-6 세션에서 staged 된 누적 변경이며 18-7 세션에서는
> **추가 수정 0**. 18-7 의 실제 변경은 `app/routers/ai.py` (+42줄) + `app/services/ai/health.py`
> (신규) + 테스트 3개 + 리포트 3개로 한정.

#### 18-0~18-6 누적 (18-7 추가 수정 0)
- `tests/conftest.py` — 18-0 격리/FakeProvider/SDK 차단 (132줄 추가)
- `app/models/models.py` — 18-4/18-5 KnowledgeChunk/KnowledgeVector ORM (123줄 추가)
- `app/services/ai/manual_qa.py` — 18-2 wrapper 분리 (298줄 변동)
- `.gitignore` — 1줄 추가 (이전 세션)

#### 18-7 무수정 (diff 0 — 본 세션 변경 없음)
- `app/services/ai/rag/{pipeline,prompts,safety,schemas,reranker,confidence,retriever}.py`
- `app/services/ai/{provider,pii,sms_draft,action_leave,ai_logging,date_resolver,validators}.py`
- `app/services/ai/vector/{__init__,embeddings,store,similarity}.py`
- `app/services/ai/knowledge/{indexer,chunker,loader,normalizer,keyword_index,__init__}.py`
- `app/migrations/m001~m013.py` (m014 미생성 — 사용자 명시 금지)
- `app/templates/main.html` (사용자 18-7 정책: API 만 구현)
- `app/static/css/app.css`
- `tests/harness/{fake_provider,rag_harness,vector_harness,reindex_harness,safety_harness,hybrid_harness,contract,db_guard,seed_data,helpers}.py`
- `pyproject.toml`, `requirements.txt`, `dosu_clinic.spec`, `pytest.ini`

## 의도/이유

### 1. health.py — 단일 진실원천 read-only 집계

**왜 별도 모듈?**
- 라우터가 8개 카운터/derive 로직을 직접 안고 있으면 라우터 모듈이 비대해지고
  단위 테스트가 어려워짐.
- 라우터 의존성 (DB 세션 / setting / sdk_installed) 만 주입받으면, build_admin_status
  는 순수 함수로 단위 테스트 가능 (37개 tests).

**왜 `build_admin_status` 단일 진입점?**
- UI 가 한 번의 GET 으로 모든 정보를 받는 정책 (rollout_plan §7).
- 여러 엔드포인트로 쪼개면 UI 가 N번 호출 + race condition 위험.

**왜 read-only?**
- 사용자 지시문 "외부 API 호출 없이 상태 조회 가능" + "운영 DB 직접 접근 금지".
- 본 모듈은 caller 가 주입한 SQLAlchemy Session 만 사용 (격리 검증).

### 2. derive_ai_mode — AiSetting 컬럼 미도입 환경에서의 안전 파생

**왜 컬럼 추가하지 않고 파생?**
- 사용자 명시 금지: "새로운 DB 테이블/migration 생성 금지".
- AiSetting 에 `ai_mode` 컬럼 추가는 m014 가 필요 — 18-7 범위 외.
- 현재 enabled/api_key/model 조합으로 effective 모드 자동 판정:
  - `enabled=False` 또는 `api_key 없음` 또는 `model 없음` → `local_only` (실질적으로 LLM 호출 불가).
  - 그 외 → `local_first` (기본 안전 모드).
- `ai_assist` 는 명시적 운영자 토글이 필요한 모드 — 18-7 시점에는 자동 추론 X.

### 3. derive_search_mode — 18-7 시점 항상 keyword

**왜 항상 keyword?**
- `pipeline.run_manual_ask` 가 `keyword_retrieve` 만 사용 (18-2 그대로).
- hybrid retriever (18-6) 는 만들어졌지만 라우터에 wire-in 안됨 — 별도 함수 (`hybrid_retrieve`) 로만 존재.
- 사용자 18-7 지시문: "vector/hybrid 로직 재작성 금지" → 18-7 에서는 pipeline 통합 X.
- 따라서 effective 검색 모드는 keyword. UI 가 "현재 keyword 모드입니다" 표시.

### 4. derive_vector_status — m014 미도입 = 항상 disabled

**왜 항상 disabled?**
- `AI_RAG_VECTOR_ENABLED` flag 컬럼이 AiSetting 에 없음 (m014 가 추가할 예정).
- 18-7 시점은 vector path 가 라우터/UI 어디에도 wire 되지 않음.
- 따라서 `enabled=False`, `available=False`, `reason="vector_disabled"` 가 정확한 표현.

### 5. recent_ai_logs — PII / 해시 미노출

**왜 9개 키만 노출?**
- AiUsageLog 는 `prompt_hash` / `response_hash` 컬럼 보유 (sha256). 해시지만 진단 가치 0
  → UI 노출 X.
- `error_detail` 은 이미 insert 시 500자 cap + PII/원문 금지 정책. 본 모듈은 추가
  200자 cap 으로 한 단계 더 보호.
- 표시 키 9개: `ts / feature / outcome / provider / model / latency_ms /
  pii_filter_hits / hallucination_guard_hits / error_detail`.
- `test_get_recent_logs_recent_entries_no_pii` 가 정확히 이 9키만 단언.

### 6. polling 안전 — `/api/ai/status` 가 AiUsageLog 안 남김

**왜?**
- 관리자 화면은 짧은 주기 새로고침 (예: 5초 마다) 가능.
- 호출마다 AiUsageLog 행 추가 시 로그 폭증 + 비용.
- 기존 `/api/ai/health` / `/api/ai/health/public` 와 동일 정책 — health 는 polling 빈도 가정.
- `test_status_endpoint_polling_safe_no_log_written` 가 3회 호출 후 AiUsageLog count 0 단언.

### 7. main.html 무수정 정책

**왜?**
- 사용자 18-7 지시문 "화면 또는 상태 API" — 둘 중 하나.
- main.html 은 5000+줄 대규모 파일. UI 통합 추가는 별도 세션에서 신중히 진행.
- API 만으로 사용자 목표 9개 모두 노출 가능 — `test_status_response_top_level_keys_sane` 등 14개
  smoke tests 로 입증.
- main.html 변경 0 입증: `test_main_html_unchanged_in_18_7` 가 source 검사로 단언.

## 테스트 통과 요약

```
tests/test_ai_health_status.py    : 37 passed
tests/test_ai_contract_manual.py  : 9 passed
tests/test_admin_ui_smoke.py      : 14 passed
회귀 묶음 (18-0~18-6 전체)        : 410 passed
전체 tests                        : 470 passed, 1 skipped, 7 xfailed, 27 warnings
ruff (app tests scripts)         : All checks passed!
check_db_path                    : OK (테스트 중 격리, 단독 실행은 의도된 INFO)
```

baseline:
- 18-6: 410 passed
- 18-7: 470 passed (+60, 회귀 0)

## 사용자 명시 금지 준수 (모두 0건)

| 금지 | 위반 0 |
|---|---|
| 실제 외부 LLM/Embedding API 연동 | ✅ 0 (status 는 read-only) |
| 새로운 AI 기능 범위 확장 | ✅ 0 (read-only 집계만 추가, /reindex 버튼 / 토글 미구현) |
| 새로운 DB 테이블/migration 생성 | ✅ 0 (m014 미생성) |
| vector/hybrid 로직 재작성 | ✅ 0 (rag/reranker/confidence/retriever 무수정) |
| RAG 검색 알고리즘 대규모 변경 | ✅ 0 (pipeline 무수정) |
| 기존 API 응답 key 변경 | ✅ 0 (manual/{search,ask}/health/health-public 모두 동일) |
| 하네스/테스트 약화 | ✅ 0 (기존 410 passed 그대로) |
| 운영 DB 직접 접근 | ✅ 0 (격리 DB 만) |
| requirements.txt / spec 불필요 수정 | ✅ 0 (둘 다 무수정) |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 0 (action_leave / sms_draft 무수정) |
| API key 화면 표시 | ✅ 0 (boolean 만, 마스킹 형식조차 X) |
| 개인정보 원문 화면 표시 | ✅ 0 (recent[] 9키만, hash 노출 X) |
| 운영 DB 경로 직접 접근 | ✅ 0 (DOSU_DB_PATH 격리 + 테스트 단언) |

## Codex 18-7 검토 후속 조치 (M-1 / M-2 / 사소한 개선 / 테스트 부족)

### M-1 (중간 위험): error_detail PII 마스킹 강화
- **지적**: `recent_ai_logs.recent[].error_detail` 가 200자 cap 만 하고 PII scan/mask 추가 안 함.
  저장 시점 정책에 의존 — 관리자 화면 노출 API 인 만큼 2차 보호 권장.
- **조치**:
  - `app/services/ai/health.py` 에 `_safe_error_detail()` 헬퍼 추가 — `pii.scan(text).cleaned` +
    200자 cap (마스킹 실패 시 빈 문자열 fallback).
  - `_serialize_log_row` 가 `_safe_error_detail` 사용으로 전환.
  - 신규 import: `from . import pii as _pii`.
- **테스트 추가** (6개):
  - `test_get_recent_logs_masks_pii_in_error_detail` — DB 에 PII 가 들어간 error_detail 시드 →
    응답에서 `[PHONE]`/`[BIRTH]`/`[RRN]` 마스킹 확인.
  - `test_safe_error_detail_helper_masks_phone` / `_caps_to_200_chars` /
    `_empty_returns_empty` / `_safe_text_passes_through` — 단위 테스트.
  - `test_status_endpoint_masks_pii_in_recent_logs` — 라우터 통합 단언.

### M-2 (중간 위험): 작업트리 baseline diff 명확화
- **지적**: `git diff --stat` 에 `tests/conftest.py`, `app/models/models.py`,
  `app/services/ai/manual_qa.py`, `.gitignore` 누적 diff 존재. fix_summary 의 "무수정" 주장과
  표현이 모호.
- **조치**: 본 fix_summary 의 "무수정" 섹션을 두 그룹으로 분리:
  - 18-0~18-6 누적 (18-7 추가 수정 0)
  - 18-7 무수정 (diff 0)
  → "18-7 본 세션에서 conftest.py 등에 추가 수정 0" 명시.

### 사소한 개선: assertion 정밀도 향상
- **지적**: `test_status_endpoint_no_api_key_in_response` 의 `"test-" not in body_text or "sk-" not in body_text`
  단언이 `or` 라 약함 — 둘 다 부재 단언이 의도라면 `and` 가 맞음.
- **조치**: 해당 테스트 재설계.
  - `or → and` 로 강화 시 fixture 의 `model="test-model"` 이 `"test-"` 와 충돌 발견.
  - model 은 의도적 노출 필드라 substring 단언 부적절.
  - 정확한 단언으로 변경:
    1. `"test-fake-key"` 정확 부재 + `"fake-key"` 부분 부재 (and)
    2. `ai_settings` dict 에 `api_key` / `api_key_masked` 키 부재 (set 차집합)
    3. `api_key_set` boolean 만 노출 + 타입 isinstance 단언

### 테스트 부족 보강
- **지적**: PII 가 들어간 error_detail 의 마스킹 검증 부재.
- **조치**: M-1 에 6개 신규 테스트 추가 (위 참조).

### 후속 조치 후 결과
- 신규 테스트 6개 추가 → **66 passed (18-7 신규)** + 410 (회귀) = **476 passed** 전체.
- ruff 0 error, check_db_path 통과.
- 18-7 자체 변경 추가: `health.py` (~30줄 — `_safe_error_detail` 헬퍼) + 테스트 6개 + assertion 1개 정밀화.

---

## 자체 판단

✅ **다음 세션 (18-8 final release / 또는 UI 통합 세션) 진입 OK** — Codex 검증 후.

근거:
1. 신규 60 tests + 18-6 baseline 410 = 470 passed (회귀 0)
2. ruff 0 error, check_db_path 통과
3. 사용자 18-7 지시문 13개 금지 항목 100% 준수
4. v1.3.3 응답 9키 후방호환 보존 (manual_qa / pipeline / 라우터 manual 엔드포인트 무수정)
5. v1.3.3 health public/admin 응답 키 100% 보존
6. 외부 LLM/Embedding 실제 호출 0 (read-only 집계)
7. API key / PII / hash 노출 0 (보호 단언 통과)
8. 1회차 통과 (5회 미만, alias shadowing 1번 즉시 수정)
