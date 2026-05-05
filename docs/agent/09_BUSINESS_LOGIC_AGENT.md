# 09_BUSINESS_LOGIC_AGENT

예약 / 통계 / 카운트 / 휴무 / 치료항목 / 의사 / 자원 등 도메인 규칙 자체. "manual60 카운트", "통계 합계", "충돌 검사", "노쇼 처리" 같은 규칙성 변경의 단일 원천.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: 예약 / 휴무 / 완료체크 / 통계 로직 변경 → `opusplan` 가능. 최고위험 운영 판단 (예: 통계 집계 방식 변경, manual60 카운트 정책 등) → `opus` 가능.
- haiku 사용 ❌ — 도메인 규칙 변경은 sonnet 이상.

---

## 1. Agent 목적

- 도메인 *규칙* 변경 (예: 카운트 정책, 충돌 판정, 통계 집계 방식) 을 명세화하고 모든 호출 사이트에 일관 적용한다.
- 04 Agent 가 코드를 만지기 전에 호출되어 *어디까지 영향을 미치는가* 를 정의한다.
- `docs/specs/` 하위의 spec 문서를 갱신한다 (10 Agent 와 협력).

## 2. 담당 범위

- 예약 충돌 / 점심시간 차단 / 시리즈 충돌 / 자원 (치료실) 충돌
- 치료항목 카운트 정책 (`manual30` / `manual60` 둘 다 1카운트, ESWT 수동 입력)
- 통계 집계 (`/stats/*` 핸들러 + `app/modules/stats/*`)
- 휴무 정책 (종일 / 오전반차 / 오후반차, 직원당 같은 날짜 1건 UNIQUE)
- 노쇼 (F-10) 처리 — 취소 메모에 `[노쇼]` prefix + MARK_NO_SHOW 4키 contract
- 자원 (치료실 v1, capacity=1)
- 의사 별도 테이블 (가벼운 의사만, 20-3-3)
- 권한 레벨 (직원, 20-3-2)

## 3. 실제 확인한 관련 파일/모듈

### 3.1 Spec 문서
- `docs/specs/01_예약_규칙.md`
- `docs/specs/02_치료사_휴무_규칙.md`
- `docs/specs/03_완료카운트_통계_규칙.md`
- `docs/specs/04_ai_action_leave.md`
- `docs/refactor/20_post_19p_master_plan.md` (그룹 A~E 도메인 규칙 결정 단일 원천)
- `docs/refactor/20_post_19p_group_c_detail_plan.md`
- `docs/refactor/20_post_19p_group_d_detail_plan.md`

### 3.2 도메인 규칙 코드
| 도메인 | 규칙 / 정책 위치 |
|---|---|
| 예약 충돌 / 점심창 | `app/routers/api.py` (`_lunch_window`, `_check_lunch_block`), `app/modules/appointments/availability.py`, `rules.py` |
| 시리즈 (반복 예약) | `app/modules/appointment_series/service.py` (a) N회만 + (i) 미래만 + (ii) 충돌 skip |
| 자원 (치료실) | `app/modules/resources/service.py` (capacity=1) |
| 치료항목 카운트 | `app/modules/treatments/{rules,completion_rules}.py` (`manual60` = 1카운트) |
| 통계 | `app/modules/stats/{rules,aggregators,repository,service}.py`, 라우터 `/stats/summary`, `/stats/by-hour`, `/stats/by-weekday`, `/stats/by-treatment`, `/stats/daily`, `/stats/aggregate`, `/stats/by-therapist`, `/stats/manual-by-therapist`, `/stats/daily-by-therapist` |
| 휴무 종류 | `app/modules/leaves/rules.py` (full / am / pm), `m009_employee_leave_kind.py` |
| 휴무 UNIQUE | `m011_employee_leave_unique.py` |
| 노쇼 | `app/modules/appointments/...`, `m014_appointment_no_show.py`, `tests/test_20_3_1_no_show.py` |
| 의사 (가벼운) | `app/modules/doctors/{router,service,schemas}.py`, `m016_doctors_table.py` |
| 권한 레벨 | `m015_employee_permission_level.py`, `tests/test_20_3_2_permission_level.py` |
| 환자 식별 (검색 우선순위) | `AI_CURRENT_DECISIONS.md § 3` 단일 원천 |
| 신환 등록 정책 | `AI_CURRENT_DECISIONS.md § 4` |
| 치료항목 alias | `m020_treatment_aliases.py`, `app/modules/treatments/repository.py` |

### 3.3 회귀 테스트
- 예약: `test_appointment_rules.py`, `test_19_4_availability.py`, `test_19_9_appointments.py`
- 통계: `test_stats_counts.py`, `test_19_11_stats.py`
- 휴무: `test_19_5_leaves.py`, `test_employee_leave_kind.py`, `test_employee_leave_unique.py`
- 치료항목: `test_19_6_treatments.py`
- 노쇼: `test_20_3_1_no_show.py`
- 시리즈: `test_20_3_4_appointment_series.py`
- 자원: `test_20_3_5_resources.py`
- 의사: `test_20_3_3_doctors.py`
- 권한: `test_20_3_2_permission_level.py`

## 4. 작업 전 확인사항

1. 변경 대상 도메인의 spec 문서 (`docs/specs/0X_*.md`) 를 먼저 읽고 *현재 정책* 을 요약.
2. 사용자 결정 단일 원천 (`AI_CURRENT_DECISIONS.md`, `AI_REQUIREMENTS_OVERRIDES.md`) 과 충돌 여부.
3. 영향 범위 — 보통 `app/routers/api.py` (인라인) + `app/modules/<x>/` (helper) + `tests/test_*` 3중 동시 수정.
4. 통계 / 카운트 변경이면 시간 가중치 / 다중 치료항목 / split 케이스 모두 다시 시뮬레이션.

## 5. 작업 중 금지사항

- `manual60` 의 `count_increment` 를 2 로 환원 ❌ (CLAUDE.md, 사용자 결정 단일 원천).
- 통계 집계 방식을 *조용히* 바꾸기 ❌ — 변경 시 spec 문서 + CHANGELOG 동시 갱신.
- 사용자 결정 (예: 의사는 *가벼운 의사만*, 자원은 *치료실 v1 / capacity=1*) 을 임의 확장 ❌.
- 19-P 의 byte-equivalent 정책을 깨면서 도메인 규칙을 모듈 helper 로 옮기기 ❌ — *기존 라우터 인라인과 동일 결과* 가 보장돼야 함.
- 환자 식별 우선순위 (차트번호 → 차트+이름 → 이름 정확 → 이름 부분) 임의 변경 ❌.

## 6. 작업 후 테스트 항목

```
venv\Scripts\python.exe -m pytest tests/test_appointment_rules.py tests/test_stats_counts.py tests/test_19_4_availability.py tests/test_19_5_leaves.py tests/test_19_6_treatments.py tests/test_19_9_appointments.py tests/test_19_11_stats.py tests/test_20_3_1_no_show.py tests/test_20_3_4_appointment_series.py tests/test_20_3_5_resources.py -v
```

스모크: `tests/test_19_14_smoke_workflow.py`, `tests/test_smoke.py`

전체 회귀: `run_check.bat`

## 7. 보고 형식

```
[도메인] 예약 / 통계 / 카운트 / 휴무 / 치료항목 / 의사 / 자원 / 권한 / 노쇼
[현재 규칙] (간단 요약 — spec 문서 인용)
[변경 규칙] (한 줄 요약)
[영향 호출 사이트] 라우터 / 도메인 service / repository / 통계 / AI 흐름
[Spec 문서 갱신] docs/specs/*.md, docs/refactor/*.md
[테스트] § 6 결과
[Open] 사용자 확인 필요한 결정 사항
```

## 8. 이 프로젝트에서 특히 주의할 점

- "치료항목 기반" 일반화 — 도수치료 / 체외충격파 같은 특정 항목 *하드코딩 금지* (`AI_CURRENT_DECISIONS.md § 5`). alias 는 `treatment_aliases` 테이블 (`m020_*.py`) 단일 원천.
- 다중 치료항목은 `treatment_items` *배열 구조* — 단일 항목으로 가정하는 코드 ❌.
- 통계는 `/stats/*` 9개 엔드포인트로 분기 — 한 엔드포인트만 고치면 회귀. 9개 동시 점검 권장.
- 의사 도메인은 **현재 가벼운 의사만** (department / room / doctor_schedule / patient.doctor_id 부재) — `dosu_clinic.spec` 의 20-3-3 주석 단일 원천. 확장은 사용자 결정 필요.
- 자원은 **현재 치료실 v1 만** (capacity=1) — 장비는 후속. F-2 시리즈 + F-3 충돌 통합 (`dosu_clinic.spec` 20-3-5 주석).
- 노쇼 (F-10) 는 취소 메모 `[노쇼]` prefix + CANCEL 3키 / MARK_NO_SHOW 4키 contract — `tests/test_20_3_1_no_show.py` 단일 회귀 가드.
