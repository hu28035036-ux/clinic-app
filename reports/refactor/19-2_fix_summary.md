# 19-2 settings / feature_flags / health 경계 정리 — 변경 요약

> 19-2 = **두 번째 실제 코드 리팩토링 세션**. `app/modules/{settings,health}/` 후보 구조 신설 +
> `app/core/feature_flags.py` 보강 + `app/core/responses.py:HEALTH_PUBLIC_KEYS` 보정.
> 5회 루프 1회차에 통과 (585 passed) — 19-1 baseline 회귀 0.

## 0. 메타

- 세션 이름: **19-2 settings / feature_flags / health 경계 정리**
- 검증일: 2026-05-03
- 시작 HEAD: `2cccc8c` (19-1 r2 — core 신설 + Codex r1+r2 검증 통과)
- 직전 19-1 Codex: pass — yes 19-2 진입 가능

## 1. 변경 파일 목록

### 신규 (4개) — `app/modules/` 후보 구조

| 파일 | 라인 수 | 종류 | 책임 |
|---|---|---|---|
| `app/modules/__init__.py` | 14 | 신규 | modules 패키지 facade docstring + D-4 정합 명시 |
| `app/modules/settings/__init__.py` | 27 | 신규 | settings 패키지 facade docstring + COMPAT/SAFETY 명시 |
| `app/modules/settings/serializers.py` | **183** | 신규 helper | AI / SMS / SystemSetting 직렬화 helper (ORM 인스턴스 read-only, 신규 라우터 ⊥) |
| `app/modules/health/__init__.py` | **57** | re-export wrapper | `app.services.ai.health` 의 24개 공개 API re-export (COMPAT) |

### 신규 (1개) — 19-2 contract 테스트

| 파일 | 라인 수 | 종류 | 책임 |
|---|---|---|---|
| `tests/test_19_2_settings_health_boundary.py` | **351** | 신규 contract | 32 테스트 (pure-input vs ORM 회귀 + serializer 회귀 + re-export 동등 + D-4 단방향 + 외부 API 0 + env helper + 응답 키 검증) |

### 수정 (4개) — 보강 / 보정

| 파일 | 변경 | 이유 |
|---|---|---|
| `app/core/feature_flags.py` | **+114 lines** (126 → 240) | 19-2 pure-input helper 3개 추가 (`derive_ai_mode_from_inputs` / `derive_vector_status_from_inputs` / `derive_external_api_status_from_inputs`) — `health.py:derive_*` 와 동등한 출력. ORM/DB 의존 0. docstring SAFETY/NOTE/RISK 보강. |
| `app/core/responses.py` | **-1, +9 lines** (110 → 118) | `HEALTH_PUBLIC_KEYS` 19-1 placeholder (`ai_enabled / ai_ready / version / node_id`) → 실제 응답 키 (`enabled / ready / provider / api_key_set`) 보정 + 19-2 보정 사유 COMPAT 주석. |
| `dosu_clinic.spec` | **+5 lines** | 19-2 modules 4개 hidden imports 추가 (`app.modules`, `app.modules.settings`, `app.modules.settings.serializers`, `app.modules.health`) + 19-2 분류 주석. |
| `tests/test_pyinstaller_hidden_imports.py` | **+22 lines** | `EXPECTED_19_X_MODULES_MODULES` (4개) + parametrized 2 tests 추가 (8 신규 검증). |

### 무수정 (회귀 보호) — 19-2 절대 금지 범위

`app/routers/api.py`, `app/routers/ai.py`, `app/services/ai/health.py`,
`app/services/ai/manual_qa.py`, `app/services/ai/action_leave.py`, `app/services/ai/sms_draft.py`,
`app/services/ai/provider.py`, `app/services/auth.py`, `app/config.py`, `app/database.py`,
`app/models/**`, `app/migrations/m001~m013.py`, `app/templates/**`, `app/static/**`,
`requirements*.txt`, `pyproject.toml`, `tests/conftest.py`, `tests/harness/**`,
기존 모든 비-19-2 테스트 (`test_pyinstaller_hidden_imports.py` 제외).

## 2. 본 세션 의도 / 이유

### 의도

19-P-2 §2-1 V2 트리의 `app/modules/{settings,health}/` 자리를 *최소 범위* 로 신설.
`app/core/feature_flags.py` 에 *pure-input* helper 추가. 19-12 admin/settings 분리 / 19-13 AI commands /
post-19-P (M-28) `/api/health` 신설 세션이 점진적으로 채택할 수 있는 *facade* 만 마련.

### 이유

1. **사용자 명시 "관리자 화면 자체를 새로 크게 만들지 마세요" + "기존 endpoint 응답 key 변경 ⊥"**:
   `app/routers/api.py` / `app/routers/ai.py` / `app/services/ai/health.py` 는 *무수정*. modules 는
   facade / re-export wrapper / 직렬화 helper 만 정의. 신규 라우터 ⊥.
2. **사용자 명시 "기존 설정 저장 방식이 있으면 그대로 유지하고, 새 저장소를 만들지 마세요"**:
   `SystemSetting` / `SmsSetting` / `AiSetting` ORM 컬럼 / 시드 / 마이그레이션 무수정. 새 저장소 ⊥.
3. **사용자 명시 "API key는 원문이 아니라 등록 여부만 반환하도록 경계 정리"**:
   `serialize_ai_setting` / `serialize_ai_health_public` / `serialize_ai_health_admin` /
   `serialize_sms_setting` 모두 마스킹 (앞 4자 + ****) 또는 boolean (api_key_set / has_password) 만 노출.
   `test_serialize_ai_setting_does_not_leak_raw_api_key` 가 회귀 보호.
4. **사용자 명시 "외부 API 호출 없이 상태 조회가 가능해야 함"**:
   `app/core/feature_flags.py` 의 pure-input helper 는 *값 조회* 만 — provider/SDK 인스턴스화 ⊥.
   `test_pure_helpers_do_not_invoke_provider_or_sdk` 가 tripwire.
5. **PyInstaller 빌드 안전성**: `dosu_clinic.spec` 에 19-2 modules 4개 추가 +
   `tests/test_pyinstaller_hidden_imports.py` 에 검증 8 tests 추가 (69 → 77).
6. **19-1 r1 caveat 보정 — `HEALTH_PUBLIC_KEYS` 실제 응답 키 정합**:
   19-1 r1 시점 placeholder (`ai_enabled / ai_ready / version / node_id`) 가 실제 응답
   (`enabled / ready / provider / api_key_set` per `tests/test_ai_health_public.py:9` +
   `app/routers/ai.py:179~184`) 와 불일치 — 본 19-2 health 경계 정리에서 정합 보정.
   상수가 아직 wire 되지 않은 상태이므로 응답 키 변경 ⊥, 단순 상수 정합화.

## 3. 새로 만든 modules 구조

```
app/modules/
├── __init__.py                 (14 lines, modules 패키지 facade + D-4 정합)
├── settings/
│   ├── __init__.py             (27 lines, settings 패키지 facade + COMPAT/SAFETY)
│   └── serializers.py          (183 lines, 7 직렬화 helper + mask 2)
└── health/
    └── __init__.py             (57 lines, services.ai.health 24 API re-export)
```

## 4. 실제 이동한 로직

**0 줄** — 본 19-2 시점에 *실제 본체 이동 0*. 모두 facade / 신규 helper / re-export wrapper.

| 파일 | 이동? | 비고 |
|---|---|---|
| `app/services/ai/health.py` | ✗ | 본체 그대로. `app.modules.health` 가 24 API re-export. `derive_*` 함수 무수정. |
| `app/routers/ai.py:_serialize_setting` | ✗ | 본체 그대로. `app.modules.settings.serializers.serialize_ai_setting` 는 *동등 helper* (대체 ⊥). |
| `app/routers/ai.py:_mask_api_key` | ✗ | 본체 그대로. `app.modules.settings.serializers.mask_api_key` 는 *동등 helper* (대체 ⊥). |
| `app/routers/api.py:sms_get` | ✗ | 본체 그대로. `serialize_sms_setting` 는 *동등 helper*. |
| `app/routers/api.py:system_settings_get` | ✗ | 본체 그대로. `serialize_system_setting` 는 *동등 helper*. |
| `app/services/ai/health.py:derive_ai_mode` | ✗ | 본체 그대로. `app.core.feature_flags.derive_ai_mode_from_inputs` 는 *동등 pure-input* (ORM 의존 ⊥). |

## 5. 유지한 compatibility wrapper

| wrapper | 위치 | 역할 |
|---|---|---|
| `app.modules.health` re-export | `app/modules/health/__init__.py` | 기존 `from app.services.ai.health import build_admin_status` 그대로. 신규 `from app.modules.health import build_admin_status` 동시 지원. |
| `app.core.feature_flags` env helper | `app/core/feature_flags.py` | 기존 `app.services.ai.health` 의 ai_mode / search_mode 파생 그대로. 신규 pure-input helper 가 byte-equivalent 출력 보장. |
| `serializers.serialize_ai_setting` | `app/modules/settings/serializers.py` | `app/routers/ai.py:_serialize_setting` 와 *9키 / 값 / 타입* 100% 일치. 미채택 (라우터 무수정). |
| `serializers.serialize_ai_health_public` | `app/modules/settings/serializers.py` | `app/routers/ai.py:ai_health_public` 의 4키 dict builder 와 일치. |
| `serializers.serialize_ai_health_admin` | `app/modules/settings/serializers.py` | `app/routers/ai.py:ai_health` 의 9키 dict builder 와 일치. |
| `serializers.serialize_sms_setting` | `app/modules/settings/serializers.py` | `app/routers/api.py:sms_get` 의 7키 dict builder 와 일치. 마스킹 정책 보존. |
| `serializers.serialize_system_setting` | `app/modules/settings/serializers.py` | `app/routers/api.py:system_settings_get` 의 6키 dict builder 와 일치. |

## 6. 기존 API 응답 구조 유지 여부

✓ **100% 보존** — `app/routers/*.py` 무수정.

| URL | 응답 키 | 보존 |
|---|---|---|
| `GET /api/ai/health` (admin 9키) | `enabled / provider / model / api_key_set / sdk_installed / sdk_errors / knowledge_doc_count / ready / version` | ✓ |
| `GET /api/ai/health/public` (4키) | `enabled / ready / provider / api_key_set` | ✓ |
| `GET /api/ai/status` (18-7 admin top-level 9 + nested) | (18-7 정합) | ✓ |
| `GET /api/ai/settings` (9키) | `enabled / provider / model / api_key_masked / api_key_set / base_url / max_tokens / temperature / pii_guard_enabled` | ✓ |
| `PUT /api/ai/settings` | (변경 사실만 audit 기록) | ✓ |
| `GET /api/sms/setting` (7키) | `munjanara_id / munjanara_pw / munjanara_key / sender_phone / clinic_phone / clinic_name / api_url` | ✓ |
| `POST /api/sms/setting` | (저장 + audit) | ✓ |
| `GET /api/system-settings` (6키) | `manual_slot_limit / treatment_minutes / sms_template / auto_backup_enabled / auto_backup_interval_min / auto_backup_keep_count` | ✓ |
| `POST /api/system-settings` | (저장 + log + audit) | ✓ |

## 7. API key / 개인정보 비노출 처리 방식

### 7-1. AI API key

| 채널 | 노출 정책 | 검증 |
|---|---|---|
| `/api/ai/health` admin 응답 | `api_key_set: bool` 만 (boolean) | `serialize_ai_health_admin` + 회귀 테스트 |
| `/api/ai/health/public` 응답 | `api_key_set: bool` 만 (boolean) | `serialize_ai_health_public` + 회귀 테스트 |
| `/api/ai/settings` 응답 | `api_key_masked: "앞4자****"` + `api_key_set: bool` | `serialize_ai_setting` + 회귀 테스트 |
| `/api/ai/status` (18-7) | `ai_settings.api_key_set: bool` 만 | 기존 `health.py:build_admin_status` 정책 보존 |
| pure-input helper 결과 | `api_key` 인자는 *boolean 판정* 후 enum/dict 반환만 — 원문 ⊥ | `test_serialize_ai_setting_does_not_leak_raw_api_key` |

### 7-2. SMS 비밀번호 / API key (munjanara)

| 채널 | 노출 정책 | 검증 |
|---|---|---|
| `/api/sms/setting` 응답 | `munjanara_pw: "****"` (있으면) / `""` (없으면) | `mask_password` + 회귀 테스트 |
| `/api/sms/setting` 응답 | `munjanara_key: "앞4자****"` (있으면) / `""` (없으면) | `serialize_sms_setting` + 회귀 테스트 |
| 본 helper 입력 → 출력 | 원문 어디에도 미포함 (4자 미만이면 앞 글자도 ⊥ — `****` 만) | `test_mask_api_key_short_returns_stars_only` |

### 7-3. 환자 PII / 직원 정보

| 영역 | 본 19-2 영향 |
|---|---|
| `/api/ai/manual/ask` 응답 | 영향 ⊥ — 본 19-2 미수정 (manual_qa.py 무수정) |
| AiUsageLog 저장 | 영향 ⊥ — 본 19-2 미수정 (ai_logging.py 무수정) |
| pii.scan / sha256 마스킹 | 영향 ⊥ — `app.services.ai.pii` 무수정 |

## 8. 외부 API 호출 차단 결과

| # | 검사 | 결과 |
|---|---|---|
| pure-input helper 안에서 provider 호출 시도 | 0 (tripwire 통과) |
| pure-input helper 안에서 SDK import 시도 | 0 |
| serializer 안에서 외부 호출 | 0 (in-memory ORM 인스턴스만) |
| modules.health re-export 시 부수효과 | 0 (`app.services.ai.health` 본체는 기존 정책 — 외부 호출 0) |
| `_block_sdk_modules` 자동 활성 | ✓ |

## 9. 운영 DB 보호 결과

| # | 검사 | 결과 |
|---|---|---|
| `scripts/check_db_path.py` exit 0 | ✓ |
| modules 안에서 DB 세션 직접 open | 0 (serializers 는 ORM 인스턴스를 *받기만*, DB 세션 부재) |
| feature_flags pure-input helper 안에서 DB 세션 | 0 (primitives 만 받음) |
| `tests/conftest.py` 4단계 격리 / `db_guard` | ✓ |

## 10. 순환참조 위험 여부

✓ **순환참조 0건** — 단방향 경계 (D-4) 검증 통과.

| 모듈 | 의존 방향 | 검증 |
|---|---|---|
| `app.core.feature_flags` | (외부) `os` + `typing` 만 — `app.models` / `app.services` / `app.modules` ⊥ | `test_core_feature_flags_does_not_import_models` |
| `app.modules.settings.serializers` | (외부) `typing` 만 — ORM / DB / SQLAlchemy ⊥ | `test_modules_settings_serializers_does_not_import_models_or_db` |
| `app.modules.settings.__init__` | (외부) 없음 — 빈 facade | (자명) |
| `app.modules.health.__init__` | `app.services.ai.health` (re-export) — 기존 import 경로 보존 | (자명) |
| `app.modules.__init__` | 없음 — 빈 facade | (자명) |

## 11. 주석 / 문서화 적용 내용

### 11-1. 카테고리별 주석 카운트 (실측)

| 카테고리 | 카운트 | 주요 위치 |
|---|---|---|
| `# COMPAT:` | 6 | feature_flags (응답 키 / 의미 보존) / serializers (라우터 dict builder 정합 5) / health/__init__ (re-export 호환) / responses (HEALTH_PUBLIC_KEYS 보정) |
| `# SAFETY:` | 7 | feature_flags (api_key/model 원문 ⊥) / serializers (mask 4 + 단방향) / settings/__init__ (api_key/PW 원문 ⊥) |
| `# NOTE:` | 6 | feature_flags (env vs DB / m014 placeholder / health.py 동등성) / serializers (treatment_minutes pure helper) / health/__init__ (post-19-P 분류) |
| `# RISK:` | 1 | feature_flags (ai_mode 잘못 도출 위험 — 외부 API 호출 가능성) |
| `# TODO(post-19-P):` | 2 | feature_flags (m014 vector path) / responses (placeholder 정합 후속) |

### 11-2. docstring

| 파일 | docstring 정책 |
|---|---|
| `app/modules/__init__.py` | 1 패키지 docstring (역할 + D-4 정합 + 19-2 후보 구조 명시) |
| `app/modules/settings/__init__.py` | 1 패키지 docstring + COMPAT/SAFETY 명시 |
| `app/modules/settings/serializers.py` | 1 모듈 docstring + 7 함수 docstring (모두 COMPAT/SAFETY 명시) |
| `app/modules/health/__init__.py` | 1 패키지 docstring + COMPAT/NOTE 명시 |
| `app/core/feature_flags.py` | 1 모듈 docstring (보강) + 3 함수 docstring (모두 SAFETY 명시) |
| `tests/test_19_2_settings_health_boundary.py` | 1 모듈 docstring + per-test docstring |

## 12. 생성한 리포트 파일

| 파일 | 역할 |
|---|---|
| `reports/refactor/19-2_test_report.md` | 본 세션 영구 보존본 |
| `reports/refactor/19-2_fix_summary.md` | 본 세션 영구 보존본 (이 파일) |
| `reports/refactor/19-2_codex_review_request.md` | 본 세션 영구 보존본 (Codex 검증 요청서) |
| `reports/refactor/latest_test_report.md` | 19-2 덮어쓰기 |
| `reports/refactor/latest_fix_summary.md` | 19-2 덮어쓰기 |
| `reports/refactor/latest_codex_review_request.md` | 19-2 덮어쓰기 |

## 13. 남은 위험 요소

| # | 위험 | 분류 | 해결 시점 |
|---|---|---|---|
| 1 | 19-2 modules 가 *미채택* — 라우터에서 본 helper 를 import 안 함 | 의도 (사용자 명시 "기존 설정 저장 방식 유지") | 19-12 admin/settings 분리 시점에 `app/routers/api.py` / `app/routers/ai.py` 가 점진적으로 채택 |
| 2 | post-19-P (M-28) `/api/health` (서버 전체 상태) 신설 | 후속 분류 | post-19-P 후속 세션 |
| 3 | T-8 (env vs DB 단일 진실원천) 통합 | 후속 분류 | post-19-P 후속 세션 |
| 4 | `health.py` 가 `app.core.feature_flags` 의 pure-input helper 로 위임되지 않음 (현재 두 경로 공존) | 의도 (서비스 본체 무수정) | post-19-P 후속 세션 또는 19-12 |
| 5 | `app/services/ai/health.py:derive_vector_status` 의 m014 미도입 placeholder 분기 — 실제 vector_enabled=True 도달 안 함 | 알려진 분기 (18-7 시점) | m014 도입 시점 |

## 14. Codex 검증으로 넘겨도 되는지 자체 판단

**yes — Codex 검증으로 넘길 준비 완료**.

근거:
1. 5회 루프 1회차 통과 — 땜질 ⊥, ruff 보정 1회 (import 정렬, 동작 영향 0).
2. 18-8 baseline (529/1/7) 회귀 0 — 19-1 baseline (545/1/7) 에 +40 신규만 추가 (총 585).
3. ruff / check_db_path / PyInstaller 77 tests 모두 통과.
4. 19-2 32 contract 테스트 + 기존 health/admin/AI-mode 101 테스트 모두 통과.
5. 운영 DB 미접근 + 외부 API 호출 0 + API key 원문 / PII 비노출 모두 정합.
6. core / modules 단방향 경계 (D-4) 검증 통과.
7. 기존 API 응답 dict / URL / 인증 정책 100% 보존.
8. 사용자 명시 9 금지 항목 모두 준수.
