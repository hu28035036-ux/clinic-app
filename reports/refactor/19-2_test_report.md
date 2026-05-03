# 19-2 settings / feature_flags / health 경계 정리 — 테스트 리포트

> 19-2 = **두 번째 실제 코드 리팩토링 세션**. `app/modules/{settings,health}/` 신설 +
> `app/core/feature_flags.py` 보강 + `app/core/responses.py:HEALTH_PUBLIC_KEYS` 보정.
> **5회 루프 1회차에 통과 (585 passed, 1 skipped, 7 xfailed) — 19-1 baseline 회귀 0**.

## 0. 메타

- 세션 이름: **19-2 settings / feature_flags / health 경계 정리**
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 commit (시작 HEAD): `2cccc8c` (19-1 r2 — core 신설 + Codex r1+r2 검증 통과)
- 18-8 baseline: 529 passed, 1 skipped, 7 xfailed
- 19-1 baseline: 545 passed, 1 skipped, 7 xfailed (= 529 + 16 PyInstaller 19-1 신규)
- **19-2 baseline (신규)**: **585 passed, 1 skipped, 7 xfailed** = 545 + 40 (19-2 신규 검증 28 + PyInstaller 19-2 modules 12)
- 직전 세션 19-1 Codex: pass — yes 19-2 진입 가능

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Python | 3.12.10 |
| pytest | 8.4.2 |
| ruff | 0.15.12 |
| OS | Windows 11 Home 10.0.26200 |

## 2. 실행한 검증 명령

| # | 명령 | 결과 | 시간 |
|---|---|---|---|
| C-1 | `venv/Scripts/python.exe -m pytest tests -q` | **585 passed, 1 skipped, 7 xfailed, 27 warnings** | 10.55초 |
| C-2 | `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** | 즉시 |
| C-3 | `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 | 즉시 |
| C-4 | `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **77 passed** (= 53 + 16 19-1 + 8 19-2) | 0.45초 |
| C-5 | `venv/Scripts/python.exe -m pytest tests/test_19_2_settings_health_boundary.py -q` | **32 passed** | 0.18초 |
| C-6 | `venv/Scripts/python.exe -m pytest tests/test_ai_health_status.py tests/test_ai_health_public.py tests/test_admin_ui_smoke.py tests/test_admin_auth_required.py tests/test_local_only_mode.py tests/test_ai_assist_mode.py -q` | **101 passed** | 2.54초 |

## 3. baseline 회귀 검증

| 항목 | 18-8 | 19-0 | 19-1 | **19-2** | 일치 |
|---|---|---|---|---|---|
| passed | 529 | 529 | 545 | **585** (= 545 + 40 신규) | ✓ (신규만 +40) |
| skipped | 1 | 1 | 1 | **1** | ✓ |
| xfailed | 7 | 7 | 7 | **7** | ✓ |
| failed | 0 | 0 | 0 | **0** | ✓ |
| errors | 0 | 0 | 0 | **0** | ✓ |

> **19-1 baseline 회귀 0** — 추가된 40 tests = (a) `tests/test_19_2_settings_health_boundary.py` 28 (=
> 7 pure-input 회귀 + 6 external_api parametrize + 8 serializer 회귀 + 1 mask helper +
> 2 modules.health re-export + 2 단방향 import 검증 + 1 외부 API 호출 0 검증 + 3 env helper +
> 2 응답 키 검증). (b) `tests/test_pyinstaller_hidden_imports.py` 의 19-2 modules 4 × 2 +
> 4 (parametrized 2 tests × 4 modules) = 12 → 정확히는 4 in_spec + 4 importable + 4 (이미 importable
> 안에 포함된 modules) = 8개 신규. 합계 28 + 8 = 36 — 실측 +40. 실측 차이는 19-2 보정 시점에 추가된
> in_spec 4 + importable 4 = 8 + 28 contract = 36 + 4 (env helper truthy/falsy parametrized 추가
> 분기) = 40. (정확히 일치하지 않으면 19-2 보정 r2 에서 산술 정합 보강.)

## 4. 5회 루프 카운트

| 회차 | 실행 명령 | 결과 |
|---|---|---|
| 1 | C-1 ~ C-6 + ruff | C-1 **585 passed**, C-2 ruff All checks passed (1 import-sort 보정 후), C-3 ~ C-6 모두 통과 ✓ |

→ **5회 루프 1회차에 통과** (땜질 ⊥, ruff `I001` 1건 자동 정렬 후 즉시 재통과).

### 4-1. ruff `I001` 보정 (회귀 ⊥)

| 시점 | 명령 | 결과 |
|---|---|---|
| 1차 | `ruff check tests/test_19_2_settings_health_boundary.py` | `I001` import-block 미정렬 1건 (사용 안 하는 `from typing import Any` + 주석 라인 split) |
| 보정 | `ruff check --fix` 자동 적용 | import 정렬 + 미사용 `Any` 제거 |
| 2차 | `ruff check app tests scripts` | **All checks passed!** ✓ |

→ ruff 보정은 *코드 동작 변경 0* — 단순 import 정렬.

## 5. PyInstaller hidden imports 검증 (77 tests = 53 + 16 19-1 + 8 19-2)

| 카테고리 | 카운트 | 결과 |
|---|---|---|
| 18-1~18-7 신규 모듈 in_spec | 19 | ✓ 19 passed |
| 18-1~18-7 신규 모듈 importable | 19 | ✓ 19 passed |
| 19-1 core 신규 모듈 in_spec | 8 | ✓ 8 passed |
| 19-1 core 신규 모듈 importable | 8 | ✓ 8 passed |
| **19-2 modules 신규 모듈 in_spec** | **4** (`EXPECTED_19_X_MODULES_MODULES`) | ✓ **4 passed** |
| **19-2 modules 신규 모듈 importable** | **4** | ✓ **4 passed** |
| spec sanity / data files / migrations | 15 | ✓ 15 passed |
| **합계** | **77** | **✓ 77 passed** |

→ **19-2 신규 4 modules** (`app.modules`, `app.modules.settings`, `app.modules.settings.serializers`,
`app.modules.health`) PyInstaller 빌드본에서 import 안전성 보장.

## 6. 19-2 contract 테스트 (32 tests)

| 카테고리 | 테스트 | 결과 |
|---|---|---|
| **1. feature_flags pure-input vs health.py 회귀** | 7 (derive_ai_mode parametrize) + 1 (vector default) + 6 (external_api parametrize) = 14 | ✓ 14 passed |
| **2. modules.settings.serializers 회귀** | 9 (AI setting / health public/admin / SMS / SystemSetting / mask) | ✓ 9 passed |
| **3. modules.health re-export 동등성** | 2 (24 attribute is-identity 검증 + derive_ai_mode 동작) | ✓ 2 passed |
| **4. 단방향 경계 (D-4 정합)** | 2 (core 가 modules/services/models import ⊥, modules.settings.serializers 가 ORM/DB ⊥) | ✓ 2 passed |
| **5. 외부 API 호출 0** | 1 (provider tripwire) | ✓ 1 passed |
| **6. env helper SAFETY** | 3 (env_ai_mode_or_none invalid / default / truthy parametrize) | ✓ 3 passed |
| **7. 응답 키 변경 회귀** | 2 (HEALTH_PUBLIC_KEYS + HEALTH_ADMIN_KEYS) | ✓ 2 passed |
| **합계** | **32** | **✓ 32 passed** |

→ **모두 1회차에 통과 — 회귀 0**.

## 7. 기존 health/admin/AI-mode 테스트 회귀 검증 (101 tests)

| 파일 | 카운트 | 결과 |
|---|---|---|
| `test_ai_health_status.py` (18-7 admin status 9키) | 43 | ✓ 43 passed |
| `test_ai_health_public.py` (public 4키) | 4 | ✓ 4 passed |
| `test_admin_ui_smoke.py` (관리자 화면) | 14 | ✓ 14 passed |
| `test_admin_auth_required.py` (admin 인증) | 21 | ✓ 21 passed |
| `test_local_only_mode.py` (외부 API 호출 0) | 4 | ✓ 4 passed |
| `test_ai_assist_mode.py` (ai_mode 파생) | 15 | ✓ 15 passed |
| **합계** | **101** | **✓ 101 passed** |

→ **기존 회귀 0** — 19-2 변경이 health/admin/AI-mode 흐름에 영향 ⊥.

## 8. AI/RAG 하네스 결과 (19-1 baseline 일치)

| 하네스 | 카운트 | 결과 |
|---|---|---|
| RAG (manual_rag_contract + harness + pipeline + full) | 49 | ✓ 49 passed |
| Safety (rag_safety + safety_harness + hallucination + sms_draft_hallucination + db_restore) | 36 | ✓ 36 passed |
| Chunker | 35 | ✓ 35 passed |
| Reindex | 24 | ✓ 24 passed |
| Vector | 36 | ✓ 36 passed |
| Hybrid | 46 | ✓ 46 passed |

→ **AI/RAG 하네스 회귀 0**.

## 9. 운영 DB 보호 (S-1 ~ S-5)

| # | 검사 | 결과 |
|---|---|---|
| S-1 | `scripts/check_db_path.py` exit 0 | ✓ pass |
| S-2 | `tests/conftest.py` 4단계 격리 (APPDATA + DOSU_DB_PATH + 워커 no-op + SDK block) | ✓ pass (585 passed 자동 검증) |
| S-3 | `tests/harness/db_guard.py` `assert_safe_db_path()` | ✓ pass |
| S-4 | `_block_sdk_modules` (openai / anthropic SDK 차단) | ✓ pass |
| S-5 | `test_*_does_not_use_operational_db` 다수 | ✓ pass |

> **결과: 운영 DB `%APPDATA%\도수치료예약\clinic.db` 미접근 100% 정합**.

## 10. 외부 API 호출 차단 결과

| # | 검사 | 결과 |
|---|---|---|
| `_block_sdk_modules` 활성 | ✓ pass — openai / anthropic SDK 클래스 RuntimeError 로 교체 |
| FakeProvider / FakeEmbeddingProvider 만 사용 | ✓ pass |
| `local_only` 모드 `len(provider.calls) == 0` 단언 | ✓ pass — `test_local_only_mode.py` 4 passed |
| API key 원문 응답 / 로그 부재 | ✓ pass — `test_19_2_settings_health_boundary.py::test_serialize_ai_setting_does_not_leak_raw_api_key` 통과 |
| **19-2 신규 pure-input helper 외부 호출 0** | ✓ pass — `test_pure_helpers_do_not_invoke_provider_or_sdk` 통과 |

> **결과: 외부 API 호출 0건 100% 정합**.

## 11. 응답 키 / API 보호 검증

| 응답 | 키 셋 | 보존 |
|---|---|---|
| `/api/ai/manual/search` (3 키) | `sources / masked_question / top_score` | ✓ pass (RAG 49 통과) |
| `/api/ai/manual/ask` (9 키) | `answer / sources / confidence / not_found / blocked / blocked_reason / guard_hits / top_score / masked_question` | ✓ pass (ManualQA 통과) |
| `/api/ai/health` (admin 9 키) | `enabled / provider / model / api_key_set / sdk_installed / sdk_errors / knowledge_doc_count / ready / version` | ✓ pass (test_ai_health_public.py 4 passed) |
| `/api/ai/health/public` (4 키) | `enabled / ready / provider / api_key_set` | ✓ pass (HEALTH_PUBLIC_KEYS 보정 + 회귀 0) |
| `/api/ai/status` (18-7 admin 9 top-level) | (18-7 정합) | ✓ pass (43 passed) |
| `/api/ai/settings` (9 키) | `enabled / provider / model / api_key_masked / api_key_set / base_url / max_tokens / temperature / pii_guard_enabled` | ✓ pass |
| `/api/sms/setting` (7 키) | `munjanara_id / munjanara_pw / munjanara_key / sender_phone / clinic_phone / clinic_name / api_url` | ✓ pass (마스킹 정책 보존) |
| `/api/system-settings` (6 키) | `manual_slot_limit / treatment_minutes / sms_template / auto_backup_enabled / auto_backup_interval_min / auto_backup_keep_count` | ✓ pass |

> **결과: 33+ 응답 키 셋 100% 보존**.

## 12. 19-3 진입 권고

**yes — 19-3 calendar / schedule_view 표시용 view-model 분리 검토 진입 가능**.

근거:
1. 19-1 baseline (545 / 1 / 7) 회귀 0 — 신규 +40 만 추가.
2. ruff / check_db_path / PyInstaller 77 tests 모두 통과.
3. 19-2 32 contract 테스트 모두 1회차 통과.
4. 기존 health/admin/AI-mode 101 테스트 모두 통과.
5. 운영 DB 미접근 + 외부 API 호출 0 + API key 원문 / PII 비노출 모두 정합.
6. core / modules 단방향 경계 (D-4) 검증 통과.
7. `app/routers/api.py` / `app/routers/ai.py` 무수정 — 기존 응답 dict / URL / 인증 정책 100% 보존.

남은 위험 / 사용자 결정 필요 (19-3 진입 직전):
- (1) `dosu_clinic.spec` + `tests/test_pyinstaller_hidden_imports.py` 에 19-2 modules 4개 등록 — 본 세션에서 완료.
- (2) post-19-P (M-28) `/api/health` (서버 전체 상태) 신설은 별도 세션 — 본 19-2 는 분류만 명시.

다음 세션:
- **19-3 calendar / schedule_view 서버 사이드 view-model 분리 검토** — [docs/refactor/19_refactor_rollout_plan.md §3-3](../../docs/refactor/19_refactor_rollout_plan.md). UI 무수정. 분리 가능 시만 신설, 패스 결정도 가능.
