# 19-P-8 단위화 리팩토링 — 의사결정 기록 (19_refactor_decision_record)

> 19-P-1 [현재 구조](19_refactor_current_state.md), 19-P-2 [목표 아키텍처](19_refactor_target_architecture.md),
> 19-P-3 [모듈 매핑](19_refactor_module_map.md), 19-P-4 [의존성 맵](19_refactor_dependency_map.md),
> 19-P-5 [테스트 전략](19_refactor_test_strategy.md), 19-P-6 [롤아웃 계획](19_refactor_rollout_plan.md),
> 19-P-7 [위험 등록](19_refactor_risk_register.md) 의 후속 문서.
>
> **단위화 리팩토링을 왜 이 구조와 순서로 진행하는지** 의사결정 근거를 정리한다.
> 본 문서는 *의사결정 기록* 문서 — 실제 코드 / 테스트 / 폴더 / 파일 / fixture / mock 미생성.

## 0. 메타

- 작성일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](../../reports/ai_dev_loop/18-8_test_report.md))
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-8 진입 가능)** ([reports/refactor/latest_codex_review.md](../../reports/refactor/latest_codex_review.md) — 19-P-7 r3 결과)
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *의사결정 기록* 문서 — 새 폴더 / 파일 / 테스트 / 마이그레이션 미생성.

### 0-1. 본 문서가 다루지 않는 범위

- 실제 코드 이동 / 테스트 작성 — 19-0 이후 별도 세션.
- m014+ 마이그레이션 도입 결정 — 본 19-P 비-목표 (19-P-2 P-4 정합).
- v1.4.0 배포 절차 — [docs/releases/18_ai_rag_final_checklist.md](../releases/18_ai_rag_final_checklist.md) 별도 게이트.
- 위험도 / 모니터링 임계값 결정 — 19-P-7 §3 기록 + 운영 단계 별도 결정.

### 0-2. 본 문서의 위치

- 19-P-1 ~ 19-P-7 = 단위화 리팩토링 *준비 단계 (구조 계획)* 문서들.
- **19-P-8 (본 문서) = 위 7개 문서가 합의한 의사결정의 *근거* 정리.**
- 19-P-9 (다음) = 모든 19-x 코드 세션이 공통 적용할 *체크리스트* 문서.
- 19-0 ~ 19-14 = 실제 코드 이동 세션. 본 의사결정 기록을 검증 시 기준으로 사용.

---

## 1. 의사결정 기록 목적

| # | 목적 | 본문 |
|---|---|---|
| 1 | 단위화 리팩토링의 기준과 이유를 남긴다 | 분리할 모듈 / 분리하지 않을 모듈 / 분리 순서 / 응답 키 보존 / DB 보존 / local-first 보존 / Codex 게이트 — 모두 *왜* 이렇게 결정했는지 1차 근거를 본 문서에 모은다. |
| 2 | 이후 코드 세션에서 방향이 흔들리지 않게 한다 | 19-0 ~ 19-14 진행 중 "왜 appointments 를 마지막에 분리하지?", "왜 doctors 를 별도 폴더로 안 만들지?", "왜 manual60 = 1 그대로 두지?" 등 질문이 생겼을 때 본 문서를 1차 답변으로 사용. |
| 3 | Codex 검증 시 "왜 이렇게 나누는지" 판단 기준으로 사용한다 | Codex 가 코드 diff 만 보고 판단하기 어려운 *구조 결정* 의 합리성 검토에 본 문서를 참조. 결정 ID 와 근거 / 대안 / 위험을 한 표로 묶어 검증을 빠르게 한다. |
| 4 | 나중에 구조를 바꿀 때 기존 결정의 이유를 확인할 수 있게 한다 | 6개월 / 1년 후 EMR 연동, 노쇼 컬럼 추가, AI 의사 가드 보강 등을 진행할 때 "왜 이전에 이 모듈을 분리하지 않았는지" 를 추적해서 기존 결정을 *재평가* 한다. |
| 5 | 18 시리즈 [docs/ai_rag_decision_record.md](../ai_rag_decision_record.md) 와 동일한 형식으로 후속 검증 / 재검토를 가능하게 한다 | 18-AI 의사결정 기록 패턴 (Why / Alternatives / Rejected / Effects / Risks) 을 19-P 단위화에 동일하게 적용. 이후 19-x 세션 / Codex 검증 / 사용자 확인 모두 동일 형식 사용. |

---

## 2. 핵심 의사결정 목록

> 각 항목 형식 (사용자 §2 명시):
> - 결정 ID
> - 결정 내용
> - 결정 이유
> - 대안
> - 선택하지 않은 이유
> - 기대 효과
> - 위험
> - 관련 문서
> - 관련 테스트/하네스
> - Codex 검증 포인트

### 2-A. 결정 A — 왜 단위화 리팩토링을 하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-A** |
| 결정 내용 | v1.3.3 위에서 **단위화 리팩토링 (구조 안정화)** 을 별도 분기 (`ai-rag-v1-integration`) 에서 진행한다. 기능 추가가 아니라 모듈 책임 분리를 목적으로 한다. |
| 결정 이유 | (1) `app/routers/api.py` 5127줄 / 86 endpoint 가 도메인 (예약 / 환자 / 직원 / 휴무 / 치료항목 / 통계 / SMS / 관리자 / 백업 / sync / 엑셀변환) 혼재로 유지보수가 어렵다. (2) [main.html](../../app/templates/main.html) 7331줄 + 6800줄 인라인 JS 도 분리 필요지만 우선순위 낮음 (UI 분리는 19-P 비-목표). (3) 이후 doctors / EMR / recurring / resources / notifications 등 신규 기능 도입 전에 도메인 경계를 먼저 정리해야 회귀 위험을 줄인다. (4) 18-AI/RAG v1 통합 (529 passed) 직후 baseline 이 안정된 시점이 적기. |
| 대안 | (1) 리팩토링 없이 v1.4.0 신규 기능 (doctors / 노쇼 / EMR) 으로 직진. (2) main.html UI 분리부터 시작. (3) 기능별 *세부* 리팩토링 (예: helper 함수 정리만). |
| 선택하지 않은 이유 | (1) 도메인 혼재 상태에서 신규 기능 추가 시 회귀 폭이 비례 증가 — 18-AI 통합에서도 검증된 위험. (2) main.html 분리는 백엔드 도메인 경계 확정 후가 안전 (router 가 흔들리면 view-model 도 같이 흔들린다). (3) helper 정리만 하면 86 endpoint 단일 파일 문제는 그대로 남는다. |
| 기대 효과 | (1) 도메인별 책임 명확화로 후속 기능 추가 시 회귀 폭 감소. (2) 테스트 단위가 명확해져 분리된 service / repository 단위 회귀 테스트가 가능. (3) PyInstaller hidden imports / Codex 검증 / 사용자 PR 리뷰 모두 도메인 단위로 가능. |
| 위험 | R-CORE-01 ~ R-CORE-05 (구조 결함 위험) + R-OPS-04 ~ R-OPS-06 (PyInstaller / requirements 회귀). 19-P-7 §3-A 치명 위험 8개와 §3-B 높음 14개 모두 본 결정의 직접 영향 범위. |
| 관련 문서 | [19_refactor_current_state.md](19_refactor_current_state.md) §1-2, [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §1 P-1, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §1 R-1, [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §1-1, [CLAUDE.md](../../CLAUDE.md) "기능 수정과 디자인 수정을 한 번에 섞지 않는다". |
| 관련 테스트/하네스 | 18-8 baseline (529 passed, 1 skipped, 7 xfailed) — 모든 19-x 분리 후 회귀 0 유지. AI 하네스 6개 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid). [scripts/check_db_path.py](../../scripts/check_db_path.py). |
| Codex 검증 포인트 | (1) 본 19-P-8 산출이 코드 / 테스트 / spec / UI 무수정인지. (2) 19-P-1 ~ 19-P-7 산출물과 결정 근거가 충돌 없는지. (3) 단위화 = 구조 안정화 정의가 일관적인지 (P-1 ~ P-12 / R-1 ~ R-14 정합). |

### 2-B. 결정 B — 왜 한 번에 전체 코드를 이동하지 않는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-B** |
| 결정 내용 | 단위화는 **세션 1개 = 모듈 1개 (또는 작은 범위) = commit 1개** 단위로 점진 분리한다. 한 번에 전체 도메인을 이동하지 않는다. |
| 결정 이유 | (1) [api.py](../../app/routers/api.py) 5127줄 안에서 예약 / 휴무 / 통계 / 문자 / AI 가 helper 함수 (`_serialize_appointment`, `_doctor_codes_set`, `_check_lunch_block`, `_bump_patient_count`, `_get_manual_treatment_rows` 등) 로 강하게 얽혀 있다. (2) 일괄 이동 시 회귀가 발생해도 *어디에서* 들어왔는지 추적이 어렵다. (3) 18-AI 시리즈 (18-0~18-8) 9세션 분할 경험상 세션별 작은 단위 이동 + 5회 루프 + Codex 검증이 가장 안정적이었다. |
| 대안 | (1) 한 PR 에 도메인 13개 (appointments / patients / staff / leaves / treatments / stats / sms / admin / backup / ai / audit / settings / export_import) 모두 이동. (2) 도메인 그룹 (예: 환자/예약 묶음 + 통계/문자 묶음 + AI 묶음) 3개 PR. (3) 단일 폴더 (예: appointments) 만 이동 후 멈추기. |
| 선택하지 않은 이유 | (1) 단일 PR 이동 시 코드 diff 가 5000줄 이상 → Codex / 사용자 모두 검토 불가. 회귀 발생 시 rollback = 전체 분리 무효. (2) 그룹 PR 도 helper 의존성 정리가 묶음 안에서 동시 발생 → 추적 어려움. (3) 단일 분리 후 멈추면 wrapper 가 무한 보유되어 코드 베이스가 *중간 상태* 로 남음. |
| 기대 효과 | (1) 세션별 회귀 검증이 명확. (2) Codex 검증이 변경 범위 안에서 완결. (3) 5회 루프 실패 시 *해당 세션만* rollback 가능 (`git revert <commit>`). (4) 사용자 PR 리뷰 가능 (도메인 1개 단위). |
| 위험 | (1) wrapper 가 일정 기간 살아남아 코드 베이스가 *중간 상태* — 19-P-2 §8-3 + 19-P-6 §3-1 으로 wrapper 보유 정책 명시. (2) 세션 사이에 우선순위 변경 가능성 (예: appointments 분리 우선) — 19-P-3 §31 / 19-P-6 §2 권장 순서로 방어. (3) 분리 도중 다른 v1.x fix 가 들어오면 충돌. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §1 P-5 + §8-1 + §8-3, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §1 R-2 + R-3 + R-7 + §2-1 표 (15개 실행 세션), [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §1 T-6 + T-7 + T-8. |
| 관련 테스트/하네스 | 도메인별 contract 테스트 (분리 *직전* 신규 추가 — 19-P-5 §4 보강 9개). 18-8 baseline 회귀 (529 passed) — 모든 세션 종료 시점 확인. PyInstaller 53 tests — 신규 모듈 폴더 추가 시점. |
| Codex 검증 포인트 | (1) 본 19-P-8 산출이 *세션 1개 = 모듈 1개* 정책과 충돌하지 않는지. (2) wrapper 보유 기간 / 제거 시점이 19-P-2 §8-3 + 19-P-6 §3-1 과 정합한지. (3) rollback 단위 (`git revert <commit>`) 가 1회로 가능한지. |

### 2-C. 결정 C — 왜 API URL 과 응답 key 를 유지해야 하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-C** |
| 결정 내용 | 분리 전후 모든 **API URL 100% 보존 + 응답 dict 키 100% 보존**. 추가만 허용, 제거 / rename / 타입 변경 ⊥. |
| 결정 이유 | (1) [main.html](../../app/templates/main.html) 7331줄 인라인 JS 가 응답 키 (`not_found` / `answer` / `confidence` / `sources[].title` / `sources[].path` / `version` / `treatment_codes` / `is_new_patient` 등) 에 직접 의존. (2) `/api/therapist-leaves` 응답이 `therapist_id` / `employee_id` 양쪽 모두 반환하는 alias 도 보존 — 프론트가 양쪽 사용. (3) 단위화의 목적이 *기능 변경이 아닌 구조 안정화* — 응답 키를 바꾸는 순간 단위화 ≠ 단위화 (= 기능 변경). (4) 외부 노드 sync `ENTITY_MAP` 9개 키도 외부 호환을 위해 보존. |
| 대안 | (1) 응답 키를 새 구조에 맞춰 일괄 변경 (예: `therapist_id` → `staff_id` 통일). (2) URL 을 도메인별 prefix 로 reorganize (`/api/appointments` → `/api/v2/appointments`). (3) Pydantic out 스키마로 강제하면서 `extra="forbid"` 로 잠그기. |
| 선택하지 않은 이유 | (1) 응답 키 변경 = main.html 7331줄 + 인라인 JS 동시 수정 필수 — 회귀 폭 폭증. UI 분리는 19-P 비-목표. (2) URL prefix 변경 = 외부 sync 노드 / FullCalendar event ID / Alpine bind 모두 영향. (3) `extra="forbid"` 강제 = 후속 추가 키 (예: AI 응답 보강) 도입 시 마이그레이션 비용 높음. |
| 기대 효과 | (1) UI / sync / 외부 의존이 변경 0 으로 단위화 가능. (2) Codex / 사용자 PR 리뷰 시 *응답 키 dict 단위 비교* 만으로 검증 가능. (3) 분리 후에도 main.html 회귀 0. |
| 위험 | R-APPT-01 (예약 응답 키) / R-PAT-02 (환자 counts dict) / R-STAT-01-02 (통계 8 GET) / R-SMS-01-02 (SMS 응답) / R-ADM-* / R-AUDIT-01 / R-EXIM-01-02 / R-CORE-04-05. 비-AI 86 endpoint contract 부재 (19-P-1 §22 C-1) — 분리 *직전* 보강 필수. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §1 P-2 + §7-1 + §7-2, [19_refactor_current_state.md](19_refactor_current_state.md) §21 (33+ 키 셋), [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §1 T-3, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §1 R-4. |
| 관련 테스트/하네스 | API contract 테스트 (분리 *직전* 도메인별 신규 추가). 기존 contract 테스트: [test_ai_manual_rag_contract.py](../../tests/test_ai_manual_rag_contract.py), [test_ai_contract_manual.py](../../tests/test_ai_contract_manual.py), [test_ai_health_public.py](../../tests/test_ai_health_public.py), [test_ai_health_status.py](../../tests/test_ai_health_status.py), [test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py). |
| Codex 검증 포인트 | (1) 본 19-P-8 산출이 응답 키 보존 정책과 일관한지. (2) 86 endpoint contract 미작성 캐비엇이 19-x 분리 직전 보강으로 명시되어 있는지. (3) 비-AI alias (`therapist_id` 이중 키) 보존 표현이 일관한지. |

### 2-D. 결정 D — 왜 DB schema 변경을 최소화하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-D** |
| 결정 내용 | 본 19-P 기간 내에 **m001 ~ m013 diff 0**. 신규 마이그레이션 m014+ 는 가능하면 미도입. 컬럼 rename / 타입 변경 / 삭제 ⊥. |
| 결정 이유 | (1) 운영 환경 DB (`%APPDATA%\도수치료예약\clinic.db`) 가 사용자별로 *서로 다른 상태* — 마이그레이션 실패 시 복구 비용이 높다. (2) 구조 리팩토링과 schema 변경을 *섞으면* 회귀 발생 시 원인 추적이 어렵다 (구조 vs 마이그레이션). (3) 마이그레이션은 별도 세션 (예: 노쇼 컬럼 / Patient.doctor_id) 에서 dedicated 로 진행하는 편이 안전. (4) 분리 후에도 ORM 19개 클래스명 / 컬럼명 / UNIQUE 제약 보존. |
| 대안 | (1) 단위화 도중 자연스럽게 새 컬럼 (예: `Appointment.no_show`, `Patient.doctor_id`) 추가. (2) 마이그레이션 실패 시 자동 rollback 구조 도입. (3) ORM 클래스명을 modules 위치에 맞춰 재명명. |
| 선택하지 않은 이유 | (1) 분리 + 마이그레이션 동시 → 회귀 발생 시 *어디 책임* 인지 모름. 사용자 운영 DB 손상 위험. (2) 자동 rollback 은 SQLite 기준 부분만 가능 — 컬럼 추가는 롤백 가능, 데이터 변환은 어려움. (3) ORM rename = sync `ENTITY_MAP` 외부 노드 호환 깨짐. |
| 기대 효과 | (1) 운영 DB 안정성 보존. (2) 회귀 추적이 *구조 분리* 로 좁혀짐. (3) 마이그레이션 실패 시 별도 세션에서 dedicated 분석. (4) 사용자 백업 정책 (`backups/*.db`) 그대로. |
| 위험 | R-BAK-01 ~ R-BAK-05 (운영 DB / 백업 / 복구). R-OPS-01 ~ R-OPS-03 (운영 DB 경로 / 외부 API). m014+ 미도입 → 부재 항목 (`Appointment.no_show`, `Patient.doctor_id`, `Doctor.schedule`) 은 19-P 후속 검토. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §1 P-4 + §7-3, [19_refactor_current_state.md](19_refactor_current_state.md) §4-1 (m001~m013), [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §1 R-6, [CLAUDE.md](../../CLAUDE.md) "DB 컬럼명을 임의로 변경하지 않는다", [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §1-2. |
| 관련 테스트/하네스 | [scripts/check_db_path.py](../../scripts/check_db_path.py) (운영 DB 경로 차단). [tests/conftest.py](../../tests/conftest.py) 4단계 격리. [tests/harness/db_guard.py](../../tests/harness/db_guard.py) `assert_safe_db_path()`. [tests/test_migration_spec_discovery.py](../../tests/test_migration_spec_discovery.py). |
| Codex 검증 포인트 | (1) `git diff --stat bcd74a7 -- app/migrations/` = 0 (m001~m013 무수정). (2) `app/models/models.py` 19개 ORM 클래스 / 컬럼 / UNIQUE 제약 무변경. (3) `dosu_clinic.spec` hidden imports 의 마이그레이션 경로가 19-P-1 §1 과 일치. |

### 2-E. 결정 E — 왜 router/service/repository/rules/schemas 구조를 선택하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-E** |
| 결정 내용 | modules 의 표준 파일 구조: **`router.py` (API endpoint) / `service.py` (비즈니스 로직) / `repository.py` (DB 접근) / `schemas.py` (Pydantic In/Out) / `rules.py` (업무 규칙) / `availability.py` (예약 가능 여부) / `completion_rules.py` (완료체크) / `aggregators.py` (통계 집계) / `provider.py` (외부 서비스 client) / `templates.py` (SMS 템플릿)**. |
| 결정 이유 | (1) FastAPI 표준 패턴 — router 는 endpoint + Depends, service 는 트랜잭션 경계, repository 는 SQLAlchemy 쿼리 만, schemas 는 순수 타입. (2) 책임이 *파일명* 으로 명확. (3) 테스트 단위가 명확 — service / repository / rules 는 단위 테스트 가능 (DB fixture / mock 분리 가능). (4) 순환참조를 줄일 수 있음 (router → service → repository → models 단방향). |
| 대안 | (1) 단일 `module.py` 파일 안에 router + service + repository 통합. (2) FastAPI [APIRouter](https://fastapi.tiangolo.com/tutorial/bigger-applications/) 표준만 따르고 service 계층 생략. (3) Domain-Driven Design (DDD) 의 Aggregate / Entity / Value Object 도입. (4) Hexagonal Architecture (Port / Adapter) 도입. |
| 선택하지 않은 이유 | (1) 단일 파일 통합 = `api.py` 5127줄 문제 *모듈별로* 재발생. (2) service 생략 = router 안에 비즈니스 로직 혼재 → 테스트 어려움. (3) DDD = 본 프로젝트 규모 (사용자 단독 / 단일 SQLite) 에 과잉. 학습 비용 + 구조 비용. (4) Hexagonal = 외부 경계가 sms.provider / ai.provider 정도로 적음. 도입 비용 > 효과. |
| 기대 효과 | (1) 도메인별 책임 분리. (2) repository 단위 / service 단위 테스트 분리 가능. (3) router 단위 contract 테스트 분리 가능. (4) 순환참조 방지 (D-1 ~ D-13 19-P-4 §1). |
| 위험 | R-CORE-01 (router → service → repository 단방향 위반). R-CORE-02 (core → modules 역참조). R-CORE-03 (중복 query). 분리 도중 service 와 repository 의 책임 경계가 *애매한 헬퍼* (예: `_serialize_*`) 가 어디로 가야 할지 결정 필요 — 도메인 분리 직전 결정. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §2 + §5 + §6, [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §1 D-1 ~ D-13 + §2 + §3, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-1 (19-1 core 분리). |
| 관련 테스트/하네스 | 분리 *직전* 도메인별 contract 테스트 (router 응답 키). service / repository 단위 테스트 (분리 후 신규 추가). [test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) 53 tests — 새 modules 폴더 추가 시 hidden imports 갱신 검증. |
| Codex 검증 포인트 | (1) 분리 후 router 가 비즈니스 로직 보유 ⊥ (service 위임). (2) repository 가 다른 모듈 service / repository 호출 ⊥. (3) core → modules 역참조 ⊥. (4) D-1 ~ D-13 의존성 방향 정합. |

### 2-F. 결정 F — 왜 appointments 를 초반에 크게 건드리지 않는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-F** |
| 결정 내용 | **appointments 분리는 19-9 (마지막에서 두 번째)**. 19-1 ~ 19-8 에서 patients / staff / treatments / leaves / availability / completion_rules / export_import / settings / core / audit 모두 분리된 후 진입. |
| 결정 이유 | (1) 예약은 환자 / 치료사 / 의사 / 휴무 / 치료항목 / 문자 / 통계 / 완료체크 와 모두 연결. 19-P-3 §31 우선순위 14 (마지막). (2) 가장 위험도 높음 — R-APPT-01 ~ R-APPT-07 + R-LOCK-01 ~ R-LOCK-03 (낙관적 락 / TOCTOU / 중복 검사 / 휴무 차단 / 점심창). (3) availability / leaves / treatments / patients / staff 경계가 먼저 정리되어야 appointments 분리 시 *의존 dependency* 가 안정. (4) 19-P-7 §3-A 치명 위험 8개 중 2개 (R-APPT-02 / R-APPT-03) 가 appointments 직접 영향. |
| 대안 | (1) appointments 를 첫 번째로 분리 (가장 큰 도메인 우선). (2) appointments 와 patients 묶음 분리. (3) appointments 분리는 19-P 비-목표로 두고 v1.5.0 별도 세션. |
| 선택하지 않은 이유 | (1) 첫 분리 시 patients / staff / treatments / leaves repository 가 *원래 위치* 에 있어 의존성 wrapping 이 폭증. (2) 묶음 분리 = DEC-B (단위화 분할) 위반. (3) 19-P 비-목표로 두면 86 endpoint 중 10 endpoint 가 *원래 자리* 에 남아 단위화 *불완전*. |
| 기대 효과 | (1) 의존 도메인이 안정된 상태에서 appointments wrapping. (2) `_serialize_appointment` / `_check_lunch_block` / `_check_version` / `_bump_patient_count` 가 명확한 modules 의 service 호출로 위임 가능. (3) 회귀 추적이 좁아짐 (이미 분리된 모듈은 영향 0). |
| 위험 | (1) 19-9 까지 도달 못하면 appointments 가 분리되지 않은 채로 19-P 종료. — 19-P-6 §2-1 + §6 (15개 실행 세션 명시) 으로 방어. (2) 분리 도중 5회 루프 실패 → rollback. (3) availability 가 19-4 에서 *불완전 분리* 되면 appointments 도 흔들림 — 19-P-5 §3-1 + §3-5 보강 필수. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-1 + §9 (M-01 우선순위 14), [19_refactor_module_map.md](19_refactor_module_map.md) §2-1, [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-A + §6, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-9 (19-9 세션 계획), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-A R-APPT-01 ~ 07. |
| 관련 테스트/하네스 | [test_appointment_rules.py](../../tests/test_appointment_rules.py) (xfail 3건 + skip 1건 → 19-4 / 19-9 분리 직전 정방향 전환). 점심창 / PUT / DELETE / 409 / 응답 키 contract — 분리 직전 신규 추가. FullCalendar event 형식 회귀 — 사용자 수동 smoke. |
| Codex 검증 포인트 | (1) appointments 가 19-9 에 위치하는지. (2) 의존 도메인 (patients / staff / treatments / leaves / availability) 이 19-1 ~ 19-8 에 모두 포함. (3) 19-9 분리 직전 contract 테스트 보강 9개 항목 명시 (R-APPT-01 ~ 07 → 보강 매핑). |

### 2-G. 결정 G — 왜 availability 를 별도 책임으로 두는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-G** |
| 결정 내용 | **`modules/appointments/availability.py`** 신설 — 점심창 / 충돌 검사 / 휴무 차단 (full / am / pm) / 반차 정책 / 백엔드 우회 방지 모두 위임. 19-4 에서 사전 분리 (appointments 분리 *직전*). |
| 결정 이유 | (1) 예약 가능 시간 / 휴무 차단 / 반차 차단 / 도수 중복 검사가 *각자 핵심 업무 규칙* 인데 현재 `api.py` 에서 헬퍼로 분산. (2) 프론트 차단만으로는 부족 — devtools / manual POST 우회 가능. 백엔드에서 검증 필수. (3) appointments 의 과도한 책임을 줄임. (4) 휴무 차단 (R-APPT-03) 과 도수 중복 차단 (R-APPT-02) 이 현재 백엔드 미구현 — 19-4 에서 차단 코드 신설 + xfail 정방향 전환. |
| 대안 | (1) appointments / leaves / treatments 의 service 안에서 각자 검증 (분산). (2) 단일 helper 모듈 (`shared/availability.py`) 로 두기. (3) Pydantic validator 안에서 처리 (router 단계). |
| 선택하지 않은 이유 | (1) 분산 = 동일 정책이 여러 곳에 중복. 변경 시 누락 위험. (2) 단일 helper 는 modules 외부 = D-4 (core → modules ⊥) 와 충돌. (3) Pydantic validator = DB 조회 필요한 검증 (휴무 / 충돌 / 환자 존재) 에 부적합. |
| 기대 효과 | (1) 예약 차단 / 충돌 / 반차 정책의 *단일 진실원천*. (2) 19-P-7 R-APPT-02 / R-APPT-03 / R-APPT-04 / R-APPT-05 / R-APPT-06 모두 본 모듈에서 일괄 검증. (3) AI 자연어 휴무 (`action_leave`) 등록 시에도 동일 차단 정책 호출 가능. |
| 위험 | R-APPT-02 (도수 중복 백엔드 미구현 — xfail 3건 + skip 1건). R-APPT-03 (휴무 차단 백엔드 미구현 — xfail 4건). R-APPT-04 (12:00 기준). R-APPT-05 (점심창). R-APPT-06 (devtools 우회). 19-4 분리 직전 보강 필수. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §2-1 (`appointments/availability.py`) + §4 (availability 분류표) + §3-1, [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-A + §5-2, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-1, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-4 (19-4), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-A R-APPT-02~06. |
| 관련 테스트/하네스 | [test_appointment_rules.py](../../tests/test_appointment_rules.py) 의 xfail 3건 + skip 1건 정방향 전환. [test_therapist_leave.py](../../tests/test_therapist_leave.py) 의 xfail 4건 정방향 전환. 점심창 / PUT / DELETE / 409 / `_check_lunch_block` 호출지 — 19-4 분리 직전 신규. |
| Codex 검증 포인트 | (1) `_lunch_window` / `_check_lunch_block` / 충돌 검사 / 휴무 차단 / 반차 정책이 모두 `availability.py` 로 위임. (2) xfail 3건 + skip 1건 + xfail 4건 = 8건 정방향 전환. (3) 12:00 기준 정확. (4) AI action_leave 가 동일 차단 정책 호출 (단일 진실원천). |

### 2-H. 결정 H — 왜 leaves 를 appointments 와 분리하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-H** |
| 결정 내용 | **`modules/leaves/`** 별도 모듈. 휴무 등록 / 표시는 본 모듈 책임, 휴무 차단은 `appointments/availability.py` 가 leaves.repository 를 read-only 호출. AI 자연어 휴무 (`action_leave`) 도 `leaves.service._upsert_employee_leave_core` 단일 진실원천. 19-5 에서 분리. |
| 결정 이유 | (1) 휴무 등록 / 표시 / 차단은 *서로 연결되지만 책임이 다름*. 등록 = leaves, 표시 = leaves + (post-19-P calendar), 차단 = appointments/availability. (2) 종일 (`full`) / 오전반차 (`am`) / 오후반차 (`pm`) / 연차 (`annual`) / 월차 (`monthly`) 규칙을 독립적으로 테스트 필요. (3) AI action_leave (917줄) 가 `_upsert_employee_leave_core` 만 호출하도록 *단일 진실원천* 정책 보존 — 시그니처 절대 변경 ⊥. (4) `(employee_id, leave_date)` UNIQUE (m011) 제약은 leaves 안에서만 보존. |
| 대안 | (1) leaves 를 appointments 안에 흡수 (단일 모듈). (2) leaves 를 staff 안에 흡수 (직원 하위). (3) AI action_leave 가 leaves 우회하고 직접 EmployeeLeave write. |
| 선택하지 않은 이유 | (1) appointments 안 흡수 = 등록 vs 차단 책임 혼재. AI 호출 경로 복잡화. (2) staff 안 흡수 = staff 가 휴무 등록 책임을 가져 D-9 (staff ⊥ leaves write) 위반. (3) AI 가 leaves 우회 = 단일 진실원천 깨짐 (R-LEAVE-01). 검증 / 차단 / audit 정책이 두 곳에서 따로 관리되어 회귀 위험. |
| 기대 효과 | (1) 휴무 등록 / 표시 / 차단의 책임 분리. (2) AI action_leave 가 도메인 service 호출만 = local-first 원칙 보존 (D-6). (3) 종일 / 반차 / 연월차 정책 테스트 분리. (4) `_upsert_employee_leave_core` 시그니처 보존으로 sync `ENTITY_MAP[employee_leave]` 외부 호환. |
| 위험 | R-LEAVE-01 ~ R-LEAVE-04 (단일 진실원천 / 종일+반차 차단 / 중복 / 캘린더 표시). R-APPT-03 (휴무 차단 백엔드 미구현 — appointments availability 책임). R-AI-* (AI action_leave 가 도메인 service 우회 ⊥). |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-4 + §2-1 (`modules/leaves/`), [19_refactor_module_map.md](19_refactor_module_map.md) §2-5 (leaves), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-E, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-5, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-5 (19-5), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-E. |
| 관련 테스트/하네스 | [test_therapist_leave.py](../../tests/test_therapist_leave.py) (xfail 4건 정방향 전환 + 반차 허용 회귀 보존). [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) (parse / preview / execute + HMAC + TOCTOU + `_upsert_employee_leave_core` 호출 회귀). [test_employee_leave_unique_violation.py](../../tests/test_employee_leave_unique_violation.py) (m011 UNIQUE). |
| Codex 검증 포인트 | (1) `_upsert_employee_leave_core` 시그니처 보존. (2) AI action_leave 가 leaves.service 호출만 = 단일 진실원천. (3) 종일 / 반차 차단 4건 정방향 전환 (19-5 보강). (4) sync `ENTITY_MAP[employee_leave]` 키 무변경. |

### 2-I. 결정 I — 왜 treatments / completion_rules 를 분리하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-I** |
| 결정 내용 | **`modules/treatments/router.py / service.py / repository.py / schemas.py / completion_rules.py`** 분리. completion_rules 는 approve / revert-approve 시 done_count ±N 책임. `manual60 count_increment=1` 보존. 19-6 에서 분리. |
| 결정 이유 | (1) 도수치료 시간별 (manual30 / manual60), 체외충격파 (eswt), 의사 항목 (injection / cartilage) 등 다양한 치료항목 분기. (2) 완료체크 = "시간 가중치 (manual60 = 2) 가 아니라 항목별 개별 체크 (manual60 = 1)" 원칙 보존 ([CLAUDE.md](../../CLAUDE.md) "manual60 = 1카운트 정책"). (3) 통계 / 환자 / 예약과 연결되므로 규칙 분리 필요. (4) approve / revert 의 `_bump_patient_count` 가 PatientTreatmentCount write — patients.repository 와의 경계 명확화. |
| 대안 | (1) `count_increment` 를 manual60 = 2 로 되돌려 시간 가중치 기반 통계. (2) treatments 와 patients 의 PatientTreatmentCount 를 patients 모듈 안에서 통합. (3) completion_rules 를 appointments 안에 흡수. |
| 선택하지 않은 이유 | (1) [CLAUDE.md](../../CLAUDE.md) "manual60 을 다시 count_increment=2 로 되돌리지 않는다 (manual60 = 1카운트 정책)" 명시. 운영 정책 결정. (2) PatientTreatmentCount = 환자 + 치료항목 결합이라 patients 흡수 시 치료항목 변경 영향이 환자 모듈에 폭증. (3) appointments 흡수 시 approve / revert 책임이 appointments 거대화 — DEC-F (appointments 책임 줄이기) 와 충돌. |
| 기대 효과 | (1) 치료항목 CRUD + 완료체크 정책 분리. (2) `manual60 = 1` 보존. (3) 통계 / 예약 / 환자가 treatments.repository 호출 (read-only). (4) approve / revert 흐름 분리 가능 (R-TX-04 done_count 음수 방지). |
| 위험 | R-TX-01 ~ R-TX-04 (manual60 / 완료체크 / count_increment / done_count). R-APPT-* (예약 approve / revert 흐름). [tests/test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py) 회귀. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-5 + §2-1 (`modules/treatments/`), [19_refactor_module_map.md](19_refactor_module_map.md) §2-6 (treatments), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-F, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-6, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-6 (19-6), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-F R-TX-01~04, [CLAUDE.md](../../CLAUDE.md) (manual60 정책), [app/models/constants.py:20](../../app/models/constants.py:20) `count_increment=1`. |
| 관련 테스트/하네스 | [test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py). [test_stats_counts.py](../../tests/test_stats_counts.py) (manual 카운트 집계). approve / revert / done_count 0 미만 방지 — 19-6 분리 직전 신규. |
| Codex 검증 포인트 | (1) `manual60 count_increment=1` 무변경. (2) approve / revert 흐름 동치. (3) done_count Lazy 생성 + 0 미만 방지. (4) treatments → patients.repository (write done_count) 단방향 (D-2). |

### 2-J. 결정 J — 왜 stats 를 별도 모듈로 분리하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-J** |
| 결정 내용 | **`modules/stats/router.py / service.py / repository.py / schemas.py / aggregators.py`** + **`modules/export_import/`** (엑셀 export). stats 는 *read-only* — 다른 도메인 데이터를 읽기만, write ⊥. 19-11 에서 분리. |
| 결정 이유 | (1) 8 GET endpoint (`/api/stats/by-{therapist,hour,weekday,treatment}`, `/api/stats/{summary,daily,daily-by-therapist,manual-by-therapist}`) + 엑셀 export 2개 + manual-counts upsert 1개로 복잡. (2) 예약 / 완료 / 치료항목 / 치료사 / 신환 / 시간대 / 요일별 집계가 *여러 모듈 데이터* 결합. (3) 상태 변경 ⊥ (D-7) — stats 는 *read-only* 가 핵심 정책. (4) 집계 기준 변경 위험 (R-STAT-01~05) 을 줄이기 위해 분리. |
| 대안 | (1) stats 를 appointments 안에 흡수. (2) stats 를 treatments 안에 흡수 (치료항목별 집계 위주). (3) ManualCount 만 별도 모듈 (`modules/manual_counts/`). |
| 선택하지 않은 이유 | (1) appointments 흡수 = appointments 거대화 + DEC-F 충돌. (2) treatments 흡수 = 치료사별 / 신환 / 시간대 통계가 treatments 외부 데이터 의존이라 책임 부적합. (3) ManualCount 별도 = 통계 흐름이 두 곳으로 갈라짐. |
| 기대 효과 | (1) read-only 책임 분리. (2) 8 endpoint 응답 키 contract 분리 가능. (3) 엑셀 export 의 *데이터 조립* 부분만 stats 로, *엑셀 파일 생성* 은 export_import. (4) `_get_manual_treatment_rows` / `_doctor_codes_set` 등 헬퍼가 stats 안 명확한 위치. |
| 위험 | R-STAT-01 ~ R-STAT-05 (예약-완료 / 치료사 / 항목 / 시간-요일 / 신환). R-EXIM-01-02 (엑셀 export). 8 endpoint contract 부재 — 19-11 분리 직전 보강 필수. `is_doctor_filter` 분기 (M-03b 의 staff.doctors_service) 가 stats 로 흘러와 의존. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-6 + §2-1 (`modules/stats/`), [19_refactor_module_map.md](19_refactor_module_map.md) §2-7 (stats), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-G + §1 D-7, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-7, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-11 (19-11), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-G + §2-P. |
| 관련 테스트/하네스 | [test_stats_counts.py](../../tests/test_stats_counts.py). 8 endpoint 응답 키 contract — 19-11 분리 직전 신규. ManualCount UNIQUE (m006). |
| Codex 검증 포인트 | (1) stats → 도메인 (read only) 단방향 (D-7). (2) ManualCount upsert UNIQUE 보존. (3) 엑셀 export 데이터 조립이 stats, 파일 생성이 export_import. (4) `is_doctor_filter` 가 staff.doctors_service 호출 (M-03b). |

### 2-K. 결정 K — 왜 sms 를 appointments 와 분리하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-K** |
| 결정 내용 | **`modules/sms/router.py / service.py / templates.py / provider.py / schemas.py`** 분리. 외부 munjanara API 호출은 `provider.py` 단일 경계. 예약 변경이 SMS 자동 트리거 ⊥ (D-8). 19-10 에서 분리. |
| 결정 이유 | (1) 문자 대상 추출 (`tomorrow-targets`) 과 예약 상태 변경은 *다른 책임*. (2) 문자나라 외부 API 연동 / 템플릿 / 발송 경계를 분리해야 외부 HTTP mock + timeout / 응답 디코딩 / 마스킹 정책 보존. (3) 테스트 중 *실제 외부 발송* 을 막기 쉬움 (provider mock). (4) `munjanara_key` 마스킹 + `_normalize_phone_for_sms` / `_is_valid_kr_mobile` / `_mask_phone_for_log` / `_sms_sanitize` 등 helper 통합. |
| 대안 | (1) SMS 를 appointments 안에 흡수 (예약 변경 시 자동 SMS). (2) `sms.provider` 를 별도 분리 안 하고 sms.service 안에 inline 유지. (3) SMS 를 노티피케이션 통합 모듈로 흡수 (notifications 후속). |
| 선택하지 않은 이유 | (1) 자동 트리거 = 예약 상태 변경의 *부수 효과* — 사용자가 명시적으로 발송 버튼을 눌러야 한다는 현재 정책 위반. R-SMS-05 (자동 트리거 위험). (2) inline 유지 = 외부 HTTP mock 어려움 + provider 시점 디코딩 정책 보존 어려움. (3) notifications 통합 = 현재 미구현. SMS 만 도입된 상태에서 통합은 과잉. |
| 기대 효과 | (1) 예약 상태 변경과 SMS 발송의 분리. (2) 외부 munjanara API mock 가능. (3) `munjanara_key` 마스킹 / 전화번호 마스킹 / 응답 디코딩 정책 보존. (4) 자동 발송 트리거 ⊥ 정책 보존 (D-8). |
| 위험 | R-SMS-01 ~ R-SMS-05 (대상 / 템플릿 / 계정 / 외부 발송 / 자동 트리거). R-OPS-03 (외부 API 차단). [test_sms_validation.py](../../tests/test_sms_validation.py) 회귀. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-7 + §2-1 (`modules/sms/`), [19_refactor_module_map.md](19_refactor_module_map.md) §2-8 (sms), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-H + §1 D-8, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-9, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-10 (19-10), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-H R-SMS-01~05. |
| 관련 테스트/하네스 | [test_sms_validation.py](../../tests/test_sms_validation.py), [test_ai_sms_validate.py](../../tests/test_ai_sms_validate.py), [test_ai_sms_draft.py](../../tests/test_ai_sms_draft.py), [test_ai_sms_draft_hallucination.py](../../tests/test_ai_sms_draft_hallucination.py). 외부 HTTP mock — 19-10 분리 직전 신규. |
| Codex 검증 포인트 | (1) sms ⊥ appointments (write). (2) `provider.py` 가 외부 HTTP 단일 경계. (3) `munjanara_key` 마스킹 보존. (4) 자동 발송 트리거 ⊥ 정책. |

### 2-L. 결정 L — 왜 patients / notes 를 분리하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-L** |
| 결정 내용 | **`modules/patients/router.py / service.py / repository.py / schemas.py / notes_service.py`** 분리. 환자별 메모 (`Patient.memo`) 는 patients 안 `notes_service.py`. 통합 `modules/notes/` 신설은 post-19-P 후속 (M-27). 19-7 에서 분리 (export_import 와 함께). |
| 결정 이유 | (1) 환자 정보 / 메모는 *개인정보 (PII) 위험* 이 큼. PII 원문이 audit_log / AiUsageLog / 응답에 부재 정책 보존 필수. (2) 메모 종류: 환자별 메모 (`Patient.memo`) / 예약별 메모 (`Appointment.memo`) / 당일 메모 / 지속 메모 — 경계가 흐릿. (3) data-convert (~600줄 `_dc_*` 헬퍼) 가 환자 import 에 의존 — export_import 와 동시 분리. (4) 통합 `modules/notes/` 는 *지속 메모 vs 당일 메모* 정책 결정 후 post-19-P. |
| 대안 | (1) patients 와 notes 를 처음부터 별도 모듈 (`modules/patients/`, `modules/notes/`). (2) 환자 메모를 `Patient.memo` 가 아니라 별도 테이블로 분리 (m014+). (3) data-convert 를 patients 안에 흡수. |
| 선택하지 않은 이유 | (1) 통합 `modules/notes/` 는 정책 결정 미완 — 지속 / 당일 메모 / 환자별 / 예약별 메모 정책이 명확해진 후. (2) 별도 테이블 = m014+ 마이그레이션 필요 (DEC-D 위반). (3) data-convert 흡수 = patients 거대화 + ~600줄 import 로직이 patients 책임 외 (엑셀 변환). |
| 기대 효과 | (1) PII 보호 정책 분리 (`# SAFETY:` 태그). (2) 환자 검색 / 중복 검사 / 메모 / counts dict 책임 분리. (3) data-convert 와 동시 분리로 import / export 흐름 통합. (4) notes 통합은 post-19-P 결정. |
| 위험 | R-PAT-01 ~ R-PAT-05 (PII / 검색 / 신환 / 메모 경계 / 환자별 메모). R-EXIM-01-02 (엑셀 변환). 환자 검색 / 메모 경계 contract 부재 — 19-7 분리 직전 보강. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-2 + §4 (notes 분류) + §2-2 (post-19-P notes), [19_refactor_module_map.md](19_refactor_module_map.md) §2-2 (patients) + §2-14 (notes), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-B, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-2, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-7 (19-7), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-B + §2-M (notes 통합 메모). |
| 관련 테스트/하네스 | 환자 CRUD / 검색 / 메모 / counts dict 응답 contract — 19-7 분리 직전 신규. PII 비노출 회귀 ([test_ai_logging.py](../../tests/test_ai_logging.py), [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py)). |
| Codex 검증 포인트 | (1) `Patient.memo` 가 patients 안 `notes_service.py` 위치. (2) PII 원문이 응답 / 로그에 부재. (3) data-convert 가 export_import 로 분리. (4) 통합 `modules/notes/` 신설은 post-19-P 후속 분류 명시. |

### 2-M. 결정 M — 왜 therapists 와 doctors / medical_staff 를 구분 또는 후보로 두는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-M** |
| 결정 내용 | **`modules/staff/`** 단일 통합 (Employee 단일 테이블 + role 분기) — `staff/router.py / service.py / repository.py / schemas.py / doctors_service.py` (얇은 분기). **별도 `modules/doctors/` 신설은 post-19-P 후속 (M-31)** — EMR 연동 도입 시. 19-8 에서 분리. |
| 결정 이유 | (1) 현재 `Employee` 단일 테이블 + `role` 컬럼 (`"doctor"` / `"therapist"`) 분기 구조. (2) 별도 `modules/doctors/` 분리 시 m014+ (Doctor 별도 테이블 / Department / Room / DoctorSchedule / Order / Prescription) 마이그레이션 필요 — DEC-D 위반. (3) 현재 부재 항목 (담당의 / 진료과 / 진료실 / 의사별 일정 / 오더 / 처방) 을 *현재 구현된 것처럼 단정 ⊥*. (4) `_doctor_codes_set` / assignment role 강제 / `is_doctor_filter` / 엑셀 doctor suffix 등 *얇은 분기* 만 있는 현재 상태에서 별도 폴더는 과잉. |
| 대안 | (1) `modules/doctors/` + `modules/therapists/` 처음부터 분리. (2) `modules/staff/{doctors,therapists}/` 서브 디렉토리 분리. (3) `modules/staff/` 단일 — doctor / therapist 함수 별도 분리 안 함. |
| 선택하지 않은 이유 | (1) m014+ Doctor 테이블 신설 + Patient.doctor_id 추가 필요 — DEC-D / R-14 위반. EMR 연동은 비-목표. (2) 서브 디렉토리 = 현재 단일 테이블 분기 수준에는 과잉. (3) 단일 함수 통합 = `_doctor_codes_set` / `is_doctor_filter` 등 의사 분기 헬퍼가 staff.service 안에 흩어짐 — 분기 책임이 모호. |
| 기대 효과 | (1) Employee 단일 테이블 정합성 보존. (2) doctor / therapist 분기는 `staff.doctors_service` 가 통합. (3) post-19-P EMR 연동 시 별도 `modules/doctors/` 신설 가능 (R-DOC-01 ~ R-DOC-02 후속 검토). (4) 의사 시드 자동 활성화 ⊥ 보존 (T-14). |
| 위험 | R-THER-01 ~ R-THER-03 (활성 / 치료항목 / 색상). R-DOC-01 ~ R-DOC-02 (doctors 단정 / 담당의 후속). R-32 ~ R-35 후속 (M-31 ~ M-35). 부재 항목 (`Patient.doctor_id`, `Doctor.schedule`, `Order`, `Prescription`) 단정 ⊥. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-3 + §2-2 (post-19-P doctors), [19_refactor_module_map.md](19_refactor_module_map.md) §2-3 (therapists) + §2-4 (doctors / medical_staff), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-C + §2-D, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-3 + §3-4, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-8 (19-8), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-C R-THER-01~03 + §2-D R-DOC-01~02. |
| 관련 테스트/하네스 | [test_employee_*.py](../../tests/) (4 파일) + [test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py) + [test_employee_hire_date.py](../../tests/test_employee_hire_date.py) + [test_employee_leave_unique_violation.py](../../tests/test_employee_leave_unique_violation.py). assignment role=doctor 강제 회귀 — 19-8 분리 직전 신규. |
| Codex 검증 포인트 | (1) `modules/staff/` 단일 통합 — 별도 `modules/doctors/` 신설 ⊥. (2) Employee `role="doctor"|"therapist"` 분기 정합. (3) alias `therapist_id` / `employee_id` 이중 키 보존. (4) 의사 부재 항목 (Patient.doctor_id 등) 단정 ⊥. |

### 2-N. 결정 N — 왜 AI/RAG local-first 원칙을 유지하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-N** |
| 결정 내용 | **AI/RAG local-first 원칙** 보존 — (1) 외부 API 토큰 비용 최소화, (2) 개인정보 보호, (3) 할루시네이션 방지, (4) API key 없이도 local 기능 유지, (5) sources 없음 / low_confidence / PII / unknown_feature 에서 provider 호출 ⊥. 19-13 에서 AI commands / 도메인 service 연결부 정리. |
| 결정 이유 | (1) [docs/AI_WORKING_RULES.md §2](../AI_WORKING_RULES.md) 절대 원칙. (2) 사용자가 AI 에 질문했다고 무조건 외부 API 토큰을 쓰지 않음 — 내부 처리 (DB 조회 / 고정 템플릿 / 규칙 매칭) 가능하면 LLM 호출 0. (3) Local Answer Composer 가 RAG 결과를 LLM 없이 조립 — LLM 은 보조. (4) Embedding 은 선택 기능 — 키워드 / Local Composer 만으로도 동작. (5) `local_only` 모드에서 `len(provider.calls) == 0` + `len(embedding_provider.calls) == 0` 단언. |
| 대안 | (1) 외부 LLM 중심 재설계 (모든 AI 응답에 LLM 사용). (2) Embedding 필수 (vector store 없으면 AI 비활성). (3) `local_only` 모드 제거. |
| 선택하지 않은 이유 | (1) 외부 LLM 중심 = 토큰 비용 폭증 + PII 외부 전송 위험 + API key 누출 가능성 + 할루시네이션 위험. (2) Embedding 필수 = 운영 환경 (사용자 단독 / 단일 SQLite) 에서 vector store 부재 시 AI 전체 비활성 — 사용자 경험 저하. (3) `local_only` 제거 = 18-AI 시리즈 absolute principle 위반. |
| 기대 효과 | (1) 운영 환경에서 외부 API 호출 0 가능. (2) PII 원문 외부 전송 ⊥. (3) API key 미등록 환경에서도 키워드 / Local Composer 만으로 매뉴얼 Q&A 동작. (4) 할루시네이션 방지 — sources 없으면 `not_found` 응답. |
| 위험 | R-AI-01 ~ R-AI-07 (local-first / sources / low_confidence / PII / 외부 API / 할루시네이션 / 의사 가드). R-LOCK-02 ~ R-LOCK-03 (lock / 동시성). |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §1 P-7 + §3-10 + §7-7, [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §1 + §2, [docs/ai_rag_decision_record.md](../ai_rag_decision_record.md), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §1 D-6 + §2-K, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §1 T-12 + T-13, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §1 R-12 + §3-13 (19-13), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-K R-AI-01~07. |
| 관련 테스트/하네스 | AI 하네스 6개 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid). [test_ai_assist_mode.py](../../tests/test_ai_assist_mode.py) + [test_local_only_mode.py](../../tests/test_local_only_mode.py) (`len(provider.calls) == 0`). [test_ai_hallucination.py](../../tests/test_ai_hallucination.py). [test_ai_logging.py](../../tests/test_ai_logging.py) (PII 비저장). [tests/conftest.py](../../tests/conftest.py) `_block_sdk_modules`. |
| Codex 검증 포인트 | (1) `local_only` 모드에서 provider / embedding calls 0. (2) `should_call_llm()` 다층 게이트 (provider_disabled / pii / local_only / no_sources / low_confidence) 보존. (3) AI / RAG → 도메인 DB 임의 생성 ⊥ (D-6). (4) PII 원문 응답 / 로그 부재. |

### 2-O. 결정 O — 왜 AI commands 와 DB 변경을 조심스럽게 다루는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-O** |
| 결정 내용 | AI 자연어 명령 (`action_leave` 917줄) 은 **`modules/ai/commands/`** 분리. parse / preview / execute + HMAC 토큰 + TOCTOU 보존. AI commands → leaves.service (write) 만 허용 (DB 변경). AI commands → appointments / patients (write) ⊥. 19-13 에서 분리. |
| 결정 이유 | (1) 자연어 명령이 *실제 예약 / 휴무 / 문자 변경* 으로 이어질 수 있음 — safety 와 검증 단계 필수. (2) DB 근거 없이 환자 / 예약 / 휴무 정보를 *생성 ⊥*. (3) HMAC 토큰 + TOCTOU 보호 + leaves.service 단일 진실원천 보존. (4) AI 가 도메인 DB 임의 변경하면 audit / sync / 일관성이 깨짐. |
| 대안 | (1) AI commands 가 appointments / patients write 도 허용. (2) HMAC 토큰 제거 (단순 confirm 만으로 execute). (3) AI 가 leaves.service 우회하고 EmployeeLeave 직접 write. |
| 선택하지 않은 이유 | (1) appointments / patients write 허용 = R-AI-* 치명 위험 (예약 / 환자 정보 임의 생성). (2) HMAC 제거 = preview 와 execute 사이 토큰 위변조 가능 — TOCTOU 공격. (3) leaves.service 우회 = DEC-H 단일 진실원천 위반. R-LEAVE-01 / R-AUDIT-* 위험. |
| 기대 효과 | (1) AI commands 가 도메인 service 호출만 = local-first 보존 (D-6). (2) HMAC 토큰 + TOCTOU 보호. (3) leaves.service 단일 진실원천. (4) AI commands 의 책임 분리 — parse / preview / execute. |
| 위험 | R-AI-01 ~ R-AI-07. R-LEAVE-01 (단일 진실원천). R-AI-* (의사 가드 후속). [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) 회귀. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-10 + §6-1 (commands → 도메인 write 허용 표), [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §2, [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-K + §1 D-6, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-? (action_leave), [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-13 (19-13), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-K R-AI-*. |
| 관련 테스트/하네스 | [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) (parse / preview / execute + HMAC + TOCTOU + `_upsert_employee_leave_core` 호출 회귀). [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py). [test_ai_hallucination.py](../../tests/test_ai_hallucination.py). |
| Codex 검증 포인트 | (1) AI commands → leaves.service (write) 만 허용. (2) AI commands → appointments / patients (write) ⊥. (3) HMAC 토큰 + TOCTOU 보존. (4) AI commands 가 DB 근거 없이 정보 생성 ⊥. |

### 2-P. 결정 P — 왜 health / settings / feature_flags 를 별도 경계로 두는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-P** |
| 결정 내용 | **`modules/settings/`** (SystemSetting + SmsSetting + AiSetting 통합 read/write) + **`core/feature_flags.py`** (AI_RAG_ENABLED / VECTOR / HYBRID + ai_mode 파생) + **`modules/health/`** (post-19-P 후속, M-28). API key 원문 노출 ⊥ — 모든 응답에 `api_key_set` boolean 만. 19-2 에서 settings / feature_flags 정리. |
| 결정 이유 | (1) AI 모드 / vector / hybrid on-off / API key 등록 여부 / 백업 상태 등 설정이 *여러 파일* (env / `AiSetting` / `SystemSetting`) 에 흩어지면 위험. (2) 단일 진입점 필요. (3) API key 원문 노출 = 보안 사고 — 모든 응답 / 로그 / audit 에서 마스킹. (4) `/api/health` 엔드포인트는 현재 부재 — `modules/health/` 신설은 post-19-P 후속. (5) feature_flags 의 환경 변수 vs DB 단일 진실원천 결정 (T-8) 은 19-2 에서. |
| 대안 | (1) feature_flags 를 settings 안에 흡수. (2) feature_flags 를 환경 변수로만 단일 (DB 무시). (3) API key 원문 응답에 포함 (마스킹 없이). (4) `/api/health` 를 19-P 안에서 신설. |
| 선택하지 않은 이유 | (1) settings 흡수 = settings 가 modules → core → modules 역참조 위험 (D-10 위반). (2) 환경 변수 단일 = 사용자 운영 환경에서 `.env` 수정 필요 — 운영 부담. (3) API key 원문 = 치명 보안 사고 (R-ADM-02). (4) `/api/health` 19-P 신설 = 비-목표 (사용자 결정 필요). |
| 기대 효과 | (1) 설정 / feature_flags / health 의 책임 분리. (2) API key 원문 비노출. (3) ai_mode (local_only / local_first / ai_assist) 단일 진입점. (4) `/api/health` 후속 검토 명시. |
| 위험 | R-ADM-01 ~ R-ADM-05 (admin 노출 / API key / AI 모드 / feature flag / audit). R-HEALTH-01 (`/api/health` 후속). |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §3-8 + §4 (health / settings / feature_flags 분류) + §2-2 (post-19-P health), [19_refactor_module_map.md](19_refactor_module_map.md) §2-15 (permissions/auth) + §2-16 (settings) + §2-19 (health/diagnostics) + §2-21 (feature_flags), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-I + §1 D-10, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-?, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-2 (19-2), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-I R-ADM-01~05 + §2-O R-HEALTH-01. |
| 관련 테스트/하네스 | [test_admin_auth_required.py](../../tests/test_admin_auth_required.py). [test_admin_ui_smoke.py](../../tests/test_admin_ui_smoke.py). [test_ai_assist_mode.py](../../tests/test_ai_assist_mode.py) + [test_local_only_mode.py](../../tests/test_local_only_mode.py) (feature_flags 파생 회귀). |
| Codex 검증 포인트 | (1) feature_flags 단일 진실원천 (T-8). (2) API key 원문 응답 / 로그 / audit 부재. (3) `/api/health` 후속 검토 명시 (코드 신설 X). (4) settings ⊥ admin 역참조. |

### 2-Q. 결정 Q — 왜 audit / logs 는 후속 검토로 두되 경계를 남기는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-Q** |
| 결정 내용 | **`modules/audit/`** 분리 (audit() / _log() 함수 통합) — 모든 CUD 모듈이 audit 호출. PII 원문 저장 ⊥. 보존 정책 (오래된 AI / 일반 audit 로그 삭제) 은 후속 검토. 19-12 에서 분리 (admin / backup / export_import 묶음). |
| 결정 이유 | (1) 예약 / 휴무 / 문자 / AI 명령 변경 기록은 *중요* — 운영 추적 / 사용자 신뢰. (2) 개인정보 원문 로그 저장은 *위험* — PII 마스킹 정책 (`pii.scan` / sha256 해시) 보존 필수. (3) 보존 정책 (보관 기간 / 자동 삭제) 은 운영 단계 결정 — 본 19-P 비-목표. (4) audit() 시그니처 보존 — 모든 모듈이 호출. |
| 대안 | (1) audit 을 별도 분리 안 하고 각 모듈이 직접 AuditLog write. (2) audit 을 core 에 흡수. (3) PII 원문 저장 (마스킹 없이). |
| 선택하지 않은 이유 | (1) 직접 write = 일관성 깨짐 (어떤 모듈은 audit 호출, 어떤 모듈은 직접 write). 호출 패턴 통합 어려움. (2) core 흡수 = audit 이 modules 역참조 (D-9 위반). (3) PII 원문 = R-PAT-01 / R-AUDIT-02 / R-AI-07 치명 보안 사고. |
| 기대 효과 | (1) audit 단일 진입점. (2) PII 마스킹 정책 보존. (3) 보존 정책 후속 검토 명시. (4) audit ⊥ 도메인 service (단방향 D-9). |
| 위험 | R-AUDIT-01 ~ R-AUDIT-02 (audit 응답 / PII). R-PAT-01 (PII). R-AI-07 (AI 로그 PII). 보존 정책 후속 — `docs/releases/18_ai_rag_known_risks.md` §3 정합. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §4 (audit / privacy 분류), [19_refactor_module_map.md](19_refactor_module_map.md) §2-17 (audit / logs) + §2-23 (privacy / retention), [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §2-N + §1 D-9, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3-?, [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-12 (19-12), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-N + §2-T (privacy 통합). |
| 관련 테스트/하네스 | [test_ai_logging.py](../../tests/test_ai_logging.py). [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py). audit 응답 키 contract — 19-12 분리 직전 신규. |
| Codex 검증 포인트 | (1) audit() 시그니처 보존 — 모든 모듈에서 호출. (2) PII 원문 audit_log / AiUsageLog 부재. (3) 보존 정책 후속 검토 명시 (코드 신설 X). (4) audit ⊥ 도메인 service. |

### 2-R. 결정 R — 왜 PyInstaller 검증을 중요하게 보는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-R** |
| 결정 내용 | **PyInstaller 53 hidden imports 동기화 + 53 tests 통과** 를 *분리 후 매 세션 끝에* 검증. 실제 `pyinstaller --noconfirm dosu_clinic.spec` 빌드 + exe smoke 는 **주요 리팩토링 묶음 완료 후** + 19-14 종료 게이트 + 사용자 명시 승인 시. |
| 결정 이유 | (1) 배포 환경 (Windows 단독 실행 PyInstaller onedir) 에서 import / hidden import 문제가 생길 수 있음. (2) 단위화 후 modules 폴더 분리가 늘어나면 빌드 누락 위험 증가. (3) `dosu_clinic.spec` 의 `hiddenimports` 누락 시 exe 실행 시점에 ImportError. (4) 53 tests 는 *빌드 없이도* 사전 검증 가능. (5) 빌드는 시간 소요 + 사용자 명시 승인 정책 ([CLAUDE.md](../../CLAUDE.md) 배포 규칙) — 매 세션 자동 ⊥. |
| 대안 | (1) PyInstaller 검증을 19-14 종료 게이트에서만 1회. (2) 매 세션 빌드 + exe smoke 자동 실행. (3) PyInstaller 사용 안 함 (Python 직접 실행). |
| 선택하지 않은 이유 | (1) 19-14 만 검증 = 중간 세션의 hidden imports 누락 시 19-14 까지 *발견 안 됨*. rollback 비용 폭증. (2) 매 세션 빌드 = 시간 소요 + 사용자 [CLAUDE.md](../../CLAUDE.md) 배포 규칙 ("빌드 + 배포할까요?" 라고 물어보기) 위반. (3) Python 직접 실행 = 운영 환경 (사용자 PC 단독 설치) 에서 Python 설치 / 의존성 / 환경 변수 모두 사용자 부담. |
| 기대 효과 | (1) 매 세션 hidden imports 누락 사전 검증 (53 tests). (2) 주요 리팩토링 묶음 (예: core + audit + settings 묶음) 완료 후 빌드 검증. (3) 19-14 종료 게이트에서 exe smoke (5 endpoint). (4) 사용자 명시 승인 시 빌드. |
| 위험 | R-OPS-04 (PyInstaller hidden imports). R-OPS-05 (실제 exe smoke). R-OPS-06 (requirements 변경). 53 tests 누락 시 빌드 실패. |
| 관련 문서 | [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §1 P-10 + §7-6, [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §2-6 (P-1~P-4), [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §3-14 (19-14), [19_refactor_risk_register.md](19_refactor_risk_register.md) §2-W R-OPS-04~06, [CLAUDE.md](../../CLAUDE.md) (배포 규칙). |
| 관련 테스트/하네스 | [test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) (53 tests). [test_migration_spec_discovery.py](../../tests/test_migration_spec_discovery.py). 실제 exe smoke (5 endpoint, 18-8 시점에 입증). |
| Codex 검증 포인트 | (1) 53 tests 가 매 세션 끝에 통과. (2) `dosu_clinic.spec` `hiddenimports` 의 modules 경로 동기화. (3) `collect_submodules` 실패 가드 / migrations 자동 글롭 / updater.bat post-build copy 정책 보존. (4) 매 세션 자동 빌드 ⊥ — 사용자 승인 시만. |

### 2-S. 결정 S — 왜 주석 / 문서화 기준을 포함하는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-S** |
| 결정 내용 | 향후 19-x 코드 이동 시 적용할 주석 카테고리 5종 + 1종 (TEMP) — **`# COMPAT:` (호환) / `# SAFETY:` (개인정보 / 운영 DB / 외부 API / API key) / `# NOTE:` (업무 규칙) / `# RISK:` (동시성 / TOCTOU / 외부 노드 / 마이그레이션) / `# TODO(19-x):` (후속 세션) / `# TEMP:` (임시 wrapper)**. 주석 작성으로 동작 변경 ⊥. |
| 결정 이유 | (1) 리팩토링 후 파일 / 함수 역할을 빠르게 이해하기 위함. (2) `COMPAT` / `SAFETY` / `RISK` / `NOTE` / `TODO` / `TEMP` 태그로 위험 지점을 명확히. (3) 모든 줄 주석이 아니라 *역할 / 경계 / 주의사항 중심*. (4) [CLAUDE.md](../../CLAUDE.md) "Don't add error handling, fallbacks, or validation for scenarios that can't happen" + "Default to writing no comments" — 의미 있는 주석만. (5) `TODO` 는 반드시 세션 번호 또는 제거 조건 포함. |
| 대안 | (1) 주석 카테고리 명시 안 하고 자유롭게 작성. (2) 모든 함수에 docstring 강제. (3) 주석을 별도 markdown 문서로 분리 (코드 주석 ⊥). |
| 선택하지 않은 이유 | (1) 자유 작성 = 일관성 깨짐 + Codex 검증 어려움. (2) 모든 docstring = [CLAUDE.md](../../CLAUDE.md) "Default to writing no comments" 위반. (3) 별도 markdown = 코드와 동기화 어려움 + 위험 지점 코드 검토 시 즉시 보이지 않음. |
| 기대 효과 | (1) 위험 지점 (`SAFETY` / `RISK`) 가 코드 검토 시 즉시 보임. (2) wrapper 제거 시점 (`TODO(19-x)` / `TEMP`) 추적 가능. (3) Codex 검증 시 5종 카테고리로 grep. (4) 후속 6개월 / 1년 후 재리팩토링 시 위험 지점 빠른 파악. |
| 위험 | (1) 주석 카테고리 미준수 시 ROI 저하. (2) `# TODO(...)` 무한 보유 시 코드 베이스 *중간 상태* — 19-P-9 체크리스트에서 정리. (3) 본 19-P-8 은 코드 미수정 — 카테고리 정의만, 실제 주석 작성 ⊥. |
| 관련 문서 | [19_refactor_module_map.md](19_refactor_module_map.md) §0-2 (주석 카테고리 5종 + TEMP), [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §4 (주석 / 문서화 기준), [19_refactor_risk_register.md](19_refactor_risk_register.md) §6-1 + §6-2 (Risk × 주석 매트릭스), [CLAUDE.md](../../CLAUDE.md) ("Default to writing no comments"). |
| 관련 테스트/하네스 | (직접 테스트 X — 주석은 동작 변경 0). Codex 검증 시 grep `# COMPAT:` / `# SAFETY:` / `# NOTE:` / `# RISK:` / `# TODO\(` / `# TEMP:` 결과 검토. |
| Codex 검증 포인트 | (1) 본 19-P-8 산출이 코드 주석 작성 ⊥ (코드 무수정). (2) 주석 카테고리 5종 + 1종 (TEMP) 정의 일관. (3) `TODO` 는 세션 번호 / 제거 조건 포함 의무. (4) 주석으로 동작 변경 ⊥. |

### 2-T. 결정 T — 왜 Codex 검증을 매 세션 게이트로 두는가

| 필드 | 값 |
|---|---|
| 결정 ID | **DEC-T** |
| 결정 내용 | **Claude Code 자체 테스트 통과 ≠ 최종 완료**. Codex 가 `latest_codex_review_request.md` 를 시작점으로 *실제 diff / 파일 / 결과 / 로그를 독립 확인* 한 후에만 다음 세션 진입. 매 세션 종료 시 [reports/refactor/{19-x,latest}_codex_review.md](../../reports/refactor/) 작성. |
| 결정 이유 | (1) Claude Code 자체 테스트만으로 놓칠 수 있는 *구조 / 범위 / 응답 키* 문제를 잡기 위함. (2) 변경 범위 초과 / 테스트 약화 / API 응답 키 변경 위험을 방지. (3) 검증 기록을 `reports/refactor/` 에 영구 보존. (4) 18-AI 시리즈 (18-0~18-8) 9세션 모두 Codex 검증을 통과한 패턴 유지. (5) 19-P-1 ~ 19-P-7 모두 Codex 검증을 거쳐 caveat 정리 — 같은 패턴을 19-x 코드 세션에도 적용. |
| 대안 | (1) Claude Code 자체 테스트 통과만으로 다음 세션 진입. (2) Codex 검증을 19-14 종료 게이트에서만 1회. (3) 사용자 직접 PR 리뷰만으로 게이트. |
| 선택하지 않은 이유 | (1) 자체 테스트만 = 18-1 / 18-2 / 18-5 등에서 Codex 가 발견한 caveat (taxonomy 메타 / API 키 마스킹 / hidden imports 누락 / 응답 키 변경 등) 가 *그대로 남음*. (2) 19-14 만 = 중간 세션 회귀가 종료 게이트까지 누적 — rollback 비용 폭증. (3) 사용자 직접 = 사용자 부담 폭증 + 시간 소요. |
| 기대 효과 | (1) 매 세션 끝에 *독립 검증* 완료. (2) 변경 범위 초과 / 테스트 약화 / 응답 키 변경 즉시 발견. (3) 영구 보존본 (`{19-x}_codex_review.md`) 으로 6개월 / 1년 후에도 결정 근거 추적 가능. (4) Codex 가 *Claude Code 요약만 믿지 않고* 실제 파일 / diff 검증. |
| 위험 | (1) Codex 검증 실패 시 다음 세션 진입 차단 — 19-14 까지 도달 못할 가능성. (2) Codex 가 신규 caveat 를 자주 제기하면 진행 속도 저하. (3) 본 19-P-8 도 Codex 검증 게이트 — fail 시 19-P-9 진입 ⊥. |
| 관련 문서 | [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §4, [docs/ai_code_session_protocol.md](../ai_code_session_protocol.md) §4 + §7 + §8, [docs/ai_codex_review_protocol.md](../ai_codex_review_protocol.md), [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §0 (각 세션 r* Codex 판정 이력), [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §1 R-10. |
| 관련 테스트/하네스 | (Codex 게이트는 테스트 결과를 검증) — Claude Code 자체 테스트 (run_check.bat / pytest tests -v / 6 AI 하네스 / 53 hidden imports / S-1~S-5 운영 DB 보호 / `_block_sdk_modules`) 결과를 Codex 가 독립 확인. |
| Codex 검증 포인트 | (1) `latest_codex_review_request.md` 작성. (2) 매 세션 종료 시 영구 보존본 (`{19-x}_codex_review.md`) 작성. (3) Codex 가 Claude Code 요약만 믿지 않고 실제 파일 검증. (4) 검증 결과 fail / pass / pass with caveat 명확. |

---

## 3. 선택하지 않은 대안

> 사용자 §3 명시 8개 대안 + 본 19-P-8 추가 명시.

### 3-1. 전체 app 구조를 한 번에 대규모 이동

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) `api.py` 5127줄 + `main.html` 7331줄 + JS 6800줄 동시 이동 시 코드 diff 가 검토 불가능. (2) Codex / 사용자 PR 리뷰 불가. (3) 회귀 발생 시 *어디 책임* 인지 추적 불가 — rollback = 전체 분리 무효. (4) 5회 루프 정책 적용 불가. (5) DEC-B (단위화 분할) 와 정면 충돌. |
| 후속 검토 가능성 | **없음**. 단위화는 *반드시* 분할 진행 (DEC-B). |

### 3-2. 새 DB schema 를 먼저 대규모 정리

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) 운영 DB (사용자별 다른 상태) 마이그레이션 실패 위험. (2) 구조 리팩토링과 schema 변경을 *섞으면* 회귀 추적 어려움. (3) DEC-D (DB 보존) 위반. (4) m001~m013 diff 0 정책 위반. (5) sync `ENTITY_MAP` 외부 노드 호환 영향. |
| 후속 검토 가능성 | **있음** — 19-P 종료 후 별도 세션. 노쇼 컬럼 / `Patient.doctor_id` / `Doctor` 별도 테이블 / `DoctorSchedule` / `Order` / `Prescription` 등은 m014+ 마이그레이션 + 응답 키 추가 + UI 변경 동반. |

### 3-3. 프론트 UI 까지 동시에 리팩토링

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) [main.html](../../app/templates/main.html) 7331줄 + 인라인 JS 6800줄 + [app.css](../../app/static/css/app.css) 3626줄 = 백엔드 86 endpoint 와 동시 이동 시 회귀 폭증. (2) UI 자동 검증 부재 — 분리 후 사용자 수동 smoke 만 가능. (3) DEC-C (응답 키 보존) 위반 가능성. (4) [CLAUDE.md](../../CLAUDE.md) "기능 수정과 디자인 수정을 한 번에 섞지 않는다" 위반. |
| 후속 검토 가능성 | **있음** — 19-P 종료 후 별도 UI 분리 세션. main.html JS 외부 분리 / FullCalendar view-model / Alpine 컴포넌트 분리는 19-P 비-목표 (P-3 / R-5). |

### 3-4. appointments 를 첫 번째로 크게 분리

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) appointments 의 의존 도메인 (patients / staff / treatments / leaves / availability / completion_rules) 이 *원래 위치* (api.py) 에 있어 wrapping 폭증. (2) `_serialize_appointment` / `_check_lunch_block` / `_bump_patient_count` / `_check_version` 등 헬퍼가 도메인 분리 안 된 상태에서 modules/appointments 로 이동 시 의존 추적 어려움. (3) DEC-F (마지막 분리) 정책 위반. (4) 19-P-7 R-APPT-01 ~ 07 치명 위험 8개 중 2개가 첫 분리 시 발생 가능. |
| 후속 검토 가능성 | **없음**. appointments 는 *반드시* 의존 도메인 분리 후 (19-9). |

### 3-5. AI/RAG 를 외부 LLM 중심으로 재설계

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) 외부 LLM 토큰 비용 폭증. (2) PII 외부 전송 위험 (R-PAT-01 / R-AI-07). (3) API key 누출 가능성. (4) 할루시네이션 위험 (sources 없이 LLM 답변 시). (5) [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §2 local-first 절대 원칙 위반. (6) 18-AI 시리즈 9세션 빌드한 RAG / Knowledge / Vector 패키지 폐기. |
| 후속 검토 가능성 | **없음**. local-first 는 *절대 원칙* (DEC-N). |

### 3-6. 기존 API 응답 key 를 새 구조에 맞춰 변경

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) main.html 7331줄 + 인라인 JS 6800줄 동시 수정 필수. (2) FullCalendar event ID / version / status / treatment_codes 필드 의존. (3) 외부 sync 노드 `ENTITY_MAP` 9개 키 외부 호환 깨짐. (4) DEC-C (응답 키 보존) 정면 위반. (5) 단위화 ≠ 단위화 (= 기능 변경). |
| 후속 검토 가능성 | **있음** — 19-P 종료 후 *별도 v2 API* 도입 시 (예: `/api/v2/...`). 단, 기존 `/api/...` 와 병행 보존 정책 필요. |

### 3-7. 테스트 없이 파일 이동부터 진행

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) 응답 키 변경 / 헬퍼 누락 / 의존성 깨짐 *발견 못함*. (2) [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §3 5회 루프 정책 위반. (3) DEC-C 응답 키 보존 검증 불가. (4) 86 endpoint contract 부재 (19-P-1 §22 C-1) 상태에서 분리 = 회귀 검증 불가. (5) [docs/ai_code_session_protocol.md](../ai_code_session_protocol.md) §4 14단계 절차 위반. |
| 후속 검토 가능성 | **없음**. 테스트 우선 (T-7 / R-7). 분리 *직전* contract 테스트 신규 추가 후 분리 (19-P-5 §4 보강 9개). |

### 3-8. Codex 검증 없이 다음 단계로 진행

| 필드 | 값 |
|---|---|
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) Claude Code 자체 테스트만으로 놓칠 수 있는 구조 / 범위 / 응답 키 문제 누적. (2) 변경 범위 초과 / 테스트 약화 발견 어려움. (3) DEC-T (Codex 게이트) 정면 위반. (4) [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §4 위반. (5) 영구 보존본 부재 → 6개월 / 1년 후 결정 근거 추적 불가. |
| 후속 검토 가능성 | **없음**. Codex 게이트는 *필수* (DEC-T). |

### 3-9. 본 19-P-8 추가 — 단위화 비활성 / 보류

| 필드 | 값 |
|---|---|
| 결정 | **미선택** — 단위화는 진행. 단, 19-x 코드 세션 사이에 사용자가 보류 결정 시 19-P-7 위험 등록 + 19-P-8 의사결정 기록을 baseline 으로 삼아 *재개 가능*. |
| 위험 / 왜 본 리팩토링 목표와 맞지 않는지 | (1) `api.py` 5127줄 / 86 endpoint 도메인 혼재 상태 그대로 v1.4.0 기능 추가 시 회귀 위험 폭증 (DEC-A). (2) 18-AI baseline (529 passed) 안정 시점 활용 못함. (3) doctors / EMR / 노쇼 등 후속 기능 도입 시 도메인 경계 부재로 비용 증가. |
| 후속 검토 가능성 | **있음** — 사용자가 v1.x 기능 추가를 우선하기로 결정 시 19-P-8 시점에 보류. 단, 19-P-1 ~ 19-P-7 산출물은 그대로 유지 (재개 시 baseline). |

---

## 4. 결정과 위험 등록 연결

> [19_refactor_risk_register.md](19_refactor_risk_register.md) 의 위험 항목 (77 Risk ID) 과 본 의사결정 항목 매핑.

| 결정 ID | 결정 요지 | 연결된 Risk ID | 위험 완화 효과 |
|---|---|---|---|
| DEC-A | 단위화 = 구조 안정화 | R-CORE-01~05 / R-OPS-04~06 | 도메인 혼재 회귀 위험 일괄 완화 |
| DEC-B | 세션 1개 = 모듈 1개 | R-CORE-01 (router→service→repository) | 대규모 이동 회귀 위험 완화 + rollback 단위 명확화 |
| DEC-C | API URL / 응답 키 보존 | R-APPT-01 / R-PAT-02 / R-STAT-01-02 / R-SMS-01-02 / R-ADM-* / R-AUDIT-01 / R-EXIM-01-02 / R-CORE-04-05 | UI / sync / 외부 호환 깨짐 위험 완화 |
| DEC-D | DB schema 최소 변경 (m001~m013 diff 0) | R-BAK-01~05 / R-OPS-01~03 | 운영 DB 손상 + 마이그레이션 실패 + sync 키 변경 위험 완화 |
| DEC-E | router/service/repository/rules/schemas | R-CORE-01~03 | 책임 혼재 + 순환참조 위험 완화 |
| DEC-F | appointments 마지막 분리 (19-9) | R-APPT-01~07 / R-LOCK-01~03 | 의존 도메인 분리 후 진입 — 응답 키 / 중복 / 휴무 / 점심창 / 락 / TOCTOU 위험 완화 |
| DEC-G | availability 별도 책임 (19-4) | R-APPT-02 (도수 중복) / R-APPT-03 (휴무 차단) / R-APPT-04 (12:00 기준) / R-APPT-05 (점심창) / R-APPT-06 (devtools 우회) | 단일 진실원천 + 백엔드 차단 보강 — xfail 8건 정방향 전환 |
| DEC-H | leaves 별도 모듈 (19-5) | R-LEAVE-01~04 / R-APPT-03 (휴무 차단) | _upsert_employee_leave_core 단일 진실원천 + 종일/반차/연월차 정책 분리 |
| DEC-I | treatments / completion_rules (19-6) | R-TX-01~04 (manual60 / 완료체크 / count_increment / done_count) | manual60=1 보존 + done_count 음수 방지 + approve/revert 흐름 분리 |
| DEC-J | stats read-only (19-11) | R-STAT-01~05 / R-EXIM-01-02 | 8 endpoint contract + ManualCount UNIQUE + read-only 책임 분리 |
| DEC-K | sms 분리 (19-10) | R-SMS-01~05 (대상 / 템플릿 / 계정 / 외부 발송 / 자동 트리거) / R-OPS-03 | 외부 발송 자동 트리거 ⊥ + munjanara 마스킹 + provider 외부 경계 |
| DEC-L | patients / notes (19-7) | R-PAT-01~05 / R-EXIM-01-02 | PII 보호 + 검색 / 메모 / 중복 검사 + data-convert 동시 분리 |
| DEC-M | staff 통합 (doctor + therapist) (19-8) | R-THER-01~03 / R-DOC-01~02 / R-32~R-35 후속 | Employee 단일 테이블 정합 + 부재 항목 단정 ⊥ |
| DEC-N | AI/RAG local-first 보존 (19-13) | R-AI-01~07 / R-LOCK-02~03 / R-PAT-01 / R-AUDIT-02 | 외부 API 호출 0 + PII 외부 전송 ⊥ + 할루시네이션 방지 |
| DEC-O | AI commands DB 변경 조심 (19-13) | R-AI-01~07 / R-LEAVE-01 (단일 진실원천) | HMAC + TOCTOU + leaves.service 우회 ⊥ + 도메인 임의 생성 ⊥ |
| DEC-P | health / settings / feature_flags (19-2) | R-ADM-01~05 / R-HEALTH-01 (post-19-P) | API key 원문 노출 ⊥ + ai_mode 단일 진입점 |
| DEC-Q | audit / logs 후속 검토 (19-12) | R-AUDIT-01~02 / R-PAT-01 / R-AI-07 | audit 단일 진입점 + PII 마스킹 + 보존 정책 후속 |
| DEC-R | PyInstaller 검증 (매 세션 53 tests + 19-14 빌드) | R-OPS-04~06 | hidden imports 누락 + exe smoke + requirements 변경 위험 완화 |
| DEC-S | 주석 카테고리 (COMPAT/SAFETY/NOTE/RISK/TODO/TEMP) | (직접 Risk ID 매핑 X — 모든 Risk 의 *위험 지점 표시* 책임) | 위험 지점 코드 검토 시 즉시 보임 + wrapper 제거 시점 추적 |
| DEC-T | Codex 게이트 매 세션 | (직접 Risk ID 매핑 X — 모든 Risk 의 *독립 검증* 책임) | Claude Code 자체 테스트 누락 발견 + 영구 보존본 |

### 4-1. 사용자 §4 요청 예시 정합

| 사용자 §4 예시 | 본 문서 매핑 |
|---|---|
| appointments 를 후반에 분리 → 예약 API 응답 key 변경 위험, 예약 중복 검사 누락 위험 완화 | DEC-F (appointments 19-9) → R-APPT-01 / R-APPT-02 |
| availability 를 먼저 분리 → 휴무 차단 / 반차 기준 누락 위험 완화 | DEC-G (availability 19-4) → R-APPT-03 / R-APPT-04 / R-APPT-05 / R-APPT-06 |
| sms 를 분리 → 문자 대상 추출 오류 / 외부 발송 위험 완화 | DEC-K (sms 19-10) → R-SMS-01 / R-SMS-04 |
| local-first 유지 → 외부 API 호출 / 개인정보 / 환각 위험 완화 | DEC-N (local-first 19-13) → R-AI-01 / R-AI-06 / R-AI-07 |

---

## 5. 결정과 테스트 전략 연결

> [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §3 + §4 보강 9개 항목과 본 의사결정 매핑.

| 결정 ID | 결정 요지 | 필요한 테스트 (19-P-5 § 매핑) |
|---|---|---|
| DEC-C | API 응답 key 유지 | API contract 테스트 — manual_qa contract (`test_ai_manual_rag_contract.py`) + health (`test_ai_health_public.py`, `test_ai_health_status.py`) — **있음**. 비-AI 86 endpoint contract — **부재 (19-P-1 §22 C-1) → 분리 직전 보강 9개 필수**. |
| DEC-D | DB schema 최소 변경 | [scripts/check_db_path.py](../../scripts/check_db_path.py), [tests/conftest.py](../../tests/conftest.py) 4단계 격리, [tests/harness/db_guard.py](../../tests/harness/db_guard.py) `assert_safe_db_path()`, [test_migration_spec_discovery.py](../../tests/test_migration_spec_discovery.py). |
| DEC-G | availability 분리 (휴무 / 반차 / 점심창 / 충돌) | [test_appointment_rules.py](../../tests/test_appointment_rules.py) xfail 3건 + skip 1건 → 정방향 전환 (19-4). [test_therapist_leave.py](../../tests/test_therapist_leave.py) xfail 4건 → 정방향 전환 (19-5). 점심창 / PUT / DELETE / 409 contract — 19-4 / 19-9 분리 직전 신규. |
| DEC-H | 휴무 분리 | [test_therapist_leave.py](../../tests/test_therapist_leave.py) xfail 4건 정방향 전환 + 반차 허용 회귀 보존. [test_employee_leave_unique_violation.py](../../tests/test_employee_leave_unique_violation.py) (m011 UNIQUE). [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) (parse / preview / execute + HMAC + TOCTOU + `_upsert_employee_leave_core` 호출 회귀). |
| DEC-I | 완료체크 분리 (manual60=1) | [test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py). [test_stats_counts.py](../../tests/test_stats_counts.py). approve / revert / done_count 0 미만 방지 — 19-6 분리 직전 신규. |
| DEC-J | 통계 분리 (read-only) | [test_stats_counts.py](../../tests/test_stats_counts.py). 8 endpoint 응답 키 contract — 19-11 분리 직전 신규. ManualCount UNIQUE (m006). |
| DEC-K | SMS 분리 | [test_sms_validation.py](../../tests/test_sms_validation.py), [test_ai_sms_validate.py](../../tests/test_ai_sms_validate.py), [test_ai_sms_draft.py](../../tests/test_ai_sms_draft.py), [test_ai_sms_draft_hallucination.py](../../tests/test_ai_sms_draft_hallucination.py). 외부 HTTP mock — 19-10 분리 직전 신규. |
| DEC-L | 환자 / 메모 분리 | 환자 CRUD / 검색 / 메모 / counts dict 응답 contract — 19-7 분리 직전 신규. PII 비노출 회귀 ([test_ai_logging.py](../../tests/test_ai_logging.py), [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py)). |
| DEC-M | staff 통합 | [test_employee_*.py](../../tests/) (4 파일) + [test_employee_can_manual_contract.py](../../tests/test_employee_can_manual_contract.py) + [test_employee_hire_date.py](../../tests/test_employee_hire_date.py) + [test_employee_leave_unique_violation.py](../../tests/test_employee_leave_unique_violation.py). assignment role=doctor 강제 회귀 — 19-8 분리 직전 신규. |
| DEC-N | AI local-first 유지 | AI 하네스 6개 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid). [test_ai_assist_mode.py](../../tests/test_ai_assist_mode.py) + [test_local_only_mode.py](../../tests/test_local_only_mode.py). [test_ai_hallucination.py](../../tests/test_ai_hallucination.py). [test_ai_logging.py](../../tests/test_ai_logging.py). [tests/conftest.py](../../tests/conftest.py) `_block_sdk_modules`. |
| DEC-O | AI commands DB 변경 조심 | [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) (parse / preview / execute + HMAC + TOCTOU + leaves.service 호출 회귀). [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py). |
| DEC-P | health / settings / feature_flags | [test_admin_auth_required.py](../../tests/test_admin_auth_required.py). [test_admin_ui_smoke.py](../../tests/test_admin_ui_smoke.py). [test_ai_assist_mode.py](../../tests/test_ai_assist_mode.py) + [test_local_only_mode.py](../../tests/test_local_only_mode.py) (feature_flags 파생 회귀). |
| DEC-R | PyInstaller 매 세션 53 tests + 19-14 빌드 | [test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) (53 tests). [test_migration_spec_discovery.py](../../tests/test_migration_spec_discovery.py). 19-14 종료 게이트 + 사용자 명시 승인 시 실제 exe smoke (5 endpoint). |
| DEC-T | Codex 게이트 매 세션 | (Codex 가 Claude Code 자체 테스트 결과를 독립 검증) — `run_check.bat` / `pytest tests -v` / 6 AI 하네스 / 53 hidden imports / S-1~S-5 / `_block_sdk_modules` 결과 grep + diff + 카운트 검증. |

### 5-1. 사용자 §5 요청 예시 정합

| 사용자 §5 예시 | 본 문서 매핑 |
|---|---|
| API 응답 key 유지 결정 → API contract 테스트 | DEC-C → 비-AI 86 endpoint contract 부재 (C-1) — 분리 직전 보강 9개 필수 |
| 휴무 분리 결정 → 휴무 차단 테스트 | DEC-H → [test_therapist_leave.py](../../tests/test_therapist_leave.py) xfail 4건 정방향 전환 |
| 완료체크 분리 결정 → 치료항목별 완료체크 테스트 | DEC-I → approve / revert / done_count 0 미만 방지 — 19-6 분리 직전 신규 |
| SMS 분리 결정 → 문자 대상 추출 테스트 | DEC-K → 외부 HTTP mock + tomorrow-targets 응답 contract — 19-10 분리 직전 신규 |
| AI local-first 유지 결정 → RAG/Safety/Vector/Hybrid 하네스 | DEC-N → AI 하네스 6개 + `_block_sdk_modules` |
| PyInstaller 중요 결정 → 주요 리팩토링 후 빌드 테스트 | DEC-R → 53 hidden imports tests 매 세션 + 19-14 빌드 + 사용자 승인 시 |

---

## 6. 결정과 주석 / 문서화 연결

> 각 결정에 필요한 주석 카테고리 (DEC-S 정의) 표시. 본 19-P-8 은 코드 미수정 — 실제 주석 작성 ⊥, *향후 코드 이동 시 주석이 필요한 결정* 만 표시.

### 6-1. 결정 × 주석 카테고리 매트릭스

| 결정 ID | COMPAT | SAFETY | NOTE | RISK | TODO | TEMP |
|---|---|---|---|---|---|---|
| DEC-A 단위화 | — | — | — | — | TODO(post-19-P) UI 분리 후속 | — |
| DEC-B 세션 1개 = 모듈 1개 | — | — | — | — | TODO(19-x) wrapper 제거 시점 | TEMP wrapper 보유 기간 |
| DEC-C API URL / 응답 키 보존 | **COMPAT** 응답 dict 빌더 / version 필드 / 비-AI alias (`therapist_id` 이중 키) / sync `ENTITY_MAP` 9개 키 | — | — | — | — | — |
| DEC-D DB schema 최소 변경 | — | **SAFETY** 운영 DB 미접근 / m001~m013 diff 0 | — | RISK 마이그레이션 의존 (m014+ 도입 시) | TODO(post-19-P) m014+ 별도 세션 | — |
| DEC-E router/service/repository | — | — | NOTE 책임 분리 정책 | — | — | — |
| DEC-F appointments 마지막 분리 | COMPAT 응답 키 + version 필드 | — | NOTE 점심창 / 충돌 / 휴무 차단 정책 | RISK 낙관적 락 TOCTOU / devtools 우회 | TODO(19-9) wrapper 제거 시점 | — |
| DEC-G availability 별도 책임 | — | — | NOTE `leave_type=am/pm` 12:00 기준 / 점심창 정책 | RISK devtools 우회 — 백엔드 검증 필수 | TODO(19-4) xfail 8건 정방향 전환 | — |
| DEC-H leaves 별도 모듈 | COMPAT `_upsert_employee_leave_core` 시그니처 / sync `ENTITY_MAP[employee_leave]` | — | NOTE 휴무 차단 spec 02 / 종일·반차·연월차 분기 | RISK devtools 우회 / AI 우회 ⊥ | TODO(19-5) xfail 4건 정방향 전환 | — |
| DEC-I treatments / completion_rules | COMPAT count_increment dict | — | NOTE manual60=1 정책 ([CLAUDE.md](../../CLAUDE.md)) / 시간 가중치 ⊥ | — | — | — |
| DEC-J stats read-only | COMPAT 8 endpoint 응답 키 | — | NOTE read-only 정책 (D-7) | — | — | — |
| DEC-K sms 분리 | COMPAT munjanara_key 마스킹 / 응답 디코딩 / 전화번호 마스킹 | **SAFETY** 외부 API 차단 / 자동 발송 트리거 ⊥ | NOTE 자동 트리거 ⊥ 정책 (D-8) | — | — | — |
| DEC-L patients / notes | COMPAT counts dict 키 | **SAFETY** PII 비노출 (응답 / 로그 / audit) | NOTE 중복 검사 정책 / 메모 경계 | — | TODO(post-19-P) `modules/notes/` 통합 | — |
| DEC-M staff 통합 | COMPAT therapist alias 이중 키 | — | NOTE Employee role 분기 정책 / 의사 시드 자동 활성화 ⊥ | — | TODO(post-19-P) `modules/doctors/` EMR 도입 시 | — |
| DEC-N AI/RAG local-first | — | **SAFETY** 외부 API 차단 / API key 마스킹 / PII 외부 전송 ⊥ | NOTE local-first 절대 원칙 ([docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §2) | RISK provider 호출 0 보장 (sources / low_confidence / PII / unknown_feature) | — | — |
| DEC-O AI commands DB 변경 조심 | — | **SAFETY** AI commands → 도메인 service 호출만 / DB 임의 생성 ⊥ | NOTE leaves.service 단일 진실원천 / HMAC 토큰 정책 | RISK TOCTOU / 토큰 위변조 | TODO(post-19-P) AI 의사 가드 (M-36) | — |
| DEC-P health / settings / feature_flags | COMPAT system-settings 응답 키 / `api_key_set` boolean | **SAFETY** API key 원문 응답 / 로그 부재 | NOTE ai_mode (local_only/local_first/ai_assist) 단일 진입점 (T-8) | — | TODO(post-19-P) `/api/health` 신설 (M-28) | — |
| DEC-Q audit / logs | — | **SAFETY** PII 원문 audit_log / AiUsageLog 부재 | NOTE audit() 시그니처 보존 / 단방향 (D-9) | — | TODO(post-19-P) 보존 정책 / 자동 삭제 | — |
| DEC-R PyInstaller 검증 | — | — | NOTE 53 hidden imports 매 세션 갱신 / 빌드는 사용자 승인 시 | RISK exe 실행 시점 ImportError | TODO(19-14) 종료 게이트 빌드 + exe smoke | — |
| DEC-S 주석 / 문서화 기준 | — | — | NOTE 주석 카테고리 5종 + TEMP 1종 | — | — | — |
| DEC-T Codex 게이트 매 세션 | — | — | NOTE [docs/ai_codex_review_protocol.md](../ai_codex_review_protocol.md) 정합 | — | — | — |

### 6-2. 향후 코드 이동 시 주석이 필요한 결정 지점 (요약)

> 본 19-P-8 은 코드 미수정 — 아래는 *19-x 코드 세션이 적용할 위치 목록*.

| 위치 | 주석 태그 | 근거 결정 |
|---|---|---|
| `app/core/config.py` (이동 후) `get_db_path` | `# SAFETY:` 운영 DB 경로 차단 | DEC-D / DEC-A |
| `app/core/security.py` (이동 후) `verify_password` / 세션 토큰 / 5회 잠금 | `# SAFETY:` PBKDF2 + 세션 + 잠금 | DEC-A / DEC-P |
| `app/modules/appointments/service.py` `_serialize_appointment` 응답 dict 빌더 | `# COMPAT:` 응답 키 + version 필드 | DEC-C / DEC-F |
| `app/modules/appointments/availability.py` `_check_lunch_block` / 충돌 / 휴무 차단 | `# NOTE:` 점심창 / `# RISK:` devtools 우회 | DEC-G |
| `app/modules/leaves/service.py` `_upsert_employee_leave_core` | `# COMPAT:` 시그니처 보존 / `# NOTE:` 단일 진실원천 | DEC-H |
| `app/modules/treatments/completion_rules.py` `count_increment` 정책 | `# NOTE:` manual60=1 ([CLAUDE.md](../../CLAUDE.md)) | DEC-I |
| `app/modules/stats/repository.py` 8 endpoint 집계 | `# COMPAT:` 응답 키 / `# NOTE:` read-only | DEC-J |
| `app/modules/sms/provider.py` munjanara API client | `# COMPAT:` 응답 디코딩 / `# SAFETY:` 외부 API 차단 / `# NOTE:` 자동 트리거 ⊥ | DEC-K |
| `app/modules/patients/notes_service.py` 환자 메모 | `# SAFETY:` PII 비노출 / `# NOTE:` 메모 경계 | DEC-L |
| `app/modules/staff/doctors_service.py` `_doctor_codes_set` / `is_doctor_filter` | `# NOTE:` Employee role 분기 / `# TODO(post-19-P):` `modules/doctors/` 후속 | DEC-M |
| `app/modules/ai/router.py` provider 호출 게이트 | `# SAFETY:` local-first / `# NOTE:` should_call_llm 다층 게이트 | DEC-N |
| `app/modules/ai/commands/action_leave.py` parse / preview / execute | `# SAFETY:` AI → 도메인 write 제한 / `# NOTE:` HMAC 토큰 / `# RISK:` TOCTOU | DEC-O |
| `app/modules/settings/service.py` AiSetting / SystemSetting | `# COMPAT:` 응답 키 / `# SAFETY:` API key 원문 부재 | DEC-P |
| `app/modules/audit/service.py` audit() | `# SAFETY:` PII 원문 부재 / `# NOTE:` 시그니처 보존 / `# TODO(post-19-P):` 보존 정책 | DEC-Q |
| `dosu_clinic.spec` `hiddenimports` 매 분리 후 갱신 | `# NOTE:` modules 경로 동기화 / `# TODO(19-14):` exe smoke | DEC-R |
| 임시 wrapper (각 분리 단계) | `# TEMP:` wrapper 보유 기간 + `# TODO(19-x):` 제거 시점 | DEC-B |

---

## 7. 변경 가능성 / 재검토 기준

> 아래 상황에서는 **본 의사결정을 재검토** 한다 (`docs/refactor/19_refactor_decision_record.md` 의 결정 ID 단위로 보정 또는 폐기).

| # | 재검토 트리거 | 영향 결정 | 재검토 절차 |
|---|---|---|---|
| 1 | **Codex 가 구조상 치명적 문제를 발견** | DEC-A / DEC-B / DEC-E / DEC-F | (a) 영향 결정 ID 보정. (b) 19-P-7 위험 등록에 새 Risk ID 추가. (c) 19-P-9 체크리스트 갱신. (d) Codex 재검증. |
| 2 | **테스트 보강 없이 진행하기 어렵다고 판단** | DEC-C / DEC-G / DEC-H / DEC-I / DEC-J / DEC-K / DEC-L | (a) 19-P-5 §4 보강 9개 항목 외에 신규 보강 항목 추가. (b) 분리 직전 contract 테스트 신규 추가 우선. (c) 5회 루프 정책 재적용. |
| 3 | **기존 API 응답 key 유지가 불가능** | DEC-C | (a) 사용자 결정 필수 — 응답 키 변경 필연성 검증 ([19_refactor_target_architecture.md §1 P-2](19_refactor_target_architecture.md) 위반 가능 여부). (b) main.html / 외부 sync 노드 영향 분석. (c) 별도 v2 API 도입 검토. |
| 4 | **DB schema 변경이 필수로 드러남** | DEC-D | (a) 사용자 결정 필수 — 운영 DB 손상 위험 사전 통보. (b) m014+ 별도 세션 분리 (단위화 안에서 동시 ⊥). (c) 백업 / 복원 / 마이그레이션 실패 시나리오 사전 검증 (R-BAK-01~05). |
| 5 | **PyInstaller 빌드가 반복적으로 실패** | DEC-R / DEC-A | (a) 53 hidden imports tests 통과해도 실제 exe 가 실행 안 되는 시나리오 발견 시. (b) `dosu_clinic.spec` `collect_submodules` / migrations 자동 글롭 정책 검토. (c) 사용자 승인 후 실제 빌드 + exe smoke. |
| 6 | **리팩토링 대상 모듈의 실제 현재 구조가 문서와 다르게 확인** | DEC-A ~ DEC-T (전부) | (a) 19-P-1 [현재 구조](19_refactor_current_state.md) 갱신. (b) 19-P-2 ~ 19-P-7 영향 부분 보정. (c) 19-P-9 체크리스트 갱신. (d) 사용자 통보. |
| 7 (추가) | **사용자가 단위화 보류 결정** | DEC-A 보류 | 19-P-1 ~ 19-P-7 산출물 그대로 유지 (재개 시 baseline). 19-x 코드 세션 진입 ⊥. v1.x 기능 추가 우선. |
| 8 (추가) | **AI/RAG local-first 정책 변경 필요** (외부 LLM 중심 도입 결정 시) | DEC-N / DEC-O | (a) [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) §2 절대 원칙 보정. (b) AI 하네스 6개 회귀 검증. (c) PII 외부 전송 정책 재정의. (d) 별도 ADR. |
| 9 (추가) | **doctors / EMR 연동 도입 결정** | DEC-M / DEC-D / R-DOC-01~02 / R-32~R-35 | (a) m014+ 별도 세션 — Doctor / Department / Room / DoctorSchedule / Order / Prescription 신설. (b) `modules/doctors/` 신설 (post-19-P, M-31). (c) Patient.doctor_id 추가 + 응답 키 + UI 변경 동반. (d) 별도 ADR + 보안 검토. |
| 10 (추가) | **5회 루프 실패가 같은 도메인에서 반복** | DEC-B / DEC-F | (a) 영향 도메인 분리 *순서 변경* 검토. (b) wrapper 패턴 재설계. (c) 사용자 결정 필수 — 해당 도메인 분리 보류. |

### 7-1. 사용자 §7 요청 예시 정합

본 §7 표는 사용자 §7 명시 6개 + 본 19-P-8 추가 4개 (총 10개) 트리거를 모두 포함.

---

## 8. 종합

- 본 19-P-8 = 19-P-1 ~ 19-P-7 (구조 계획 7개 문서) 의 *의사결정 근거* 정리. 단위화 = 구조 안정화 (DEC-A) / 세션 1개 = 모듈 1개 (DEC-B) / API URL + 응답 키 보존 (DEC-C) / DB schema 최소 변경 (DEC-D) / router/service/repository (DEC-E) / appointments 마지막 (DEC-F) / availability + leaves + treatments + completion_rules + stats + sms + patients + staff 분리 (DEC-G ~ DEC-M) / AI/RAG local-first (DEC-N) / AI commands DB 조심 (DEC-O) / health + settings + feature_flags (DEC-P) / audit 후속 (DEC-Q) / PyInstaller 매 세션 (DEC-R) / 주석 카테고리 (DEC-S) / Codex 게이트 매 세션 (DEC-T) — **20개 결정 ID**.
- 선택하지 않은 대안 8개 (사용자 §3) + 추가 1개 (3-9 단위화 보류) — 9개 모두 위험 / 후속 검토 가능성 명시.
- 위험 등록 매핑 (§4) — 결정 20개 → Risk ID 77개 매핑. 사용자 §4 4가지 예시 모두 정합.
- 테스트 전략 매핑 (§5) — 결정 14개 → 19-P-5 §3 + §4 보강 9개 항목 매핑. 사용자 §5 6가지 예시 모두 정합.
- 주석 / 문서화 매트릭스 (§6) — 결정 × 6 주석 카테고리 (COMPAT/SAFETY/NOTE/RISK/TODO/TEMP) 매트릭스. 향후 코드 이동 시 주석이 필요한 위치 16개 (§6-2).
- 재검토 기준 (§7) — 사용자 §7 명시 6개 + 본 추가 4개 = 10개 트리거.
- 본 19-P-8 산출 = `docs/refactor/19_refactor_decision_record.md` (본 문서) + `reports/refactor/{19-P-8,latest}_codex_review_request.md` (3개 신규 문서). 코드 / 테스트 / spec / UI / migrations / requirements 무수정.
- 다음 세션: **19-P-9 공통 체크리스트 문서** (`docs/refactor/19_refactor_common_checklist.md` 후보) — 19-x 코드 세션이 매 세션 적용할 *체크리스트* 정리. Codex 검증 통과 후 진입.
