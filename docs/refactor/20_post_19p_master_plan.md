# 20-P-1 post-19-P 부재 항목 도입 마스터 플랜 (20_post_19p_master_plan)

> 19-P 사이클 (19-P-1 ~ 19-P-9, 19-0 ~ 19-14, 19-C) 종료 후 후속 부재 항목 도입을 위한 *준비 단계* 문서.
> 본 문서는 *마스터 플랜* — 실제 코드 / 테스트 / 폴더 / 파일 / fixture / mock / 마이그레이션 미생성.
> 19-P 와 마찬가지로 read-only 문서 세션.

## 0. 메타

- 작성일: 2026-05-04
- 기준 브랜치: `ai-rag-v1-integration`
- 직전 commit: `a8db9f1` (19-C r2 보정 + Codex 조건부 통과)
- 19-14 baseline: **1671 passed, 1 skipped, 10 xfailed** (자체 회귀 검증 통과)
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.

### 0-1. 본 문서가 다루지 않는 범위

- 실제 코드 / 마이그레이션 / 테스트 작성 — 20-1 ~ 20-4 그룹 묶음 세션에서 처리.
- v1.4.0 / v1.5.0 배포 절차 — [docs/releases/](../releases/) 별도 게이트.
- 사용자 결정 필요 항목의 *최종 결정* — 본 §4 에 후보만 정리, 실제 결정은 사용자가 답할 것.

### 0-2. 본 문서의 위치

- 19-P-1 ~ 19-P-9 = 19-x 단위화 리팩토링 *준비 단계* (구조 변경, 기능 변경 ⊥).
- 19-0 ~ 19-14 + 19-C = 19-x 실제 코드 + 공통 문서화 (구조 변경, 기능 변경 ⊥).
- **20-P-1 (본 문서) = 부재 항목 도입 *준비 단계* (기능 추가 — 19-P 비-목표였던 영역).**
- 20-1 ~ 20-4 = 그룹 A/B/C/D 묶음 실제 코드 / 마이그레이션 / 테스트.

### 0-3. 19-P 사이클과의 차이

| 구분 | 19-P 사이클 | 20-P 사이클 |
|---|---|---|
| 목적 | 구조 변경 (단위화) | **기능 추가** (부재 항목 도입) |
| 응답 키 변경 | ⊥ (33+ 키 셋 보존) | **추가 허용** (기존 key 삭제 / rename ⊥) |
| API URL 변경 | ⊥ | **신설 허용** (`/api/health` / `/api/notifications` 등) |
| DB schema 변경 | ⊥ (m001~m013 diff 0) | **m014+ 신설 허용** |
| UI 변경 | ⊥ | **신설 / 보정 허용** (calendar UI 분리 / 출력물 / 알림 화면 등) |
| 외부 API 호출 | ⊥ (`_block_sdk_modules`) | EMR / 알림 채널은 **외부 호출 후보** (사용자 결정 필요) |
| Codex 검증 | 통과 게이트 | 통과 게이트 (동일) |
| 19-C 작동확인 | 14 영역 A~N | 동일 적용 + **신규 영역 (알림 / 출력물 / EMR 등) 추가** |

---

## 1. 부재 항목 15개 분류 (그룹 A/B/C/D)

> [19_refactor_rollout_plan.md §9 F-1 ~ F-15](19_refactor_rollout_plan.md) 정합.

### 1-A. 그룹 A — 가벼움 (정책 / 가드 / schema 변경 ⊥)

| ID | 항목 | 마이그레이션 | UI | 외부 호출 | 사용자 결정 |
|---|---|---|---|---|---|
| F-15 | AI 의사 정보 임의 생성 차단 (의사 가드 M-36) | ✗ | ✗ | ✗ | 차단 패턴 정의 |
| F-7 | privacy / retention 정책 고도화 | ✗ | ✗ | ✗ | 보존 기간 |
| F-8 | audit / logs 보존 / 자동 정리 | ✗ | ✗ | ✗ | 보존 기간 |

특성: 신설 모듈 / 정책 상수 / 가드 패턴 추가. 응답 key / DB / UI 변경 0. 위험도 **낮음**.

### 1-B. 그룹 B — 중간 (신설 모듈 / schema 변경 ⊥)

| ID | 항목 | 마이그레이션 | UI | 외부 호출 | 사용자 결정 |
|---|---|---|---|---|---|
| F-13 | `/api/health` 신설 (M-28) | ✗ | ✗ | ✗ | health 응답 키 정의 |
| F-12 | `modules/notes/` 통합 (지속 vs 당일 메모) | ✗ | ✗ | ✗ | 메모 정책 (당일/지속 경계) |
| F-14 | calendar / schedule_view UI 분리 | ✗ | ✓ (main.html JS 외부) | ✗ | UI 분리 범위 |

특성: 신설 폴더 / view-model / UI 분리. m001~m013 diff 0. 위험도 **낮음~중간**.

### 1-C. 그룹 C — 큰 (마이그레이션 동반)

| ID | 항목 | 마이그레이션 | UI | 외부 호출 | 사용자 결정 |
|---|---|---|---|---|---|
| F-10 | 노쇼 별도 필드 | m014 (`Appointment.no_show` boolean) | ✓ (체크박스 / 통계 분기) | ✗ | status 분기 정책 + 통계 영향 |
| F-11 | 권한 다중 등급 (직원 / 관리자 분리) | m015 (`Employee.permission_level`) | ✓ (로그인 / 화면 분기) | ✗ | 등급 매트릭스 (직원 / 관리자 / 슈퍼관리자?) + 권한 구분 |
| F-1 | doctors / `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` | m016 ~ m020 (5개) | ✓ (담당의 / 진료실 / 진료과) | ✗ | EMR 도입 범위 (현재 도수치료 전문 — 의사 기능 추가 필요?) |
| F-2 | 반복 예약 | m021 (`AppointmentSeries` + `Appointment.series_id`) | ✓ (반복 패턴 입력) | ✗ | 반복 패턴 (주간 / 격주 / 월간 / N회) |
| F-3 | 자원 (치료실 / 장비) | m022 ~ m023 (`Resource` + `Appointment.resource_id`) | ✓ (자원 선택 / 충돌) | ✗ | 자원 모델 + 자원 충돌 정책 |

특성: 신설 ORM / 컬럼 + UI + 통계 / 응답 key 추가. 위험도 **높음**. 사용자 정책 결정 필수.

### 1-D. 그룹 D — 최대 (외부 연동 / 시간 소요)

| ID | 항목 | 마이그레이션 | UI | 외부 호출 | 사용자 결정 |
|---|---|---|---|---|---|
| F-4 | 알림 (내부 / 외부 채널) | m024 (`Notification` + 채널별) | ✓ (알림 화면 / 설정) | **✓ (Slack / 이메일 / push)** | 채널 결정 (어떤 채널? 어떤 이벤트?) |
| F-5 | 출력물 (예약표 / 통계표 / 환자 안내문) | ✗ | ✓ (출력 미리보기 / PDF) | ✗ (PDF 생성은 내부) | 템플릿 / 포맷 (PDF? HTML? Excel? 기존 export 와 통합?) |
| F-6 | export_import 확장 (CSV / EMR import) | ✗ | ✓ (import 화면) | ✗ | 포맷 / 매핑 (어떤 EMR 포맷? 한국형 EMR? CSV 표준?) |
| F-9 | 비트U차트 / EMR 연동 | m025+ | ✓ | **✓ (EMR API)** | EMR 벤더 / API / 인증 / 데이터 매핑 |

특성: 외부 시스템 연동 + UI + 마이그레이션. 위험도 **최대**. F-4 / F-9 는 사용자 정책 + 외부 인증 정보 (key) 필수.

---

## 2. 그룹 간 의존성 그래프

| 의존 | 설명 |
|---|---|
| F-1 (doctors) → F-9 (EMR) | EMR 연동 시 의사 / 진료과 / 진료실 모델이 선행 필요. F-1 없이 F-9 불가능. |
| F-1 (doctors) → F-15 (의사 가드) | 의사 가드 패턴은 F-1 도입 후에야 *DB 근거* 로 검증 가능. F-1 없이 F-15 는 *임의 생성 차단 패턴* 만 (현재 가능). |
| F-3 (자원) → F-2 (반복 예약) | 반복 예약이 자원 충돌도 함께 검사하려면 F-3 선행. F-2 만 단독 도입 가능 (자원 검사 ⊥). |
| F-10 (노쇼) → F-8 (audit 보존) | 노쇼 통계 / audit 보존 기간 영향. F-10 후 F-8 정책 재검토. |
| F-11 (권한 다중) → F-15 (의사 가드) | 의사 가드 적용 권한 등급 정책 영향. F-11 후 F-15 강화. |
| F-12 (notes 통합) ← 19-7 patients 분리 결과 | 19-7 에서 분리한 `notes_service` 와 통합. 의존성 0 (이미 19-7 종료). |
| F-13 (/api/health) ← 19-2 health 분류 | 19-2 에서 후속 검토 분류만 — F-13 에서 신설. 의존성 0. |
| F-14 (calendar UI) ← 19-3 view-model | 19-3 에서 view-model 만 분리 — F-14 에서 main.html JS 외부 분리. 의존성 0. |
| F-7 (privacy retention) ← F-8 (audit 보존) | 둘 다 보존 정책 — 함께 결정 + 함께 도입. |
| F-4 (알림) → F-5 (출력물) | 알림 채널 일부 (이메일 첨부 등) 가 출력물 포맷 의존. 단순 알림은 F-5 없이 가능. |

### 2-1. 그룹 진입 순서 권장

1. **그룹 A (F-15 / F-7 / F-8)** — 의존성 0, 정책만 추가, 가장 안전.
2. **그룹 B (F-13 / F-12 / F-14)** — 의존성 0, 신설 모듈 + UI 분리만, schema 변경 ⊥.
3. **그룹 C 분할 진행** (사용자 정책 결정 필수):
   - 3-1: F-10 (노쇼) — 가장 작은 마이그레이션, F-8 정책 재검토 동반.
   - 3-2: F-11 (권한) — F-15 강화 동반.
   - 3-3: F-1 (doctors) — 5개 마이그레이션 + 의사 가드 강화.
   - 3-4: F-2 (반복) — F-1 후 (담당의 반복 적용 가능).
   - 3-5: F-3 (자원) — F-2 후 (자원 충돌 검사 통합).
4. **그룹 D 분할 진행** (외부 연동 사용자 결정 필수):
   - 4-1: F-5 (출력물) — 외부 호출 ⊥, 사용자 템플릿 결정만.
   - 4-2: F-6 (export_import 확장) — 외부 호출 ⊥, 포맷 결정.
   - 4-3: F-4 (알림) — 외부 호출 ✓ (채널 인증 정보 사용자 입력).
   - 4-4: F-9 (EMR) — F-1 / F-3 / F-4 후, 가장 마지막.

---

## 3. 마이그레이션 영향 (m014 ~ m025+)

> 19-P 기간 내 m014+ 미도입 (DEC-D 정합) — 본 20-P 부터 신설 가능.

| 마이그레이션 | 그룹 | 항목 | 변경 |
|---|---|---|---|
| m014 | C | F-10 노쇼 | `Appointment.no_show` BOOLEAN DEFAULT 0 |
| m015 | C | F-11 권한 다중 | `Employee.permission_level` ENUM(staff/admin/super) |
| m016 | C | F-1 doctors | `Doctor` 별도 테이블 (또는 `Employee.role="doctor"` 확장 정책 결정) |
| m017 | C | F-1 진료과 | `Department` 테이블 |
| m018 | C | F-1 진료실 | `Room` 테이블 |
| m019 | C | F-1 의사 일정 | `DoctorSchedule` 테이블 (또는 EmployeeLeave 확장) |
| m020 | C | F-1 환자-담당의 | `Patient.doctor_id` FK 추가 |
| m021 | C | F-2 반복 예약 | `AppointmentSeries` 테이블 + `Appointment.series_id` FK |
| m022 | C | F-3 자원 | `Resource` 테이블 (room/equipment) |
| m023 | C | F-3 예약-자원 | `Appointment.resource_id` FK + 충돌 인덱스 |
| m024 | D | F-4 알림 | `Notification` + `NotificationChannel` 테이블 |
| m025 | D | F-9 EMR | `EmrMapping` + `EmrSyncLog` 테이블 |
| m026+ | D | F-9 EMR 확장 | 사용자 EMR 결정 후 |

### 3-1. PyInstaller spec 갱신

각 마이그레이션 신설 시 [dosu_clinic.spec](../../dosu_clinic.spec) `hiddenimports` 자동 글롭 / 명시 등록 + [tests/test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) 케이스 추가.

---

## 4. 사용자 결정 필요 항목 (그룹별)

> 본 §4 는 *후보* 만 정리 — 실제 결정은 사용자가 그룹 진입 시점에 답.

### 4-A. 그룹 A 사용자 결정

| 항목 | 후보 | 권장 (사용자 답 전) |
|---|---|---|
| F-15 의사 가드 차단 패턴 | (a) 의사 단정 표현 (`담당의는 X 입니다`) (b) 의사 일정 단정 (`Y 의사는 화요일 ...`) (c) 의사 진단 단정 (`X 의사가 진단했습니다`) | a + b + c 모두 차단 (의사 정보 부재 — DB 근거 없는 응답 ⊥) |
| F-7 privacy 보존 기간 | (a) 환자 비활성 N개월 후 마스킹 (b) AI 로그 N개월 후 삭제 | (a) 18개월 (b) 6개월 |
| F-8 audit 보존 기간 | (a) audit_log 영구 보존 (b) N년 후 자동 정리 | 5년 보존 후 자동 정리 |

### 4-B. 그룹 B 사용자 결정

| 항목 | 후보 |
|---|---|
| F-13 health 응답 키 | `db_ok` / `migration_version` / `backup_age` / `disk_free` / `version` / `uptime` 등 — 어디까지 포함? |
| F-12 메모 정책 | (a) 당일 메모 (`Appointment.memo`) 와 지속 메모 (`Patient.memo`) 통합 모듈 — 표시 / 저장 분리 (b) 별도 유지 |
| F-14 calendar UI 분리 범위 | (a) main.html JS 외부 분리 + Alpine 모듈화 (b) FullCalendar wrapper 만 (c) 패스 (현재 유지) |

### 4-C. 그룹 C 사용자 결정 (큰 결정)

| 항목 | 후보 | 위험 |
|---|---|---|
| F-10 노쇼 정책 | (a) 별도 boolean (`no_show=true` + `status="canceled"` 동시) (b) status ENUM 확장 (`canceled` / `no_show`) (c) status + 별도 boolean 둘 다 | b → 기존 `status="canceled"` 분기 변경 多. a → 통계 분기 추가만. |
| F-11 권한 등급 매트릭스 | (a) 직원 / 관리자 / 슈퍼관리자 3등급 (b) 더 세분화 | 매트릭스 + 화면 분기 多. |
| F-1 doctors 도입 범위 | (a) Employee `role="doctor"` 확장 (현재 분기 강화) (b) Doctor 별도 테이블 + Employee 분리 (c) 패스 (현재 도수치료 전문 + 의사 기능 부재 유지) | a → m016 1개. b → m016~m020 5개 + UI 大. c → 후속 미진행. |
| F-2 반복 패턴 | (a) 주간 (b) 격주 (c) 월간 (d) N회 (e) 모두 | a~e 모두면 series 모델 복잡. |
| F-3 자원 모델 | (a) 치료실만 (b) 치료실 + 장비 (c) 치료실 + 장비 + 인력 | b 권장 (현재 도수 / 체외충격파 = 장비 분기 의존). |

### 4-D. 그룹 D 사용자 결정 (외부 연동)

| 항목 | 후보 | 외부 인증 |
|---|---|---|
| F-4 알림 채널 | (a) 내부 알림만 (b) 이메일 (c) Slack (d) 카카오톡 / SMS (e) 다중 | b/c/d → 각 채널 API key 사용자 등록 + provider mock 가능? |
| F-4 알림 이벤트 | (a) 백업 실패 (b) reindex 실패 (c) 예약 취소 (d) 매뉴얼 검색 부재 (e) 사용자 정의 | 단계별 도입. |
| F-5 출력 포맷 | (a) PDF (b) Excel (c) HTML (d) 모두 | PDF (`reportlab`) / Excel (`openpyxl` 이미 있음) |
| F-6 import 포맷 | (a) CSV (b) Excel (이미 부분 있음) (c) EMR 표준 (HL7 / FHIR / 한국형) | b 확장 우선, c 는 F-9 동반. |
| F-9 EMR 벤더 | (a) 비트U차트 (b) 의사랑 (c) 한국형 EMR 표준 (d) FHIR | 사용자 사용 EMR 확인 필수. |

---

## 5. 응답 key / API URL 변경 영향

> 19-P 의 33+ 응답 key 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9 + 비-AI alias) **삭제 / rename ⊥** — 기존 key 보존 + 추가만.

| 그룹 | 신설 응답 key | 신설 API URL |
|---|---|---|
| A | F-15 hallucination_guard 결과 (`safety_blocked` / `pattern` 등) — 기존 응답에 추가 | (없음) |
| A | F-7/F-8 retention 정책 — 기존 응답에 `retention_*` 추가 | (없음) |
| B | F-13 health 응답 키 (사용자 결정) | `/api/health` 신설 |
| B | F-12 notes 응답 키 (당일 / 지속 분리 vs 통합) | (기존 `/api/patients/{pid}/memo` 유지) |
| B | F-14 calendar view-model 응답 (기존 보존) | (기존 `/api/appointments` 유지) |
| C | F-10 `no_show` 필드 — appointment 응답에 추가 | (없음) |
| C | F-11 `permission_level` — admin / employee 응답에 추가 | `/api/auth/*` 분기 |
| C | F-1 doctors 응답 — 기존 `_serialize_employee` 와 별도 / 통합 결정 | `/api/doctors` / `/api/departments` / `/api/rooms` |
| C | F-2 series 응답 | `/api/appointment-series` |
| C | F-3 resource 응답 | `/api/resources` |
| D | F-4 알림 응답 | `/api/notifications` + 채널별 |
| D | F-5 출력물 | `/api/reports/{type}.{pdf|xlsx|html}` |
| D | F-6 import 확장 | `/api/import/{format}` |
| D | F-9 EMR 응답 | `/api/emr/{sync,mapping,status}` |

---

## 6. 위험도 평가

| 그룹 | 위험도 | 근거 |
|---|---|---|
| A | 낮음 | 정책 / 가드만 — 응답 / DB / UI 변경 0. 19-14 baseline 회귀 0 예상. |
| B | 낮음~중간 | 신설 모듈 + UI 분리 (F-14). schema / 외부 호출 0. |
| C-1 (F-10) | 중간 | m014 + 통계 분기 추가. 기존 status 정책 보존. |
| C-2 (F-11) | 중간 | m015 + 권한 매트릭스. 기존 admin 단일 등급 호환 유지. |
| C-3 (F-1) | **높음** | m016~m020 (5개 마이그레이션) + UI + 응답 키 + 통계 영향 多. |
| C-4 (F-2) | **높음** | series 모델 복잡 + UI 입력 패턴 多 + 충돌 검사 정책. |
| C-5 (F-3) | **높음** | 자원 모델 + 예약 충돌 정책 변경. |
| D-1 (F-5) | 중간 | 출력 포맷 결정 + 템플릿 작성. 외부 호출 0. |
| D-2 (F-6) | 중간 | import 매핑 + 트랜잭션 안전성. |
| D-3 (F-4) | **높음** | 외부 채널 (Slack / 이메일) — 인증 정보 + provider mock 정책. |
| D-4 (F-9) | **최대** | EMR 연동 — 외부 시스템 + 사용자 EMR 결정 + 데이터 매핑 + 인증. F-1 / F-3 / F-4 모두 선행. |

---

## 7. 검증 패턴 (19-x 와 동일)

> [19_refactor_function_verification_checklist.md](19_refactor_function_verification_checklist.md) 14 영역 (A~N) + 신규 영역 추가.

### 7-1. 19-C 14 영역 (A~N) 적용

각 20-x 그룹 묶음 세션은:
- §3 공통 필수 확인 C-1 ~ C-12.
- §4 ~ §17 14 영역 중 영향 항목 확인.
- §1 V-1 ~ V-10 공통 원칙.

### 7-2. 신규 영역 (20-P 부터 추가)

| 신규 영역 | 그룹 | 내용 |
|---|---|---|
| O. 노쇼 / 권한 / 담당의 / 자원 / 반복 | C | 신규 컬럼 / 분기 / 통계 영향 |
| P. 알림 / 출력물 / EMR import | D | 외부 채널 / 포맷 / 인증 |
| Q. 마이그레이션 안전성 | C / D | m014+ 다운타임 / 롤백 / 백업 |

### 7-3. 자체 회귀 검증

각 20-x 세션 종료 시:
- `pytest tests -q` (19-14 baseline 1671/1/10 정합 또는 갱신 baseline)
- `ruff check app tests scripts`
- `python scripts/check_db_path.py`
- 19-C 영향 범위 작동확인 + 신규 영역 (O / P / Q) 영향 항목 작동확인

---

## 8. 진행 순서 (사용자 결정 후)

> 본 §8 은 *권장* 순서 — 사용자 결정 답에 따라 조정.

### 8-1. 그룹 A 진입 흐름 (즉시 진입 가능)

1. **20-1** = F-15 + F-7 + F-8 묶음 (사용자 §4-A 답 후)
   - 기획: 차단 패턴 정의 + 보존 기간 결정
   - 코드: `app/modules/ai/safety/hallucination_guard.py` 패턴 추가 + `app/modules/audit/retention.py` 신설
   - 테스트: 가드 패턴 회귀 + retention 정책 단위 테스트
   - 검증: 19-C E (치료사·의사) + I (관리자·백업) + J (AI·RAG) + M (보안)
   - Codex 검증 + 자체 회귀 + commit

### 8-2. 그룹 B 진입 흐름 (그룹 A 완료 후)

2. **20-2** = F-13 + F-12 + F-14 묶음 (사용자 §4-B 답 후)
   - 검증: 19-C K (Health) + D (환자·메모) + F (캘린더)

### 8-3. 그룹 C 진입 흐름 (사용자 §4-C 답 후 — 큰 결정 多)

- 20-3-1 = F-10 노쇼 (m014)
- 20-3-2 = F-11 권한 (m015)
- 20-3-3 = F-1 doctors (m016~m020) — **F-1 도입 X 결정 시 스킵**
- 20-3-4 = F-2 반복 예약 (m021)
- 20-3-5 = F-3 자원 (m022~m023)

### 8-4. 그룹 D 진입 흐름 (사용자 §4-D 답 + 외부 인증 정보 후)

- 20-4-1 = F-5 출력물
- 20-4-2 = F-6 import 확장
- 20-4-3 = F-4 알림 (채널별)
- 20-4-4 = F-9 EMR (가장 마지막)

---

## 9. 종합

- 본 20-P-1 = 부재 항목 15개 (F-1 ~ F-15) 도입을 위한 *준비 단계* 마스터 플랜.
- §1 그룹 A/B/C/D 분류 = 가벼움 / 중간 / 큰 / 최대 위험도별 묶음.
- §2 의존성 = F-1 → F-9 / F-3 → F-2 / F-10 → F-8 등 진입 순서 영향.
- §3 마이그레이션 = m014 ~ m025+ — 19-P 기간 내 미도입, 본 20-P 부터 신설.
- §4 사용자 결정 필요 항목 = 그룹 A 3개 / B 3개 / C 5개 / D 5개 = 총 16개 후보 — 사용자 답 후 진입.
- §5 응답 key / API URL = 기존 33+ 셋 보존 + 신설만 (rename / 삭제 ⊥).
- §6 위험도 = A 낮음 / B 낮음~중간 / C 중간~높음 / D 높음~최대.
- §7 검증 = 19-C 14 영역 + 신규 3 영역 (O/P/Q).
- §8 진입 순서 = 20-1 (그룹 A) → 20-2 (그룹 B) → 20-3-1 ~ 20-3-5 (그룹 C 분할) → 20-4-1 ~ 20-4-4 (그룹 D 분할).
- 다음 단계 = **20-P-1 Codex 검증 통과 후** → 사용자 §4-A 결정 → 20-1 그룹 A 묶음 진입.
