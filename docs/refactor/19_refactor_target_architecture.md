# 19-P-2 단위화 리팩토링 — 목표 모듈 구조 (19_refactor_target_architecture, r3 보정본)

> 19-P-1 [19_refactor_current_state.md](19_refactor_current_state.md) 의 현재 구조 스냅샷을 기준으로,
> 이후 단계적 분리 후 도달할 **목표 모듈 구조**를 설계한다.
> 본 문서는 *방향*만 정의한다 — 실제 코드 이동은 19-P-3 이후 별도 세션.

## 0. 메타

- 작성일: 2026-05-02
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: 529 passed, 1 skipped, 7 xfailed
- 19-P-1 Codex r2 판정: **pass** ([reports/refactor/19-P-1_codex_review.md](../../reports/refactor/19-P-1_codex_review.md))
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *설계 의도* 문서 — 새 폴더 / 파일을 실제로 만들지 않는다.
- **r1 Codex 검증 (2026-05-02 fail)** + **r2 Codex 검증 (2026-05-02 fail)** 후 본 r3 보정 — 보정 이력:
  - **r2 보정**:
    - §2-1 V2 트리에서 `calendar/`, `notes/`, `health/` 3개를 **§2-2 post-19-P 후보 블록** 으로 분리.
    - §9 분류표 항목 수 정정: "36항목" → **"37행"** (M-01~M-36 + M-03b).
    - §12 종합 A/B/C 카운트 재계산: 즉시분리 **21** / 하위책임 **6** / 후속검토 **10** = 합 37.
    - §3-8 admin / §4 health / §4 calendar / §4 notes 행에 후속 검토 명시 추가.
  - **r3 보정** (Codex r2 G-5 fail — modules 개수 표기 오류 정정):
    - §0 메타 + §2-1 트리 머리말 + §12 종합: V2 modules **"11개" → "13개"** (실제 트리: appointments / patients / staff / leaves / treatments / stats / sms / admin / backup / ai / audit / settings / export_import = 13개).
    - §2-2 post-19-P 블록 머리말: **"다음 4개 모듈" → "다음 6개 모듈"** (calendar / notes / health / doctors / resources / emr).
    - §0 / §2-1 / §2-2 / §12 4개 위치 모두 정합.

---

## 1. 목표 구조 설계 원칙

| # | 원칙 | 본문 |
|---|---|---|
| P-1 | 기능 변경 금지 | 단위화의 목적은 **구조 안정화**. 예약/휴무/문자/통계/AI 등 기능 결과는 변경 전후 동일해야 한다. |
| P-2 | 응답 키 후방호환 | [19_refactor_current_state.md §21](19_refactor_current_state.md) 의 33+키 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9 + 비-AI alias) 모두 보존. 추가만 허용. |
| P-3 | UI 동작 보존 | [main.html](../../app/templates/main.html) 7331줄 + JS 의존 키 (특히 `not_found`/`answer`/`confidence`/`sources[].title,path`) 보존. UI 분리는 19-P 비-목표. |
| P-4 | DB schema 보존 | m001~m013 diff 0. 신규 마이그레이션은 m014 부터, 본 19-P 기간 내에는 가능하면 미도입. 컬럼 rename 금지. |
| P-5 | 단계적 이동 | 한 번에 모든 도메인 분리 X. **모듈 1개씩** wrapper/adaptor → 내부 위임 순서. |
| P-6 | rollback 가능성 | 각 단계 분리 후 git revert 1회로 이전 상태 복원 가능해야 함. 신규 폴더 추가 + import 변경 + wrapper 만 — DB 마이그레이션/응답 키 변경 동반 금지. |
| P-7 | AI/RAG local-first 보존 | [docs/AI_WORKING_RULES.md §2](../AI_WORKING_RULES.md) 절대 원칙 — 외부 LLM/Embedding 호출 0 가능, `local_only` 모드에서 `len(provider.calls)==0`. |
| P-8 | 기능 결과 동치 | 예약/휴무/문자/통계 동일 입력 → 동일 응답. 회귀 테스트 (529 passed) 100% 통과 유지. |
| P-9 | 프론트 의존 응답 키 보존 | C-1~C-7 (§22) 의 비-AI 응답 키 매트릭스는 분리 *직전* 별도 contract 테스트로 잠근 후에만 해당 도메인 분리 진행. |
| P-10 | PyInstaller 안정성 | [dosu_clinic.spec](../../dosu_clinic.spec) hidden imports 매 분리마다 동기화 + [test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) 53 tests 통과. |
| P-11 | per-file-ignores 보존 | `pyproject.toml` `app/**/*.py` per-file-ignores 풀지 않는다 ([CLAUDE.md](../../CLAUDE.md) 명시). 대량 포맷 변경 발생 방지. |
| P-12 | 운영 DB 비접근 | 본 세션 + 모든 후속 19-P 세션은 `%APPDATA%\도수치료예약\clinic.db` 미접근. `tests/conftest.py` 4단계 격리 약화 금지. |

---

## 2. 목표 폴더 구조

> 사용자 제시 후보 (modules/* + core/*) 를 현재 코드와 정합하도록 조정. **즉시 분리 / 하위 책임 / 후속 검토** 3분류로 구분 (§9 표 참조).

### 2-1. 단계 이동 후 도달 구조 (V2 = 19-P 종료 시점 가정)

```
app/
  main.py                      # FastAPI 앱 부트스트랩 (그대로)
  core/                        # ※ 신설 — modules/* 가 공통 참조
    config.py                  # 현재 app/config.py 이동 (resource_path / get_db_path / load_config)
    database.py                # 현재 app/database.py 이동 (engine / SessionLocal / init_db)
    errors.py                  # ※ 신설 — 공통 HTTPException + reason_code 매핑
    responses.py               # ※ 신설 — 표준 응답 envelope (현재 응답 키 그대로 + 추가만)
    time_utils.py              # ※ 신설 — Asia/Seoul 기준 today/tomorrow + 점심창 헬퍼 이동
    security.py                # 현재 app/services/auth.py 이동 (PBKDF2 + 세션 토큰)
    feature_flags.py           # ※ 신설 — AI_RAG_ENABLED / VECTOR / HYBRID + ai_mode 파생
  modules/
    appointments/
      router.py                # POST/PATCH/PUT/DELETE /api/appointments + assign/split-code/approve/cancel
      service.py               # _bump_patient_count / _check_version / _bump_version 이동
      repository.py            # Appointment / TreatmentAssignment ORM 접근
      schemas.py               # AppointmentIn / Update / AssignmentChange / ApproveAction / CancelAction
      rules.py                 # 점심창 차단 / 충돌 검사 / 낙관적 락 정책
      availability.py          # 예약 가능 시간 계산 + 휴무 차단 + 오전/오후반차 차단
    patients/
      router.py                # /api/patients[/search/{pid}/memo/last-appointments/manual-history-summary/history]
      service.py               # _patient_to_dict / _serialize_patients_bulk / _check_patient_duplicate
      repository.py            # Patient / PatientTreatmentCount 접근
      schemas.py               # PatientIn / PatientCountIn
      notes_service.py         # 환자별 메모 (현재 PATCH /api/patients/{pid}/memo)
    staff/                     # ※ 19-P-2 보완: doctor + therapist 통합 (Employee 단일 테이블, role 컬럼 분기)
      router.py                # /api/employees + alias /api/therapists
      service.py               # _serialize_employee / 정렬 / can_eswt/can_manual 매트릭스 / role 분기
      repository.py            # Employee 접근 (role="doctor" | "therapist")
      schemas.py               # EmployeeIn
      doctors_service.py       # ※ 신설 (얇음) — _doctor_codes_set + role=doctor 필터 (api.py:153, 3525) 통합
      # ※ 별도 modules/doctors/ 폴더는 후속 검토 (담당의/진료과/진료실/오더/처방/EMR 도입 시)
    leaves/
      router.py                # /api/employee-leaves + alias /api/therapist-leaves[/bulk-set]
      service.py               # _upsert_employee_leave_core (단일 진실원천 — AI action_leave 도 호출)
      repository.py            # EmployeeLeave 접근
      schemas.py               # EmployeeLeaveIn
      rules.py                 # full/half_morning/half_afternoon/annual/monthly 분기 정책
    treatments/
      router.py                # /api/treatments + /api/treatment-meta + /api/treatments/{tid}/references
      service.py               # _serialize_treatment / _normalize_incentive / _build_treatment_meta
      repository.py            # Treatment 접근
      schemas.py               # TreatmentIn / TreatmentOut
      completion_rules.py      # count_increment 정책 (manual60=1 보존), approve/revert 시 done_count 증감
    stats/
      router.py                # /api/stats/* (8 GET) + /api/manual-counts + /api/export/{manual-schedule,stats}.xlsx
      service.py               # _resolve_stats_range / _date_list / 색상 헬퍼
      repository.py            # ManualCount + Appointment 집계 쿼리
      schemas.py               # 통계 응답 스키마 (현재 응답 키 그대로)
      aggregators.py           # _get_manual_treatment_rows / _get_manual_therapy_codes / by-therapist/hour/weekday/treatment 분기
    sms/
      router.py                # /api/sms/{setting,tomorrow-targets,templates,send}
      service.py               # 발송 흐름 + _normalize_phone_for_sms / _is_valid_kr_mobile / _mask_phone_for_log / _sms_sanitize
      templates.py             # SmsTemplate CRUD (현재 router 내 직접 처리)
      provider.py              # 문자나라 외부 API client (현재 sms_send 안에 inline) — 외부 경계 분리
      schemas.py               # SmsSettingIn / SmsTemplateIn / SmsSendPayload
    admin/
      router.py                # /api/admin/* + /api/about/* + /api/config/*
      service.py               # 관리자 흐름 (auth wrapper / change-password / config 갱신)
      schemas.py               # AdminLogin / ChangePassword / ConfigPatch
    backup/
      router.py                # /api/backup/* + /api/restore (UploadFile)
      service.py               # 현재 app/services/backup.py 이동 (make/restore_latest/restore_by_name + 타이머)
      schemas.py               # BackupItem / RestoreResult
    ai/
      router.py                # /api/ai/* (13 endpoint) — 18-7 status 포함
      rag/                     # 현재 app/services/ai/rag/ 그대로
      knowledge/               # 현재 app/services/ai/knowledge/ 그대로
      vector/                  # 현재 app/services/ai/vector/ 그대로
      safety/                  # 현재 rag/safety.py 가 디렉토리화 (pii / hallucination_guard 분리)
      commands/                # action_leave (917줄) 분리 — parse / preview / execute + HMAC 토큰
      manual_qa.py             # wrapper 그대로 (시그니처 보존)
      sms_draft.py             # 현재 그대로
      provider.py              # 현재 그대로
      health.py                # 현재 그대로 (/api/ai/status 본체)
      logging.py               # 현재 ai_logging.py rename
    audit/
      service.py               # AuditLog insert (현재 api.py:audit())
      repository.py            # AuditLog 접근
      schemas.py
    settings/
      service.py               # SystemSetting + SmsSetting + AiSetting 통합 read/write
      repository.py
      schemas.py
    export_import/
      service.py               # data-convert/preview + apply (현재 _dc_* 헬퍼 ~400줄)
      schemas.py               # 엑셀 import 응답
```

> **본 V2 트리는 19-P 종료 시점에 실제로 도달하는 modules 13개** + `core/` (총 14개). 후속 검토 (post-19-P) 모듈은 본 트리에 포함하지 않으며 §2-2 별도 블록으로 분리 표시한다 (Codex r1 G-5 fail 보정 + r2 G-5 fail 카운트 정정).
>
> 13개 modules 명시: appointments / patients / staff / leaves / treatments / stats / sms / admin / backup / ai / audit / settings / export_import.

### 2-2. post-19-P 후보 블록 (V2 트리에 미포함 — 19-P 비-목표)

다음 6개 모듈은 19-P 종료 시점에 도달하지 않는다. §9-2 분류표의 후속 검토 (C) 항목과 1:1 대응한다.

목록: `calendar/` (M-26) · `notes/` (M-27) · `health/` (M-28) · `doctors/` (M-31) · `resources/` (M-33) · `emr/` (M-35).

```
app/modules/                     # ※ 본 블록은 19-P 종료 후 사용자 결정 시 추가 검토
  calendar/                      # M-26 — main.html FullCalendar 서버 사이드 view-model. UI 분리는 19-P 비-목표.
    service.py
    schemas.py
    view_models.py
  notes/                         # M-27 — 환자/예약 메모 통합. 지속 메모 vs 당일 메모 정책 미결정.
    service.py
    repository.py
    schemas.py
  health/                        # M-28 — /api/health 신규 (현재 부재). /api/ai/health 와는 별개.
    router.py
    service.py
    diagnostics.py
  doctors/                       # M-31 — EMR 연동 도입 시. 진료과/진료실/담당의/일정.
    router.py
    service.py
    repository.py
    schemas.py
  resources/                     # M-33 — 진료실 / 장비 / 자원.
  emr/                           # M-35 — 오더 / 처방 / EMR 연동.
```

또한 다음 위치 결정도 19-P 종료 후 별도 결정:

- `modules/sms/provider.py` 의 분리 시점 — 문자나라 외부 API client. 19-P 후반 또는 별도 세션.
- `modules/sync/` 위치 — `services/sync.py` 그대로 vs `core/sync.py` 이동 (T-3).
- AI 의사 hallucination 가드 보강 (M-36).

---

## 3. 핵심 모듈 책임 정의

### 3-1. appointments

- 예약 생성/수정/삭제/조회 ([api.py:1608-2057](../../app/routers/api.py:1608)).
- 예약 상태 관리 (`status` ∈ `reserved`/`approved`/`canceled`).
- 예약 중복 검사 + 낙관적 락 (`version` 컬럼).
- 예약 가능 시간 계산 (`availability.py`).
- 치료사 휴무와의 충돌 검사 (`leaves` 모듈에서 read).
- DevTools/manual POST 우회 방지 — 백엔드에서 점심창/충돌/락 검증.
- 완료 카운트 +N 증가는 `treatments.completion_rules` 위임 (현재 `_bump_patient_count`).
- **담당의 연결 후보** (후속 검토): 도수치료 예약과 의사 (`Treatment.role="doctor"` 항목 — injection/cartilage) 연결은 현재 `TreatmentAssignment.handler_id` 로만 추적 ([api.py:1773-1775](../../app/routers/api.py:1773) `change_assignment` 가 의사 항목 배정 시 handler role=doctor 강제). **환자별 담당의 (Patient.doctor_id) 는 부재** — 후속.
- **진료 예약 vs 도수치료 예약 경계** (후속 검토): 현재 단일 `Appointment` 테이블에 `treatment_codes` JSON 으로 분기. 진료 전용 별도 테이블/엔드포인트는 부재.

### 3-2. patients

- 환자 정보 CRUD ([api.py:1280-1607](../../app/routers/api.py:1280)).
- 신환 여부 (`Appointment.is_new_patient`).
- 환자별 메모 (`patients.notes_service` — `PATCH /api/patients/{pid}/memo`).
- 환자 검색 (이름/연락처/차트번호 인덱스 활용).
- 개인정보 보호 — PII 원문은 AI 로그/응답에 포함 금지 (현재 정책 그대로).
- **환자별 담당의 후보** (후속 검토): 현재 `Patient` 모델에 담당의 컬럼 부재. EMR 연동 도입 시 `doctor_id` (또는 `staff/doctors`) 추가 후보 — m014+ 마이그레이션 + 응답 키 추가.

### 3-3. staff (doctors + therapists)

> 19-P-2 보완: 현재 `Employee` 단일 테이블 + `role` 컬럼 분기 구조이므로 단일 `modules/staff/` 로 통합 처리. `modules/doctors/` 별도 분리는 EMR 연동 도입 시 후속 검토.

#### 3-3-1. 공통 (Employee)

- 직원 정보 CRUD ([api.py:1009-1079](../../app/routers/api.py:1009)).
- 활성 여부 (`active`), 색상 표시 (`color`).
- `role` 분기: `"doctor"` | `"therapist"` ([constants.py:9-11](../../app/models/constants.py:9)).
- 시드 자동 등록 ([services/seed.py:97-117](../../app/services/seed.py:97) — 의사 2명 + 치료사 3명 — 단, `_seed_demo_data` 는 현재 비활성화).
- 휴무 모듈과의 경계: staff 는 `Employee` 만, 휴무는 `EmployeeLeave` 별도 모듈.

#### 3-3-2. therapists 책임

- 치료 가능 항목 (`can_eswt`, `can_manual`).
- alias `/api/therapists` (role=therapist 필터, [api.py:1175-1182](../../app/routers/api.py:1175)).
- 도수/체외충격파 배정 대상.

#### 3-3-3. doctors 책임 (얇은 분기)

- `_doctor_codes_set()` ([api.py:153-156](../../app/routers/api.py:153)) — 의사 전용 치료항목 코드 집합 (injection/cartilage).
- assignment 시 의사 항목 (`Treatment.role="doctor"`) 배정 대상 강제 ([api.py:1773-1775](../../app/routers/api.py:1773)).
- 통계 (`stats_by_therapist`) 의 의사 필터 분기 ([api.py:3464, 3491-3527](../../app/routers/api.py:3464)) — `is_doctor_filter` 시 doctor role 직원만 집계.
- 엑셀 export 의 의사 항목 suffix 처리 ([api.py:4339, 4362-4465](../../app/routers/api.py:4339)).

#### 3-3-4. 부재 / 후속 검토 (의사 EMR 연동 경계)

- 진료과 (`department`) — 부재.
- 진료실 (`room` / `resource`) — 부재 (§4 resources 후속).
- 의사별 진료 일정 (`Doctor.schedule`) — 부재 (현재 `Appointment` 단일 테이블).
- 담당의 연결 (`Patient.doctor_id`) — 부재 (§3-2 patients 후속).
- 오더 / 처방 (EMR `Order` / `Prescription`) — 부재.
- 향후 비트U차트/EMR 연동 — 후속 검토. 본 19-P 비-목표.
- **AI 명령에서 의사/진료진 정보 임의 생성 금지** (§3-10 ai 정책으로 명시).

### 3-4. leaves

- 휴무 / 연차 / 월차 / 오전반차 / 오후반차 (현재 `leave_kind` + `leave_type`).
- 휴무일 예약 차단은 `appointments.availability` 가 `leaves.repository` 를 read-only 호출.
- 휴무 중복 방지: `(employee_id, leave_date)` UNIQUE — m011 보존.
- AI 자연어 휴무 등록은 `modules/ai/commands/action_leave.py` 가 `leaves.service._upsert_employee_leave_core` 만 호출 — 단일 진실원천 유지.

### 3-5. treatments

- 치료항목 CRUD + 시드 5개 (injection/cartilage/eswt/manual30/manual60).
- `count_increment=1` 정책 보존 (manual60 = 1 — [CLAUDE.md](../../CLAUDE.md) 명시).
- 도수치료 시간별 항목 (manual30/60), 체외충격파 (eswt) 분기 — `aggregators` 가 사용.
- 완료체크 = `treatments.completion_rules` — approve 시 +N, revert 시 -N.
- "시간 가중치가 아니라 항목별 개별 체크" 원칙 보존.

### 3-6. stats

- 8 GET endpoint + 엑셀 export (현재 [api.py:3450-5127](../../app/routers/api.py:3450)).
- 예약 통계 / 완료 통계 / 치료사별 / 항목별 / 시간대별 / 요일별.
- 신환 수 (`is_new_patient` 카운트).
- 취소 / 노쇼: 현재 `status="canceled"` 만, 노쇼는 별도 필드 부재 — **후속 검토** (§4 cancellations/no_show).
- ManualCount upsert (수동 카운트, 당일 입력).
- **의사별 통계** (현재 부분 구현): `is_doctor_filter` 분기로 의사 항목 (injection/cartilage) 만 의사별 집계 ([api.py:3491-3527](../../app/routers/api.py:3491)). 향후 진료 통계 (의사 진료 건수 / 진료시간 / 환자 수) 는 EMR 연동 도입 시 후속 검토.

### 3-7. sms

- 예약문자 발송 (`sms.service` + `sms.provider` 외부 API client 분리).
- 문자 템플릿 CRUD (`sms.templates`).
- 문자나라 연동 — `provider.py` 가 외부 경계 (URL/ID/Key/Pw + `_smart_decode_response`).
- 발송 대상 추출 (`sms.service` `tomorrow-targets`).
- 관리자 설정 (`SmsSetting`) — `modules/settings` 또는 `modules/sms/service` 둘 다 가능. **결정 필요** ([§9 분류표](#9-모듈-분류표) 표시).
- `munjanara_key` 마스킹 패턴 보존.
- **담당의 정보 포함 문자 후보** (후속 검토): 현재 템플릿 변수에 담당의 placeholder (`{담당의}`) 부재. 추가 시 `Patient.doctor_id` (또는 `Appointment.doctor_id`) + 템플릿 변수 매핑 + AI sms_draft 가드 모두 동반 변경 필요.

### 3-8. admin

- `/api/admin/{status,login,logout,change-password}` + `/api/about/*` + `/api/config/*`.
- 관리자 인증 = `core.security` (PBKDF2 + 세션 + 5회 잠금).
- 시스템 상태 확인 — 현재는 `modules/admin/` 안에서 `/api/admin/status` (인증 상태) 만 응답. 별도 `/api/health` (DB/백업/sync 상태) 는 부재 — `modules/health/` 신설은 post-19-P 후속 (§2-2, M-28).
- API key 등록 여부 표시는 `/api/ai/status` (`modules/ai/health.py` 본체) — admin 모듈은 boolean 만.
- API key 원문 노출 금지 — 모든 응답에 `api_key_masked` 키 부재 (`api_key_set` boolean 만).
- **의사 관리 설정 후보** (후속 검토): 현재 의사 등록은 `/api/employees` (role=doctor) 로 처리. 진료과/진료실/담당의 매핑 관리 화면은 부재. 도입 시 `modules/admin/` 또는 `modules/staff/` 하위에 별도 endpoint 추가 후보.

### 3-9. backup

- 자동 백업 + 수동 백업 + 복원 (현재 [services/backup.py](../../app/services/backup.py) 그대로 이동).
- 백업 목록, 백업 경로, 오래된 백업 자동 정리 (보관 개수 정책).
- `/api/restore` UploadFile 처리 — integrity_check + atomic rename.
- 타이머 스레드는 `modules/backup/service.py` 가 시작 책임 보유. `app/main.py` 는 호출만.

### 3-10. ai

- `/api/ai/*` 13 endpoint (현재 [routers/ai.py](../../app/routers/ai.py) 929줄).
- RAG/Knowledge/Vector 패키지는 18-1~18-6 구조 그대로 유지 — 19-P 에서 추가 분리 불필요.
- Safety 가 디렉토리화: `pii` + `hallucination_guard` 분리.
- Commands: `action_leave` (917줄) 가 `commands/action_leave.py` 로 이동 (parse/preview/execute + HMAC).
- Local-first 원칙 보존: 외부 API 호출 0 가능, `local_only` 모드 단언.
- AI 로그 = `modules/ai/logging.py` (`AiUsageLog` 컬럼 보존).
- **의사/진료진 정보 임의 생성 금지**: AI 응답이 의사 이름/진료과/진료실/담당의/진료일정/오더/처방을 *DB 근거 없이* 생성하는 것을 금지. RAG hallucination guard (현재 `_RE_MEDICAL_CLAIM` / `_RE_EXECUTION_CLAIM` / 출처 없는 단정) 와 동일 정책 — 의사 관련 단정 표현 (`담당의는 X 입니다` / `Y 의사 진료실 ...`) 도 차단 대상으로 추가 후보. 본 19-P 비-목표지만 AI safety 보강 시 후속.
- **담당의/진료일정 답변 정책**: AI 가 `담당의`, `진료일정`, `진료과` 관련 질문을 받았을 때 — 현재 부재 (Patient.doctor_id / Doctor.schedule 컬럼 부재). 도입 시 RAG 가 DB 조회 결과 근거가 있을 때만 답변, 부재 시 `not_found` 응답.

---

## 4. 추가 보조/공통 기능 분류

> 사용자 §4 에서 제시한 14개 항목을 본 분류표에 모두 정리.

| 항목 | 분류 | 위치 / 의사결정 |
|---|---|---|
| **calendar / schedule_view** | 후속 검토 (post-19-P, §2-2 / M-26) | UI 분리 비-목표. main.html 7331줄 단일 script 안에 FullCalendar 코드. 본 19-P 종료 시점 V2 에 미포함. view-model 만 서버 사이드로 빼는 안은 후속 검토. |
| **availability** | 독립 모듈 (`modules/appointments/availability.py`) | 점심창 + 충돌 + 휴무 + 반차 + 치료시간별 가능 여부 + 백엔드 우회 방지. 현재 [api.py:64-107](../../app/routers/api.py:64) 점심창 헬퍼만 존재 — 19-P-3 에서 분리 결정. |
| **notes** | 기존 모듈 하위 책임 (`modules/patients/notes_service.py`) — 19-P 안. 통합 `modules/notes/` 는 후속 검토 (post-19-P, §2-2 / M-27) | 환자별 메모 (`Patient.memo`) + 예약별 메모 (`Appointment.memo`) 는 patients 모듈 안에서 처리. 통합 `modules/notes/` 신설은 지속 메모 vs 당일 메모 정책 결정 후 post-19-P. |
| **permissions / auth** | 기존 모듈 (`core/security`) | 관리자 인증은 `core.security`. AI 설정 / reindex / vector on-off / 백업복구 접근 제한은 `require_admin`. **현재 권한 구조는 admin 단일 등급만** — 직원/관리자 분리는 후속 검토. |
| **settings** | 독립 모듈 (`modules/settings/`) | SystemSetting + SmsSetting + AiSetting 통합 read/write. 단, AI 설정의 KEY 갱신은 `modules/ai/router.py` 가 기존 `/api/ai/settings` 엔드포인트 보유 — settings 모듈은 read-only or low-level. |
| **audit / logs** | 독립 모듈 (`modules/audit/`) | 예약/휴무/문자/AI/관리자 변경 모두 `audit.service.audit()` 호출. 현재 [api.py:110-127](../../app/routers/api.py:110) `audit()`/`_log()` 가 단일 함수. PII 원문 저장 금지 정책 보존. |
| **export_import** | 독립 모듈 (`modules/export_import/`) | 엑셀 다운로드 (manual-schedule.xlsx, stats.xlsx) + data-convert (환자 엑셀 import ~400줄 `_dc_*` 헬퍼). CSV/비트U차트 import는 후속 검토. |
| **health / diagnostics** | 후속 검토 (post-19-P, §2-2 / M-28) | DB / 백업 / sync / PyInstaller 환경. **현재 `/api/health` 엔드포인트 부재** — 추가 결정 필요. `/api/ai/health` 는 `modules/ai/router.py` 가 그대로 가짐 (별도 도메인). 본 19-P 종료 시점 V2 에 미포함. |
| **core responses/errors** | 독립 모듈 (`core/responses.py`, `core/errors.py`) | 표준 응답 envelope + reason_code → HTTPException 매핑. 기존 응답 키 100% 보존 — 추가만. validation error 표준화 (현재 FastAPI 기본 422). |
| **feature_flags** | 독립 모듈 (`core/feature_flags.py`) | AI_RAG_ENABLED / VECTOR_ENABLED / HYBRID_ENABLED / ai_mode (local_only/local_first/ai_assist) — 현재 `AiSetting` + 환경 변수에서 파생. 통합 진입점 신설. |
| **batch / jobs** | 독립 모듈 (후속) | 자동 백업 (현재 backup.py 타이머) + reindex (현재 indexer.py lock) + 향후 SMS 대상 자동 생성. 통합 스케줄러는 후속 검토. 동시 실행 lock 은 각 모듈에서 보유. |
| **printing / documents** | 후속 검토 | 현재 미구현 — 예약표/통계표/환자 안내문 출력은 후속 결정. |
| **notifications** | 후속 검토 | 현재 미구현 — 내부 알림 / reindex 실패 / 백업 실패 알림 후속 결정. |
| **cancellations / no_show** | 후속 검토 | 취소는 `status="canceled"` 존재. 노쇼는 별도 필드 부재 → m014 컬럼 추가 후보 (본 19-P 비-목표). |
| **recurring_appointments** | 후속 검토 | 현재 미구현 — 주기/반복 예약은 후속 결정. |
| **resources** | 후속 검토 | 치료실 / 장비 / 공간 자원 — 현재 미구현. |
| **privacy / retention** | 기존 모듈 하위 책임 | PII 마스킹 = `modules/ai/safety/pii.py`. 로그 보존 = `modules/audit`. 오래된 AI 로그 삭제 정책은 후속 검토 (현재 무한 보존). 환자정보 비활성/삭제 정책 후속. |
| **concurrency / locking** | 기존 모듈 하위 책임 | 중복 클릭 방지 = `appointments.rules` (낙관적 락 `version`). reindex lock = `modules/ai/knowledge/indexer.py`. 백업/복구 중 실행 제한은 후속 검토 (현재 `engine.dispose()` 만). |
| **time_utils** | 독립 모듈 (`core/time_utils.py`) | 오늘 / 내일 / 이번달 / 점심창 / 오전반차 / 오후반차 / Asia/Seoul 명시. 현재 `datetime` 직접 사용 다수 — 통합. |
| **doctors / medical_staff** | 기존 모듈 하위 책임 (`modules/staff/doctors_service.py`) — 현재 + 독립 모듈 (`modules/doctors/`) — 후속 검토 | 현재: `Employee.role="doctor"` + `Treatment.role="doctor"` 분기 + `_doctor_codes_set()` + 통계 `is_doctor_filter` + assignment role 검증 — 모두 §3-3 staff 안에서 통합. **부재 (후속 검토)**: 진료과 / 진료실 / 담당의 (Patient.doctor_id) / 의사별 진료 일정 / 오더 / 처방 / EMR 연동 — 분리 시 `modules/doctors/` 신설 + m014+ 마이그레이션 + 응답 키 추가. 현재는 별도 폴더 분리 *과잉* 판단. AI 명령에서 의사 관련 정보 임의 생성 금지 (§3-10 명시). |

---

## 5. 파일별 책임 기준

| 파일명 패턴 | 책임 | 외부 호출 가능 |
|---|---|---|
| `router.py` | API endpoint 정의 + Depends 주입 + HTTPException raise | service / schemas |
| `service.py` | 비즈니스 로직 + 트랜잭션 경계 | repository / rules / 다른 모듈의 service (단, 의존성 방향 §6 준수) |
| `repository.py` | DB 접근 (SQLAlchemy 쿼리) | models 만 |
| `schemas.py` | Pydantic In/Out 타입 | 없음 (순수 타입 정의) |
| `rules.py` | 업무 규칙 / 검증 (점심창 / 충돌 / 정책) | 순수 함수 — DB 미접근 |
| `availability.py` | 예약 가능 여부 / 충돌 검사 | repository 만 (read-only) |
| `templates.py` | 문자 템플릿 CRUD | repository |
| `provider.py` | 외부 서비스 연동 경계 (HTTP client) | 외부 API |
| `aggregators.py` | 통계 집계 함수 모음 | repository |
| `completion_rules.py` | 완료체크 / 카운트 규칙 (manual60=1 등) | repository (read), 다른 모듈의 repository (write 대상) |
| `view_models.py` | 프론트 표시용 데이터 조립 | service / schemas |
| `diagnostics.py` | 상태 점검 (DB / 백업 / sync) | core / 다른 모듈의 service (read-only) |
| `responses.py` | 표준 응답 envelope (현재 키 보존 + 추가만) | 없음 |
| `errors.py` | 공통 예외 / reason_code 매핑 | 없음 |
| `feature_flags.py` | 플래그 통합 (env + AiSetting 파생) | core.config |

---

## 6. 모듈 간 의존성 방향

```
                 ┌────────────────────────────────┐
                 │  router (FastAPI APIRouter)    │
                 └───────────────┬────────────────┘
                                 │
                 ┌───────────────▼────────────────┐
                 │  service (비즈니스 로직)        │
                 └───────────────┬────────────────┘
                                 │
                 ┌───────────────▼────────────────┐
                 │  repository (DB 접근)           │
                 └───────────────┬────────────────┘
                                 │
                 ┌───────────────▼────────────────┐
                 │  models (ORM)                   │
                 └────────────────────────────────┘
```

### 6-1. 도메인 간 호출 허용 / 금지

| from → to | 허용 | 예 |
|---|---|---|
| appointments → patients / therapists / treatments / leaves (read) | ✅ | 예약 충돌 검사, 환자/치료사 존재 검증 |
| appointments → sms (호출) | ❌ | sms 발송은 별도 흐름. 예약 변경이 자동 SMS 트리거하지 않음 (현재 정책 보존) |
| sms → appointments / patients / therapists (read) | ✅ | tomorrow-targets / send 시 환자/예약 데이터 조회 |
| sms → appointments (write) | ❌ | sms 가 예약 상태 변경 금지 |
| stats → appointments / treatments / therapists (read) | ✅ | 집계 시 read-only |
| stats → repository (직접) | ❌ — 각 도메인 repository 경유 권장 | DB 접근이 stats 에 난잡하게 퍼지지 않게 |
| ai/commands → leaves (write via service.\_upsert_employee_leave_core) | ✅ | 단, safety 검증 + HMAC 토큰 + TOCTOU 통과 후 |
| ai/commands → appointments / patients (write) | ❌ — 현재 정책 | 본 19-P 기간 내 변경 X |
| ai/rag → appointments / patients / therapists (DB) | ❌ — local-first | RAG 가 임의로 환자/예약 데이터 주입 금지 |
| audit → 모든 모듈 | ✅ — 호출만 | audit 은 read-only (insert) only |
| 모든 모듈 → audit | ✅ | CUD 작업 시 audit.service.audit() 호출 |
| 모든 모듈 → core | ✅ | core.config / core.database / core.errors / core.responses 자유 사용 |
| core → modules | ❌ | core 가 modules 를 import 하지 않음 (단방향) |

### 6-2. 외부 API / sync 경계

- `sms/provider.py` — 문자나라 외부 HTTP API 호출 (현재 [api.py:3225](../../app/routers/api.py:3225) `sms_send` 안에 inline). 분리 시 timeout / retry / 응답 디코딩 정책 그대로.
- `services/sync.py` 는 `modules/` 외부의 노드 간 sync 로 그대로 유지. `ENTITY_MAP` 의 9개 도메인 모델 문자열 키는 분리 후에도 보존 (외부 노드 호환).
- `ai/provider.py` — OpenAI / Anthropic SDK 호출. 테스트는 `tests/conftest.py:_block_sdk_modules` 가 차단.

---

## 7. 호환성 보존 (P-2 / P-3 / P-4 / P-7 / P-9 / P-10 구체화)

### 7-1. API URL 보존

| 카테고리 | 기존 URL | 분리 후에도 동일 URL 유지 |
|---|---|---|
| 예약 | `/api/appointments[/...]` | ✅ |
| 환자 | `/api/patients[/...]` | ✅ |
| 직원 | `/api/employees[/...]` | ✅ |
| 치료사 alias | `/api/therapists`, `/api/therapist-leaves[/bulk-set]` | ✅ — 호환 alias 보존 |
| 휴무 | `/api/employee-leaves[/...]` | ✅ |
| 치료항목 | `/api/treatments[/...]`, `/api/treatment-meta` | ✅ |
| 통계 | `/api/stats/*`, `/api/manual-counts`, `/api/export/*.xlsx` | ✅ |
| SMS | `/api/sms/*` | ✅ |
| 관리자 | `/api/admin/*`, `/api/about/*`, `/api/config/*`, `/api/system-settings`, `/api/audit-logs` | ✅ |
| 백업 | `/api/backup/*`, `/api/restore`, `/api/data-convert/*` | ✅ |
| AI | `/api/ai/*` (13개) | ✅ |
| sync | `/api/sync/{pull,push,now}` | ✅ |

→ FastAPI APIRouter 의 `prefix` 만 모듈별로 재할당 — URL 변경 0.

### 7-2. 응답 키 보존

§21 ([19_refactor_current_state.md](19_refactor_current_state.md)) 의 33+키 셋 모두 보존.

→ 비-AI 응답 키 (C-1~C-7) 는 분리 *직전* 별도 contract 테스트 추가 후 잠근다. 본 19-P-2 단계에서는 **현재 응답을 통째로 dict 단위로 보존** 정책만 명시.

### 7-3. DB schema 보존

- m001~m013 diff 0.
- 신규 마이그레이션 m014+ 는 본 19-P 기간 내 미도입. (필요 시 별도 세션)
- 컬럼 rename 금지 — 특히 `AiSetting`, `AiUsageLog`, `EmployeeLeave`, `Treatment.count_increment`, `Appointment.version`, `PatientTreatmentCount.{rx,done}_count`.
- ORM 19개 클래스명 보존.

### 7-4. UI 동작 보존

- [main.html](../../app/templates/main.html) 7331줄 + JS / CSS / FullCalendar 무수정.
- 프론트 fetch 호출 URL + 응답 키 그대로.
- AI 매뉴얼 Q&A 의존 키 5개 (`not_found` / `answer` / `confidence` / `sources[].title` / `sources[].path`) 보존.

### 7-5. 하네스 / 테스트 보존

- 529 passed baseline 유지. 분리 후 회귀 0.
- `tests/conftest.py` 4단계 격리 약화 금지.
- `tests/harness/*.py` 12 모듈 (~1420줄) 그대로.
- FakeProvider / FakeEmbeddingProvider 컨벤션 (`len(.calls)`) 보존.
- 분리 단계마다 **분리 직전**: 도메인별 contract 테스트 신규 추가 → **분리 직후**: 회귀 통과 확인.

### 7-6. PyInstaller 배포 안정성

- `dosu_clinic.spec` hidden imports 매 분리마다 동기화 (신규 modules 경로 추가).
- [test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) 53 tests 통과 유지.
- `collect_submodules` 실패 가드 + migrations 자동 글롭 + updater.bat post-build 복사 정책 그대로.
- excludes (tkinter/matplotlib/numpy/pandas/PyQt5/6) 그대로.

### 7-7. AI/RAG local-first 보존

- 18-0 `_block_sdk_modules` 정책 그대로.
- `local_only` 모드에서 `len(provider.calls)==0` + `len(embedding_provider.calls)==0` 단언 유지.
- `should_call_llm()` 다층 게이트 (provider_disabled / pii / local_only / no_sources / low_confidence) 보존.
- 외부 LLM/Embedding 호출은 운영 환경 + 사용자 명시 활성화에서만.
- RAG 가 환자/예약 DB 임의 생성 금지 (modules/ai/rag → modules/appointments 의존성 ❌).

---

## 8. 단계적 이동 원칙

### 8-1. 모듈 1개당 1세션 1커밋 원칙

```
1. 사전: 도메인별 contract 테스트 신규 추가 (응답 키 잠금)
2. 사전: 회귀 baseline 확인 (529 passed)
3. 신규 modules/<domain>/ 폴더 + router/service/repository/schemas 생성
4. 기존 api.py 의 해당 도메인 함수를 modules/<domain>/service 에 위임 (wrapper 패턴)
5. main.py 에 신규 router include (기존 router 와 둘 다 활성)
6. 회귀 테스트 통과 확인 (529 passed + 신규 contract tests)
7. 기존 api.py 에서 해당 도메인 함수 + endpoint 제거
8. 다시 회귀 테스트 — 응답 동일 입증
9. dosu_clinic.spec hidden imports 갱신 + test_pyinstaller_hidden_imports.py 53 tests 통과
10. ruff + check_db_path 통과
11. Codex 검증 → 통과 시 다음 모듈
```

### 8-2. 5회 루프 정책 적용

각 단계에서 회귀 실패 시 [docs/AI_WORKING_RULES.md §3](../AI_WORKING_RULES.md) 5회 루프:
- 5회 안에 통과 → 성공 리포트 + Codex 검증.
- 5회 실패 → **rollback** (해당 모듈 분리 취소) + `latest_failure_report.md` + 사용자 결정.

### 8-3. wrapper / adaptor 패턴

분리 *전* 단계에서 새 모듈은 wrapper:

```python
# modules/appointments/service.py (신규)
from app.routers.api import _bump_patient_count as _legacy_bump
def bump_patient_count(*args, **kwargs):
    return _legacy_bump(*args, **kwargs)
```

→ 내부 구현은 점진적으로 이동. 기존 api.py 함수는 wrapper 가 안정화될 때까지 유지.

### 8-4. rollback 가능성

각 분리 commit 은:
- 신규 폴더/파일 추가만 (DB 마이그레이션 동반 X).
- 기존 응답 키 / URL / 동작 변경 X.
- `git revert <commit>` 1회로 이전 상태 복원 가능.

---

## 9. 모듈 분류표

> 컬럼: 기능/책임 · 현재 위치 · 목표 위치 · 분류 · 분리 난이도 · 위험도 · 선행 테스트 · 관련 API · 관련 DB · 관련 UI · 주의사항.

분류 기호:
- **A**: 즉시 분리 (19-P 안에 처리)
- **B**: 기존 모듈 하위 책임 (다른 모듈로 흡수)
- **C**: 후속 검토 (19-P 비-목표)

난이도 / 위험도: 1 (낮음) ~ 5 (높음)

| ID | 기능/책임 | 현재 위치 | 목표 위치 | 분류 | 난이도 | 위험도 | 선행 테스트 | 관련 API | 관련 DB | 관련 UI | 주의사항 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M-01 | 예약 CRUD + 충돌 + 락 | api.py:1608-2057 | modules/appointments/ | A | 4 | 4 | 응답 키 contract + 점심창 + 낙관적 락 | /api/appointments/* | Appointment / TreatmentAssignment | 예약탭 + FullCalendar | 다른 도메인 의존 多 (patients/therapists/treatments/leaves) — 분리 마지막 권장 |
| M-02 | 환자 CRUD + 검색 + 메모 + 카운트 | api.py:1280-1607 | modules/patients/ | A | 3 | 3 | 응답 키 contract + 검색 인덱스 | /api/patients/* | Patient / PatientTreatmentCount | 환자탭 | data-convert 와 분리 — _dc_* 헬퍼는 export_import 로 |
| M-03 | 직원 CRUD (doctor + therapist 통합) + alias | api.py:1009-1208 | modules/staff/ | A | 2 | 2 | 응답 키 contract + therapist_id alias + role 분기 | /api/employees, /api/therapists | Employee | 직원탭 | alias 응답 키 (therapist_id 이중) 보존 + role="doctor"/"therapist" 분기 시드 정합 (constants.py SEED_TREATMENTS) |
| M-03b | 의사 전용 분기 (`_doctor_codes_set`, `is_doctor_filter`, role=doctor handler 검증) | api.py:153-156, 1773-1775, 3464+3491-3527, 4339-4465 | modules/staff/doctors_service.py | B | 2 | 3 | 의사 항목 배정 role 강제 회귀 + 통계 필터 회귀 | (서버측 헬퍼) | Employee + Treatment.role | 통계탭 의사 필터 | M-03 staff 모듈 하위 — 별도 modules/doctors/ 분리는 **후속 검토** (EMR 연동 도입 시) |
| M-04 | 휴무 CRUD + AI 단일 진실원천 | api.py:1082-1170, services/ai/action_leave.py | modules/leaves/ | A | 3 | 4 | 응답 키 contract + AI action_leave 회귀 | /api/employee-leaves/*, /api/therapist-leaves/* | EmployeeLeave | 직원탭 (휴무 표시) | _upsert_employee_leave_core 가 AI 자연어 휴무에서도 호출 — 시그니처 절대 보존 |
| M-05 | 치료항목 CRUD + 메타 | api.py:858-1008 | modules/treatments/ | A | 2 | 3 | count_increment 정책 + manual60=1 | /api/treatments/*, /api/treatment-meta | Treatment | 관리자탭 | manual60 count_increment=2 로 절대 되돌리지 않을 것 |
| M-06 | 완료체크 / done_count 증감 | api.py:1934 + 1956-2005 | modules/treatments/completion_rules.py | B | 3 | 4 | approve / revert 회귀 | /api/appointments/{aid}/{approve,revert-approve} | PatientTreatmentCount | (서버측) | _bump_patient_count 정책 보존 — Lazy 생성 + 0 미만 방지 |
| M-07 | 통계 8 GET + 엑셀 export | api.py:3450-5127 | modules/stats/ + export_import/ | A | 4 | 3 | 8 endpoint 응답 키 contract + 카운트 정책 | /api/stats/*, /api/export/*.xlsx | ManualCount, Appointment | 통계탭 | _get_manual_treatment_rows / _doctor_codes_set 등 헬퍼 다수 — 의존성 그래프 정리 필요 |
| M-08 | 수동 카운트 upsert | api.py:3883-3942 | modules/stats/service.py | B | 1 | 2 | 응답 키 contract | /api/manual-counts | ManualCount | 통계탭 | (count_date, therapist_id, treatment_code) UNIQUE 보존 |
| M-09 | SMS 설정 + 템플릿 + 발송 + 대상자 | api.py:2927-3449 | modules/sms/ | A | 4 | 4 | 발송 결과 contract + munjanara_key 마스킹 | /api/sms/* | SmsSetting / SmsLog / SmsTemplate | 문자탭 | 외부 munjanara API 호출 — provider.py 로 분리 시 timeout/응답 디코딩 정책 보존 |
| M-10 | 관리자 인증 + 비번 변경 | api.py:224-269, services/auth.py | core/security.py + modules/admin/ | A | 2 | 4 | 로그인 5회 잠금 + 세션 TTL 회귀 | /api/admin/* | (config.json) | (서버측) | 모든 admin endpoint 가 의존 — core/security 위치 결정이 우선 |
| M-11 | 자동 백업 + 수동 백업 + 복원 | services/backup.py + api.py:2159-2906 | modules/backup/ | A | 3 | 5 | 복원 후 DB 정합 + audit 폴백 | /api/backup/*, /api/restore | (backups/*.db) | 관리자탭 | engine.dispose() + atomic rename 정책 보존. 복원 중 다른 작업 차단 후속 검토 |
| M-12 | 엑셀 환자 import (data-convert) | api.py:2258-2855 (~600줄) | modules/export_import/ | A | 3 | 3 | 변환 결과 contract + 중복 검사 | /api/data-convert/* | Patient | 관리자탭 | _dc_* 헬퍼 ~400줄 — 단일 모듈로 통째 이동 권장 |
| M-13 | sync (분산 노드) | services/sync.py + api.py:2098-2158 | modules/sync/ (또는 services/sync 그대로) | C | 4 | 5 | sync_pull / push 회귀 + ENTITY_MAP 호환 | /api/sync/* | SyncOp + 모든 도메인 모델 | 상단 동기화 버튼 | ENTITY_MAP 9개 키 (treatment_assignment / patient_treatment_count / employee_leave 등) 외부 노드 호환 — 분리 시 키 절대 보존 |
| M-14 | 감사 로그 (AuditLog insert) | api.py:110-127 (audit, _log) | modules/audit/ | A | 1 | 2 | 모든 CUD 액션 회귀 | /api/audit-logs | AuditLog | 관리자탭 | audit() 시그니처 보존 — 모든 모듈에서 호출 |
| M-15 | 시스템 설정 (SystemSetting) | api.py:2058-2096 | modules/settings/ | A | 1 | 2 | 응답 키 contract | /api/system-settings | SystemSetting | 관리자탭 | manual_slot_limit / auto_backup_* 보존 |
| M-16 | 자동 업데이트 (about/check/download/apply) | api.py:271-668 | modules/admin/ (하위) 또는 modules/updates/ | A | 3 | 4 | check-update 응답 키 + apply-update 안전성 | /api/about/* | (config.json) | 관리자탭 | updater.bat 결합 + PyInstaller post-build copy 보존 |
| M-17 | AI 라우터 13 endpoint | routers/ai.py | modules/ai/router.py | A | 3 | 4 | 응답 키 33+ contract + local-first | /api/ai/* | AiSetting / AiUsageLog | AI 도우미 탭 | 4개 부도메인 (settings/sms/manual/action) — 단일 router 유지 vs 분리 결정 필요 |
| M-18 | AI action_leave (자연어 휴무) | services/ai/action_leave.py (917줄) | modules/ai/commands/action_leave.py | A | 4 | 5 | parse/preview/execute 회귀 + HMAC 토큰 + TOCTOU | /api/ai/action/* | EmployeeLeave (write via leaves.service) | AI 도우미 탭 | 토큰 + 락 + leaves.service._upsert_employee_leave_core 의존 — 분리 시 정책 절대 보존 |
| M-19 | AI 18-7 status 본체 | services/ai/health.py (563줄) | modules/ai/health.py | B | 1 | 2 | /api/ai/status 9키 contract | /api/ai/status | AiSetting / AiUsageLog / KnowledgeChunk / KnowledgeVector | 관리자탭 | ERROR_DETAIL_DISPLAY_LIMIT=200 + PII 마스킹 정책 보존 |
| M-20 | AI manual_qa wrapper | services/ai/manual_qa.py (78줄) | modules/ai/manual_qa.py | B | 1 | 1 | 시그니처 + 9키 응답 contract | /api/ai/manual/{search,ask} | (없음) | (서버측) | provider_override= 키워드 인자 + LOW_SCORE_THRESHOLD 노출 보존 |
| M-21 | AI sms_draft + validators | services/ai/{sms_draft,validators}.py | modules/ai/sms_*.py | A | 2 | 3 | sms validate/draft 회귀 | /api/ai/sms/* | SmsSetting | 문자탭 | LLM 호출 + 결정론적 검증 분리 보존 |
| M-22 | AI provider / openai_client / anthropic_client | services/ai/{provider,openai_client,anthropic_client}.py | modules/ai/provider/ | A | 2 | 2 | get_provider 시그니처 + KNOWN_PROVIDERS | (서버측) | AiSetting | (서버측) | lazy import + AiUnavailable / AiPiiBlocked 예외 보존 |
| M-23 | AI rag/knowledge/vector 패키지 | services/ai/{rag,knowledge,vector}/ | modules/ai/{rag,knowledge,vector}/ (그대로) | A | 1 | 2 | 18-0~18-6 회귀 | (없음 — 내부 호출만) | KnowledgeChunk / KnowledgeIndexRun / KnowledgeVector | (서버측) | LOW_SCORE_THRESHOLD / HIGH/LOW THRESHOLD / QUERY_MIN_CHARS / vector lazy import 보존 |
| M-24 | AI 로깅 (AiUsageLog insert) | services/ai/ai_logging.py | modules/ai/logging.py | B | 1 | 2 | 회귀 — log_ai_usage 시그니처 | (서버측) | AiUsageLog | (서버측) | sha256 해시만 저장 + 원문 미저장 정책 보존 |
| M-25 | core 신설 (config / database / errors / responses / time_utils / security / feature_flags) | app/{config,database}.py + services/auth.py + (분산) | core/ | A | 3 | 3 | 모든 모듈 import 변경 → 회귀 | (없음) | (없음) | (없음) | core 가 modules 를 import 하지 않는 단방향 보장 |
| M-26 | calendar / view-model 분리 | (현재 main.html JS 안) | modules/calendar/ (후속) | C | 5 | 5 | UI 분리 — 19-P 비-목표 | (none) | Appointment | 예약탭 FullCalendar | 19-P 기간 내 미도입 |
| M-27 | notes 통합 (지속/당일 메모) | (현재 Patient.memo + Appointment.memo) | modules/notes/ (후속) | C | 3 | 3 | 정책 결정 후 | /api/patients/{pid}/memo | Patient.memo / Appointment.memo | 환자탭 / 예약 모달 | 정책 결정 미완 — 후속 |
| M-28 | /api/health (서버 상태) | (현재 부재) | modules/health/router.py (신규) | C | 2 | 2 | (신규) | /api/health (신규) | (없음) | (없음) | 추가 결정 필요 — /api/ai/health 와는 별개 |
| M-29 | sms/provider 외부 client | api.py:3225 inline | modules/sms/provider.py | A | 3 | 4 | sms_send 응답 디코딩 + 마스킹 | (서버 내부) | (없음) | (없음) | 문자나라 외부 API timeout / 응답 코드 디코딩 보존 |
| M-30 | feature_flags 통합 | (분산 — AiSetting + 환경변수) | core/feature_flags.py | A | 2 | 2 | ai_mode / search_mode 파생 회귀 | /api/ai/status | AiSetting | (서버측) | ai_mode (local_only/local_first/ai_assist) 단일 진실원천 보존 |
| M-31 | doctors 별도 모듈 분리 (EMR 연동 도입 시) | (현재 부재 — M-03b 가 staff 안에서 처리) | modules/doctors/ (후속) | C | 4 | 4 | (신규 — m014+ 마이그레이션 + 응답 키 contract) | /api/doctors/* (신규) | Doctor (m014+ 신설) | 직원탭 / 진료탭 (신규) | 진료과 / 진료실 / 담당의 / 의사별 일정 / 오더 / 처방 / EMR 연동 — 19-P 비-목표 |
| M-32 | 환자 담당의 연결 (Patient.doctor_id) | (현재 부재) | modules/patients/ + Patient 모델 변경 (후속) | C | 3 | 4 | (신규 — m014+ 컬럼 추가) | /api/patients/{pid} (응답 키 추가) | Patient.doctor_id (m014+) | 환자탭 | DB 마이그레이션 + 응답 키 추가 + UI 변경 동반 — 별도 세션 |
| M-33 | 진료실 / 자원 (resources) | (현재 부재) | modules/resources/ (후속) | C | 4 | 3 | (신규) | /api/resources/* (신규) | Resource (m014+ 신설) | (UI 신설) | §4 resources 항목과 동일 — 후속 검토 |
| M-34 | 의사별 진료 일정 (Doctor schedule) | (현재 부재 — Appointment 단일 테이블) | modules/doctors/schedule_service.py (후속) | C | 4 | 4 | (신규 — 진료 예약 vs 도수치료 예약 경계 결정 후) | /api/doctors/{id}/schedule (신규) | DoctorSchedule (m014+ 신설) 또는 Appointment 확장 | 예약탭 / 진료탭 (신규) | 진료 예약과 도수치료 예약의 경계 정책 결정 필요 — §3-1 후속 |
| M-35 | 오더 / 처방 (EMR Order/Prescription) | (현재 부재) | modules/emr/ (후속) | C | 5 | 5 | (신규 — EMR 연동 ADR 필요) | /api/orders/* (신규) | Order / Prescription (m014+ 신설) | (UI 신설) | 비트U차트 등 외부 EMR 연동 경계 — 본 19-P 비-목표 |
| M-36 | AI 의사/진료진 정보 hallucination 가드 | services/ai/rag/safety.py + manual_qa validate (현재 부분) | modules/ai/safety/medical_guard.py (후속) | C | 3 | 4 | 의사 단정 표현 차단 회귀 (`담당의는 X` / `Y 의사 진료실` 등) | /api/ai/manual/ask | (없음 — guard 패턴) | (서버측) | 현재 `_RE_MEDICAL_CLAIM` 의료 단정 차단만. 의사 이름/진료과 단정은 별도 패턴 필요 — 후속 검토 |

### 9-1. 즉시 분리 (A) 우선순위 권장

| 순서 | 모듈 | 사유 |
|---|---|---|
| 1 | M-25 core | 모든 모듈이 core 에 의존 — 가장 먼저. import 경로 변경만, 위험도 낮음. |
| 2 | M-14 audit | 모든 CUD 가 호출하는 단순 함수 — 가장 안전. |
| 3 | M-15 settings | SystemSetting 단일 — 가장 단순. |
| 4 | M-03 staff (+M-03b doctors_service 통합) | 환자/예약 의존이 적은 도메인. doctor + therapist 분기를 service 안에서 통합. |
| 5 | M-05 treatments + M-06 completion_rules | manual60 / count_increment 정책 보존. |
| 6 | M-04 leaves + M-18 ai/commands/action_leave | _upsert_employee_leave_core 보존. AI action_leave 와 한 묶음. |
| 7 | M-02 patients + M-12 export_import | data-convert 분리. |
| 8 | M-08 + M-07 stats | 헬퍼 의존성 그래프 정리 후. |
| 9 | M-09 + M-29 sms | sms.provider 분리 포함. |
| 10 | M-21 ai sms_draft / validators | M-09 과 함께. |
| 11 | M-11 backup + M-16 about/updates | 자동 업데이트 묶음. |
| 12 | M-17 + M-19 + M-20 + M-22 + M-23 + M-24 ai modules | AI 라우터 + health + manual_qa + provider + rag/knowledge/vector + logging. |
| 13 | M-30 feature_flags | core 기반 — AI 분리 후. |
| 14 | M-01 appointments | **마지막** — 다른 도메인 의존 多. 모든 도메인 분리 후 참조 가능 상태에서 분리. |

### 9-2. 후속 검토 (C) 항목

| ID | 항목 | 사유 |
|---|---|---|
| M-13 | sync (분산 노드) | ENTITY_MAP 외부 노드 호환 — 분리 위험. 별도 ADR 필요. |
| M-26 | calendar / view-model | UI 분리는 19-P 비-목표 (별도 UI 세션). |
| M-27 | notes 통합 | 지속/당일 메모 정책 미결정. |
| M-28 | /api/health 신규 | 추가 결정 필요. |
| M-31 | doctors 별도 모듈 | EMR 연동 도입 시 — 진료과/진료실/담당의/의사별 일정. m014+ 마이그레이션 동반. |
| M-32 | 환자 담당의 연결 (Patient.doctor_id) | EMR 연동 또는 담당의 운영 정책 결정 후. m014+ 컬럼 + 응답 키 + UI 동반. |
| M-33 | resources (진료실 / 장비) | 자원 관리 도입 시. 현재 미구현. |
| M-34 | 의사별 진료 일정 (Doctor schedule) | 진료 예약 vs 도수치료 예약 경계 정책 결정 후. |
| M-35 | 오더 / 처방 (EMR) | 비트U차트 등 외부 EMR 연동 경계 — 별도 ADR + 보안 검토. |
| M-36 | AI 의사/진료진 hallucination 가드 보강 | 의사 이름 / 진료과 단정 표현 차단 패턴 추가 — AI safety 보강 시점. |

---

## 10. 보류 / 후속 항목 정리

| 항목 | 보류 사유 | 후속 시점 |
|---|---|---|
| 실제 코드 이동 | 본 19-P-2 는 설계 문서 세션 — 코드 무수정 | 19-P-3 (모듈 매핑) → 19-P-4+ (모듈 1개씩 이동) |
| DB schema 변경 | m014+ 미도입 | 별도 세션 (예: 노쇼 컬럼 추가 시) |
| UI 구조 변경 | main.html / app.css 분리 | 별도 UI 분리 세션 (19-P 비-목표) |
| 미구현 기능 (printing / notifications / recurring / resources) | 현재 부재 | 사용자 결정 필요 — 본 문서는 후속 검토 분류만 |
| 의사 EMR 연동 (진료과 / 진료실 / 담당의 / 의사별 일정 / 오더 / 처방 / 비트U차트 연동) | 현재 부재. M-31~M-35 + M-36 모두 후속 검토 | 사용자 결정 필요 — 별도 ADR + DB 마이그레이션 + UI 변경 동반. 본 19-P 비-목표 |
| `docs/ai_rag_current_state.md` stale 보정 | §24 caveat 만으로 19-P 사용 가능 | 별도 문서 갱신 세션 (Codex r2 §3 권고) |
| 18-0~18-8 변경분 main 머지 | baseline 미커밋 → G-1 caveat | 사용자 결정 (Codex r2 §3 권고) |

---

## 11. 확인 필요 항목

> 본 19-P-2 세션 안에서 단정 짓지 못한 항목.

| ID | 항목 | 사유 / 다음 검증 시점 |
|---|---|---|
| T-1 | `modules/admin/` vs `modules/settings/` 경계 — `AiSetting` 갱신은 어느 모듈? | 현재 `/api/ai/settings` 는 `modules/ai/router.py` 가 보유. settings 모듈은 SystemSetting 만 담당? 19-P-3 결정. |
| T-2 | `modules/ai/router.py` 단일 vs 부도메인별 분리 | 13 endpoint = 4 부도메인 (settings/sms/manual/action) — 단일 router 가 관리 부담일지, 부도메인 라우터로 나눌지. 19-P-3 결정. |
| T-3 | `modules/sync/` vs `services/sync.py` 위치 | sync 는 도메인이 아니라 인프라 — `core/sync.py` 또는 그대로 두기. 19-P-3 결정. |
| T-4 | `modules/health/router.py` 의 `/api/health` 신규 추가 여부 | 현재 부재. 추가 시 `/api/ai/health` 와 명확히 분리. 사용자 결정 필요. |
| T-5 | wrapper 패턴 보유 기간 | 분리 후 wrapper 가 언제까지 살아있어야 하는지 — 같은 세션 내 제거 vs 다음 세션 제거. 19-P-3 결정. |
| T-6 | `modules/ai/safety/` 디렉토리화 | 현재 `rag/safety.py` 50줄 — pii / hallucination_guard 분리 시점. 18-1~18-6 구조 그대로 유지가 더 안전할 수도. 19-P-3 결정. |
| T-7 | `modules/calendar/` UI view-model | main.html 7331줄 단일 script 분리 가능성 — 19-P 비-목표지만 view-model 만 서버 사이드로 빼는 안 후속 검토. |
| T-8 | `core/feature_flags.py` 의 환경 변수 vs DB | AI_RAG_ENABLED 등은 환경 변수 + AiSetting 둘 다 사용 — 단일 진실원천 결정 필요. 19-P-3 결정. |
| T-9 | `services/sync.py:ENTITY_MAP` 9개 키 변경 가능 여부 | 외부 노드 호환 위해 키 그대로 유지 — 분리 시 모듈 위치 변경에도 ENTITY_MAP 키 보존 절대 필요. 19-P-3 명시. |
| T-10 | 비-AI 응답 키 86개 endpoint 매트릭스 | 19-P-1 §22 C-1 — 도메인 분리 *직전* 별도 보강. 19-P-4+ 도메인 별 분리 직전 작성. |
| T-11 | `data-convert` 의 분리 단위 | api.py:2258-2855 ~600줄 — 단일 service.py vs 세분화. 19-P-3 결정. |
| T-12 | wrapper 단계의 라우터 중복 등록 안전성 | 같은 URL 두 router 가 등록될 경우 FastAPI 동작 — 분리 직전 검증 필요. 19-P-4+ 구현 시점. |
| T-13 | `modules/staff/` 단일 vs `modules/staff/{doctors,therapists}/` 서브 디렉토리 | 현재 Employee 단일 모델이라 단일 staff 권장. 단, EMR 연동 도입 시 doctors 서브 디렉토리로 분리 검토. 19-P-3 결정. |
| T-14 | 의사 알림 / 시드 정책 | `services/seed.py:_seed_demo_data` 가 의사 2명 시드를 포함하지만 현재 비활성화 (line 21 주석). 운영 환경에서 의사 시드는 사용자 수동 등록. 본 정책 보존 — 단위화 후에도 시드 자동 활성화 금지. |
| T-15 | AI hallucination 가드 의사 단정 패턴 추가 시점 | `_RE_MEDICAL_CLAIM` 에 의사 이름 / 진료과 단정 표현 추가는 AI safety 보강 시점에 별도 결정. M-36 항목. |

---

## 12. 종합

- 19-P 단위화 후 도달할 V2 구조: `app/main.py` + `app/core/` + `app/modules/{appointments,patients,staff,leaves,treatments,stats,sms,admin,backup,ai,audit,settings,export_import}/` (총 **modules 13개** + `core/`).
- `app/services/` 는 `modules/` 내부로 흡수 (auth → core/security, backup → modules/backup, ai/* → modules/ai/, sync → modules/sync 또는 그대로).
- `app/routers/api.py` 5127줄 / 86 endpoint 는 도메인별로 단계 이동 후 facade or 폐기.
- §9 분류표 합계 = **37행** (M-01~M-36 + M-03b). 분류 카운트:
  - **즉시 분리 (A): 21개** — M-01 / M-02 / M-03 / M-04 / M-05 / M-07 / M-09 / M-10 / M-11 / M-12 / M-14 / M-15 / M-16 / M-17 / M-18 / M-21 / M-22 / M-23 / M-25 / M-29 / M-30
  - **기존 모듈 하위 책임 (B): 6개** — M-03b / M-06 / M-08 / M-19 / M-20 / M-24
  - **후속 검토 (C): 10개** — M-13 sync / M-26 calendar / M-27 notes / M-28 /api/health / M-31 doctors EMR / M-32 patient.doctor_id / M-33 resources / M-34 doctor schedule / M-35 EMR orders / M-36 AI 의사 가드
- **의사 / 진료진 관련 책임은 현재 `Employee.role="doctor"` + `Treatment.role="doctor"` 분기로만 존재** — 별도 `modules/doctors/` 분리는 EMR 연동 도입 시 후속 검토 (M-31). 본 19-P 에서는 `modules/staff/doctors_service.py` (얇은 분기) 로 통합.
- AI/RAG 18-0~18-6 패키지는 위치 이동만 (`services/ai/{rag,knowledge,vector}` → `modules/ai/{rag,knowledge,vector}`) — 내부 구조 무수정. local-first 원칙 + LOW_SCORE_THRESHOLD / HIGH/LOW THRESHOLD / QUERY_MIN_CHARS 보존.
- AI 명령에서 의사 / 진료진 정보 임의 생성 금지 — RAG hallucination guard 와 동일 정책 (§3-10). 의사 단정 표현 패턴 추가는 후속 (M-36).
- 분리 *직전* 도메인별 contract 테스트 추가 → wrapper → 내부 위임 → 기존 코드 제거 → 회귀 통과 확인 → Codex 검증 → 다음 모듈.
- 5회 루프 실패 시 rollback. baseline `bcd74a7` 위에서 단방향 진행 — DB 마이그레이션 없이 단계 분리만.
- 다음 문서: `docs/refactor/19_refactor_module_mapping.md` (19-P-3) — 본 §9 분류표를 1:1 코드 매핑으로 구체화 (현재 함수/라인 → 목표 모듈/파일/함수).
