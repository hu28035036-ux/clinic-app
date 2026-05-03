# 19-P-3 단위화 리팩토링 — 모듈 매핑 (19_refactor_module_map)

> 19-P-1 [현재 구조](19_refactor_current_state.md) + 19-P-2 [목표 아키텍처](19_refactor_target_architecture.md) 를 기준으로,
> 30개 모듈 후보별로 **현재 위치 → 목표 위치** 매핑을 정리한다.
> 본 문서는 *매핑 의도* 문서 — 실제 코드 이동은 19-P-4+ 별도 세션.

## 0. 메타

- 작성일: 2026-05-02
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: 529 passed, 1 skipped, 7 xfailed
- 19-P-1 r2 / 19-P-2 r3 Codex 판정: **pass / pass** ([latest_codex_review.md](../../reports/refactor/latest_codex_review.md))
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *매핑* 문서 — 실제 코드 / 폴더 / 파일 생성하지 않는다.

### 0-1. 분류 기호

- **현재 기능**: 코드 + DB + UI 가 운영 환경에서 정상 동작.
- **부분 존재**: 흔적 일부 있지만 완성되지 않음 (예: 노쇼 — `status="canceled"` 만 있고 노쇼 별도 필드 부재).
- **후속 검토**: 현재 부재. 19-P 비-목표. 별도 세션에서 사용자 결정 후 도입.

### 0-2. 주석 카테고리 (실제 코드 이동 시 후속 세션이 추가할 주석 기준)

향후 19-P-4+ 단계에서 코드를 이동할 때 다음 카테고리로 주석을 추가한다 (본 문서에 위치만 표시):

| 카테고리 | 의미 | 적용 대상 |
|---|---|---|
| `# COMPAT:` | 기존 응답 키 / URL / 시그니처 후방호환 보존 사유 | wrapper 함수, 호환 alias, response dict 빌더 |
| `# SAFETY:` | PII 마스킹 / 운영 DB 차단 / 외부 API 차단 / API key 비노출 | pii.scan, audit, AiUsageLog, masking 함수 |
| `# NOTE:` | 업무 규칙 / 정책 / 의존성 (제거 시 회귀 발생) | 점심창, 휴무 차단, 반차, 완료체크, 카운트 정책 |
| `# RISK:` | 동시성 / TOCTOU / 외부 노드 호환 / 마이그레이션 의존 | 낙관적 락, ENTITY_MAP, indexer lock, restore atomic |
| `# TODO(19-P-N):` | 후속 세션 번호 + 제거 조건 | wrapper 일시 보유 (제거 후 본 라인 삭제) |

> 본 19-P-3 세션은 코드를 수정하지 않으므로 주석을 직접 작성하지 않는다. §9 / 모듈별 섹션의 "주석 필요" 항목을 후속 단계가 참조한다.

---

## 1. 모듈 매핑 인덱스

| # | 모듈 | M-ID (19-P-2 §9) | 분류 | 우선순위 (§31) |
|---|---|---|---|---|
| 1 | appointments | M-01 | 현재 기능 | 14 (마지막) |
| 2 | patients | M-02 | 현재 기능 | 7 |
| 3 | therapists | M-03 (staff 안) | 현재 기능 | 4 |
| 4 | doctors / medical_staff | M-03b (staff 안) + M-31~M-36 후속 | 부분 존재 + 후속 검토 | 4 (M-03b) / 후속 (M-31~M-36) |
| 5 | leaves | M-04 | 현재 기능 | 6 |
| 6 | treatments | M-05 | 현재 기능 | 5 |
| 7 | stats | M-07 + M-08 | 현재 기능 | 8 |
| 8 | sms | M-09 + M-29 | 현재 기능 | 9 |
| 9 | admin | M-10 + M-16 | 현재 기능 | 11 |
| 10 | backup | M-11 | 현재 기능 | 11 |
| 11 | ai | M-17 ~ M-24 | 현재 기능 | 12 |
| 12 | calendar / schedule_view | M-26 | 후속 검토 | post-19-P |
| 13 | availability | (M-01 하위 — appointments 안) | 부분 존재 | 14 (appointments 동시) |
| 14 | notes | (M-02 하위 — patients 안) + 통합 후속 (M-27) | 현재 기능 + 후속 검토 | 7 (M-02 동시) / 후속 (통합) |
| 15 | permissions / auth | (M-25 core/security) | 현재 기능 | 1 |
| 16 | settings | M-15 | 현재 기능 | 3 |
| 17 | audit / logs | M-14 | 현재 기능 | 2 |
| 18 | export_import | M-12 | 현재 기능 | 7 (patients 동시) |
| 19 | health / diagnostics | M-28 | 후속 검토 | post-19-P |
| 20 | core responses/errors | (M-25 core 하위) | 부분 존재 | 1 |
| 21 | feature_flags | M-30 | 부분 존재 | 13 |
| 22 | batch / jobs | (M-11 backup + M-23 indexer 하위) | 부분 존재 | (각 모듈 동시) |
| 23 | privacy / retention | (M-14 audit + M-23 ai/safety 하위) | 부분 존재 | (각 모듈 동시) |
| 24 | concurrency / locking | (M-01 + M-23 + M-11 하위) | 부분 존재 | (각 모듈 동시) |
| 25 | time_utils | (M-25 core 하위) | 부분 존재 | 1 |
| 26 | cancellations / no_show | (M-01 + M-07 — `status` 만) + 노쇼 후속 | 부분 존재 | (appointments 동시) |
| 27 | recurring_appointments | (없음) | 후속 검토 | post-19-P |
| 28 | resources | M-33 | 후속 검토 | post-19-P |
| 29 | printing / documents | (없음) | 후속 검토 | post-19-P |
| 30 | notifications | (없음) | 후속 검토 | post-19-P |

---

## 2. 모듈별 매핑

### 2-1. appointments

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [app/routers/api.py:1608-2057](../../app/routers/api.py:1608) (10 endpoint) + [api.py:64-107](../../app/routers/api.py:64) `_lunch_window`/`_check_lunch_block` + [api.py:1664-1679](../../app/routers/api.py:1664) `_check_version`/`_bump_version` + [api.py:1934-1953](../../app/routers/api.py:1934) `_bump_patient_count` |
| 현재 관련 API | `POST /api/appointments` `PUT /api/appointments/{aid}` `POST /api/appointments/{aid}/{assign,split-code,approve,revert-approve,cancel}` `DELETE /api/appointments/{aid}` `GET /api/appointments` |
| 현재 DB | `Appointment` ([models.py:134](../../app/models/models.py:134)) + `TreatmentAssignment` ([models.py:165](../../app/models/models.py:165)) |
| 현재 UI | [main.html](../../app/templates/main.html) 예약탭 (line 41-88, FullCalendar) + 예약 모달 |
| 목표 위치 | `app/modules/appointments/{router,service,repository,schemas,rules,availability}.py` |
| 분리 난이도 | **높음** |
| 위험도 | **높음** (다른 도메인 의존 多) |
| 선행 테스트 | 응답 키 contract + 점심창 + 낙관적 락 + 충돌 검사 + assign role 강제 + split-code TOCTOU |
| 응답 key 보존 | ✅ 필수 (현재 86 endpoint contract 미작성 — C-1 §22 19-P-1 — 분리 직전 보강 필수) |
| 프론트 호환 | FullCalendar event ID / version / status 필드 그대로. main.html JS 5747-5793 외 예약탭 다수 의존. |
| 관련 하네스 | `tests/test_appointment_rules.py` (~232줄) |
| Codex 검증 포인트 | 분리 후 응답 키 33+ 셋 보존 + 점심창/낙관적 락 회귀 0 + 의사 항목 handler role 강제 정합 |
| 비고 | **마지막 분리 권장** (§31 우선순위 14) — patients/therapists/treatments/leaves 모두 분리된 후 진입. wrapper 패턴으로 점진 위임. |
| 주석 필요 | `# COMPAT:` (응답 키 + version 필드) / `# NOTE:` (점심창, 충돌 검사) / `# RISK:` (낙관적 락 TOCTOU) / `# TODO(19-P-?):` (wrapper 제거 시점) |

### 2-2. patients

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [api.py:1280-1607](../../app/routers/api.py:1280) (10 endpoint) + [api.py:1213](../../app/routers/api.py:1213) `_patient_counts_dict` / [api.py:1235](../../app/routers/api.py:1235) `_patient_to_dict` / [api.py:1357](../../app/routers/api.py:1357) `_serialize_patients_bulk` / [api.py:1408](../../app/routers/api.py:1408) `_check_patient_duplicate` |
| 현재 관련 API | `GET /api/patients[/search/{pid}/last-appointments]` `POST /api/patients` `PUT /api/patients/{pid}` `PATCH /api/patients/{pid}/memo` `DELETE /api/patients/{pid}` `GET /api/patients/{pid}/{history,manual-history-summary}` |
| 현재 DB | `Patient` ([models.py:90](../../app/models/models.py:90)) + `PatientTreatmentCount` ([models.py:110](../../app/models/models.py:110)) |
| 현재 UI | main.html 환자탭 (line 89-109) + 환자 모달 |
| 목표 위치 | `app/modules/patients/{router,service,repository,schemas,notes_service}.py` |
| 분리 난이도 | **중간** |
| 위험도 | **중간** |
| 선행 테스트 | 응답 키 contract + 검색 인덱스 (이름/연락처/차트번호) + 중복 검사 + history 응답 |
| 응답 key 보존 | ✅ — 환자 dict / counts dict 키 보존 |
| 프론트 호환 | 환자탭 + 예약 모달 검색 자동완성 + counts 표시 |
| 관련 하네스 | (현재 별도 파일 부재 — `tests/test_employee_can_manual_contract.py` 일부) |
| Codex 검증 포인트 | 분리 후 PII 마스킹 정책 보존 + 메모 PATCH 분리 |
| 비고 | data-convert (M-12 export_import) 와 함께 분리 권장 (헬퍼 의존 多). |
| 주석 필요 | `# COMPAT:` (counts dict 키) / `# SAFETY:` (PII 비노출) / `# NOTE:` (중복 검사 정책) |

### 2-3. therapists

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** (Employee `role="therapist"` 분기) |
| 현재 관련 파일 | [api.py:1009-1079](../../app/routers/api.py:1009) (직원 CRUD) + [api.py:1175-1208](../../app/routers/api.py:1175) (`/api/therapists`, `/api/therapist-leaves` alias) + [api.py:169-178](../../app/routers/api.py:169) `_serialize_employee` |
| 현재 관련 API | `GET /api/employees` `POST /api/employees` `PUT /api/employees/{eid}` `DELETE /api/employees/{eid}` `POST /api/employees/reorder` + alias `GET /api/therapists` |
| 현재 DB | `Employee.role="therapist"` ([models.py:22](../../app/models/models.py:22)) — doctors 와 단일 테이블 공유 |
| 현재 UI | main.html 직원탭 (line 110-205) |
| 목표 위치 | `app/modules/staff/` (doctors + therapists 통합) — `staff/router.py` + `staff/service.py` 안에서 role 분기 |
| 분리 난이도 | **낮음~중간** |
| 위험도 | **낮음~중간** |
| 선행 테스트 | 응답 키 contract + alias `therapist_id` 이중 키 보존 |
| 응답 key 보존 | ✅ — `/api/therapist-leaves` 응답이 `therapist_id`/`employee_id` 양쪽 모두 반환 ([api.py:1184-1199](../../app/routers/api.py:1184)) |
| 프론트 호환 | 프론트가 `therapist_id` / `employee_id` 양쪽 사용 — 분리 후에도 alias 응답 유지 필수 |
| 관련 하네스 | `tests/test_employee_*.py` (4 파일) |
| Codex 검증 포인트 | 단일 staff 모듈로 doctor + therapist 통합 시 role 분기 정합 |
| 비고 | doctors 와 함께 분리 (M-03 + M-03b). 별도 `modules/therapists/` 분리 안 함. |
| 주석 필요 | `# COMPAT:` (therapist alias 이중 키) / `# NOTE:` (role 분기 정책) |

### 2-4. doctors / medical_staff

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (Employee `role="doctor"` + Treatment `role="doctor"` 분기) + **후속 검토** (담당의/진료과/진료실/오더/처방/EMR) |
| 현재 관련 파일 | [api.py:153-156](../../app/routers/api.py:153) `_doctor_codes_set` + [api.py:1773-1775](../../app/routers/api.py:1773) assign role=doctor 강제 + [api.py:3464,3491-3527](../../app/routers/api.py:3464) `is_doctor_filter` (통계) + [api.py:4339,4362-4465](../../app/routers/api.py:4339) 엑셀 doctor suffix + [services/seed.py:97-117](../../app/services/seed.py:97) demo doctors 시드 (현재 비활성화) |
| 현재 관련 API | (전용 endpoint 부재. `GET /api/employees?role=doctor` + 통계 / 예약에서 분기 사용) |
| 현재 DB | `Employee.role="doctor"` + `Treatment.role="doctor"` (injection/cartilage). **부재**: `Patient.doctor_id`, `Doctor` 별도 테이블, `Department`, `Room`, `DoctorSchedule`, `Order`, `Prescription`. |
| 현재 UI | main.html 직원탭 + 통계탭 의사 필터 (확인 필요) |
| 목표 위치 | `app/modules/staff/doctors_service.py` (얇은 분기) — 19-P 안. 별도 `app/modules/doctors/` 신설은 **post-19-P** (M-31). |
| 분리 난이도 | **중간** (현재 분기) / **높음** (EMR 도입 시) |
| 위험도 | **중간** (현재 분기) / **높음** (EMR — 마이그레이션 + 응답 키 + UI 동반) |
| 선행 테스트 | role=doctor handler 강제 회귀 + 통계 의사 필터 회귀 + 엑셀 doctor suffix 회귀 |
| 응답 key 보존 | ✅ — 통계 응답에서 의사 필터 결과 키 보존 |
| 프론트 호환 | 통계탭 의사 필터 (확인 필요) |
| 관련 하네스 | (전용 부재 — 후속 보강) |
| Codex 검증 포인트 | 의사 EMR 후속 (M-31~M-35) 이 *현재 부재* 로 분류되었는지 + AI 가 의사 정보 임의 생성 금지 정책 (M-36) 명시 |
| 비고 | EMR 연동 (담당의/진료과/진료실/오더/처방/비트U차트) 모두 19-P 비-목표. M-31~M-35 후속 검토. |
| 주석 필요 | `# NOTE:` (role=doctor 분기 정책) / `# RISK:` (handler role 강제 — 의사 항목 배정 시) / `# SAFETY:` (AI 가 의사 정보 임의 생성 금지) |

### 2-5. leaves

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** (full / annual / monthly) + **부분 존재** (오전반차 / 오후반차 = `leave_type` 값으로만 구분) |
| 현재 관련 파일 | [api.py:1082-1170](../../app/routers/api.py:1082) (4 endpoint) + [api.py:1098-1118](../../app/routers/api.py:1098) `_upsert_employee_leave_core` (단일 진실원천) + [api.py:1184-1208](../../app/routers/api.py:1184) (`/api/therapist-leaves` alias) + [services/ai/action_leave.py](../../app/services/ai/action_leave.py) (917줄, AI 자연어 휴무) |
| 현재 관련 API | `GET/POST /api/employee-leaves` `DELETE /api/employee-leaves/{lid}` `POST /api/employee-leaves/bulk-set` + alias `GET /api/therapist-leaves` `POST /api/therapist-leaves/bulk-set` + AI `POST /api/ai/action/{parse,preview,execute}` |
| 현재 DB | `EmployeeLeave` ([models.py:43](../../app/models/models.py:43)) — `(employee_id, leave_date)` UNIQUE (m011) + `leave_kind` (annual/monthly, m009) + `leave_type` (full / 반차값 — **확인 필요**) |
| 현재 UI | main.html 직원탭 휴무 표시 + 휴무 등록 모달 |
| 목표 위치 | `app/modules/leaves/{router,service,repository,schemas,rules}.py` |
| 분리 난이도 | **중간~높음** (AI 자연어 휴무와 결합) |
| 위험도 | **높음** (AI action_leave HMAC + TOCTOU 정책 보존 필수) |
| 선행 테스트 | UNIQUE 회귀 + AI action_leave 통과 + alias `therapist_id` 보존 |
| 응답 key 보존 | ✅ — `therapist_id`/`employee_id` 이중 키 |
| 프론트 호환 | 직원탭 휴무 표시 + 예약 모달의 휴무자 차단 |
| 관련 하네스 | `tests/test_employee_leave_unique.py` (157줄), `test_employee_leave_kind.py` (154줄), `test_therapist_leave.py` (122줄), `test_ai_action_leave.py` (1232줄) |
| Codex 검증 포인트 | `_upsert_employee_leave_core` 시그니처 보존 (AI action_leave 도 호출) |
| 비고 | **`_upsert_employee_leave_core` 는 단일 진실원천** — 분리 후에도 leaves.service 가 노출, AI 가 호출 |
| 주석 필요 | `# COMPAT:` (alias 이중 키) / `# NOTE:` (`leave_type` full vs 반차 정책) / `# RISK:` (AI action_leave 가 같은 헬퍼 호출 — 시그니처 변경 금지) / `# SAFETY:` (HMAC 토큰 + TOCTOU 재조회) |

### 2-6. treatments

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** (시드 5개: injection / cartilage / eswt / manual30 / manual60) |
| 현재 관련 파일 | [api.py:858-1008](../../app/routers/api.py:858) (5 endpoint) + [api.py:148-168](../../app/routers/api.py:148) (`_doctor_codes_set` 등 5개 분류 헬퍼) + [api.py:767-815](../../app/routers/api.py:767) `_serialize_treatment` / `_normalize_incentive` / `_build_treatment_meta` + [models/constants.py:14](../../app/models/constants.py:14) `SEED_TREATMENTS` + [services/seed.py:23](../../app/services/seed.py:23) `_seed_treatments` |
| 현재 관련 API | `GET /api/treatments` `POST /api/treatments` `PUT /api/treatments/{tid}` `DELETE /api/treatments/{tid}` `GET /api/treatments/{tid}/references` `GET /api/treatment-meta` |
| 현재 DB | `Treatment` ([models.py:58](../../app/models/models.py:58)) — `count_increment` (manual60=1 보존) + `price` + `incentive_pct/amount` (m005) |
| 현재 UI | main.html 관리자탭 치료항목 관리 |
| 목표 위치 | `app/modules/treatments/{router,service,repository,schemas,completion_rules}.py` |
| 분리 난이도 | **낮음~중간** |
| 위험도 | **중간~높음** (manual60=1 정책 / approve done_count 증감 정책 — CLAUDE.md 명시) |
| 선행 테스트 | count_increment 정책 + price/incentive 검증 |
| 응답 key 보존 | ✅ — `/api/treatment-meta` 의 `doctor_treatments` / `manual_codes` / `eswt_code` 키 |
| 프론트 호환 | 관리자탭 치료항목 + 예약 모달 항목 선택 + 통계탭 분류 |
| 관련 하네스 | (현재 별도 파일 부재 — `test_stats_counts.py` 일부 의존) |
| Codex 검증 포인트 | manual60 `count_increment=1` 절대 보존 (CLAUDE.md 절대 금지) |
| 비고 | completion_rules.py 안에 `_bump_patient_count` 이동 — approve / revert 시 done_count 증감 |
| 주석 필요 | `# NOTE:` (manual60=1 정책 — CLAUDE.md 절대 금지) / `# RISK:` (count_increment 변경 시 통계 회귀) / `# COMPAT:` (treatment-meta 응답 키) |

### 2-7. stats

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [api.py:3450-4332](../../app/routers/api.py:3450) (8 GET) + [api.py:3883-3942](../../app/routers/api.py:3883) (manual-counts upsert) + [api.py:4333-5127](../../app/routers/api.py:4333) (엑셀 export 2개) + [api.py:3732-3757](../../app/routers/api.py:3732) `_get_manual_treatment_rows` / `_get_manual_therapy_codes` + [api.py:3944-3982](../../app/routers/api.py:3944) `_resolve_stats_range` |
| 현재 관련 API | `GET /api/stats/{by-therapist,manual-by-therapist,aggregate,daily-by-therapist,summary,by-hour,by-weekday,by-treatment,daily}` (8개) + `POST /api/manual-counts` + `GET /api/export/{manual-schedule,stats}.xlsx` |
| 현재 DB | `ManualCount` ([models.py:216](../../app/models/models.py:216)) + `Appointment` 집계 |
| 현재 UI | main.html 통계탭 (월별/주별/일별 차트 + 엑셀 다운로드) |
| 목표 위치 | `app/modules/stats/{router,service,repository,schemas,aggregators}.py` (+ 엑셀 export 는 `modules/export_import/`) |
| 분리 난이도 | **높음** (헬퍼 의존성 그래프) |
| 위험도 | **중간~높음** |
| 선행 테스트 | 8 endpoint 응답 키 contract + 의사 필터 / manual_all 분기 + manual60=1 카운트 정합 |
| 응답 key 보존 | ✅ (현재 contract 미작성 — C-7 19-P-1 §22 — 분리 직전 보강) |
| 프론트 호환 | 통계탭 다수 의존 |
| 관련 하네스 | `tests/test_stats_counts.py` (162줄) |
| Codex 검증 포인트 | `_doctor_codes_set` / `_get_manual_treatment_rows` 가 stats / appointments / sms 동시 의존 → aggregators 단일 진실원천 분리 |
| 비고 | manual-counts (M-08) 는 stats.service 안에 흡수. 엑셀 export 는 export_import 로 분리. |
| 주석 필요 | `# NOTE:` (manual_all / doctor 분기 정책) / `# COMPAT:` (응답 키 8개 endpoint) / `# RISK:` (헬퍼 분리 시 회귀) |

### 2-8. sms

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [api.py:2927-3449](../../app/routers/api.py:2927) (8 endpoint) + [api.py:3115-3220](../../app/routers/api.py:3115) (전화/마스킹 헬퍼 5개) + [api.py:3225](../../app/routers/api.py:3225) `sms_send` (외부 munjanara API inline) + [services/ai/sms_draft.py](../../app/services/ai/sms_draft.py) (469줄, AI 초안) + [services/ai/validators.py](../../app/services/ai/validators.py) (285줄) |
| 현재 관련 API | `GET/POST /api/sms/setting` `GET /api/sms/tomorrow-targets` `GET/POST/PUT/DELETE /api/sms/templates*` `POST /api/sms/send` + AI `POST /api/ai/sms/{validate,draft}` |
| 현재 DB | `SmsSetting` ([models.py:236](../../app/models/models.py:236)) + `SmsLog` ([models.py:252](../../app/models/models.py:252)) + `SmsTemplate` ([models.py:263](../../app/models/models.py:263)) |
| 현재 UI | main.html 문자탭 (line 206-329) |
| 목표 위치 | `app/modules/sms/{router,service,templates,provider,schemas}.py` (provider = 외부 munjanara client 분리) |
| 분리 난이도 | **높음** |
| 위험도 | **높음** (외부 API 호출 + munjanara_key 마스킹 + 발송 비용) |
| 선행 테스트 | 발송 결과 contract + munjanara_key 마스킹 회귀 + sms_send 응답 디코딩 |
| 응답 key 보존 | ✅ — 발송 결과 / 템플릿 / setting 응답 키 (현재 contract 미작성 — C-2 19-P-1 §22) |
| 프론트 호환 | 문자탭 다수 의존 + 발송 후 결과 표시 |
| 관련 하네스 | `test_ai_sms_validate.py` `test_ai_sms_draft.py` `test_ai_sms_draft_hallucination.py` `test_sms_secret_masking.py` |
| Codex 검증 포인트 | provider.py 분리 후 외부 API timeout / 응답 디코딩 / 코드 매핑 정합 |
| 비고 | sms.provider (M-29) 는 외부 munjanara HTTP 호출 — 별도 파일로 분리. AI sms_draft / validators 는 modules/ai/ 로. |
| 주석 필요 | `# SAFETY:` (munjanara_key 마스킹) / `# RISK:` (외부 API 비용 + 발송 결과 디코딩) / `# COMPAT:` (응답 키) / `# NOTE:` (대상자 추출 정책) |

### 2-9. admin

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [api.py:224-269](../../app/routers/api.py:224) (`/api/admin/*` 4개) + [api.py:271-668](../../app/routers/api.py:271) (`/api/about/*` 5개 + `/api/config/*` 4개) + [services/auth.py](../../app/services/auth.py) (119줄, PBKDF2 + 세션) + [api.py:34-61](../../app/routers/api.py:34) `require_admin` / `require_admin_or_sync_token` |
| 현재 관련 API | `GET /api/admin/status` `POST /api/admin/{login,logout,change-password}` `GET /api/about` `POST /api/about/{check-update,download-update,apply-update}` `GET /api/about/update-log` `GET/POST /api/config[/sync-secret/regenerate-sync-secret]` `POST /api/mode` `GET/POST /api/system-settings` `GET /api/audit-logs` |
| 현재 DB | (config.json) + `SystemSetting` (M-15 settings) + `AuditLog` (M-14 audit) |
| 현재 UI | main.html 관리자탭 (line 377+) |
| 목표 위치 | `app/modules/admin/{router,service,schemas}.py` + 인증은 `core/security.py` (M-25) |
| 분리 난이도 | **중간** |
| 위험도 | **높음** (인증 / 자동 업데이트 / config) |
| 선행 테스트 | 로그인 5회 잠금 + 세션 TTL + 비번 변경 + check-update / apply-update 회귀 |
| 응답 key 보존 | ✅ |
| 프론트 호환 | 관리자탭 다수 의존 + about 알림 |
| 관련 하네스 | `tests/test_admin_auth_required.py` (282줄) + `test_admin_ui_smoke.py` (228줄) |
| Codex 검증 포인트 | 자동 업데이트 (about/check/download/apply) + updater.bat post-build 정합 |
| 비고 | core/security 와 분리 — admin.service 는 비즈니스 로직만, 인증 구현체는 core. |
| 주석 필요 | `# SAFETY:` (PBKDF2 / 5회 잠금 / 세션 TTL) / `# RISK:` (apply-update 가 PyInstaller 폴더 교체) / `# COMPAT:` (응답 키) |

### 2-10. backup

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [services/backup.py](../../app/services/backup.py) (180줄) + [api.py:2159-2906](../../app/routers/api.py:2159) (8 endpoint, 단 data-convert 는 export_import) + [main.py:22](../../app/main.py:22) `start_auto_backup()` |
| 현재 관련 API | `GET /api/backup` `POST /api/restore` `GET /api/backup/{list,dir}` `POST /api/backup/{now,restore-latest,restore-by-name}` |
| 현재 DB | (backups/*.db 파일) — DB 모델 없음. `SystemSetting.auto_backup_*` 가 정책. |
| 현재 UI | main.html 관리자탭 백업 섹션 |
| 목표 위치 | `app/modules/backup/{router,service,schemas}.py` |
| 분리 난이도 | **중간** |
| 위험도 | **높음** (복원 시 운영 DB 교체 — engine.dispose() + atomic rename) |
| 선행 테스트 | restore_by_name 정합 + integrity_check + audit 폴백 + 타이머 스레드 격리 (conftest 무력화) |
| 응답 key 보존 | ✅ |
| 프론트 호환 | 관리자탭 백업 목록 + 복원 버튼 |
| 관련 하네스 | `tests/test_db_restore_safety.py` (151줄) |
| Codex 검증 포인트 | 타이머 스레드 분리 후에도 conftest 무력화 가능 |
| 비고 | `start_auto_backup()` 호출은 `app/main.py` 가 그대로 유지. 타이머 구현은 `modules/backup/service.py` 가 보유. |
| 주석 필요 | `# SAFETY:` (운영 DB 교체 — engine.dispose() 필수) / `# RISK:` (atomic rename Windows 정책) / `# NOTE:` (타이머 스레드 — 테스트는 람다 교체) |

### 2-11. ai

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** (18-0~18-7 결과) |
| 현재 관련 파일 | [routers/ai.py](../../app/routers/ai.py) (929줄, 13 endpoint) + [services/ai/{provider,openai_client,anthropic_client,pii,prompts,validators,ai_logging,sms_draft,manual_qa,action_leave,date_resolver,health}.py](../../app/services/ai/) (12 파일) + [services/ai/{rag,knowledge,vector}/](../../app/services/ai/) (3 패키지 17 파일) |
| 현재 관련 API | `GET /api/ai/{health,health/public,status,providers,settings}` `PUT /api/ai/settings` `POST /api/ai/sms/{validate,draft}` `POST /api/ai/manual/{search,ask}` `POST /api/ai/action/{parse,preview,execute}` |
| 현재 DB | `AiSetting` ([models.py:280](../../app/models/models.py:280)) + `AiUsageLog` ([models.py:304](../../app/models/models.py:304)) + `KnowledgeChunk` (m012) + `KnowledgeIndexRun` (m012) + `KnowledgeVector` (m013) |
| 현재 UI | main.html AI 도우미 탭 (line 330-376, 5747-5793 응답 키 5개 의존) |
| 목표 위치 | `app/modules/ai/{router,manual_qa,sms_draft,provider,health,logging,rag/,knowledge/,vector/,safety/,commands/}` |
| 분리 난이도 | **중간** (위치 이동만, 내부 구조 18-1~18-6 그대로) |
| 위험도 | **중간~높음** (응답 키 33+ + local-first + manual_qa wrapper 시그니처) |
| 선행 테스트 | 응답 키 33+ contract + local_only 단언 (`len(provider.calls)==0`) + RAG/Vector/Hybrid 회귀 |
| 응답 key 보존 | ✅ 절대 — manual/search 3 + manual/ask 9 + health 9 + health/public 4 + status 9 + sources 3 |
| 프론트 호환 | AI 도우미 탭 5747-5793 사용 5키 (`not_found`/`answer`/`confidence`/`sources[].title,path`) 절대 보존 |
| 관련 하네스 | 18-0~18-7 결과 13 파일 (4194줄, 293 tests) + 기존 8 파일 (~98 tests) |
| Codex 검증 포인트 | local-first 보존 + manual_qa wrapper 시그니처 (`provider_override=`) + LOW_SCORE_THRESHOLD=2 + HIGH/LOW=0.7/0.3 |
| 비고 | action_leave (917줄) → `commands/action_leave.py`. health (563줄) → `health.py` 그대로. rag/knowledge/vector 패키지 위치만 이동. |
| 주석 필요 | `# COMPAT:` (응답 키 33+ + manual_qa wrapper) / `# SAFETY:` (PII / API key / local_only) / `# NOTE:` (LOW_SCORE_THRESHOLD=2 등 임계치) / `# RISK:` (vector lazy import + ENTITY_MAP 변경 금지) |

### 2-12. calendar / schedule_view

| 항목 | 값 |
|---|---|
| 분류 | **후속 검토** (post-19-P, M-26) |
| 현재 관련 파일 | (서버 사이드 view-model 부재. main.html 안 FullCalendar JS 만 존재) |
| 현재 관련 API | (없음 — `/api/appointments` 의 응답을 클라이언트가 직접 렌더) |
| 현재 DB | (없음 — 클라이언트 렌더) |
| 현재 UI | main.html 예약탭 (line 41-88) FullCalendar + 미니캘린더 + 시간대 표시 + 휴무자 표시 |
| 목표 위치 | (post-19-P) `app/modules/calendar/{service,schemas,view_models}.py` |
| 분리 난이도 | **높음** (UI 분리 동반) |
| 위험도 | **높음** |
| 선행 테스트 | (신규 — view-model 응답 키 contract) |
| 응답 key 보존 | (신규 endpoint 추가만 — 기존 미영향) |
| 프론트 호환 | main.html FullCalendar 의존 多 (예약 색상 / 휴무 표시 / 의사 필터) |
| 관련 하네스 | (없음) |
| Codex 검증 포인트 | 19-P 비-목표로 분류되었는지 |
| 비고 | UI 분리 자체가 19-P 비-목표. view-model 만 서버 사이드로 빼는 것도 후속. |
| 주석 필요 | (해당 없음 — 본 19-P 진행 안 함) |

### 2-13. availability

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (점심창만 명시 헬퍼, 그 외 인라인) |
| 현재 관련 파일 | [api.py:64-107](../../app/routers/api.py:64) `_lunch_window` / `_check_lunch_block` + [api.py:1621-1746](../../app/routers/api.py:1621) `create_appointment` 안 인라인 충돌 검사 + 휴무 차단 (확인 필요) |
| 현재 관련 API | (전용 endpoint 부재 — 예약 생성/수정 안에서 호출) |
| 현재 DB | `Appointment` (start_at/duration_min) + `EmployeeLeave` (휴무 차단) + `SystemSetting` (점심창) |
| 현재 UI | main.html 예약 모달 (가능 시간 자동 계산 — 클라이언트 측) |
| 목표 위치 | `app/modules/appointments/availability.py` (M-01 안 — 별도 파일) |
| 분리 난이도 | **중간~높음** (현재 인라인 — 추출 필요) |
| 위험도 | **높음** (예약 충돌 / 우회 방지) |
| 선행 테스트 | 점심창 + 휴무 차단 + 충돌 검사 + 오전반차/오후반차 차단 (확인 필요 — `leave_type` 값 매핑 검증) |
| 응답 key 보존 | (응답 자체보다 차단 일관성이 중요) |
| 프론트 호환 | 클라이언트 자동 계산과 백엔드 검증 일치 (DevTools/manual POST 우회 방지) |
| 관련 하네스 | `tests/test_appointment_rules.py` (~232줄) — 일부 |
| Codex 검증 포인트 | 오전/오후 반차 차단이 실제 코드에 있는지 (확인 필요) — 현재 `leave_type="full"` 만 명확. 반차 분기 코드 위치는 별도 grep 필요. |
| 비고 | appointments 와 동시 분리. 19-P 안. |
| 주석 필요 | `# NOTE:` (점심창 정책 / 충돌 검사 / 휴무 차단) / `# RISK:` (DevTools/manual POST 우회 — 백엔드 강제) |

### 2-14. notes

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** (단일 메모 필드) + **후속 검토** (지속/당일 메모 통합) |
| 현재 관련 파일 | [api.py:1444-1455](../../app/routers/api.py:1444) `update_patient_memo` (PATCH) + 환자 모달 메모 필드 + `Appointment.memo` 필드 (`Appointment.memo` 는 예약별 메모) |
| 현재 관련 API | `PATCH /api/patients/{pid}/memo` + `Appointment.memo` 는 PUT/POST 응답에 포함 |
| 현재 DB | `Patient.memo` (Text) + `Appointment.memo` (Text) — 두 컬럼 따로 존재 |
| 현재 UI | main.html 환자탭 메모 필드 + 예약 모달 메모 필드 |
| 목표 위치 | `app/modules/patients/notes_service.py` (현재) — 19-P 안. 통합 `app/modules/notes/` 는 **post-19-P** (M-27). |
| 분리 난이도 | **낮음** (현재) / **중간** (통합 시) |
| 위험도 | **낮음~중간** |
| 선행 테스트 | 메모 PATCH 응답 + PII 마스킹 정책 |
| 응답 key 보존 | ✅ |
| 프론트 호환 | 환자탭 + 예약 모달 |
| 관련 하네스 | (전용 부재) |
| Codex 검증 포인트 | "지속 메모 vs 당일 메모" 정책 미결정 — 후속 분류 |
| 비고 | 본 19-P 에서는 patients 모듈 안에 두고, 통합은 post-19-P. |
| 주석 필요 | `# SAFETY:` (메모는 PII 포함 가능 — AI 응답 / 로그 마스킹 대상) / `# NOTE:` (Patient.memo vs Appointment.memo 의미 차이) |

### 2-15. permissions / auth

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** (admin 단일 등급) + **부분 존재** (직원/관리자 분리는 부재) |
| 현재 관련 파일 | [services/auth.py](../../app/services/auth.py) (119줄) + [api.py:34-61](../../app/routers/api.py:34) `require_admin` / `require_admin_or_sync_token` + [routers/ai.py:51](../../app/routers/ai.py:51) AI 라우터 별도 정의 |
| 현재 관련 API | (모든 admin 전용 endpoint 가 의존) |
| 현재 DB | (config.json `admin_password_hash` + 인메모리 세션) |
| 현재 UI | main.html 로그인 모달 + admin-tab 표시 분기 |
| 목표 위치 | `app/core/security.py` (M-25) — 인증 / 비번 / 세션 |
| 분리 난이도 | **낮음** (단일 모듈 이동) |
| 위험도 | **높음** (모든 admin endpoint 가 의존 — import 경로 변경 多) |
| 선행 테스트 | 로그인 5회 잠금 + 세션 TTL + 비번 변경 |
| 응답 key 보존 | ✅ |
| 프론트 호환 | login / change-password 응답 |
| 관련 하네스 | `tests/test_admin_auth_required.py` (282줄) |
| Codex 검증 포인트 | core/security 가 단일 진실원천 + 라우터 의 require_admin 모두 import |
| 비고 | 직원/관리자 다중 등급은 후속 검토 (현재는 admin or guest). |
| 주석 필요 | `# SAFETY:` (PBKDF2 / 세션 / 5회 잠금 / DEFAULT_PASSWORD) |

### 2-16. settings

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [api.py:2058-2096](../../app/routers/api.py:2058) (system-settings GET/POST) + [api.py:669-743](../../app/routers/api.py:669) (config GET/POST) + [routers/ai.py:243-346](../../app/routers/ai.py:243) (AI settings 별도) + [services/seed.py:42-62](../../app/services/seed.py:42) `_seed_system_setting` / `_seed_sms_setting` |
| 현재 관련 API | `GET/POST /api/system-settings` `GET/POST /api/config[/sync-secret]` `GET/PUT /api/ai/settings` `GET/POST /api/sms/setting` |
| 현재 DB | `SystemSetting` ([models.py:182](../../app/models/models.py:182)) + `SmsSetting` + `AiSetting` + (config.json) |
| 현재 UI | main.html 관리자탭 시스템 설정 + 문자탭 SMS 설정 + AI 설정 모달 |
| 목표 위치 | `app/modules/settings/{service,repository,schemas}.py` (SystemSetting 만 통합) — SmsSetting / AiSetting 은 각 모듈 안 유지 |
| 분리 난이도 | **낮음** |
| 위험도 | **낮음~중간** |
| 선행 테스트 | system-settings 응답 + manual_slot_limit + auto_backup_* 정책 |
| 응답 key 보존 | ✅ |
| 프론트 호환 | 관리자탭 |
| 관련 하네스 | (전용 부재) |
| Codex 검증 포인트 | AiSetting 갱신은 modules/ai/router.py 가 보유 (T-1 19-P-2) — settings 모듈은 SystemSetting 만 |
| 비고 | feature_flags (M-30) 와 분리. SystemSetting / SmsSetting / AiSetting 통합 read-only 인터페이스 가능. |
| 주석 필요 | `# COMPAT:` (응답 키) / `# NOTE:` (auto_backup_keep_count 정책) |

### 2-17. audit / logs

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** |
| 현재 관련 파일 | [api.py:110-127](../../app/routers/api.py:110) `audit()` / `_log()` (sync 위임) + [api.py:2907-2926](../../app/routers/api.py:2907) `list_audit_logs` + [services/ai/ai_logging.py](../../app/services/ai/ai_logging.py) (225줄, AI 전용) |
| 현재 관련 API | `GET /api/audit-logs` |
| 현재 DB | `AuditLog` ([models.py:194](../../app/models/models.py:194)) + `AiUsageLog` (m008 확장) |
| 현재 UI | main.html 관리자탭 감사 로그 (확인 필요) |
| 목표 위치 | `app/modules/audit/{service,repository,schemas}.py` (AuditLog 단일) — AI 로그는 `modules/ai/logging.py` 별도 |
| 분리 난이도 | **낮음** |
| 위험도 | **중간** (모든 CUD 가 호출) |
| 선행 테스트 | audit() 시그니처 보존 + 모든 CUD 호출지에서 정상 insert |
| 응답 key 보존 | ✅ |
| 프론트 호환 | 관리자탭 audit 표시 |
| 관련 하네스 | (전용 부재) |
| Codex 검증 포인트 | audit() 가 모든 모듈에서 import 가능 + PII 원문 저장 금지 정책 보존 |
| 비고 | M-14 — 우선순위 2 (가장 안전한 분리). |
| 주석 필요 | `# SAFETY:` (PII 원문 저장 금지 — detail 500자 cap) / `# NOTE:` (모든 CUD 호출 — 시그니처 변경 금지) |

### 2-18. export_import

| 항목 | 값 |
|---|---|
| 분류 | **현재 기능** (엑셀 export + 환자 엑셀 import) |
| 현재 관련 파일 | [api.py:4333-5127](../../app/routers/api.py:4333) (엑셀 export 2개, ~800줄) + [api.py:2258-2855](../../app/routers/api.py:2258) (data-convert preview/apply, `_dc_*` 헬퍼 ~600줄) |
| 현재 관련 API | `GET /api/export/{manual-schedule,stats}.xlsx` + `POST /api/data-convert/{preview,apply}` |
| 현재 DB | (read-only 집계) + `Patient` (import 시 write) |
| 현재 UI | main.html 통계탭 엑셀 다운로드 + 환자탭 데이터 변환 모달 |
| 목표 위치 | `app/modules/export_import/{service,schemas}.py` (+ stats.export 와 patients.import 분리 가능) |
| 분리 난이도 | **중간** (~1400줄) |
| 위험도 | **중간** |
| 선행 테스트 | 엑셀 export 응답 + import preview/apply 응답 + 중복 검사 |
| 응답 key 보존 | ✅ (현재 contract 미작성 — C-6 19-P-1 §22) |
| 프론트 호환 | 통계탭 다운로드 + 환자탭 변환 모달 |
| 관련 하네스 | (전용 부재) |
| Codex 검증 포인트 | _dc_* 헬퍼 ~400줄 단일 모듈로 통째 이동 vs 세분화 (T-11 19-P-2) |
| 비고 | patients 와 함께 분리 (M-12). 향후 비트U차트 import/CSV 등은 후속. |
| 주석 필요 | `# COMPAT:` (응답 키) / `# NOTE:` (_dc_* 정규화 정책 — gender/SSN/phone) / `# RISK:` (대량 import 시 트랜잭션) |

### 2-19. health / diagnostics

| 항목 | 값 |
|---|---|
| 분류 | **후속 검토** (post-19-P, M-28) — `/api/ai/health` 는 별도 도메인 |
| 현재 관련 파일 | (전용 부재 — `/api/admin/status` 가 인증 상태만) |
| 현재 관련 API | (없음 — 추가 후보) |
| 현재 DB | (없음) |
| 현재 UI | main.html 상단 모드/노드 ID 표시 (line 9-30) — 부분 |
| 목표 위치 | (post-19-P) `app/modules/health/{router,service,diagnostics}.py` |
| 분리 난이도 | **낮음~중간** (신규) |
| 위험도 | **낮음** |
| 선행 테스트 | (신규) |
| 응답 key 보존 | (신규 추가만) |
| 프론트 호환 | (신규 추가) |
| 관련 하네스 | (없음) |
| Codex 검증 포인트 | 후속 검토 분류 적절성 — 현재 부재 명시 |
| 비고 | `/api/health` 신설 결정 필요 (사용자). `/api/ai/health` 는 modules/ai/ 가 그대로 보유. |
| 주석 필요 | (해당 없음 — 본 19-P 미진행) |

### 2-20. core responses / errors

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (FastAPI 기본 + HTTPException 직접 raise — 표준화 부재) |
| 현재 관련 파일 | [api.py](../../app/routers/api.py) 전반 + [routers/ai.py](../../app/routers/ai.py) — `HTTPException(status, detail)` 패턴 다수 + 응답 dict 직접 빌드 |
| 현재 관련 API | (모든 endpoint) |
| 현재 DB | (없음) |
| 현재 UI | main.html JS 가 `j.detail` 표시 + status code 분기 |
| 목표 위치 | `app/core/{responses,errors}.py` (M-25 하위) |
| 분리 난이도 | **중간** (모든 모듈에 영향) |
| 위험도 | **중간** (응답 형식 통일 시 후방호환 깨질 수 있음) |
| 선행 테스트 | HTTPException detail 형식 + status code 매핑 |
| 응답 key 보존 | ✅ — 표준화하더라도 *현재 응답 dict 키 절대 보존* |
| 프론트 호환 | `j.detail` 사용 패턴 그대로 + 추가 키만 가능 |
| 관련 하네스 | 33+ 응답 키 contract 테스트 (이미 존재) |
| Codex 검증 포인트 | 표준 envelope 도입 시 기존 응답 dict 키 보존 — 추가만 |
| 비고 | core 단계 우선순위 1 (M-25). 단, 표준 envelope 강제 도입은 위험 — 옵션 사용 권장. |
| 주석 필요 | `# COMPAT:` (응답 dict 키 보존 — 추가만 허용) / `# NOTE:` (HTTPException detail 한국어 텍스트 그대로) |

### 2-21. feature_flags

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (분산 — `AiSetting.enabled` + 환경 변수 + ai_mode 파생) |
| 현재 관련 파일 | [services/ai/health.py](../../app/services/ai/health.py) (ai_mode/search_mode 파생) + [models.py:280-302](../../app/models/models.py:280) `AiSetting` + (환경 변수 `AI_RAG_ENABLED` / `AI_RAG_VECTOR_ENABLED` / `AI_RAG_HYBRID_ENABLED` — 확인 필요) |
| 현재 관련 API | `/api/ai/status` (ai_mode/search_mode 응답) |
| 현재 DB | `AiSetting` |
| 현재 UI | AI 설정 모달 + 관리자 status 표시 |
| 목표 위치 | `app/core/feature_flags.py` (M-30) |
| 분리 난이도 | **중간** |
| 위험도 | **낮음~중간** |
| 선행 테스트 | ai_mode (local_only/local_first/ai_assist) + search_mode 파생 회귀 |
| 응답 key 보존 | ✅ — `/api/ai/status` 의 ai_mode/search_mode 키 |
| 프론트 호환 | (소규모 — AI 도우미 탭만) |
| 관련 하네스 | `tests/test_ai_assist_mode.py` (355줄) + `test_local_only_mode.py` (72줄) |
| Codex 검증 포인트 | 단일 진실원천 — 환경 변수 + DB 둘 중 우선순위 명시 (T-8 19-P-2) |
| 비고 | core 분리 후 ai 모듈에서 import. |
| 주석 필요 | `# NOTE:` (ai_mode 파생 정책) / `# COMPAT:` (응답 키) |

### 2-22. batch / jobs

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (자동 백업 타이머 + reindex lock — 통합 스케줄러 부재) |
| 현재 관련 파일 | [services/backup.py:143-181](../../app/services/backup.py:143) `_timer_loop` / `start_auto_backup` + [services/sync.py](../../app/services/sync.py) sync 워커 + [services/ai/knowledge/indexer.py](../../app/services/ai/knowledge/indexer.py) reindex lock |
| 현재 관련 API | (전용 endpoint 부재 — 각 모듈 안에서 시작) |
| 현재 DB | (없음) |
| 현재 UI | (없음 — 백그라운드) |
| 목표 위치 | (각 모듈 하위 — `modules/backup/service.py`, `modules/ai/knowledge/indexer.py`, `modules/sync/`) |
| 분리 난이도 | **낮음** (각 모듈 따라감) |
| 위험도 | **중간** (테스트 격리 — conftest 람다 교체) |
| 선행 테스트 | 타이머 / 워커 / lock 가 conftest 에서 정상 무력화 |
| 응답 key 보존 | (해당 없음) |
| 프론트 호환 | (해당 없음) |
| 관련 하네스 | `tests/test_graceful_shutdown.py` (85줄) |
| Codex 검증 포인트 | 통합 스케줄러는 후속 검토 — 본 19-P 비-목표 |
| 비고 | 각 모듈이 자체 lifecycle 관리 — 통합 스케줄러 도입은 별도 ADR. |
| 주석 필요 | `# RISK:` (백그라운드 스레드 — daemon=True + stop flag) / `# SAFETY:` (테스트는 람다 교체 — 약화 금지) |

### 2-23. privacy / retention

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (PII 마스킹 + sha256 해시 + 200자 cap) — 보존 정책 부재 |
| 현재 관련 파일 | [services/ai/pii.py](../../app/services/ai/pii.py) (127줄) + [services/ai/ai_logging.py](../../app/services/ai/ai_logging.py) + [services/ai/health.py:_safe_error_detail](../../app/services/ai/health.py) (200자 cap) + [api.py:3139-3160](../../app/routers/api.py:3139) `_mask_phone_for_log` / `_sms_sanitize` |
| 현재 관련 API | (간접 — 모든 응답에 적용) |
| 현재 DB | `AiUsageLog` (prompt_hash/response_hash 만 — 원문 미저장) |
| 현재 UI | (간접) |
| 목표 위치 | `app/modules/ai/safety/pii.py` + `app/modules/audit/` (보존 정책) |
| 분리 난이도 | **낮음** (현재 위치 이동만) |
| 위험도 | **높음** (정책 변경 시 PII 노출 위험) |
| 선행 테스트 | PII 마스킹 회귀 + 200자 cap + sha256 해시 |
| 응답 key 보존 | ✅ |
| 프론트 호환 | (간접) |
| 관련 하네스 | `test_ai_safety_harness.py` (153줄) + `test_ai_logging.py` (216줄) + `test_sms_secret_masking.py` (81줄) |
| Codex 검증 포인트 | AI 응답 / 로그 / SMS 발송 모두 PII 마스킹 일관 적용 |
| 비고 | 오래된 AI 로그 삭제 / 환자정보 비활성화 정책은 후속 검토. |
| 주석 필요 | `# SAFETY:` (PII 마스킹 / sha256 / 200자 cap / API key 마스킹) / `# NOTE:` (보존 정책 미정 — 후속) |

### 2-24. concurrency / locking

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (낙관적 락 + reindex lock + atomic rename — 통합 정책 부재) |
| 현재 관련 파일 | [api.py:1664-1679](../../app/routers/api.py:1664) `_check_version` / `_bump_version` (Appointment) + [services/ai/knowledge/indexer.py](../../app/services/ai/knowledge/indexer.py) reindex lock + [api.py:2168-2256](../../app/routers/api.py:2168) restore atomic rename + [services/sync.py](../../app/services/sync.py) sync 워커 락 |
| 현재 관련 API | (간접) |
| 현재 DB | `Appointment.version` 컬럼 + `KnowledgeIndexRun.status` |
| 현재 UI | 클라이언트 측 중복 클릭 방지 (확인 필요) + 버전 충돌 시 409 표시 |
| 목표 위치 | (각 모듈 하위 — appointments.rules / ai/knowledge/indexer / backup.service / sync) |
| 분리 난이도 | **낮음** (각 모듈 따라감) |
| 위험도 | **높음** (TOCTOU / 동시성 사고) |
| 선행 테스트 | 동시 예약 생성 충돌 + reindex lock + restore 중 다른 작업 차단 |
| 응답 key 보존 | ✅ — `version` 키 + 409 status |
| 프론트 호환 | 버전 충돌 응답 처리 (현재 main.html JS) |
| 관련 하네스 | `test_appointment_rules.py` + `test_ai_reindex_harness.py` (~691줄) + `test_db_restore_safety.py` (151줄) |
| Codex 검증 포인트 | 분리 후 락 정책 일관 — 통합 잠금은 후속 |
| 비고 | 통합 잠금 매니저는 후속 검토. |
| 주석 필요 | `# RISK:` (낙관적 락 / TOCTOU / atomic rename) / `# NOTE:` (reindex lock — 단일 인스턴스) |

### 2-25. time_utils

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (분산 — `datetime` 직접 사용 多, 점심창만 헬퍼) |
| 현재 관련 파일 | [api.py:64-107](../../app/routers/api.py:64) 점심창 + [api.py:3944-3982](../../app/routers/api.py:3944) `_resolve_stats_range` / `_date_list` + [services/ai/date_resolver.py](../../app/services/ai/date_resolver.py) (233줄, AI 자연어 날짜) + 다수 위치 `datetime.now()` |
| 현재 관련 API | (간접) |
| 현재 DB | (없음) |
| 현재 UI | (간접) |
| 목표 위치 | `app/core/time_utils.py` (M-25) |
| 분리 난이도 | **낮음~중간** (다수 호출지 변경) |
| 위험도 | **낮음~중간** |
| 선행 테스트 | 점심창 + 오전/오후 반차 + 이번달 / 내일 정합 |
| 응답 key 보존 | (해당 없음) |
| 프론트 호환 | (해당 없음) |
| 관련 하네스 | (각 모듈 회귀로 충분) |
| Codex 검증 포인트 | Asia/Seoul 명시 + tz-aware vs naive 일관 |
| 비고 | core 단계에서 점진 도입. AI date_resolver 는 modules/ai/ 그대로. |
| 주석 필요 | `# NOTE:` (Asia/Seoul 기준) / `# RISK:` (오전/오후 반차 정책 — `leave_type` 값 매핑) |

### 2-26. cancellations / no_show

| 항목 | 값 |
|---|---|
| 분류 | **부분 존재** (취소만 — `Appointment.status="canceled"`) — 노쇼는 **후속 검토** |
| 현재 관련 파일 | [api.py:2006-2023](../../app/routers/api.py:2006) `cancel_appointment` + [api.py:3486-3497](../../app/routers/api.py:3486) 통계 `canceled` 카운트 |
| 현재 관련 API | `POST /api/appointments/{aid}/cancel` (취소만) |
| 현재 DB | `Appointment.status` ∈ `reserved`/`approved`/`canceled` — **노쇼 별도 필드 부재** |
| 현재 UI | main.html 예약 모달 취소 버튼 + 통계탭 취소 카운트 |
| 목표 위치 | 취소 = `app/modules/appointments/` (M-01). 노쇼 = **post-19-P** (m014+ 컬럼 / 별도 status 값) |
| 분리 난이도 | **낮음** (취소만) / **높음** (노쇼 도입 시) |
| 위험도 | **중간** |
| 선행 테스트 | cancel 응답 + 통계 canceled 카운트 정합 |
| 응답 key 보존 | ✅ |
| 프론트 호환 | 통계탭 |
| 관련 하네스 | `test_appointment_rules.py` 일부 + `test_stats_counts.py` |
| Codex 검증 포인트 | 노쇼 도입 시 m014+ 마이그레이션 + 응답 키 추가 + UI 변경 동반 — 본 19-P 비-목표 |
| 비고 | 노쇼 통계는 사용자 결정 후 도입. 현재 "취소" 만 분리 가능. |
| 주석 필요 | `# NOTE:` (status 분기 — canceled / approved / reserved) / `# COMPAT:` (응답 키) |

### 2-27. recurring_appointments

| 항목 | 값 |
|---|---|
| 분류 | **후속 검토** (현재 부재) |
| 현재 관련 파일 | (없음) |
| 현재 관련 API | (없음) |
| 현재 DB | (없음) |
| 현재 UI | (없음) |
| 목표 위치 | (post-19-P) — 별도 ADR + DB 마이그레이션 + UI 동반 |
| 분리 난이도 | **(해당 없음)** |
| 위험도 | **(해당 없음)** |
| 선행 테스트 | (해당 없음) |
| 응답 key 보존 | (해당 없음) |
| 프론트 호환 | (해당 없음) |
| 관련 하네스 | (없음) |
| Codex 검증 포인트 | 현재 부재로 분류되었는지 |
| 비고 | 사용자 결정 필요 시 도입. 본 19-P 비-목표. |
| 주석 필요 | (해당 없음) |

### 2-28. resources

| 항목 | 값 |
|---|---|
| 분류 | **후속 검토** (post-19-P, M-33) — 진료실 / 장비 / 자원 |
| 현재 관련 파일 | (없음) |
| 현재 관련 API | (없음) |
| 현재 DB | (없음 — `Resource` 모델 부재) |
| 현재 UI | (없음) |
| 목표 위치 | (post-19-P) `app/modules/resources/` |
| 분리 난이도 | **(해당 없음)** |
| 위험도 | **(해당 없음)** |
| 선행 테스트 | (해당 없음) |
| 응답 key 보존 | (해당 없음) |
| 프론트 호환 | (해당 없음) |
| 관련 하네스 | (없음) |
| Codex 검증 포인트 | 현재 부재 분류 |
| 비고 | 의사 EMR 연동 (M-31~M-35) 과 함께 결정. |
| 주석 필요 | (해당 없음) |

### 2-29. printing / documents

| 항목 | 값 |
|---|---|
| 분류 | **후속 검토** (현재 부재) |
| 현재 관련 파일 | (없음 — 엑셀 export 는 별도 export_import) |
| 현재 관련 API | (없음) |
| 현재 DB | (없음) |
| 현재 UI | (없음 — 브라우저 인쇄만) |
| 목표 위치 | (post-19-P) |
| 분리 난이도 | **(해당 없음)** |
| 위험도 | **(해당 없음)** |
| 선행 테스트 | (해당 없음) |
| 응답 key 보존 | (해당 없음) |
| 프론트 호환 | (해당 없음) |
| 관련 하네스 | (없음) |
| Codex 검증 포인트 | 현재 부재 분류 |
| 비고 | 예약표 / 통계표 / 환자 안내문 출력 — 사용자 결정 필요. |
| 주석 필요 | (해당 없음) |

### 2-30. notifications

| 항목 | 값 |
|---|---|
| 분류 | **후속 검토** (현재 부재) |
| 현재 관련 파일 | (없음 — reindex 실패는 `KnowledgeIndexRun.errors` 텍스트로만 저장) |
| 현재 관련 API | (없음) |
| 현재 DB | (없음 — 알림 테이블 부재) |
| 현재 UI | (없음) |
| 목표 위치 | (post-19-P) |
| 분리 난이도 | **(해당 없음)** |
| 위험도 | **(해당 없음)** |
| 선행 테스트 | (해당 없음) |
| 응답 key 보존 | (해당 없음) |
| 프론트 호환 | (해당 없음) |
| 관련 하네스 | (없음) |
| Codex 검증 포인트 | 현재 부재 분류 |
| 비고 | 내부 알림 / reindex 실패 / 백업 실패 알림 — 사용자 결정 필요. |
| 주석 필요 | (해당 없음) |

---

## 31. 우선 분리하면 좋은 모듈

> 의존도 낮음 + 위험도 낮음 + 단일 책임 + 모든 모듈이 의존.

| 순서 | 모듈 | 사유 |
|---|---|---|
| 1 | **core** (M-25) — config / database / errors / responses / time_utils / security / feature_flags | 모든 modules 가 의존 — 가장 먼저. import 경로 변경만, 위험도 낮음. |
| 2 | **audit** (M-14) | 모든 CUD 가 호출하는 단순 함수. 가장 안전. |
| 3 | **settings** (M-15) | SystemSetting 단일 — 가장 단순. |
| 4 | **staff** (M-03 + M-03b) | 환자/예약 의존이 적은 도메인. |
| 5 | **treatments + completion_rules** (M-05 + M-06) | manual60=1 정책 보존 단위. |
| 6 | **leaves + ai/commands/action_leave** (M-04 + M-18) | `_upsert_employee_leave_core` 단일 진실원천 보존. AI action_leave 와 함께 분리. |
| 7 | **patients + export_import** (M-02 + M-12) | data-convert 분리 동시. |

## 32. 나중에 분리해야 할 모듈

> 다른 도메인 의존이 많거나 헬퍼 의존성 그래프가 큰 모듈.

| 순서 | 모듈 | 사유 |
|---|---|---|
| 8 | **stats** (M-07 + M-08) | `_get_manual_treatment_rows` / `_doctor_codes_set` 헬퍼 의존성 정리 후. |
| 9 | **sms + sms.provider** (M-09 + M-29) | 외부 API 호출 + 발송 비용. |
| 10 | **ai sms_draft / validators** (M-21) | sms 와 함께. |
| 11 | **backup + admin/about-update** (M-11 + M-16) | 자동 업데이트 묶음. |
| 12 | **ai modules 일괄** (M-17 + M-19~M-24) | router + health + manual_qa + provider + rag/knowledge/vector + logging. |
| 13 | **feature_flags** (M-30) | core 기반 — AI 분리 후. |
| 14 | **appointments + availability** (M-01) | **마지막** — 다른 도메인 의존 多. 모든 도메인 분리 후 진입. |

## 33. 분리 위험이 높은 모듈

| 모듈 | 위험 사유 |
|---|---|
| **appointments (M-01)** | 다른 도메인 의존 多 + 점심창 / 충돌 / 낙관적 락 / split-code TOCTOU + 가장 큰 endpoint 묶음 |
| **leaves + ai/commands/action_leave (M-04 + M-18)** | `_upsert_employee_leave_core` 단일 진실원천 — 시그니처 절대 보존. AI action_leave (917줄) HMAC + TOCTOU 정책 보존 |
| **stats (M-07)** | 헬퍼 의존성 그래프 (`_doctor_codes_set` / `_get_manual_*` / `_apply_patient_counts`) — 통계/예약/sms/treatments 동시 의존 |
| **sms (M-09)** | 외부 munjanara API + 발송 비용 + munjanara_key 마스킹 + AI sms_draft 결합 |
| **backup (M-11)** | 운영 DB 교체 — engine.dispose() + atomic rename + 타이머 스레드 |
| **ai (M-17~M-24)** | 응답 키 33+ + local-first + manual_qa wrapper 시그니처 + vector lazy import + 18-7 status 9키 |
| **admin/about-update (M-16)** | apply-update 가 PyInstaller 폴더 교체 + updater.bat post-build 정합 |
| **sync (M-13)** | ENTITY_MAP 9개 키 외부 노드 호환 — 분리 시 키 절대 보존 (별도 ADR 필요 — C 후속) |

## 34. 리팩토링 전 테스트 보강이 필요한 모듈

> 현재 응답 키 contract 미작성 → 분리 직전 별도 contract 테스트 추가 필수.

| 모듈 | 보강 필요 (C-1~C-7 19-P-1 §22 — 분리 직전) |
|---|---|
| **appointments** (M-01) | 10 endpoint 응답 키 contract — 회귀 보호 |
| **patients** (M-02) | 환자 dict / counts dict / history 응답 contract |
| **stats** (M-07) | 8 GET endpoint 응답 키 contract |
| **sms** (M-09 + M-29) | 발송 결과 / 템플릿 / setting / draft 응답 contract |
| **admin/about-update** (M-16) | check-update / apply-update 응답 contract |
| **export_import** (M-12) | data-convert preview/apply 응답 contract |
| **availability** | 점심창 + 휴무 + 반차 + 충돌 검사 통합 회귀 (M-01 동시) |

## 35. API 응답 key 변경 위험이 큰 모듈

> 추가만 허용. 제거/이름변경/타입변경 절대 금지.

| 모듈 | 키 셋 |
|---|---|
| **ai** | manual/search 3키 + manual/ask 9키 + sources 3키 + health 9키 + health/public 4키 + status 9키 = **33+ 키** (자동 contract 테스트로 보호 — `test_ai_manual_rag_contract.py` / `test_ai_health_status.py` / `test_admin_ui_smoke.py`) |
| **appointments** | 10 endpoint — 현재 자동 contract 부재 → 보강 필요 |
| **stats** | 8 GET endpoint — 현재 자동 contract 부재 → 보강 필요 |
| **sms** | 발송 / 템플릿 / setting — 현재 자동 contract 부재 → 보강 필요 |
| **leaves** | `therapist_id` / `employee_id` 이중 alias — 보존 필수 ([api.py:1184-1199](../../app/routers/api.py:1184)) |
| **therapists** | `/api/therapists` alias 응답 보존 필수 |

## 36. 프론트 JS 의존성이 큰 모듈

> [main.html](../../app/templates/main.html) 7331줄 + 단일 `<script>` (line 521-7330) 안에서 fetch 호출지가 많은 모듈.

| 모듈 | UI 위치 |
|---|---|
| **appointments** | 예약탭 (line 41-88, FullCalendar) + 예약 모달 |
| **patients** | 환자탭 (line 89-109) + 환자 모달 + 자동완성 검색 |
| **stats** | 통계탭 (월별/주별/일별 차트) |
| **sms** | 문자탭 (line 206-329) |
| **therapists** | 직원탭 (line 110-205) — alias `therapist_id` 의존 |
| **ai** | AI 도우미 탭 (line 330-376) — 5747-5793 응답 키 5개 사용 |
| **admin** | 관리자탭 (line 377+) |

> UI 분리 자체는 19-P 비-목표 (별도 UI 세션). 본 모듈 분리는 UI 무수정으로 진행.

## 37. DB schema 변경 없이 먼저 분리 가능한 모듈

> m014+ 마이그레이션 동반 X — 본 19-P 안에 안전하게 가능.

- **core (M-25)** — DB 무관
- **audit (M-14)** — `AuditLog` 그대로
- **settings (M-15)** — `SystemSetting` 그대로
- **staff (M-03 + M-03b)** — `Employee` / `Treatment.role` 그대로
- **treatments (M-05 + M-06)** — `Treatment` / `PatientTreatmentCount` 그대로
- **leaves (M-04)** — `EmployeeLeave` 그대로
- **patients (M-02)** — `Patient` / `PatientTreatmentCount` 그대로
- **stats (M-07 + M-08)** — `Appointment` / `ManualCount` 그대로
- **sms (M-09 + M-29)** — `SmsSetting` / `SmsLog` / `SmsTemplate` 그대로
- **admin (M-10 + M-16)** — config.json / `AuditLog` 그대로
- **backup (M-11)** — 파일 시스템 + `SystemSetting.auto_backup_*` 그대로
- **export_import (M-12)** — `Patient` 그대로
- **ai (M-17~M-24)** — `AiSetting` / `AiUsageLog` / `KnowledgeChunk` / `KnowledgeIndexRun` / `KnowledgeVector` 그대로
- **feature_flags (M-30)** — DB 무관
- **appointments + availability (M-01)** — `Appointment` / `TreatmentAssignment` 그대로

→ 19-P 전체 13 modules + core 모두 m001~m013 그대로 진행 가능.

## 38. 현재 기능이 아니라 후속 검토로만 남길 모듈

| 모듈 | 사유 |
|---|---|
| **calendar / schedule_view** (M-26) | UI 분리 비-목표 (별도 UI 세션) |
| **notes 통합** (M-27) | 지속/당일 메모 정책 미결정 |
| **/api/health** (M-28) | 신규 endpoint 추가 결정 필요 (사용자) |
| **doctors 별도 모듈** (M-31) | EMR 연동 도입 시 — 진료과 / 진료실 / 담당의 / 일정. m014+ 마이그레이션 동반. |
| **Patient.doctor_id** (M-32) | 담당의 운영 정책 결정 후. |
| **resources** (M-33) | 진료실 / 장비 / 자원 — 사용자 결정 |
| **DoctorSchedule** (M-34) | 진료 예약 vs 도수치료 예약 경계 정책 결정 후 |
| **EMR Order/Prescription** (M-35) | 비트U차트 등 외부 EMR 연동 — 별도 ADR + 보안 검토 |
| **AI 의사 hallucination 가드** (M-36) | AI safety 보강 시점 — 의사 단정 표현 패턴 추가 |
| **recurring_appointments** | 주기/반복 예약 — 사용자 결정 |
| **printing / documents** | 예약표/통계표/환자 안내문 출력 — 사용자 결정 |
| **notifications** | 내부 알림 / reindex/백업 실패 알림 — 사용자 결정 |
| **노쇼 통계** | `Appointment.status` 에 노쇼 값 추가 또는 별도 컬럼 — m014+ 동반 |

## 39. 향후 코드 주석 / 문서화가 꼭 필요한 위험 지점

> 본 19-P-3 세션에서는 문서 표기만. 19-P-4+ 단계 코드 이동 시 후속 세션이 추가.

| 위험 지점 | 현재 위치 | 주석 카테고리 | 사유 |
|---|---|---|---|
| 매뉴얼 Q&A 응답 9키 빌더 | [services/ai/rag/pipeline.py](../../app/services/ai/rag/pipeline.py) `run_manual_ask` | `# COMPAT:` | 9키 후방호환 (v1.3.3 응답 계약) |
| `manual_qa.ask_manual_question(provider_override=)` 시그니처 | [services/ai/manual_qa.py:47-65](../../app/services/ai/manual_qa.py:47) | `# COMPAT:` | 라우터/테스트 모두 keyword 인자 의존 |
| `LOW_SCORE_THRESHOLD=2` | [services/ai/rag/pipeline.py](../../app/services/ai/rag/pipeline.py) | `# NOTE:` | manual_qa wrapper 가 export — 변경 시 회귀 |
| `HIGH_THRESHOLD=0.7 / LOW_THRESHOLD=0.3` | [services/ai/rag/confidence.py](../../app/services/ai/rag/confidence.py) | `# NOTE:` | hybrid 임계치 — 별도 결정 필요 |
| `_upsert_employee_leave_core` 시그니처 | [api.py:1098-1118](../../app/routers/api.py:1098) | `# COMPAT:` `# RISK:` | AI action_leave 도 호출 — 시그니처 변경 금지 |
| AI action_leave HMAC + TOCTOU | [services/ai/action_leave.py](../../app/services/ai/action_leave.py) | `# RISK:` `# SAFETY:` | 토큰 + 락 + DB 재조회 |
| 점심창 / 충돌 / 낙관적 락 | [api.py:64-107](../../app/routers/api.py:64) + [api.py:1664-1679](../../app/routers/api.py:1664) | `# NOTE:` `# RISK:` | DevTools/manual POST 우회 방지 |
| `manual60 count_increment=1` | [models/constants.py:20](../../app/models/constants.py:20) | `# NOTE:` | CLAUDE.md 절대 금지 (2로 되돌리지 않을 것) |
| `_doctor_codes_set` / `is_doctor_filter` | [api.py:153-156](../../app/routers/api.py:153) + [api.py:3464](../../app/routers/api.py:3464) | `# NOTE:` | role=doctor 분기 정책 |
| assign role=doctor 강제 | [api.py:1773-1775](../../app/routers/api.py:1773) | `# RISK:` | 의사 항목 (injection/cartilage) handler 강제 |
| AI 응답 의사 정보 임의 생성 금지 | [services/ai/rag/pipeline.py](../../app/services/ai/rag/pipeline.py) `_RE_MEDICAL_CLAIM` 등 | `# SAFETY:` | M-36 후속 — 의사 단정 패턴 추가 시점 |
| PII 마스킹 + sha256 + 200자 cap | [services/ai/{pii,ai_logging,health}.py](../../app/services/ai/) | `# SAFETY:` | API key + PII 비노출 정책 |
| munjanara_key 마스킹 | [api.py:3115-3160](../../app/routers/api.py:3115) `_sms_sanitize` | `# SAFETY:` | 외부 SMS provider 비밀 |
| restore atomic rename + engine.dispose() | [api.py:2168-2256](../../app/routers/api.py:2168) | `# RISK:` `# SAFETY:` | 운영 DB 교체 — Windows 파일 lock |
| reindex lock + DELETE 금지 | [services/ai/knowledge/indexer.py](../../app/services/ai/knowledge/indexer.py) | `# RISK:` | 부분 실패 시 기존 chunk 보존 |
| ENTITY_MAP 9개 키 | [services/sync.py:21-29](../../app/services/sync.py:21) | `# RISK:` `# COMPAT:` | 외부 노드 호환 — 키 절대 보존 |
| 자동 백업 타이머 daemon=True | [services/backup.py:143-181](../../app/services/backup.py:143) | `# NOTE:` | conftest 람다 교체 — 테스트 약화 금지 |
| `pyproject.toml app/**/*.py per-file-ignores` | [pyproject.toml](../../pyproject.toml) | `# NOTE:` | CLAUDE.md 명시 — 풀면 대량 포맷 변경 |
| `dosu_clinic.spec` hidden imports 17개 (18-8) | [dosu_clinic.spec:31-97](../../dosu_clinic.spec:31) | `# COMPAT:` `# RISK:` | 신규 modules 분리마다 동기화 + 53 tests 통과 |
| FakeProvider / FakeEmbeddingProvider 컨벤션 | [tests/conftest.py:112-137](../../tests/conftest.py:112) | `# SAFETY:` | 외부 SDK 차단 + `len(.calls)` 단언 |

---

## 40. 종합

- 30개 모듈 매핑: **현재 기능 12개** + **부분 존재 7개** + **후속 검토 11개**.
- 19-P 안에 즉시 분리 (A): **modules 13개** (appointments / patients / staff / leaves / treatments / stats / sms / admin / backup / ai / audit / settings / export_import) + `core/`.
- post-19-P 후속 (C): calendar / notes 통합 / health / doctors EMR / resources / EMR / 노쇼 / recurring / printing / notifications + sync 위치 결정 + AI 의사 가드.
- 우선순위 14단계 (§31 + §32) — core 1번 → appointments 14번 (마지막).
- 본 19-P-3 단계는 **DB schema 변경 없이** 모든 즉시 분리 모듈 진행 가능 (§37).
- 응답 키 보호: AI 33+ 키는 자동 contract 테스트로 이미 잠금. 비-AI (appointments/patients/stats/sms/admin/export_import) 는 **분리 직전** 별도 contract 테스트 보강 필수 (§34).
- 위험 지점 19개 (§39) — 후속 코드 이동 세션이 COMPAT/SAFETY/NOTE/RISK 주석 추가.
- 다음 문서: `docs/refactor/19_refactor_dependencies.md` (19-P-4) — 본 §의 모듈 매핑을 기반으로 **모듈 간 의존성 그래프 + 분리 시 import 변경 매트릭스** 구체화.
