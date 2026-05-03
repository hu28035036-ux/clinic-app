# 19-P-7 단위화 리팩토링 — 위험 등록 (19_refactor_risk_register, r3 보정본)

> 19-P-1 [현재 구조](19_refactor_current_state.md), 19-P-2 [목표 아키텍처](19_refactor_target_architecture.md),
> 19-P-3 [모듈 매핑](19_refactor_module_map.md), 19-P-4 [의존성 맵](19_refactor_dependency_map.md),
> 19-P-5 [테스트 전략](19_refactor_test_strategy.md), 19-P-6 [롤아웃 계획](19_refactor_rollout_plan.md) 의 후속 문서.
> 단위화 리팩토링 중 발생할 수 있는 위험을 기능별 / 모듈별로 정리하고,
> 방지 방법 / 필요한 테스트 / rollback 기준 / Codex 검증 포인트를 위험 항목 단위로 등록한다.
> 본 문서는 *위험 등록* 문서 — 실제 코드 / 테스트 / fixture / mock 미생성.

## 0. 메타

- 작성일: 2026-05-02 (r1) / 2026-05-03 (r2)
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-7 진입 가능)** ([reports/refactor/19-P-6_codex_review.md](../../reports/refactor/19-P-6_codex_review.md))
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *위험 등록* 문서 — 새 폴더 / 파일 / 테스트 / fixture 미생성.
- **r1 Codex 검증 (2026-05-03 pass with caveat — yes 19-P-8 진입 가능)** + **r2 Codex 재검증 (2026-05-03 fail — taxonomy 숫자 정정 미완료)** 후 본 r3 보정 — 보정 이력:
  - **r2 보정** (r1 caveat — taxonomy 정리 시도, 4개 항목): TIME 키 추가 / FF·PRIV·NOTES 통합 표시 / R-LOCK-04 통합 메모 격하 / "약 70개" → 정정 시도. **결과: r2 가 주장한 숫자 ("21 prefix / 78 제목 / 약 74 순수") 가 실제 파일과 불일치 → Codex r2 fail**.
  - **r3 보정** (Codex r2 fail caveat — taxonomy 숫자 실측 정합):
    - (1) **§1-3 카테고리 키 표 = 23행** (단독 Risk prefix **20개** + 통합 키 **3개** — FF / PRIV / NOTES) — r2 의 "21 prefix" 주장 정정.
    - (2) **§2 섹션 = 23개** (2-A ~ 2-W, 그 중 3개 = 2-M notes / 2-R feature_flags / 2-T privacy 는 통합 메모 섹션, 별도 Risk ID 부재).
    - (3) **실제 Risk ID 제목 = 77개** (`grep -cE "^#### R-"` 실측) — r2 의 "78개" 주장 정정. R-LOCK-04 는 별도 Risk ID 제목이 아니라 통합 메모 (R-BAK-03 atomic rename 통합).
    - (4) **순수 등록 Risk ID = 77개** (R-LOCK-04 격하 후 R-* 제목 = 모두 단독 Risk ID). r2 의 "약 74개" 표현 폐기.
    - (5) §8 종합 + 본 요청서 §2 / §15 모두 23 / 23 / 77 / 77 기준으로 동기화.
    - 본 r3 는 메타 숫자 정정만 — 실제 위험 항목 / 위험도 분류 / 모듈별 매핑 / 세션별 연결 / 주석 매트릭스 모두 r1 시점 그대로 유지. Codex r1 G-1 ~ G-12 (G-2 / G-11 r2 fail) 결과는 r3 에서 G-2 / G-11 정정으로 pass 복귀 기대.

### 0-1. 18-AI 알려진 위험 본 19-P-7 통합

[docs/releases/18_ai_rag_known_risks.md](../releases/18_ai_rag_known_risks.md) §1 ~ §8 의 위험 / 후속 / 사고 대응 항목을 본 위험 등록의 AI / RAG / privacy / batch / monitoring 카테고리에 통합 (R-AI-* / R-PRIV-* / R-OPS-* 등).

### 0-2. 본 문서가 다루지 않는 범위

- 실제 코드 이동 / 테스트 작성 — 19-0 이후 별도 세션.
- m014+ 마이그레이션 도입 결정 — 본 19-P 비-목표 (19-P-2 P-4 정합).
- 위험 평가 외 *모니터링 지표 임계값 결정* — 운영 단계 별도 결정.

---

## 1. 위험 등록 기준

### 1-1. 위험 항목 형식 (사용자 §1 기준)

각 위험 항목은 아래 14개 필드로 등록.

| 필드 | 설명 |
|---|---|
| Risk ID | `R-{카테고리}-{번호}` 형식 (예: `R-APPT-01`) |
| 위험 이름 | 1줄 한국어 |
| 관련 모듈 | 19-P-3 모듈 매핑 + 19-P-2 § 분류 |
| 위험 설명 | 무엇이 어떻게 깨지는지 (2~5줄) |
| 발생 가능성 | 낮음 / 중간 / 높음 |
| 영향도 | 낮음 / 중간 / 높음 |
| 전체 위험도 | 낮음 / 중간 / 높음 / 치명 (= 가능성 × 영향도) |
| 발생 징후 | 어떤 증상이 나타나면 본 위험이 발생한 것인지 |
| 방지 방법 | 본 위험을 막기 위한 작업 / 정책 |
| 필요한 테스트/하네스 | 19-P-5 §2 + §4 보강 항목 매핑 |
| 필요한 주석 태그 | COMPAT / SAFETY / NOTE / RISK / TODO / TEMP — 19-P-6 §4 정합 |
| rollback 기준 | 19-P-6 §7 RB-1 ~ RB-10 매핑 |
| Codex 검증 포인트 | Codex 가 독립 확인할 항목 |
| 비고 / 확인 필요 | 19-P-1~6 미해결 캐비엇 + 추가 |

### 1-2. 위험도 매트릭스

| 가능성 \ 영향도 | 낮음 | 중간 | 높음 |
|---|---|---|---|
| **낮음** | 낮음 | 낮음 | 중간 |
| **중간** | 낮음 | 중간 | 높음 |
| **높음** | 중간 | 높음 | **치명** |

### 1-3. 카테고리 키 (Risk ID 접두)

> **r2 보정** — Codex r1 caveat 정합. **TIME 키 추가** (R-TIME-01 누락 보정). **FF / PRIV / NOTES 키는 통합 처리** (별도 Risk ID 부여 ⊥, 다른 카테고리에 위험 등록).

| 키 | 카테고리 | 분류 | Risk ID 위치 |
|---|---|---|---|
| APPT | appointments (예약) | 단독 | R-APPT-01 ~ 07 |
| PAT | patients / notes | 단독 (notes 통합) | R-PAT-01 ~ 05 |
| THER | therapists | 단독 | R-THER-01 ~ 03 |
| DOC | doctors / medical_staff (후속 검토) | 단독 | R-DOC-01 ~ 02 |
| LEAVE | leaves (휴무) | 단독 | R-LEAVE-01 ~ 04 |
| TX | treatments / completion_rules | 단독 | R-TX-01 ~ 04 |
| STAT | stats (통계) | 단독 | R-STAT-01 ~ 05 |
| SMS | sms | 단독 | R-SMS-01 ~ 05 |
| ADM | admin / settings (+ feature_flags 통합) | 단독 + FF 통합 | R-ADM-01 ~ 05 (R-ADM-04 가 feature_flags 위험) |
| BAK | backup / restore | 단독 | R-BAK-01 ~ 05 |
| AI | ai / rag / safety / vector / hybrid | 단독 | R-AI-01 ~ 07 |
| CAL | calendar / schedule_view (post-19-P) | 단독 | R-CAL-01 ~ 04 |
| AUDIT | audit / logs | 단독 | R-AUDIT-01 ~ 02 |
| HEALTH | health / diagnostics (post-19-P) | 단독 | R-HEALTH-01 |
| EXIM | export_import | 단독 | R-EXIM-01 ~ 02 |
| CORE | core / responses / errors | 단독 | R-CORE-01 ~ 05 |
| **TIME** (r2 추가) | time_utils | 단독 | R-TIME-01 |
| BATCH | batch / jobs | 단독 | R-BATCH-01 |
| LOCK | concurrency / locking | 단독 | R-LOCK-01 ~ 03 (LOCK-04 = R-BAK-03 통합 메모) |
| OPS | 운영 / 배포 / PyInstaller | 단독 | R-OPS-01 ~ 06 |
| **FF** (통합) | feature_flags | 통합 — ADM 카테고리 안 (R-ADM-04) | (별도 Risk ID 부재) |
| **PRIV** (통합) | privacy / retention | 통합 — PAT (R-PAT-01) + AI (R-AI-07) + AUDIT (R-AUDIT-02) | (별도 Risk ID 부재) |
| **NOTES** (통합) | notes | 통합 — PAT 카테고리 안 (R-PAT-04 ~ 05) | (별도 Risk ID 부재) |

**Taxonomy 합계** (r3 보정 — Codex r2 fail caveat 실측 정합):
- **§1-3 카테고리 키 표 = 23행** (단독 Risk prefix **20개** + 통합 키 **3개** — FF / PRIV / NOTES). 단독 prefix 20개: APPT / PAT / THER / DOC / LEAVE / TX / STAT / SMS / ADM / BAK / AI / CAL / AUDIT / HEALTH / EXIM / CORE / TIME / BATCH / LOCK / OPS.
- **§2 섹션 = 23개** (2-A ~ 2-W) — 그 중 3개 (2-M notes / 2-R feature_flags / 2-T privacy) = **통합 메모 섹션** (별도 Risk ID 부재, 다른 섹션 참조).
- **실제 Risk ID 제목 = 77개** (`grep -cE "^#### R-" docs/refactor/19_refactor_risk_register.md` 실측). R-LOCK-04 는 별도 Risk ID 제목이 아니라 통합 메모 (`#### (통합 메모) atomic rename` → R-BAK-03 통합).
- **순수 등록 Risk ID = 77개** (모두 단독 Risk ID — R-LOCK-04 격하 후).
- **카테고리별 Risk ID 합계** (r3 실측): APPT 7 + PAT 5 + THER 3 + DOC 2 + LEAVE 4 + TX 4 + STAT 5 + SMS 5 + ADM 5 + BAK 5 + AI 7 + CAL 4 + AUDIT 2 + HEALTH 1 + EXIM 2 + CORE 5 + TIME 1 + BATCH 1 + LOCK 3 + OPS 6 = **77 ✓**.

---

## 2. 위험 항목 (카테고리별)

### 2-A. appointments (예약)

#### R-APPT-01 — 예약 생성 / 수정 / 삭제 API 응답 key 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments (19-9) |
| 위험 설명 | `_serialize_appointment` ([api.py:186](../../app/routers/api.py:186)) 의 응답 dict 키 (`id` / `patient_id` / `therapist_id` / `start_at` / `end_at` / `treatment_codes` / `status` / `version` / `memo` / `is_new_patient`) 가 변경되면 main.html FullCalendar event 표시 + 환자 모달 + 통계 / 엑셀 export 가 동시 깨짐. |
| 발생 가능성 | 중간 (대규모 분리 시 dict 빌드 위치 다중 — 누락 가능성) |
| 영향도 | 높음 (UI 동시 깨짐 + 외부 노드 sync `ENTITY_MAP` 영향) |
| 전체 위험도 | **높음** |
| 발생 징후 | (a) FullCalendar event 미표시 / 색상 누락. (b) `j.detail` 메시지 깨짐. (c) `version` 필드 부재 → 낙관적 락 항상 실패. |
| 방지 방법 | 19-9 분리 직전 응답 키 contract 테스트 추가 (10 endpoint). dict 단위 비교 (분리 전후). FastAPI APIRouter `prefix` 만 모듈별 재할당. |
| 필요한 테스트 | 19-P-5 §4 (6 비-AI contract — C-1) + 신규 PUT/DELETE/409 contract (19-4 / 19-9 분리 직전 보강). `test_appointment_rules.py` 회귀. |
| 주석 태그 | `# COMPAT:` (응답 dict 빌더 / version 필드) |
| rollback 기준 | RB-1 (응답 키 변경) / RB-2 (예약 결과 변경). |
| Codex 검증 | `_serialize_appointment` 응답 dict 키 100% 보존. FullCalendar event 형식. |
| 비고 | 19-P-1 §22 C-1 (86 endpoint contract 부재). 19-9 분리 직전 보강 필수. |

#### R-APPT-02 — 예약 중복 검사 누락 (도수 중복 차단 백엔드 미구현)

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments (19-4 availability / 19-9) |
| 위험 설명 | spec 01 §1 "도수치료 같은 슬롯 중복 시 두 번째 차단" 정책이 백엔드에 미구현. 현재 [test_appointment_rules.py](../../tests/test_appointment_rules.py) 의 `test_two_manual30/60_same_slot_blocked`, `test_eswt_then_manual30_same_slot_blocked` 3건이 `xfail`, 취소-후-중복 1건이 `skip`. devtools / manual POST 로 우회 시 중복 예약 발생 가능. |
| 발생 가능성 | 높음 (현재 백엔드 차단 코드 자체 부재) |
| 영향도 | 높음 (도수 슬롯 충돌 → 운영 환경 직접 영향) |
| 전체 위험도 | **치명** |
| 발생 징후 | 같은 치료사 / 시간 / 환자 (또는 다른 환자) 의 manual30 / manual60 예약이 두 건 이상 동시 등록됨. |
| 방지 방법 | 19-4 availability 분리 시 백엔드 차단 코드 신설 + `xfail` → 정방향 전환 + `skip` 활성화. 비도수 (eswt / injection) 중복 허용 정방향 회귀 보존. |
| 필요한 테스트 | `test_appointment_rules.py` 의 `xfail` 3건 + `skip` 1건 → 정방향 전환 + 비도수 허용 회귀 (`test_two_eswt_same_slot_allowed` / `test_injection_and_eswt_same_slot_allowed`). |
| 주석 태그 | `# NOTE:` (도수 중복 차단 spec 01) / `# RISK:` (devtools 우회 방지 — 백엔드 검증 필수). |
| rollback 기준 | RB-2 (예약 결과 변경). |
| Codex 검증 | `_check_lunch_block` / 충돌 검증 코드 위치 grep. xfail 3건 + skip 1건 정방향 전환. |
| 비고 | 19-P-4 caveat / 19-P-5 §3-1 / 19-P-6 §3-4. 19-4 보강 필수. |

#### R-APPT-03 — 치료사 휴무일 예약 차단 누락 (백엔드 미구현)

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments (19-4) ↔ leaves (19-5) |
| 위험 설명 | spec 02 "휴무일 치료사 예약 차단" 정책이 백엔드에 미구현. 현재 [test_therapist_leave.py](../../tests/test_therapist_leave.py) 의 full / am / pm 차단 4건 모두 `xfail` (백엔드 미구현 명시). 휴무 등록은 동작하지만 예약 차단은 안 됨. |
| 발생 가능성 | 높음 (현재 백엔드 차단 자체 부재) |
| 영향도 | 높음 (휴무 치료사에게 예약 배정 → 운영 사고) |
| 전체 위험도 | **치명** |
| 발생 징후 | 휴무 등록된 치료사 (full) 의 휴무일에 예약 등록이 200 응답으로 통과. |
| 방지 방법 | 19-4 availability 분리 시 백엔드 차단 코드 신설 — `EmployeeLeave.leave_date` ↔ `Appointment.appt_date` 충돌 검사 + `leave_type=full` 시 항상 차단. 19-5 leaves 분리 시 `_upsert_employee_leave_core` 단일 진실원천 보존. |
| 필요한 테스트 | `test_therapist_leave.py` 의 `xfail` 4건 → 정방향 전환 + 반차 허용 시간대 정방향 (`test_morning/afternoon_leave_allows_*` / `test_normal_day_for_full_day_leave_therapist_works`) 회귀 보존. |
| 주석 태그 | `# NOTE:` (휴무 차단 spec 02) / `# RISK:` (devtools 우회 — 백엔드 검증 필수). |
| rollback 기준 | RB-3 (휴무 차단 깨짐). |
| Codex 검증 | xfail 4건 정방향 전환. 반차 허용 회귀 0. |
| 비고 | 19-P-4 caveat / 19-P-5 §3-5 핵심. 19-4 / 19-5 보강 필수. |

#### R-APPT-04 — 오전반차 / 오후반차 차단 기준 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments (19-4) ↔ leaves (19-5) |
| 위험 설명 | `leave_type="am"` (< 12:00 차단) / `leave_type="pm"` (>= 12:00 차단) 기준이 분리 시 잘못 변경되면 (예: 13:00 기준 / 11:30 기준) 반차 시간대 예약이 잘못 통과 / 차단됨. |
| 발생 가능성 | 중간 (12:00 기준 명시적 코드 신설 시점) |
| 영향도 | 높음 (반차 운영 정책 위반) |
| 전체 위험도 | **높음** |
| 발생 징후 | 오전반차 치료사의 13:00 예약이 200 거부 / 오후반차 치료사의 11:00 예약이 200 거부. |
| 방지 방법 | 12:00 정확 기준 명시 (test_therapist_leave.py 의 `_start(11, 0)` / `_start(14, 0)` 정합). 반차 허용 시간대 정방향 회귀. |
| 필요한 테스트 | `test_morning_leave_blocks_before_noon` / `test_afternoon_leave_blocks_after_noon` (정방향 전환 후) + `test_morning_leave_allows_after_noon` / `test_afternoon_leave_allows_before_noon`. |
| 주석 태그 | `# NOTE:` (`leave_type=am/pm` 기준 = 12:00 정확). |
| rollback 기준 | RB-3 (휴무 차단 깨짐). |
| Codex 검증 | 12:00 기준 정확 (테스트 시드의 `am`/`pm` 분기). |
| 비고 | 19-5 leaves 분리 시 `leave_type` DB 표준 보존. |

#### R-APPT-05 — 예약 가능 시간 계산 오류 (점심창)

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments (19-4) |
| 위험 설명 | `_lunch_window` ([api.py:64-107](../../app/routers/api.py:64)) 의 점심 시간대 차단 로직이 분리 시 누락 / 변경되면 점심 시간대 예약이 200 통과. |
| 발생 가능성 | 중간 |
| 영향도 | 중간 (운영 정책 위반 — 사용자 운영 환경에 따라 영향도 차이) |
| 전체 위험도 | 중간 |
| 발생 징후 | 점심 시간 (예: 12:30) 예약이 200 통과. |
| 방지 방법 | `_lunch_window` / `_check_lunch_block` 추출 시 함수 시그니처 보존 + 점심창 contract 테스트 신규 추가. |
| 필요한 테스트 | 신규 점심창 차단 contract (19-P-5 §3-1 부재). |
| 주석 태그 | `# NOTE:` (점심창 정책). |
| rollback 기준 | RB-2 (예약 결과 변경). |
| Codex 검증 | `_check_lunch_block` 호출지 보존. |
| 비고 | 19-P-5 §3-1 의 "점심창 차단 테스트 부재" 정합. |

#### R-APPT-06 — devtools / manual POST 우회 방지 실패

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments (19-9) ↔ availability (19-4) |
| 위험 설명 | 프론트 검증만으로 차단되고 백엔드 검증이 wrapper 분리 시 누락되면 devtools / curl / Postman 으로 점심창 / 충돌 / 휴무 / 반차 / 낙관적 락 우회 가능. |
| 발생 가능성 | 중간 (wrapper 패턴 시 호출 누락 가능) |
| 영향도 | 높음 (모든 운영 정책 우회) |
| 전체 위험도 | **높음** |
| 발생 징후 | curl / Postman 으로 직접 POST 시 정책 위반 예약이 200 통과. |
| 방지 방법 | router 핸들러에서 service 호출 → service 가 rules.py + availability.py 모두 호출. 백엔드 검증 빠짐 ⊥. CLAUDE.md "프론트에서 막는 기능은 반드시 백엔드에서도 검증" 정책. |
| 필요한 테스트 | router → service → rules / availability 호출 흐름 통합 테스트. |
| 주석 태그 | `# RISK:` (devtools 우회 방지 — 백엔드 검증 필수) / `# NOTE:` (CLAUDE.md 정책). |
| rollback 기준 | RB-2 / RB-3. |
| Codex 검증 | wrapper 패턴 시 service 호출 누락 0. |
| 비고 | CLAUDE.md 명시 정책. |

#### R-APPT-07 — 예약 상태 / 취소 / 노쇼 후보가 통계와 충돌

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments ↔ stats (19-11) |
| 위험 설명 | 현재 `Appointment.status` ENUM (`reserved` / `approved` / `canceled`) 만 존재. 노쇼 별도 필드 부재. 19-11 stats 분리 시 status 분기 (`is_new_patient` 카운트 / 취소 제외 등) 가 잘못되면 통계 결과 변경. |
| 발생 가능성 | 중간 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | summary / by-therapist 응답의 카운트 변경. |
| 방지 방법 | 19-11 stats 분리 시 status 분기 흐름 보존. 노쇼 별도 필드 신설 ⊥ (19-P 비-목표 — m014+ post-19-P). |
| 필요한 테스트 | `test_stats_counts.py` 회귀 + 신규 8 endpoint contract (C-7). |
| 주석 태그 | `# NOTE:` (status 분기 — `canceled` 만 통계 제외) / `# TODO(post-19-P):` (노쇼 별도 컬럼 m014+). |
| rollback 기준 | RB-6 (통계 기준 변경). |
| Codex 검증 | `is_new_patient` 카운트 + status 분기 무변경. |
| 비고 | 19-P-2 §3-6 / 19-P-6 §9 F-10 (노쇼 후속 검토). |

### 2-B. patients / notes

#### R-PAT-01 — 환자 개인정보 로그 노출

| 필드 | 값 |
|---|---|
| 관련 모듈 | patients (19-7) ↔ audit (19-12) ↔ ai (19-13) |
| 위험 설명 | 환자명 / 연락처 / 차트번호 / 메모 원문이 `audit_log.detail`, `AiUsageLog.error_detail`, traceback, 응답 본문, AI 로그에 노출되면 PII 사고. |
| 발생 가능성 | 중간 (분리 시 audit / log 호출 위치 변경 가능) |
| 영향도 | 높음 (PII 사고 → 법적 / 운영 사고) |
| 전체 위험도 | **치명** |
| 발생 징후 | `audit_log.detail` 또는 `AiUsageLog.error_detail` 에 010 / 주민번호 / 환자명 원문이 그대로 저장됨. |
| 방지 방법 | `pii.scan` + `_safe_error_detail` (200자 cap) + sha256 해시 정책 보존. PBKDF2 / API key 마스킹 정책 보존. AiUsageLog 의 `prompt_hash` / `response_hash` 만 저장 — 원문 ⊥. |
| 필요한 테스트 | `test_ai_safety_harness.py` (153줄) + `test_ai_logging.py` (216줄). 비-AI 도메인 audit 호출 시 PII 부재 회귀. |
| 주석 태그 | `# SAFETY:` (PII 마스킹 / sha256 / 200자 cap / 원문 ⊥). |
| rollback 기준 | RB-7 / 추가 PII 회귀. |
| Codex 검증 | 모든 audit / log 호출지에서 PII 원문 부재. |
| 비고 | [docs/AI_WORKING_RULES.md §1.5](../AI_WORKING_RULES.md) 절대 원칙. |

#### R-PAT-02 — 환자 검색 결과 구조 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | patients (19-7) |
| 위험 설명 | `GET /api/patients/search` 응답 dict 키 (`id` / `name` / `phone_masked` / `chart_no` / `last_visit` 등) 변경 → 환자 검색 자동완성 + 예약 모달 깨짐. |
| 발생 가능성 | 낮음 (분리 시 wrapper 보존 가능) |
| 영향도 | 중간 (UI 직접 깨짐) |
| 전체 위험도 | 중간 |
| 발생 징후 | 환자 검색 자동완성에 결과 미표시 / 잘못된 필드 매핑. |
| 방지 방법 | 19-7 분리 직전 응답 키 contract 추가 (이름/연락처/차트번호 인덱스). |
| 필요한 테스트 | 신규 환자 검색 contract (19-P-5 §4 항목 11). |
| 주석 태그 | `# COMPAT:` (검색 응답 dict 키). |
| rollback 기준 | RB-1. |
| Codex 검증 | 검색 인덱스 (이름/연락처/차트번호) 결과 무변경. |
| 비고 | 19-P-1 §22 C-1. |

#### R-PAT-03 — 신환 체크 기준 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | patients ↔ appointments ↔ stats |
| 위험 설명 | `Appointment.is_new_patient` 카운트 기준이 분리 시 잘못 변경되면 stats summary 의 신환 수 결과 변경. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | summary 신환 카운트 변경. |
| 방지 방법 | `is_new_patient` 컬럼 / 결정 로직 보존 — 19-9 appointments 분리 시 wrapper. |
| 필요한 테스트 | `test_stats_counts.py` (신환 카운트). |
| 주석 태그 | `# NOTE:` (신환 결정 정책). |
| rollback 기준 | RB-6. |
| Codex 검증 | summary 신환 카운트 결과 무변경. |
| 비고 |  |

#### R-PAT-04 — 당일메모 / 지속 메모 경계 혼재

| 필드 | 값 |
|---|---|
| 관련 모듈 | patients / notes (19-7 + post-19-P) |
| 위험 설명 | `Patient.memo` (지속) 와 `Appointment.memo` (당일) 가 분리 시 잘못 매핑되면 의미 충돌 — 당일 메모가 환자 영구 메모로 저장 / 지속 메모가 예약마다 표시. |
| 발생 가능성 | 중간 (의미 명시 부재) |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 환자 메모에 일회성 메모 표시 / 예약마다 같은 메모 반복. |
| 방지 방법 | 19-7 patients 분리 시 `Patient.memo` 와 `Appointment.memo` 의미 차이 명시. 통합 `modules/notes/` 는 post-19-P (정책 결정 후). |
| 필요한 테스트 | `PATCH /api/patients/{pid}/memo` contract — 다른 환자 영향 X. |
| 주석 태그 | `# NOTE:` (`Patient.memo` vs `Appointment.memo` 의미 차이) / `# TODO(post-19-P):` (`modules/notes/` 통합). |
| rollback 기준 | 메모 의미 충돌 발생 시 즉시. |
| Codex 검증 | 두 컬럼의 분리 보존. |
| 비고 | 19-P-6 §3-7 / §9 F-12. |

#### R-PAT-05 — 환자별 메모와 예약별 메모 잘못 연결

| 필드 | 값 |
|---|---|
| 관련 모듈 | patients ↔ appointments |
| 위험 설명 | `PATCH /api/patients/{pid}/memo` 가 다른 환자의 메모에 영향 / 예약 모달 메모가 다른 예약에 표시. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 (개인정보 혼재) |
| 전체 위험도 | 중간 |
| 발생 징후 | 환자 A 메모 수정이 환자 B 메모 변경 발생. |
| 방지 방법 | UPDATE WHERE id 절 정확 — 19-7 분리 시 SQL 흐름 보존. |
| 필요한 테스트 | 메모 PATCH 다른 환자 영향 X 테스트. |
| 주석 태그 | `# SAFETY:` (메모는 PII 포함 가능). |
| rollback 기준 | 메모 혼재 발생 시 즉시. |
| Codex 검증 | UPDATE WHERE id 절 무변경. |
| 비고 | 19-P-5 §3-2. |

### 2-C. therapists

#### R-THER-01 — 활성 / 비활성 기준 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | therapists (19-8 staff) |
| 위험 설명 | `Employee.active` 분기가 분리 시 잘못 변경되면 비활성 치료사가 예약 / SMS / 통계 대상에 포함. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 비활성 치료사가 `/api/therapists` 응답에 표시. |
| 방지 방법 | `active=True` 필터 흐름 보존 — `_serialize_employee` 분리 시 wrapper. |
| 필요한 테스트 | `test_employee_*.py` (4 파일) 회귀. |
| 주석 태그 | `# NOTE:` (`active` 필터 정책). |
| rollback 기준 | RB-1. |
| Codex 검증 | `active` 필터 조건 무변경. |
| 비고 |  |

#### R-THER-02 — 치료 가능 항목 (`can_eswt` / `can_manual`) 연결 누락

| 필드 | 값 |
|---|---|
| 관련 모듈 | therapists ↔ treatments |
| 위험 설명 | 치료사의 `can_eswt` / `can_manual` 필드가 응답에서 누락 / 잘못 매핑되면 도수 / 체외충격파 배정이 잘못됨. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | manual30 배정이 `can_manual=False` 치료사에게 통과 / 응답에 필드 누락. |
| 방지 방법 | `_serialize_employee` 보존 + `test_employee_can_manual_contract.py` 회귀. |
| 필요한 테스트 | `test_employee_can_manual_contract.py`. |
| 주석 태그 | `# COMPAT:` (`can_eswt` / `can_manual` 응답 키). |
| rollback 기준 | RB-1. |
| Codex 검증 | `_serialize_employee` 응답 dict 보존. |
| 비고 |  |

#### R-THER-03 — 치료사 색상 표시 깨짐

| 필드 | 값 |
|---|---|
| 관련 모듈 | therapists ↔ calendar |
| 위험 설명 | `Employee.color` 응답 누락 / `_lighten_hex` 분리 시 색상 hex 변경 → FullCalendar event 색상 깨짐. |
| 발생 가능성 | 낮음 |
| 영향도 | 낮음 (UI 표시) |
| 전체 위험도 | 낮음 |
| 발생 징후 | FullCalendar event 색상 누락 / 잘못된 색상. |
| 방지 방법 | `_lighten_hex` 색상 헬퍼 보존 — 19-11 stats / 19-3 calendar 분리 시 결정 결과 무변경. |
| 필요한 테스트 | UI 자동 검증 부재 — 분리 후 사용자 수동 smoke. |
| 주석 태그 | `# NOTE:` (`_lighten_hex` 결정 hex). |
| rollback 기준 | RB-1 (UI 표시 깨짐). |
| Codex 검증 | `_lighten_hex` / `_lighten_hex_inner` 결과 무변경. |
| 비고 |  |

### 2-D. doctors / medical_staff (후속 검토 위험)

> **부재 항목** — 본 19-P 기간 내 도입 ⊥ (R-14 / 19-P-6 §9 F-1). 본 카테고리 위험은 *본 19-P 비-목표인 항목을 실제 구현된 것처럼 단정* 하는 위험만 등록.

#### R-DOC-01 — 의사 / 진료진 기능이 현재 없는 기능인데 구현된 것처럼 문서화

| 필드 | 값 |
|---|---|
| 관련 모듈 | staff (19-8) — doctors_service 얇은 분기만. |
| 위험 설명 | 19-8 staff 분리 시 `_doctor_codes_set` (얇은 분기) 외에 `Doctor` 별도 테이블 / `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` / `Order` / `Prescription` 등 부재 항목을 *문서 / docstring / 응답 키 / endpoint* 에 실제로 존재하는 것처럼 단정. |
| 발생 가능성 | 중간 (분리 시 추측 / 하이프 가능) |
| 영향도 | 높음 (운영 환경에 잘못된 기대 발생 + 후속 EMR 연동 시 호환 깨짐) |
| 전체 위험도 | **높음** |
| 발생 징후 | docstring / 응답 키 / endpoint 이름에 `doctor_id` / `department` / `room` / `schedule` / `order` / `prescription` 등이 등장. |
| 방지 방법 | 19-8 분리 시 *현재 구현된 항목만* 명시 — `Employee.role="doctor"` + `Treatment.role="doctor"` + `_doctor_codes_set()` (`injection`/`cartilage`) + `is_doctor_filter`. 별도 `modules/doctors/` 폴더 신설 ⊥ (post-19-P). |
| 필요한 테스트 | 부재 항목 grep 회귀 — `grep -nE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription" app/models/models.py` 결과 0건 유지. |
| 주석 태그 | `# TODO(post-19-P):` (`modules/doctors/` 별도 폴더 — EMR 도입 시) / `# NOTE:` (현재 = role 분기만). |
| rollback 기준 | 부재 항목이 코드에 등장 시 즉시. |
| Codex 검증 | 부재 항목 grep 0건. |
| 비고 | 19-P-2 §3-3-4 / 19-P-3 2-4 / 19-P-5 §3-4 / 19-P-6 §9 F-1. |

#### R-DOC-02 — 담당의 / 진료과 / 진료실 후보가 실제 기능으로 오해

| 필드 | 값 |
|---|---|
| 관련 모듈 | staff / patients / appointments (모두 후속 검토) |
| 위험 설명 | 사용자 / 운영자가 *후속 검토 항목* (담당의 / 진료과 / 진료실 / 자원 / 의사 일정) 을 본 19-P 결과로 인해 실제 기능이라고 오해. |
| 발생 가능성 | 중간 (문서화 톤 부주의 시) |
| 영향도 | 중간 (운영 기대 misalignment) |
| 전체 위험도 | 중간 |
| 발생 징후 | 사용자 / 운영자가 "담당의 표시 어떻게 봐요?" / "진료실 자원 관리는?" 같은 질문 발생. |
| 방지 방법 | 모든 docstring / 응답 키 / 안내 문구에서 후속 검토 항목 명시. AI / RAG 의사 가드 (M-36) 후속 보강. |
| 필요한 테스트 | RAG hallucination guard 회귀 + 의사 단정 표현 차단 패턴 후속 (post-19-P). |
| 주석 태그 | `# TODO(post-19-P):` (의사 가드 M-36) / `# SAFETY:` (AI 응답에서 의사 정보 임의 생성 차단 후속). |
| rollback 기준 | docstring / 안내 문구에 부재 항목이 실제 기능처럼 등장 시 즉시 수정. |
| Codex 검증 | docstring / 응답 / 안내 문구의 부재 항목 표현 검토. |
| 비고 | 19-P-6 §9 F-15. |

### 2-E. leaves (휴무)

#### R-LEAVE-01 — 종일 / 오전반차 / 오후반차 규칙 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | leaves (19-5) |
| 위험 설명 | `leave_type=full/am/pm` DB 표준 + `leave_kind=annual/monthly` (m009) 가 분리 시 변경 / rename 되면 휴무 등록 + 차단 + 표시 모두 영향. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | 휴무 등록 시 `leave_type` 누락 / `leave_kind` ENUM 불일치. |
| 방지 방법 | DB 표준 보존 — `EmployeeLeave` 컬럼 무변경. m011 (UNIQUE) / m009 (`leave_kind`) 보존. |
| 필요한 테스트 | `test_employee_leave_unique.py` / `test_employee_leave_kind.py`. |
| 주석 태그 | `# NOTE:` (`leave_type` / `leave_kind` DB 표준). |
| rollback 기준 | RB-3. |
| Codex 검증 | `EmployeeLeave` ORM 컬럼 무변경. |
| 비고 |  |

#### R-LEAVE-02 — 휴무 중복 처리 방식 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | leaves (19-5) |
| 위험 설명 | `(employee_id, leave_date)` UNIQUE (m011) 가 깨지면 같은 직원 / 같은 날짜 중복 휴무 등록 가능. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | 같은 직원 / 같은 날짜 중복 row. |
| 방지 방법 | UNIQUE 제약 보존. |
| 필요한 테스트 | `test_employee_leave_unique.py`. |
| 주석 태그 | `# NOTE:` (`(employee_id, leave_date)` UNIQUE). |
| rollback 기준 | RB-3. |
| Codex 검증 | UNIQUE 제약 무변경. |
| 비고 |  |

#### R-LEAVE-03 — 휴무 표시와 예약 차단 로직 분리 후 불일치

| 필드 | 값 |
|---|---|
| 관련 모듈 | leaves (19-5) ↔ calendar (19-3) ↔ appointments (19-9) |
| 위험 설명 | 19-3 calendar view-model 과 19-5 leaves rules 가 같은 휴무 데이터를 다르게 해석 → 캘린더 표시는 휴무인데 예약 차단은 안 됨 (또는 반대). |
| 발생 가능성 | 중간 |
| 영향도 | 높음 |
| 전체 위험도 | **높음** |
| 발생 징후 | 캘린더에 휴무자로 표시되는데 예약 등록 200 통과 / 캘린더에 휴무 안 나오는데 예약 차단. |
| 방지 방법 | leaves.repository read-only 인터페이스를 calendar / appointments 가 같이 호출 — 단일 진실원천. |
| 필요한 테스트 | calendar view-model + appointments availability 통합 회귀. |
| 주석 태그 | `# NOTE:` (단일 진실원천 — leaves.repository read-only). |
| rollback 기준 | RB-3 (휴무 차단 깨짐). |
| Codex 검증 | leaves.repository → calendar / appointments / `_upsert_employee_leave_core` 단일 호출지. |
| 비고 |  |

#### R-LEAVE-04 — 캘린더 휴무자 표시 누락

| 필드 | 값 |
|---|---|
| 관련 모듈 | leaves ↔ calendar |
| 위험 설명 | 19-3 calendar view-model 분리 시 `EmployeeLeave` 응답이 빠지면 미니캘린더 / 메인 캘린더에 휴무자 미표시. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 휴무 등록된 치료사가 캘린더에 정상 출근으로 표시. |
| 방지 방법 | calendar view-model 의 leaves 호출 보존. |
| 필요한 테스트 | UI smoke (자동 검증 부재 — 분리 후 사용자 수동 확인). |
| 주석 태그 | `# NOTE:` (calendar = leaves read 호출). |
| rollback 기준 | UI 표시 깨짐 시 즉시. |
| Codex 검증 | calendar view-model 의 leaves 호출 보존. |
| 비고 |  |

### 2-F. treatments / completion_rules

#### R-TX-01 — 도수치료 시간별 항목 구조 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | treatments (19-6) |
| 위험 설명 | `SEED_TREATMENTS` 5개 (injection / cartilage / eswt / manual30 / manual60) 의 코드 / 시간 (`duration_min`) / `count_increment` 가 변경되면 시드 / 통계 / 예약 / 엑셀 export 모두 영향. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | manual30 이 30분이 아닌 다른 시간 / `count_increment` 변경. |
| 방지 방법 | `SEED_TREATMENTS` ([constants.py:14](../../app/models/constants.py:14)) 보존. `manual60` `count_increment=1` 직접 단언 추가. |
| 필요한 테스트 | `manual60=1` 직접 단언 + `test_stats_counts.py` (manual 카운트 집계). |
| 주석 태그 | `# NOTE:` (`SEED_TREATMENTS` / `manual60=1`). |
| rollback 기준 | RB-4 (완료체크 변경). |
| Codex 검증 | `SEED_TREATMENTS` 무변경. |
| 비고 | CLAUDE.md 명시 — `manual60=1` 절대 2 ⊥. |

#### R-TX-02 — 완료체크가 시간 가중치 방식으로 되돌아감

| 필드 | 값 |
|---|---|
| 관련 모듈 | treatments / completion_rules (19-6) |
| 위험 설명 | 현재 정책 = "치료항목별 개별 카운트 (manual30 +1, manual60 +1)". 19-6 분리 시 `count_increment` 무시 / 시간 가중치 (manual30 +1, manual60 +2) 로 되돌리면 완료체크 변경 + CLAUDE.md 명시 정책 위반. |
| 발생 가능성 | 낮음 (CLAUDE.md 명시 — 의도적으로 1 유지) |
| 영향도 | **치명** (CLAUDE.md 명시 정책 위반 + 통계 집계 전부 영향) |
| 전체 위험도 | **높음** |
| 발생 징후 | manual60 approve 시 `done_count` +2 / `_bump_patient_count` 의 increment 가 2. |
| 방지 방법 | `manual60` `count_increment=1` 직접 단언 추가. CLAUDE.md "manual60 = 1카운트 정책" 명시 인용 주석. |
| 필요한 테스트 | `manual60=1` 단언 (신규) + `test_appointment_rules.py` approve 흐름 회귀. |
| 주석 태그 | `# NOTE:` (`manual60=1` 정책 — CLAUDE.md 명시) / `# RISK:` (`count_increment` 변경 시 stats 회귀 多). |
| rollback 기준 | RB-4. |
| Codex 검증 | `count_increment=1` 직접 단언 + CLAUDE.md 인용. |
| 비고 | CLAUDE.md "manual60 을 다시 `count_increment=2` 로 되돌리지 않는다" 명시. |

#### R-TX-03 — 체외충격파 등 확장 치료항목 집계 누락

| 필드 | 값 |
|---|---|
| 관련 모듈 | treatments ↔ stats |
| 위험 설명 | `eswt` (체외충격파) / `injection` / `cartilage` 가 19-11 stats 분리 시 `_get_manual_treatment_rows` / `_get_manual_therapy_codes` 분기에서 누락되면 통계 집계 영향. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | by-treatment 응답에서 `eswt` 카운트 0. |
| 방지 방법 | `_get_manual_treatment_rows` ([api.py:3732](../../app/routers/api.py:3732)) 분기 보존. |
| 필요한 테스트 | `test_stats_counts.py` 의 ESWT 카운트 회귀. |
| 주석 태그 | `# NOTE:` (`_get_manual_treatment_rows` 다중 의존). |
| rollback 기준 | RB-6. |
| Codex 검증 | `_get_manual_treatment_rows` 결과 무변경. |
| 비고 |  |

#### R-TX-04 — 완료 카운트와 통계 집계 불일치

| 필드 | 값 |
|---|---|
| 관련 모듈 | treatments / completion_rules ↔ stats |
| 위험 설명 | `PatientTreatmentCount.done_count` (approve / revert) 와 `ManualCount` (수동 카운트) 가 19-6 / 19-11 분리 시 잘못 동기화되면 통계 결과가 환자 카운트와 불일치. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | summary 의 완료 카운트 vs 환자별 `done_count` 합계 차이. |
| 방지 방법 | approve / revert 흐름 + ManualCount upsert 흐름 분리 보존. |
| 필요한 테스트 | `test_stats_counts.py` + `test_appointment_rules.py` 의 approve / revert. |
| 주석 태그 | `# NOTE:` (`done_count` ↔ `ManualCount` 동기 정책). |
| rollback 기준 | RB-4 / RB-6. |
| Codex 검증 | approve / revert 후 `done_count` 결과 + ManualCount upsert 결과 무변경. |
| 비고 |  |

### 2-G. stats (통계)

#### R-STAT-01 — 예약 기준 / 완료 기준 혼재

| 필드 | 값 |
|---|---|
| 관련 모듈 | stats (19-11) |
| 위험 설명 | summary / by-therapist / aggregate 의 "예약 수" vs "완료 수" 분기가 19-11 분리 시 섞이면 응답 결과 변경. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | summary 의 예약/완료 카운트 변경. |
| 방지 방법 | 8 endpoint 별 status 분기 / done_count 분기 흐름 보존. |
| 필요한 테스트 | `test_stats_counts.py` + 신규 8 endpoint contract (C-7). |
| 주석 태그 | `# COMPAT:` (8 endpoint 응답 키). |
| rollback 기준 | RB-6. |
| Codex 검증 | 8 endpoint 응답 키 + 분기 결과 무변경. |
| 비고 |  |

#### R-STAT-02 — 치료사별 / 항목별 / 시간대 / 요일별 통계 집계 오류

| 필드 | 값 |
|---|---|
| 관련 모듈 | stats |
| 위험 설명 | by-therapist / by-treatment / by-hour / by-weekday 의 GROUP BY / WHERE 절이 분리 시 변경되면 집계 결과 변경. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 4 endpoint 응답 카운트 변경. |
| 방지 방법 | aggregators.py 의 SQL 흐름 보존. |
| 필요한 테스트 | 신규 4 endpoint contract (C-7). |
| 주석 태그 | `# COMPAT:` (4 endpoint 응답 키). |
| rollback 기준 | RB-6. |
| Codex 검증 | SQL 결과 무변경. |
| 비고 |  |

#### R-STAT-03 — 의사 필터 (`is_doctor_filter`) 분기 결과 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | stats ↔ staff (19-8) |
| 위험 설명 | `is_doctor_filter` ([api.py:3491-3527](../../app/routers/api.py:3491)) 분기가 19-8 staff 분리 시 잘못 변경되면 의사 통계 분기 결과 변경. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | by-therapist 의 의사 필터 결과 변경. |
| 방지 방법 | `_doctor_codes_set` (`injection`/`cartilage`) + `is_doctor_filter` 분기 보존. |
| 필요한 테스트 | 신규 의사 분기 회귀 (19-P-5 §4 항목 12). |
| 주석 태그 | `# NOTE:` (의사 필터 = `Treatment.role="doctor"` 코드 분기). |
| rollback 기준 | RB-6. |
| Codex 검증 | `is_doctor_filter` 분기 결과 무변경. |
| 비고 |  |

#### R-STAT-04 — 신환 수 집계 누락

| 필드 | 값 |
|---|---|
| 관련 모듈 | stats ↔ patients |
| 위험 설명 | summary 의 신환 카운트가 19-11 분리 시 누락 / 잘못 집계. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | summary 신환 카운트 0 또는 변경. |
| 방지 방법 | `Appointment.is_new_patient` 카운트 흐름 보존. |
| 필요한 테스트 | `test_stats_counts.py` (신환 카운트). |
| 주석 태그 | `# NOTE:` (신환 카운트 = `is_new_patient=True` 합계). |
| rollback 기준 | RB-6. |
| Codex 검증 | summary 신환 카운트 무변경. |
| 비고 |  |

#### R-STAT-05 — 취소 / 노쇼 후보가 잘못 반영

| 필드 | 값 |
|---|---|
| 관련 모듈 | stats ↔ appointments |
| 위험 설명 | 현재 `status="canceled"` 만 통계 제외. 노쇼 별도 필드 부재. 19-11 분리 시 status 분기 잘못되면 취소가 통계에 포함되거나 정상 예약이 통계에서 제외. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | summary 카운트가 status 별로 잘못 분기. |
| 방지 방법 | `status` 분기 흐름 보존. 노쇼 별도 필드 신설 ⊥ (post-19-P). |
| 필요한 테스트 | `test_stats_counts.py` 의 status 분기. |
| 주석 태그 | `# NOTE:` (status 분기) / `# TODO(post-19-P):` (노쇼 컬럼 m014+). |
| rollback 기준 | RB-6. |
| Codex 검증 | status 분기 결과 무변경. |
| 비고 | 19-P-6 §9 F-10. |

### 2-H. sms

#### R-SMS-01 — 예약문자 대상 추출 오류

| 필드 | 값 |
|---|---|
| 관련 모듈 | sms (19-10) |
| 위험 설명 | `tomorrow-targets` ([api.py:2998](../../app/routers/api.py:2998)) 의 대상자 추출 SQL 흐름이 분리 시 변경되면 발송 대상 누락 / 중복. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 (운영 환경 직접) |
| 전체 위험도 | 중간 |
| 발생 징후 | 다음날 예약 환자 발송 대상에 누락 / 다른 환자 포함. |
| 방지 방법 | `tomorrow-targets` SQL 흐름 + 응답 키 보존. |
| 필요한 테스트 | 신규 sms 응답 키 contract (C-2). |
| 주석 태그 | `# COMPAT:` (sms 응답 키) / `# NOTE:` (대상자 추출 SQL). |
| rollback 기준 | RB-5. |
| Codex 검증 | `tomorrow-targets` SQL 결과 무변경. |
| 비고 |  |

#### R-SMS-02 — 문자 템플릿 변경으로 기존 문구 흐름 깨짐

| 필드 | 값 |
|---|---|
| 관련 모듈 | sms |
| 위험 설명 | `SmsTemplate` 시드 / 응답 키 / placeholder (`{환자명}` / `{시간}`) 가 19-10 분리 시 변경. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 발송 시 placeholder 미치환 / 다른 템플릿 사용. |
| 방지 방법 | `SmsTemplate` 시드 + `_serialize_sms_template` 보존. |
| 필요한 테스트 | 신규 sms templates contract. |
| 주석 태그 | `# COMPAT:` (`_serialize_sms_template`). |
| rollback 기준 | RB-5. |
| Codex 검증 | placeholder + 시드 무변경. |
| 비고 |  |

#### R-SMS-03 — 문자나라 계정 / API key / 설정 노출

| 필드 | 값 |
|---|---|
| 관련 모듈 | sms ↔ admin / settings |
| 위험 설명 | `SmsSetting.munjanara_id` / `key` / `pw` / `sender_phone` 응답 / 로그 / traceback 노출 시 보안 사고. |
| 발생 가능성 | 중간 (분리 시 마스킹 호출 누락 가능) |
| 영향도 | 높음 |
| 전체 위험도 | **높음** |
| 발생 징후 | `/api/sms/setting` 응답 또는 로그에 평문 / 마스킹 표시. |
| 방지 방법 | `_sms_sanitize` ([api.py:3160](../../app/routers/api.py:3160)) 마스킹 패턴 보존. 응답 키에서 평문 / 마스킹 부재 (boolean 만). |
| 필요한 테스트 | `test_sms_secret_masking.py` (81줄). |
| 주석 태그 | `# SAFETY:` (API key / 계정 마스킹). |
| rollback 기준 | RB-7. |
| Codex 검증 | `_sms_sanitize` 마스킹 패턴 보존. 응답에 평문 부재. |
| 비고 |  |

#### R-SMS-04 — 실제 외부 문자 발송이 테스트 중 발생

| 필드 | 값 |
|---|---|
| 관련 모듈 | sms |
| 위험 설명 | 19-10 분리 시 외부 HTTP client (`provider.py`) 가 mock 처리되지 않으면 테스트가 실제 문자나라 API 호출 → 실제 SMS 발송 + 비용. |
| 발생 가능성 | 중간 (mock fixture 부재 시) |
| 영향도 | **치명** (실제 발송 + 비용 + 운영 사고) |
| 전체 위험도 | **치명** |
| 발생 징후 | 테스트 실행 후 실제 문자 수신 / 외부 API 비용 청구. |
| 방지 방법 | `provider.py` 경계 분리 + 외부 HTTP client mock fixture (`urllib.request` / `requests`). conftest 의 `_block_sdk_modules` 와 같은 패턴. |
| 필요한 테스트 | 외부 HTTP mock 회귀 + `len(provider.calls) == 0` 단언. |
| 주석 태그 | `# SAFETY:` (외부 HTTP 차단 / mock 필수). |
| rollback 기준 | RB-8 (외부 API 호출 발생). |
| Codex 검증 | 모든 sms 테스트에서 외부 HTTP 호출 0. |
| 비고 | 19-P-5 §3-8 외부 HTTP mock 필수. |

#### R-SMS-05 — 문자 모듈이 예약 상태 직접 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | sms ↔ appointments |
| 위험 설명 | sms 발송 후 `Appointment.status` 자동 변경 (예: `sms_sent=True` 토글) → 예약 자동 트리거 발생 = D-8 (sms → appointments write ⊥) 위반. |
| 발생 가능성 | 낮음 (현재 정책 = 자동 트리거 X) |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | sms send 후 예약 상태 자동 변경. |
| 방지 방법 | sms → appointments write ⊥ (의존성 D-8). 자동 발송 트리거 ⊥. |
| 필요한 테스트 | sms send 후 appointment 상태 무변경 회귀. |
| 주석 태그 | `# NOTE:` (자동 발송 트리거 ⊥) / `# RISK:` (sms → appointments write ⊥). |
| rollback 기준 | RB-2. |
| Codex 검증 | sms 모듈에서 appointments write 호출 0. |
| 비고 | 19-P-4 §6-1 / 19-P-6 §3-10. |

### 2-I. admin / settings / 권한

#### R-ADM-01 — 관리자 전용 기능이 일반 직원에게 노출

| 필드 | 값 |
|---|---|
| 관련 모듈 | admin (19-12) ↔ core/security (19-1) |
| 위험 설명 | `require_admin` / `require_admin_or_sync_token` 의존성이 19-1 / 19-12 분리 시 누락되면 비-admin 사용자가 admin 전용 endpoint (예: `/api/admin/change-password`, `/api/ai/settings` PUT, `/api/restore`) 접근 가능. |
| 발생 가능성 | 중간 (의존성 import 경로 변경 多) |
| 영향도 | **치명** |
| 전체 위험도 | **치명** |
| 발생 징후 | 인증 없이 admin 전용 endpoint 가 200 응답. |
| 방지 방법 | `require_admin` Depends 호출 보존 — 19-1 / 19-12 분리 시 wrapper. PBKDF2 + 5회 잠금 + 8h 세션 정책 무변경. |
| 필요한 테스트 | `test_admin_auth_required.py` (282줄) 회귀. |
| 주석 태그 | `# SAFETY:` (PBKDF2 + 잠금 / `require_admin` Depends). |
| rollback 기준 | RB-7 추가 권한 회귀. |
| Codex 검증 | 모든 admin 전용 endpoint 의 `require_admin` Depends 보존. |
| 비고 | 19-P-4 §2-I / 19-P-6 §3-12. |

#### R-ADM-02 — API key 원문이 화면 / 로그 노출

| 필드 | 값 |
|---|---|
| 관련 모듈 | admin (19-12) ↔ ai (19-13) |
| 위험 설명 | `AiSetting.api_key` / `SmsSetting.munjanara_key` 평문 / 마스킹이 응답 / 로그 / traceback 에 노출 시 보안 사고. |
| 발생 가능성 | 중간 (분리 시 마스킹 호출 누락 가능) |
| 영향도 | **치명** |
| 전체 위험도 | **치명** |
| 발생 징후 | `/api/ai/settings` 응답 또는 로그에 sk-X.... 평문 / 마스킹 표시. |
| 방지 방법 | 모든 응답에 `api_key_set` boolean 만 노출. `_mask_api_key` / `_sms_sanitize` 마스킹 패턴 보존. |
| 필요한 테스트 | `test_ai_health_public.py` / `test_ai_health_status.py` / `test_admin_ui_smoke.py` / `test_sms_secret_masking.py`. |
| 주석 태그 | `# SAFETY:` (API key 비노출 — boolean 만). |
| rollback 기준 | RB-7. |
| Codex 검증 | 모든 응답 / 로그에 평문 / 마스킹 부재. |
| 비고 | [docs/AI_WORKING_RULES.md §1.6](../AI_WORKING_RULES.md). |

#### R-ADM-03 — AI 모드 설정이 잘못 반영

| 필드 | 값 |
|---|---|
| 관련 모듈 | admin / settings (19-2) ↔ ai (19-13) |
| 위험 설명 | `derive_ai_mode` (`local_only` / `local_first` / `ai_assist`) 파생 정책이 19-2 feature_flags 분리 시 잘못 변경되면 잘못된 모드로 운영. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | `/api/ai/status` 의 `ai_mode` 가 expected 와 불일치. |
| 방지 방법 | `derive_ai_mode` 파생 우선순위 (enabled / api_key / model) 보존. `local_only` / `local_first` / `ai_assist` 분기 흐름. |
| 필요한 테스트 | `test_ai_assist_mode.py` (355줄) + `test_local_only_mode.py` (72줄). |
| 주석 태그 | `# NOTE:` (`ai_mode` 파생 정책 — single source). |
| rollback 기준 | RB-1 (응답 키 결과 변경). |
| Codex 검증 | `ai_mode` 파생 결과 무변경. |
| 비고 | T-8 19-P-2. |

#### R-ADM-04 — feature flag 가 여러 위치 분산

| 필드 | 값 |
|---|---|
| 관련 모듈 | core/feature_flags (19-1 / 19-2) |
| 위험 설명 | `AiSetting.enabled` + 환경 변수 (`AI_RAG_ENABLED` / `AI_RAG_VECTOR_ENABLED` / `AI_RAG_HYBRID_ENABLED`) + ai_mode 파생이 분산되어 있어 19-1 / 19-2 분리 시 단일 진실원천 깨짐. |
| 발생 가능성 | 중간 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 같은 플래그가 다른 위치에서 다르게 읽힘. |
| 방지 방법 | `core/feature_flags.py` 단일 진입점 + 환경 변수 우선순위 명시 (T-8 19-P-2). |
| 필요한 테스트 | `test_ai_assist_mode.py` + 신규 feature_flags 통합 회귀. |
| 주석 태그 | `# NOTE:` (`feature_flags` 단일 진실원천 — 환경 변수 vs DB 우선순위). |
| rollback 기준 | RB-1 (응답 결과 변경). |
| Codex 검증 | `feature_flags.py` 가 단일 진입점. |
| 비고 |  |

#### R-ADM-05 — 설정 변경이 감사 기록 없이 반영

| 필드 | 값 |
|---|---|
| 관련 모듈 | admin / settings ↔ audit (19-12) |
| 위험 설명 | system-settings / config / AI settings 변경이 19-12 audit 분리 시 `audit()` 호출 누락되면 변경 추적 불가. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 설정 변경 후 `/api/audit-logs` 에 기록 부재. |
| 방지 방법 | 모든 settings PUT/POST 핸들러에서 `audit()` 호출 보존. |
| 필요한 테스트 | settings PUT 시 audit insert 회귀. |
| 주석 태그 | `# SAFETY:` (`audit()` 모든 CUD 호출). |
| rollback 기준 | RB-7 / 추가 audit 회귀. |
| Codex 검증 | settings PUT/POST 핸들러의 `audit()` 호출 보존. |
| 비고 |  |

### 2-J. backup / restore

#### R-BAK-01 — 운영 DB 잘못 건드림

| 필드 | 값 |
|---|---|
| 관련 모듈 | backup (19-12) |
| 위험 설명 | 19-12 backup 분리 시 `make_backup` / `restore_*` 가 격리 경로 (`tests/temp/`) 가 아닌 운영 경로 (`%APPDATA%\도수치료예약\clinic.db`) 를 직접 건드리면 운영 DB 손상. |
| 발생 가능성 | 낮음 (`scripts/check_db_path.py` 머지 게이트) |
| 영향도 | **치명** |
| 전체 위험도 | **치명** |
| 발생 징후 | `scripts/check_db_path.py` 실패 / `tests/harness/db_guard.assert_safe_db_path()` raise. |
| 방지 방법 | `tests/conftest.py` 4단계 격리 + `_block_sdk_modules` + `db_guard` + `check_db_path` 보존. |
| 필요한 테스트 | `test_db_restore_safety.py` (151줄) + `tests/test_*_does_not_use_operational_db` 다수. |
| 주석 태그 | `# SAFETY:` (운영 DB 격리). |
| rollback 기준 | RB-7. |
| Codex 검증 | `db_guard.assert_safe_db_path()` 호출 보존 (import-time + session fixture). |
| 비고 | [docs/AI_WORKING_RULES.md §1.2](../AI_WORKING_RULES.md). |

#### R-BAK-02 — 백업 경로 표시 오류

| 필드 | 값 |
|---|---|
| 관련 모듈 | backup |
| 위험 설명 | `GET /api/backup/dir` 응답이 19-12 분리 시 잘못된 경로 표시. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 사용자 화면에 잘못된 백업 폴더 경로 표시. |
| 방지 방법 | `get_backup_dir()` ([config.py:29](../../app/config.py:29)) 함수 보존. |
| 필요한 테스트 | 백업 경로 응답 contract. |
| 주석 태그 | `# COMPAT:` (`get_backup_dir` 결과). |
| rollback 기준 | RB-1. |
| Codex 검증 | `get_backup_dir` 결과 무변경. |
| 비고 |  |

#### R-BAK-03 — 복구 후 앱 상태 불일치

| 필드 | 값 |
|---|---|
| 관련 모듈 | backup ↔ core/database |
| 위험 설명 | `/api/restore` UploadFile 후 `engine.dispose()` + atomic rename 흐름이 19-12 분리 시 깨지면 복구 후 SQLAlchemy connection 이 stale → 앱 재시작 필요. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | 복구 후 첫 query 가 SQLite 잠금 / stale connection error. |
| 방지 방법 | `engine.dispose()` + atomic rename + integrity_check 흐름 보존. 사용자에게 앱 재시작 / 새로고침 안내 표시. |
| 필요한 테스트 | `test_db_restore_safety.py`. |
| 주석 태그 | `# RISK:` (atomic rename + integrity_check + engine.dispose). |
| rollback 기준 | RB-7 추가 백업 회귀. |
| Codex 검증 | `engine.dispose()` + atomic rename 흐름 보존. |
| 비고 |  |

#### R-BAK-04 — 오래된 백업 삭제 정책 오류

| 필드 | 값 |
|---|---|
| 관련 모듈 | backup |
| 위험 설명 | `auto_backup_keep_count` (SystemSetting) 정책이 19-12 분리 시 잘못 변경되면 백업 폴더 무한 증가 / 너무 빠른 삭제. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 백업 파일 수가 expected `keep_count` 초과 / 미만. |
| 방지 방법 | `auto_backup_keep_count` 정책 보존. |
| 필요한 테스트 | 백업 정리 정책 회귀 (현재 부재 — 보강 후보). |
| 주석 태그 | `# NOTE:` (`auto_backup_keep_count` 정책). |
| rollback 기준 | RB-7. |
| Codex 검증 | `_timer_loop` 정책 결과 무변경. |
| 비고 |  |

#### R-BAK-05 — 백업 / 복구 중 다른 작업과 충돌

| 필드 | 값 |
|---|---|
| 관련 모듈 | backup ↔ all (CUD) |
| 위험 설명 | `make_backup` / `restore_*` 실행 중 다른 라우터의 CUD 가 발생하면 SQLite 락 / 부분 백업 / 손상. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | SQLite `database is locked` error 또는 백업 파일 부분 손상. |
| 방지 방법 | 백업 / 복구 중 동시 실행 lock (현재 미구현 — post-19-P 후보). 운영 환경에서 사용자에게 안내. |
| 필요한 테스트 | 백업 중 동시 CUD 회귀 (현재 부재). |
| 주석 태그 | `# RISK:` (백업 중 동시 실행 lock 미구현 — post-19-P) / `# TODO(post-19-P):` (lock 도입). |
| rollback 기준 | RB-7. |
| Codex 검증 | post-19-P 후속 검토 명시. |
| 비고 |  |

### 2-K. ai / rag / safety / vector / hybrid

#### R-AI-01 — local-first 원칙이 깨질 위험

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai (19-13) ↔ rag / safety |
| 위험 설명 | 19-13 분리 시 `should_call_llm` 다층 게이트 (provider_disabled / pii / local_only / no_sources / low_confidence) 가 우회되면 외부 LLM 호출 발생. |
| 발생 가능성 | 중간 (게이트 호출 경로 변경 시) |
| 영향도 | **치명** (비용 / PII 사고) |
| 전체 위험도 | **치명** |
| 발생 징후 | `local_only` 모드에서 `len(provider.calls) > 0` / `local_first` 에서 게이트 통과 안 한 호출 발생. |
| 방지 방법 | `should_call_llm` 게이트 우선순위 보존 + 응답 dict 의 reason_code 확인. |
| 필요한 테스트 | `test_local_only_mode.py` + `test_ai_full_harness.py` + `test_full_harness.py`. |
| 주석 태그 | `# SAFETY:` (`should_call_llm` 게이트 + `_block_sdk_modules`). |
| rollback 기준 | RB-8. |
| Codex 검증 | `should_call_llm` 우선순위 (provider_disabled > pii > local_only > no_sources > low_confidence) 무변경. |
| 비고 | [docs/AI_WORKING_RULES.md §2](../AI_WORKING_RULES.md) 절대 원칙. |

#### R-AI-02 — local_only 에서 LLM / Embedding 호출

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai |
| 위험 설명 | `local_only` 모드에서 LLM 또는 Embedding provider 가 호출되면 (현재 정책 = 0 호출) 비용 / PII 사고 + 보안 모드 위반. |
| 발생 가능성 | 낮음 |
| 영향도 | **치명** |
| 전체 위험도 | **높음** |
| 발생 징후 | `len(provider.calls) > 0` 또는 `len(embedding_provider.calls) > 0` (local_only 모드). |
| 방지 방법 | `should_call_llm` 의 `local_only` 우선순위 + Embedding factory 차단 (`get_embedding_provider(mode="local_only")` → `EmbeddingUnavailable`). |
| 필요한 테스트 | `test_local_only_mode.py`. |
| 주석 태그 | `# SAFETY:` (local_only = 호출 0 단언). |
| rollback 기준 | RB-8. |
| Codex 검증 | `local_only` 모드 단언 보존. |
| 비고 |  |

#### R-AI-03 — sources 없음 / low_confidence / PII / unknown_feature 에서 provider 호출

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai |
| 위험 설명 | reason_code (`no_sources` / `low_confidence` / `pii_detected` / `unknown_feature`) 케이스에서 provider 호출 발생 시 비용 / 무근거 응답 / PII 사고. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | reason_code 케이스에서 `len(provider.calls) > 0`. |
| 방지 방법 | 게이트 5단계 우선순위 보존. |
| 필요한 테스트 | `test_full_harness.py` + `test_ai_full_harness.py` (reason_code 별 호출 카운트 단언). |
| 주석 태그 | `# SAFETY:` (게이트 5단계). |
| rollback 기준 | RB-8. |
| Codex 검증 | reason_code 별 호출 카운트 무변경. |
| 비고 |  |

#### R-AI-04 — RAG 가 근거 없는 예약 / 휴무 / 환자 정보 생성

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai / rag |
| 위험 설명 | RAG 가 도메인 DB (Appointment / EmployeeLeave / Patient) 를 임의로 query / 생성하는 응답 (D-6 / F-5 위반). |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 (할루시네이션 / 사용자 오해) |
| 전체 위험도 | 중간 |
| 발생 징후 | manual_qa 응답에 환자명 / 예약 시간 / 휴무 정보가 매뉴얼 sources 와 무관하게 등장. |
| 방지 방법 | AI/RAG → 도메인 ⊥ (D-6 / F-5). hallucination guard (`validate_answer` / `_RE_MEDICAL_CLAIM` / `_RE_EXECUTION_CLAIM`). |
| 필요한 테스트 | `test_ai_hallucination.py` + `test_rag_safety.py` + `test_ai_safety_harness.py`. |
| 주석 태그 | `# SAFETY:` (AI/RAG → 도메인 ⊥). |
| rollback 기준 | RB-1 (응답 변경) + 별도 PII / 할루시네이션 회귀. |
| Codex 검증 | rag/* 모듈에서 도메인 모델 import 0. |
| 비고 |  |

#### R-AI-05 — vector / hybrid fallback 깨짐

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai / vector / hybrid |
| 위험 설명 | vector provider 실패 시 keyword 단독 fallback 이 19-13 분리 시 깨지면 검색 중단. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | vector 실패 후 manual/search / manual/ask 가 500 응답. |
| 방지 방법 | `hybrid_retrieve` catch 후 keyword fallback 정책 보존. |
| 필요한 테스트 | `test_hybrid_retriever.py` + `test_ai_vector_harness.py`. |
| 주석 태그 | `# RISK:` (vector fallback — keyword 단독 동작 보장). |
| rollback 기준 | RB-1. |
| Codex 검증 | hybrid → keyword fallback 흐름 보존. |
| 비고 | [docs/releases/18_ai_rag_known_risks.md §1-1](../releases/18_ai_rag_known_risks.md) circuit breaker. |

#### R-AI-06 — 외부 API 호출이 테스트 중 발생

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai |
| 위험 설명 | conftest 의 `_block_sdk_modules` 가 19-13 분리 시 우회되면 테스트가 실제 OpenAI / Anthropic API 호출 → 비용 + 운영 LLM 모드 의도치 않게 호출. |
| 발생 가능성 | 낮음 |
| 영향도 | **치명** |
| 전체 위험도 | **높음** |
| 발생 징후 | 테스트 실행 후 외부 API 비용 청구 / RuntimeError 부재. |
| 방지 방법 | `_block_sdk_modules` 정책 보존 — openai / anthropic SDK 클래스를 RuntimeError 로 교체. |
| 필요한 테스트 | conftest 의 import-time 검증 + AI 하네스 6개. |
| 주석 태그 | `# SAFETY:` (`_block_sdk_modules` — 외부 SDK 차단). |
| rollback 기준 | RB-8. |
| Codex 검증 | `_block_sdk_modules` 정책 보존. |
| 비고 |  |

#### R-AI-07 — AI 로그에 개인정보 원문 저장

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai / privacy |
| 위험 설명 | `AiUsageLog.error_detail` / `prompt_text` / `response_text` 에 PII 원문이 저장 (현재 정책 = sha256 해시 only + 200자 cap). 19-13 분리 시 마스킹 누락 시 사고. |
| 발생 가능성 | 낮음 |
| 영향도 | **치명** |
| 전체 위험도 | **높음** |
| 발생 징후 | AiUsageLog 직접 SELECT 시 010 / 환자명 / 주민번호 원문. |
| 방지 방법 | `pii.scan` + `_safe_error_detail` (200자 cap) + sha256 해시 정책 보존. |
| 필요한 테스트 | `test_ai_logging.py` + `test_ai_safety_harness.py`. |
| 주석 태그 | `# SAFETY:` (PII 마스킹 + sha256 + 200자 cap). |
| rollback 기준 | RB-7. |
| Codex 검증 | AiUsageLog `prompt_hash` / `response_hash` 만 저장. |
| 비고 |  |

### 2-L. calendar / schedule_view (후속 검토 위험)

#### R-CAL-01 — 저장 로직과 표시용 view-model 혼재

| 필드 | 값 |
|---|---|
| 관련 모듈 | calendar (19-3) ↔ appointments / leaves |
| 위험 설명 | 19-3 calendar view-model 분리 시 view-model 이 write 책임 (예약 / 휴무 변경) 을 갖게 되면 의존성 방향 위반 (D-11 = view-model read-only). |
| 발생 가능성 | 중간 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | calendar view-model 안에서 `Appointment` / `EmployeeLeave` write 발생. |
| 방지 방법 | view-model = read-only 조립. write 는 appointments / leaves service 만. |
| 필요한 테스트 | calendar view-model 의 write 호출 0 회귀 (보강 필요). |
| 주석 태그 | `# NOTE:` (view-model = read-only). |
| rollback 기준 | RB-2 (예약 결과 변경) / RB-3. |
| Codex 검증 | view-model 의 도메인 write 호출 0. |
| 비고 | 19-P-4 D-11. |

#### R-CAL-02 — 금일예약환자 표시 깨짐

| 필드 | 값 |
|---|---|
| 관련 모듈 | calendar |
| 위험 설명 | 19-3 분리 시 today_targets / `/api/appointments` 응답 흐름이 변경되어 메인 화면 금일예약환자 미표시. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 메인 화면 금일예약환자 영역 비어 있음. |
| 방지 방법 | view-model 조립 시 응답 dict 키 보존. |
| 필요한 테스트 | UI smoke 수동 (자동 검증 부재). |
| 주석 태그 | `# COMPAT:` (today_targets 응답 키). |
| rollback 기준 | RB-1. |
| Codex 검증 | 응답 dict 키 보존. |
| 비고 |  |

#### R-CAL-03 — 미니캘린더 휴무 / 예약 표시 깨짐

| 필드 | 값 |
|---|---|
| 관련 모듈 | calendar ↔ leaves ↔ appointments |
| 위험 설명 | 미니캘린더 (`/api/employee-leaves` / `/api/appointments` 통합) 표시가 분리 시 깨짐. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 미니캘린더에 휴무 / 예약 미표시. |
| 방지 방법 | calendar view-model 의 leaves / appointments read 호출 보존. |
| 필요한 테스트 | UI smoke 수동. |
| 주석 태그 | `# NOTE:` (calendar = leaves + appointments read). |
| rollback 기준 | RB-1. |
| Codex 검증 | view-model read 호출 보존. |
| 비고 |  |

#### R-CAL-04 — 치료사 색상 표시 깨짐

| 필드 | 값 |
|---|---|
| 관련 모듈 | calendar ↔ therapists |
| 위험 설명 | R-THER-03 와 같은 위험 — calendar view-model 에서 색상 응답 누락. |
| 발생 가능성 | 낮음 |
| 영향도 | 낮음 |
| 전체 위험도 | 낮음 |
| 발생 징후 | FullCalendar event 색상 누락. |
| 방지 방법 | `Employee.color` 응답 보존. |
| 필요한 테스트 | UI smoke 수동. |
| 주석 태그 | `# NOTE:` (`_lighten_hex` 결정 결과). |
| rollback 기준 | RB-1. |
| Codex 검증 | `Employee.color` 필드 응답 보존. |
| 비고 |  |

### 2-M. notes (위험은 §2-B R-PAT-04 / R-PAT-05 와 통합)

> 본 카테고리 위험은 §2-B (patients / notes) 의 R-PAT-04 / R-PAT-05 로 통합 등록. 통합 `modules/notes/` 는 post-19-P 후속.

### 2-N. audit / logs

#### R-AUDIT-01 — `audit()` 시그니처 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | audit (19-12) |
| 위험 설명 | `audit(actor, action, entity_id, detail)` 시그니처가 19-12 분리 시 변경되면 모든 CUD 호출지에서 회귀 발생. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 (모든 CUD 회귀) |
| 전체 위험도 | 중간 |
| 발생 징후 | TypeError / 호출 실패 → CUD 흐름 깨짐. |
| 방지 방법 | `audit()` 시그니처 보존 — wrapper. |
| 필요한 테스트 | 전체 CUD 흐름 회귀 (간접). |
| 주석 태그 | `# COMPAT:` (`audit()` 시그니처 — 모든 CUD 호출). |
| rollback 기준 | RB-7. |
| Codex 검증 | `audit()` 시그니처 무변경. |
| 비고 |  |

#### R-AUDIT-02 — audit_log.detail 200자 cap 누락

| 필드 | 값 |
|---|---|
| 관련 모듈 | audit / privacy |
| 위험 설명 | `_safe_error_detail` (200자 cap + PII 마스킹) 이 19-12 분리 시 누락되면 audit_log / AiUsageLog 에 PII 원문 저장 가능. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | audit_log.detail 에 200자 초과 / PII 원문. |
| 방지 방법 | `_safe_error_detail` 호출 보존. |
| 필요한 테스트 | `test_get_recent_logs_masks_pii_in_error_detail`. |
| 주석 태그 | `# SAFETY:` (200자 cap + PII 마스킹). |
| rollback 기준 | RB-7. |
| Codex 검증 | `_safe_error_detail` 호출지 보존. |
| 비고 |  |

### 2-O. health / diagnostics (후속 검토)

#### R-HEALTH-01 — `/api/health` 신설을 본 19-P 에서 도입

| 필드 | 값 |
|---|---|
| 관련 모듈 | health (post-19-P) |
| 위험 설명 | `/api/health` 신규 endpoint 신설은 post-19-P (M-28). 본 19-P 기간 내 도입 시 응답 키 추가 + 19-P 비-목표 위반. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 낮음 |
| 발생 징후 | 19-2 / 19-12 분리 시 `/api/health` 신설. |
| 방지 방법 | post-19-P 후속 검토 분류 명시 — `/api/admin/status` 가 인증 상태만, `/api/ai/health` 는 별도. |
| 필요한 테스트 | post-19-P 신설 시. |
| 주석 태그 | `# TODO(post-19-P):` (`/api/health` 신설 — `modules/health/`). |
| rollback 기준 | 신설 시 즉시 제거. |
| Codex 검증 | `/api/health` endpoint 부재 확인. |
| 비고 | 19-P-2 §2-2 / 19-P-6 §9 F-13. |

### 2-P. export_import

#### R-EXIM-01 — 엑셀 export 응답 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | export_import (19-7 / 19-12) |
| 위험 설명 | `/api/export/{manual-schedule,stats}.xlsx` 응답 (Content-Type / 파일 형식 / 컬럼 순서) 변경. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 사용자가 다운로드한 엑셀 파일 컬럼 / 형식 변경. |
| 방지 방법 | `_lighten_hex` 색상 + 컬럼 순서 보존. |
| 필요한 테스트 | 엑셀 export 응답 contract (현재 부재 — C-7). |
| 주석 태그 | `# COMPAT:` (엑셀 응답 형식). |
| rollback 기준 | RB-1. |
| Codex 검증 | 엑셀 컬럼 / 형식 무변경. |
| 비고 |  |

#### R-EXIM-02 — data-convert 정규화 정책 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | export_import (19-7) |
| 위험 설명 | `_dc_*` 헬퍼 (~600줄) 의 gender / SSN / phone 정규화 정책이 19-7 분리 시 변경되면 환자 import 결과 변경. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 환자 import 결과 (데이터 정규화 / 중복 검사 / 매칭) 변경. |
| 방지 방법 | `_dc_*` 헬퍼 통째 이동 (T-11 19-P-2). |
| 필요한 테스트 | 신규 data-convert preview / apply contract (C-6). |
| 주석 태그 | `# COMPAT:` (`_dc_*` 정규화) / `# RISK:` (대량 import 트랜잭션). |
| rollback 기준 | RB-1. |
| Codex 검증 | `_dc_*` 결과 무변경. |
| 비고 |  |

### 2-Q. core / responses / errors / time_utils

#### R-CORE-01 — repository 가 service 참조 (역의존성)

| 필드 | 값 |
|---|---|
| 관련 모듈 | core / 모든 modules |
| 위험 설명 | repository.py → service.py import 발생 시 의존성 방향 위반 (F-1). 분리 시 추후 큰 회귀 발생. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 (구조 회귀) |
| 전체 위험도 | 중간 |
| 발생 징후 | `import` 위반 — repository 안에서 service 호출. |
| 방지 방법 | router → service → repository 단방향 (D-1 19-P-4). |
| 필요한 테스트 | import 그래프 회귀 (선택 — 정적 분석). |
| 주석 태그 | `# NOTE:` (repository = read/write 만 / service 호출 ⊥). |
| rollback 기준 | RB-9 (5회 루프 실패 후 재작성). |
| Codex 검증 | `grep -r "from app.modules.*.service" app/modules/*/repository.py` 0건. |
| 비고 | 19-P-4 D-1 / F-1. |

#### R-CORE-02 — core 가 modules 참조 (순환참조)

| 필드 | 값 |
|---|---|
| 관련 모듈 | core (19-1) |
| 위험 설명 | core/* 에서 modules/* import 발생 시 의존성 방향 위반 (F-2). |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 (구조 회귀 / import 순환) |
| 전체 위험도 | 중간 |
| 발생 징후 | `import` 위반 — core 안에서 modules 호출. |
| 방지 방법 | core ⊥ modules (D-4). |
| 필요한 테스트 | import 그래프 회귀. |
| 주석 태그 | `# NOTE:` (core ⊥ modules — 단방향). |
| rollback 기준 | RB-9. |
| Codex 검증 | `grep -r "from app.modules" app/core/` 0건. |
| 비고 | 19-P-4 D-4 / F-2. |

#### R-CORE-03 — 여러 모듈이 같은 DB query 중복 구현

| 필드 | 값 |
|---|---|
| 관련 모듈 | 모든 modules |
| 위험 설명 | `_doctor_codes_set` / `_get_manual_treatment_rows` 등 공통 query 가 staff / stats / appointments / sms 등 여러 모듈에서 중복 구현. |
| 발생 가능성 | 중간 (분리 시 발생 가능성 높음) |
| 영향도 | 중간 (유지보수 비용 + 일관성 깨짐) |
| 전체 위험도 | 중간 |
| 발생 징후 | 같은 SQL / 결정 로직이 여러 모듈에 중복. |
| 방지 방법 | 공통 query 는 단일 모듈 (예: treatments / staff) 의 service 에 두고 다른 모듈은 호출. |
| 필요한 테스트 | grep 검증 (선택). |
| 주석 태그 | `# NOTE:` (공통 query 단일 위치). |
| rollback 기준 | RB-9. |
| Codex 검증 | 공통 query 중복 0. |
| 비고 | 19-P-4 F-7. |

#### R-CORE-04 — 공통 응답 key 를 모듈별로 다르게

| 필드 | 값 |
|---|---|
| 관련 모듈 | core/responses (19-1) ↔ 모든 modules |
| 위험 설명 | 공통 응답 dict (`detail` / `error_code` / 페이지네이션) 키가 모듈별로 다르게 되면 프론트 JS 분기 깨짐. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | 모듈별 응답 키 일관성 깨짐. |
| 방지 방법 | `core/responses.py` 표준 envelope (현재 키 그대로 + 추가만 허용). |
| 필요한 테스트 | API contract 회귀 33+ 키 셋. |
| 주석 태그 | `# COMPAT:` (응답 dict 키 보존 — 추가만). |
| rollback 기준 | RB-1. |
| Codex 검증 | 표준 envelope 도입 시 기존 응답 dict 키 100% 보존. |
| 비고 | 19-P-2 §2-1 / 19-P-3 2-20. |

#### R-CORE-05 — 프론트 JS 의존 API key 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | 모든 modules ↔ UI |
| 위험 설명 | main.html JS (5747~5793 의 manual_qa 5키 / 환자 / 예약 / 통계 다수) 가 의존하는 응답 키가 분리 시 변경. |
| 발생 가능성 | 중간 |
| 영향도 | 높음 (UI 직접 깨짐) |
| 전체 위험도 | **높음** |
| 발생 징후 | 프론트 화면 표시 / 분기 깨짐 (예: AI Q&A 의 `not_found` 분기 / `confidence` 표시). |
| 방지 방법 | UI 분리 비-목표 + 응답 키 dict 단위 보존. |
| 필요한 테스트 | 신규 비-AI contract (C-1) + manual_qa 5키 회귀 + UI smoke 수동. |
| 주석 태그 | `# COMPAT:` (UI 의존 응답 키 — 추가만). |
| rollback 기준 | RB-1. |
| Codex 검증 | main.html JS 의존 키 grep + 응답 dict 보존. |
| 비고 | 19-P-1 §21-1. |

### 2-R. feature_flags

> 본 카테고리 위험은 §2-I (admin / settings) 의 R-ADM-04 (feature flag 분산) 으로 통합 등록.

### 2-S. batch / jobs

#### R-BATCH-01 — daemon thread 정책 약화

| 필드 | 값 |
|---|---|
| 관련 모듈 | batch (backup / sync / indexer) |
| 위험 설명 | `start_auto_backup` / `start_sync_worker` / reindex lock 의 `daemon=True` + stop flag 가 분리 시 변경되면 테스트 격리 (conftest 람다 교체) 깨짐 / 운영 환경에서 thread leak. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | 테스트 종료 후 thread leak / 운영 환경에서 종료 시 hang. |
| 방지 방법 | `daemon=True` + stop flag 정책 보존. conftest 람다 교체 우회 ⊥. |
| 필요한 테스트 | `test_graceful_shutdown.py` (85줄). |
| 주석 태그 | `# RISK:` (daemon thread + stop flag — 테스트 람다 교체). |
| rollback 기준 | RB-9. |
| Codex 검증 | `daemon=True` + stop flag 보존. |
| 비고 |  |

### 2-T. privacy / retention

> §2-B R-PAT-01 (PII 노출) + §2-K R-AI-07 (AI 로그 PII) + §2-N R-AUDIT-02 (200자 cap) 와 통합 등록. 보존 정책 고도화 (오래된 AI 로그 삭제 / 환자정보 비활성화) 는 post-19-P 후속.

### 2-U. concurrency / locking

#### R-LOCK-01 — 낙관적 락 (`Appointment.version`) TOCTOU

| 필드 | 값 |
|---|---|
| 관련 모듈 | appointments (19-9) |
| 위험 설명 | `_check_version` / `_bump_version` 의 TOCTOU 가 19-9 분리 시 잘못 변경되면 동시 수정 시 한쪽 변경 무시 / lost update. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | 동시 수정 시 409 응답 부재 / lost update 발생. |
| 방지 방법 | `_check_version` / `_bump_version` 시그니처 보존. |
| 필요한 테스트 | 신규 409 contract (19-4 / 19-9 분리 직전 보강). |
| 주석 태그 | `# RISK:` (낙관적 락 TOCTOU). |
| rollback 기준 | RB-2. |
| Codex 검증 | `_check_version` / `_bump_version` 보존. |
| 비고 |  |

#### R-LOCK-02 — HMAC + TOCTOU (action_leave)

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai (19-13) ↔ leaves (19-5) |
| 위험 설명 | action_leave parse / preview / execute 흐름의 HMAC 토큰 + TOCTOU 정책이 19-13 / 19-5 분리 시 변경되면 토큰 재사용 / 동시 등록 사고. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | 토큰 재사용 시 200 응답 / 동시 등록 시 중복 row. |
| 방지 방법 | HMAC + TOCTOU 정책 보존. `_upsert_employee_leave_core` 단일 진실원천. |
| 필요한 테스트 | `test_ai_action_leave.py` (1232줄). |
| 주석 태그 | `# RISK:` (HMAC + TOCTOU — action_leave). |
| rollback 기준 | RB-3. |
| Codex 검증 | HMAC 토큰 정책 보존. |
| 비고 |  |

#### R-LOCK-03 — reindex lock 우회

| 필드 | 값 |
|---|---|
| 관련 모듈 | ai / knowledge / indexer |
| 위험 설명 | indexer.py 의 reindex lock 이 19-13 분리 시 우회되면 동시 reindex → 부분 chunk / vector 손상. |
| 발생 가능성 | 낮음 |
| 영향도 | 중간 |
| 전체 위험도 | 중간 |
| 발생 징후 | `KnowledgeIndexRun.status` 가 `partial` / `failed` 다발. |
| 방지 방법 | reindex lock 정책 보존. |
| 필요한 테스트 | `test_ai_reindex_harness.py`. |
| 주석 태그 | `# RISK:` (reindex lock — 동시 실행 차단). |
| rollback 기준 | RB-9. |
| Codex 검증 | reindex lock 보존. |
| 비고 |  |

#### (통합 메모) atomic rename (`/api/restore`) 깨짐

> **r2 보정** — Codex r1 caveat 정합. 본 항목은 별도 Risk ID 부여 ⊥. R-BAK-03 (복구 후 앱 상태 불일치) 와 동일 위험 — `/api/restore` UploadFile 후 `engine.dispose()` + atomic rename + integrity_check 흐름 깨짐. R-BAK-03 항목 참조.

### 2-V. time_utils

#### R-TIME-01 — Asia/Seoul 기준 변경

| 필드 | 값 |
|---|---|
| 관련 모듈 | core/time_utils (19-1) |
| 위험 설명 | 오늘 / 내일 / 이번달 / 점심창 시간이 분리 시 timezone naive / UTC 로 변경되면 모든 시간 분기 (sms tomorrow-targets / stats by-hour / 점심창) 영향. |
| 발생 가능성 | 낮음 |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | 시간대 관련 응답 결과 변경. |
| 방지 방법 | Asia/Seoul 기준 명시 (현재 `datetime` 직접 사용 多 — 19-1 분리 시 통합). |
| 필요한 테스트 | 신규 time_utils 단언 회귀. |
| 주석 태그 | `# NOTE:` (Asia/Seoul 기준). |
| rollback 기준 | RB-2 / RB-5 / RB-6 (시간 의존 결과 변경). |
| Codex 검증 | timezone 처리 무변경. |
| 비고 |  |

### 2-W. 운영 / 배포

#### R-OPS-01 — 운영 DB 접근 (테스트 / 분리 중)

> R-BAK-01 와 통합. 보강 — `scripts/check_db_path.py` 머지 게이트 + `tests/conftest.py` 4단계 격리 우회 ⊥.

#### R-OPS-02 — 테스트 DB 와 운영 DB 경로 혼동

| 필드 | 값 |
|---|---|
| 관련 모듈 | core/config (19-1) ↔ tests/conftest |
| 위험 설명 | `DOSU_DB_PATH` / `APPDATA` 격리가 19-1 / 19-12 분리 시 깨지면 테스트가 운영 DB 사용. |
| 발생 가능성 | 낮음 |
| 영향도 | **치명** |
| 전체 위험도 | **높음** |
| 발생 징후 | `tests/harness/db_guard.assert_safe_db_path()` raise. |
| 방지 방법 | 4단계 격리 보존. `get_db_path` (`DOSU_DB_PATH` 우선) 정책 보존. |
| 필요한 테스트 | `scripts/check_db_path.py` 머지 게이트. |
| 주석 태그 | `# SAFETY:` (`DOSU_DB_PATH` 우선 + `APPDATA` 격리). |
| rollback 기준 | RB-7. |
| Codex 검증 | `get_db_path` 정책 보존. |
| 비고 |  |

#### R-OPS-03 — 외부 API 호출 차단 실패

> R-AI-06 / R-SMS-04 와 통합.

#### R-OPS-04 — PyInstaller 빌드 실패 (hidden imports 누락)

| 필드 | 값 |
|---|---|
| 관련 모듈 | OPS / dosu_clinic.spec |
| 위험 설명 | 19-1~13 분리 시 신규 모듈 (`app/core/*` / `app/modules/*/`) 이 spec hidden imports 에 등록 안 되면 PyInstaller 빌드 시 ImportError. |
| 발생 가능성 | 중간 (분리 시 누락 가능성 높음) |
| 영향도 | 높음 |
| 전체 위험도 | **높음** |
| 발생 징후 | `pyinstaller --noconfirm dosu_clinic.spec` 실행 후 ImportError / 빌드 실패. |
| 방지 방법 | 매 모듈 분리 즉시 spec hidden imports 갱신 + `tests/test_pyinstaller_hidden_imports.py` 53 tests 통과. |
| 필요한 테스트 | `tests/test_pyinstaller_hidden_imports.py` (370줄, 53 tests). |
| 주석 태그 | `# RISK:` (spec hidden imports — 분리 시 누락 ⊥). |
| rollback 기준 | RB-10. |
| Codex 검증 | hidden imports 53+ tests 통과. |
| 비고 | 19-P-1 §20-3. |

#### R-OPS-05 — 빌드 산출물 실행 실패

| 필드 | 값 |
|---|---|
| 관련 모듈 | OPS |
| 위험 설명 | PyInstaller exe 빌드 후 사용자 환경에서 실행 시 import / migration / startup 실패. |
| 발생 가능성 | 낮음 (53 tests + 사용자 승인 시 실제 빌드) |
| 영향도 | **치명** |
| 전체 위험도 | **높음** |
| 발생 징후 | exe 더블클릭 후 8000 포트 listen 실패 / 브라우저 미연결. |
| 방지 방법 | 19-14 종료 게이트 + 사용자 승인 시 실제 빌드 + exe smoke 5 endpoint. |
| 필요한 테스트 | exe smoke (18-8 입증 기준 — 5 endpoint). |
| 주석 태그 | `# RISK:` (exe smoke — 사용자 승인 시 실제 빌드). |
| rollback 기준 | RB-10. |
| Codex 검증 | exe smoke 통과 (사용자 승인 시). |
| 비고 |  |

#### R-OPS-06 — requirements 변경으로 빌드 깨짐

| 필드 | 값 |
|---|---|
| 관련 모듈 | OPS / requirements*.txt |
| 위험 설명 | 19-1~13 분리 중 requirements*.txt 변경 (의도치 않게) 시 빌드 환경 깨짐. |
| 발생 가능성 | 낮음 (수정 금지 범위) |
| 영향도 | 높음 |
| 전체 위험도 | 중간 |
| 발생 징후 | requirements diff 발생. |
| 방지 방법 | requirements*.txt 무수정 (19-P-6 R-2). |
| 필요한 테스트 | `git diff --stat -- requirements.txt requirements-dev.txt` 0. |
| 주석 태그 | `# SAFETY:` (requirements 무수정). |
| rollback 기준 | RB-10. |
| Codex 검증 | requirements diff 0. |
| 비고 |  |

---

## 3. 위험도별 분류

> 본 §3 은 §2 항목을 위험도별로 재분류 + 우선 보강 / 리팩토링 전 확인 / rollback 기준 / Codex 집중 검증 항목 제시.

### 3-A. 치명 위험 (높음 가능성 × 높음 영향도)

| Risk ID | 위험 이름 | 우선 보강 |
|---|---|---|
| R-APPT-02 | 도수 중복 차단 미구현 (xfail 3 + skip 1) | 19-4 백엔드 차단 코드 + 정방향 전환 |
| R-APPT-03 | 휴무 차단 미구현 (xfail 4) | 19-4 백엔드 차단 코드 + 정방향 전환 |
| R-PAT-01 | PII 노출 | 분리 직전 audit / log 호출지 PII 부재 회귀 |
| R-SMS-04 | 외부 문자 발송 | 19-10 외부 HTTP mock fixture |
| R-ADM-01 | admin 전용 기능 노출 | 19-1 / 19-12 `require_admin` Depends 보존 |
| R-ADM-02 | API key 평문 노출 | 19-13 / 19-10 마스킹 정책 보존 |
| R-AI-01 | local-first 깨짐 | 19-13 `should_call_llm` 게이트 보존 |
| R-BAK-01 | 운영 DB 손상 | `db_guard` + `check_db_path` 보존 (모든 세션) |

**우선 보강 테스트**: 19-P-5 §4 보강 9개 항목 + 외부 HTTP mock + `should_call_llm` 게이트 + audit / log PII 부재.

**리팩토링 전 확인**: `xfail` 7건 + `skip` 1건 정방향 전환 (19-4 baseline). `_block_sdk_modules` + `db_guard` + `check_db_path` 정책 보존.

**rollback 기준**: RB-2 / RB-3 / RB-7 / RB-8.

**Codex 집중 검증**: (1) `xfail`/`skip` → 정방향 전환. (2) `_block_sdk_modules` 보존. (3) `db_guard` 호출 2회 (import-time + fixture). (4) `should_call_llm` 우선순위. (5) admin 전용 endpoint 의 `require_admin` Depends. (6) API key boolean 만 응답.

### 3-B. 높은 위험

| Risk ID | 위험 이름 | 우선 보강 |
|---|---|---|
| R-APPT-01 | 예약 응답 키 변경 | 19-9 분리 직전 응답 키 contract |
| R-APPT-04 | 반차 12:00 기준 변경 | 19-4 / 19-5 정합 |
| R-APPT-06 | devtools 우회 | 19-4 / 19-9 백엔드 검증 흐름 보존 |
| R-DOC-01 | doctors 단정 | 19-8 부재 항목 명시 + 부재 grep 회귀 |
| R-LEAVE-03 | 표시 / 차단 불일치 | 19-3 / 19-5 / 19-9 단일 진실원천 |
| R-TX-02 | manual60=1 되돌아감 | 19-6 직접 단언 + CLAUDE.md 인용 |
| R-SMS-03 | 문자나라 계정 노출 | 19-10 마스킹 정책 |
| R-AI-02 | local_only 호출 발생 | 19-13 모드 단언 보존 |
| R-AI-06 | 외부 API 호출 (테스트 중) | `_block_sdk_modules` |
| R-AI-07 | AI 로그 PII | 19-13 마스킹 정책 |
| R-CORE-05 | 프론트 JS 의존 키 변경 | 19-9 / 19-13 contract |
| R-OPS-02 | DB 경로 혼동 | 19-1 분리 시 격리 정책 보존 |
| R-OPS-04 | PyInstaller 빌드 실패 | 53 tests + 매 분리 즉시 갱신 |
| R-OPS-05 | exe 실행 실패 | 19-14 사용자 승인 시 실제 빌드 + smoke |

**우선 보강 테스트**: 86 endpoint contract (C-1) + manual_qa 5키 회귀 + manual60 단언 + `_block_sdk_modules` + 53 hidden imports + DB 경로 격리.

**리팩토링 전 확인**: 19-0 baseline 재고정 (529/1/7) + `xfail` 7건 정방향 전환 baseline + main.html JS 의존 키 grep.

**rollback 기준**: RB-1 / RB-3 / RB-4 / RB-7 / RB-8 / RB-10.

**Codex 집중 검증**: (1) 응답 키 33+ 보존. (2) `manual60=1` 단언. (3) `_block_sdk_modules`. (4) 53 hidden imports. (5) doctors 부재 항목 grep 0건.

### 3-C. 중간 위험

> §2 의 위험 중 위험도 "중간" 으로 표기된 항목 (다수 — R-APPT-05 / R-APPT-07 / R-PAT-02~05 / R-THER-01~02 / R-LEAVE-01~02/04 / R-TX-01/03/04 / R-STAT-01~05 / R-SMS-01~02/05 / R-ADM-03~05 / R-BAK-02~05 / R-AI-03~05 / R-CAL-01~03 / R-AUDIT-01~02 / R-EXIM-01~02 / R-CORE-01~04 / R-BATCH-01 / R-LOCK-01~03 / R-TIME-01 / R-OPS-06).

**우선 보강 테스트**: 도메인별 contract (C-1~C-7) + `test_stats_counts.py` + AI 하네스 6개 + 백업 / 복구 회귀.

**리팩토링 전 확인**: 도메인별 응답 키 + 헬퍼 결정 결과 baseline.

**rollback 기준**: RB-1 / RB-5 / RB-6.

**Codex 집중 검증**: 모듈별 응답 키 + 헬퍼 결정 결과 무변경.

### 3-D. 낮은 위험

| Risk ID | 위험 이름 |
|---|---|
| R-THER-03 | 치료사 색상 표시 깨짐 (UI 표시) |
| R-CAL-04 | 치료사 색상 (calendar) |
| R-HEALTH-01 | `/api/health` 신설 (post-19-P) |

**우선 보강 테스트**: UI smoke 수동.

**리팩토링 전 확인**: `_lighten_hex` 결정 결과 baseline.

**rollback 기준**: RB-1 (UI 표시 깨짐 시).

**Codex 집중 검증**: post-19-P 후속 검토 분류 명시.

### 3-E. 후속 검토 위험 (현재 부재 — post-19-P)

| Risk ID | 항목 | 분류 |
|---|---|---|
| (R-DOC-01 / 02 와 함께) | 별도 `modules/doctors/` 폴더 (M-31) | 부재 — EMR 도입 시 |
| (해당 없음) | recurring_appointments | 부재 |
| (해당 없음) | resources / 자원 (M-33) | 부재 |
| (해당 없음) | notifications | 부재 |
| (해당 없음) | printing / documents | 부재 |
| (해당 없음) | export 확장 (CSV / EMR) | 부재 |
| (해당 없음) | privacy 보존 정책 고도화 | 부재 |
| (해당 없음) | audit 보존 / 자동 정리 | 부재 |
| (해당 없음) | 노쇼 별도 필드 | 부재 |
| (해당 없음) | 권한 다중 등급 | 부재 |
| R-HEALTH-01 | `/api/health` 신설 (M-28) | 부재 |
| (해당 없음) | calendar UI 분리 (M-26) | 부재 |
| (해당 없음) | AI 의사 가드 (M-36) | 부재 |
| (해당 없음) | `modules/notes/` 통합 | 부재 |

**우선 보강**: 본 19-P 비-목표 — 단정 ⊥.

**리팩토링 전 확인**: 부재 항목 grep 회귀.

**rollback 기준**: 부재 항목이 코드 / docstring / 응답 키에 등장 시 즉시.

**Codex 집중 검증**: 부재 항목 grep 0건.

---

## 4. 모듈별 위험 요약

| 모듈 | 위험 항목 | 핵심 위험 |
|---|---|---|
| **appointments** | R-APPT-01~07, R-LOCK-01 | 응답 키 / 도수 중복 차단 미구현 / 휴무 차단 미구현 / 반차 기준 / 점심창 / devtools / status 통계 충돌 / 낙관적 락 |
| **patients** | R-PAT-01~05 | PII 노출 / 검색 / 신환 / 메모 경계 / 환자별/예약별 메모 |
| **therapists** | R-THER-01~03 | 활성 / can_eswt·can_manual / 색상 표시 |
| **doctors / medical_staff** (후속) | R-DOC-01~02 | 단정 ⊥ / 후속 오해 |
| **leaves** | R-LEAVE-01~04, R-LOCK-02 | DB 표준 / UNIQUE / 표시·차단 불일치 / 캘린더 / HMAC TOCTOU |
| **treatments** | R-TX-01~04 | SEED 5개 / manual60=1 / 확장 항목 / 카운트 vs 통계 |
| **stats** | R-STAT-01~05 | 예약·완료 분기 / 4 endpoint / 의사 필터 / 신환 / 취소·노쇼 |
| **sms** | R-SMS-01~05 | 대상 추출 / 템플릿 / 계정 노출 / 외부 발송 / 자동 트리거 |
| **admin / settings** | R-ADM-01~05 | 권한 노출 / API key / AI 모드 / feature flag / audit |
| **backup** | R-BAK-01~05 | 운영 DB / 경로 / 복구 / 보관 정책 / 충돌 |
| **ai / rag / safety / vector / hybrid** | R-AI-01~07, R-LOCK-03 | local-first / local_only / 게이트 / RAG 도메인 ⊥ / fallback / 외부 API / 로그 PII / reindex lock |
| **calendar / schedule_view** (post-19-P) | R-CAL-01~04 | 저장·표시 혼재 / 금일예약 / 미니캘린더 / 색상 |
| **notes** | (R-PAT-04~05 통합) | (patients 카테고리 통합) |
| **audit / logs** | R-AUDIT-01~02 | `audit()` 시그니처 / 200자 cap |
| **health / diagnostics** (post-19-P) | R-HEALTH-01 | 신설 ⊥ |
| **export_import** | R-EXIM-01~02 | 엑셀 / data-convert 정규화 |
| **core / responses / errors** | R-CORE-01~05 | 의존 방향 / 순환 / 중복 / envelope / UI 키 |
| **feature_flags** | (R-ADM-04 통합) | (admin 카테고리 통합) |
| **batch / jobs** | R-BATCH-01 | daemon thread + stop flag |
| **privacy / retention** | (R-PAT-01 + R-AI-07 + R-AUDIT-02 통합) | (privacy 정책 고도화는 post-19-P 후속) |
| **concurrency / locking** | R-LOCK-01~03 (+ R-BAK-03 통합) | 낙관적 락 / HMAC TOCTOU / reindex lock / atomic rename |
| **time_utils** | R-TIME-01 | Asia/Seoul 기준 |
| **OPS / 운영 / 배포** | R-OPS-01~06 | 운영 DB / DB 경로 / 외부 API / PyInstaller / exe / requirements |

---

## 5. 리팩토링 세션별 위험 연결

> 19-P-6 [§2-1 단계 개요](19_refactor_rollout_plan.md) 의 19-0 ~ 19-14 와 §2 의 Risk ID 매핑.

| 세션 | 핵심 위험 (Risk ID) | 우선 대응 |
|---|---|---|
| **19-0** baseline 재고정 | R-OPS-01~03 / R-BAK-01 | dirty 정리 + 4단계 격리 + `_block_sdk_modules` 동작 확인 |
| **19-1** core 분리 | R-CORE-02 / R-OPS-02 / R-ADM-01 / R-TIME-01 / R-OPS-06 | core ⊥ modules / DB 경로 격리 / `require_admin` / Asia/Seoul / requirements diff 0 |
| **19-2** settings / feature_flags / health 경계 | R-ADM-03 / R-ADM-04 / R-HEALTH-01 | `ai_mode` 파생 / feature_flags 단일 / `/api/health` 부재 명시 |
| **19-3** calendar view-model | R-CAL-01~04 / R-LEAVE-04 / R-THER-03 | view-model = read-only / 색상 / 미니캘린더 |
| **19-4** availability + 백엔드 차단 보강 | **R-APPT-02 / R-APPT-03 / R-APPT-04 / R-APPT-05 / R-APPT-06 / R-LEAVE-03** | **`xfail` 3 + `skip` 1 + xfail 4 정방향 전환 / 점심창 / 12:00 기준 / devtools** |
| **19-5** leaves 분리 | R-LEAVE-01~04 / R-LOCK-02 | DB 표준 / UNIQUE / 단일 진실원천 / HMAC TOCTOU |
| **19-6** treatments / completion_rules | R-TX-01~04 | SEED 보존 / `manual60=1` 단언 / 확장 항목 / 카운트 vs 통계 |
| **19-7** patients / notes / data-convert | R-PAT-01~05 / R-EXIM-02 | PII 노출 / 검색 / 신환 / 메모 경계 / `_dc_*` 정규화 |
| **19-8** staff (therapists + doctors 얇은 분기) | R-THER-01~03 / R-DOC-01~02 / R-STAT-03 | alias 이중 키 / `_doctor_codes_set` / 부재 단정 ⊥ |
| **19-9** appointments 분리 (마지막) | **R-APPT-01 / R-APPT-06 / R-APPT-07 / R-LOCK-01 / R-CORE-05** | **응답 키 / devtools / status / 낙관적 락 / UI 의존 키** |
| **19-10** sms | R-SMS-01~05 | 대상 추출 / 템플릿 / 계정 노출 / **외부 발송 차단** / 자동 트리거 |
| **19-11** stats | R-STAT-01~05 / R-EXIM-01 | 4 endpoint / 의사 필터 / 신환 / 취소·노쇼 / 엑셀 |
| **19-12** admin / backup / audit / export_import | R-ADM-01~05 / R-BAK-01~05 / R-AUDIT-01~02 / R-BATCH-01 | 권한 / API key / AI 모드 / 운영 DB / 복구 / `audit()` / daemon thread |
| **19-13** AI commands | **R-AI-01~07 / R-LOCK-03 / R-LOCK-02 / R-DOC-02** | **local-first / local_only / 게이트 / RAG 도메인 ⊥ / fallback / 외부 API / 로그 PII / reindex lock / HMAC / AI 의사 가드 후속** |
| **19-14** 종료 게이트 | **R-OPS-04~06** | **PyInstaller / exe smoke / requirements** |

---

## 6. 주석 / 문서화 기준 (각 위험에 향후 코드 이동 시 필요한 태그)

> 본 19-P-7 은 코드 미수정 — 본 §6 은 19-1~14 실제 코드 리팩토링 세션에 적용할 *기준 표*.

### 6-1. 적용 기준 (19-P-6 §4 정합)

| # | 기준 | 적용 |
|---|---|---|
| 1 | 기존 API/UI 호환성 위험 | `# COMPAT:` |
| 2 | 개인정보/운영DB/외부API 차단 위험 | `# SAFETY:` |
| 3 | 업무 규칙 설명 필요 | `# NOTE:` |
| 4 | 변경 시 위험한 규칙 | `# RISK:` |
| 5 | 후속 세션 처리 필요 | `# TODO(19-x):` |
| 6 | 임시 adaptor / wrapper | `# TEMP:` 또는 `# COMPAT:` |
| 7 | 의미 없는 모든 줄 주석 ⊥ |  |
| 8 | 주석 작성 때문에 기능 동작 변경 ⊥ |  |

### 6-2. 위험 항목별 주석 태그 매트릭스 (인덱스)

| Risk ID | COMPAT | SAFETY | NOTE | RISK | TODO/TEMP |
|---|---|---|---|---|---|
| R-APPT-01 | ✓ (응답 키 + version) |  |  |  |  |
| R-APPT-02 |  |  | ✓ (도수 중복 spec 01) | ✓ (devtools 우회) |  |
| R-APPT-03 |  |  | ✓ (휴무 spec 02) | ✓ (devtools 우회) |  |
| R-APPT-04 |  |  | ✓ (12:00 기준) |  |  |
| R-APPT-05 |  |  | ✓ (점심창 정책) |  |  |
| R-APPT-06 |  |  | ✓ (CLAUDE.md 정책) | ✓ (백엔드 검증 필수) |  |
| R-APPT-07 |  |  | ✓ (status 분기) |  | TODO(post-19-P) 노쇼 |
| R-PAT-01 |  | ✓ (PII / sha256) |  |  |  |
| R-PAT-02 | ✓ (검색 응답 키) |  |  |  |  |
| R-PAT-03 |  |  | ✓ (신환 결정) |  |  |
| R-PAT-04 |  |  | ✓ (메모 의미 차이) |  | TODO(post-19-P) 통합 |
| R-PAT-05 |  | ✓ (PII 메모) |  |  |  |
| R-THER-01 |  |  | ✓ (active 필터) |  |  |
| R-THER-02 | ✓ (can_eswt/can_manual) |  |  |  |  |
| R-THER-03 |  |  | ✓ (`_lighten_hex`) |  |  |
| R-DOC-01 |  |  | ✓ (role 분기 only) |  | TODO(post-19-P) doctors |
| R-DOC-02 |  | ✓ (의사 가드 후속) |  |  | TODO(post-19-P) M-36 |
| R-LEAVE-01 |  |  | ✓ (`leave_type`/`leave_kind`) |  |  |
| R-LEAVE-02 |  |  | ✓ (UNIQUE) |  |  |
| R-LEAVE-03 |  |  | ✓ (단일 진실원천) |  |  |
| R-LEAVE-04 |  |  | ✓ (calendar = leaves read) |  |  |
| R-TX-01 |  |  | ✓ (`SEED_TREATMENTS`) |  |  |
| R-TX-02 |  |  | ✓ (`manual60=1` CLAUDE.md) | ✓ (count_increment 변경) |  |
| R-TX-03 |  |  | ✓ (`_get_manual_treatment_rows` 다중) |  |  |
| R-TX-04 |  |  | ✓ (done_count ↔ ManualCount) |  |  |
| R-STAT-01 | ✓ (8 endpoint 키) |  |  |  |  |
| R-STAT-02 | ✓ (4 endpoint 키) |  |  |  |  |
| R-STAT-03 |  |  | ✓ (의사 필터) |  |  |
| R-STAT-04 |  |  | ✓ (신환 카운트) |  |  |
| R-STAT-05 |  |  | ✓ (status 분기) |  | TODO(post-19-P) 노쇼 |
| R-SMS-01 | ✓ (sms 응답 키) |  | ✓ (대상 SQL) |  |  |
| R-SMS-02 | ✓ (`_serialize_sms_template`) |  |  |  |  |
| R-SMS-03 |  | ✓ (계정 마스킹) |  |  |  |
| R-SMS-04 |  | ✓ (외부 HTTP 차단) |  |  |  |
| R-SMS-05 |  |  | ✓ (자동 트리거 ⊥) | ✓ (sms → appt write ⊥) |  |
| R-ADM-01 |  | ✓ (PBKDF2 + Depends) |  |  |  |
| R-ADM-02 |  | ✓ (api_key boolean 만) |  |  |  |
| R-ADM-03 |  |  | ✓ (`ai_mode` 파생) |  |  |
| R-ADM-04 |  |  | ✓ (feature_flags 단일) |  |  |
| R-ADM-05 |  | ✓ (audit 모든 CUD) |  |  |  |
| R-BAK-01 |  | ✓ (운영 DB 격리) |  |  |  |
| R-BAK-02 | ✓ (`get_backup_dir`) |  |  |  |  |
| R-BAK-03 |  |  |  | ✓ (atomic rename + dispose) |  |
| R-BAK-04 |  |  | ✓ (`auto_backup_keep_count`) |  |  |
| R-BAK-05 |  |  |  | ✓ (백업 중 동시 lock 부재) | TODO(post-19-P) lock |
| R-AI-01 |  | ✓ (`should_call_llm` 게이트) |  |  |  |
| R-AI-02 |  | ✓ (`local_only` 호출 0) |  |  |  |
| R-AI-03 |  | ✓ (게이트 5단계) |  |  |  |
| R-AI-04 |  | ✓ (AI/RAG → 도메인 ⊥) |  |  |  |
| R-AI-05 |  |  |  | ✓ (vector fallback) |  |
| R-AI-06 |  | ✓ (`_block_sdk_modules`) |  |  |  |
| R-AI-07 |  | ✓ (PII + 200자 cap) |  |  |  |
| R-CAL-01 |  |  | ✓ (view-model = read-only) |  |  |
| R-CAL-02 | ✓ (today_targets 키) |  |  |  |  |
| R-CAL-03 |  |  | ✓ (calendar = leaves+appt read) |  |  |
| R-CAL-04 |  |  | ✓ (`_lighten_hex`) |  |  |
| R-AUDIT-01 | ✓ (`audit()` 시그니처) |  |  |  |  |
| R-AUDIT-02 |  | ✓ (200자 cap + 마스킹) |  |  |  |
| R-HEALTH-01 |  |  |  |  | TODO(post-19-P) `/api/health` |
| R-EXIM-01 | ✓ (엑셀 형식) |  |  |  |  |
| R-EXIM-02 | ✓ (`_dc_*` 정규화) |  |  | ✓ (대량 import 트랜잭션) |  |
| R-CORE-01 |  |  | ✓ (repo ⊥ service) |  |  |
| R-CORE-02 |  |  | ✓ (core ⊥ modules) |  |  |
| R-CORE-03 |  |  | ✓ (공통 query 단일 위치) |  |  |
| R-CORE-04 | ✓ (응답 envelope) |  |  |  |  |
| R-CORE-05 | ✓ (UI 의존 응답 키) |  |  |  |  |
| R-BATCH-01 |  |  |  | ✓ (daemon + stop flag) |  |
| R-LOCK-01 |  |  |  | ✓ (낙관적 락 TOCTOU) |  |
| R-LOCK-02 |  |  |  | ✓ (HMAC TOCTOU) |  |
| R-LOCK-03 |  |  |  | ✓ (reindex lock) |  |
| R-TIME-01 |  |  | ✓ (Asia/Seoul) |  |  |
| R-OPS-02 |  | ✓ (`DOSU_DB_PATH` 우선) |  |  |  |
| R-OPS-04 |  |  |  | ✓ (spec hidden imports) |  |
| R-OPS-05 |  |  |  | ✓ (exe smoke) |  |
| R-OPS-06 |  | ✓ (requirements 무수정) |  |  |  |

---

## 7. Codex 검증 결과 기록 위치

본 19-P-7 산출물의 Codex 검증 결과는 다음 위치에 기록된다:

- [reports/refactor/19-P-7_codex_review.md](../../reports/refactor/19-P-7_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](../../reports/refactor/latest_codex_review.md) (덮어쓰기 — 다음 세션 진입점)

### 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

---

## 8. 종합

- **위험 등록 기준** = 14개 필드 / 위험도 매트릭스 (가능성 × 영향도) / **§1-3 카테고리 키 표 = 23행** (단독 Risk prefix 20개 + 통합 키 3개 — FF / PRIV / NOTES).
- **Taxonomy** (r3 보정 — Codex r2 fail caveat 실측 정합) = **§1-3 카테고리 키 표 23행 (단독 20 + 통합 3) → §2 섹션 23개 (2-A~2-W, 그 중 3개 = 2-M / 2-R / 2-T 는 통합 메모 섹션, 별도 Risk ID 부재) → 실제 Risk ID 제목 77개** (`grep -cE "^#### R-"` 실측, R-LOCK-04 는 별도 Risk ID 제목이 아닌 통합 메모 → R-BAK-03 atomic rename 통합).
- **등록한 위험 항목 수** (r3 실측) — APPT 7 / PAT 5 / THER 3 / DOC 2 / LEAVE 4 / TX 4 / STAT 5 / SMS 5 / ADM 5 / BAK 5 / AI 7 / CAL 4 / AUDIT 2 / HEALTH 1 / EXIM 2 / CORE 5 / TIME 1 / BATCH 1 / **LOCK 3 (+1 통합 메모 = R-BAK-03 통합)** / OPS 6 = **순수 Risk ID 77개** + 통합 메모 4개 (LOCK-04 + notes / FF / PRIV 통합 섹션 3개).
- **치명 위험 8개** (R-APPT-02 / R-APPT-03 / R-PAT-01 / R-SMS-04 / R-ADM-01 / R-ADM-02 / R-AI-01 / R-BAK-01) — 19-4 / 19-7 / 19-10 / 19-12 / 19-13 분리 직전 보강 필수.
- **높은 위험 14개** — 19-9 / 19-13 / 19-14 분리 직전 보강.
- **모듈별 위험 요약** = 21 카테고리 모두 §4 표 정합. 후속 검토 (doctors / 반복예약 / 자원 / 알림 / 출력물 / export 확장 / privacy 고도화 / audit 고도화 / 노쇼 / 권한 등급 / `/api/health` / calendar UI / AI 의사 가드 / `modules/notes/` 통합) 14개 모두 단정 ⊥.
- **세션별 위험 연결** = 19-0 ~ 19-14 모두 매핑 — 19-4 (xfail 7 + skip 1 정방향 전환 핵심) / 19-9 (응답 키 + 낙관적 락 + UI 키) / 19-13 (AI local-first + 외부 API 차단 + 의사 가드 후속) / 19-14 (PyInstaller + exe smoke).
- **rollback 기준** = §2 모든 위험 항목 + 19-P-6 §7 RB-1 ~ RB-10 매핑.
- **우선 보강 테스트** = 19-P-5 §4 보강 9개 항목 + 외부 HTTP mock + `should_call_llm` 게이트 + audit/log PII 부재 + `xfail` 7건 + `skip` 1건 정방향 전환 + 신규 86 endpoint contract + manual_qa 5키 회귀 + manual60 단언 + `_block_sdk_modules` + 53 hidden imports + DB 경로 격리 + UI smoke 수동.
- **주석 지점 인덱스** = §6-2 매트릭스 — 위험 약 70개 × COMPAT/SAFETY/NOTE/RISK/TODO 5 카테고리 (위험당 평균 1~2 태그).
- **다음 단계** = 19-P-8 의사결정 기록 문서 (`docs/refactor/19_refactor_decision_record.md`) — 19-P-1~7 전 과정에서 합의된 의사결정 (T-1 ~ T-15 등) + 향후 결정 필요 항목 정리.
