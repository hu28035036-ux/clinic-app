# 19-7 patients / notes 환자·메모 경계 분리 — 변경 요약

> 19-7 = **일곱 번째 실제 코드 리팩토링 세션**. `app/modules/patients/` +
> `app/modules/notes/` 후보 구조 신설 — 환자 직렬화 + 중복 검사 + 신환 체크 + PII
> 마스킹 + 메모 분류 + 취소 prefix.
> 5회 루프 3회차 통과 (938 passed) — 19-6 baseline 회귀 0.

## 0. 메타

- 세션 이름: **19-7 patients / notes 환자·메모 경계 분리**
- 시작 HEAD: `67ce889` (19-6 treatments)
- 직전 19-6 Codex: pass — yes 19-7 진입 가능

### 0-1. Revision 이력

| 회차 | 결과 | 변경 |
|---|---|---|
| r1 | 조건부 통과 (Codex 19-7 r1 — caveat 1: contract 테스트 줄 수 670 vs 662 / caveat 2: `__pycache__` 잔여 / caveat 3: `docs/ai/` untracked 19-7 무관) | 초기 작성 |
| r2 | (본 revision) | **r1 caveat 1 + 2 보정** — `tests/test_19_7_patients_notes.py` **662** lines (ruff `--fix` 후 실측), `__pycache__` 정리. 코드 / 테스트 동작 변경 0 — 보고서 수치만 보정. |

## 1. 변경 파일 목록

### 신규 (7개)

| 파일 | 라인 수 | 종류 |
|---|---|---|
| `app/modules/patients/__init__.py` | 30 | 신규 facade |
| `app/modules/patients/rules.py` | 239 | 신규 helper (12 + 정책 상수) — 중복 검사 / 신환 체크 / PII 마스킹 (5 mask + summary + scrub) |
| `app/modules/patients/repository.py` | 120 | 신규 helper (6 — DB 호출자 주입, lazy import) |
| `app/modules/patients/service.py` | 173 | 신규 helper (5) — counts dict / patient_to_dict / light / search envelope / manual_history_summary |
| `app/modules/notes/__init__.py` | 31 | 신규 facade — *현재 구현 2종 명시 (단정 ⊥)* |
| `app/modules/notes/rules.py` | 137 | 신규 helper (5 + 정책 상수) — NOTE_KIND / append_cancel_memo / mask_memo_for_log / persistent vs per-appointment |
| `tests/test_19_7_patients_notes.py` | **662** (실측 `wc -l`) | 신규 contract (80 테스트) |

합계 — helper **28** (patients 23 + notes 5).

### 수정 (2개)

| 파일 | 변경 |
|---|---|
| `dosu_clinic.spec` | +9 lines (19-7 modules 6개 hidden imports) |
| `tests/test_pyinstaller_hidden_imports.py` | +7 lines (`EXPECTED_19_X_MODULES_MODULES` 17 → 23) |

### 무수정

`app/routers/api.py` (모든 환자 / 메모 / 검색 / 신환 체크 핸들러 + 본체 함수 무수정),
`app/routers/ai.py`, `app/services/**`, `app/models/**`, `app/migrations/**`,
`app/templates/**`, `app/static/**`, `tests/conftest.py`, `tests/harness/**`,
`app/modules/{appointments,leaves,calendar,treatments,settings,health}/`.

## 2. 본 세션 의도 / 이유

### 의도

19-P-2 §2-1 V2 트리의 `app/modules/patients/` + `app/modules/notes/` 후보 자리를
*최소 범위* 로 신설. 환자 / 메모 도메인 helper + PII 마스킹 정책 명시.

### 이유

1. **사용자 명시 "환자 검색, 신환 체크, 환자별 메모, 예약별 메모 후보, 당일메모/지속메모
   경계를 문서와 코드 구조에서 명확히 합니다"**: notes 패키지 docstring + rules.py
   에서 *현재 2종만 구현* 명시 (Patient.memo / Appointment.memo) + 후속 검토 분류 명시.
2. **사용자 명시 "당일메모와 지속 메모는 성격이 다르므로 혼동하지 않습니다"**:
   `is_persistent_note` / `is_per_appointment_note` helper 분리 + RISK 주석 (공식 정의 ⊥).
3. **사용자 명시 "현재 기능에 없는 메모 유형은 실제 구현된 것처럼 단정하지 말고 후속
   검토로 표시합니다"**: __init__ docstring + rules NOTE 주석 — m014+ 후속 분류 명시.
4. **사용자 명시 "개인정보 원문이 로그/AI prompt/테스트 출력에 불필요하게 노출되지
   않도록 경계를 정리합니다"**: PII 마스킹 helper 5종 (name/phone/birth/memo/chart) +
   `_scrub_pii_patterns` (전화/주민 패턴 → `***`) — 운영 응답에는 평문 그대로 (UI 정합).
5. **사용자 명시 "라우터 / 서비스 본체 무수정"**: api.py 의 모든 환자 / 메모 핸들러
   본체 무수정. 19-7 helper 는 byte-equivalent 동등 helper 만.

## 3. 새로 만든 modules.patients / modules.notes 구조

```
app/modules/patients/
├── __init__.py                 (30 lines, patients 패키지 facade)
├── rules.py                    (239 lines, helper 12 + 정책 상수)
│   ├── 중복 검사: normalize_for_duplicate_check / should_check_chart_no_duplicate /
│   │             should_check_name_birth_duplicate + DUPLICATE_*_MESSAGE
│   ├── 신환 체크: derive_has_new_patient_flag / derive_has_manual_history
│   └── PII 마스킹: mask_name / mask_phone / mask_birth_date / mask_memo /
│                  mask_chart_no / patient_summary_for_log + _scrub_pii_patterns
├── repository.py               (120 lines, helper 6 — lazy app.models)
│   └── list_all_patients / get_patient_by_id / find_patient_by_chart_no /
│      find_patient_by_name_birth / list_patient_counts /
│      list_patient_appointments_active
└── service.py                  (173 lines, helper 5)
    └── build_patient_counts_dict / build_patient_dict (9키) /
       build_patient_light_dict (7키) / build_patient_search_response (6키 envelope) /
       build_manual_history_summary (5키)

app/modules/notes/
├── __init__.py                 (31 lines, notes 패키지 facade — 현재 2종 명시)
└── rules.py                    (137 lines, helper 5 + 정책 상수)
    ├── 메모 종류 enum: NOTE_KIND_PATIENT / NOTE_KIND_APPOINTMENT
    ├── append_cancel_memo (api.py:cancel_appointment 정합)
    ├── mask_memo_for_log (patients.mask_memo 동등)
    └── is_persistent_note / is_per_appointment_note
```

## 4. 실제 이동한 환자 로직

**0 줄 이동** — 모두 facade / 동등 helper.

| api.py | 19-7 helper |
|---|---|
| `_check_patient_duplicate` (line 1408) | `rules.normalize_for_duplicate_check` + `should_check_*` 분기 + 메시지 상수 |
| `_patient_counts_dict` (line 1213) | `service.build_patient_counts_dict` |
| `_patient_to_dict` (line 1235) | `service.build_patient_dict` (9키) |
| `list_patients(light=1)` 응답 dict | `service.build_patient_light_dict` (7키) |
| `search_patients` 응답 envelope | `service.build_patient_search_response` (6키) |
| `patient_manual_history_summary` 응답 (line 1516~1522) | `service.build_manual_history_summary` (5키) |
| `_serialize_patients_bulk` (line 1357) — N+1 회피 일괄 직렬화 | (라우터에서 직접 사용 — 19-7 helper 미정의, 19-9 시점 추가 후보) |

## 5. 실제 이동한 메모 로직

**0 줄 이동** — 모두 동등 helper.

| api.py | 19-7 helper |
|---|---|
| `cancel_appointment` 의 `\\n[취소] {memo}` prefix (line 2016) | `notes.rules.append_cancel_memo` (byte-equivalent) |
| 메모 PII 마스킹 (현재 부재) | `patients.rules.mask_memo` + `notes.rules.mask_memo_for_log` (전화 / 주민 스크럽 + truncate) |
| 메모 분류 (Patient.memo / Appointment.memo) | `notes.rules.NOTE_KIND_*` + `is_persistent_note` / `is_per_appointment_note` |

## 6. 유지한 compatibility wrapper

28 helper 모두 byte-equivalent 동등 helper. 19-9 시점 라우터 채택 후보.

## 7. 기존 API 응답 구조 유지 여부

✓ **100% 보존** — `app/routers/api.py` 무수정.

## 8. 환자 검색 / 신환 체크 동작 유지 여부

✓ **유지** — `_check_patient_duplicate` / `search_patients` / `patient_manual_history_summary`
본체 무수정. test_admin_ui_smoke.py + 라우터 endpoint 회귀 0.

## 9. 당일메모 / 지속메모 / 환자별 메모 경계 유지 여부

✓ **유지 + 명시**:
- 현재 구현 = `Patient.memo` (지속 메모 *후보*) + `Appointment.memo` (당일 메모 *후보*)
- *공식 정의 단정 ⊥* — RISK 주석으로 명시
- 후속 검토: m014+ Note 테이블 / 작성자 / 카테고리 별도 분리 후보

## 10. 기존 예약 / 문자 / 통계 영향 여부

✗ **무영향** — 라우터 / SMS / 통계 / AI 본체 무수정. SMS validate 11 + draft 11 +
action_leave 44 + 통계 / 예약 / 휴무 회귀 0.

## 11. 개인정보 / 운영 DB / 외부 API 보호 결과

### 11-1. 개인정보 (PII) 보호

✓ **강화**:
- 5종 마스킹 helper (name / phone / birth / memo / chart_no)
- `_scrub_pii_patterns` — 메모 안 전화/주민 패턴 → `***` 사전 스크럽 (truncate head 노출 ⊥)
- `patient_summary_for_log` 통합 dict — 로그 / AI prompt / 진단 출력 전용
- 운영 응답 dict 는 *기존 평문 그대로* (UI / SMS / 검색 흐름이 평문 PII 필요)
- contract 테스트 `test_patient_summary_for_log_does_not_leak_pii` 가 회귀 보호

### 11-2. 운영 DB 보호

✓ **100% 보호** — `check_db_path.py` exit 0. repository 가 DB 호출자 주입 + lazy import.

### 11-3. 외부 API 호출

✓ **0건** — `test_helpers_do_not_invoke_provider_or_db` 통과.

## 12. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 (ast 6 검증):
- `patients.rules`: `re` + `typing` 만
- `patients.repository`: top-level 부재 (`app.models` lazy)
- `patients.service`: `app.routers` / `fastapi` ⊥
- `notes.rules`: `re` + `typing` 만
- `patients.__init__` / `notes.__init__`: `app.models` ⊥

→ **modules.patients ↔ modules.notes 직접 import ⊥** — 평행 정의 (mask_memo 동등성은
contract 테스트가 보호).

## 13. 실행한 테스트와 결과

- `pytest tests`: **938 passed, 1 skipped, 7 xfailed** (= 846 + 92 신규)
- `ruff`: All checks passed!
- `check_db_path`: exit 0
- PyInstaller: **115 passed**
- 19-7 contract: **80 passed**
- 회귀: **262 passed, 1 skipped, 3 xfailed** (admin / appointment / availability /
  leaves / treatments / AI action_leave / SMS validate / SMS draft)

## 14. 주석 / 문서화 적용 내용

| 카테고리 | 주요 위치 |
|---|---|
| `# COMPAT:` | 7 신규 파일 + 28 helper docstring |
| `# SAFETY:` | __init__ + rules docstring + 마스킹 helper 다수 |
| `# NOTE:` | 메모 분류 / 마스킹 정책 / 단정 ⊥ |
| `# RISK:` | __init__ + rules — *PII audit_log 노출 위험* / *메모 분류 단정 ⊥* / *마스킹 정책 변경 영향* |
| `TODO(19-x)` | 0 — 후속 작업 모두 19-9 / 19-12 / m014+ 명시 |

## 15. 생성한 리포트 파일

- `reports/refactor/19-7_test_report.md`
- `reports/refactor/19-7_fix_summary.md`
- `reports/refactor/19-7_codex_review_request.md`
- `latest_*.md` 3개 동기화

## 16. 남은 위험 요소

| # | 위험 | 분류 | 해결 시점 |
|---|---|---|---|
| 1 | 19-7 helpers 미채택 (라우터 / 로그 / AI prompt) | 의도 | 19-9 / 19-13 |
| 2 | `_check_patient_duplicate` / `_patient_to_dict` 등 두 사본 공존 | 알려진 — 19-9 통합 | 19-9 |
| 3 | data-convert 흐름 (~600줄 `_dc_*`) 미분리 | 후속 | 19-12 export_import |
| 4 | mask_memo PII 스크럽 정책이 두 모듈 (patients + notes) 평행 정의 | 알려진 — contract 테스트 보호 | post-19-P (core/pii_masking.py 통합) |
| 5 | 메모 분류 (당일/지속) 공식 정의 부재 — 매핑은 후속 결정 | RISK 주석 명시 | m014+ |

## 17. Codex 검증으로 넘겨도 되는지 자체 판단

**yes — Codex 검증 진입 가능**.

근거:
1. 5회 루프 3회차 통과 (1회차 SAFETY 강화 — PII 스크럽 추가).
2. 19-6 baseline (846/1/7) 회귀 0 — 신규 +92 만 추가 (총 938).
3. ruff / check_db_path / PyInstaller 115 tests 모두 통과.
4. 19-7 80 contract + 회귀 262 tests 모두 통과.
5. PII 마스킹 강화 (전화 / 주민 패턴 스크럽).
6. 라우터 / SMS / AI / 통계 / 휴무 / 예약 / availability / treatments 본체 무수정.
7. 운영 DB 미접근 + 외부 API 호출 0.
8. modules.patients / notes 단방향 경계 (D-4) 검증 통과.
9. 사용자 명시 14 금지 항목 모두 준수.
