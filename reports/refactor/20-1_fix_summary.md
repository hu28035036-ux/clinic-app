# 20-1 그룹 A 변경 요약

## 변경 파일 목록

### 신규 (5개)

| 파일 | 줄 수 | 내용 |
|---|---:|---|
| `app/modules/ai/safety/__init__.py` | 16 | F-15 doctor_guard re-export |
| `app/modules/ai/safety/doctor_guard.py` | 78 | F-15 의사 단정 / 일정 / 진단 차단 패턴 + `block_doctor_claims` |
| `app/modules/privacy/__init__.py` | 22 | F-7 retention re-export |
| `app/modules/privacy/retention.py` | 132 | F-7 환자 18개월 마스킹 + AI 로그 6개월 삭제 |
| `app/modules/audit/retention.py` | 60 | F-8 audit_log 5년 삭제 |
| `tests/test_20_1_group_a.py` | 218 | 15 cases (F-15 / F-7 / F-8) |

### 수정 (3개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/services/ai/rag/pipeline.py` | +9줄 | `validate_answer` §5 단계 — F-15 doctor_guard 호출 추가 |
| `dosu_clinic.spec` | +9줄 | 신설 5개 모듈 hidden_imports 등록 |
| `tests/test_pyinstaller_hidden_imports.py` | +6줄 | `EXPECTED_19_X_MODULES_MODULES` 에 신설 5개 추가 |

### 삭제

없음.

## 파일별 변경 의도

### F-15 의사 가드 (post-19-P / M-36)

- `app/modules/ai/safety/doctor_guard.py` 신설 — 의사 단정 / 일정 / 진단 3종 정규식 + `block_doctor_claims`/`has_doctor_claim` 헬퍼.
- `app/services/ai/rag/pipeline.py:validate_answer()` 의 §5 단계로 호출 추가 — 기존 §1 PII / §2 medical claim / §3 execution claim / §4 unsupported claim 보존 + §5 의사 가드 추가.
- 사용자 §4-A 권장값 정합: 의사 단정 표현 + 의사 일정 단정 + 의사 진단 단정 모두 차단.

### F-7 privacy retention (post-19-P)

- `app/modules/privacy/retention.py` 신설 — `mask_inactive_patients` (18개월 비활성 후 PII 마스킹) + `delete_old_ai_logs` (6개월 후 삭제).
- 사용자 §4-A 권장값 정합: `PATIENT_INACTIVE_MASK_MONTHS=18`, `AI_LOG_RETENTION_MONTHS=6`.
- schema 변경 ⊥ — 기존 `Patient` / `AiUsageLog` 컬럼만 활용. 자동 트리거 ⊥ — admin endpoint / cron 별도 결정.

### F-8 audit retention (post-19-P)

- `app/modules/audit/retention.py` 신설 — `delete_old_audit_logs` (5년 후 삭제).
- 사용자 §4-A 권장값 정합: `AUDIT_LOG_RETENTION_YEARS=5`.
- 19-12 audit 모듈 (service.py / schemas.py — PII 무저장 / 500자 cap) 보존. 자동 트리거 ⊥.

### PyInstaller spec / test 갱신

- 신설 5개 모듈 (`app.modules.ai.safety` / `.doctor_guard` / `app.modules.privacy` / `.retention` / `app.modules.audit.retention`) 등록.
- `EXPECTED_19_X_MODULES_MODULES` 에 5개 추가 — parametrized 테스트 자동 생성 (5 × 2 = 10 cases).

## 호환성 보존

- 19-14 baseline 1671 cases 회귀 0.
- 응답 dict / API URL / DB schema / UI: 변경 0.
- 33+ 응답 key 셋: 보존 (본 20-1 은 응답 dict 변경 ⊥ — 가드 결과는 기존 `validate_answer` 의 `{blocked, reason, cleaned, guard_hits}` dict 안에서 처리).
- 기존 `_RE_MEDICAL_CLAIM` / `_RE_EXECUTION_CLAIM` 패턴 보존 (제거 ⊥ — `test_validate_answer_existing_medical_claim_still_blocked` 회귀 단언).

## 주석 카테고리 적용

- `# SAFETY:` — doctor_guard 모듈 docstring + retention 모듈 docstring + pipeline.py:§5 단계 (DB 근거 없는 의사 정보 응답 ⊥)
- `# NOTE:` — retention.py 사용자 §4-A 결정값 정합 명시
- `# COMPAT:` — 테스트 안 기존 가드 회귀 단언 (`_RE_MEDICAL_CLAIM` 보존)

## 5회 루프 횟수

- **1회차** — 코드 작성 + ruff (1 fix 자동 적용 — import order) + pytest 단위 → 15 passed
- **2회차** — PyInstaller hidden imports 테스트 → 205 passed
- **3회차** — 전체 회귀 → 1696 passed (회귀 0)

총 1회차 코드 작성 + 2회차 검증 단계로 5회 루프 안에 통과.
