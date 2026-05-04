# 19-P-6 단위화 리팩토링 — 롤아웃 계획 (19_refactor_rollout_plan, r2 보정본)

> 19-P-1 [현재 구조](19_refactor_current_state.md), 19-P-2 [목표 아키텍처](19_refactor_target_architecture.md),
> 19-P-3 [모듈 매핑](19_refactor_module_map.md), 19-P-4 [의존성 맵](19_refactor_dependency_map.md),
> 19-P-5 [테스트 전략](19_refactor_test_strategy.md) 의 후속 문서.
> 단위화 리팩토링을 실제 코드 세션으로 진행하기 전에, **어떤 순서로 어떤 범위를 나누어 진행할지** 롤아웃 계획을 문서화한다.
> 본 문서는 *순서/일정* 문서 — 실제 코드 이동은 19-0 이후 별도 세션.

## 0. 메타

- 작성일: 2026-05-02
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-6 진입 가능)** ([reports/refactor/19-P-5_codex_review.md](../../reports/refactor/19-P-5_codex_review.md))
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *순서/일정* 문서 — 실제 폴더 / 파일 / 테스트 미생성.
- **r1 Codex 검증 (2026-05-02 pass with caveat — yes 진입 가능)** 후 본 r2 보정 — 보정 이력:
  - **r2 보정** (Codex r1 caveat 2개):
    - (1) "추천 순서 14단계" 표현을 **"19-1 ~ 19-14 = 14개 리팩토링 세션 + 19-0 기준 테스트 baseline = 합계 15개 실행 세션 (+ 19-P 구조 계획)"** 으로 정정 (§2-1 머리말 / §10 종합).
    - (2) §0 메타의 19-P-5 r3 Codex 판정 링크를 매 세션 덮어쓰기되는 `latest_codex_review.md` → 영구 보존본 `19-P-5_codex_review.md` 로 변경.
    - 본 r2 는 표현/링크 정정만 — 실제 순서 / 세션별 계획 / 응답 키 보호 / 후속 검토 분류 모두 r1 시점 그대로 유지. Codex r1 G-1 ~ G-12 모두 pass / pass with caveat 결과 보존.

### 0-1. 19-P-5 r3 Codex caveat 본 19-P-6 반영

| caveat | 19-P-6 반영 |
|---|---|
| 워크트리 18-0~18-8 계열 dirty/untracked 변경 다수 | §2 19-0 시점에 "변경 소유권 + diff 기준 좁히기" 명시 (19-0 선행 조건). |
| pytest 미실행 (read-only 검증) | 본 19-P-6 도 read-only 문서 세션 — pytest 실행은 19-0 부터. |

### 0-2. 본 문서가 다루지 않는 범위

- 실제 코드 이동 / 파일 생성 / 테스트 작성 — 19-0 이후 별도 세션.
- m014+ 마이그레이션 결정 — 본 19-P 기간 내 미도입 (19-P-2 P-4 정합).
- v1.4.0 배포 절차 — [docs/releases/18_ai_rag_final_checklist.md](../releases/18_ai_rag_final_checklist.md) 별도 게이트.

---

## 1. 롤아웃 기본 원칙

> 19-P-2 [§1 P-1 ~ P-12](19_refactor_target_architecture.md) + 19-P-5 [§1 T-1 ~ T-15](19_refactor_test_strategy.md) 의 통합 적용.

| # | 원칙 | 본문 |
|---|---|---|
| R-1 | 기능 변경이 아니라 구조 정리 | 단위화 = 구조 안정화. 예약/휴무/문자/통계/AI 결과는 변경 전후 동일. |
| R-2 | 한 번에 대규모 이동 금지 | 한 세션 = 한 모듈 (또는 작은 범위). 모듈 1개당 1 PR/1 commit 권장. |
| R-3 | 세션별로 작은 범위만 이동 | wrapper/adaptor 패턴 — 신규 폴더 + 기존 함수 위임 → 응답 검증 → 기존 코드 제거. 세션 안에 모두 마무리 안 되어도 OK (다음 세션 이어서). |
| R-4 | 기존 API URL과 응답 key 유지 | 19-P-1 §21 의 33+ 키 셋 + 비-AI alias (`therapist_id`/`employee_id` 이중 키 등) 보존. **추가만** 허용. |
| R-5 | 기존 UI 동작 유지 | [app/templates/main.html](../../app/templates/main.html) 7331줄 + JS / CSS / FullCalendar 무수정. UI 분리는 19-P 비-목표. |
| R-6 | 기존 DB schema 가능하면 유지 | m001~m013 diff 0. 컬럼 rename 금지. 신규 마이그레이션 m014+ 는 19-P 기간 내 미도입 (필요 시 별도 세션). |
| R-7 | 테스트 먼저 고정 후 코드 이동 | 분리 *직전*: 도메인별 contract 테스트 신규 추가 → **분리 직후**: 회귀 통과 확인. 19-P-5 §4 보강 9개 항목 도메인별로 적용. |
| R-8 | 이동 후 전체 회귀 테스트 | 큰 모듈 1개 이동 완료 직후 `pytest tests -v` (전체) — 18-8 baseline (529 passed, 1 skipped, 7 xfailed) 회귀 0 확인. |
| R-9 | 5회 실패 시 땜질 중단 → rollback 또는 재작성 | [docs/AI_WORKING_RULES.md §3](../AI_WORKING_RULES.md) + 19-P-5 §6-E. `latest_failure_report.md` 작성 + 사용자 결정. |
| R-10 | Codex 검증 없이 다음 세션 진행 금지 | Claude Code 자체 통과 = 최종 완료 X. Codex 가 실제 diff·파일·결과·로그 독립 확인 후에만 다음 세션 진입. |
| R-11 | 운영 DB 미접근 + 외부 API 차단 | `tests/conftest.py` 4단계 격리 + `_block_sdk_modules` + `tests/harness/db_guard.assert_safe_db_path()` + `scripts/check_db_path.py` 머지 게이트 — 매 세션 자동. |
| R-12 | local-first 보존 | `local_only` 모드에서 `len(provider.calls) == 0` + `len(embedding_provider.calls) == 0`. AI/RAG → 도메인 DB 임의 생성 ⊥. |
| R-13 | per-file-ignores / `manual60=1` 보존 | `pyproject.toml` `app/**` per-file-ignores 풀지 않음. `manual60` `count_increment=1` 절대 2로 되돌리지 않음. |
| R-14 | 후속 검토 항목 단정 X | doctors / `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` / `Order` / `Prescription` / 노쇼 / 반복예약 / 자원 / 알림 / 출력물 / EMR 등은 **현재 부재** — 본 19-P 기간 내 도입 X. |

---

## 2. 추천 리팩토링 순서

> 19-P-2 [§9 모듈 분류표](19_refactor_target_architecture.md), 19-P-3 [§31 우선순위](19_refactor_module_map.md), 19-P-4 [§6 분리 순서 영향](19_refactor_dependency_map.md), 19-P-5 [§5 테스트 우선순위](19_refactor_test_strategy.md) 통합 정리.
>
> 사용자 §2 후보 순서를 기본으로 하되 위험도 + 의존성 + 테스트 보강 시점을 반영.

> **단계 수 표기** (r2 보정 — Codex r1 caveat 1번 정합):
> - **19-P** = 구조 계획 (본 19-P-1~6, read-only 문서) — 본 §2 표 1행.
> - **19-0** = 리팩토링 전 기준 테스트 / 하네스 재확인 (baseline 고정) — 본 §2 표 1행.
> - **19-1 ~ 19-14** = **실제 코드 리팩토링 14개 세션** (19-1 core ~ 19-14 종료 게이트).
> - **§2-1 표 합계** = 19-P + 19-0 + 19-1~14 = **16행** (19-P 메타 1 + 실행 세션 15).
> - **실행 세션 수** = 19-0~19-14 = **15개** (= 19-1~19-14 의 14개 리팩토링 + 19-0 의 1개 baseline).

### 2-1. 단계 개요

| 단계 | 세션 이름 | 위험도 | 분리 타입 |
|---|---|---|---|
| **19-P** | 구조 계획 (19-P-1~6) | 0 (read-only) | 문서 |
| **19-0** | 리팩토링 전 기준 테스트 / 하네스 재확인 | 낮음 | 테스트 baseline 고정 |
| **19-1** | core 공통 유틸 / 응답 / 에러 / 시간 유틸 정리 | 낮음 | core 분리 |
| **19-2** | settings / feature_flags / health 경계 정리 | 낮음~중간 | core + 신규 / 후속 분류 명시 |
| **19-3** | calendar / schedule_view 표시용 view-model 분리 (post-19-P 후보, view-model 만) | 낮음 | view-model only |
| **19-4** | availability 예약 가능 여부 / 충돌 검사 분리 | 중간 | appointments 사전 준비 |
| **19-5** | leaves 휴무 규칙 분리 + `am`/`pm`/`full` 백엔드 차단 보강 | **높음** | 단일 진실원천 보존 |
| **19-6** | treatments / completion_rules 치료항목·완료체크 분리 | 중간 | `manual60=1` 보존 |
| **19-7** | patients / notes 환자·메모 경계 분리 | 중간 | export_import (data-convert) 와 함께 분리 |
| **19-8** | staff (therapists + doctors 얇은 분기) 정리 | 낮음~중간 | medical_staff 통합 (별도 doctors 폴더는 후속) |
| **19-9** | appointments 예약 service / repository 분리 | **높음** | **마지막 분리 권장** |
| **19-10** | sms 문자 대상 추출 / 템플릿 / provider 경계 분리 | 중간 | 외부 HTTP mock |
| **19-11** | stats 통계 집계 분리 | 중간 | 8 endpoint contract |
| **19-12** | admin / backup / audit / export_import 경계 정리 | 낮음~중간 | 묶음 분리 |
| **19-13** | AI commands 와 기존 예약 / 휴무 / 문자 연결부 정리 | 중간 | local-first 보존 |
| **19-14** | 전체 회귀 테스트 / PyInstaller 검증 | 낮음 (검증) | 종료 게이트 |

### 2-2. 순서 결정 근거

| 결정 | 근거 |
|---|---|
| **19-1 core 우선** | 19-P-3 §31 우선순위 1 + 19-P-4 §6-A "먼저 분리" — modules/* 가 공통 참조하는 경계 (config/database/responses/errors/time_utils/security/feature_flags) 가 안정되지 않으면 후속 모듈 분리가 흔들린다. |
| **19-2 settings/health 경계** | settings 는 19-P-3 §31 우선순위 3 + 19-P-4 §5-7 (admin↔settings↔feature_flags 단방향 정리). health 는 post-19-P 후속 — 19-2 에서 *분류만* 확정 (코드 신설 X). |
| **19-3 calendar view-model** | 19-P-2 §2-2 / 19-P-3 §31 post-19-P. **본 19-3 은 view-model only — main.html JS/UI 무수정**. 19-P-2 §2-2 의 "M-26 calendar/" 후보 폴더 신설은 본 19-P 비-목표. 사용자 §2 가 19-3 으로 명시했으므로 *서버 사이드 view-model 분리 가능 여부만 검토 + 후속 결정 보류* 로 진행. |
| **19-4 availability 분리** | appointments 사전 준비 — 점심창 / 충돌 / 휴무 / 반차 백엔드 차단 코드를 `modules/appointments/availability.py` 후보 위치로 추출 검토. 19-P-4 §5-2 (appointments↔availability 같은 모듈 안 분리). 19-P-5 §3-1 의 점심창/PUT/DELETE/낙관적 락 보강 9개 항목 일부도 본 시점 보강 후보. |
| **19-5 leaves + `am`/`pm`/`full` 백엔드 차단** | 19-P-3 §31 우선순위 6 + 19-P-4 §5-1 (appointments↔leaves) + **19-P-4 caveat / 19-P-5 §3-5 핵심 — `xfail` 4건 백엔드 차단 코드 추가 + 정방향 전환**. `_upsert_employee_leave_core` 단일 진실원천 보존 + AI action_leave 가 같이 호출하는 의존성 보호. |
| **19-6 treatments / completion_rules** | 19-P-3 §31 우선순위 5 + 19-P-2 §3-5 — `manual60=1` 정책 보존 + approve/revert 흐름. completion_rules 분리는 appointments / patients / stats 가 의존하는 핵심. |
| **19-7 patients / notes + data-convert** | 19-P-3 §31 우선순위 7 + 19-P-2 §3-2 — 환자 검색 / 메모 / 중복 검사 + data-convert (`_dc_*` ~600줄) 함께. notes 통합 (`modules/notes/`) 은 post-19-P 후속. |
| **19-8 staff 통합** | 19-P-2 §3-3 / 19-P-3 §31 우선순위 4 — Employee `role="doctor"|"therapist"` 단일 테이블 분기 + alias 이중 키. **별도 `modules/doctors/` 폴더 신설은 post-19-P** (M-31, EMR 도입 시). |
| **19-9 appointments 마지막** | 19-P-2 P-5 + 19-P-3 §2-1 + 19-P-4 §6-B "나중 분리" — patients/staff/treatments/leaves/availability 모두 안정된 후 진입. wrapper 점진 위임. |
| **19-10 sms** | 19-P-3 §31 우선순위 9 + 19-P-2 §3-7 — 외부 HTTP client (`provider.py`) 분리 + 자동 발송 트리거 ⊥ (appointments 와 분리됨 보장). |
| **19-11 stats** | 19-P-3 §31 우선순위 8 — 8 endpoint contract + 엑셀 export. read-only 의존 — appointments / treatments / patients / leaves 안정 후 진입. |
| **19-12 admin / backup / audit / export_import 묶음** | 19-P-3 §31 우선순위 2 (audit) / 11 (admin/backup) — 위험도 낮은 모듈 묶음. export_import 는 19-7 patients 와 동시 분리도 가능 (참고). |
| **19-13 AI commands 연결부** | 19-P-2 §3-10 + 19-P-4 §5-8 — `action_leave` (917줄) → `modules/ai/commands/`. local-first 보존 + 도메인 service 호출만 (commands → 도메인 ⊥ 역참조 X). |
| **19-14 종료 게이트** | 19-P-5 §6-D PyInstaller 4단계 + 사용자 명시 승인 시 빌드 (CLAUDE.md 배포 규칙). |

### 2-3. 사용자 §2 주의사항 정합

- **예약 모듈은 의존성이 크므로 너무 초반에 크게 이동하지 않습니다** → 19-9 마지막 권장 (R-3 / 19-P-3 우선순위 14).
- **appointments 분리 전 availability, leaves, treatments, patients, therapists 경계를 먼저 정리** → 19-4 ~ 19-8 순서로 사전 정리 후 19-9 진입.
- **현재 기능에 없는 doctors, recurring_appointments, resources, notifications, printing 등은 후속 검토** → R-14 + §9 후속 검토 항목 표 정합.

---

## 3. 각 세션별 계획

> 컬럼 12개: 세션 번호 / 세션 이름 / 목표 / 수정 가능 범위 / 수정 금지 범위 / 선행 조건 / 반드시 실행할 테스트 / 유지해야 할 API/응답 key / 위험도 / rollback 기준 / Codex 검증 포인트 / 주석/문서화 필요 지점.
>
> 가독성을 위해 세션마다 **세로 표 1개** 로 작성.

### 3-0. 19-0 리팩토링 전 기준 테스트 / 하네스 재확인

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-0 |
| 세션 이름 | 리팩토링 전 기준 테스트 / 하네스 재확인 (baseline 재고정) |
| 목표 | (1) 18-8 baseline 529/1/7 통과 재확인. (2) 워크트리 dirty/untracked 정리 (18-0~18-8 변경분 main 머지 또는 별도 commit). (3) 19-P-1~5 캐비엇 / 후속 검토 / 보강 필요 9개 항목 인덱싱. (4) 19-1 진입 직전의 깨끗한 baseline 확보. |
| 수정 가능 범위 | (a) 18-0~18-8 변경분 commit / main 머지 (사용자 승인 후). (b) 보강 contract 테스트 추가 후보 grep / 인덱싱 (테스트 작성은 본 세션 비-목표 — 작성 시점은 19-1+ 도메인 분리 직전). |
| 수정 금지 범위 | `app/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`. 19-P-1~6 산출물 무수정. |
| 선행 조건 | 19-P-5 r3 Codex pass with caveat (yes 진입 가능). |
| 반드시 실행할 테스트 | `run_check.bat` (pytest + ruff + check_db_path) — 18-8 baseline 일치 확인. `pytest tests -v` (전체 회귀). 18-7 / 18-8 하네스 6개 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid). 운영 DB 보호 5단계 (S-1~S-5). 외부 API 차단 (`_block_sdk_modules`). |
| 유지해야 할 API/응답 key | 33+ 키 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9 + 비-AI alias). 본 세션은 분리 X — 변경 0 확인. |
| 위험도 | 낮음 (baseline 검증). |
| rollback 기준 | baseline 회귀 발생 시 — 18-0~18-8 변경분 어디에서 회귀가 들어왔는지 추적 후 별도 fix 세션. 19-1 진입 차단. |
| Codex 검증 포인트 | (1) 18-8 baseline 일치. (2) 워크트리 cleanliness (`git status --short` + `git diff --stat bcd74a7`). (3) 보강 9개 항목 분류 정합 (19-P-5 §4-1). |
| 주석/문서화 필요 지점 | 본 세션은 코드 수정 X — 신규 주석 0. 19-1+ 적용을 위한 주석 카테고리 표 (§4) 인덱싱만. |

### 3-1. 19-1 core 공통 유틸 / 응답 / 에러 / 시간 유틸 정리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-1 |
| 세션 이름 | core 공통 유틸 / 응답 / 에러 / 시간 유틸 / 보안 / feature_flags 분리 |
| 목표 | 19-P-2 §2-1 의 `app/core/` 폴더 신설 — `config.py` / `database.py` / `responses.py` / `errors.py` / `time_utils.py` / `security.py` / `feature_flags.py`. 기존 위치 (`app/config.py`, `app/database.py`, `app/services/auth.py`, `_lunch_window` 등) 에서 wrapper/adaptor 로 위임. |
| 수정 가능 범위 | (a) `app/core/` 신규 폴더. (b) `app/config.py` → `app/core/config.py` 이동 (wrapper 보존). (c) `app/database.py` → `app/core/database.py`. (d) `app/services/auth.py` → `app/core/security.py`. (e) `dosu_clinic.spec` hidden imports 갱신. (f) `app/main.py` import 경로 갱신. (g) 신규 contract 테스트 (security / time_utils 단언). |
| 수정 금지 범위 | `app/routers/api.py`, `app/routers/ai.py`, `app/templates/**`, `app/static/**`, `app/migrations/m001~m013.py`, `app/models/**`, `pyproject.toml` per-file-ignores, 18-0~18-8 산출물. 응답 키 / URL 변경 ⊥. |
| 선행 조건 | 19-0 baseline 재고정 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat` 전체. `test_admin_auth_required.py` (security 회귀). `test_pyinstaller_hidden_imports.py` 53 tests (spec 갱신 즉시). 운영 DB 보호 5단계. AI 하네스 6개 (회귀 0). |
| 유지해야 할 API/응답 key | 변경 0 (분리만 — 응답 dict 그대로). `require_admin` / `require_admin_or_sync_token` 시그니처 보존. |
| 위험도 | **낮음** (단일 모듈 이동, 단 import 경로 변경 多). |
| rollback 기준 | (a) `require_admin` 의존 86 endpoint 중 하나라도 깨짐. (b) `init_db()` 호출 순서 변경 (마이그레이션 누락). (c) PyInstaller 53 hidden imports 회귀. (d) 5회 루프 실패. |
| Codex 검증 포인트 | (1) `app/core/` 신설 + 기존 import 경로 wrapper 유지. (2) PBKDF2 / `SESSION_TTL_SEC` / `MAX_FAILURES` 정책 무변경. (3) 응답 dict 키 그대로. (4) `dosu_clinic.spec` hidden imports 갱신. |
| 주석/문서화 필요 지점 | `# COMPAT:` (config / database / auth wrapper — import 경로 호환). `# SAFETY:` (PBKDF2 + 세션 + 5회 잠금). `# NOTE:` (`get_db_path` `DOSU_DB_PATH` 우선 정책). `# TODO(19-2):` (feature_flags 단일 진실원천 — settings 분리 후 통합). |

### 3-2. 19-2 settings / feature_flags / health 경계 정리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-2 |
| 세션 이름 | settings / feature_flags 통합 + health 경계 (`/api/health` 신설은 후속) |
| 목표 | (1) `app/modules/settings/` 신규 — `SystemSetting` read/write. (2) `app/core/feature_flags.py` 단일 진입점 — `AiSetting.enabled` + 환경 변수 (`AI_RAG_*`) 파생. (3) **`/api/health` 신설은 post-19-P 후속** (M-28) — 본 19-2 는 분류 / 후속 검토 명시만. (4) 기존 `/api/system-settings` / `/api/config/*` URL 그대로. |
| 수정 가능 범위 | (a) `app/modules/settings/` 신규 폴더 (router 포함, URL 변경 0). (b) `app/core/feature_flags.py` 신규. (c) `app/services/seed.py:_seed_system_setting` import 경로 갱신. (d) `app/routers/api.py` 의 system-settings / config 핸들러 위임. (e) `dosu_clinic.spec` 갱신. (f) 신규 contract 테스트 (system-settings 응답 키). |
| 수정 금지 범위 | `app/routers/ai.py` 의 AI settings 흐름 (`/api/ai/settings` 는 19-13 에서 처리). `SmsSetting` / `AiSetting` 컬럼 / 시드. m001~m013 무수정. |
| 선행 조건 | 19-1 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_ai_assist_mode.py` + `test_local_only_mode.py` (feature_flags 파생 회귀). `test_admin_ui_smoke.py` (관리자 설정 화면). PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `GET/POST /api/system-settings`, `GET/POST /api/config[/sync-secret]`, `POST /api/mode`. `ai_mode` / `search_mode` (`/api/ai/status`) 키. `enabled / provider / model / api_key_set / sdk_installed / sdk_errors / knowledge_doc_count / ready / version` (9키 admin health). |
| 위험도 | 낮음~중간. |
| rollback 기준 | (a) `ai_mode` (local_only/local_first/ai_assist) 파생 결과 변경. (b) `/api/system-settings` 응답 키 변경. (c) `manual_slot_limit` / `auto_backup_*` 정책 무시됨. (d) 5회 루프 실패. |
| Codex 검증 포인트 | (1) `feature_flags` 단일 진실원천 — 환경 변수 + DB 우선순위 명시 (T-8 19-P-2). (2) `/api/system-settings` 응답 키 보존. (3) `health` 후속 검토 명시 (코드 신설 X). |
| 주석/문서화 필요 지점 | `# COMPAT:` (system-settings 응답 키). `# NOTE:` (`auto_backup_keep_count` / `manual_slot_limit` 정책). `# TODO(post-19-P):` (`/api/health` 신설 후속 — `modules/health/`). |

### 3-3. 19-3 calendar / schedule_view 표시용 view-model 분리 (서버 사이드 only)

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-3 |
| 세션 이름 | calendar / schedule_view 서버 사이드 view-model 분리 검토 |
| 목표 | **검토 + 분류 명시 only**. 19-P-2 §2-2 가 calendar 를 post-19-P 후속으로 둠. 본 19-3 은 사용자 §2 명시에 따라 **서버 사이드 view-model 만** 분리 가능 여부를 검토. main.html JS / FullCalendar / Alpine 무수정. 결과: (a) 분리 가능하면 `app/modules/calendar/view_models.py` 신설 (read-only 조립), (b) 분리 어려우면 19-3 패스 + 19-P-7 위험 등록 + post-19-P 후속 분류 확정. |
| 수정 가능 범위 | (a) `app/modules/calendar/view_models.py` 신규 (분리 가능 시만). (b) `app/routers/api.py` 의 calendar 관련 GET 핸들러 (`/api/appointments`, `/api/employee-leaves`, `/api/therapists`) 응답 조립부 위임. (c) `dosu_clinic.spec` 갱신. (d) 검토 결과 문서 [docs/refactor/19-3_calendar_decision.md](19-3_calendar_decision.md) 신설. |
| 수정 금지 범위 | `app/templates/main.html` JS / FullCalendar 코드. `app/static/**`. CSS. `app/routers/api.py` 의 응답 dict 키. UI 분리 ⊥. |
| 선행 조건 | 19-2 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_admin_ui_smoke.py`. PyInstaller 53 tests (신설 시). AI 하네스 6개. UI smoke 는 자동 검증 부재 — 분리 후 사용자 수동 확인 권장. |
| 유지해야 할 API/응답 key | `/api/appointments` / `/api/employee-leaves` / `/api/therapists` 응답 키 100%. FullCalendar event ID / start / end / status / version / treatment_codes 필드. |
| 위험도 | 낮음 (분리 가능 시) / **0** (분리 패스 시). |
| rollback 기준 | (a) FullCalendar event 표시 깨짐. (b) 휴무자 / 치료사 색상 표시 깨짐. (c) 응답 키 변경. (d) UI 자동 검증 부재로 인해 *분리 후 사용자 수동 확인 실패* 시 즉시 rollback. (e) 5회 루프 실패. |
| Codex 검증 포인트 | (1) view-model 만 분리 (UI 무수정). (2) 응답 키 100%. (3) **분리 패스 결정 시** post-19-P 후속 분류 확정 정합 (19-P-2 §2-2 / 19-P-3 §31). |
| 주석/문서화 필요 지점 | `# COMPAT:` (FullCalendar event 필드 보존). `# NOTE:` (view-model = read-only 조립, write 책임 부재). `# TODO(post-19-P):` (UI 분리 후속 — main.html JS 외부 분리 별도 세션). |

### 3-4. 19-4 availability 예약 가능 여부 / 충돌 검사 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-4 |
| 세션 이름 | appointments availability — 점심창 / 충돌 / 휴무 / 반차 / 시간 가능 여부 분리 |
| 목표 | (1) `app/modules/appointments/availability.py` 신규 (또는 19-9 까지 wrapper). (2) `_lunch_window` / `_check_lunch_block` ([api.py:64-107](../../app/routers/api.py:64)) 추출. (3) 19-P-4 caveat — `leave_type=am/pm/full` 백엔드 차단 코드 위치 grep + 신설 (현재 부재 — 19-P-5 §3-1/§3-5 `xfail` 4건 정방향 전환 사전 작업). (4) 충돌 검사 (도수 중복) 백엔드 차단 코드 신설 후보. |
| 수정 가능 범위 | (a) `app/modules/appointments/availability.py` 신규. (b) `app/routers/api.py` 의 점심창 / 충돌 / 휴무 차단 호출 위임. (c) **백엔드 차단 코드 신설 (휴무 차단 + 도수 중복)** — `_serialize_appointment` 등 응답 dict 무변경. (d) `tests/test_appointment_rules.py` `xfail` 3건 정방향 전환 (백엔드 차단 추가 시). (e) `tests/test_therapist_leave.py` `xfail` 4건 정방향 전환. (f) 신규 점심창 / PUT / DELETE / 409 contract 테스트. |
| 수정 금지 범위 | `_serialize_appointment` 응답 dict 키. `Appointment.version` 컬럼 / `_check_version` / `_bump_version` 시그니처. m001~m013. AI action_leave 흐름 (19-13 에서 처리). |
| 선행 조건 | 19-3 완료 + Codex pass. **19-P-5 §3-1 / §3-5 의 `xfail` 7건 + `skip` 1건 인덱싱 완료**. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_appointment_rules.py` (xfail → 정방향 전환 후). `test_therapist_leave.py` (동상). PyInstaller 53 tests. AI 하네스 6개. **백엔드 차단 추가 시 회귀 0 확인 — 비도수 중복 허용 / 반차 허용 시간대 정방향 유지**. |
| 유지해야 할 API/응답 key | `POST /api/appointments` / `PUT /api/appointments/{aid}` 응답 키 (특히 `version`, `treatment_codes`, `status`). 점심창 / 충돌 / 휴무 차단 시 400 응답 + `detail` 한국어 메시지. |
| 위험도 | **중간** — 백엔드 차단 코드 신설은 *기능 추가 X* (spec 01/02 에 명시된 차단을 코드로 구현). 응답 키는 변경 0. |
| rollback 기준 | (a) 비도수 중복 허용 (`test_two_eswt_same_slot_allowed`) 회귀 — 차단되면 안 됨. (b) 반차 허용 시간대 회귀 (`test_morning_leave_allows_after_noon` 등). (c) 응답 키 변경. (d) `Appointment.version` 낙관적 락 깨짐. (e) 5회 루프 실패. |
| Codex 검증 포인트 | (1) `tests/test_appointment_rules.py` `xfail` 3건 + `skip` 1건 → 정방향 전환 (marker 제거). (2) `tests/test_therapist_leave.py` `xfail` 4건 → 정방향. (3) 비도수 중복 허용 + 반차 허용 시간대 회귀 0. (4) 응답 키 + 낙관적 락 무변경. (5) `_upsert_employee_leave_core` 시그니처 무변경 (19-5 에서 분리). |
| 주석/문서화 필요 지점 | `# NOTE:` (점심창 정책 / 도수 중복 차단 spec 01 / 휴무 차단 spec 02). `# RISK:` (낙관적 락 TOCTOU). `# COMPAT:` (응답 키 + version 필드). `# TODO(19-9):` (wrapper 제거 — appointments service 통합 후). |

### 3-5. 19-5 leaves 휴무 규칙 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-5 |
| 세션 이름 | leaves 휴무 규칙 분리 + `_upsert_employee_leave_core` 단일 진실원천 보존 |
| 목표 | (1) `app/modules/leaves/{router,service,repository,schemas,rules}.py` 신규. (2) `_upsert_employee_leave_core` ([api.py:1098](../../app/routers/api.py:1098)) → `leaves.service` 이동. (3) `/api/employee-leaves[/...]` + alias `/api/therapist-leaves[/...]` URL 그대로. (4) `leave_kind` (annual/monthly) + `leave_type` (am/pm/full) DB 표준 보존. (5) AI `action_leave` 가 `leaves.service._upsert_employee_leave_core` 만 호출 — 단일 진실원천 유지. |
| 수정 가능 범위 | (a) `app/modules/leaves/` 신규 폴더. (b) `app/routers/api.py` 의 휴무 핸들러 위임. (c) `app/services/ai/action_leave.py` 의 `_upsert_employee_leave_core` import 경로 갱신 (호출만 — 흐름 무변경). (d) `dosu_clinic.spec` 갱신. (e) 신규 alias 이중 키 contract 테스트. |
| 수정 금지 범위 | `EmployeeLeave` ORM 컬럼 / `(employee_id, leave_date)` UNIQUE / `leave_kind` 컬럼 (m011 / m009). HMAC + TOCTOU 정책. AI action_leave 의 parse / preview / execute 흐름. m001~m013. |
| 선행 조건 | 19-4 완료 + Codex pass. **19-P-5 §3-5 `xfail` 4건이 19-4 에서 정방향 전환 완료**. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_employee_leave_unique.py` / `test_employee_leave_kind.py` (등록 측면). `test_therapist_leave.py` (정방향 전환 후 — 19-4 결과). `test_ai_action_leave.py` (1232줄). PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `/api/employee-leaves[/...]` + alias `/api/therapist-leaves[/...]` URL + 응답 키 100%. `therapist_id` ↔ `employee_id` 이중 키 ([api.py:1184-1199](../../app/routers/api.py:1184)). `leave_kind` (annual/monthly) + `leave_type` (am/pm/full) 응답 필드. |
| 위험도 | **높음** — `_upsert_employee_leave_core` 가 leaves API + AI action_leave 가 같이 호출하는 단일 진실원천. 잘못 분리하면 두 흐름의 정책이 갈라짐. |
| rollback 기준 | (a) AI action_leave parse / preview / execute 흐름 깨짐. (b) HMAC + TOCTOU 정책 무시. (c) alias 이중 키 응답 한쪽만 반환. (d) `leave_kind` / `leave_type` DB 표준 변경. (e) 5회 루프 실패. |
| Codex 검증 포인트 | (1) `_upsert_employee_leave_core` 단일 진실원천 — leaves.service + AI action_leave 두 호출지 모두 `from app.modules.leaves.service import _upsert_employee_leave_core`. (2) HMAC 토큰 정책 무변경. (3) alias 응답 키 보존. (4) 19-4 에서 정방향 전환된 4건이 19-5 분리 후에도 정방향 유지. |
| 주석/문서화 필요 지점 | `# NOTE:` (`leave_type` DB 표준 — `am`/`pm`/`full` / `leave_kind` annual/monthly). `# RISK:` (HMAC + TOCTOU — AI action_leave 와 동시 호출 시 락). `# COMPAT:` (alias 이중 키 — `therapist_id` / `employee_id`). `# SAFETY:` (PII 마스킹 — leaves 흐름은 PII 부재지만 audit 호출 시 환자명 부재 확인). |

### 3-6. 19-6 treatments / completion_rules 치료항목·완료체크 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-6 |
| 세션 이름 | treatments + completion_rules 분리 (`manual60=1` 보존) |
| 목표 | (1) `app/modules/treatments/{router,service,repository,schemas,completion_rules}.py` 신규. (2) `Treatment` CRUD ([api.py:858-1008](../../app/routers/api.py:858)) → treatments.router. (3) `_bump_patient_count` ([api.py:1934](../../app/routers/api.py:1934)) + `approve` / `revert-approve` 흐름 → completion_rules. (4) `manual60` `count_increment=1` 정책 직접 단언 추가. (5) `_doctor_codes_set` / `_existing_codes_set` 등 코드 분류 헬퍼 ([api.py:148-168](../../app/routers/api.py:148)) treatments 모듈 안에서 통합 (또는 wrapper). |
| 수정 가능 범위 | (a) `app/modules/treatments/` 신규. (b) `app/routers/api.py` 의 treatments / approve / revert-approve 핸들러 위임. (c) `app/models/constants.py` `manual60` 단언 직접 검증 테스트 추가. (d) `dosu_clinic.spec` 갱신. (e) `_normalize_incentive` / `_serialize_treatment` 이동. |
| 수정 금지 범위 | `Treatment.count_increment` (특히 `manual60=1`). `PatientTreatmentCount.(patient_id, treatment_id)` UNIQUE / `rx_count` / `done_count` 컬럼. m001~m013. `_check_version` / `_bump_version` 시그니처. AI 하네스. |
| 선행 조건 | 19-5 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_appointment_rules.py` (approve / revert 흐름). `test_stats_counts.py` (manual 카운트 집계). 신규 `manual60=1` 직접 단언. PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `GET /api/treatments` / `POST/PUT/DELETE /api/treatments/{tid}` / `GET /api/treatment-meta` / `GET /api/treatments/{tid}/references` 응답 키. `POST /api/appointments/{aid}/approve` / `POST /api/appointments/{aid}/revert-approve` 응답 키 + done_count ±N 정책. |
| 위험도 | 중간 — `_doctor_codes_set` / `_existing_codes_set` 가 stats / appointments / sms 다중 의존. |
| rollback 기준 | (a) `manual60` `count_increment` 가 1 이외로 변경. (b) approve 후 `done_count` +N 정책 변경. (c) 시간 가중치 방식으로 되돌림. (d) `_doctor_codes_set` 결과 변경 (현재 injection/cartilage). (e) 5회 루프 실패. |
| Codex 검증 포인트 | (1) `manual60` `count_increment=1` 직접 단언 추가. (2) approve / revert 흐름 응답 키 보존. (3) `_doctor_codes_set` 결과 (`injection`/`cartilage`) 무변경. (4) PatientTreatmentCount UNIQUE 보존. |
| 주석/문서화 필요 지점 | `# NOTE:` (`manual60=1` 정책 — CLAUDE.md 명시 / 절대 2 ⊥). `# COMPAT:` (응답 키 + done_count). `# RISK:` (count_increment 정책 변경 시 stats 회귀 다수). `# TODO(19-9):` (wrapper 제거 — appointments service 통합 후). |

### 3-7. 19-7 patients / notes / data-convert 환자·메모·엑셀 변환 경계 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-7 |
| 세션 이름 | patients + notes_service + export_import (data-convert) 분리 |
| 목표 | (1) `app/modules/patients/{router,service,repository,schemas,notes_service}.py` 신규. (2) `_patient_to_dict` / `_serialize_patients_bulk` / `_check_patient_duplicate` 이동. (3) `PATCH /api/patients/{pid}/memo` → notes_service. (4) `app/modules/export_import/{service,schemas}.py` 신규 — `data-convert/preview/apply` (`_dc_*` ~600줄). (5) 통합 `modules/notes/` 는 post-19-P 후속 (지속 메모 vs 당일 메모 정책 결정 후). |
| 수정 가능 범위 | (a) `app/modules/patients/` + `app/modules/export_import/` 신규. (b) `app/routers/api.py` 의 patients / data-convert 핸들러 위임. (c) `dosu_clinic.spec` 갱신. (d) 신규 contract 테스트 (환자 검색 / 메모 / 중복 검사 / data-convert preview/apply). |
| 수정 금지 범위 | `Patient` ORM 컬럼 / `gender` (m002) / 인덱스 (m004). `PatientTreatmentCount` (19-6 분리됨). `Appointment.memo` vs `Patient.memo` 의미 차이. m001~m013. |
| 선행 조건 | 19-6 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. 신규 환자 contract 테스트. data-convert preview/apply contract. `test_stats_counts.py` (신환 카운트). PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `/api/patients[/search/{pid}/last-appointments]` + `/api/patients/{pid}/{history,manual-history-summary}` + `PATCH /api/patients/{pid}/memo` 응답 키. `/api/data-convert/preview` + `/api/data-convert/apply` 응답 키. counts dict (treatment_id → {rx_count, done_count}). |
| 위험도 | 중간. |
| rollback 기준 | (a) 환자 검색 인덱스 (이름/연락처/차트번호) 결과 변경. (b) 중복 검사 정책 변경 (`_check_patient_duplicate`). (c) data-convert 정규화 정책 변경 (gender / SSN / phone). (d) memo PATCH 가 다른 환자 영향. (e) 5회 루프 실패. |
| Codex 검증 포인트 | (1) PII 마스킹 정책 보존 — 환자명/연락처가 audit / AiUsageLog / 로그 / 응답에 원문 부재. (2) counts dict 키 보존. (3) data-convert 트랜잭션 안전성. (4) `_dc_*` 헬퍼 통째 이동 vs 세분화 결정 (T-11 19-P-2 — 19-7 에서 결정). |
| 주석/문서화 필요 지점 | `# COMPAT:` (counts dict 키). `# SAFETY:` (PII 비노출 — 환자명/연락처). `# NOTE:` (`_check_patient_duplicate` 정책). `# RISK:` (data-convert 대량 import 트랜잭션). `# TODO(post-19-P):` (`modules/notes/` 통합 — 지속 메모 vs 당일 메모 정책 결정 후). |

### 3-8. 19-8 staff (therapists + doctors 얇은 분기) 정리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-8 |
| 세션 이름 | staff 통합 모듈 (Employee role 분기) + alias 이중 키 보존 |
| 목표 | (1) `app/modules/staff/{router,service,repository,schemas,doctors_service}.py` 신규. (2) Employee CRUD + reorder + alias `/api/therapists` / `/api/therapist-leaves` 통합. (3) `_serialize_employee` 이동. (4) `_doctor_codes_set` (얇은 분기) → `staff/doctors_service`. (5) **별도 `modules/doctors/` 폴더 신설은 post-19-P 후속** (M-31, EMR / `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` / `Order` / `Prescription` 도입 시). |
| 수정 가능 범위 | (a) `app/modules/staff/` 신규. (b) `app/routers/api.py` 의 employees / therapists / therapist-leaves alias 핸들러 위임. (c) `dosu_clinic.spec` 갱신. (d) 신규 alias 이중 키 contract 테스트. (e) 신규 의사 분기 회귀 테스트 (`_doctor_codes_set` / `is_doctor_filter` 결과). |
| 수정 금지 범위 | `Employee` ORM 컬럼 / `role` ENUM / `can_eswt` / `can_manual` / `hire_date` (m010). `Treatment.role="doctor"` 분기. m001~m013. **부재 항목 신설 ⊥** — `Doctor` 별도 테이블 / `Department` / `Room` / `DoctorSchedule` / `Patient.doctor_id` / `Order` / `Prescription` 도입 ⊥. |
| 선행 조건 | 19-7 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_employee_*.py` (4 파일) + `test_employee_can_manual_contract.py` + `test_employee_hire_date.py`. 신규 alias 이중 키 contract. 신규 의사 분기 회귀. PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `GET/POST/PUT/DELETE /api/employees` + `POST /api/employees/reorder`. alias `/api/therapists` (role=therapist 필터) + `/api/therapist-leaves[/bulk-set]` (이중 키 `therapist_id`/`employee_id`). `_serialize_employee` 응답 dict. |
| 위험도 | 낮음~중간. |
| rollback 기준 | (a) alias `therapist_id` 키 부재. (b) `role` 분기 결과 변경 (의사/치료사 필터). (c) `_doctor_codes_set` 결과 변경 (현재 `injection`/`cartilage`). (d) `Treatment.role="doctor"` 분기 결과 변경 (assignment role 강제). (e) 5회 루프 실패. |
| Codex 검증 포인트 | (1) alias 이중 키 응답 보존 ([api.py:1184-1199](../../app/routers/api.py:1184)). (2) `_doctor_codes_set` (`injection`/`cartilage`) 무변경. (3) `is_doctor_filter` 통계 분기 ([api.py:3491-3527](../../app/routers/api.py:3491)) 무변경. (4) **부재 항목 (Doctor 별도 테이블 / Patient.doctor_id 등) 신설 안 함** 확인. |
| 주석/문서화 필요 지점 | `# COMPAT:` (alias 이중 키 / `_serialize_employee`). `# NOTE:` (role 분기 정책 — Employee 단일 테이블). `# TODO(post-19-P):` (`modules/doctors/` 별도 폴더 — EMR / `Patient.doctor_id` 도입 시). `# SAFETY:` (의사 가드 후속 — AI 응답에서 의사 정보 임의 생성 차단 패턴, M-36). |

### 3-9. 19-9 appointments 예약 service / repository 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-9 |
| 세션 이름 | appointments 분리 (마지막 + 가장 위험) |
| 목표 | (1) `app/modules/appointments/{router,service,repository,schemas,rules}.py` 신규 (availability 는 19-4 에서 분리됨). (2) 예약 CRUD + assign + split-code + approve + cancel ([api.py:1608-2057](../../app/routers/api.py:1608)) 위임. (3) `_check_version` / `_bump_version` (낙관적 락) → rules. (4) `_serialize_appointment` 이동. (5) FullCalendar event 형식 보존. |
| 수정 가능 범위 | (a) `app/modules/appointments/` 신규. (b) `app/routers/api.py` 의 appointments 핸들러 위임 → 제거. (c) `dosu_clinic.spec` 갱신. (d) 신규 응답 키 contract 테스트 (10 endpoint). (e) 신규 PUT/DELETE/409 contract (19-4 보강 결과 활용). |
| 수정 금지 범위 | `Appointment` / `TreatmentAssignment` ORM 컬럼 / `version` 컬럼 / `treatment_codes` JSON. m001~m013. AI action_leave 흐름 (19-13). FullCalendar event 형식. UI 무수정. |
| 선행 조건 | 19-8 완료 + Codex pass. **19-4 의 백엔드 차단 코드 + 19-5 leaves 분리 + 19-6 completion_rules 분리 + 19-7 patients 분리 + 19-8 staff 분리 모두 완료**. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_appointment_rules.py` (정방향 전환 후 — 19-4). `test_therapist_leave.py` (동상). 신규 응답 키 contract (10 endpoint). PyInstaller 53 tests. AI 하네스 6개. **`pytest tests -v` 전체 회귀 — 18-8 baseline 회귀 0**. |
| 유지해야 할 API/응답 key | `GET /api/appointments` (range 필수). `POST /api/appointments` / `PUT /api/appointments/{aid}` / `DELETE /api/appointments/{aid}` / `POST /api/appointments/{aid}/{assign,split-code,approve,revert-approve,cancel}`. `version` 필드 (낙관적 락) / `treatment_codes` JSON / `status` ENUM. FullCalendar event 형식. |
| 위험도 | **높음** — 의존성 가장 큼 (patients / staff / treatments / leaves / availability / completion_rules / sync). |
| rollback 기준 | (a) FullCalendar event 표시 깨짐. (b) 낙관적 락 409 응답 변경. (c) `treatment_codes` JSON 형식 변경. (d) approve / revert 흐름 깨짐. (e) assign role=doctor 강제 회귀. (f) 운영 DB 보호 5단계 회귀. (g) 5회 루프 실패. |
| Codex 검증 포인트 | (1) 응답 키 100% 보존. (2) `version` 낙관적 락 정책 무변경. (3) `_check_lunch_block` / 휴무 차단 / 충돌 검사 흐름 정합 (19-4 결과 통합). (4) AI action_leave / sms 흐름 무영향. (5) FullCalendar event 형식. |
| 주석/문서화 필요 지점 | `# COMPAT:` (응답 키 + version + treatment_codes JSON). `# NOTE:` (점심창 / 충돌 / 휴무 차단 — availability 모듈에서 호출). `# RISK:` (낙관적 락 TOCTOU / sync `ENTITY_MAP` 호환). `# TODO(19-13):` (AI action_leave 연결부 통합 시점). |

### 3-10. 19-10 sms 문자 대상 추출 / 템플릿 / provider 경계 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-10 |
| 세션 이름 | sms 분리 + 외부 HTTP provider 경계 + API key 마스킹 보존 |
| 목표 | (1) `app/modules/sms/{router,service,templates,provider,schemas}.py` 신규. (2) `_normalize_phone_for_sms` / `_is_valid_kr_mobile` / `_mask_phone_for_log` / `_sms_sanitize` ([api.py:3115-3160](../../app/routers/api.py:3115)) 이동. (3) 문자나라 외부 HTTP client → `provider.py` 경계 분리. (4) 자동 발송 트리거 ⊥ (appointments → sms ⊥) 보장. |
| 수정 가능 범위 | (a) `app/modules/sms/` 신규. (b) `app/routers/api.py` 의 sms 핸들러 위임. (c) `dosu_clinic.spec` 갱신. (d) 외부 HTTP client mock fixture. (e) 신규 응답 키 contract (C-2/C-3 보강). |
| 수정 금지 범위 | `SmsSetting` / `SmsLog` / `SmsTemplate` ORM 컬럼 / 시드 ([services/seed.py:56-63](../../app/services/seed.py:56)). m001~m013. AI sms_draft / sms_validate 흐름 ([app/services/ai/sms_draft.py](../../app/services/ai/sms_draft.py) / [validators.py](../../app/services/ai/validators.py)). 19-13 에서 별도 처리. |
| 선행 조건 | 19-9 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_sms_secret_masking.py` (API key / 전화번호 마스킹). `test_ai_sms_validate.py` + `test_ai_sms_draft.py` + `test_ai_sms_draft_hallucination.py` (AI 흐름 회귀). 신규 sms 응답 키 contract. 외부 HTTP mock 회귀. PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `GET/POST /api/sms/setting` / `GET /api/sms/tomorrow-targets` / `GET/POST/PUT/DELETE /api/sms/templates[/{tid}]` / `POST /api/sms/send`. `_serialize_sms_template` 응답 dict. AI `/api/ai/sms/{validate,draft}` 응답 키 보존. |
| 위험도 | 중간. |
| rollback 기준 | (a) API key 평문 / 마스킹 응답에 노출. (b) 전화번호 평문 로그 노출. (c) `tomorrow-targets` 대상자 추출 결과 변경. (d) 자동 발송 트리거 발생 (appointments → sms ⊥ 위반). (e) 외부 HTTP 호출 차단 깨짐. (f) 5회 루프 실패. |
| Codex 검증 포인트 | (1) `_sms_sanitize` 마스킹 패턴 보존. (2) `_mask_phone_for_log` 정책 보존. (3) 외부 HTTP mock 가 `provider.py` 경계에서만 호출. (4) 자동 발송 트리거 ⊥. (5) AI sms_draft 흐름 무영향. |
| 주석/문서화 필요 지점 | `# SAFETY:` (API key / 전화번호 마스킹 / 외부 HTTP 차단). `# COMPAT:` (sms 응답 키 / `_serialize_sms_template`). `# RISK:` (외부 HTTP timeout / retry / 응답 디코딩 `_smart_decode_response`). `# NOTE:` (자동 발송 트리거 ⊥ — appointments 와 분리 정책). |

### 3-11. 19-11 stats 통계 집계 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-11 |
| 세션 이름 | stats 8 endpoint + manual-counts + 엑셀 export 분리 |
| 목표 | (1) `app/modules/stats/{router,service,repository,schemas,aggregators}.py` 신규. (2) 8 GET endpoint + `POST /api/manual-counts` + 엑셀 export 위임. (3) `_resolve_stats_range` / `_date_list` / `_get_manual_treatment_rows` / `_get_manual_therapy_codes` 이동. (4) read-only 의존 — appointments / treatments / patients / leaves 호출만. |
| 수정 가능 범위 | (a) `app/modules/stats/` 신규. (b) `app/routers/api.py` 의 stats / manual-counts / export 핸들러 위임. (c) `dosu_clinic.spec` 갱신. (d) 신규 8 endpoint contract (C-7). (e) 엑셀 export 응답 contract. |
| 수정 금지 범위 | `ManualCount` / `Appointment` / `Patient` / `PatientTreatmentCount` ORM 컬럼. `_lighten_hex` / `_lighten_hex_inner` 색상 헬퍼 (UI 결합). m001~m013. |
| 선행 조건 | 19-10 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_stats_counts.py` (162줄). 신규 8 endpoint contract. 엑셀 export 응답 contract. PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `GET /api/stats/{by-therapist,manual-by-therapist,aggregate,daily-by-therapist,summary,by-hour,by-weekday,by-treatment,daily}`. `POST /api/manual-counts`. `GET /api/export/{manual-schedule,stats}.xlsx`. `is_doctor_filter` 분기 결과 ([api.py:3491-3527](../../app/routers/api.py:3491)). |
| 위험도 | 중간. |
| rollback 기준 | (a) 신환 (`is_new_patient`) 카운트 결과 변경. (b) 의사 필터 (`is_doctor_filter`) 분기 결과 변경. (c) ManualCount UNIQUE 제약 회귀. (d) `_get_manual_treatment_rows` 결과 변경 — appointments / sms / 엑셀 export 다중 의존. (e) 색상 hex 결과 변경 (UI 결합). (f) 5회 루프 실패. |
| Codex 검증 포인트 | (1) 8 endpoint 응답 키 100%. (2) `is_doctor_filter` 분기 결과 무변경. (3) `_get_manual_treatment_rows` / `_get_manual_therapy_codes` 결과 무변경 (다중 의존). (4) stats → 도메인 read-only (write ⊥, D-7 의존성). |
| 주석/문서화 필요 지점 | `# COMPAT:` (8 endpoint 응답 키). `# NOTE:` (`_get_manual_treatment_rows` 정책 — stats / appointments / 엑셀 다중 의존). `# RISK:` (색상 hex — UI CSS 의존). `# TODO(post-19-P):` (노쇼 별도 컬럼 — m014+ 도입 시). |

### 3-12. 19-12 admin / backup / audit / export_import 묶음 분리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-12 |
| 세션 이름 | admin / backup / audit / export_import 묶음 분리 (위험도 낮음) |
| 목표 | (1) `app/modules/admin/{router,service,schemas}.py` 신규 — `/api/admin/*` + `/api/about/*` + `/api/config/*` (settings 는 19-2 에서 분리됨). (2) `app/modules/backup/{router,service,schemas}.py` 신규 — `/api/backup/*` + `/api/restore` (UploadFile + integrity_check + atomic rename). (3) `app/modules/audit/{service,repository,schemas}.py` 신규 — `audit()` 시그니처 보존. (4) export_import 는 19-7 에서 분리됨 — 본 19-12 는 audit / admin / backup 만. |
| 수정 가능 범위 | (a) `app/modules/{admin,backup,audit}/` 신규. (b) `app/routers/api.py` 의 admin / about / config / backup / restore / audit-logs 핸들러 위임. (c) `app/services/backup.py` → `app/modules/backup/service.py` 이동 (타이머 스레드 보존). (d) `app/main.py` 의 `start_auto_backup()` import 경로 갱신. (e) `dosu_clinic.spec` 갱신. (f) 신규 contract (C-5 about/check-update). |
| 수정 금지 범위 | `AuditLog` / `SystemSetting` ORM 컬럼. `make_backup` / `restore_latest` / `restore_by_name` 정책. atomic rename + integrity_check. m001~m013. |
| 선행 조건 | 19-11 완료 + Codex pass. |
| 반드시 실행할 테스트 | `run_check.bat`. `test_admin_auth_required.py` / `test_db_restore_safety.py` / `test_graceful_shutdown.py` / `test_update_log.py` / `test_updater_invocation.py`. 신규 about/check-update 응답 contract. PyInstaller 53 tests. AI 하네스 6개. |
| 유지해야 할 API/응답 key | `/api/admin/{status,login,logout,change-password}` / `/api/about/{check-update,download-update,apply-update,update-log}` / `/api/config[/sync-secret]` / `/api/backup/{list,now,dir,restore-latest,restore-by-name}` / `/api/restore` / `/api/audit-logs`. `audit()` 시그니처 (`actor / action / entity_id / detail`). |
| 위험도 | 낮음~중간. |
| rollback 기준 | (a) PBKDF2 / 5회 잠금 / 8h 세션 정책 변경. (b) atomic rename + integrity_check 깨짐. (c) `audit()` 시그니처 변경 (모든 CUD 가 호출 — 회귀 多). (d) `start_auto_backup` daemon thread 정책 변경 (테스트는 conftest 람다 교체). (e) 5회 루프 실패. |
| Codex 검증 포인트 | (1) PBKDF2 + 잠금 정책 무변경. (2) `audit()` 시그니처 모든 CUD 호출지에서 정상 insert. (3) 백업 / 복구 atomic 정책. (4) updater.bat post-build 정책 (PyInstaller 53 tests). |
| 주석/문서화 필요 지점 | `# SAFETY:` (PBKDF2 + 세션 + 5회 잠금 / `audit` PII 원문 ⊥ / 200자 cap). `# COMPAT:` (admin / about / config 응답 키 / `audit()` 시그니처). `# RISK:` (atomic rename + integrity_check + daemon thread). `# NOTE:` (`audit()` 모든 CUD 호출 — 시그니처 변경 ⊥). |

### 3-13. 19-13 AI commands 와 기존 예약 / 휴무 / 문자 연결부 정리

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-13 |
| 세션 이름 | AI 라우터 + commands (action_leave) + sms_draft + manual_qa wrapper 분리 |
| 목표 | (1) `app/modules/ai/{router,manual_qa,sms_draft,health,logging,provider,commands/}.py` 신규. (2) `action_leave` (917줄) → `commands/action_leave.py`. (3) `rag/` `knowledge/` `vector/` 패키지는 18-1~18-6 구조 그대로 유지 — 19-P 추가 분리 불필요. (4) Safety 디렉토리화 (`pii.py` + `hallucination_guard.py` 분리). (5) local-first 보존 — `local_only` 모드에서 `len(provider.calls)==0` + `len(embedding_provider.calls)==0`. (6) AI 라우터 13 endpoint URL 그대로. |
| 수정 가능 범위 | (a) `app/modules/ai/` 신규. (b) `app/routers/ai.py` 의 13 endpoint 핸들러 위임. (c) `app/services/ai/*` 의 모듈을 `app/modules/ai/*` 로 이동 (wrapper 보존). (d) `dosu_clinic.spec` 갱신 (PyInstaller hidden imports 다수). (e) 신규 ai/action 응답 contract (C-4). |
| 수정 금지 범위 | `manual_qa.ask_manual_question(db, question, *, provider_override=)` 시그니처. `LOW_SCORE_THRESHOLD=2` / `HIGH=0.7` / `LOW=0.3` / `LLM_CALL=0.3` / `QUERY_MIN_CHARS=2` / `ERROR_DETAIL_DISPLAY_LIMIT=200` / `KNOWN_PROVIDERS=("openai","anthropic","local")`. `AiSetting` / `AiUsageLog` 컬럼. `KnowledgeChunk` / `KnowledgeVector` (m012/m013). |
| 선행 조건 | 19-12 완료 + Codex pass. **19-5 leaves 분리 완료 — `_upsert_employee_leave_core` 가 `leaves.service` 에 있음**. |
| 반드시 실행할 테스트 | `run_check.bat`. AI 하네스 전체 6개 + `test_local_only_mode.py` + `test_ai_assist_mode.py` + `test_ai_action_leave.py` + `test_ai_sms_validate.py` + `test_ai_sms_draft.py` + `test_ai_manual_qa.py` + `test_ai_health_*.py` + `test_ai_logging.py` + `test_ai_hallucination.py`. PyInstaller 53 tests. **신규 ai/action 응답 contract (C-4)**. |
| 유지해야 할 API/응답 key | `/api/ai/*` 13 endpoint URL + 33+ 응답 키 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9). action/parse/preview/execute 응답 키 (C-4 보강). |
| 위험도 | 중간 — local-first 보존 + 응답 키 33+ 보호. |
| rollback 기준 | (a) `local_only` 에서 `len(provider.calls) > 0` 또는 `len(embedding_provider.calls) > 0`. (b) 응답 키 33+ 중 하나라도 변경. (c) `ask_manual_question` 시그니처 변경. (d) RAG → 도메인 DB 임의 생성 (D-6 / F-5 위반). (e) AI action_leave 가 `leaves.service._upsert_employee_leave_core` 외 다른 경로로 휴무 등록. (f) HMAC + TOCTOU 정책 변경. (g) PII 마스킹 / sha256 / 200자 cap 정책 변경. (h) 5회 루프 실패. |
| Codex 검증 포인트 | (1) AI/RAG → 도메인 ⊥ (D-6 / F-5 / §7-2-B). (2) 33+ 응답 키 셋. (3) 임계치 상수 (`LOW_SCORE_THRESHOLD`/`HIGH`/`LOW`/`LLM_CALL`/`QUERY_MIN_CHARS`) 무변경. (4) `_block_sdk_modules` 정책 보존. (5) `manual60=1` 정책 (treatments) 와 무관 — AI 응답에 영향 X. |
| 주석/문서화 필요 지점 | `# SAFETY:` (PII 마스킹 + sha256 + 200자 cap + `_block_sdk_modules` + AI ⊥ 도메인 + 의사 가드 후속 M-36). `# COMPAT:` (33+ 응답 키 + `ask_manual_question` 시그니처). `# NOTE:` (임계치 상수 — 변경은 별도 결정 + eval 후). `# RISK:` (HMAC + TOCTOU — action_leave). `# TODO(post-19-P):` (의사 가드 보강 — `_RE_MEDICAL_CLAIM` / `_RE_EXECUTION_CLAIM` 패턴 추가). |

### 3-14. 19-14 전체 회귀 테스트 / PyInstaller 검증 (종료 게이트)

| 항목 | 값 |
|---|---|
| 세션 번호 | 19-14 |
| 세션 이름 | 19-P 종료 게이트 — 전체 회귀 + PyInstaller 빌드 + exe smoke |
| 목표 | (1) `pytest tests -v` 전체 회귀 — 18-8 baseline (529 passed, 1 skipped, 7 xfailed) → **19-P 후 baseline (예상: 529+ passed, 1 skipped, 0~3 xfailed — `xfail` 7건 중 4 leaves + 3 appointments 가 19-4 / 19-5 에서 정방향 전환되면 0)**. (2) `tests/test_pyinstaller_hidden_imports.py` 53 tests + 신설 모듈 17→다수 추가. (3) **사용자 명시 승인 시** 실제 PyInstaller 빌드 (`pyinstaller --noconfirm dosu_clinic.spec`) — CLAUDE.md 배포 규칙 정합. (4) exe smoke 5 endpoint (18-8 입증 기준). (5) [docs/releases/19_refactor_final_checklist.md](../releases/19_refactor_final_checklist.md) 신설 (사용자 수동 확인 항목). |
| 수정 가능 범위 | (a) `dosu_clinic.spec` hidden imports 최종 갱신. (b) `versions/INDEX.txt` / `CHANGELOG.txt` / `VERSION.txt` / `app/config.py` `APP_VERSION` 갱신 (사용자 승인 시). (c) [docs/releases/19_refactor_final_checklist.md](../releases/19_refactor_final_checklist.md) 신설. (d) 19-P 종료 코덱스 검증 요청서. |
| 수정 금지 범위 | 본 종료 게이트 단계에서 **신규 코드 분리 ⊥** (이미 19-1~13 에서 완료). 응답 키 / DB schema / UI 무수정. |
| 선행 조건 | 19-1 ~ 19-13 모두 완료 + 각 단계 Codex pass. |
| 반드시 실행할 테스트 | `pytest tests -v` 전체. `run_check.bat`. PyInstaller 53+ tests. **사용자 승인 시** 실제 빌드 + exe smoke. |
| 유지해야 할 API/응답 key | 33+ 키 셋 + 비-AI 응답 키 100% (19-1~13 누적 보호 결과). |
| 위험도 | 낮음 (검증) / **높음** (사용자 승인 시 빌드 — 시간 소요 + 배포 가능 산출물). |
| rollback 기준 | (a) 18-8 baseline 회귀. (b) PyInstaller 빌드 실패. (c) exe smoke 5 endpoint 중 하나라도 실패. (d) 응답 키 33+ 중 하나라도 변경. |
| Codex 검증 포인트 | (1) 19-P 후 baseline 통과. (2) PyInstaller 53+ tests + 실제 빌드 (사용자 승인 시) + exe smoke. (3) [docs/releases/19_refactor_final_checklist.md](../releases/19_refactor_final_checklist.md) 사용자 수동 확인 항목 정합. |
| 주석/문서화 필요 지점 | 본 세션은 신규 코드 분리 X — 신규 주석 0. 19-1~13 누적 결과 검증만. |

---

## 4. 세션별 주석 / 문서화 기준

> 본 19-P-6 은 코드 미수정 — 본 §4 는 19-1~13 실제 코드 리팩토링 세션에 적용할 *기준 표*.
> 19-P-3 §0-2 + 19-P-4 §7 + 19-P-5 §7 통합 정합.

### 4-1. 적용 기준 (19-1~13 모든 세션 공통)

| # | 기준 | 적용 |
|---|---|---|
| D-1 | 새로 생성/분리하는 파일에 파일 상단 docstring 추가 | router.py / service.py / repository.py / schemas.py / rules.py / availability.py / completion_rules.py / view_models.py / aggregators.py / templates.py / provider.py 등 — 1~3줄 한국어 docstring (모듈 책임 + 의존성 방향). |
| D-2 | 새로 분리하는 주요 service / rules / repository 함수에 함수 docstring 추가 | 공개 함수 (`def public_xxx`) 한정 — 1~2줄 (입력 / 출력 / 부작용). private 함수 (`_private_xxx`) 는 의도가 비-자명할 때만. |
| D-3 | 기존 API / UI 호환 wrapper 에 `# COMPAT:` 주석 추가 | wrapper 함수, 호환 alias, response dict 빌더, sync `ENTITY_MAP` 키, manual_qa wrapper 시그니처. |
| D-4 | 개인정보 / 운영DB / 외부 API 차단 부분에 `# SAFETY:` 주석 추가 | `pii.scan`, `audit`, `AiUsageLog`, masking 함수, `_block_sdk_modules`, `db_guard`, `check_db_path`. |
| D-5 | 휴무 차단 / 오전·오후 반차 / 완료체크 / 통계 집계 / 문자 대상 추출 등 업무 규칙에 `# NOTE:` 또는 `# RISK:` 주석 추가 | 점심창, 충돌, 휴무 차단, 반차, `manual60=1`, `_doctor_codes_set`, `_get_manual_treatment_rows`, 임계치 상수, reindex lock, atomic rename, HMAC TOCTOU, `_upsert_employee_leave_core`. |
| D-6 | TODO 는 반드시 세션 번호 또는 제거 조건 포함 | `# TODO(19-9):` (wrapper 제거 — appointments service 통합 후) / `# TODO(post-19-P):` (`modules/notes/` 통합 / `/api/health` 신설 / 의사 가드 M-36). |
| D-7 | 의미 없는 모든 줄 주석 ⊥ | `# Initialize x` / `# Loop through y` 같은 자명한 주석 ⊥. **역할 / 경계 / 주의사항 중심**. |
| D-8 | 주석 작성 때문에 기능 동작 변경 ⊥ | 주석은 *기록* 만 — 코드 흐름 변경 X. |

### 4-2. 권장 태그 정의

| 태그 | 의미 | 예시 위치 |
|---|---|---|
| `# COMPAT:` | 기존 API / UI 호환성 유지 | `/api/therapist-leaves` 이중 키 / `manual_qa` wrapper / 응답 dict 빌더 / sync `ENTITY_MAP` |
| `# SAFETY:` | 개인정보 / 운영 DB / 외부 API 차단 | `pii.scan` / `_block_sdk_modules` / `db_guard` / `check_db_path` / `_sms_sanitize` / PBKDF2 / api_key 비노출 |
| `# NOTE:` | 설계 의도 설명 | 점심창 / `manual60=1` / role 분기 / `_doctor_codes_set` / 임계치 상수 |
| `# RISK:` | 변경 시 위험한 업무 규칙 | 낙관적 락 TOCTOU / HMAC + TOCTOU / atomic rename / reindex lock / `ENTITY_MAP` |
| `# TODO(19-x):` | 후속 세션 작업 | `# TODO(19-9): wrapper 제거 — appointments service 통합 후` |
| `# TEMP:` | 임시 처리, 제거 조건 필수 | `# TEMP: 19-9 wrapper 제거 시 본 import 도 제거` (제거 조건 명시 필수) |

### 4-3. 19-1~13 세션별 주석 카테고리 매트릭스

> 각 세션의 §3 표 "주석/문서화 필요 지점" 행과 동기. 본 §4-3 은 통합 인덱스.

| 세션 | COMPAT | SAFETY | NOTE | RISK | TODO/TEMP |
|---|---|---|---|---|---|
| 19-1 core | config / database / auth wrapper | PBKDF2 + 세션 + 잠금 | `get_db_path` `DOSU_DB_PATH` 우선 |  | `TODO(19-2):` feature_flags 통합 |
| 19-2 settings/feature_flags | system-settings 응답 키 |  | `auto_backup_keep_count` / `manual_slot_limit` |  | `TODO(post-19-P):` `/api/health` 신설 |
| 19-3 calendar | FullCalendar event 필드 |  | view-model = read-only |  | `TODO(post-19-P):` UI 분리 |
| 19-4 availability | 응답 키 + version |  | 점심창 / 도수 중복 / 휴무 차단 spec | 낙관적 락 TOCTOU | `TODO(19-9):` wrapper 제거 |
| 19-5 leaves | alias 이중 키 | PII 마스킹 (audit) | `leave_type` / `leave_kind` DB 표준 | HMAC + TOCTOU |  |
| 19-6 treatments/completion | 응답 키 + done_count |  | `manual60=1` 정책 | `count_increment` 변경 시 회귀 多 | `TODO(19-9):` wrapper 제거 |
| 19-7 patients/notes | counts dict 키 | PII 비노출 | `_check_patient_duplicate` | data-convert 트랜잭션 | `TODO(post-19-P):` `modules/notes/` |
| 19-8 staff | alias / `_serialize_employee` | 의사 가드 후속 M-36 | role 분기 정책 |  | `TODO(post-19-P):` `modules/doctors/` |
| 19-9 appointments | 응답 키 + version + treatment_codes | 운영 DB 보호 | 점심창 / 충돌 / 휴무 차단 | 낙관적 락 / sync `ENTITY_MAP` | `TODO(19-13):` AI 연결부 |
| 19-10 sms | sms 응답 키 | API key + 전화번호 마스킹 | 자동 발송 트리거 ⊥ | 외부 HTTP timeout / retry |  |
| 19-11 stats | 8 endpoint 응답 키 |  | `_get_manual_treatment_rows` 다중 의존 | 색상 hex UI 결합 | `TODO(post-19-P):` 노쇼 컬럼 |
| 19-12 admin/backup/audit | admin 응답 키 / `audit()` 시그니처 | PBKDF2 + audit PII ⊥ | `audit()` 모든 CUD 호출 | atomic rename + daemon thread |  |
| 19-13 AI | 33+ 응답 키 / `ask_manual_question` | `_block_sdk_modules` + AI ⊥ 도메인 + 의사 가드 후속 | 임계치 상수 | HMAC + TOCTOU | `TODO(post-19-P):` 의사 가드 M-36 |

---

## 5. 19-0 기준 테스트 / 하네스 재확인 계획

### 5-1. 실행 명령

| # | 명령 | 검증 |
|---|---|---|
| 1 | `venv\Scripts\python.exe -m pytest tests -v` | 전체 회귀 — 18-8 baseline (529 passed, 1 skipped, 7 xfailed) 일치. |
| 2 | `venv\Scripts\python.exe -m ruff check app tests scripts` | lint — `app/**` per-file-ignores 보존. |
| 3 | `venv\Scripts\python.exe scripts/check_db_path.py` | 운영 DB 경로 안전 검사 (머지 게이트). |
| 4 | (개별) `pytest tests/test_appointment_rules.py tests/test_employee_leave_*.py tests/test_therapist_leave.py tests/test_stats_counts.py tests/test_sms_secret_masking.py -v` | 기존 예약 / 휴무 / 통계 / 문자 회귀 테스트. |
| 5 | (개별) `pytest tests/test_full_harness.py tests/test_ai_full_harness.py tests/test_rag_pipeline.py tests/test_rag_safety.py tests/test_ai_safety_harness.py tests/test_ai_chunker_harness.py tests/test_ai_reindex_harness.py tests/test_ai_vector_harness.py tests/test_hybrid_retriever.py tests/test_ai_health_*.py tests/test_admin_ui_smoke.py -v` | AI / RAG 전체 하네스. |
| 6 | (개별) `pytest tests/test_ai_manual_rag_contract.py tests/test_ai_contract_manual.py -v` | API contract 테스트 (manual_qa 5키 등). |
| 7 | (자동 — conftest) `tests/harness/db_guard.assert_safe_db_path()` | 운영 DB 보호 검사 (import-time 1회 + session fixture 1회). |
| 8 | (자동 — conftest) `_block_sdk_modules` | 외부 API 호출 금지 검사 (openai / anthropic SDK 클래스 RuntimeError 교체). |
| 9 | `git status --short` + `git diff --stat bcd74a7` | 워크트리 정리 — 18-0~18-8 변경분 main 머지 또는 별도 commit (사용자 승인 후). |

### 5-2. 19-0 통과 기준 (= 19-1 진입 게이트)

- [ ] §5-1 명령 1~8 모두 통과 (18-8 baseline 일치).
- [ ] §5-1 명령 9 워크트리 cleanliness — `app/**` / `tests/**` / `app/migrations/**` / spec / `requirements*.txt` / UI 의 dirty 변경분 0 또는 commit 완료.
- [ ] 19-P-5 §4 보강 9개 항목 (휴무 차단 백엔드 / 통계 8 endpoint / 문자 응답 키 / 비-AI contract / 환자 검색·메모 / 의사 분기 / about/check-update / data-convert / ai/action) 인덱싱 완료 — 각 도메인 분리 직전 보강 시점 확정.
- [ ] 19-P-3 §31 우선순위 + 19-P-4 §6 분리 순서와 본 §2 추천 순서 정합.

---

## 6. 위험도별 진행 원칙

### 6-1. 낮은 위험

> 19-1 core / 19-2 settings·feature_flags·health (분류) / 19-3 calendar (view-model only 또는 패스) / 19-12 admin·audit 일부 / 19-14 검증.

원칙:
- wrapper 패턴 — 신규 폴더 + 기존 함수 위임 → 응답 검증 → 기존 코드 제거.
- 응답 키 변경 0 입증 (dict 단위 비교).
- 5회 루프 안에서 마무리 가능.
- Codex 검증 후 다음 세션.

### 6-2. 중간 위험

> 19-4 availability / 19-6 treatments·completion_rules / 19-7 patients·notes·data-convert / 19-8 staff / 19-10 sms / 19-11 stats / 19-12 backup / 19-13 AI commands 분리.

원칙 (낮은 위험 + 추가):
- **분리 직전 contract 테스트 신규 추가** (응답 키 잠금) — 19-P-5 §4 보강 9개 항목 도메인별로 적용.
- 분리 직후 회귀 테스트 통과 확인 (18-8 baseline 회귀 0).
- PyInstaller 53 tests 갱신과 동시 — 신설 모듈 hidden imports 등록.
- Codex 검증 시 의존성 그래프 (19-P-4 §2~§5) 정합 확인.

### 6-3. 높은 위험

> 19-5 leaves (`xfail` 4건 정방향 전환 + `_upsert_employee_leave_core` 단일 진실원천) / 19-9 appointments (마지막 + 의존성 가장 큼) / completion_rules 정책 변경 / backup·restore (atomic rename + daemon thread) / AI commands 가 DB 변경과 연결되는 부분 (action_leave).

원칙 (중간 위험 + 추가):
- **관련 테스트 보강 후 진행** — 19-4 의 백엔드 차단 코드 + `xfail` 정방향 전환이 19-5 진입 전제.
- **wrapper / adaptor 먼저 생성** — 한 번에 통째 이동 ⊥. 신규 폴더에 wrapper → 호출지 한 줄씩 전환 → 마지막에 wrapper 제거.
- **기존 endpoint 유지** — URL 변경 0, FastAPI APIRouter `prefix` 만 모듈별 재할당.
- **Codex 검증 후 다음 단계 진행** — 5회 루프 안에서 통과 못 하면 rollback 우선 검토.
- 19-9 appointments 진입 직전: 19-4 ~ 19-8 모두 완료 + 각 단계 Codex pass + `pytest tests -v` 전체 회귀 18-8 baseline 일치.

---

## 7. rollback 기준

> 19-P-5 §6-E + 19-P-2 P-6 정합. 각 세션에서 아래 문제 발생 시 rollback 또는 재작성 검토.

| # | rollback 트리거 | 검증 위치 |
|---|---|---|
| RB-1 | 기존 API 응답 key 변경 (33+ 키 셋 + 비-AI alias) | API contract 테스트 + dict 단위 비교 |
| RB-2 | 예약 생성 / 수정 / 삭제 결과 변경 | `test_appointment_rules.py` + 신규 PUT/DELETE/409 contract |
| RB-3 | 휴무 차단 로직 깨짐 (`am`/`pm`/`full`) | `test_therapist_leave.py` (19-4 정방향 전환 후) |
| RB-4 | 완료체크 카운트 방식 변경 (`manual60=1` / done_count ±N) | `test_appointment_rules.py` + `test_stats_counts.py` + `manual60` 직접 단언 |
| RB-5 | 문자 대상 추출 오류 (`tomorrow-targets`) | 신규 sms contract (C-2) |
| RB-6 | 통계 집계 기준 변경 (`is_doctor_filter` / `_get_manual_treatment_rows` / 신환 카운트) | `test_stats_counts.py` + 신규 8 endpoint contract (C-7) |
| RB-7 | 운영 DB 접근 위험 발생 | `scripts/check_db_path.py` + `tests/harness/db_guard.assert_safe_db_path()` |
| RB-8 | 외부 API 호출 발생 | `_block_sdk_modules` + `len(provider.calls) > 0` 단언 (local_only) |
| RB-9 | 5회 수정 루프 실패 | `reports/ai_dev_loop/latest_failure_report.md` 작성 + 사용자 결정 |
| RB-10 | PyInstaller 실행 불가 | `tests/test_pyinstaller_hidden_imports.py` 53 tests + (사용자 승인 시) 실제 빌드 |

### 7-1. rollback 절차

1. **부분 수정 즉시 중단** — 땜질식 수정 ⊥.
2. `reports/ai_dev_loop/latest_failure_report.md` + `reports/ai_dev_loop/{SESSION_NAME}_failure_report.md` 작성 (시도 회차별 가설 / 변경 / 결과 + 마지막 테스트 출력 + 코드 재작성 / 설계 재검토 권고).
3. `git status` / `git stash` / `git checkout -- <files>` 등으로 변경 되돌리기 (사용자 승인 후).
4. 사용자에게 보고 + 재작성 / 재설계 결정 대기.
5. 재시도 시 본 §7-1 사이클 반복.

---

## 8. Codex 검증 운영 방식

> 19-P-5 §8 + [docs/AI_WORKING_RULES.md §4](../AI_WORKING_RULES.md) + [docs/ai_code_session_protocol.md §7](../ai_code_session_protocol.md) 정합.

### 8-1. 각 19-x 세션 완료 후 Claude Code 가 작성

- [reports/refactor/latest_codex_review_request.md](../../reports/refactor/latest_codex_review_request.md) (덮어쓰기 — Codex 진입점)
- [reports/refactor/{SESSION_NAME}_codex_review_request.md](../../reports/refactor/) (영구 보존본)

### 8-2. 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

### 8-3. Codex 검증 결과 기록 위치

- [reports/refactor/latest_codex_review.md](../../reports/refactor/latest_codex_review.md) (덮어쓰기 — 다음 세션 진입점)
- [reports/refactor/{SESSION_NAME}_codex_review.md](../../reports/refactor/) (영구 보존본)

### 8-4. Codex 판정별 다음 단계

| 판정 | 다음 단계 |
|---|---|
| **pass** | 다음 세션 진입 가능. |
| **pass with caveat** | caveat 가 *진입 차단 사항* 인지 *동기화 권고* 인지 확인. 진입 차단 X 면 다음 세션 진입 가능 + caveat 는 다음 r2 / 별도 세션에서 동기화. |
| **fail** | 본 세션 r2 / r3 / ... 보정 후 Codex 재검증. 5회 안에 통과 못 하면 rollback 검토. |

### 8-5. Codex 검증 게이트 정책

- Claude Code 자체 통과 = **최종 완료 X**.
- Codex 검증 = **다음 세션 진입 필수 게이트**.
- Codex 결과가 "재작업 필요" 면 [docs/ai_code_session_protocol.md §4](../ai_code_session_protocol.md) 1~10 단계 다시 실행.

---

## 8-A. 각 19-x 세션 공통 완료 조건 (19-C 연결)

> 19-C [실제 기능 작동확인 체크리스트](19_refactor_function_verification_checklist.md) 신설 후 본 §8-A 추가. §3-0 ~ §3-14 의 각 세션 표 외에 *모든 세션 공통* 으로 충족해야 할 완료 조건 정리.

### 8-A-1. 공통 완료 조건 10개 (모든 19-x 세션)

| # | 항목 | 검증 |
|---|---|---|
| G-1 | 관련 자동 테스트 통과 | `run_check.bat` + `pytest tests -v` (또는 도메인별) + ruff + check_db_path 모두 통과. |
| G-2 | 관련 실제 기능 작동확인 수행 | [19-C §18 세션별 영향 범위 매핑](19_refactor_function_verification_checklist.md) 기준 영향 항목 모두 확인. |
| G-3 | 수동 확인 필요 항목 기록 | UI / FullCalendar / 문자 복사 / PyInstaller exe 등 자동 검증 부재 항목 명시. |
| G-4 | 운영 DB / 외부 API / 실제 문자 발송 없음 확인 | `check_db_path.py` + `_block_sdk_modules` + sms provider mock 모두 활성. |
| G-5 | 개인정보 / API key 원문 노출 없음 확인 | 응답 / 로그 / AI prompt grep — 환자 / API key 원문 부재. |
| G-6 | [reports/refactor/{SESSION_NAME}_test_report.md](../../reports/refactor/) 작성 | [19-C §2-2 형식](19_refactor_function_verification_checklist.md) 7대 분류 모두 포함. |
| G-7 | [reports/refactor/{SESSION_NAME}_fix_summary.md](../../reports/refactor/) 작성 | 변경 파일 목록 + 파일별 변경 요약 + 의도 + 이유. |
| G-8 | [reports/refactor/{SESSION_NAME}_codex_review_request.md](../../reports/refactor/) + `latest_codex_review_request.md` 작성 | 본 §8-A-2 의 14 항목 모두 포함. |
| G-9 | Codex 검증 통과 | pass 또는 pass with caveat (yes 진입 가능). |
| G-10 | 다음 세션 진행 가능 판단 | yes / no + 근거. no 면 본 §7 (rollback) 또는 보강 후 재검증. |

### 8-A-2. Codex 검증 요청 문서 공통 항목 (모든 19-x 세션)

> 본 19-P-9 [§9-2 14 항목](19_refactor_checklists.md) + 19-C 추가 항목.

| # | 항목 |
|---|---|
| 1 | 세션 이름 (`19-x_<domain>`) |
| 2 | 작업 목표 (한 문장) |
| 3 | 변경 파일 목록 (신규 / 수정 / 삭제 분류) |
| 4 | 수정 가능 범위 |
| 5 | 수정 금지 범위 |
| 6 | 실제 변경 요약 (이동한 로직 / wrapper / 새 contract 테스트) |
| 7 | 실행한 테스트 (run_check.bat / pytest / AI 하네스 / PyInstaller / S-1~S-5) |
| 8 | 테스트 결과 요약 (529 passed baseline 또는 갱신값) |
| 9 | 수정 루프 횟수 (1 ~ 5) |
| **10** | **실제 기능 작동확인 수행 여부 (19-C §3 ~ §17 영향 범위 기준)** |
| **11** | **자동 테스트로 확인한 항목** |
| **12** | **테스트 클라이언트 / API 호출로 확인한 항목** |
| **13** | **수동 확인 필요 항목** |
| **14** | **이번 세션 영향 없음으로 판단한 항목** |
| **15** | **확인하지 못한 항목과 이유** |
| 16 | 운영 DB 접근 여부 |
| 17 | 외부 API 호출 여부 |
| 18 | 실제 문자 발송 여부 |
| 19 | 개인정보 / API key 원문 노출 여부 |
| 20 | 기존 API 응답 key 유지 여부 |
| 21 | 기능 작동확인 누락 여부 |
| 22 | 다음 세션 진행 가능 여부 (yes / no + 근거) |

### 8-A-3. 세션별 실제 기능 확인 범위 (간단 매핑)

> [19-C §18](19_refactor_function_verification_checklist.md) 인덱스 요약. 각 세션 작업 시 해당 항목만 확인.

| 세션 | 실제 기능 확인 범위 |
|---|---|
| **19-0** | 공통 (운영 DB 보호 / 외부 API 차단 / 18-8 baseline 유지). |
| **19-1** core | 공통 (응답 키 0 변경 / 운영 DB 보호). |
| **19-2** settings/feature_flags/health | API key 비노출 / health 응답 / AI 모드 분기. |
| **19-3** calendar (view-model) | 캘린더 표시 / FullCalendar event / UI 무수정 (수동 확인). |
| **19-4** availability | 예약 생성 / 수정 / 충돌 / 휴무차단 / 반차차단 / 점심창 / devtools 우회 차단. |
| **19-5** leaves | 휴무 등록 (full/am/pm) / 조회 / 삭제 / 표시 / 예약차단 / `_upsert_employee_leave_core` 단일 진실원천 / AI action_leave 회귀. |
| **19-6** treatments / completion_rules | 치료항목 / 완료체크 / 개별 카운트 / `manual60=1` 보존 / 시간 가중치 ⊥. |
| **19-7** patients / notes / data-convert | 환자검색 / 신환 / 메모 (당일 vs 지속) / 개인정보 비노출 / data-convert 트랜잭션. |
| **19-8** staff | 치료사 활성 / 색상 / `can_eswt` / `can_manual` / alias 이중 키 / **F-1 의사 부재 단정 ⊥** / 의사 가드 후속. |
| **19-9** appointments | 예약 생성 / 수정 / 삭제 / 조회 / 충돌 / 낙관적 락 / FullCalendar event / approve · revert. |
| **19-10** sms | 문자대상 / 템플릿 / **실제발송 없음** / API key 마스킹 / 자동 발송 트리거 ⊥. |
| **19-11** stats | 기존 통계 집계 결과 유지 / 8 endpoint 응답 키 / read-only 정책 / `is_doctor_filter` / `_get_manual_treatment_rows`. |
| **19-12** admin / backup / audit | API key 비노출 / 백업 atomic rename / 운영 DB 보호 / `audit()` 시그니처. |
| **19-13** AI commands | 승인 없는 실행 없음 / Safety → Preview → Execute / `local_only` provider 호출 0 / 33+ 응답 키 / HMAC + TOCTOU. |
| **19-14** final | 전체 기능 + PyInstaller 빌드 (사용자 승인 시) + exe smoke. |

### 8-A-4. 진행 순서 (모든 19-x 세션 공통)

> [docs/ai_code_session_protocol.md](../ai_code_session_protocol.md) + 본 19-P-9 [§1 ~ §8](19_refactor_checklists.md) + 19-C 통합.

1. 이전 세션 Codex 검증 결과 확인 ([reports/refactor/{이전 세션}_codex_review.md](../../reports/refactor/) 영구 보존본).
2. 해당 세션 작업 범위 확인 (§3-N 표 + 사용자 지시문).
3. 수정 금지 범위 확인.
4. 코드 수정 전 관련 기능 작동 기준 확인 ([19-C §18 세션별 영향 범위 매핑](19_refactor_function_verification_checklist.md)).
5. 작은 범위로 코드 수정.
6. 자동 테스트 실행 (`run_check.bat` + 도메인별 pytest + AI 하네스).
7. 실제 기능 작동확인 수행 ([19-C §4 ~ §17 영향 항목](19_refactor_function_verification_checklist.md)).
8. 실패 시 최대 5회 수정 루프 (T-7 / 19-P-9 §7).
9. 5회 실패 시 [failure report](../../reports/ai_dev_loop/) 작성 후 중단.
10. [reports/refactor/{SESSION_NAME}_test_report.md](../../reports/refactor/) 작성 + `latest_test_report.md` 동기.
11. [reports/refactor/{SESSION_NAME}_fix_summary.md](../../reports/refactor/) 작성 + `latest_fix_summary.md` 동기.
12. [reports/refactor/{SESSION_NAME}_codex_review_request.md](../../reports/refactor/) + `latest_codex_review_request.md` 작성 (본 §8-A-2 22 항목 포함).
13. Codex 검증 요청 (사용자 → Codex).
14. Codex 검증 결과 문서 확인 ([reports/refactor/{SESSION_NAME}_codex_review.md](../../reports/refactor/)).
15. 치명 / 중간 위험 없을 때 다음 세션 진행.

### 8-A-5. 필수 원칙

- [ ] **Codex 검증 전 다음 세션 진행 ⊥** (R-10 / DEC-T 정합).
- [ ] **기능 작동확인 누락 시 다음 세션 진행 보류** ([19-C §1 V-1 / V-7 / V-8](19_refactor_function_verification_checklist.md) 정합).
- [ ] **자동 테스트만 통과하고 실제 기능 확인이 누락되면 완료로 보지 않음** (G-2 / G-6 누락 시 Codex 가 *재작업 필요* 판정 가능).

---

## 9. 보류 / 후속 검토 항목

> 19-P-2 §2-2 + 19-P-3 §31 post-19-P + 19-P-5 §5-3 정합.
> **현재 기능이 없는 항목은 실제 구현 대상으로 단정하지 말고 "후속 검토" 로 표시**.

| # | 항목 | 분류 | 현재 상태 | post-19-P 도입 시 동반 작업 |
|---|---|---|---|---|
| F-1 | doctors / medical_staff (별도 모듈) | 후속 검토 (M-31) | Employee `role="doctor"` + Treatment `role="doctor"` 얇은 분기만 (19-8 staff 안에 통합). 별도 폴더 부재. | EMR 도입 시 `modules/doctors/` 신설 + m014+ 마이그레이션 (`Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule`) + 응답 키 추가. |
| F-2 | recurring_appointments (반복 예약) | 후속 검토 | 현재 미구현. | m014+ 컬럼 / 응답 키 / UI 추가. |
| F-3 | resources (치료실 / 장비 / 자원) | 후속 검토 (M-33) | 현재 미구현. | `modules/resources/` + m014+ + UI. |
| F-4 | notifications (알림) | 후속 검토 | 현재 미구현. | 내부 알림 / reindex 실패 / 백업 실패 알림 — 별도 결정. |
| F-5 | printing / documents (출력물) | 후속 검토 | 현재 미구현. | 예약표 / 통계표 / 환자 안내문 출력 — 별도 결정. |
| F-6 | export_import 확장 (CSV / EMR import) | 후속 검토 | 엑셀 export 2개 + 환자 엑셀 import (`_dc_*`) 만 — 19-7 에서 분리 대상. CSV / 비트U차트 / EMR import 부재. | post-19-P 에서 `modules/export_import/` 확장. |
| F-7 | privacy / retention 고도화 | 후속 검토 | PII 마스킹 + sha256 + 200자 cap 보존. 보존 정책 (오래된 AI 로그 삭제 / 환자정보 비활성화) 부재. | post-19-P 에서 `modules/audit/` 보존 정책 추가. |
| F-8 | audit / logs 고도화 | 후속 검토 | `audit()` + AuditLog 응답 / `audit-logs` endpoint 보존. 무한 보존 정책. | post-19-P 에서 보존 기간 / 자동 정리 정책 추가. |
| F-9 | 비트U차트 / EMR 연동 | 후속 검토 | 현재 미구현. | EMR 연동 도입 시 F-1 / F-2 / F-3 / F-6 모두 동반. |
| F-10 | 노쇼 별도 필드 | 후속 검토 | 현재 `status="canceled"` 만. 노쇼 별도 필드 부재. | m014+ 컬럼 추가 + 통계 분기 + UI. |
| F-11 | 권한 다중 등급 (직원 / 관리자 분리) | 후속 검토 | 현재 admin 단일 등급만. | `app/core/security.py` 다중 role 추가 + UI 분기. |
| F-12 | `modules/notes/` 통합 (지속 메모 vs 당일 메모) | 후속 검토 | 19-7 에서 `modules/patients/notes_service.py` 안에 두고, 통합은 post-19-P. | 정책 결정 후 `modules/notes/` 신설. |
| F-13 | `/api/health` 신설 (M-28) | 후속 검토 | 현재 부재 (`/api/admin/status` 가 인증 상태만). `/api/ai/health` 는 별도. | `modules/health/{router,service,diagnostics}.py` 신설. |
| F-14 | calendar / schedule_view 통합 | 후속 검토 | 19-3 에서 view-model only 검토. UI 분리는 19-P 비-목표. | post-19-P 에서 main.html JS 외부 분리 + `modules/calendar/` 폴더. |
| F-15 | AI 의사 정보 임의 생성 차단 (의사 가드 M-36) | 후속 검토 | 현재 RAG hallucination guard 부분. 의사 단정 표현 (`담당의는 X 입니다` / `Y 의사 진료실 ...`) 차단 패턴 부재. | `app/modules/ai/safety/hallucination_guard.py` 에 패턴 추가. F-1 동반 시. |

### 9-1. 후속 검토 항목의 단정 금지 정책

- 각 19-x 세션에서 본 §9 의 항목을 **실제 구현된 것처럼 단정하지 않는다**.
- 응답 키 / 모델 / endpoint 부재를 코드 / docstring / 주석에 그대로 반영.
- AI / RAG 응답이 본 §9 의 부재 항목을 *DB 근거 없이* 생성하는 것을 차단 (RAG hallucination guard + F-15 의사 가드 후속).
- 본 19-P 기간 내 본 §9 항목 중 어느 것도 도입 X — 19-9 appointments 분리에서도 `Patient.doctor_id` / `Doctor.schedule` / `Order` / `Prescription` 컬럼 신설 ⊥.

---

## 10. 종합

- **롤아웃 원칙 R-1 ~ R-14** = 기능 변경 X / 한 세션 한 모듈 / 응답 키 33+ 보존 / UI 무수정 / DB schema 보존 / 테스트 먼저 / 5회 루프 / Codex 게이트 / 운영 DB ⊥ / 외부 API ⊥ / local-first / per-file-ignores / `manual60=1` / 후속 검토 단정 X.
- **추천 순서** (r2 보정 — Codex r1 caveat 1번 정합) = **19-1 ~ 19-14 의 14개 리팩토링 세션 + 19-0 기준 테스트 baseline = 합계 15개 실행 세션** (+ 19-P 구조 계획 메타). 흐름: 19-P (구조계획 완료) → 19-0 (baseline 재고정) → 19-1 (core) → 19-2 (settings/feature_flags) → 19-3 (calendar view-model) → 19-4 (availability + 백엔드 차단 보강) → 19-5 (leaves) → 19-6 (treatments/completion) → 19-7 (patients/notes/data-convert) → 19-8 (staff) → 19-9 (appointments — 마지막) → 19-10 (sms) → 19-11 (stats) → 19-12 (admin/backup/audit) → 19-13 (AI commands) → 19-14 (전체 회귀 + PyInstaller). **appointments (19-9) 위치** = 실행 세션 15개 중 11/15 번째 (= 19-0 부터 11번째 — 사용자 §2 의 "예약 마지막 권장" 정합).
- **세션별 계획 표 12 컬럼** = 세션 번호 / 이름 / 목표 / 수정 가능 / 금지 / 선행 조건 / 테스트 / 응답 키 / 위험도 / rollback / Codex / 주석.
- **위험도별 원칙** = 낮은 (wrapper / 응답 키 0 변경 / 5회 안에) / 중간 (contract 보강 + 회귀 + PyInstaller) / 높은 (테스트 보강 후 진행 + wrapper 먼저 + Codex 후 진행 — 19-5 leaves / 19-9 appointments / completion_rules / backup·restore / AI commands·DB 연결).
- **rollback 트리거 RB-1 ~ RB-10** = 응답 키 변경 / 예약 결과 변경 / 휴무 차단 깨짐 / 완료체크 변경 / 문자 대상 오류 / 통계 기준 변경 / 운영 DB 접근 / 외부 API 호출 / 5회 루프 실패 / PyInstaller 실행 불가.
- **주석 / 문서화 기준 D-1 ~ D-8** = 파일 docstring / 함수 docstring (공개만) / COMPAT / SAFETY / NOTE / RISK / TODO(19-x) / TEMP — 의미 없는 줄 주석 ⊥, 주석으로 동작 변경 ⊥.
- **후속 검토 F-1 ~ F-15** = doctors / 반복예약 / 자원 / 알림 / 출력물 / export 확장 / privacy 고도화 / audit 고도화 / EMR / 노쇼 / 권한 등급 / notes 통합 / `/api/health` / calendar UI / AI 의사 가드 — 모두 본 19-P 비-목표, 단정 ⊥.
- **PyInstaller 검증 시점** = 53+ hidden imports 단위 테스트는 매 세션 분리 직후. 실제 빌드 + exe smoke 는 19-14 종료 게이트 + 사용자 명시 승인 시 (CLAUDE.md 배포 규칙 정합).
- **다음 단계** = 19-P-7 위험 등록 문서 (`docs/refactor/19_refactor_risk_register.md`) — 19-1~14 진행 중 발생 가능한 위험 + 완화 방안 + 모니터링 지표.
