# 20-P-2 post-19-P 그룹 C 상세 기획 (20_post_19p_group_c_detail_plan)

> 20-P-1 [마스터 플랜](20_post_19p_master_plan.md) Codex 검증 caveat 정합 — "그룹 C/D 는 진입 전 별도 상세 기획 권장".
> 본 문서는 *그룹 C 5개 항목 (F-10 / F-11 / F-1 / F-2 / F-3) 의 상세 기획* — read-only 문서 세션.
> 실제 코드 / 마이그레이션 / 테스트 / fixture / mock 미생성.

## 0. 메타

- 작성일: 2026-05-04
- 기준 브랜치: `ai-rag-v1-integration`
- 직전 commit: `2a7f533` (20-2 그룹 B)
- 20-2 baseline: **1726 passed / 1 skipped / 10 xfailed**
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.

### 0-1. 본 문서가 다루지 않는 범위

- 그룹 D 4개 항목 (F-4 / F-5 / F-6 / F-9) 상세 기획 — 별도 문서 (`20-P-3 group_d_detail_plan.md`).
- 실제 코드 / 마이그레이션 / 테스트 작성 — 20-3-1 ~ 20-3-5 분할 세션에서 처리.
- 사용자 정책 결정 *최종 답* — 본 §3 ~ §7 에 후보만 정리.

### 0-2. 본 문서의 위치

- 20-P-1 = 부재 항목 15개 도입 마스터 플랜 (Codex 통과).
- **20-P-2 (본 문서) = 그룹 C 5개 항목 상세 기획.**
- 20-3-1 ~ 20-3-5 = 그룹 C 분할 진입 (실제 코드 + 마이그레이션 + 테스트).

---

## 1. 그룹 C 5개 항목 개요 + 의존성

| 항목 | 마이그레이션 | UI | 외부 호출 | 위험 |
|---|---|---|---|---|
| F-10 노쇼 별도 필드 | m014 (단일 컬럼) | ✓ (체크박스 + 통계 분기) | ✗ | 중간 |
| F-11 권한 다중 등급 | m015 (단일 컬럼) | ✓ (로그인 / 화면 분기) | ✗ | 중간 |
| F-1 doctors 도입 | m016 ~ m020 (5개) | ✓ (담당의 / 진료실 / 진료과) | ✗ | **높음** |
| F-2 반복 예약 | m021 (series 테이블) | ✓ (반복 패턴 입력) | ✗ | **높음** |
| F-3 자원 (치료실 / 장비) | m022 ~ m023 (2개) | ✓ (자원 선택 / 충돌) | ✗ | **높음** |

### 1-1. 그룹 C 내부 의존성

| 의존 | 설명 |
|---|---|
| F-1 (doctors) → F-15 강화 | 본 20-1 F-15 doctor_guard 는 *DB 근거 없는 의사 정보 차단* 만. F-1 도입 시 *DB 근거 있는 의사 정보* 가 생기므로 가드 정책 재검토 필요. |
| F-3 (자원) → F-2 (반복 예약) | 반복 예약이 자원 충돌 검사를 함께하려면 F-3 선행. F-2 단독 도입 가능 (자원 검사 ⊥). |
| F-10 (노쇼) → F-11 (권한) | 노쇼 통계 / 알림이 권한 등급 영향 받음. F-10 단독 도입 가능. |
| F-1 (doctors) ↔ F-11 (권한) | 의사 / 직원 / 관리자 권한 매트릭스 — F-1 / F-11 둘 다 결정 후에야 명확. |
| 모두 ↔ 통계 / 캘린더 / 응답 키 | 각 항목이 응답 dict / FullCalendar event 형식 / 통계 분기에 영향. |

### 1-2. 권장 진입 순서

1. **20-3-1 F-10 노쇼** — 단일 컬럼 m014, 가장 작은 변경.
2. **20-3-2 F-11 권한** — 단일 컬럼 m015, 화면 분기 추가만.
3. **20-3-3 F-1 doctors** — 5개 마이그레이션, 가장 큰 변경. **사용자 EMR 도입 범위 결정 필수**.
4. **20-3-4 F-2 반복 예약** — F-1 후 (담당의 반복 적용 가능).
5. **20-3-5 F-3 자원** — F-2 후 (자원 충돌 통합).

---

## 2. 공통 원칙 (그룹 C 모든 항목)

| # | 원칙 | 본문 |
|---|---|---|
| GC-1 | 기존 33+ 응답 key 보존 | `삭제 / rename ⊥` — 신설 key 만 추가. |
| GC-2 | 기존 API URL 보존 | 신설 endpoint 만 추가 (`/api/doctors`, `/api/notifications`, `/api/resources` 등). |
| GC-3 | 기존 m001~m013 변경 ⊥ | m014+ 만 신설. 기존 마이그레이션 역행 ⊥. |
| GC-4 | DB 컬럼 추가 시 NULL 허용 + 기본값 | 기존 row 가 깨지지 않도록 `Column(... nullable=True)` 또는 `DEFAULT` 명시. |
| GC-5 | 19-14 baseline 회귀 ⊥ | 1726 passed / 1 skipped / 10 xfailed 유지. |
| GC-6 | 운영 DB 보호 + 외부 API 호출 ⊥ | check_db_path / `_block_sdk_modules` 정합. |
| GC-7 | UI 변경 최소화 | 가능하면 main.html JS 무수정 (응답 dict 추가만). UI 분기는 별도 분할 가능. |
| GC-8 | PII 비노출 + audit_log 추가 | 새 컬럼 / 새 endpoint 가 PII 원문 응답 / 로그 / AI prompt 에 노출 ⊥. |
| GC-9 | 19-C 14 영역 작동확인 + 신규 O 영역 | 노쇼 / 권한 / 담당의 / 자원 / 반복 = O 영역 (20-P-1 §7-2). |
| GC-10 | Codex 검증 게이트 | 각 분할 (20-3-1 ~ 20-3-5) 마다 Codex 통과 후 다음. |

---

## 3. F-10 노쇼 별도 필드 — 20-3-1 상세

### 3-1. 현재 상태

- `Appointment.status` ENUM = `reserved` / `approved` / `canceled`. 노쇼 별도 필드 부재.
- 노쇼는 현재 `status="canceled"` + 메모 prefix `[취소]` 로만 표현 — *통계 / 알림 분기 부재*.

### 3-2. 도입 후보

| 후보 | 설명 | 영향 |
|---|---|---|
| (a) 별도 boolean | `Appointment.no_show=true` + `status="canceled"` 동시 | 통계 분기 추가만. 기존 status 정책 보존. **권장**. |
| (b) status ENUM 확장 | `canceled` / `no_show` 분리 | 기존 `status="canceled"` 분기 코드 다수 변경 — 회귀 多. |
| (c) 둘 다 | (a) + (b) 동시 도입 | 가장 안전하지만 schema 多. |

### 3-3. 마이그레이션 m014 (후보 (a) 기준)

```sql
ALTER TABLE appointments ADD COLUMN no_show BOOLEAN DEFAULT 0;
```

- 기존 row 모두 `no_show=False` 자동 세팅 (DEFAULT). 후방 호환 100%.
- 컬럼 추가만 — 기존 인덱스 / 제약 / 외래키 영향 0.
- 백업 / 복원 안전 — m001~m013 시점 백업 복원 시 컬럼 부재만 — `init_db()` 가 m014 실행 시 자동 추가.

### 3-4. 응답 dict / API URL 영향

- `_serialize_appointment` 응답 dict 에 `no_show: bool` 추가.
- 기존 키 (`id` / `patient_id` / ... / `version`) 보존.
- 신설 endpoint: `POST /api/appointments/{aid}/mark-no-show` (별도 trigger).
- 기존 `/api/appointments/{aid}/cancel` 에 `no_show` query param 추가 가능.
- FullCalendar event: extendedProps 에 `no_show` 추가.

### 3-5. UI 영향

- 예약 카드 모달: 노쇼 체크박스 추가.
- 통계 화면: 노쇼 통계 별도 항목.
- 알림: F-4 알림 도입 시 노쇼 알림 트리거 (그룹 D).

### 3-6. 통계 영향

- `/api/stats/aggregate` 응답에 `no_show_count` 추가.
- `/api/stats/by-therapist` / `/api/stats/by-treatment` 에 노쇼 분기 추가.
- 기존 `cancel_count` 와 *별도* 집계 — 사용자 결정 필요 (노쇼는 cancel 의 부분집합인가, 별도인가?).

### 3-7. 사용자 결정 필요 항목 (20-3-1 진입 전)

| 결정 | 후보 | 권장 |
|---|---|---|
| 도입 후보 | (a) boolean / (b) ENUM 확장 / (c) 둘 다 | (a) — 회귀 영향 최소 |
| 노쇼 → cancel 동시? | (i) `no_show=true` 이면 자동 `status="canceled"` (ii) 별개 | (i) — 통계 일관성 |
| 통계 집계 | (i) cancel 안에 노쇼 포함 (ii) 별도 항목 | (ii) — 노쇼 별도 통계 추적 |

### 3-8. 위험도

**중간**. 마이그레이션 1개 + 응답 키 추가 + UI 분기 + 통계 분기. 회귀 위험 = `_serialize_appointment` 호출지 多 (캘린더 / 검색 / 통계 / SMS 모두 의존).

### 3-9. 회귀 보호

- `_serialize_appointment` 응답 키 셋 + `no_show=False` 기본값 단언.
- FullCalendar event 형식 (기존 키 + `no_show` 추가) 단언.
- 통계 by-therapist / by-treatment 응답에 `no_show_count` 추가 단언.
- 19-3 calendar/view_models 회귀.

---

## 4. F-11 권한 다중 등급 — 20-3-2 상세

### 4-1. 현재 상태

- `Employee.role` = `therapist` / `doctor` 만 (의료 직군 분기).
- 관리자 권한 = `app/services/auth.py` 의 PBKDF2 + 5회 잠금 + 8h 세션 — *단일 등급* (admin only).
- `require_admin` 의존 86 endpoint 모두 admin 단일 권한.

### 4-2. 도입 후보

| 후보 | 등급 | 비고 |
|---|---|---|
| (a) 3등급 | staff / admin / super | 권장 — 직원 / 관리자 / 슈퍼관리자 |
| (b) 4등급 | viewer / staff / admin / super | viewer 는 읽기 전용 |
| (c) 더 세분화 | staff / scheduler / admin / accountant / super | 매트릭스 多, 화면 분기 多 |

### 4-3. 마이그레이션 m015 (후보 (a) 기준)

```sql
ALTER TABLE employees ADD COLUMN permission_level VARCHAR(20) DEFAULT 'staff';
```

- 기존 직원 모두 `staff` 자동. 기존 admin 로그인은 *관리자 비밀번호* 별도 필드 (`AdminCredential` 테이블) — 기존 동작 보존.
- 또는 별도 테이블 `EmployeePermission` 신설 — Employee 와 1:1 매핑.

### 4-4. 응답 dict / API URL 영향

- `_serialize_employee` 응답 dict 에 `permission_level: str` 추가.
- 신설 endpoint: `POST /api/admin/employees/{eid}/permission` (등급 변경).
- 기존 `/api/admin/login` 동작 보존 — admin 비밀번호 단일 게이트.

### 4-5. UI 영향

- 직원 관리 화면: 등급 select 추가.
- 로그인 후 권한별 화면 분기 (예: staff 는 통계 화면 접근 ⊥).
- F-15 의사 가드 → 권한 등급 정책 강화 (super 만 의사 정보 응답 가능 등).

### 4-6. 사용자 결정 필요 항목 (20-3-2 진입 전)

| 결정 | 후보 | 권장 |
|---|---|---|
| 등급 매트릭스 | (a) 3등급 (b) 4등급 (c) 세분화 | (a) — 가장 단순 |
| admin 별도 게이트 | (i) admin 로그인 + permission 둘 다 (ii) admin 통합 | (i) — 기존 admin 흐름 보존 |
| viewer 도입 여부 | (i) 도입 (ii) 미도입 | (ii) — 후속 결정 |

### 4-7. 위험도

**중간**. 마이그레이션 1개 + 화면 분기 추가. 회귀 위험 = `require_admin` 86 endpoint 의 권한 정책 변경 위험 — 기존 admin 단일 게이트 *반드시* 보존.

### 4-8. 회귀 보호

- `_serialize_employee` 응답 키 셋 + `permission_level='staff'` 기본값 단언.
- 기존 admin 로그인 / 5회 잠금 / 8h 세션 회귀 0.
- F-15 의사 가드 + 권한 등급 결합 회귀.

---

## 5. F-1 doctors 도입 — 20-3-3 상세

### 5-1. 현재 상태

- `Employee.role="doctor"` + `Treatment.role="doctor"` 얇은 분기만 (19-8 staff 안에 통합).
- `Doctor` 별도 테이블 / `Department` / `Room` / `DoctorSchedule` / `Patient.doctor_id` 부재.
- 본 시스템 = *도수치료 전문* — 의사 기능은 *가벼운 분기* 만 (`_doctor_codes_set` = `injection` / `cartilage`).

### 5-2. 도입 후보 — **사용자 EMR 결정 필수**

| 후보 | 설명 | 마이그레이션 |
|---|---|---|
| (a) Employee 확장 | `Employee.role="doctor"` 그대로 + `Doctor` 별도 테이블 신설 | m016 (Doctor) |
| (b) Doctor 별도 테이블 + Department + Room + Schedule + Patient.doctor_id | 풀 EMR 도입 | m016~m020 (5개) |
| (c) **패스** (현재 도수치료 전문 유지) | 의사 기능 추가 ⊥ — F-1 본 사이클 진입 X | 0 |

### 5-3. 사용자 EMR 도입 범위 — 결정 우선

본 시스템이 *도수치료 전문* 인지 *EMR 도입 의도* 가 있는지에 따라:

- **결정 (a)**: EMR 미도입 / 도수치료 전문 유지 → **F-1 패스** + post-20 후속.
- **결정 (b)**: EMR 도입 의도 있음 → 풀 5개 마이그레이션 진행.
- **결정 (c)**: 가벼운 의사 기능만 추가 → m016 (Doctor) 만 + Department / Room 부재 유지.

### 5-4. 마이그레이션 m016 ~ m020 (후보 (b) 풀 EMR)

| # | 테이블 | 컬럼 |
|---|---|---|
| m016 | `Doctor` | id / name / department_id / specialty / license_no / created_at |
| m017 | `Department` | id / name / code |
| m018 | `Room` | id / department_id / name / capacity |
| m019 | `DoctorSchedule` | id / doctor_id / weekday / start_time / end_time / room_id |
| m020 | `Patient.doctor_id` | FK 추가 (담당의) |

### 5-5. 응답 dict / API URL 영향

- 신설 endpoint: `/api/doctors` / `/api/departments` / `/api/rooms` / `/api/doctor-schedules`.
- `Patient` 응답에 `doctor_id` / `doctor_name` 추가.
- `Appointment` 응답에 `doctor_id` 추가 (담당의 분기).
- F-15 의사 가드 → `Doctor` 테이블 기반 *DB 근거 검증* 가능 (현재 가드 = DB 근거 없는 차단만).

### 5-6. UI 영향

- 환자 카드 / 예약 카드 / 캘린더에 담당의 표시.
- 의사 관리 화면 신설 (CRUD).
- 진료실 / 진료과 관리 화면.

### 5-7. 사용자 결정 필요 항목 (20-3-3 진입 전 — 가장 큰 결정)

| 결정 | 후보 | 비고 |
|---|---|---|
| EMR 도입 범위 | (a) 패스 (b) 풀 EMR (c) 가벼운 의사만 | **가장 중요** — 본 시스템 정체성 결정 |
| Doctor ↔ Employee 관계 | (i) 별도 테이블 (ii) Employee.role="doctor" 확장 | (b) 풀 EMR 시 (i) 권장 |
| 진료과 (Department) 도입 | (i) 도입 (ii) 미도입 | (b) 풀 EMR 시 (i) |
| 진료실 (Room) 도입 | (i) 도입 (ii) 미도입 | F-3 자원 (Room) 과 충돌 가능 — 사용자 결정 |
| 의사 일정 (Schedule) 도입 | (i) 도입 (ii) 미도입 | EmployeeLeave 와 통합 / 별도 결정 |
| F-15 가드 강화 | (i) DB 근거 기반 검증 추가 (ii) 현재 가드 유지 | (i) 권장 |

### 5-8. 위험도

**높음**. 5개 마이그레이션 + 응답 키 추가 多 + UI 분기 多 + F-15 가드 강화. 본 시스템 정체성 변경 가능 (도수치료 전문 → 일반 진료).

### 5-9. F-1 패스 결정 시

사용자가 EMR 미도입 결정 시:
- F-1 본 사이클 진입 X.
- F-15 doctor_guard 는 현재 상태 유지 (DB 근거 없는 차단만).
- F-2 반복 예약 / F-3 자원은 F-1 없이 단독 도입 가능.
- 후속 (post-20-x) 으로 미룸.

---

## 6. F-2 반복 예약 — 20-3-4 상세

### 6-1. 현재 상태

- 예약 = 1건 단위. 반복 예약 부재.
- 같은 환자 여러 예약 = *수동* 만 (1건씩 등록).

### 6-2. 도입 후보

| 후보 | 패턴 | 마이그레이션 |
|---|---|---|
| (a) 단순 N회 반복 | "X일 간격으로 N회" | m021 (`AppointmentSeries`) |
| (b) 주간 / 격주 / 월간 | "매주 화요일 / 격주 화요일 / 매월 X일" | m021 (`AppointmentSeries`) + 패턴 컬럼 |
| (c) 모두 | (a) + (b) | m021 + 더 풍부한 schema |

### 6-3. 마이그레이션 m021

```sql
CREATE TABLE appointment_series (
    id VARCHAR(32) PRIMARY KEY,
    patient_id VARCHAR(32) NOT NULL,
    therapist_id VARCHAR(32),
    pattern VARCHAR(20),  -- 'weekly' / 'biweekly' / 'monthly' / 'n_times'
    pattern_data TEXT,     -- JSON: {"interval_days":7,"count":12} 등
    start_date DATE,
    end_date DATE,
    created_at DATETIME
);
ALTER TABLE appointments ADD COLUMN series_id VARCHAR(32) REFERENCES appointment_series(id);
```

### 6-4. 응답 dict / API URL 영향

- 신설 endpoint: `POST /api/appointment-series` (반복 등록), `DELETE /api/appointment-series/{sid}` (시리즈 일괄 취소).
- `Appointment` 응답에 `series_id: str | None` 추가.
- FullCalendar event extendedProps 에 `series_id` 추가.

### 6-5. UI 영향

- 예약 등록 모달: 반복 패턴 입력.
- 시리즈 일괄 수정 / 취소 흐름.
- 캘린더에 반복 예약 시각적 표시.

### 6-6. 사용자 결정 필요 항목 (20-3-4 진입 전)

| 결정 | 후보 | 권장 |
|---|---|---|
| 반복 패턴 | (a) N회 (b) 주간/격주/월간 (c) 모두 | (b) — 도수치료 일반적 패턴 |
| 시리즈 일괄 처리 | (i) 미래 예약만 일괄 변경 (ii) 과거+미래 모두 | (i) — 안전 |
| 충돌 검사 | (i) 시리즈 등록 시 모든 슬롯 검사 (ii) 등록 후 충돌만 안내 | (i) — 일관성 |

### 6-7. 위험도

**높음**. 신규 테이블 + 충돌 검사 통합 + UI 多. 회귀 위험 = `_serialize_appointment` / 충돌 검사 / FullCalendar event.

### 6-8. F-3 (자원) 의존성

F-3 도입 시 반복 예약이 자원 충돌도 함께 검사하려면 F-3 선행. F-3 패스 / 후속 시 F-2 단독 도입 가능.

---

## 7. F-3 자원 (치료실 / 장비) — 20-3-5 상세

### 7-1. 현재 상태

- 치료실 / 장비 / 자원 부재.
- 예약 = 환자 + 치료사 + 시간 + 치료항목 만. 자원 충돌 검사 ⊥.

### 7-2. 도입 후보

| 후보 | 자원 | 마이그레이션 |
|---|---|---|
| (a) 치료실만 | `Room` 테이블 | m022 |
| (b) 치료실 + 장비 | `Room` + `Equipment` | m022 + m023 |
| (c) 치료실 + 장비 + 인력 추가 | `Room` + `Equipment` + 인력풀 | m022~m024 |

### 7-3. 마이그레이션 m022 ~ m023 (후보 (b) 기준)

```sql
CREATE TABLE resources (
    id VARCHAR(32) PRIMARY KEY,
    type VARCHAR(20) NOT NULL,  -- 'room' / 'equipment'
    name VARCHAR(100) NOT NULL,
    capacity INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT TRUE
);
ALTER TABLE appointments ADD COLUMN resource_id VARCHAR(32) REFERENCES resources(id);
CREATE INDEX idx_appt_resource_time ON appointments(resource_id, start_at);
```

### 7-4. 응답 dict / API URL 영향

- 신설 endpoint: `/api/resources` (CRUD).
- `Appointment` 응답에 `resource_id` / `resource_name` 추가.
- 충돌 검사 응답: `409 Conflict` + `detail="자원 충돌"` 신설.

### 7-5. UI 영향

- 예약 등록 모달: 자원 선택 dropdown.
- 자원 관리 화면 신설.
- 캘린더 자원별 column view (FullCalendar resourceTimeline 가능).

### 7-6. F-1 (Room) 충돌 가능성

F-1 풀 EMR 의 `Room` 과 F-3 자원의 `Room` 가 *별개 모델* 인지 *통합* 인지 결정 필요.
- (i) 별개: F-1 Room = 진료실 / F-3 Resource = 치료실 (다른 도메인).
- (ii) 통합: 둘 다 `Resource` 또는 `Room` 단일 테이블.

### 7-7. 사용자 결정 필요 항목 (20-3-5 진입 전)

| 결정 | 후보 | 권장 |
|---|---|---|
| 자원 모델 | (a) 치료실만 (b) 치료실 + 장비 (c) 더 풍부 | (b) — 도수 + 체외충격파 장비 분기 의존 |
| F-1 Room 과 통합? | (i) 별개 (ii) 통합 | F-1 결정 후 |
| 자원 충돌 정책 | (i) 같은 자원 동시 예약 ⊥ (ii) capacity > 1 허용 | (i) — 단순 시작 |
| 인력 자원 도입? | (i) 미도입 (ii) 인력풀 | (i) — 후속 |

### 7-8. 위험도

**높음**. 신규 테이블 + 충돌 검사 변경 + UI 자원 dropdown + 캘린더 view 변경 후보. F-2 와 동시 진입 시 회귀 위험 가중.

---

## 8. 진입 순서 권장

> 사용자 결정 답에 따라 조정.

### 8-1. 표준 진입 순서

1. **20-3-1 F-10 노쇼** — 가장 작음, 가장 안전. (사용자 §3-7 답 후)
2. **20-3-2 F-11 권한** — 화면 분기 추가. (사용자 §4-6 답 후)
3. **20-3-3 F-1 doctors** — **사용자 EMR 결정 필수**. 결정에 따라 진입 / 패스.
   - 결정 (a) 패스 → 20-3-4 로 점프
   - 결정 (b) 풀 EMR → 5개 마이그레이션 진행
   - 결정 (c) 가벼운 의사만 → m016 만
4. **20-3-4 F-2 반복 예약** — F-1 결정 후. F-1 패스 시 단독 도입.
5. **20-3-5 F-3 자원** — F-2 후. F-1 풀 EMR 시 Room 통합 결정 필요.

### 8-2. 분할 vs 묶음 진입

- 권장: **분할** (각 분할마다 Codex 검증 + commit). 5개 분할 = 5 commits.
- 묶음 진입 ⊥ — 마이그레이션 多 + UI 多 + 회귀 위험 가중.

---

## 9. 응답 key / API URL 요약

| 그룹 | 신설 응답 key | 신설 API URL |
|---|---|---|
| F-10 | `Appointment.no_show: bool` + `stats.no_show_count` | `POST /api/appointments/{aid}/mark-no-show` |
| F-11 | `Employee.permission_level: str` | `POST /api/admin/employees/{eid}/permission` |
| F-1 (b 풀) | `Patient.doctor_id` / `Appointment.doctor_id` / `_serialize_doctor` | `/api/doctors` / `/api/departments` / `/api/rooms` / `/api/doctor-schedules` |
| F-2 | `Appointment.series_id` | `/api/appointment-series` |
| F-3 | `Appointment.resource_id` + `Resource` | `/api/resources` |

기존 33+ 응답 key: 모두 보존.

---

## 10. UI / FullCalendar event 영향

| 그룹 | extendedProps 추가 키 | 캘린더 view 변경 |
|---|---|---|
| F-10 | `no_show: bool` | 노쇼 표시 (배경색 / 아이콘) |
| F-11 | (없음) | (없음, 화면 분기는 라우팅 단계) |
| F-1 (b) | `doctor_id` / `doctor_name` | 담당의 표시 |
| F-2 | `series_id` | 반복 마커 |
| F-3 | `resource_id` / `resource_name` | resourceTimeline view (옵션) |

기존 extendedProps 키 (16개): 모두 보존.

---

## 11. 위험도 종합

| 분할 | 위험 | 마이그레이션 | UI 변경 |
|---|---|---|---|
| 20-3-1 F-10 | 중간 | m014 (1개) | 작음 (체크박스) |
| 20-3-2 F-11 | 중간 | m015 (1개) | 작음 (등급 select) |
| 20-3-3 F-1 (b 풀) | **높음** | m016~m020 (5개) | 큼 (의사 / 진료실 / 진료과 화면) |
| 20-3-3 F-1 (c 가벼움) | 중간 | m016 (1개) | 작음 |
| 20-3-3 F-1 (a 패스) | 0 | 0 | 0 |
| 20-3-4 F-2 | **높음** | m021 (1개) | 중간 (반복 입력 모달) |
| 20-3-5 F-3 | **높음** | m022~m023 (2개) | 큼 (자원 dropdown / 캘린더 view) |

---

## 12. 검증 패턴 (19-C 14 영역 + 신규 O 영역)

각 분할마다 19-C [§4 ~ §17 14 영역](19_refactor_function_verification_checklist.md) 영향 항목 + 신규 O 영역 (노쇼 / 권한 / 담당의 / 자원 / 반복) 검증.

| 분할 | 19-C 영향 영역 | 신규 O 영역 |
|---|---|---|
| 20-3-1 F-10 | A (예약) / H (통계) / G (SMS — 노쇼 알림 후속) | O-1 (노쇼) |
| 20-3-2 F-11 | E (치료사·의사) / I (관리자) / J (AI — 권한 게이트) | O-2 (권한) |
| 20-3-3 F-1 | A (예약) / E (치료사·의사) / D (환자) / F (캘린더) / J (AI 가드 강화) | O-3 (담당의 / 진료실 / 진료과) |
| 20-3-4 F-2 | A (예약) / F (캘린더) | O-4 (반복) |
| 20-3-5 F-3 | A (예약) / F (캘린더) / H (통계) | O-5 (자원) |

---

## 13. Codex 검증 요청 형식

각 분할마다 [reports/refactor/20-3-N_codex_review_request.md](../../reports/refactor/) 작성:
- 본 20-P-2 [§3 ~ §7 상세 기획](#) 정합 확인
- 마이그레이션 m014~m023 안전성 (NULL 허용 / 기본값)
- 응답 키 33+ 셋 보존
- 19-14 baseline 1726 회귀 0
- 운영 DB / 외부 API / 실제 문자 발송 ⊥

---

## 14. 종합

- 본 20-P-2 = 그룹 C 5개 항목 (F-10 / F-11 / F-1 / F-2 / F-3) 의 *상세 기획* — read-only 문서.
- §1 그룹 C 개요 + 의존성 (F-1 → F-15 / F-3 → F-2 / F-10 → F-11).
- §2 공통 원칙 GC-1 ~ GC-10 = 응답 key 보존 / API URL 보존 / m014+ 신설 / NULL 허용 / 1726 baseline 회귀 ⊥ / 운영 DB 보호 / UI 최소화 / PII 비노출 / 19-C 14 영역 + O 영역 / Codex 검증 게이트.
- §3 ~ §7 = 5개 항목 상세 (현재 상태 / 도입 후보 / 마이그레이션 / 응답·UI 영향 / 사용자 결정 / 위험도 / 회귀 보호).
- §8 진입 순서 = 20-3-1 (F-10) → 20-3-2 (F-11) → 20-3-3 (F-1 / 패스 가능) → 20-3-4 (F-2) → 20-3-5 (F-3).
- §9 ~ §10 응답 key / API URL / FullCalendar event 영향 — 기존 33+ 셋 + 16 extendedProps 키 보존.
- §11 위험도 종합 — F-10 / F-11 = 중간, F-1 / F-2 / F-3 = 높음.
- §12 검증 = 19-C 14 영역 + 신규 O 영역 (노쇼 / 권한 / 담당의 / 자원 / 반복).
- 다음 단계 = **20-P-2 Codex 검증 통과** 후 → 사용자 §3-7 (F-10 결정) 답 → **20-3-1 F-10 노쇼 진입**.
- F-1 EMR 결정 (가장 큰 결정) 은 20-3-3 진입 직전에 받음 — 본 시스템 정체성 (도수치료 전문 vs 일반 진료) 선택.
