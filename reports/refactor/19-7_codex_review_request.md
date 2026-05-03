# 19-7 patients / notes 환자·메모 경계 분리 — Codex 검증 요청서

> 사용자 양식 19개 항목 정합. Codex 가 본 문서를 시작점으로 쓰되 **실제 diff /
> 변경 파일 / 결과 / 로그를 독립적으로 확인** 한다.

## r2 Revision (Codex 19-7 r1 caveat 보정)

| 항목 | r1 표기 | 실측 (r2 보정) |
|---|---|---|
| `tests/test_19_7_patients_notes.py` | 670 lines | **662 lines** |
| `__pycache__` | 잔여 | **정리됨** |
| `docs/ai/` untracked | 19-7 무관 (이전 세션과 동일) | 별도 기획 문서 — 19-7 커밋 범위 외 |

→ 코드 / 테스트 동작 변경 0 — 보고서 수치만 보정. r1 검증 결과 (조건부 통과,
yes 19-8 진입 가능) 유지.

---

## 1. 세션 이름

**19-7 patients / notes 환자·메모 경계 분리**.

## 2. 이번 세션 목표

`app/modules/patients/` + `app/modules/notes/` 후보 구조 신설 — 환자 직렬화 + 중복
검사 + 신환 체크 + PII 마스킹 + 메모 분류 + 취소 prefix. 라우터 / SMS / AI 본체 무수정.

## 3. 변경 파일 목록

### 신규 (7개)

| 파일 | 라인 수 | 종류 |
|---|---|---|
| `app/modules/patients/__init__.py` | 30 | facade |
| `app/modules/patients/rules.py` | 239 | helper 12 + 정책 상수 |
| `app/modules/patients/repository.py` | 120 | helper 6 (lazy import) |
| `app/modules/patients/service.py` | 173 | helper 5 |
| `app/modules/notes/__init__.py` | 31 | facade (현재 2종 명시) |
| `app/modules/notes/rules.py` | 137 | helper 5 + 정책 상수 |
| `tests/test_19_7_patients_notes.py` | **662** (r2 보정) | contract 80 테스트 |

### 수정 (2개)

| 파일 | 변경 |
|---|---|
| `dosu_clinic.spec` | +9 lines (19-7 modules 6개) |
| `tests/test_pyinstaller_hidden_imports.py` | +7 lines (`EXPECTED_19_X_MODULES_MODULES` 17 → 23) |

### 무수정

`app/routers/api.py` (모든 환자 / 메모 / 검색 / 신환 체크 핸들러 + 본체 함수 무수정),
`app/routers/ai.py`, `app/services/**`, `app/models/**`, `app/migrations/**`,
`app/templates/**`, `app/static/**`, `tests/conftest.py`, `tests/harness/**`,
`app/modules/{appointments,leaves,calendar,treatments,settings,health}/`.

## 4. 실제 이동 / 분리한 환자 로직

**0 줄 이동**:

| api.py | 19-7 helper |
|---|---|
| `_check_patient_duplicate` (line 1408) | `rules.normalize_for_duplicate_check` + 분기 + 메시지 상수 |
| `_patient_counts_dict` (line 1213) | `service.build_patient_counts_dict` (9키 per item) |
| `_patient_to_dict` (line 1235) | `service.build_patient_dict` (9키) |
| `list_patients(light=1)` 응답 | `service.build_patient_light_dict` (7키) |
| `search_patients` 응답 envelope | `service.build_patient_search_response` (6키) |
| `patient_manual_history_summary` 응답 (5키) | `service.build_manual_history_summary` |

## 5. 실제 이동 / 분리한 메모 로직

**0 줄 이동**:

| api.py | 19-7 helper |
|---|---|
| `cancel_appointment` 의 `\n[취소] {memo}` (line 2016) | `notes.rules.append_cancel_memo` (byte-equivalent) |
| (현재 부재) 메모 PII 마스킹 | `patients.rules.mask_memo` + `notes.rules.mask_memo_for_log` (전화/주민 스크럽 + truncate) |
| (현재 부재) 메모 분류 enum | `notes.rules.NOTE_KIND_*` + `is_persistent_note` / `is_per_appointment_note` |

## 6. Compatibility wrapper 유지 여부

✓ **유지**. 28 helper 모두 byte-equivalent 동등 helper. 라우터 미채택 (19-9 시점).

## 7. 수정 금지 범위 준수 여부

✓ **모두 준수**:

| 금지 항목 | 결과 |
|---|---|
| 예약 생성/수정/삭제 전체 흐름 대규모 변경 | ✗ — api.py 무수정 |
| 예약 API 응답 key 변경 | ✗ |
| DB schema / migration 생성 | ✗ |
| UI 디자인 변경 | ✗ |
| 통계 집계 기준 변경 | ✗ |
| 문자/SMS / 휴무/availability/treatments 로직 변경 | ✗ |
| AI/RAG 로직 변경 | ✗ |
| **개인정보 원문 로그 저장** | ✗ — `mask_memo` PII 스크럽 + `patient_summary_for_log` 마스킹 dict |
| 하네스/테스트 약화 | ✗ |
| 운영 DB 접근 / 외부 API 호출 | ✗ |
| `requirements.txt` / spec 불필요 수정 | ✗ — spec 6개 hidden imports 만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✗ — action_leave 44 / sms 22 회귀 0 |

## 8. 기존 API 응답 key 유지 여부

✓ **100% 보존**.

| URL | 응답 키 | 보존 |
|---|---|---|
| `GET /api/patients?light=1` | 7키 | ✓ |
| `GET /api/patients/search` | 6키 envelope | ✓ |
| `GET /api/patients/{pid}/manual-history-summary` | 5키 | ✓ |
| `GET /api/patients/{pid}` | 9키 (counts) | ✓ |
| `PATCH /api/patients/{pid}/memo` | ok | ✓ |
| `POST /api/appointments/{aid}/cancel` 메모 prefix | `\n[취소] {memo}` | ✓ |

## 9. 환자 검색 / 신환 체크 동작 유지 여부

✓ **유지** — `search_patients` / `patient_manual_history_summary` 본체 무수정. endpoint
회귀 통과.

## 10. 당일메모 / 지속메모 / 환자별 메모 경계 유지 여부

✓ **유지 + 명시**:
- 현재 구현 = `Patient.memo` (지속 후보) + `Appointment.memo` (당일 후보) — 2종만
- *공식 정의 단정 ⊥* — RISK 주석 명시
- 별도 `Note` 테이블 / 카테고리 / 작성자 분리 = 후속 검토 (m014+)

## 11. 개인정보 원문 로그 / 응답 / prompt 노출 여부

✓ **노출 ⊥**:
- 5종 마스킹 helper + `_scrub_pii_patterns` (전화 / 주민 패턴 → `***`)
- `patient_summary_for_log` 결과 dict 에 *원문 PII* 포함 ⊥ (contract 테스트 보호)
- 운영 응답 dict 는 *기존 평문 그대로* (UI / SMS 발송 / 검색 모달 흐름 정합) — 마스킹
  정책 변경 ⊥

## 12. 기존 예약 / 문자 / 통계 영향 여부

✗ **무영향** — 라우터 / SMS / 통계 / AI 본체 무수정. 회귀 262 tests 통과.

## 13. 운영 DB 보호 여부

✓ **100% 보호** — `check_db_path.py` exit 0. repository 의 DB 세션 호출자 주입 +
lazy import.

## 14. 외부 API 호출 여부

✓ **0건** — `test_helpers_do_not_invoke_provider_or_db` 통과.

## 15. 순환참조 위험 여부

✓ **0건** — D-4 단방향 경계 (ast 6 검증):
- `patients.rules`: `re` + `typing` 만
- `patients.repository`: top-level 부재 (`app.models` lazy)
- `patients.service`: `app.routers` / `fastapi` ⊥
- `notes.rules`: `re` + `typing` 만
- `patients.__init__` / `notes.__init__`: 외부 미참조

→ **modules.patients ↔ modules.notes 직접 import ⊥** — 평행 정의.

## 16. 주석 / 문서화 기준 적용 여부

✓ **모두 적용**:

| # | 기준 | 적용 |
|---|---|---|
| 1 | 새 파일 상단 docstring | 7 신규 파일 모두 |
| 2 | 주요 helper 함수 docstring | 28 helper 모두 (COMPAT 명시) |
| 3 | API/UI 호환 wrapper `COMPAT` 주석 | 다수 |
| 4 | 개인정보 마스킹 / 운영 DB 보호 부분 `SAFETY` 주석 | 다수 |
| 5 | 당일메모 / 지속메모 / 환자별 메모 경계 `NOTE`/`RISK` 주석 | 다수 |
| 6 | TODO(19-x) 형식 | 0 (모든 후속 19-9 / 19-12 / m014+ 명시) |
| 7 | 의미 없는 모든 줄 주석 금지 | ✓ |
| 8 | 주석 작성 때문에 기능 동작 변경 금지 | ✓ |

## 17. 실행한 테스트와 결과

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `pytest tests -q` | **938 passed, 1 skipped, 7 xfailed** |
| C-2 | `ruff check app tests scripts` | **All checks passed!** (자동 fix 1회) |
| C-3 | `scripts/check_db_path.py` | exit 0 |
| C-4 | PyInstaller hidden imports | **115 passed** |
| C-5 | 19-7 contract | **80 passed** |
| C-6 | 회귀 (admin/예약/availability/leaves/treatments/AI/SMS) | **262 passed, 1 skipped, 3 xfailed** |

## 18. 실패 / 수정 루프 횟수

| 회차 | 결과 |
|---|---|
| 1 | `test_patient_summary_for_log_does_not_leak_pii` 1건 실패: `mask_memo` truncate head 안 전화번호 노출 |
| 2 | `_scrub_pii_patterns` (전화/주민 패턴 → `***`) 추가. C-1 ~ C-6 통과. ruff `I001` 1건 |
| 3 | `ruff check --fix` 자동 정렬 → **모두 통과** ✓ |

→ **5회 루프 3회차 통과**. 1회차 실패는 SAFETY 정책 강화 (PII 스크럽 추가).

## 19. 19-8 therapists / doctors 또는 medical_staff 경계 정리로 넘어가도 되는지 판단 기준

**yes — 19-8 진입 가능**.

근거:
1. **5회 루프 3회차 통과** — SAFETY 강화 1회 + ruff 자동 fix 1회.
2. **19-6 baseline (846/1/7) 회귀 0** — 신규 +92 (총 938).
3. **ruff / check_db_path / PyInstaller 115 tests 모두 통과**.
4. **19-7 80 contract + 회귀 262 tests 모두 통과**.
5. **PII 보호 강화** — 마스킹 + 스크럽 정책 + contract 테스트 보호.
6. **라우터 / SMS / AI / 통계 / 휴무 / 예약 / treatments 본체 무수정**.
7. **운영 DB 미접근 + 외부 API 호출 0**.
8. **modules.patients / notes 단방향 경계 (D-4) 검증 통과 (ast 6)**.
9. **사용자 명시 14 금지 항목 모두 준수**.

남은 위험:
- (1) 19-7 helpers 미채택 (의도) — 19-9 / 19-13 시점 채택.
- (2) `_check_patient_duplicate` / `_patient_to_dict` 등 두 사본 공존 — 19-9 통합.
- (3) data-convert ~600줄 `_dc_*` 분리 — 19-12 export_import.
- (4) mask_memo PII 스크럽 정책 두 모듈 평행 정의 — post-19-P core 통합.

다음 세션:
- **19-8 therapists / doctors 또는 medical_staff 경계 정리** — Employee role 분기 +
  alias `therapist_id` 이중 키 + doctors 후속 검토 분류 명시.

---

## Codex 가 집중 검토할 파일

1. `app/modules/patients/__init__.py` — 패키지 facade.
2. `app/modules/patients/rules.py` — 12 helper. PII 스크럽 + 마스킹 정책.
3. `app/modules/patients/service.py` — 5 직렬화 helper. api.py 응답 dict 정합.
4. `app/modules/patients/repository.py` — lazy import.
5. `app/modules/notes/__init__.py` + `rules.py` — *현재 2종 명시 + 단정 ⊥*.
6. `tests/test_19_7_patients_notes.py` — 80 contract.
7. `dosu_clinic.spec` 19-7 추가 9줄 + `tests/test_pyinstaller_hidden_imports.py` 7줄.

## Codex 가 반드시 확인할 체크리스트

1. **응답 키 100% 보존** — api.py 무수정.
2. **byte-equivalent** — patient_to_dict 9키 / light 7키 / search 6키 / manual_history 5키 /
   counts dict / append_cancel_memo / mask_memo (PII 스크럽 + truncate).
3. **PII 보호** — 5종 마스킹 helper + `_scrub_pii_patterns` 동작. 운영 응답 평문 정책 보존.
4. **메모 분류** — 현재 2종만 (Patient/Appointment). *공식 정의 단정 ⊥* (RISK 주석).
5. **단방향 경계 (D-4 ast 6)** — patients ↔ notes 직접 import ⊥.
6. **운영 DB 미접근** + **외부 API 호출 0**.
7. **PyInstaller 빌드 안전성** — 19-7 modules 6개 + 12 신규 tests.
8. **5회 루프 3회차 통과**.

## 자체 판단

**yes — 19-8 진입 가능 (Codex 검증 통과 후)**.
