# 19-C 단위화 리팩토링 — 실제 기능 작동확인 체크리스트 (19_refactor_function_verification_checklist)

> 19-P-1 ~ 19-P-9 + 19-0 ~ 19-14 의 후속 공통 문서.
> 자동 테스트만으로 놓칠 수 있는 **실제 기능 흐름**을 확인하기 위한 공통 체크리스트.
> 본 문서는 *체크리스트* 문서 — 실제 코드 / 테스트 / 폴더 / 파일 / fixture / mock / 마이그레이션 미생성.

## 0. 메타

- 작성일: 2026-05-04
- 기준 브랜치: `ai-rag-v1-integration`
- 19-P-1 ~ 19-P-9 / 19-0 ~ 19-14 모두 Codex pass with caveat (yes 진입 가능) 후 작성.
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *체크리스트* 문서 — 새 폴더 / 파일 / 테스트 / fixture / 마이그레이션 미생성.
- 본 문서는 19-x (19-1 ~ 19-14 또는 후속 19-X) 리팩토링 세션마다 영향 범위에 맞게 참조.

### 0-1. 본 문서가 다루지 않는 범위

- 실제 자동 테스트 코드 작성 — 19-P-5 [테스트 전략](19_refactor_test_strategy.md) + 각 19-x 세션 별도 처리.
- 새 기능 도입 결정 — [19_refactor_rollout_plan.md §9](19_refactor_rollout_plan.md) 후속 검토 항목 표 (F-1 ~ F-15) 정합.
- v1.4.0 배포 절차 — [docs/releases/18_ai_rag_final_checklist.md](../releases/18_ai_rag_final_checklist.md) 별도 게이트.
- m014+ 마이그레이션 도입 — 19-P 비-목표.

### 0-2. 본 문서의 위치

- 19-P-1 ~ 19-P-9 = 단위화 리팩토링 *준비 단계* 문서들 (8 + 1 = 9개).
- 19-0 ~ 19-14 = *실제 코드 리팩토링* 세션들 (15개).
- **19-C (본 문서) = 19-x 리팩토링 세션이 매 세션 적용할 *실제 기능 작동확인 체크리스트*.**
- 자동 테스트 통과 + 본 체크리스트 영향 범위 확인 + Codex 검증 통과 후 다음 세션 진입.

---

## 1. 실제 기능 작동확인 공통 원칙

> 모든 19-x 세션이 자동 테스트 통과 외에 추가로 실행해야 할 공통 원칙.

| # | 원칙 | 본문 |
|---|---|---|
| V-1 | 자동 테스트 통과만으로 완료 처리 ⊥ | `pytest tests -v` / `ruff check` / `check_db_path.py` 모두 통과해도 *그 자체로* 세션 완료 ⊥. |
| V-2 | 영향 범위 기준 작동확인 | 해당 리팩토링이 영향을 줄 수 있는 실제 기능 흐름을 **테스트 DB / 임시 DB / 샘플 데이터** 기준으로 확인. |
| V-3 | 운영 DB 사용 ⊥ | `%APPDATA%\도수치료예약\clinic.db` 미접근. `scripts/check_db_path.py` + `tests/conftest.py` 4단계 격리 + `tests/harness/db_guard.assert_safe_db_path()` 로 검증. |
| V-4 | 외부 LLM / Embedding API 호출 ⊥ | 실제 OpenAI / Anthropic / 외부 Embedding API 호출 ⊥. `_block_sdk_modules` + FakeProvider / FakeEmbeddingProvider 만 사용. |
| V-5 | 실제 문자 발송 ⊥ | 실제 문자나라 / 외부 SMS provider 호출 ⊥. 외부 HTTP mock 또는 `provider.py` mock 사용. |
| V-6 | API key / 계정 / PII 원문 비노출 | API key, 문자나라 계정/비밀번호, 환자 개인정보 원문이 로그/응답/화면/AI prompt 에 노출되지 않는지 확인. |
| V-7 | 자동 vs 수동 구분 | 자동 확인 가능 항목과 수동 확인 필요 항목을 구분해서 기록. |
| V-8 | 누락 항목 사유 기록 | 확인하지 못한 항목은 *이유 + 후속 확인 세션* 을 기록. |
| V-9 | 영향 범위 밖 분류 | 이번 세션 영향 범위 밖의 기능은 "이번 세션 영향 없음" 으로 분류 (skip 사유 명시). |
| V-10 | 단정 ⊥ | 현재 기능이 없는 항목 (doctors / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 등 [19_refactor_rollout_plan.md §9](19_refactor_rollout_plan.md) F-1 ~ F-15) 을 실제 구현된 것처럼 단정 ⊥. |

---

## 2. 보고서 기록 형식

> 각 19-x 세션의 [reports/refactor/{SESSION_NAME}_test_report.md](../../reports/refactor/) 에 아래 항목 포함.

### 2-1. 7대 분류

| # | 분류 | 본문 |
|---|---|---|
| R-1 | 자동 테스트로 확인한 항목 | `pytest tests -v` / 도메인별 `pytest tests/test_<domain>_*.py -v` 통과 결과. |
| R-2 | 테스트 클라이언트 / API 호출로 확인한 항목 | `TestClient(app)` 기반 endpoint 호출 + 응답 dict 검증 결과. |
| R-3 | 수동 확인이 필요한 항목 | UI / FullCalendar 표시 / 문자 복사 흐름 등 자동 검증 부재 항목. |
| R-4 | 이번 세션 영향 없음으로 판단한 항목 | 본 19-C §3 ~ §16 의 분류 항목 중 해당 세션 범위 밖. |
| R-5 | 확인하지 못한 항목과 이유 | 환경 / 시간 / 의존성 부족 / 후속 확인 세션 명시. |
| R-6 | 보안 확인 결과 | (a) 운영 DB 접근 여부 (b) 외부 API 호출 여부 (c) 실제 문자 발송 여부 (d) 개인정보 / API key 원문 노출 여부. |
| R-7 | 결론 | (a) 다음 단계 진행 가능 여부 (b) 남은 위험 요소. |

### 2-2. 보고 형식 권장

각 보고서는 아래 7개 섹션을 포함한다 (마크다운 heading / numbered list / 표 등 형식은 자유, 7개 섹션이 모두 포함되어야 함).

1. **자동 테스트로 확인한 항목** — 통과한 pytest 케이스 / 도메인별 회귀 결과.
2. **테스트 클라이언트 / API 호출로 확인한 항목** — `TestClient(app)` 기반 endpoint 호출 + 응답 dict 검증 결과.
3. **수동 확인 필요 항목** — UI / FullCalendar / 문자 복사 / PyInstaller exe 등 자동 검증 부재 항목.
4. **이번 세션 영향 없음으로 판단한 항목** — 본 19-C §3 ~ §17 의 분류 항목 중 해당 세션 범위 밖.
5. **확인하지 못한 항목과 이유** — 환경 / 시간 / 의존성 부족 / 후속 확인 세션 명시.
6. **보안 확인 결과**
   - 운영 DB 접근: 없음 / 있음 (근거)
   - 외부 API 호출: 없음 / 있음 (근거)
   - 실제 문자 발송: 없음 / 있음 (근거)
   - 개인정보 / API key 원문 노출: 없음 / 있음 (근거)
7. **결론**
   - 다음 단계 진행 가능 여부: yes / no (근거)
   - 남은 위험 요소: …

> 본 §2-2 는 *권장 구조* 만 — 실제 보고서 파일에서는 자유 형식 가능. 단 7개 섹션 모두 누락 ⊥.

---

## 3. 모든 세션 공통 필수 확인

> 19-x 모든 세션에서 매번 확인해야 할 항목.

| # | 항목 | 검증 |
|---|---|---|
| C-1 | 기존 API URL 유지 | `git diff` + `grep -cE "^@router\." app/routers/api.py app/routers/ai.py` 카운트 일치. |
| C-2 | 기존 API 응답 key 유지 | [19_refactor_current_state.md §21](19_refactor_current_state.md) 33+ 키 셋 보존. dict 단위 비교. |
| C-3 | 기존 프론트 JS 동작 유지 | [main.html](../../app/templates/main.html) FullCalendar / Alpine 의존 키 무수정. UI 분리 ⊥. |
| C-4 | 운영 DB 접근 없음 | `scripts/check_db_path.py` 통과 + 4단계 격리 + `db_guard.assert_safe_db_path()`. |
| C-5 | 외부 API 호출 없음 | `_block_sdk_modules` 활성 + `len(provider.calls) == 0` (`local_only` 모드). |
| C-6 | 실제 문자 발송 없음 | sms `provider.py` 외부 HTTP mock 또는 차단 확인. |
| C-7 | 개인정보 / API key 원문 노출 없음 | 응답 / 로그 / AI prompt / 화면 grep — 환자 이름 / 연락처 / 차트번호 / API key 원문 부재. |
| C-8 | `pytest tests -v` 통과 | 18-8 baseline (529 passed) 또는 갱신 baseline 회귀 0. |
| C-9 | `ruff check app tests scripts` 통과 | per-file-ignores 보존. |
| C-10 | `python scripts/check_db_path.py` 통과 | exit 0 — 머지 게이트. |
| C-11 | 관련 하네스 유지 | AI / RAG / Safety / Vector / Hybrid 6개 + SMS / 휴무 AI / manual_qa 회귀 0. |
| C-12 | 기능 작동확인 결과 기록 | [reports/refactor/{SESSION_NAME}_test_report.md](../../reports/refactor/) 에 §2-2 형식으로 기록. |

---

## 4. A. 예약 기능 작동확인

> 19-4 availability / 19-9 appointments 영향 범위.

### 4-1. 예약 생성

- [ ] 정상 예약이 생성되는지 (`POST /api/appointments` → 200 + `id` / `version` / `treatment_codes` / `status`).
- [ ] 환자 / 치료사 / 치료항목 / 날짜 / 시간이 정확히 저장되는지 (응답 + DB row 비교).
- [ ] 예약 생성 후 캘린더 (`GET /api/appointments?range=...`) 에 표시되는지.
- [ ] 예약 생성 후 금일예약환자 목록에 반영되는지.
- [ ] 예약 생성 후 통계 (`/api/stats/*`) 에 기존 기준대로 반영되는지.
- [ ] 예약 생성 후 문자 대상 추출 (`/api/sms/tomorrow-targets`) 에 기존 기준대로 반영되는지.

### 4-2. 예약 수정

- [ ] 예약 날짜 변경이 되는지 (`PUT /api/appointments/{aid}`).
- [ ] 예약 시간 변경이 되는지.
- [ ] 치료사 변경이 되는지.
- [ ] 치료항목 변경이 되는지 (`treatment_codes` JSON).
- [ ] 환자 정보 연결이 유지되는지 (`patient_id`).
- [ ] 예약 수정 후 캘린더 표시가 갱신되는지.
- [ ] 예약 수정 시 자기 자신과의 충돌은 제외되는지 (자기 자신 제외 충돌 검사).

### 4-3. 예약 삭제 / 취소

- [ ] 예약 삭제 (`DELETE /api/appointments/{aid}`) 또는 취소 (`POST /api/appointments/{aid}/cancel`) 가 기존처럼 동작하는지.
- [ ] 삭제 / 취소 후 캘린더에서 사라지거나 상태가 반영되는지.
- [ ] 삭제 / 취소 후 금일예약환자 목록이 갱신되는지.
- [ ] 통계 반영 기준이 기존과 같은지.
- [ ] 문자 대상 추출에서 제외 / 포함 기준이 기존과 같은지.

### 4-4. 예약 조회

- [ ] 날짜별 예약 조회가 되는지 (`GET /api/appointments?range=...`).
- [ ] 치료사별 예약 조회가 되는지.
- [ ] 환자별 예약 조회가 되는지.
- [ ] 오늘 예약 조회가 되는지.
- [ ] 빈 날짜 조회 시 오류 없이 빈 결과가 나오는지.

### 4-5. 예약 충돌 / 차단

- [ ] 같은 치료사 / 같은 시간 중복 예약이 차단되는지.
- [ ] 시간 겹침 예약이 차단되는지.
- [ ] 종일 휴무 치료사에게 예약이 차단되는지.
- [ ] 오전반차 시간대 (< 12:00) 예약이 차단되는지.
- [ ] 오후반차 시간대 (>= 12:00) 예약이 차단되는지.
- [ ] devtools / manual POST 우회 예약도 백엔드에서 차단되는지 (R-APPT-06 정합).
- [ ] 예약 불가 사유가 기존 방식대로 표시되는지 (400 + `detail` 한국어).

### 4-6. 호환성

- [ ] 기존 예약 API URL 유지.
- [ ] 기존 예약 API 응답 key 유지 (`id` / `patient_id` / `therapist_id` / `start_at` / `end_at` / `treatment_codes` / `status` / `version` / `memo` / `is_new_patient`).
- [ ] 기존 프론트 JS 동작 유지 (FullCalendar event 형식).

---

## 5. B. 휴무 기능 작동확인

> 19-5 leaves 영향 범위.

### 5-1. 휴무 등록

- [ ] 종일 휴무 (`leave_type=full`) 등록이 되는지.
- [ ] 오전반차 (`leave_type=am`) 등록이 되는지.
- [ ] 오후반차 (`leave_type=pm`) 등록이 되는지.
- [ ] 같은 날짜에 여러 휴무 데이터가 기존 정책대로 처리되는지 (`(employee_id, leave_date)` UNIQUE / m011).
- [ ] 휴무 등록 후 캘린더 / 미니캘린더에 표시되는지.

### 5-2. 휴무 조회 / 삭제

- [ ] 치료사별 휴무 조회가 되는지.
- [ ] 날짜별 휴무 조회가 되는지.
- [ ] 휴무 삭제가 되는지.
- [ ] 삭제 후 예약 차단 / 표시가 갱신되는지.

### 5-3. 휴무 예약 차단

- [ ] 종일 휴무일 예약이 차단되는지.
- [ ] 오전반차 시간대 예약이 차단되는지.
- [ ] 오후반차 시간대 예약이 차단되는지.
- [ ] 휴무 표시 기준과 예약 차단 기준이 일치하는지 (R-LEAVE-03).

### 5-4. 휴무 UI 표시

- [ ] 미니캘린더에 휴무자 이름이 표시되는지.
- [ ] 도수치료 캘린더에 휴무 슬롯이 기존처럼 표시되는지.
- [ ] 휴무 표시가 중복되거나 어긋나지 않는지.

### 5-5. 호환성

- [ ] 기존 휴무 API 응답 key 유지 (alias `therapist_id` ↔ `employee_id` 이중 키 / `leave_kind` / `leave_type`).
- [ ] 기존 휴무 AI 테스트 (`test_ai_action_leave.py`) 유지.

---

## 6. C. 치료항목 / 완료체크 작동확인

> 19-6 treatments / completion_rules 영향 범위.

### 6-1. 치료항목

- [ ] 치료항목 목록 (`GET /api/treatments`) 이 기존처럼 조회되는지.
- [ ] 도수30, 도수60 등 기존 항목이 유지되는지.
- [ ] 체외충격파 등 다른 치료항목이 누락되지 않는지.
- [ ] 치료항목 표시명이 기존 UI 에서 깨지지 않는지.
- [ ] 치료사별 치료 가능 항목 연결 (`can_eswt` / `can_manual`) 이 유지되는지.

### 6-2. 예약과 치료항목

- [ ] 예약 생성 시 치료항목이 정확히 연결되는지 (`treatment_codes` JSON).
- [ ] 예약 수정 시 치료항목 변경이 유지되는지.
- [ ] 여러 치료항목이 있는 예약이 기존처럼 처리되는지.

### 6-3. 완료체크

- [ ] 치료항목별 완료 체크 (`POST /api/appointments/{aid}/approve`) 가 되는지.
- [ ] 도수30 완료가 도수30 항목으로 집계되는지.
- [ ] 도수60 완료가 도수60 항목으로 집계되는지.
- [ ] **도수60 이 2카운트로 계산되는 시간 가중치 방식으로 되돌아가지 않았는지** (`manual60` `count_increment=1` / [CLAUDE.md](../../CLAUDE.md) 명시 / R-TX-01).
- [ ] 각 치료항목이 개별 체크 기준으로 유지되는지.
- [ ] 완료 취소 / 해제 (`POST /api/appointments/{aid}/revert-approve`) 가 기존처럼 동작하는지.

### 6-4. 통계 연결

- [ ] 완료체크 결과가 통계에 기존 기준대로 반영되는지.
- [ ] 치료항목별 완료 통계가 기존과 같은지.
- [ ] 치료사별 완료 통계가 기존과 같은지.

### 6-5. 호환성

- [ ] 기존 완료체크 API 응답 key 유지.
- [ ] 기존 프론트 체크박스 동작 유지.

---

## 7. D. 환자 / 메모 기능 작동확인

> 19-7 patients / notes 영향 범위.

### 7-1. 환자 검색

- [ ] 이름으로 환자 검색이 되는지 (`GET /api/patients/search`).
- [ ] 차트번호로 환자 검색이 되는지.
- [ ] 연락처 기준 검색이 기존처럼 되는지.
- [ ] 동명이인 / 여러 후보가 있을 때 기존 방식대로 표시되는지.
- [ ] 환자 검색 결과에 필요한 정보가 유지되는지.

### 7-2. 환자 정보

- [ ] 환자 생성 (`POST /api/patients`) 이 기존처럼 되는지.
- [ ] 환자 수정 (`PUT /api/patients/{pid}`) 이 기존처럼 되는지.
- [ ] 환자 조회 (`GET /api/patients/{pid}`) 가 기존처럼 되는지.
- [ ] 생년월일 / 연락처 / 차트번호 (`birth_date` / `phone` / `chart_no`) 가 기존 응답 구조로 유지되는지.
- [ ] 신환 체크 (`is_new_patient`) 가 기존처럼 동작하는지.

### 7-3. 예약 연결

- [ ] 예약 생성 시 환자 연결 (`patient_id`) 이 유지되는지.
- [ ] 예약 수정 시 환자 연결이 깨지지 않는지.
- [ ] 환자 정보가 문자 대상 추출 / 통계에 기존처럼 반영되는지.

### 7-4. 메모

- [ ] 당일메모 (`Appointment.memo`) 가 기존처럼 표시 / 저장되는지.
- [ ] 지속 메모 (`Patient.memo`) 가 기존처럼 표시 / 저장되는지.
- [ ] 당일메모와 지속 메모가 섞이지 않는지 (R-PAT-04 ~ R-PAT-05).
- [ ] 환자별 메모가 다른 환자에게 잘못 연결되지 않는지.
- [ ] 예약별 메모 후보가 있으면 기존 기능 여부 확인.

### 7-5. 개인정보 보호

- [ ] 환자 개인정보 원문이 로그에 남지 않는지.
- [ ] 환자 개인정보 원문이 AI prompt 에 들어가지 않는지.
- [ ] 테스트 출력에 개인정보 원문이 불필요하게 노출되지 않는지.

---

## 8. E. 치료사 / 의사·진료진 후보 작동확인

> 19-8 staff 영향 범위.

### 8-1. 치료사

- [ ] 치료사 목록 조회 (`GET /api/employees` / alias `/api/therapists`) 가 되는지.
- [ ] 치료사 생성 / 수정 (`POST/PUT /api/employees`) 이 기존처럼 되는지.
- [ ] 치료사 활성 / 비활성 상태가 유지되는지.
- [ ] 치료사 색상 (`color`) 표시가 유지되는지.
- [ ] 치료 가능 항목 (`can_eswt` / `can_manual`) 연결이 유지되는지.
- [ ] 치료사별 예약 표시가 유지되는지.
- [ ] 치료사별 휴무 표시가 유지되는지.
- [ ] 치료사별 통계가 유지되는지.

### 8-2. 의사 / 진료진

- [ ] 현재 실제 기능이 있는지 확인 (Employee `role="doctor"` + Treatment `role="doctor"` 얇은 분기만 / 별도 폴더 부재).
- [ ] 현재 기능이 없으면 후속 검토로만 남겼는지 ([19_refactor_rollout_plan.md §9 F-1](19_refactor_rollout_plan.md)).
- [ ] 담당의 / 진료과 / 진료실 기능을 새로 구현하지 않았는지 (DEC-R14 / R-14 정합).
- [ ] AI 가 의사 / 담당의 / 진료일정을 DB 근거 없이 생성하지 않는지 (F-15 의사 가드 / M-36 후속).

### 8-3. 호환성

- [ ] 기존 치료사 API 응답 key 유지 (`_serialize_employee` 응답 dict).
- [ ] 기존 UI 색상 / 이름 표시 유지.

---

## 9. F. 캘린더 / 표시 화면 작동확인

> 19-3 calendar / 19-4 / 19-5 / 19-9 영향 범위.

### 9-1. 메인 캘린더

- [ ] 날짜별 예약이 기존처럼 표시되는지.
- [ ] 시간대별 예약 위치가 기존처럼 표시되는지.
- [ ] 치료사별 색상이 기존처럼 표시되는지.
- [ ] 휴무 슬롯이 기존처럼 표시되는지.
- [ ] 예약 클릭 / 수정 흐름이 기존처럼 되는지.

### 9-2. 미니캘린더

- [ ] 예약 있는 날짜 표시가 유지되는지.
- [ ] 휴무자 이름 표시가 유지되는지.
- [ ] 월 이동 / 날짜 선택이 기존처럼 되는지.

### 9-3. 금일예약환자

- [ ] 치료사별 환자 목록이 기존처럼 표시되는지.
- [ ] 환자 목록 스크롤 / 영역 넘침 문제가 없는지.
- [ ] 예약 생성 / 수정 / 삭제 후 목록이 갱신되는지.

### 9-4. 표시용 view model

- [ ] 표시용 데이터 분리 후에도 기존 key 가 유지되는지.
- [ ] 저장 로직과 표시 로직이 섞이지 않는지 (D-1 정합).

---

## 10. G. 문자 / SMS 기능 작동확인

> 19-10 sms 영향 범위.

### 10-1. 문자 대상 추출

- [ ] 다음날 예약 환자 목록 (`GET /api/sms/tomorrow-targets`) 이 기존처럼 추출되는지.
- [ ] 체크된 환자만 문자 대상으로 구성되는지.
- [ ] 예약 시간 / 환자명 / 치료사명이 기존처럼 들어가는지.
- [ ] 취소 / 삭제된 예약이 기존 기준대로 제외되는지.

### 10-2. 문자 내용

- [ ] 기존 문자 템플릿이 유지되는지 (`GET /api/sms/templates`).
- [ ] 예약시간이 정확히 표시되는지.
- [ ] 환자별 문자 내용이 기존처럼 출력되는지.
- [ ] 문자 내용 복사 흐름이 기존처럼 되는지 (수동 확인 가능).

### 10-3. 문자나라 / 외부 발송

- [ ] **실제 외부 문자 발송이 테스트 중 발생하지 않는지** (V-5 정합).
- [ ] 문자나라 계정 / API key / 비밀번호 원문이 노출되지 않는지 (`_sms_sanitize` / `_mask_phone_for_log` 정합).
- [ ] 문자 provider 는 테스트에서 fake / mock 으로 처리되는지 (`provider.py` 외부 HTTP 단일 경계).

### 10-4. AI 문자

- [ ] SMS AI 기존 테스트 (`test_ai_sms_validate.py` / `test_ai_sms_draft.py` / `test_ai_sms_draft_hallucination.py`) 가 유지되는지.
- [ ] AI 가 실제 외부 문자를 바로 보내지 않는지.
- [ ] 문자 초안은 preview / 확인 흐름을 유지하는지.

### 10-5. 호환성

- [ ] 기존 문자 관련 API 응답 key 유지 (`_serialize_sms_template`).
- [ ] 기존 문자 UI 흐름 유지.

---

## 11. H. 통계 기능 작동확인

> 19-11 stats 영향 범위.

### 11-1. 기본 통계

- [ ] 총 예약 수가 기존과 같은지 (`GET /api/stats/aggregate`).
- [ ] 총 완료 수가 기존과 같은지.
- [ ] 도수 예약 수가 기존과 같은지.
- [ ] 도수 완료 수가 기존과 같은지.
- [ ] 취소가 있으면 기존 기준대로 반영되는지.

### 11-2. 치료사별 통계

- [ ] 치료사별 예약 수가 기존과 같은지 (`GET /api/stats/by-therapist`).
- [ ] 치료사별 완료 수가 기존과 같은지.
- [ ] 치료사별 치료항목 집계가 기존과 같은지 (`GET /api/stats/manual-by-therapist`).

### 11-3. 치료항목별 통계

- [ ] 도수30 / 도수60 등 항목별 집계가 기존과 같은지 (`GET /api/stats/by-treatment`).
- [ ] 체외충격파 등 확장 항목이 누락되지 않는지.
- [ ] 치료항목별 개별 체크 기준이 유지되는지.
- [ ] **시간 가중치 방식으로 되돌아가지 않았는지** (`manual60=1` / R-TX-01).

### 11-4. 시간 / 요일 통계

- [ ] 시간대별 예약 / 완료 분포 (`GET /api/stats/by-hour`) 가 기존과 같은지.
- [ ] 요일별 예약 / 완료 분포 (`GET /api/stats/by-weekday`) 가 기존과 같은지.

### 11-5. 신환 통계

- [ ] 신환 수 집계가 기존과 같은지 (`Appointment.is_new_patient`).
- [ ] 신환 체크 기준이 바뀌지 않았는지.

### 11-6. 호환성

- [ ] 기존 통계 API 응답 key 유지 (8 endpoint contract / C-7 정합).
- [ ] 기존 통계 UI / 차트 / 표 유지.
- [ ] **stats 모듈이 예약 / 환자 / 치료사 / 문자 상태를 직접 변경하지 않는지** (D-7 read-only 정합).

---

## 12. I. 관리자 / 설정 / 백업 기능 작동확인

> 19-2 settings / 19-12 admin·backup·audit 영향 범위.

### 12-1. 관리자 설정

- [ ] 관리자 설정 조회 (`GET /api/system-settings`) 가 기존처럼 되는지.
- [ ] 관리자 설정 저장 (`POST /api/system-settings`) 이 기존처럼 되는지.
- [ ] AI 모드 (`local_only` / `local_first` / `ai_assist`) 설정이 기존처럼 조회되는지.
- [ ] feature flag 상태가 기존과 충돌하지 않는지 (`core/feature_flags.py` 단일 진입점).

### 12-2. API key / 계정 정보

- [ ] **API key 원문이 화면에 노출되지 않는지** (`api_key_set` boolean 만 / `api_key_masked` 부재).
- [ ] API key 원문이 로그에 노출되지 않는지.
- [ ] 문자나라 계정 / 비밀번호 원문이 노출되지 않는지.
- [ ] 등록 여부만 표시되는지.

### 12-3. 백업

- [ ] 백업 생성 (`POST /api/backup/now`) 이 기존처럼 되는지.
- [ ] 백업 목록 조회 (`GET /api/backup/list`) 가 기존처럼 되는지.
- [ ] 백업 경로 표시 (`GET /api/backup/dir`) 가 기존처럼 되는지.
- [ ] 최신 백업 복구 후보 기능 (`POST /api/backup/restore-latest`) 이 기존처럼 유지되는지.
- [ ] 복구 후 새로고침 / 재시작 안내가 기존처럼 유지되는지.
- [ ] 운영 DB 보호 원칙이 깨지지 않는지 (V-3 정합).

### 12-4. audit / export_import

- [ ] 현재 실제 기능 (`GET /api/audit-logs` / `data-convert/preview/apply`) 이 있으면 기존처럼 동작하는지.
- [ ] 현재 기능이 없으면 후속 검토 (F-7 / F-8 / F-6) 로만 남겼는지.
- [ ] 새 기능처럼 단정하지 않았는지 (V-10 정합).

---

## 13. J. AI / RAG / AI commands 작동확인

> 19-13 AI commands 영향 범위.

### 13-1. RAG

- [ ] 매뉴얼 검색 (`POST /api/ai/manual/search`) 이 기존처럼 되는지.
- [ ] 매뉴얼 질문 답변 (`POST /api/ai/manual/ask`) 이 기존처럼 되는지.
- [ ] sources 가 유지되는지.
- [ ] no_sources 에서 억지 답변하지 않는지.
- [ ] **low_confidence 에서 provider 호출이 0 인지** (R-AI-03).

### 13-2. Safety

- [ ] PII 질문이 차단 / 마스킹되는지.
- [ ] 없는 기능 질문에 임의 경로 / 기능을 만들지 않는지 (RAG hallucination guard).
- [ ] 근거 없는 예약 / 휴무 / 환자 정보를 생성하지 않는지 (D-6 / R-AI-05).
- [ ] **unknown_feature 에서 provider 호출이 0 인지**.

### 13-3. local-first

- [ ] **`local_only` 에서 LLM / Embedding 호출이 0 인지** (`len(provider.calls) == 0` + `len(embedding_provider.calls) == 0` / R-AI-02).
- [ ] `local_first` 에서 내부 처리 가능하면 외부 호출이 0 인지.
- [ ] API key 없어도 local 기능이 동작하는지.

### 13-4. Vector / Hybrid

- [ ] vector disabled 시 keyword fallback 이 되는지.
- [ ] provider error 시 fallback 이 되는지.
- [ ] hybrid 결과가 기존 API 응답 구조를 깨지 않는지.

### 13-5. AI commands

- [ ] **AI 예약 명령이 바로 실행되지 않는지** (parse → preview → execute / DEC-O 정합).
- [ ] **AI 휴무 명령이 바로 실행되지 않는지**.
- [ ] **AI 문자 명령이 바로 발송되지 않는지**.
- [ ] Safety → Preview → 사용자 승인 → Execute 흐름이 유지되는지.
- [ ] **승인 전 DB 변경이 발생하지 않는지** (HMAC 토큰 + TOCTOU 정합).
- [ ] 환자 후보에는 차트번호 / 이름 / 생년월일 / 연락처가 *근거 기반* 으로 표시되는지.
- [ ] 치료항목 약어 / alias 가 DB 기준으로 검증되는지.
- [ ] 개인정보 원문이 prompt / log 에 남지 않는지 (sha256 / 200자 cap / R-AI-07).

---

## 14. K. Health / 진단 / 네트워크 표시 작동확인

> 19-2 health / 19-12 admin 영향 범위.

### 14-1. Health

- [ ] 서버 상태 조회가 되는지 (`GET /api/admin/status` 등).
- [ ] DB 상태 조회가 되는지.
- [ ] 백업 상태 조회가 되는지.
- [ ] AI / RAG 상태 조회 (`GET /api/ai/status` / `GET /api/ai/health/public`) 가 되는지.
- [ ] vector / hybrid 상태 조회가 되는지.
- [ ] 외부 API 호출 없이 상태 조회가 되는지.

### 14-2. 네트워크 / 주소 표시

- [ ] 메인 주소 표시가 기존처럼 되는지 (M-28 후속 검토 — `/api/health` 신설 X).
- [ ] 서브 주소 표시가 기존처럼 되는지.
- [ ] PyInstaller 실행 환경에서도 주소 표시가 깨지지 않는지.

### 14-3. 보안

- [ ] **health 응답에 API key 원문이 없는지**.
- [ ] **health 응답에 개인정보 원문이 없는지**.

---

## 15. L. 공통 API / 프론트 호환 작동확인

> 모든 19-x 세션 공통 (모듈 무관).

### 15-1. API

- [ ] 기존 API URL 이 유지되는지 (C-1 정합).
- [ ] 기존 응답 key 가 유지되는지 (C-2 정합).
- [ ] 새 key 추가는 가능하더라도 기존 key 삭제 / 이름 변경이 없는지.
- [ ] 에러 응답 구조가 기존 프론트를 깨지 않는지.
- [ ] 500 에러가 남발되지 않는지.

### 15-2. 프론트

- [ ] 예약 화면이 기존처럼 열리는지.
- [ ] 환자관리 화면이 기존처럼 열리는지.
- [ ] 치료사관리 화면이 기존처럼 열리는지.
- [ ] 휴무일관리 화면이 기존처럼 열리는지.
- [ ] 예약문자 화면이 기존처럼 열리는지.
- [ ] 관리자 화면이 기존처럼 열리는지.
- [ ] 주요 버튼 클릭이 기존처럼 동작하는지.
- [ ] 테이블 / 캘린더 표시가 깨지지 않는지.

---

## 16. M. 보안 / 개인정보 / 운영 보호 작동확인

> 모든 19-x 세션 공통.

### 16-1. 운영 DB

- [ ] 테스트 중 운영 DB 경로를 사용하지 않는지.
- [ ] `%APPDATA%\Roaming\도수치료예약\clinic.db` 접근이 없는지.
- [ ] `scripts/check_db_path.py` 가 통과하는지.

### 16-2. 개인정보

- [ ] 환자명 / 연락처 / 생년월일 / 차트번호가 불필요하게 로그에 남지 않는지.
- [ ] AI prompt 에 개인정보 원문이 들어가지 않는지.
- [ ] 테스트 출력에 개인정보 원문이 남지 않는지.

### 16-3. API key / 계정

- [ ] OpenAI / 외부 AI API key 원문 노출 없음.
- [ ] 문자나라 계정 / 비밀번호 원문 노출 없음.
- [ ] 등록 여부만 표시.

### 16-4. 외부 호출

- [ ] 실제 LLM API 호출 없음.
- [ ] 실제 Embedding API 호출 없음.
- [ ] 실제 문자 발송 없음.
- [ ] 테스트에서는 fake / mock provider 사용.

---

## 17. N. PyInstaller / 배포 작동확인

> 19-14 종료 게이트 영향 범위 (사용자 승인 시).

### 17-1. 빌드

- [ ] 기존 PyInstaller 빌드 명령 (`pyinstaller --noconfirm dosu_clinic.spec`) 이 실행되는지.
- [ ] 빌드가 성공하는지.
- [ ] hidden import 누락이 없는지 (`tests/test_pyinstaller_hidden_imports.py` 53+ tests).
- [ ] 새로 분리한 modules / core 파일이 빌드에 포함되는지.

### 17-2. 실행

- [ ] 빌드 산출물이 실행되는지.
- [ ] 기본 화면이 열리는지.
- [ ] 주요 API 가 응답하는지.
- [ ] DB 경로가 기존 기준대로 잡히는지.
- [ ] static 파일이 누락되지 않았는지.
- [ ] AI / RAG 관련 파일 import 오류가 없는지.

### 17-3. 주의

- [ ] 빌드 확인 중 운영 DB 를 직접 건드리지 않는다 (`DOSU_DB_PATH=$(pwd)/.test-build-tmp/test_clinic.db` 등 임시 경로 사용).
- [ ] 빌드 실패 수정은 최소 변경만 허용한다.
- [ ] 실제 빌드는 [CLAUDE.md](../../CLAUDE.md) 배포 규칙 — *사용자 명시 승인 시* 만 진행.

---

## 18. 세션별 영향 범위 매핑

> 각 19-x 세션이 본 §4 ~ §17 중 어느 항목에 영향을 주는지 빠른 인덱스. 세션 작업 시 해당 항목만 §3 (공통) + 영향 항목 확인.

| 세션 | 영향 §  | 비고 |
|---|---|---|
| **19-0** baseline 재고정 | §3 (공통 모두) | 분리 X — baseline 회귀 0 확인. |
| **19-1** core | §3 + §15 + §16 | 응답 키 0 변경 / 운영 DB 보호. |
| **19-2** settings/feature_flags/health | §3 + §12 + §14 + §15 + §16 | API key 비노출 / health 응답. |
| **19-3** calendar (view-model) | §3 + §9 + §15 | UI 무수정 — view-model only. |
| **19-4** availability | §3 + §4 + §5 + §15 + §16 | 점심창 / 충돌 / 휴무 차단 / 반차. |
| **19-5** leaves | §3 + §5 + §9 + §13 + §15 + §16 | `_upsert_employee_leave_core` 단일 진실원천 + AI action_leave 보존. |
| **19-6** treatments / completion_rules | §3 + §6 + §11 + §15 | `manual60=1` 보존 / 통계 회귀 0. |
| **19-7** patients / notes / data-convert | §3 + §7 + §12 + §15 + §16 | PII 비노출 / 메모 / data-convert. |
| **19-8** staff (therapists + doctors 분기) | §3 + §8 + §9 + §15 | alias 이중 키 / `_doctor_codes_set` 분기 / **F-1 의사 부재 단정 ⊥**. |
| **19-9** appointments | §3 + §4 + §6 + §9 + §11 + §15 + §16 | 마지막 + 가장 위험 / 낙관적 락 / FullCalendar. |
| **19-10** sms | §3 + §10 + §12 + §15 + §16 | 자동 발송 트리거 ⊥ / API key 마스킹. |
| **19-11** stats | §3 + §6 + §11 + §15 | 8 endpoint contract / read-only 정책. |
| **19-12** admin / backup / audit | §3 + §12 + §14 + §15 + §16 | PBKDF2 / atomic rename / audit PII ⊥. |
| **19-13** AI commands | §3 + §5 + §10 + §13 + §15 + §16 | local-first / 33+ 응답 키 / HMAC + TOCTOU. |
| **19-14** 종료 게이트 | §3 + §17 + §15 + §16 | PyInstaller 빌드 + exe smoke (사용자 승인 시). |

---

## 19. 종합

- 본 19-C = 자동 테스트만으로 놓칠 수 있는 *실제 기능 흐름* 확인 공통 체크리스트.
- §1 공통 원칙 V-1 ~ V-10 = 자동 테스트 통과 + 영향 범위 작동확인 + 운영 DB ⊥ + 외부 API ⊥ + 실제 문자 발송 ⊥ + PII / API key 비노출 + 자동/수동 구분 + 누락 사유 기록 + 영향 없음 분류 + 부재 항목 단정 ⊥.
- §2 보고 형식 R-1 ~ R-7 = 자동 테스트 / API 호출 / 수동 / 영향 없음 / 확인 못함 / 보안 / 결론.
- §3 공통 필수 확인 C-1 ~ C-12 = URL / 응답 key / 프론트 / 운영 DB / 외부 API / 문자 발송 / PII / pytest / ruff / check_db_path / 하네스 / 작동확인 기록.
- §4 ~ §17 = 14개 기능 영역 (예약 / 휴무 / 치료항목·완료체크 / 환자·메모 / 치료사·의사 / 캘린더 / SMS / 통계 / 관리자·백업 / AI·RAG·commands / Health·진단 / API·프론트 / 보안 / PyInstaller).
- §18 세션별 영향 범위 매핑 = 19-0 ~ 19-14 각 세션이 어느 §에 영향을 주는지 인덱스. 세션 작업 시 해당 항목만 작동확인.
- 본 19-C 는 **read-only 문서 세션** — 코드 / 테스트 / fixture / 마이그레이션 / spec / requirements 1바이트도 수정 ⊥.
- 다음 단계 = 본 19-C Codex 검증 후 → 후속 19-x 리팩토링 세션부터 본 체크리스트 영향 범위 확인 + 보고서 §2-2 형식으로 기록 의무화.
