# 20-1 그룹 A Codex 검증 요청서

## 1. 세션 이름

`20-1_group_a` — F-15 AI 의사 가드 + F-7 privacy retention + F-8 audit retention 묶음 도입.

## 2. 작업 목표

20-P-1 마스터 플랜 §4-A 사용자 권장값 정합:
- F-15: 의사 단정 / 일정 / 진단 표현 차단 가드 (RAG pipeline 통합).
- F-7: 환자 비활성 18개월 후 PII 마스킹 + AI 로그 6개월 후 삭제 (헬퍼).
- F-8: audit_log 5년 후 자동 정리 (헬퍼).

본 v1 = 헬퍼 함수만 (admin endpoint / 자동 트리거 ⊥) — 호출 시점은 후속 결정.

## 3. 변경 파일 목록 (신규 / 수정 / 삭제)

### 신규 (6개)

```
app/modules/ai/safety/__init__.py            (16줄)
app/modules/ai/safety/doctor_guard.py        (78줄)
app/modules/privacy/__init__.py              (22줄)
app/modules/privacy/retention.py             (132줄)
app/modules/audit/retention.py               (60줄)
tests/test_20_1_group_a.py                   (218줄, 15 cases)
```

### 수정 (3개)

```
app/services/ai/rag/pipeline.py              (+9줄, validate_answer §5 단계)
dosu_clinic.spec                             (+9줄, hidden_imports 5개)
tests/test_pyinstaller_hidden_imports.py     (+6줄, EXPECTED_19_X_MODULES_MODULES)
```

### 삭제

없음.

## 4. 수정 가능 범위

- `app/modules/{ai/safety,privacy}/` 신규.
- `app/modules/audit/retention.py` 추가 (기존 `audit/__init__,service,schemas.py` 보존).
- `app/services/ai/rag/pipeline.py:validate_answer()` 안에 §5 단계 호출 추가 — 기존 §1~§4 보존.
- `dosu_clinic.spec` hiddenimports 5줄 추가.
- `tests/test_pyinstaller_hidden_imports.py` `EXPECTED_19_X_MODULES_MODULES` 5개 추가.
- `tests/test_20_1_group_a.py` 신규.

## 5. 수정 금지였던 범위

- 기존 응답 dict / API URL / DB schema / UI 변경 ⊥.
- m001~m013 마이그레이션 변경 ⊥ (본 20-1 = schema 변경 ⊥).
- 기존 `_RE_MEDICAL_CLAIM` / `_RE_EXECUTION_CLAIM` 가드 패턴 보존.
- 19-12 audit `service.py` / `schemas.py` 변경 ⊥ (retention.py 만 추가).
- 19-13 `app/modules/ai/commands/` 변경 ⊥ (별도 `safety/` 폴더 신설).

## 6. 실제 변경 요약 (이동한 로직 / wrapper / 새 contract 테스트)

- **F-15**: `app.modules.ai.safety.doctor_guard.has_doctor_claim/block_doctor_claims` 신설. 정규식 3개 (이름 / 일정 / 진단). RAG pipeline.validate_answer §5 단계에서 호출.
- **F-7**: `app.modules.privacy.retention.mask_inactive_patients/delete_old_ai_logs`. Patient.appointments 가장 최근 start_at 기준 비활성 판단. AI 로그는 ts < cutoff row 삭제. dry_run / 멱등성 / 권장값 상수.
- **F-8**: `app.modules.audit.retention.delete_old_audit_logs`. AuditLog.ts < cutoff row 삭제.
- 신규 contract 테스트 = `tests/test_20_1_group_a.py` 15 cases.

## 7. 실행한 테스트

```
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
venv\Scripts\python.exe -m pytest tests/test_20_1_group_a.py -v
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q
venv\Scripts\python.exe -m pytest tests -q
```

## 8. 테스트 결과 요약

| 검증 | 결과 |
|---|---|
| ruff | All checks passed (1회 자동 fix) |
| check_db_path | exit 0 |
| `test_20_1_group_a.py` | **15 passed** in 0.21s |
| `test_pyinstaller_hidden_imports.py` | **205 passed** (신설 5개 모듈 검증 포함) |
| `pytest tests -q` 전체 | **1696 passed / 1 skipped / 10 xfailed** |

19-14 baseline 1671 → 20-1 baseline **1696** (+25). 증가분 = group_a 15 + PyInstaller 신설 모듈 10 = 25. 회귀 0.

## 9. 수정 루프 횟수

1회차 (코드 작성 + ruff autofix + pytest 단위) → 15 passed.
2회차 (PyInstaller hidden imports 단위) → 205 passed.
3회차 (전체 회귀) → 1696 passed.

총 5회 루프 안에 통과.

## 10. 실제 기능 작동확인 수행 여부 (19-C §3 ~ §17 영향 범위 기준)

- 본 20-1 은 헬퍼 함수만 (admin endpoint / 자동 트리거 ⊥) — TestClient 호출 ⊥.
- F-15 RAG pipeline 통합은 `validate_answer` 직접 호출 회귀로 검증.
- 19-C §13 J (AI / RAG / commands) 부분 검증 — `validate_answer` 의사 단정 차단 회귀.

## 11. 자동 테스트로 확인한 항목

- F-15 doctor_guard 단위: 7 cases.
- F-15 RAG pipeline 통합 회귀: 3 cases.
- F-7 환자 마스킹 + AI 로그 삭제: 3 cases.
- F-8 audit_log 삭제: 2 cases.
- 신설 5개 모듈 PyInstaller 등록 + import 가능: 10 cases.
- 19-14 baseline 회귀 0: 1671 cases 모두 통과.

## 12. 테스트 클라이언트 / API 호출로 확인한 항목

본 20-1 v1 = 헬퍼 함수만 — TestClient 호출 ⊥. F-15 는 함수 직접 호출 회귀로 충분.

## 13. 수동 확인 필요 항목

- 운영 환경에서 retention 헬퍼 트리거 시점 (admin endpoint / cron) — 후속 세션 결정.
- F-15 가드가 실제 RAG 답변 흐름에서 차단되는지 UI 수동 확인 — 운영 데이터 필요.

## 14. 이번 세션 영향 없음으로 판단한 항목

- 19-C §4 A 예약 / B 휴무 / C 치료항목·완료체크 / F 캘린더 / G SMS / H 통계 — 영향 0.
- DB schema (m001~m013) — 변경 0.

## 15. 확인하지 못한 항목과 이유

- PyInstaller 실제 빌드 + exe smoke — 본 20-1 자체 회귀에서 미실행 (Codex 빌드 검증으로 미룸).
- 운영 데이터에서 mask_inactive_patients / delete_old_ai_logs 실제 결과 — 운영 DB 접근 ⊥.

## 16. 운영 DB 접근 여부

**없음.** `scripts/check_db_path.py` exit 0 + `tests/conftest.py` 4단계 격리 + `tests/harness/db_guard.assert_safe_db_path()` 정합.

## 17. 외부 API 호출 여부

**없음.** `_block_sdk_modules` 활성. 본 20-1 은 LLM / Embedding 호출 자체가 ⊥ (의사 가드 = 정규식 / retention = DB 쿼리만).

## 18. 실제 문자 발송 여부

**없음.** sms 모듈 무영향.

## 19. 개인정보 / API key 원문 노출 여부

**없음.** `mask_inactive_patients` 가 PII 마스킹 후 commit. 응답 dict 에는 카운트만 (`candidates` / `masked` / `dry_run`).

## 20. 기존 API 응답 key 유지 여부

**유지.** 본 20-1 = 응답 dict 변경 ⊥. 가드 결과는 기존 `validate_answer` 의 `{blocked, reason, cleaned, guard_hits}` dict 안에서 처리. 33+ 응답 key 셋 보존.

## 21. 기능 작동확인 누락 여부

- 자동 테스트 / 함수 회귀는 완료.
- TestClient endpoint 호출 = 본 v1 영향 없음 (헬퍼만).
- UI 수동 확인 = 운영 데이터 필요 — 수동 확인 필요 항목으로 기록.

## 22. 다음 세션 진행 가능 여부

**yes** — Codex 검증 통과 시. caveat 후보:
- F-7 / F-8 자동 트리거 (admin endpoint / cron) 결정 시점 — 후속 세션.
- F-15 가드 패턴이 manual_qa / sms_draft / action_leave 호출지에도 통합될지 결정 — 후속 세션 (현재 RAG pipeline 만 통합).

## 23. Codex 가 직접 검증할 명령

```bash
# 코드 변경 범위 확인
git diff --stat HEAD~0 -- app/modules/ai/safety app/modules/privacy app/modules/audit app/services/ai/rag/pipeline.py dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py tests/test_20_1_group_a.py

# F-15 패턴 / 호출지 확인
grep -nE "doctor_guard|has_doctor_claim|block_doctor_claims" app/modules/ai/safety/ app/services/ai/rag/pipeline.py -r

# F-7 / F-8 정책 상수 확인
grep -nE "PATIENT_INACTIVE_MASK_MONTHS|AI_LOG_RETENTION_MONTHS|AUDIT_LOG_RETENTION_YEARS" app/modules/

# 응답 key 보존
grep -nE "blocked|reason|cleaned|guard_hits" app/services/ai/rag/pipeline.py

# 자체 회귀 baseline
venv\Scripts\python.exe -m pytest tests -q   # 1696/1/10 예상
venv\Scripts\python.exe -m pytest tests/test_20_1_group_a.py -v   # 15 passed 예상
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q   # 205 passed 예상

# DB / 외부 API 보호
venv\Scripts\python.exe scripts/check_db_path.py   # exit 0 예상
```

## 24. Codex 검증 결과 기록 위치

- [reports/refactor/20-1_codex_review.md](20-1_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 25. 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 20-1 그룹 A 검증 시작해줘. Claude Code 요약만 믿지 말고 신설 6개 파일 (`app/modules/ai/safety/`, `app/modules/privacy/`, `app/modules/audit/retention.py`, `tests/test_20_1_group_a.py`) + 수정 3개 파일 (`pipeline.py`, `dosu_clinic.spec`, `test_pyinstaller_hidden_imports.py`) 을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-1_codex_review.md 에 남겨줘."
