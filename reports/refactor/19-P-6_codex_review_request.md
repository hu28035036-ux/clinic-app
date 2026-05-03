# 19-P-6 Codex 검증 요청서 (revision 2 — r1 caveat 정정본)

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-02 | **pass with caveat — yes 19-P-7 진입 가능** ([reports/refactor/19-P-6_codex_review.md](19-P-6_codex_review.md), 12 게이트 모두 pass / pass with caveat. 단 minor caveat 2개 — "추천 순서 14단계" 표현 vs 실제 19-0~19-14 = 15개 실행 세션 + §0 의 `latest_codex_review.md` 링크는 매 세션 덮어쓰기 — 영구 근거 `19-P-5_codex_review.md` 권장) | 초기 작성 |
| r2 | 2026-05-02 | (본 revision) | **2개 caveat 정정**. (1) "14단계" 표현 → **"19-1 ~ 19-14 의 14개 리팩토링 세션 + 19-0 기준 테스트 baseline = 합계 15개 실행 세션"** 으로 정정 (롤아웃 계획 §2-1 머리말 + §10 종합 + 본 요청서 §2 / §8 / §12 / §15). (2) §0 메타의 19-P-5 r3 판정 링크 `latest_codex_review.md` → `19-P-5_codex_review.md`. 코드/테스트/spec/UI/migrations/requirements 무수정 유지. Codex 재검증은 선택 사항 — 진입 자체는 차단 X (r1 yes 판정 유지). |

본 요청서는 19-P 단위화 리팩토링 여섯 번째 세션의 산출물 (롤아웃 계획 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0-A. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-6 진입 가능)** ([reports/refactor/19-P-5_codex_review.md](19-P-5_codex_review.md))
- 19-P-6 r1 Codex 판정: **pass with caveat — yes 19-P-7 진입 가능** ([reports/refactor/19-P-6_codex_review.md](19-P-6_codex_review.md))
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 19-P-5 r3 caveat 본 19-P-6 반영:
  - 워크트리 18-0~18-8 계열 dirty/untracked 변경 다수 → 본 19-P-6 §0-1 / §2 19-0 시점 "변경 소유권 + diff 기준 좁히기" 명시 (19-0 선행 조건).
  - pytest 미실행 (read-only 검증) → 본 19-P-6 도 read-only 문서 세션, pytest 실행은 19-0 부터.
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가만 수행. 코드/테스트/spec/UI/migrations/requirements 무수정.

## 1. 세션 이름

**19-P-6 단위화 리팩토링 롤아웃 계획 문서 작성**

- 19-P-1 [현재 구조](../../docs/refactor/19_refactor_current_state.md), 19-P-2 [목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md), 19-P-3 [모듈 매핑](../../docs/refactor/19_refactor_module_map.md), 19-P-4 [의존성 맵](../../docs/refactor/19_refactor_dependency_map.md), 19-P-5 [테스트 전략](../../docs/refactor/19_refactor_test_strategy.md) 의 후속 문서.
- 단위화 리팩토링을 실제 코드 세션으로 진행하기 전에, **어떤 순서로 어떤 범위를 나누어 진행할지** 롤아웃 계획을 문서화.
- read-only 문서 세션. 실제 코드 / 테스트 / fixture / mock 미작성.

## 2. 이번 세션 목표

| # | 목표 | 본문 위치 |
|---|---|---|
| 1 | §1 롤아웃 기본 원칙 R-1 ~ R-14 (14개) — 기능 변경 X / 한 세션 한 모듈 / 응답 키 보존 / UI / DB schema / 테스트 먼저 / 5회 루프 / Codex 게이트 / 운영 DB ⊥ / 외부 API ⊥ / local-first / per-file-ignores / manual60=1 / 후속 검토 단정 X | docs/refactor/19_refactor_rollout_plan.md §1 |
| 2 | §2 추천 리팩토링 순서 — **19-1 ~ 19-14 의 14개 리팩토링 세션 + 19-0 기준 테스트 baseline = 합계 15개 실행 세션** (+ 19-P 구조 계획 메타). 위험도 / 의존성 / 테스트 보강 시점 통합 정리 + 사용자 §2 주의사항 정합 (예약 마지막 / availability·leaves·treatments·patients·therapists 사전 정리 / 후속 검토 단정 X) | §2 |
| 3 | §3 각 세션별 계획 표 12 컬럼 (세션 번호 / 이름 / 목표 / 수정 가능 / 금지 / 선행 조건 / 테스트 / 응답 키 / 위험도 / rollback / Codex / 주석) — 19-0 ~ 19-14 모두 (15 표) | §3 |
| 4 | §4 세션별 주석 / 문서화 기준 D-1 ~ D-8 + 권장 태그 (COMPAT / SAFETY / NOTE / RISK / TODO(19-x) / TEMP) + 19-1~13 매트릭스 | §4 |
| 5 | §5 19-0 기준 테스트 / 하네스 재확인 계획 — 9개 명령 + 통과 기준 4개 | §5 |
| 6 | §6 위험도별 진행 원칙 — 낮은 / 중간 / 높은 (19-5 / 19-9 / completion_rules / backup·restore / AI commands·DB) | §6 |
| 7 | §7 rollback 기준 RB-1 ~ RB-10 + 절차 5단계 | §7 |
| 8 | §8 Codex 검증 운영 방식 — 작성 / 전달 문구 / 결과 위치 / 판정별 다음 단계 / 게이트 정책 | §8 |
| 9 | §9 보류 / 후속 검토 항목 F-1 ~ F-15 + 단정 금지 정책 | §9 |

## 3. 작성한 문서

### 신규 (3)

- [docs/refactor/19_refactor_rollout_plan.md](../../docs/refactor/19_refactor_rollout_plan.md) — 롤아웃 계획 (§0 ~ §10). 본 19-P-6 신규.
- [reports/refactor/19-P-6_codex_review_request.md](19-P-6_codex_review_request.md) (본 문서, 영구 보존본)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### Codex 작성 예정

- [reports/refactor/19-P-6_codex_review.md](19-P-6_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 4. 수정 금지였던 범위

11개 금지 항목 (사용자 명시):
1. 코드 수정 / 2. `app/` 기능 코드 수정 / 3. `tests/` 테스트 코드 작성 / 4. migration 생성 / 5. `requirements.txt` 수정 / 6. PyInstaller spec 수정 / 7. UI 수정 / 8. 기존 API 응답 구조 변경 / 9. 운영 DB 접근 / 10. 실제 외부 API 호출 / 11. 하네스/테스트 약화

추가:
- 18-8 baseline 회귀 보호 (529 passed, 1 skipped, 7 xfailed).
- m001~m013 diff 0.
- 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 산출물 무수정.

## 5. 실제 수정한 파일 목록

### 신규 (3)

- `docs/refactor/19_refactor_rollout_plan.md`
- `reports/refactor/19-P-6_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1~19-P-5 산출물.

> `latest_codex_review_request.md` 는 19-P-6 진입점으로 덮어쓰여진다 (19-P-5 본문은 `19-P-5_codex_review_request.md` r3 영구 보존).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

| 검사 | 결과 |
|---|---|
| 본 19-P-6 신규 파일 | `19_refactor_rollout_plan.md` + `{19-P-6,latest}_codex_review_request.md` (3개) |
| `app/**` / `tests/**` / migrations / spec / UI / `pyproject.toml` 변경 | 0 |
| 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 산출물 변경 | 0 |
| 새 fixture / mock / harness 파일 추가 | 0 |
| 새 contract 테스트 추가 | 0 (롤아웃 계획만 — 19-1~13 분리 직전 보강) |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 + 본 19-P-6 추가 변경분 0
ls docs/refactor/
ls reports/refactor/
```

> **dirty/untracked 표현 (19-P-3 caveat 반영)**: 본 19-P-6 산출 = 신규 문서 3개. 18-0~18-8 변경분 (m012/m013, AI RAG/knowledge/vector, harness/test) 은 작업트리에 dirty/untracked 로 남아 있지만 본 세션과 무관 — 19-0 시점에 정리 (본 문서 §0-1 / §2 / §5-2 명시).

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_rollout_plan.md](../../docs/refactor/19_refactor_rollout_plan.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3)
- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (19-P-3)
- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) (19-P-4 r2)
- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) (19-P-5 r2)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (5회 루프 / Codex 게이트 / local-first)
- [docs/ai_code_session_protocol.md](../../docs/ai_code_session_protocol.md) (14단계 절차)
- [docs/releases/18_ai_rag_final_checklist.md](../../docs/releases/18_ai_rag_final_checklist.md) (18-8 baseline)
- [reports/refactor/19-P-5_codex_review.md](19-P-5_codex_review.md) (직전 r3 pass with caveat — yes 진입 가능)

## 8. 리팩토링 순서가 위험도 / 의존성 기준으로 현실적인지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| 19-P-3 §31 우선순위 (1 core / 2 audit / 3 settings / 4 staff / 5 treatments / 6 leaves / 7 patients / 8 stats / 9 sms / 11 admin·backup / 12 ai / 13 feature_flags / 14 appointments) 와 정합 | §2-2 / §2-3 |
| 19-P-4 §6 분리 순서 영향 (6-A 먼저 / 6-B 나중 / 6-C 테스트 보강 / 6-D wrapper / 6-E DB schema 무관) 와 정합 | §2-2 / §6 |
| 19-P-5 §5 테스트 우선순위 (최우선 6 / 중요 5 / 후속 10) 와 정합 | §3 / §5 |
| appointments (19-9) 가 marathon 전체에서 후반부에 위치 — 실행 세션 15개 (19-0~19-14) 중 11/15 번째 (= 19-0 부터 11번째) | §2-1 |
| availability (19-4) / leaves (19-5) / treatments (19-6) / patients (19-7) / staff (19-8) 가 19-9 (appointments) 진입 전에 모두 완료되도록 배치 | §2-1 / §2-3 / §3-9 선행 조건 |
| 19-3 calendar 가 view-model only 또는 패스 (UI 분리 비-목표) | §2-1 / §3-3 |
| 19-13 AI commands 가 19-5 leaves 분리 후 진입 (action_leave 가 `_upsert_employee_leave_core` 호출) | §3-13 선행 조건 |
| 19-P-4 caveat (`leave_type=am/pm/full` 백엔드 차단) 이 19-4 / 19-5 에서 정방향 전환 명시 | §3-4 / §3-5 / §7 RB-3 |

### Codex 검증 명령

```bash
# 의존성 정합 — symbol 위치 확인
grep -n "_upsert_employee_leave_core" app/routers/api.py app/services/ai/action_leave.py
grep -nE "_check_version|_bump_version|_check_lunch_block|_lunch_window" app/routers/api.py
grep -n "_doctor_codes_set\|is_doctor_filter" app/routers/api.py
grep -n "manual60\|count_increment" app/models/constants.py
grep -nE "^@router\." app/routers/api.py | wc -l   # 86 endpoint
grep -nE "^@router\." app/routers/ai.py | wc -l    # 13 endpoint
# xfail / skip 분류 확인
grep -nE "xfail|skip" tests/test_appointment_rules.py tests/test_therapist_leave.py
```

## 9. 세션별 테스트 / rollback / Codex 검증 기준이 충분한지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| 각 19-x 세션 표 12 컬럼 모두 작성 | §3-0 ~ §3-14 (15 표) |
| 각 세션 "반드시 실행할 테스트" 가 18-8 baseline (529/1/7) + AI 하네스 6개 + 도메인별 회귀 + PyInstaller 53 tests 포함 | §3 모든 표 |
| 각 세션 "유지해야 할 API/응답 key" 가 33+ 키 셋 + 비-AI alias + 모듈별 응답 dict 포함 | §3 모든 표 |
| 각 세션 "rollback 기준" 이 RB-1~RB-10 (§7) 와 정합 | §3 모든 표 + §7 |
| 각 세션 "Codex 검증 포인트" 가 의존성 / 응답 키 / local-first / 후속 검토 분류 포함 | §3 모든 표 |
| 19-0 진입 게이트 (§5-2) — 4개 통과 기준 | §5-2 |
| 5회 루프 정책 + rollback 절차 5단계 | §7-1 |
| 위험도 3분류 — 높은 위험 모듈 (19-5 / 19-9 / completion_rules / backup·restore / AI commands·DB) 추가 원칙 | §6-3 |

### Codex 검증 포인트 — 응답 키 보호 검증

```bash
# 33+ 응답 키 셋 위치 확인
grep -n "sources\|masked_question\|top_score\|confidence\|not_found\|blocked\|guard_hits" app/services/ai/rag/pipeline.py
grep -n "api_key_set\|sdk_installed\|sdk_errors\|knowledge_doc_count\|ready" app/routers/ai.py app/services/ai/health.py
grep -n "ai_mode\|search_mode\|vector_status\|external_api\|knowledge\|prompt_versions\|recent_ai_logs" app/services/ai/health.py
# alias 이중 키
grep -n "therapist_id\|employee_id" app/routers/api.py | head -20
```

## 10. 주석 / 문서화 기준이 각 세션에 반영되었는지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| §4-1 적용 기준 D-1 ~ D-8 (8개) | §4-1 |
| §4-2 권장 태그 (COMPAT / SAFETY / NOTE / RISK / TODO(19-x) / TEMP) | §4-2 |
| §4-3 19-1~13 세션별 주석 카테고리 매트릭스 | §4-3 |
| 각 19-x 세션 표의 "주석/문서화 필요 지점" 행이 §4-2 태그와 정합 | §3 모든 표 + §4-3 |
| 의미 없는 모든 줄 주석 ⊥ + 주석 작성 때문에 기능 동작 변경 ⊥ 정책 명시 | §4-1 D-7 / D-8 |
| TODO 는 반드시 세션 번호 또는 제거 조건 포함 | §4-1 D-6 + §4-2 |

### Codex 검증 명령 — 주석 카테고리 정합

```bash
# 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 의 주석 카테고리와 본 19-P-6 §4 정합
grep -n "COMPAT\|SAFETY\|NOTE\|RISK\|TODO\|TEMP" docs/refactor/19_refactor_test_strategy.md docs/refactor/19_refactor_dependency_map.md docs/refactor/19_refactor_module_map.md | head -30
```

## 11. 후속 검토 항목 분류 정합 + 단정 금지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| §9 후속 검토 F-1 ~ F-15 (15개) — 모두 현재 부재 명시 + post-19-P 도입 시 동반 작업 | §9 |
| F-1 doctors / medical_staff (별도 모듈) — Patient.doctor_id / Department / Room / DoctorSchedule / Order / Prescription 부재 | §9 / §3-8 |
| F-2 ~ F-5 recurring_appointments / resources / notifications / printing — 모두 미구현 | §9 |
| F-10 노쇼 별도 필드 — 현재 status="canceled" 만 | §9 |
| F-13 `/api/health` 신설 — 현재 부재 (M-28) | §9 / §3-2 |
| F-15 AI 의사 가드 (M-36) — RAG hallucination guard 부분만, 의사 단정 표현 차단 패턴 부재 | §9 / §3-13 |
| §9-1 단정 금지 정책 — 본 19-P 기간 내 어떤 항목도 도입 X | §9-1 |
| 19-9 appointments 분리에서 m014+ 컬럼 신설 ⊥ | §3-9 수정 금지 범위 |

### Codex 검증 명령 — 부재 항목 확인

```bash
# 부재 항목이 실제로 부재한지 확인
grep -nE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py   # 0건 기대
grep -n "doctor_id" app/models/models.py   # Patient 에 0건 기대
grep -nE "no_show|noshow" app/models/models.py app/routers/api.py | head   # 노쇼 별도 필드 0건 기대
grep -nE "/api/health\b" app/routers/api.py app/routers/ai.py   # /api/health 0건 (있다면 /api/ai/health 만)
```

## 12. 다음 단계 (19-P-7 위험 등록 문서) 진입 가능 판단 기준

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 본 19-P-6 추가 변경분 0. 19-P-1 ~ 19-P-5 산출물 무수정. |
| G-2 리팩토링 순서 정합 | §2 의 19-1~19-14 (14개 리팩토링) + 19-0 (baseline) = 15개 실행 세션 순서가 19-P-3 §31 우선순위 + 19-P-4 §6 + 19-P-5 §5 와 정합. appointments (19-9) 마지막. availability/leaves/treatments/patients/staff (19-4~8) 사전 정리. |
| G-3 세션별 계획 12 컬럼 | §3-0 ~ §3-14 (15 표) 모두 12 컬럼 작성 (세션 번호 / 이름 / 목표 / 수정 가능 / 금지 / 선행 조건 / 테스트 / 응답 키 / 위험도 / rollback / Codex / 주석). |
| G-4 응답 키 / URL 후방호환 | §1 R-4 + §3 모든 표의 "유지해야 할 API/응답 key" 행 + §7 RB-1 명시. 33+ 키 셋 + 비-AI alias 보존. |
| G-5 AI/RAG local-first | §1 R-12 + §3-13 + §7 RB-8 명시. AI/RAG → 도메인 ⊥ (D-6 / F-5). |
| G-6 doctors / medical_staff 부재 단정 X | §3-8 + §9 F-1 + §9-1 단정 금지 정책. 부재 항목 7개 (Doctor / Department / Room / DoctorSchedule / Patient.doctor_id / Order / Prescription) 모두 후속 검토. |
| G-7 19-P-4 caveat (`am`/`pm`/`full` 백엔드 차단) 반영 | §3-4 (19-4 백엔드 차단 코드 신설 + xfail 정방향 전환) + §3-5 (19-5 leaves 분리 시 정방향 유지) + §7 RB-3. |
| G-8 PyInstaller 검증 시점 | §3-1 ~ §3-13 의 "반드시 실행할 테스트" 행에 53 tests 매 세션 분리 직후 + §3-14 종료 게이트 + 사용자 승인 시 실제 빌드 명시. |
| G-9 5회 루프 + Codex 게이트 | §1 R-9 / R-10 + §7-1 rollback 절차 + §8 Codex 검증 운영 방식. |
| G-10 하네스 약화 ⊥ | §1 R-11 / R-12 + §3 모든 표의 "수정 금지 범위" 행 + §5 19-0 baseline 재고정. |
| G-11 후속 검토 단정 X | §9 F-1 ~ F-15 + §9-1 단정 금지 정책. 본 19-P 기간 내 도입 X. |
| G-12 (신규) 워크트리 dirty 정리 게이트 | §0-1 / §2-1 19-0 / §5-2 통과 기준 4 — 18-0~18-8 변경분 main 머지 또는 별도 commit 명시. |

→ G-1 ~ G-12 전부 통과 시 **yes — 19-P-7 진입 가능**.

## 13. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 무수정 | §5 / §6 |
| `docs/refactor/19_refactor_rollout_plan.md` 작성 또는 수정 | §3 신규 |
| `reports/refactor/{19-P-6,latest}_codex_review_request.md` 작성 | §3 신규 |
| 리팩토링 순서가 의존성 맵과 테스트 전략에 맞는가 | §8 + 본 검증 요청서 §8 |
| appointments 를 너무 초반에 대규모로 이동하지 않도록 되어 있는가 | §2-1 (19-9 = 실행 세션 15개 중 11/15 번째 — 후반부) + §2-3 + §3-9 선행 조건 |
| availability / leaves / treatments / patients / therapists 경계를 먼저 정리하도록 되어 있는가 | §2-1 (19-4 ~ 19-8) + §2-3 |
| 각 세션별 수정 가능 범위와 금지 범위가 명확한가 | §3-0 ~ §3-14 (15 표 12 컬럼) |
| 각 세션별 테스트와 rollback 기준이 명확한가 | §3 모든 표 + §7 RB-1~RB-10 |
| 주석/문서화 기준이 실제 코드 리팩토링 세션에 적용되도록 되어 있는가 | §4-1 D-1~D-8 + §4-2 + §4-3 매트릭스 |
| 현재 없는 기능을 실제 구현 대상으로 단정하지 않고 후속 검토로 분류했는가 | §9 F-1~F-15 + §9-1 |
| 다음 단계 19-P-7 위험 등록 문서로 넘어가도 되는가 | §12 G-1 ~ G-12 |

## 14. Codex 검증 결과 기록 위치

- [reports/refactor/19-P-6_codex_review.md](19-P-6_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-P-6 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- G-1 ~ G-12: {결과 + 근거}

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-P-7 진입 권고
{yes / no + 근거}
```

## 15. Claude Code 자체 판단

**yes (19-P-7 진입 권고)** — Codex 검증 후 다음 세션 진입 가능.

근거:
1. 본 세션은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `19_refactor_rollout_plan.md` 11개 섹션 (§0~§10) — 원칙 14개 + **추천 순서 (19-1~19-14 의 14개 리팩토링 + 19-0 baseline = 15개 실행 세션 + 19-P 메타)** + 세션별 계획 15표 (12 컬럼 — 19-0~19-14) + 주석 기준 8 + 19-0 계획 + 위험도 3분류 + rollback 10 + Codex 운영 + 후속 검토 15 = 사용자 §1~§9 모두 커버.
3. 19-P-5 r3 Codex caveat 2개 모두 반영 — 워크트리 dirty 정리 (19-0 게이트) + pytest 미실행 (read-only 세션, 19-0 부터 실행).
4. 19-P-4 caveat (`am`/`pm`/`full` 백엔드 차단) 본 19-4 / 19-5 에서 정방향 전환 명시.
5. 의사 / 진료진 부재 항목 7개 (§9 F-1) 모두 후속 검토 분류 — 실제 구현된 것처럼 단정 X.
6. AI/RAG local-first 보존 — R-12 / §3-13 / §7 RB-8.
7. 응답 키 보호 — R-4 + §3 모든 표 + §7 RB-1.
8. 운영 DB 보호 + 외부 API 차단 — R-11 + §3 모든 표 + §7 RB-7 / RB-8.
9. PyInstaller 검증 시점 — §3 매 세션 53 tests + §3-14 종료 게이트 + 사용자 승인 시 빌드.
10. 5회 루프 + Codex 게이트 — R-9 / R-10 + §7-1 + §8.
11. 18-8 baseline 회귀 보호 100%.
12. 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 산출물 무수정.

남은 위험:
- T-1 ~ T-15 (19-P-2) 의사결정 항목 — 19-P-7 위험 등록에서 위험 + 완화 방안으로 정리 후 19-1~14 진행 시 점진 결정.
- 비-AI 86 endpoint contract 미작성 (C-1 ~ C-7) — 본 19-P-6 은 계획만, 실제 보강은 각 19-x 분리 직전 (R-7).
- `xfail` 7건 + `skip` 1건 — 19-4 (예약 도수 중복 차단 3건 + 취소-후-중복 1건) + 19-4 (휴무 차단 4건) 에서 백엔드 차단 코드 + 정방향 전환 필수 (§3-4 / §3-5 명시).
- 워크트리 dirty 정리 — 19-0 진입 시점 게이트 (§0-1 / §2-1 / §5-2 명시).
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 19-0 또는 별도 세션.
- 세션 경계 Git 검증 caveat — 18-0~18-8 미커밋 (이전 세션부터 알려진 사항).

다음 세션:
- 19-P-7 위험 등록 문서 (`docs/refactor/19_refactor_risk_register.md`) — 19-1 ~ 19-14 진행 중 발생 가능한 위험 + 완화 방안 + 모니터링 지표.
