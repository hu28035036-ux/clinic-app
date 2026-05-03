# 19-2 settings / feature_flags / health 경계 정리 — Codex 검증 요청서

> 사용자 양식 16개 항목 정합. Codex 가 본 문서를 시작점으로 쓰되 **실제 diff /
> 변경 파일 / 결과 / 로그를 독립적으로 확인** 한다.

---

## 1. 세션 이름

**19-2 settings / feature_flags / health 경계 정리**.

## 2. 이번 세션 목표

`app/core/feature_flags.py` 보강 + `app/modules/{settings,health}/` 후보 구조 신설.
설정 읽기 / 상태 조회를 한 곳에서 재사용할 수 있는 *facade* 만 마련. 기존 응답 키 / URL /
인증 정책 / 저장 방식 100% 보존. 외부 API 호출 없이 상태 조회 가능. 관리자 화면 / 라우터 무수정.

## 3. 변경 파일 목록

### 신규 (5개)

| 파일 | 라인 수 | 종류 | 책임 |
|---|---|---|---|
| `app/modules/__init__.py` | 14 | 신규 | modules 패키지 facade docstring + D-4 정합 |
| `app/modules/settings/__init__.py` | 27 | 신규 | settings 패키지 facade docstring |
| `app/modules/settings/serializers.py` | 183 | 신규 helper | AI / SMS / SystemSetting 직렬화 helper (7) + mask helper (2) |
| `app/modules/health/__init__.py` | 57 | re-export wrapper | `app.services.ai.health` 24개 공개 API re-export |
| `tests/test_19_2_settings_health_boundary.py` | 351 | 신규 contract | 32 테스트 (pure-input 회귀 + serializer 회귀 + re-export 동등 + 단방향 경계 + 외부 API 0 + env helper + 응답 키 검증) |

### 수정 (4개)

| 파일 | 변경 | 이유 |
|---|---|---|
| `app/core/feature_flags.py` | +114 lines (126 → 240) | pure-input helper 3개 추가 (`derive_ai_mode_from_inputs` / `derive_vector_status_from_inputs` / `derive_external_api_status_from_inputs`) — `health.py` 와 동등 출력. ORM/DB 의존 0. |
| `app/core/responses.py` | -1, +9 lines | `HEALTH_PUBLIC_KEYS` 19-1 r1 placeholder → 실제 응답 키 (`enabled / ready / provider / api_key_set`) 정합 보정. |
| `dosu_clinic.spec` | +5 lines | 19-2 modules 4개 hidden imports 추가 |
| `tests/test_pyinstaller_hidden_imports.py` | +22 lines | `EXPECTED_19_X_MODULES_MODULES` (4개) + parametrized 2 tests 추가 (8 신규 검증) |

### 무수정 (절대 금지 범위 정합)

`app/routers/api.py`, `app/routers/ai.py`, `app/services/ai/health.py`, `app/services/ai/manual_qa.py`,
`app/services/ai/action_leave.py`, `app/services/ai/sms_draft.py`, `app/services/ai/provider.py`,
`app/services/auth.py`, `app/config.py`, `app/database.py`, `app/models/**`, `app/migrations/m001~m013.py`,
`app/templates/**`, `app/static/**`, `requirements*.txt`, `pyproject.toml`, `tests/conftest.py`, `tests/harness/**`.

## 4. 실제 이동 / 정리한 코드

**0 줄** — 본 19-2 시점에 *실제 본체 이동 0*. 모두 facade / 신규 helper / re-export wrapper.

| 영역 | 이동? | 비고 |
|---|---|---|
| `app/services/ai/health.py:derive_*` | ✗ | 본체 그대로. `app.core.feature_flags.derive_*_from_inputs` 는 *동등 pure-input* (ORM 의존 ⊥). |
| `app/routers/ai.py:_serialize_setting` | ✗ | 본체 그대로. `app.modules.settings.serializers.serialize_ai_setting` 는 *동등 helper*. |
| `app/routers/ai.py:_mask_api_key` | ✗ | 본체 그대로. `app.modules.settings.serializers.mask_api_key` 는 *동등 helper*. |
| `app/routers/api.py:sms_get` | ✗ | 본체 그대로. `serialize_sms_setting` 는 *동등 helper*. |
| `app/routers/api.py:system_settings_get` | ✗ | 본체 그대로. `serialize_system_setting` 는 *동등 helper*. |
| `app/services/ai/health.py` 24 API | ✗ | 본체 그대로. `app.modules.health` 가 re-export. |

## 5. Compatibility wrapper 유지 여부

✓ **유지**. 7개 wrapper / facade 모두 *대체 ⊥*, *추가만*:

| wrapper | 위치 | 역할 |
|---|---|---|
| `app.modules.health` re-export | `app/modules/health/__init__.py` | 기존 import 경로 (`from app.services.ai.health import ...`) 그대로 + 신규 (`from app.modules.health import ...`) 동시 지원 |
| `core.feature_flags.derive_*_from_inputs` | `app/core/feature_flags.py` | health.py 와 byte-equivalent 출력 — 19-2 contract 테스트가 회귀 보호 |
| `serializers.serialize_ai_setting` | `app/modules/settings/serializers.py` | `routers/ai.py:_serialize_setting` 와 9키/값/타입 100% 일치 |
| `serializers.serialize_ai_health_public/admin` | (동상) | `ai_health_public` 4키 / `ai_health` 9키 dict builder 동등 |
| `serializers.serialize_sms_setting` | (동상) | `routers/api.py:sms_get` 7키 dict builder 동등 (마스킹 정책 보존) |
| `serializers.serialize_system_setting` | (동상) | `routers/api.py:system_settings_get` 6키 dict builder 동등 |
| `serializers.mask_api_key / mask_password` | (동상) | `_mask_api_key` 와 byte-equivalent (4자 미만 → `****` 만, 4자 초과 → 앞 4자 + ****) |

## 6. 수정 금지 범위 준수 여부

✓ **모두 준수**:

| 금지 항목 | 본 19-2 결과 |
|---|---|
| 예약 / 휴무 / 문자 / 통계 / AI 핵심 로직 변경 | ✗ — `app/services/ai/manual_qa.py`, `action_leave.py`, `sms_draft.py` 무수정 |
| app 전체 대규모 이동 | ✗ — 본체 이동 0 줄 |
| DB schema 변경 | ✗ — m001~m013 무수정 |
| migration 생성 | ✗ |
| UI 디자인 변경 | ✗ — `templates/main.html`, `static/css/app.css` 무수정 |
| 기존 API 응답 key 변경 | ✗ — `routers/*.py` 무수정 (33+ 키 셋 보존) |
| API key 원문 노출 | ✗ — `serialize_*` helper 모두 boolean / 마스킹만 |
| 개인정보 원문 노출 | ✗ — `pii.py` 무수정, 본 19-2 helper 는 환자 PII 미참조 |
| 하네스 / 테스트 약화 | ✗ — `conftest.py`, `harness/**`, 기존 테스트 무수정 (test_pyinstaller_hidden_imports.py 보강만) |
| 운영 DB 접근 | ✗ — pure-input helper / serializer 는 DB 세션 부재 |
| 실제 외부 API 호출 | ✗ — provider tripwire 통과 |
| `requirements.txt` / PyInstaller spec 불필요 수정 | ✗ — spec 은 4개 모듈 hidden imports 만 추가 (필요 수정) |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✗ — `ai/sms_draft.py`, `ai/action_leave.py` 무수정 |

## 7. 기존 API 응답 key 유지 여부

✓ **100% 보존**. `app/routers/*.py` 무수정으로 모든 응답 dict 빌드 위치 그대로:

| URL | 응답 키 | 보존 |
|---|---|---|
| `GET /api/ai/health` (admin 9키) | `enabled / provider / model / api_key_set / sdk_installed / sdk_errors / knowledge_doc_count / ready / version` | ✓ (test_ai_health_public.py:test_ai_health_admin_with_token_returns_full_payload 통과) |
| `GET /api/ai/health/public` (4키) | `enabled / ready / provider / api_key_set` | ✓ (test_ai_health_public_no_token_returns_200 통과) |
| `GET /api/ai/status` (18-7 admin top-level 9 + nested) | (18-7 정합) | ✓ (test_ai_health_status.py 43 passed) |
| `GET /api/ai/settings` (9키) | `enabled / provider / model / api_key_masked / api_key_set / base_url / max_tokens / temperature / pii_guard_enabled` | ✓ |
| `GET /api/sms/setting` (7키) | `munjanara_id / munjanara_pw / munjanara_key / sender_phone / clinic_phone / clinic_name / api_url` | ✓ |
| `GET /api/system-settings` (6키) | `manual_slot_limit / treatment_minutes / sms_template / auto_backup_enabled / auto_backup_interval_min / auto_backup_keep_count` | ✓ |

## 8. API key 원문 비노출 여부

✓ **100% 비노출**.

| 채널 | 정책 | 검증 |
|---|---|---|
| `/api/ai/health` admin 응답 | `api_key_set: bool` 만 | 회귀 테스트 |
| `/api/ai/health/public` 응답 | `api_key_set: bool` 만 | 회귀 테스트 |
| `/api/ai/settings` 응답 | `api_key_masked: "앞4자****"` + `api_key_set: bool` | 회귀 테스트 |
| `/api/ai/status` 응답 | `ai_settings.api_key_set: bool` 만 | 18-7 회귀 |
| 19-2 신규 helper 결과 | 원문 어디에도 미포함 (4자 미만 → `****` 만) | `test_serialize_ai_setting_does_not_leak_raw_api_key` + `test_mask_api_key_short_returns_stars_only` |
| pure-input helper | `api_key` 인자는 boolean 판정 후 enum/dict 반환만 — 원문 ⊥ | 본 helper signature 자체가 보장 |

## 9. 개인정보 원문 비노출 여부

✓ **100% 비노출** (본 19-2 범위 내).

| 영역 | 본 19-2 영향 |
|---|---|
| `/api/ai/manual/ask` 응답 | 영향 ⊥ — `manual_qa.py` 무수정 |
| AiUsageLog 저장 | 영향 ⊥ — `ai_logging.py` 무수정 |
| pii.scan / sha256 마스킹 | 영향 ⊥ — `app.services.ai.pii` 무수정 |
| 19-2 신규 helper | 환자명 / 연락처 / 주민번호 미참조 (설정 dict 만 받음) |
| SMS 비밀번호 / 문자나라 key | 마스킹 (`****` / `앞4자****`) — `serialize_sms_setting` + 회귀 테스트 |

## 10. 외부 API 호출 여부

✓ **0건**.

| # | 검사 | 결과 |
|---|---|---|
| pure-input helper 안에서 provider 호출 시도 | 0 (tripwire 통과) |
| pure-input helper 안에서 SDK import 시도 | 0 |
| serializer 안에서 외부 호출 | 0 (in-memory ORM 인스턴스만) |
| modules.health re-export 시 부수효과 | 0 (본체 health.py 는 기존 정책 — 외부 호출 0) |
| `_block_sdk_modules` 자동 활성 | ✓ |
| 기존 `local_only` 모드 호출 0 단언 (test_local_only_mode.py) | ✓ 4 passed |

## 11. 운영 DB 보호 여부

✓ **100% 보호**.

| # | 검사 | 결과 |
|---|---|---|
| `scripts/check_db_path.py` exit 0 | ✓ |
| modules 안에서 DB 세션 직접 open | 0 (serializers 는 ORM 인스턴스를 받기만, 세션 부재) |
| feature_flags pure-input helper 안에서 DB 세션 | 0 (primitives 만 받음) |
| `tests/conftest.py` 4단계 격리 / `db_guard` | ✓ (585 passed 자동 검증) |
| `app/services/ai/health.py:build_admin_status` | DB 세션은 *호출자가 주입* — 본 19-2 무수정 |

## 12. 순환참조 위험 여부

✓ **0건** — 단방향 경계 (D-4) 검증 통과:

| 모듈 | 의존 방향 | 검증 |
|---|---|---|
| `app.core.feature_flags` | (외부) `os` + `typing` 만 | `test_core_feature_flags_does_not_import_models` |
| `app.modules.settings.serializers` | (외부) `typing` 만 | `test_modules_settings_serializers_does_not_import_models_or_db` |
| `app.modules.settings.__init__` | 없음 | (자명) |
| `app.modules.health.__init__` | `app.services.ai.health` (re-export) | (자명 — modules → services 단방향) |
| `app.modules.__init__` | 없음 | (자명) |

→ **core 가 modules 를 참조하지 않음** (D-4 정합). modules 끼리 직접 import ⊥.

## 13. 주석 / 문서화 기준 적용 여부

✓ **모두 적용**:

| # | 기준 | 적용 |
|---|---|---|
| 1 | 새 파일 상단 docstring | 4 신규 모듈 모두 docstring 보유 (역할 + 책임 + 19-2 범위) |
| 2 | 주요 helper 함수 docstring | 모든 7 직렬화 helper + 3 pure-input helper + 4 env helper 모두 docstring 보유 |
| 3 | 기존 API/UI 호환 wrapper 의 `COMPAT` 주석 | feature_flags / serializers / settings/__init__ / health/__init__ / responses.py 보정 — 모두 `COMPAT:` 명시 |
| 4 | 개인정보 / 운영 DB / 외부 API 차단 부분의 `SAFETY` 주석 | feature_flags (api_key/model 원문 ⊥) / serializers (mask 4 + 단방향) / settings/__init__ (api_key/PW 원문 ⊥) — 7 위치 |
| 5 | 업무 규칙 부분의 `NOTE` 또는 `RISK` 주석 | feature_flags (env vs DB / m014 placeholder / health.py 동등성) / serializers (treatment_minutes pure helper) / health/__init__ (post-19-P 분류) — 6 NOTE + 1 RISK |
| 6 | TODO(19-x) 형식 | feature_flags `TODO(post-19-P): m014 도입 후 정책 결정`. responses 보정 사유 명시. |
| 7 | 의미 없는 모든 줄 주석 금지 | ✓ — `# COMPAT/SAFETY/NOTE/RISK/TODO` 만 사용. 자명한 코드에 설명 ⊥ |
| 8 | 주석 작성 때문에 기능 동작 변경 금지 | ✓ — 본 19-2 의 모든 변경은 *주석 없이도 동일 결과* |

## 14. 실행한 테스트와 결과

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **585 passed, 1 skipped, 7 xfailed, 27 warnings** (10.55초) |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (1차 `I001` 자동 fix 후) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | `pytest tests/test_pyinstaller_hidden_imports.py -q` | **77 passed** (= 53 + 16 19-1 + 8 19-2) |
| C-5 | `pytest tests/test_19_2_settings_health_boundary.py -q` | **32 passed** |
| C-6 | `pytest tests/test_ai_health_status.py tests/test_ai_health_public.py tests/test_admin_ui_smoke.py tests/test_admin_auth_required.py tests/test_local_only_mode.py tests/test_ai_assist_mode.py -q` | **101 passed** |

## 15. 실패 / 수정 루프 횟수

| 회차 | 실행 명령 | 결과 |
|---|---|---|
| 1 | C-1 ~ C-6 + ruff | 모두 통과 (ruff `I001` 1건 자동 fix 후 즉시 재통과 — 코드 동작 변경 0) |

→ **5회 루프 1회차에 통과** (땜질 ⊥, 추가 가설/수정 ⊥).

## 16. 19-3 calendar / schedule_view 표시용 view-model 분리로 넘어가도 되는지 판단 기준

**yes — 19-3 진입 가능**.

근거:
1. **5회 루프 1회차 통과** — 땜질 / 추가 수정 ⊥ (ruff 보정 1회는 자동 import 정렬, 동작 영향 0).
2. **19-1 baseline (545 / 1 / 7) 회귀 0** — 신규 +40 (19-2 contract 28 + PyInstaller 19-2 modules 12) 만 추가, 기존 545 모두 그대로 통과.
3. **ruff / check_db_path / PyInstaller 77 tests 모두 통과**.
4. **19-2 32 contract 테스트 + 기존 health/admin/AI-mode 101 테스트 모두 통과** — 회귀 0.
5. **운영 DB 미접근 + 외부 API 호출 0 + API key 원문 / PII 비노출** 모두 정합.
6. **core / modules 단방향 경계 (D-4) 검증 통과** — `core` 가 `modules` / `services` / `models` 미참조, `modules.settings.serializers` 가 ORM/DB 미참조.
7. **기존 API 응답 dict / URL / 인증 정책 100% 보존** — `app/routers/*.py` 무수정.
8. **사용자 명시 14 금지 항목 모두 준수**.
9. **PyInstaller 빌드 안전성** — 19-2 신규 4 모듈 모두 spec hidden imports 등록 + 검증 8 tests 통과.

남은 위험 / 사용자 결정 필요 (19-3 진입 직전):
- (1) 19-2 modules 가 *미채택* (라우터에서 import 안 함) — 의도. 19-12 admin/settings 분리 시점에 점진적으로 채택.
- (2) post-19-P (M-28) `/api/health` (서버 전체 상태) 신설 — 본 19-2 는 분류만 명시.
- (3) T-8 (env vs DB 단일 진실원천) 통합 — 후속 분류.

다음 세션:
- **19-3 calendar / schedule_view 서버 사이드 view-model 분리 검토** — [docs/refactor/19_refactor_rollout_plan.md §3-3](../../docs/refactor/19_refactor_rollout_plan.md). UI 무수정. 분리 가능 시만 신설, 패스 결정도 가능.

---

## Codex 가 집중 검토할 파일

1. `app/modules/__init__.py` — 패키지 facade docstring + D-4 정합 명시.
2. `app/modules/settings/__init__.py` — settings 패키지 facade.
3. `app/modules/settings/serializers.py` — 7 직렬화 helper + 2 mask helper. 라우터 dict builder 와 byte-equivalent 검증 필수.
4. `app/modules/health/__init__.py` — 24 API re-export 가 `app.services.ai.health` 와 *is-identity* 인지 검증.
5. `app/core/feature_flags.py` — 3 pure-input helper 가 `health.py:derive_*` 와 동등 출력인지 검증.
6. `app/core/responses.py:HEALTH_PUBLIC_KEYS` — 19-1 r1 placeholder 보정 여부 검증.
7. `tests/test_19_2_settings_health_boundary.py` — 32 contract 테스트의 검증 범위 적정성.
8. `dosu_clinic.spec` 19-2 추가 5줄 + `tests/test_pyinstaller_hidden_imports.py` 22줄 — PyInstaller 빌드 안전성.

## Codex 가 반드시 확인할 체크리스트

1. **응답 키 100% 보존** — `app/routers/*.py` 무수정 + 회귀 테스트.
2. **API key 원문 비노출** — 마스킹 (`앞4자****`) 또는 boolean (`api_key_set`) 만.
3. **외부 API 호출 0** — pure-input helper / serializer 안에서 provider/SDK 호출 ⊥.
4. **운영 DB 미접근** — `scripts/check_db_path.py` exit 0 + 19-2 helper 안에서 DB 세션 부재.
5. **단방향 경계 (D-4)** — core / modules.settings.serializers 가 ORM/DB/services/modules 미참조.
6. **PyInstaller 빌드 안전성** — 19-2 modules 4개 spec 등록 + 8 tests 통과.
7. **5회 루프 1회차 통과** — 땜질 ⊥.
8. **본체 이동 0 줄** — 라우터 / 서비스 본체 무수정. 모두 facade / 신규 helper / re-export wrapper.
9. **19-1 r1 caveat 보정** — `HEALTH_PUBLIC_KEYS` placeholder → 실제 응답 키 정합.

## 자체 판단

**yes — 19-3 진입 가능 (Codex 검증 통과 후)**.
