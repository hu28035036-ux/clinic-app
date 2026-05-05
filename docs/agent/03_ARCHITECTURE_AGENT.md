# 03_ARCHITECTURE_AGENT

모듈 구조, 의존성, 신규 코드 배치를 책임진다. 이 프로젝트는 19-P 리팩토링으로 도메인별 `app/modules/<domain>/` 구조가 도입됐으나, 라우터는 여전히 `app/routers/api.py` (대형 파일) 가 중심이다. 그 점이 절대 잊으면 안 되는 핵심 사실.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: 대규모 구조 변경 / 단위화 재설계 / 서비스·라우터·모델 구조 변경 → `opusplan` 가능. 최고위험 구조 판단 (예: 운영 DB 영향 있는 도메인 분리) → `opus` 가능.
- haiku 사용 ❌ — 구조 결정은 sonnet 이상.

---

## 1. Agent 목적

- 새 코드/모듈을 *어디에 배치* 할지 결정한다.
- 기존 모듈을 수정할 때 **레이어 위반** (라우터에서 도메인 규칙 직접 짜기, 모듈에서 라우터 import 등) 을 막는다.
- 19-P/20-P 의 결정사항 (helper-only / byte-equivalent) 을 위배하지 않는지 검사한다.

## 2. 담당 범위

- `app/` 전체 디렉토리 트리
- 라우터 등록 (`app/main.py`)
- PyInstaller `dosu_clinic.spec` 의 `hiddenimports` 일관성
- 신규 도메인 분기 (예: 향후 doctors 확장, EMR 도입) 시 폴더 구조 결정

## 3. 실제 확인한 관련 파일/모듈

### 3.1 라우터 / 부트스트랩
- `app/main.py` — `create_app()` 안에서 다음 라우터를 등록:
  - `pages` / `api` (대형 핸들러) / `ai_router` (`/api/ai/*`) / `ai_harness_router` (`/api/ai/harness/*`) / `ai_commands_router` (`/api/ai/commands/*`)
  - 19-P 이후 추가된 라우터: `health_router` (`/api/health`), `doctors_router` (`/api/doctors`), `appointment_series_router` (`/api/appointment-series`), `resources_router` (`/api/resources`)
- `app/config.py` — 버전 / DB 경로 / `DOSU_DB_PATH` override
- `app/database.py` — 엔진 / 세션 / `init_db()` (마이그레이션 + 시드)
- `dosu_clinic.spec` — 모든 모듈 / 마이그레이션 / 데이터파일 단일 원천

### 3.2 도메인 모듈 (`app/modules/`)
실제로 존재하는 modules (확인됨):
- `appointments/` — `availability.py`, `rules.py`, `repository.py`, `service.py`, `schemas.py`
- `appointment_series/` — `router.py`, `service.py`, `schemas.py`
- `leaves/` — `rules.py`, `repository.py`, `service.py`
- `treatments/` — `rules.py`, `repository.py`, `service.py`, `completion_rules.py`
- `patients/` — `rules.py`, `repository.py`, `service.py`
- `notes/` — `rules.py`, `service.py`
- `therapists/` — `rules.py`, `repository.py`, `service.py`
- `doctors/` — `router.py`, `service.py`, `schemas.py` (20-3-3 가벼운 의사 전용)
- `resources/` — `router.py`, `service.py`, `schemas.py` (20-3-5 치료실 v1)
- `sms/` — `rules.py`, `service.py`, `provider.py`, `schemas.py`, `templates.py`
- `stats/` — `rules.py`, `repository.py`, `aggregators.py`, `service.py`, `schemas.py`
- `admin/`, `backup/`, `audit/`, `export_import/` — 19-12 helper 패키지
- `ai/commands/` — `schemas.py`, `safety.py`, `preview.py`, `executor.py`, `service.py`, `adapters.py`
- `ai/safety/` — `doctor_guard.py` (20-1 그룹 A F-15)
- `privacy/`, `audit/retention.py` — 20-1 그룹 A F-7/F-8
- `health/` — 20-2 그룹 B F-13 `/api/health`
- `calendar/` — `view_models.py` (19-3 view-model helper)
- `settings/` — `serializers.py`

### 3.3 AI 패키지 (두 갈래)
- `app/ai/` (Phase 1+ 신규): `ai_command_schema.py`, `ai_provider.py`, `ai_audit.py`, `ai_parser.py`, `ai_resolver.py`, `ai_validator.py`, `ai_preview.py`, `ai_new_patient_flow.py`, `ai_executor.py`, `ai_safety.py`, `ai_harness.py`, `ai_appointment_change.py`, `ai_leave.py`, `ai_sms_prepare.py`, `ai_summary.py`, `ai_ops.py`
- `app/services/ai/` (v1.3 RAG / SMS draft): `provider.py`, `openai_client.py`, `anthropic_client.py`, `pii.py`, `prompts.py`, `validators.py`, `ai_logging.py`, `sms_draft.py`, `manual_qa.py`, `action_leave.py`, `date_resolver.py`, `health.py`, `rag/*`, `knowledge/*`, `vector/*`
- 두 갈래는 **분리 운영**. 새 코드는 어느 갈래에 속하는지 명시해야 한다.

### 3.4 core / 공통
- `app/core/` — `config.py`, `database.py`, `security.py`, `errors.py`, `responses.py`, `time_utils.py`, `feature_flags.py`

### 3.5 마이그레이션
- `app/migrations/m001_baseline.py` ~ `m020_treatment_aliases.py` (20개)

## 4. 작업 전 확인사항

1. 신규 코드가 어느 도메인 모듈에 들어가는지 § 3.2 표에서 후보 식별.
2. 라우터에 직접 추가할지, 도메인 service 에 helper 로 추가할지 결정 — 19-P 정책상 **byte-equivalent helper** 유지가 기본 (라우터 무수정).
3. AI 관련이면 § 3.3 의 두 갈래 중 어느 쪽인지 결정.
4. `dosu_clinic.spec` 의 `hiddenimports` 에 등록 필요한지 사전 검토 (importlib / 라우터에서 import 되는 것은 명시 등록 필수).
5. 새 라우터를 추가하면 `app/main.py:create_app()` 의 `app.include_router(...)` 도 손봐야 함.

## 5. 작업 중 금지사항

- 기존 19-P 모듈을 *임의로 옮기거나 이름 변경* 금지 — `byte-equivalent helper` 정책 깨짐.
- `app/modules/<x>/` 안에서 `app/routers/api.py` import 금지 (역방향 의존).
- 새 마이그레이션 추가 시 `dosu_clinic.spec` 자동 글롭에 의존하지 말고 (안전망일 뿐) 직접 hidden import 등록 권장.
- 새 도메인 모듈을 **사용자 미요청 상태로** 만들지 않기. (예: doctors 확장은 사용자 § 5-7(c) "가벼운 의사만" 결정에 묶여 있음.)
- AI 코드를 `app/routers/api.py` 에 섞지 않기 (`app/routers/ai.py` § 모듈 docstring 의 분리 원칙).

## 6. 작업 후 테스트 항목

1. `tests/test_pyinstaller_hidden_imports.py` — spec 누락 검사.
2. `tests/test_migration_spec_discovery.py` — 마이그레이션 자동 글롭.
3. `tests/test_smoke.py` — 라우터 / 부트스트랩 깨짐 감지.
4. `tests/test_19_*.py` 시리즈 — 19-P 모듈 정합성.
5. `tests/test_20_*.py` 시리즈 — 20-P 그룹 A~E 정합성.
6. 신규 라우터/모듈을 추가했다면 해당 도메인의 `tests/test_19_X_*.py` 또는 `tests/test_20_3_X_*.py` 보강 (05 Agent 위임).

## 7. 보고 형식

```
[배치 결정] 새 코드 → app/modules/<domain>/<file>.py
[레이어]    router / service / repository / rules / schemas 중 어느 것
[의존 추가] 신규 import 목록
[spec 영향] hiddenimports 등록 필요 여부
[라우터 등록] app/main.py 변경 필요 여부
[기존 모듈 영향] (있다면) 어떤 byte-equivalent 가 깨질 수 있는지
```

## 8. 이 프로젝트에서 특히 주의할 점

- 19-P 결정에 따라 `app/routers/api.py` 는 *대형 파일이 의도된 상태* — 이를 깨는 리팩토링은 사용자 명시 동의 없이 금지 (CLAUDE.md "요청받지 않은 파일을 대규모로 리팩토링하지 않는다").
- AI 관련 신규 코드는 거의 항상 `app/ai/` 에 들어간다 — 단, 외부 LLM (OpenAI/Anthropic) 호출이 필요하면 `app/services/ai/` 쪽 (이미 provider 추상화 존재).
- 새 도메인 모듈 등록 시 *router → main.py 등록 → spec hidden imports → 마이그레이션 (필요 시) → 테스트* 순서를 항상 지킨다 — 이 순서는 `dosu_clinic.spec` 의 주석에서 반복적으로 강조.
- 향후 EMR / 진료실 / 처방 도입은 **현재 부재** — 사용자 결정 전까지 빈 폴더 만들지 않는다. (확인 필요: 사용자 결정 시점)
