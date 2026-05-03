# 19-P-4 단위화 리팩토링 — 의존성 맵 (19_refactor_dependency_map, r2 보정본)

> 19-P-3 [모듈 매핑](19_refactor_module_map.md) 의 30개 모듈을 기반으로,
> **모듈 간 의존성 방향 + 위험도 + 순환참조 + 분리 순서 영향** 을 정리한다.
> 본 문서는 *의존성 의도* 문서 — 실제 코드 이동은 19-P-5+ 별도 세션.
>
> **r2 보정 (Codex r1 minor issues 후)**: §0-1 "문서 2개 → 3개" + §2-B PII 경로 "현재 vs 목표 후속" 명시.

## 0. 메타

- 작성일: 2026-05-02
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: 529 passed, 1 skipped, 7 xfailed
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 Codex 판정: **pass / pass / pass with caveat**
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *의존성 의도* 문서 — 실제 코드 / import 변경 없음.

### 0-1. 19-P-3 Codex r1 caveat 반영

| caveat | 본 문서 반영 |
|---|---|
| 줄 번호 대신 symbol grep 기준 권장 | 본 문서는 함수명 / 클래스명 / endpoint 경로 위주. 줄 번호는 참고용. |
| `leave_type="am"`/`"pm"` 반차 차단 정책 구체화 | §2-Leaves + §5-2 + §6 에서 명시. DB 표준 = `am` / `pm` / `full` ([action_leave.py:346](../../app/services/ai/action_leave.py:346)). AI hint = `morning` / `afternoon` → `am` / `pm` 변환. **현재 예약 차단 로직 안 인라인** — availability 모듈로 추출 필요. |
| dirty/untracked 작업트리 표현 정확히 | 본 19-P-4 산출 = 문서 **3개** 신규 (`docs/refactor/19_refactor_dependency_map.md` + `reports/refactor/19-P-4_codex_review_request.md` + `reports/refactor/latest_codex_review_request.md`). 18-0~18-8 dirty/untracked 는 별개. |

### 0-2. 의존성 표기 기호

| 기호 | 의미 |
|---|---|
| `A → B (read)` | A 가 B 의 데이터 / 함수를 *읽기* 만 사용 (write 없음) |
| `A → B (write)` | A 가 B 의 데이터 / 함수를 *변경* (CUD) |
| `A → B (호출)` | A 가 B 의 service 함수를 호출 (read+write 모두 가능) |
| `A ↔ B` | 양방향 / 순환 가능성 |
| `A ⊥ B` | 의존성 금지 (raise 또는 컴파일 에러) |
| `A ?→ B` | 후속 검토 — 현재 부재 또는 미정 |

---

## 1. 의존성 설계 원칙

| # | 원칙 | 본문 |
|---|---|---|
| D-1 | router → service → repository | 표준 단방향. router 는 비즈니스 로직 X, repository 는 DB 쿼리만. |
| D-2 | service → rules / schemas | service 가 rules / schemas 를 import 가능. 역방향 ⊥. |
| D-3 | repository → models 만 | repository 는 ORM 만 사용. 다른 모듈 service / repository 호출 ⊥. |
| D-4 | core → modules ⊥ | core 는 modules 를 import 하지 않는다. 단방향. |
| D-5 | 모든 모듈 → core 허용 | core/config / core/database / core/errors / core/responses / core/security / core/time_utils / core/feature_flags 자유 사용. |
| D-6 | AI/RAG ⊥ 도메인 DB 임의 생성 | AI 가 환자 / 예약 / 휴무 / 의사 정보를 DB 근거 없이 생성 / 변경 ⊥. local-first 원칙 ([AI_WORKING_RULES.md §1-4](../AI_WORKING_RULES.md)). |
| D-7 | stats → 다른 도메인 (read only) | stats 는 appointments / patients / therapists / treatments / leaves 데이터를 *읽기만* — 상태 변경 ⊥. |
| D-8 | sms → 예약/환자/치료사/의사 (read only) | sms 가 예약 상태 변경 ⊥. 발송 결과는 sms.repository (`SmsLog`) 에만 write. |
| D-9 | audit → 모든 모듈 (호출 가능, 단방향) | audit.service.audit() 는 모든 모듈에서 호출 가능. 단, audit 가 도메인 모듈 service 호출 ⊥. PII 원문 저장 ⊥. |
| D-10 | settings / feature_flags → 단방향 read | 모든 모듈이 read 가능. 단, settings ⊥ modules 역참조 (순환 방지). |
| D-11 | calendar → appointments / leaves / staff (read) | view-model 전용 — 상태 변경 ⊥. |
| D-12 | health → 모든 모듈 (read only, 외부 API 호출 0) | 상태 조회만. 외부 LLM/Embedding 호출 ⊥. |
| D-13 | export_import → 다른 도메인 (read + import 시 write) | 엑셀 export = read only. 환자 import = patients.repository write 만. |

---

## 2. 주요 의존성 맵

### 2-A. appointments

```
appointments → patients (read)              # 예약 생성 시 환자 존재 검증
appointments → staff (read)                 # therapist_id / handler_id 검증 (doctor + therapist 통합)
appointments → treatments (read)            # treatment_codes 검증
appointments → leaves (read)                # 휴무 차단 (am/pm/full 분기)
appointments → availability (호출)           # 점심창 + 충돌 + 반차 차단
appointments → audit (호출)                  # CUD 시 audit.service.audit()
appointments → core (read)                  # config / database / errors / time_utils
appointments ⊥ sms (write)                  # 예약 변경이 sms 발송 자동 트리거 ⊥
appointments ⊥ stats (write)                # stats 가 read 만, 역방향도 동일
appointments ?→ calendar/view-model         # 후속 검토 (post-19-P)
appointments ?→ doctors (별도 모듈)          # 후속 검토 (Patient.doctor_id 도입 시)
```

> **NOTE**: appointments 는 다른 도메인 의존이 가장 많음 — §6 분리 순서에서 마지막 (14번).

### 2-B. patients

```
patients → notes_service (호출)              # 환자 메모 (Patient.memo) — patients.notes_service.py 안
patients → audit (호출)                      # CUD audit
patients → core (read)
patients → privacy/retention 정책 (read)     # PII 마스킹 (현재: app/services/ai/pii.py / 목표 후속: modules/ai/safety/pii.py)
patients ⊥ stats (호출)                      # stats 가 read 만
patients ?→ doctors (read)                   # 후속 검토 (Patient.doctor_id 도입 시)
patients ?→ appointments (read for history)  # /api/patients/{pid}/history 가 Appointment 직접 조회 — patients.repository 안 read 허용
```

### 2-C. staff (doctors + therapists 통합 — 19-P-2 §3-3)

```
staff → audit (호출)
staff → core (read)
staff ⊥ appointments (write)                 # staff 가 예약 상태 변경 ⊥
staff ⊥ leaves (write)                       # leaves 가 staff_id 검증만 — staff 가 휴무 등록 ⊥
staff ?→ stats (read for 의사별 집계)        # is_doctor_filter 분기 — staff.doctors_service 안 분리

# staff 안 doctor 분기 (M-03b — 얇은 분기)
staff.doctors_service → staff.repository (read)  # role=doctor 필터
staff.doctors_service → treatments (read)        # _doctor_codes_set: Treatment.role="doctor" (injection/cartilage)
```

### 2-D. doctors / medical_staff (별도 모듈, 후속 검토)

> **현재**: `Employee.role="doctor"` 분기로만 존재 — `staff.doctors_service` 안 흡수 (M-03b, A 분류).
> **후속 검토 (post-19-P, M-31~M-35)**: 별도 `modules/doctors/` 신설 시 의존성:

```
?→ doctors → patients (read for 담당의 매핑)     # Patient.doctor_id (m014+) 도입 시
?→ doctors → appointments (read for 진료 일정)   # DoctorSchedule (m014+) 도입 시
?→ doctors → stats (read for 의사별 통계)
?→ doctors → sms (read for 담당의 정보 포함 문자)
?→ doctors → EMR/오더/처방 (Order/Prescription m014+)
```

→ **본 19-P 비-목표**. 본 문서는 의존성 *후보* 만 표시.

### 2-E. leaves

```
leaves → staff (read)                        # employee_id 검증
leaves → audit (호출)
leaves → core (read)
leaves ← appointments.availability (read)    # 휴무 차단 — am/pm/full 분기
leaves ← ai/commands/action_leave (호출)     # _upsert_employee_leave_core 단일 진실원천
leaves ?→ calendar (read)                    # 휴무 표시 (post-19-P)
```

> **RISK**: `_upsert_employee_leave_core` 시그니처 절대 보존. AI action_leave 가 같은 헬퍼 호출.

### 2-F. treatments

```
treatments → core (read)
treatments → audit (호출)
treatments.completion_rules → patients.repository (write done_count)  # approve/revert 시
treatments ← appointments (read for treatment_codes 검증)
treatments ← stats (read for 분류)
treatments ← sms (read for 항목 표시)
treatments ?← ai/commands (read)             # 후속 — AI 가 치료항목 정보 임의 생성 ⊥
```

> **NOTE**: `manual60 count_increment=1` 절대 보존 ([CLAUDE.md](../../CLAUDE.md)).

### 2-G. stats (read-only — D-7)

```
stats → appointments.repository (read)
stats → patients.repository (read)
stats → staff.repository (read for 의사 필터)
stats → treatments.repository (read)
stats → leaves.repository (read for 부재 일자)  # 향후 — 현재 stats 는 leaves 직접 read 안 함
stats → core (read)
stats → audit (호출 — manual-counts upsert 시)
stats ⊥ appointments (write)                 # 절대 금지
stats ⊥ patients (write)                     # 절대 금지
stats ⊥ staff (write)                        # 절대 금지
```

### 2-H. sms (read only for 도메인 — D-8)

```
sms → appointments.repository (read for tomorrow-targets)
sms → patients.repository (read for 환자 phone)
sms → staff.repository (read for 발신자 정보)
sms → templates (호출 — sms.templates 안)
sms → settings (read for SmsSetting)
sms → audit (호출)
sms → provider (호출 — 외부 munjanara API)
sms → core (read)
sms ⊥ appointments (write)                   # 예약 상태 변경 ⊥
sms ⊥ patients (write)                       # 환자 정보 변경 ⊥
sms ?→ doctors (read for 담당의 정보)        # 후속
```

### 2-I. admin / settings

```
admin → settings (read+write)
admin → feature_flags (read)
admin → backup (호출)
admin → audit (호출)
admin → core/security (read+write — 비번 변경)
admin ?→ health (호출)                       # 후속 — /api/health 신설 시
admin ?→ ai/health.build_admin_status (read)  # /api/ai/status 는 ai 모듈 안에서 처리

settings → core (read)
settings → audit (호출)
settings ⊥ admin (역참조 금지 — 순환 방지)
settings ⊥ modules 역참조                     # D-10
```

> **SAFETY**: API key 등록 여부는 admin 응답에 boolean 만. 원문 노출 ⊥.

### 2-J. backup

```
backup → core/database (read+write — engine.dispose + atomic rename)
backup → settings (read for auto_backup_*)
backup → audit (호출 — restore 시)
backup → core (read)
backup ⊥ modules (호출)                      # backup 은 도메인 service 호출 안 함
?→ backup 중 다른 작업 차단                   # 후속 검토 (concurrency / locking)
```

### 2-K. ai

```
# ai router → 부도메인
ai/router → ai/manual_qa (호출)
ai/router → ai/sms_draft (호출)
ai/router → ai/commands/action_leave (호출)
ai/router → ai/health (호출 — /api/ai/status)
ai/router → ai/provider (호출)
ai/router → ai/logging (호출)
ai/router → core/security (read — require_admin)
ai/router → audit (호출)

# ai 부도메인 → 패키지
ai/manual_qa → ai/rag/pipeline (호출)         # wrapper 시그니처 절대 보존
ai/rag/pipeline → ai/rag/{retriever,reranker,confidence,safety,prompts} (호출)
ai/rag/retriever → ai/knowledge/keyword_index (호출)
ai/rag/retriever → ai/vector/store (호출)     # lazy import — vector 부재 환경 호환
ai/knowledge/indexer → ai/vector/embeddings (lazy import)
ai/knowledge/indexer → ai/vector/store (lazy import)

# ai/commands → 도메인 (write 허용 — single source of truth)
ai/commands/action_leave → leaves.service._upsert_employee_leave_core (호출)
ai/commands/action_leave ⊥ appointments (write)
ai/commands/action_leave ⊥ patients (write)
ai/commands/action_leave ⊥ sms (write)         # 본 19-P 정책 — AI 가 직접 발송 ⊥

# ai/safety
ai/safety → ai/pii (호출)
ai/safety → ai/rag/safety (호출 — hallucination_guard)

# ai/rag → 도메인 ⊥ (D-6 local-first)
ai/rag ⊥ appointments
ai/rag ⊥ patients
ai/rag ⊥ staff
ai/rag ⊥ leaves

# ai/logging
ai/logging → core/database (write — AiUsageLog)
ai/logging ⊥ audit                             # 분리 — AiUsageLog 는 별도 테이블
```

> **RISK**: `manual_qa.ask_manual_question(provider_override=)` 시그니처 + `LOW_SCORE_THRESHOLD=2` + `HIGH_THRESHOLD=0.7` / `LOW_THRESHOLD=0.3` 절대 보존.

### 2-L. calendar / schedule_view (post-19-P, M-26)

```
?→ calendar → appointments.repository (read)
?→ calendar → leaves.repository (read for 휴무 표시)
?→ calendar → staff.repository (read for 색상)
?→ calendar → time_utils (read)
?→ calendar ⊥ 모든 도메인 (write)              # view-model 전용
```

→ **후속 검토** — 본 19-P 비-목표 (UI 분리 미수행).

### 2-M. notes (현재 patients 안, 통합은 post-19-P, M-27)

```
patients.notes_service → patients.repository (write Patient.memo)
patients.notes_service → audit (호출)

# 통합 modules/notes/ (후속)
?→ notes → patients (read+write Patient.memo)
?→ notes → appointments (read+write Appointment.memo)  # 정책 미정 — 지속 메모 vs 당일 메모
?→ notes → privacy/retention (read for PII 정책)
```

### 2-N. health / diagnostics (post-19-P, M-28)

```
?→ health → core/database (read for DB 상태)
?→ health → backup (read for 백업 상태)
?→ health → ai/health (read for AI/RAG 상태) — 별도 도메인 분리
?→ health → core/feature_flags (read)
?→ health ⊥ 외부 API 호출 (D-12)               # 외부 LLM/Embedding 호출 ⊥
```

> **현재 부재** — `/api/health` 신설 결정은 사용자 (post-19-P).

### 2-O. export_import

```
export_import → stats.aggregators (read)         # /api/export/stats.xlsx
export_import → appointments.repository (read)   # /api/export/manual-schedule.xlsx
export_import → patients.repository (write)      # /api/data-convert/apply
export_import → audit (호출)
export_import → core (read)
?→ export_import → EMR / 비트U차트 (후속)
```

### 2-P. core (D-4: core ⊥ modules)

```
core/config → (없음 — env / 파일만)
core/database → models (read for create_all)
core/errors → (없음)
core/responses → (없음)
core/time_utils → (없음)
core/security → core/config (read — admin_password_hash)
core/feature_flags → core/config (read — env)
core/feature_flags → ai/health (read for ai_mode 파생) — **순환 위험**: 후속 결정 필요 (T-8 19-P-2)
```

> **RISK**: `core/feature_flags ↔ ai/health` 잠재적 순환 — 한쪽이 read-only 인터페이스로 분리 필요. §5-7 참조.

---

## 3. 의존성 분류표

> 컬럼: From / To / 목적 / 현재 / 허용 / 위험도 / 순환참조 / 테스트 / 주석 태그 / 비고

| From | To | 목적 | 현재 | 허용 | 위험도 | 순환위험 | 테스트 | 주석 | 비고 |
|---|---|---|---|---|---|---|---|---|---|
| appointments | patients (read) | 환자 존재 검증 | 현재 | 허용 | 낮음 | 없음 | contract | NOTE | 표준 도메인 read |
| appointments | staff (read) | therapist_id / handler_id 검증 | 현재 | 허용 | 낮음 | 없음 | contract | NOTE | role=doctor 강제 분기 포함 |
| appointments | treatments (read) | treatment_codes 검증 | 현재 | 허용 | 낮음 | 없음 | contract | NOTE | manual60 / eswt 분기 |
| appointments | leaves (read) | 휴무 차단 (am/pm/full) | 현재 | 허용 | 중간 | 없음 | rules + availability | RISK | 반차 차단 정책 — 현재 인라인 |
| appointments | availability (호출) | 점심창 / 충돌 / 반차 | 부분 | 허용 | 높음 | 없음 | rules + integration | RISK | DevTools 우회 방지 |
| appointments | audit (호출) | CUD 감사 | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | 모든 CUD |
| appointments | sms | 예약 발송 트리거 | 부재 | **금지** | — | sms↔appointments | — | RISK | sms 가 자동 트리거 ⊥ |
| appointments | stats | 통계 갱신 | 부재 | **금지** | — | stats↔appointments | — | NOTE | stats read-only |
| appointments | calendar | view-model 갱신 | 후속 | 후속 | — | — | — | — | post-19-P |
| appointments | doctors (별도) | 담당의 연결 | 후속 | 후속 | — | — | — | — | M-31~M-35 |
| patients | notes_service (호출) | 환자 메모 | 현재 | 허용 | 낮음 | 없음 | contract | SAFETY | PII 마스킹 |
| patients | audit (호출) | CUD 감사 | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | |
| patients | privacy/retention | PII 정책 | 부분 | 허용 | 중간 | 없음 | safety | SAFETY | AI 로그 마스킹 일관 |
| patients | doctors (read) | 담당의 매핑 | 후속 | 후속 | — | — | — | — | Patient.doctor_id 도입 시 |
| staff | audit (호출) | CUD 감사 | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | |
| staff.doctors_service | treatments (read) | role=doctor 분기 | 현재 | 허용 | 중간 | 없음 | rules | NOTE | _doctor_codes_set 정책 |
| staff | appointments | 예약 변경 | 부재 | **금지** | — | — | — | RISK | staff ⊥ 예약 변경 |
| staff | leaves | 휴무 등록 | 부재 | **금지** | — | staff↔leaves | — | RISK | staff_id 검증만 |
| therapists/staff | calendar | 색상 표시 | 후속 | 후속 | — | — | — | — | post-19-P |
| therapists/staff | stats | 의사별 집계 | 부분 | 허용 (read) | 중간 | 없음 | contract | NOTE | is_doctor_filter |
| leaves | staff (read) | employee_id 검증 | 현재 | 허용 | 낮음 | 없음 | contract | NOTE | |
| leaves | audit (호출) | CUD 감사 | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | |
| ai/commands/action_leave | leaves.service._upsert_employee_leave_core | 단일 진실원천 | 현재 | 허용 | 높음 | leaves↔ai | full + safety | COMPAT + RISK | 시그니처 절대 보존 |
| treatments | core (read) | config / time | 현재 | 허용 | 낮음 | 없음 | smoke | — | |
| treatments.completion_rules | patients.repository (write done_count) | approve/revert | 현재 | 허용 | 높음 | 없음 | rules + integration | NOTE + RISK | _bump_patient_count 정책 |
| treatments | appointments (read) | treatment_codes 분류 | 현재 | 허용 | 낮음 | 없음 | contract | NOTE | |
| stats | appointments.repository (read) | 집계 | 현재 | 허용 | 중간 | 없음 | contract + counts | NOTE | _resolve_stats_range |
| stats | patients.repository (read) | 신환 카운트 | 현재 | 허용 | 낮음 | 없음 | counts | — | |
| stats | staff.repository (read) | 의사 필터 | 현재 | 허용 | 중간 | 없음 | counts | NOTE | is_doctor_filter |
| stats | treatments.repository (read) | 분류 | 현재 | 허용 | 낮음 | 없음 | counts | — | |
| stats | leaves.repository (read) | 부재 일자 | 부분 | 허용 | 낮음 | 없음 | counts | — | 현재 stats 가 leaves read 거의 안 함 |
| stats | (모든 도메인) write | 상태 변경 | 부재 | **금지 (D-7)** | — | — | — | RISK | 절대 금지 |
| sms | appointments.repository (read) | tomorrow-targets | 현재 | 허용 | 중간 | 없음 | smoke | NOTE | |
| sms | patients.repository (read) | phone | 현재 | 허용 | 중간 | 없음 | smoke + masking | SAFETY | _mask_phone_for_log |
| sms | staff.repository (read) | 발신자 정보 | 현재 | 허용 | 낮음 | 없음 | smoke | — | |
| sms | templates (호출) | SmsTemplate CRUD | 현재 | 허용 | 낮음 | 없음 | contract | — | |
| sms | settings (read SmsSetting) | munjanara_id/key/pw | 현재 | 허용 | 높음 | 없음 | masking | SAFETY | _sms_sanitize |
| sms | audit (호출) | 발송 감사 | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | |
| sms | provider (호출 외부 munjanara) | 발송 | 현재 | 허용 | 높음 | 없음 | masking | SAFETY + RISK | timeout / 디코딩 |
| sms | appointments (write) | 예약 상태 변경 | 부재 | **금지 (D-8)** | — | sms↔appointments | — | RISK | 절대 금지 |
| sms | doctors (read) | 담당의 표시 | 후속 | 후속 | — | — | — | — | post-19-P |
| admin | settings (read+write) | SystemSetting | 현재 | 허용 | 중간 | admin↔settings | smoke | COMPAT | |
| admin | feature_flags (read) | ai_mode | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | |
| admin | backup (호출) | 수동 백업 | 현재 | 허용 | 높음 | 없음 | restore_safety | RISK | apply-update |
| admin | audit (호출) | 설정 변경 | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | |
| admin | core/security (read+write) | 비번 변경 | 현재 | 허용 | 높음 | 없음 | auth | SAFETY | PBKDF2 |
| admin | ai/health (read) | AI 상태 | 현재 | 허용 (read) | 중간 | admin↔ai (자기 정의 회피) | smoke | SAFETY | api_key_set boolean |
| settings | admin | 역참조 | 부재 | **금지 (D-10)** | — | admin↔settings | — | NOTE | 순환 방지 |
| backup | core/database | engine.dispose + rename | 현재 | 허용 | 높음 | 없음 | restore_safety | SAFETY + RISK | atomic rename |
| backup | settings (read) | auto_backup_* | 현재 | 허용 | 낮음 | 없음 | smoke | — | |
| backup | audit (호출) | 복원 감사 | 현재 | 허용 | 중간 | 없음 | restore_safety | NOTE | |
| ai/router | ai/manual_qa (호출) | 매뉴얼 Q&A | 현재 | 허용 | 중간 | 없음 | contract | COMPAT | wrapper 시그니처 |
| ai/router | ai/commands/action_leave (호출) | 자연어 휴무 | 현재 | 허용 | 높음 | ai↔leaves | full | RISK | HMAC + TOCTOU |
| ai/router | core/security (read) | require_admin | 현재 | 허용 | 낮음 | 없음 | auth | SAFETY | |
| ai/manual_qa | ai/rag/pipeline (호출) | RAG 본체 | 현재 | 허용 | 중간 | 없음 | rag | COMPAT | wrapper |
| ai/rag/retriever | ai/vector/store (lazy) | hybrid | 현재 | 허용 | 중간 | 없음 | vector + hybrid | RISK | lazy import |
| ai/knowledge/indexer | ai/vector/embeddings (lazy) | reindex | 현재 | 허용 | 중간 | 없음 | reindex | RISK | lazy import |
| ai/rag | appointments / patients / staff / leaves | DB 임의 생성 | 부재 | **금지 (D-6)** | — | — | safety | SAFETY | local-first |
| ai/commands/action_leave | leaves.service | 단일 진실원천 호출 | 현재 | 허용 | 높음 | ai↔leaves | full | COMPAT + RISK + SAFETY | _upsert_employee_leave_core |
| ai/commands | sms | AI 직접 발송 | 부재 | **금지** | — | — | safety | SAFETY | sms_sent=0 항상 |
| ai/logging | core/database (write AiUsageLog) | sha256 해시만 | 현재 | 허용 | 중간 | 없음 | logging | SAFETY | 원문 미저장 |
| audit | (모든 모듈) | service 호출 | 부재 | **금지 (D-9)** | — | audit↔모든 | — | NOTE | audit 단방향 |
| 모든 모듈 | audit (호출) | CUD 감사 | 현재 | 허용 | 낮음 | 없음 | smoke | NOTE | |
| 모든 모듈 | core (read) | 표준 | 현재 | 허용 | 낮음 | 없음 | smoke | — | D-5 |
| core | modules (호출) | 역참조 | 부재 | **금지 (D-4)** | — | — | smoke | NOTE | |
| calendar | appointments / leaves / staff (read) | view-model | 후속 | 후속 | — | — | — | — | post-19-P |
| notes | patients / appointments | 통합 메모 | 후속 | 후속 | — | — | — | — | post-19-P |
| health | core/database / backup / ai/health | 상태 조회 | 후속 | 후속 (read only) | — | health↔ai/backup | — | SAFETY | post-19-P, 외부 API ⊥ |
| export_import | stats / appointments / patients | 엑셀 export + 환자 import | 현재 | 허용 | 중간 | 없음 | contract | NOTE | _dc_* 헬퍼 |
| feature_flags | ai/health (read for ai_mode) | 단일 진실원천 | 부분 | 허용 (단방향 분리 후) | 중간 | core↔ai (잠재) | smoke | RISK | T-8 19-P-2 결정 |

---

## 4. 금지 / 줄여야 할 의존성

| # | 금지 / 줄임 항목 | 현재 상태 | 19-P 분리 시 정책 |
|---|---|---|---|
| F-1 | repository → service 역참조 | 현재 부재 (api.py 안 인라인) | 분리 시 단방향 절대 보장. repository 안에서 service 호출 ⊥. |
| F-2 | core → modules 참조 | 현재 부재 (단방향) | 분리 후에도 절대 금지 (D-4). |
| F-3 | stats → 다른 도메인 write | 현재 부재 | 분리 후 절대 금지 (D-7). |
| F-4 | sms → appointments write | 현재 부재 (sms_send 가 SmsLog write 만) | 분리 후 절대 금지 (D-8). |
| F-5 | AI/RAG → 도메인 임의 생성 | 현재 부재 (action_leave 만 leaves write) | 분리 후 절대 금지 (D-6). action_leave 는 예외 (단일 진실원천 호출). |
| F-6 | UI/static JS → DB 구조 직접 의존 | 현재 ✅ — main.html 5747-5793 등 응답 키 5개 의존 | 본 19-P 비-목표 (UI 분리). 응답 키 보존만 보장. |
| F-7 | 같은 DB query 중복 구현 | 현재 ✅ — `_doctor_codes_set` 등 일부 중복 | 분리 시 staff.doctors_service / treatments.repository 단일화. |
| F-8 | API key / 설정 분산 | 현재 ✅ — AiSetting / SmsSetting / SystemSetting / config.json 분산 | 분리 시 settings 모듈이 통합 read 인터페이스 제공 (write 는 각 도메인). |
| F-9 | 개인정보 원문 로그 | 현재 ✅ — sha256 해시만 (`AiUsageLog`) + 200자 cap (`recent_ai_logs`) | 분리 후에도 절대 보존. PII 원문 ⊥ (D-9). |

---

## 5. 순환참조 위험 구간

> 9개 위험 구간. 각 구간에 대해 (1) 위험 사유 (2) 정리 방향 (3) wrapper/adaptor 필요 (4) 테스트 필요.

### 5-1. appointments ↔ leaves

- **위험**: appointments.availability 가 leaves.repository read + leaves.bulk-set 이 appointments 를 read (확인 필요) → 잠재 순환.
- **정리 방향**: leaves.repository 를 appointments.availability 가 *read only* 호출. 역방향 (leaves → appointments) ⊥.
- **wrapper 필요**: 분리 직전 leaves.repository 의 read 인터페이스 정의 (`get_leaves_for_employee_on_date(employee_id, date)`).
- **테스트 필요**: 휴무 차단 + am/pm/full 분기 회귀 (`test_appointment_rules.py` + 신규 `test_availability_*`).

### 5-2. appointments ↔ availability

- **위험**: availability 가 appointments.repository read (충돌 검사) + appointments.service 가 availability 호출 → 같은 모듈 안에서는 OK, 분리 시 순환 위험.
- **정리 방향**: availability.py 를 `modules/appointments/` 하위 파일로 유지 (M-01 안). 단, 함수 시그니처는 `(start_at, duration_min, therapist_id, db) → bool` — 외부 의존성 명시.
- **wrapper 필요**: 없음 (같은 모듈 안).
- **테스트 필요**: 점심창 + 충돌 + 휴무 + am/pm 반차 통합 회귀.

> **확인 필요**: 현재 `leave_type="am"`/`"pm"` 차단 로직 위치 — `app/routers/api.py` 의 예약 생성/수정 안 인라인인지, 별도 헬퍼인지 grep 필요. 본 의존성 맵에서는 "현재 인라인" 가정.

### 5-3. appointments ↔ sms

- **위험**: 만약 예약 변경이 sms 자동 발송을 트리거하면 순환. 현재는 부재 (D-8).
- **정리 방향**: sms 가 appointments read only. appointments 가 sms 호출 ⊥. 발송 주체는 항상 사용자 명시적 액션.
- **wrapper 필요**: 없음.
- **테스트 필요**: `test_ai_sms_*` 가 이미 자동 발송 차단 단언 보유.

### 5-4. appointments ↔ stats

- **위험**: stats 가 appointments read + appointments 가 stats 갱신 호출 가능성. 현재는 부재.
- **정리 방향**: stats read-only (D-7). 통계는 *조회 시점 집계*. appointments → stats 호출 ⊥.
- **wrapper 필요**: 없음.
- **테스트 필요**: stats 응답 contract + appointments CUD 후 stats 자동 갱신 부재 단언.

### 5-5. patients ↔ notes

- **위험**: 통합 `modules/notes/` 가 patients.repository write 시 patients 가 notes 호출 → 순환.
- **정리 방향**: 본 19-P 안에서는 `patients/notes_service.py` 안에 두기. 통합은 post-19-P.
- **wrapper 필요**: 통합 시 notes.service → patients.repository 단방향. patients → notes 호출 ⊥.
- **테스트 필요**: 메모 PATCH + AI 응답 PII 마스킹.

### 5-6. staff (therapists) ↔ leaves

- **위험**: leaves 가 staff.repository read (employee_id 검증) + staff 가 leaves 표시 (직원탭) → 잠재 순환.
- **정리 방향**: staff → leaves 호출 ⊥. 표시는 calendar / 직원탭 view-model 이 담당 (양쪽 모두 read).
- **wrapper 필요**: 없음.
- **테스트 필요**: alias `therapist_id`/`employee_id` 이중 키 회귀.

### 5-7. admin ↔ settings ↔ feature_flags

- **위험**: admin → settings (write) + settings → feature_flags (read) + feature_flags → admin (현재 부재) → 잠재 순환.
- **정리 방향**: admin → settings → feature_flags 단방향. settings ⊥ admin 역참조. feature_flags 는 read-only 단일 진실원천 — `core/feature_flags.py` 안에서 env / AiSetting 파생 (T-8 19-P-2).
- **wrapper 필요**: feature_flags 는 import-time 1회 로드 + read-only.
- **테스트 필요**: `test_ai_assist_mode.py` (ai_mode 파생) + `test_local_only_mode.py`.

### 5-8. ai/commands ↔ appointments / leaves / sms

- **위험**: ai/commands/action_leave → leaves.service write + ai/commands ?→ appointments / sms (후속) → 순환 가능성.
- **정리 방향**: ai/commands 는 *다른 도메인 service 호출*만 가능. 도메인 → ai 호출 ⊥. action_leave 는 leaves.service 의 read+write 헬퍼만 사용 (`_upsert_employee_leave_core`).
- **wrapper 필요**: leaves.service.upsert_leave(*, source="ai"|"manual") 인자로 호출 출처 표시 — audit 분기.
- **테스트 필요**: `test_ai_action_leave.py` (1232줄) 회귀 + HMAC + TOCTOU.

### 5-9. health ↔ ai / backup / settings

- **위험**: health → ai/health (read) + ai/health → core/feature_flags + feature_flags → ai/health → 잠재 3차 순환.
- **정리 방향**: health 는 *모든 모듈을 read-only* 로 호출. 다른 모듈 → health 호출 ⊥. core/feature_flags 는 ai/health 의존성 끊기 — env + AiSetting 직접 read.
- **wrapper 필요**: ai/health.build_admin_status() 가 단일 진실원천 (현재) — health 모듈은 이를 read 만.
- **테스트 필요**: `test_ai_health_status.py` + 신규 `test_health_*` (post-19-P).

### 5-10. audit / logs ↔ 모든 모듈

- **위험**: 모든 모듈 → audit 호출 ✅. 단, audit 내부에서 도메인 service 호출 ⊥ (단방향).
- **정리 방향**: audit.service.audit() 시그니처 보존. PII 원문 ⊥ (D-9). detail 500자 cap.
- **wrapper 필요**: 없음 (현재 시그니처 그대로).
- **테스트 필요**: audit insert 회귀 (모든 CUD 호출지).

---

## 6. 안전한 분리 순서에 주는 영향

> 19-P-3 §31-§32 우선순위와 의존성 분석 정합 검증.

### 6-A. 먼저 분리해도 안전한 모듈 (의존성 ↓)

| 순서 | 모듈 | 의존성 분석 |
|---|---|---|
| 1 | **core** (M-25) | core ⊥ modules (D-4). 다른 모듈이 의존하지만 core 자체는 외부 의존 ↓. |
| 2 | **audit** (M-14) | audit 단방향 (D-9). 모든 모듈이 호출하지만 audit 가 호출하는 모듈 0. |
| 3 | **settings** (M-15) | SystemSetting 단일. settings ⊥ 역참조 (D-10). |
| 4 | **staff (M-03 + M-03b)** | leaves / treatments / appointments 가 read 만. staff → leaves/appointments write ⊥. |
| 5 | **treatments + completion_rules (M-05 + M-06)** | treatments → patients.repository write (done_count) — 단일 흐름. 명확. |

### 6-B. 의존성이 많아 나중에 분리할 모듈 (의존성 ↑)

| 순서 | 모듈 | 의존성 분석 |
|---|---|---|
| 14 (마지막) | **appointments** (M-01) | patients / staff / treatments / leaves / availability / audit / sms (후속) / stats (후속) — **6개 도메인 의존**. 모든 도메인 분리 후 진입. |
| 12 | **ai 모듈 일괄** (M-17~M-24) | ai/router → 부도메인 + ai/commands → leaves + ai/rag → 도메인 ⊥ (D-6). 응답 키 33+ + manual_qa wrapper + LOW_SCORE_THRESHOLD 등 정책 보존. |
| 9 | **sms + sms.provider** (M-09 + M-29) | sms → appointments / patients / staff / settings / templates / provider / audit — **6개 의존**. 외부 API + 발송 비용. |

### 6-C. 테스트 보강 후 분리해야 할 모듈

§5 순환 위험 구간을 가진 모듈 + 19-P-3 §34 contract 미작성 모듈:

- **appointments** — 5-1 / 5-2 / 5-3 / 5-4 모두 영향
- **leaves** — 5-1 / 5-6 / 5-8 영향 + AI action_leave 회귀 보호
- **stats** — 5-4 영향 + 8 endpoint contract 신규
- **sms** — 5-3 영향 + 발송 비용
- **availability** — 5-1 / 5-2 영향 + am/pm 반차 정책 추출 정합

### 6-D. wrapper / adaptor 가 필요한 구간

| 구간 | wrapper 형식 | 사유 |
|---|---|---|
| `_upsert_employee_leave_core` | leaves.service.upsert_leave(source="ai"\|"manual") | AI action_leave 가 같은 헬퍼 호출 — 시그니처 절대 보존 + audit 분기 |
| `manual_qa.ask_manual_question(provider_override=)` | 그대로 보존 (이미 wrapper) | 라우터/테스트 모두 keyword 인자 의존 |
| `audit()` / `_log()` | audit.service.audit(...) 그대로 보존 | 모든 CUD 호출지 — 시그니처 변경 금지 |
| treatments → patients.repository write | treatments.completion_rules.bump(patient_id, treatment_code, delta) | `_bump_patient_count` 정책 (Lazy 생성, 0 미만 방지) 보존 |
| sms → 외부 munjanara | sms.provider.send(text, recipients) — timeout / 디코딩 정책 보존 | 외부 API 직접 호출 분리 |
| availability 차단 | appointments.availability.is_slot_available(...) | 점심창 + 휴무 (am/pm/full) + 충돌 통합 |
| ai/commands ↔ leaves | leaves.service.upsert_leave 의 source 인자 | 5-8 정리 |

### 6-E. DB schema 변경 없이 먼저 분리 가능한 모듈

19-P-3 §37 그대로 — 19-P 안 13 modules + core 모두 m001~m013 그대로 진행 가능. 의존성 분석 결과 **DB 마이그레이션 없이 안전 분리 가능**:

- core / audit / settings / staff / treatments / patients / leaves / stats / sms / admin / backup / ai / export_import + appointments + availability.

후속 검토 (m014+ 동반): doctors EMR / Patient.doctor_id / DoctorSchedule / Order / Prescription / 노쇼 컬럼.

---

## 7. 향후 코드 주석 / 문서화 기준 (의존성 지점)

> 본 19-P-4 세션은 코드 무수정 — 위치만 표시. 19-P-5+ 단계에서 후속 세션이 추가.

### 7-A. COMPAT 주석 후보

| 위치 | 사유 |
|---|---|
| `manual_qa.ask_manual_question(provider_override=)` | wrapper 시그니처 절대 보존 |
| `_upsert_employee_leave_core` | AI action_leave 가 같은 헬퍼 호출 |
| `audit()` / `_log()` | 모든 CUD 호출지 — 시그니처 변경 금지 |
| `/api/therapist-leaves` 응답 `therapist_id`/`employee_id` 이중 키 | alias 보존 |
| `/api/treatment-meta` 응답 `doctor_treatments`/`manual_codes`/`eswt_code` 키 | 프론트 분기 |
| `manual/search` 3키 + `manual/ask` 9키 + sources 3키 + health 9키 + health/public 4키 + status 9키 | v1.3.3 응답 계약 |
| ENTITY_MAP 9개 키 (`services/sync.py`) | 외부 노드 호환 |

### 7-B. SAFETY 주석 후보

| 위치 | 사유 |
|---|---|
| `pii.scan` + `_safe_error_detail` (200자 cap) | PII 마스킹 |
| `_mask_phone_for_log` / `_sms_sanitize` | SMS 비밀 마스킹 |
| `ai/logging.py` | sha256 해시만 — 원문 미저장 |
| API key 응답 비노출 (`api_key_set` boolean 만) | API key 원문 ⊥ |
| `tests/conftest.py:_block_sdk_modules` | 외부 SDK 차단 |
| `engine.dispose()` + atomic rename (backup) | 운영 DB 교체 |
| `core/security` PBKDF2 + 5회 잠금 | 인증 |
| AI/RAG ⊥ 도메인 DB write (D-6) | local-first |
| AI 가 의사 정보 임의 생성 ⊥ (M-36) | 후속 가드 |

### 7-C. NOTE 주석 후보

| 위치 | 사유 |
|---|---|
| `manual60 count_increment=1` | CLAUDE.md 절대 금지 |
| `LOW_SCORE_THRESHOLD=2` / `HIGH_THRESHOLD=0.7` / `LOW_THRESHOLD=0.3` / `QUERY_MIN_CHARS=2` | 임계치 — 별도 결정 후 변경 |
| `_lunch_window` / `_check_lunch_block` | 점심창 정책 |
| `_doctor_codes_set` / `is_doctor_filter` | role=doctor 분기 정책 |
| `pyproject.toml app/**/*.py per-file-ignores` | CLAUDE.md 명시 |
| 자동 백업 타이머 daemon=True | conftest 람다 교체 |
| `leave_type ∈ {am, pm, full}` DB 표준 | action_leave + 차단 정책 |

### 7-D. RISK 주석 후보

| 위치 | 사유 |
|---|---|
| `_check_version` / `_bump_version` (Appointment 낙관적 락) | TOCTOU |
| split-code TOCTOU | 동시 분리 위험 |
| AI action_leave HMAC + TOCTOU | 토큰 + 락 |
| reindex lock + DELETE 금지 (`indexer.py`) | 부분 실패 보존 |
| atomic rename Windows (`restore`) | 파일 lock |
| ENTITY_MAP 외부 노드 호환 | 키 변경 ⊥ |
| `dosu_clinic.spec` hidden imports | 신규 모듈 동기화 |
| `_upsert_employee_leave_core` 시그니처 (AI 도 호출) | 변경 ⊥ |
| availability 반차 차단 (am/pm) — 현재 인라인 | 추출 시 누락 위험 |
| `core/feature_flags ↔ ai/health` 잠재 순환 (T-8) | 한쪽 read-only 분리 필요 |

### 7-E. TEMP / TODO 주석 후보

> 분리 진행 중 일시 wrapper / adaptor — 후속 세션에서 제거.

| 위치 | 후속 제거 시점 |
|---|---|
| `from app.routers.api import _legacy_X` 임시 wrapper | 분리 commit 후 N+1 세션 |
| `from app.services.sync import ENTITY_MAP` legacy 키 | post-19-P sync 위치 결정 후 |
| `from app.services.rag.search import _load_index` (legacy keyword index) | 19-5 (M-23) ai/knowledge 통합 결정 후 |
| availability 차단 인라인 → 헬퍼 추출 직후 wrapper | 19-P-N (appointments 분리) commit 후 N+1 |

---

## 8. 종합

- 30 모듈 의존성 분석 결과 **D-1 ~ D-13** 13개 원칙 + **9개 순환 위험 구간** 식별.
- 즉시 분리 (A) 13 modules + core 모두 **DB 마이그레이션 없이 진행 가능** (§6-E).
- 의존성 *낮은* 순서: core → audit → settings → staff → treatments → leaves → patients → stats → sms → admin / backup → ai → feature_flags → **appointments (마지막)**.
- 위험 구간 9개 모두 wrapper / adaptor 또는 단방향 정리로 해결 가능 (§5).
- 후속 검토 (post-19-P): doctors 별도 모듈 (M-31~M-35) / calendar / notes 통합 / health 신규 / sync 위치 / 노쇼 컬럼 / AI 의사 가드 (M-36).
- 19-P-3 Codex r1 caveat 3개 모두 반영 — symbol 위주 / `leave_type` 값 명시 / dirty 표현 정확.
- 다음 문서: `docs/refactor/19_refactor_test_strategy.md` (19-P-5) — 본 §의 9 순환 위험 구간 + §6-C 테스트 보강 필요 모듈을 **분리 직전 / 직후 contract 테스트 전략** 으로 구체화.
