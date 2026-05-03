# 19-P-7 Codex 검증 요청서 (revision 3 — r2 fail 후 taxonomy 숫자 실측 정합본)

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-03 | **pass with caveat — yes 19-P-8 진입 가능** ([reports/refactor/19-P-7_codex_review.md](19-P-7_codex_review.md), 12 게이트 모두 pass / pass with caveat. caveat = taxonomy 메타 정리 minor) | 초기 작성 |
| r2 | 2026-05-03 | **fail — no 19-P-8** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r2, G-2 / G-11 fail. r2 의 "21 prefix / 78 제목 / 약 74 순수" 주장이 실제 파일 (23행 / 77 제목) 과 불일치) | 4개 taxonomy 메타 정정 시도 — TIME 키 추가 / FF·PRIV·NOTES 통합 / R-LOCK-04 격하 / 숫자 정정. 그러나 숫자 자체가 여전히 틀려서 fail. |
| r3 | 2026-05-03 | (본 revision) | **r2 fail caveat 실측 정합**. Codex r2 의 정확한 권고 표현 ("§1-3 표 행 = 23개: 단독 Risk prefix 20개 + 통합 키 3개(FF/PRIV/NOTES)" / "§2 섹션 = 23개" / "실제 Risk ID 제목 = 77개" / "R-LOCK-04는 별도 Risk ID 제목이 아니라 통합 메모") 를 위험 등록 §0 보정 이력 / §1-3 표 / §1-3 Taxonomy 합계 / §8 종합 + 본 요청서 §2 / §15 모두 적용. **77개 카테고리별 합계 검증 — APPT 7 + PAT 5 + THER 3 + DOC 2 + LEAVE 4 + TX 4 + STAT 5 + SMS 5 + ADM 5 + BAK 5 + AI 7 + CAL 4 + AUDIT 2 + HEALTH 1 + EXIM 2 + CORE 5 + TIME 1 + BATCH 1 + LOCK 3 + OPS 6 = 77 ✓**. 코드/테스트/spec/UI/migrations/requirements 무수정 유지. Codex 재검증 필수. |

본 요청서는 19-P 단위화 리팩토링 일곱 번째 세션의 산출물 (위험 등록 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0-A. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-7 진입 가능)** ([reports/refactor/19-P-6_codex_review.md](19-P-6_codex_review.md))
- 19-P-7 r1 Codex 판정: **pass with caveat — yes 19-P-8 진입 가능** ([reports/refactor/19-P-7_codex_review.md](19-P-7_codex_review.md))
- 19-P-7 r2 Codex 판정: **fail — no 19-P-8** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r2 — taxonomy 숫자 정정 미완료)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 19-P-6 r1 caveat 본 19-P-7 반영:
  - "추천 순서 14단계" 표현 정정 (r2 보정 완료) → 본 19-P-7 §5 도 "19-1~19-14 = 14개 리팩토링 + 19-0 baseline = 15개 실행 세션" 표현 정합.
  - §0 Codex 판정 링크 영구 근거 (`19-P-6_codex_review.md`) 사용.
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가만 수행. 코드/테스트/spec/UI/migrations/requirements 무수정.

## 1. 세션 이름

**19-P-7 단위화 리팩토링 위험 등록 문서 작성**

- 19-P-1 [현재 구조](../../docs/refactor/19_refactor_current_state.md), 19-P-2 [목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md), 19-P-3 [모듈 매핑](../../docs/refactor/19_refactor_module_map.md), 19-P-4 [의존성 맵](../../docs/refactor/19_refactor_dependency_map.md), 19-P-5 [테스트 전략](../../docs/refactor/19_refactor_test_strategy.md), 19-P-6 [롤아웃 계획](../../docs/refactor/19_refactor_rollout_plan.md) + [docs/releases/18_ai_rag_known_risks.md](../../docs/releases/18_ai_rag_known_risks.md) 의 후속 문서.
- 단위화 리팩토링 중 발생할 수 있는 위험을 기능별 / 모듈별로 정리하고, **방지 방법 / 필요한 테스트 / rollback 기준 / Codex 검증 포인트** 를 위험 항목 단위로 등록.
- read-only 문서 세션. 실제 코드 / 테스트 / fixture / mock 미작성.

## 2. 이번 세션 목표

| # | 목표 | 본문 위치 |
|---|---|---|
| 1 | §1 위험 등록 기준 — 14개 필드 (Risk ID / 위험 이름 / 관련 모듈 / 위험 설명 / 가능성 / 영향도 / 전체 위험도 / 발생 징후 / 방지 방법 / 필요한 테스트 / 주석 태그 / rollback 기준 / Codex 검증 포인트 / 비고) + 위험도 매트릭스 + **§1-3 카테고리 키 표 = 23행** (단독 Risk prefix 20개 + 통합 키 3개 — FF/PRIV/NOTES, r3 정정) | docs/refactor/19_refactor_risk_register.md §1 |
| 2 | §2 위험 항목 등록 (**§2 섹션 23개 — 그 중 3개 = 2-M notes / 2-R feature_flags / 2-T privacy 는 통합 메모 섹션, 실제 Risk ID 제목 77개** = 단독 Risk ID 77 — R-LOCK-04 격하 후 모두 단독 — 통합 메모 LOCK-04 별도, r3 정정) — 사용자 §2 의 핵심 위험 모두 포함 | §2 (2-A appointments / 2-B patients / 2-C therapists / 2-D doctors 후속 / 2-E leaves / 2-F treatments / 2-G stats / 2-H sms / 2-I admin / 2-J backup / 2-K ai / 2-L calendar / 2-M notes 통합 / 2-N audit / 2-O health 후속 / 2-P export_import / 2-Q core / 2-R feature_flags 통합 / 2-S batch / 2-T privacy 통합 / 2-U concurrency / 2-V time_utils / 2-W OPS) |
| 3 | §3 위험도별 분류 — 치명 8 / 높음 14 / 중간 다수 / 낮음 3 / 후속 검토 14 | §3 |
| 4 | §4 모듈별 위험 요약 (21 카테고리 — 사용자 §4 정합) | §4 |
| 5 | §5 리팩토링 세션별 위험 연결 (19-0 ~ 19-14) | §5 |
| 6 | §6 주석 / 문서화 기준 (각 위험에 향후 코드 이동 시 필요한 태그 매트릭스) | §6 |

## 3. 작성한 문서

### 신규 (3)

- [docs/refactor/19_refactor_risk_register.md](../../docs/refactor/19_refactor_risk_register.md) — 위험 등록 (§0 ~ §8). 본 19-P-7 신규.
- [reports/refactor/19-P-7_codex_review_request.md](19-P-7_codex_review_request.md) (본 문서, 영구 보존본)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### Codex 작성 예정

- [reports/refactor/19-P-7_codex_review.md](19-P-7_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 4. 수정 금지였던 범위

11개 금지 항목 (사용자 명시):
1. 코드 수정 / 2. `app/` 기능 코드 수정 / 3. `tests/` 테스트 코드 작성 / 4. migration 생성 / 5. `requirements.txt` 수정 / 6. PyInstaller spec 수정 / 7. UI 수정 / 8. 기존 API 응답 구조 변경 / 9. 운영 DB 접근 / 10. 실제 외부 API 호출 / 11. 하네스/테스트 약화

추가:
- 18-8 baseline 회귀 보호 (529 passed, 1 skipped, 7 xfailed).
- m001~m013 diff 0.
- 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 산출물 무수정.

## 5. 실제 수정한 파일 목록

### 신규 (3)

- `docs/refactor/19_refactor_risk_register.md`
- `reports/refactor/19-P-7_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1~19-P-6 산출물.

> `latest_codex_review_request.md` 는 19-P-7 진입점으로 덮어쓰여진다 (19-P-6 본문은 `19-P-6_codex_review_request.md` r2 영구 보존).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

| 검사 | 결과 |
|---|---|
| 본 19-P-7 신규 파일 | `19_refactor_risk_register.md` + `{19-P-7,latest}_codex_review_request.md` (3개) |
| `app/**` / `tests/**` / migrations / spec / UI / `pyproject.toml` 변경 | 0 |
| 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 산출물 변경 | 0 |
| 새 fixture / mock / harness 파일 추가 | 0 |
| 새 contract 테스트 추가 | 0 (위험 등록만 — 19-1~13 분리 직전 보강) |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 + 본 19-P-7 추가 변경분 0
ls docs/refactor/
ls reports/refactor/
```

> **dirty/untracked 표현 (19-P-3 caveat 반영)**: 본 19-P-7 산출 = 신규 문서 3개. 18-0~18-8 변경분은 작업트리에 dirty/untracked 로 남아 있지만 본 세션과 무관 — 19-0 시점에 정리 (19-P-6 §0-1 / §2 / §5-2 명시).

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_risk_register.md](../../docs/refactor/19_refactor_risk_register.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3)
- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (19-P-3)
- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) (19-P-4 r2)
- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) (19-P-5 r2)
- [docs/refactor/19_refactor_rollout_plan.md](../../docs/refactor/19_refactor_rollout_plan.md) (19-P-6 r2)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (절대 원칙 + local-first)
- [docs/releases/18_ai_rag_known_risks.md](../../docs/releases/18_ai_rag_known_risks.md) (AI 알려진 위험)
- [docs/releases/18_ai_rag_final_checklist.md](../../docs/releases/18_ai_rag_final_checklist.md) (18-8 baseline)
- [reports/refactor/19-P-6_codex_review.md](19-P-6_codex_review.md) (직전 r1 pass with caveat — yes 진입 가능)

## 8. 핵심 위험이 빠짐없이 등록되었는지 확인할 항목

### Codex 검증 포인트

| 사용자 §2 카테고리 | Risk ID 매핑 | 검증 위치 |
|---|---|---|
| 예약 (응답 키 / 중복 / 휴무 차단 / 반차 / 가능 시간 / devtools / 통계 충돌) | R-APPT-01~07 | §2-A |
| 환자 / 메모 (PII / 검색 / 신환 / 메모 경계 / 환자별 메모) | R-PAT-01~05 | §2-B |
| 치료사 / 의사 (활성 / 치료 항목 / 색상 / doctors 단정 / 담당의 후보) | R-THER-01~03 / R-DOC-01~02 | §2-C / §2-D |
| 휴무 (full/am/pm / 중복 / 표시-차단 / 캘린더) | R-LEAVE-01~04 | §2-E |
| 치료항목 / 완료체크 (시간별 / 시간 가중치 되돌아감 / 확장 / 카운트-통계) | R-TX-01~04 | §2-F |
| 통계 (예약-완료 / 치료사 / 항목 / 시간-요일 / 신환 / 취소-노쇼) | R-STAT-01~05 | §2-G |
| 문자 (대상 / 템플릿 / 계정 / 외부 발송 / 자동 트리거) | R-SMS-01~05 | §2-H |
| 관리자 / 설정 / 권한 (admin 노출 / API key / AI 모드 / feature flag / audit) | R-ADM-01~05 | §2-I |
| 백업 / 복구 (운영 DB / 경로 / 복구 / 보관 / 충돌) | R-BAK-01~05 | §2-J |
| AI / RAG (local-first / local_only / sources-low_confidence-PII-unknown / RAG 도메인 / vector / 외부 API / AI 로그 PII) | R-AI-01~07 | §2-K |
| 캘린더 / 표시 (저장-표시 / 금일예약 / 미니캘린더 / 색상) | R-CAL-01~04 | §2-L |
| 공통 구조 (repo→service / core→modules / 중복 query / 응답 envelope / UI 키 / spec hidden imports / requirements) | R-CORE-01~05 / R-OPS-04 / R-OPS-06 | §2-Q / §2-W |
| 운영 / 배포 (운영 DB / DB 경로 / 외부 API 차단 / PyInstaller / exe / requirements) | R-OPS-01~06 | §2-W |

### Codex 검증 명령

```bash
# 핵심 위험 키워드 grep
grep -nE "manual30|manual60|count_increment|leave_type|am|pm|full|_upsert_employee_leave_core|_doctor_codes_set|is_doctor_filter|_check_lunch_block|_check_version|_bump_version|_bump_patient_count|_get_manual_treatment_rows|_lighten_hex" app/routers/api.py app/models/constants.py | head -40
# xfail / skip 분류
grep -nE "xfail|skip" tests/test_appointment_rules.py tests/test_therapist_leave.py
# 응답 키 보호
grep -n "sources\|masked_question\|top_score\|confidence\|not_found\|blocked" app/services/ai/rag/pipeline.py
# 부재 항목 (doctors / EMR)
grep -nE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py   # 0건 기대
grep -n "doctor_id" app/models/models.py   # Patient 에 0건 기대
```

## 9. 위험도 / 발생 가능성 / 영향도 분류가 현실적인지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| 위험도 매트릭스 (가능성 × 영향도 → 낮음/중간/높음/치명) | §1-2 |
| 치명 위험 8개 (R-APPT-02 / R-APPT-03 / R-PAT-01 / R-SMS-04 / R-ADM-01 / R-ADM-02 / R-AI-01 / R-BAK-01) | §3-A |
| 높은 위험 14개 (응답 키 / 12:00 기준 / devtools / doctors 단정 / 표시-차단 / manual60 / 계정 노출 / local_only / 외부 API / AI 로그 PII / UI 키 / DB 경로 / PyInstaller / exe smoke) | §3-B |
| 중간 위험 (다수 — 응답 키 / 헬퍼 / 의존성 / time_utils / batch / lock 등) | §3-C |
| 낮은 위험 3개 (R-THER-03 / R-CAL-04 / R-HEALTH-01) | §3-D |
| 후속 검토 위험 14개 (doctors / 반복 / 자원 / 알림 / 출력물 / export 확장 / privacy / audit 고도화 / 노쇼 / 권한 / `/api/health` / calendar UI / AI 의사 가드 / `modules/notes/`) | §3-E |
| 18 AI 알려진 위험 (`docs/releases/18_ai_rag_known_risks.md`) 통합 | §0-1 + §2-K |

### Codex 검증 — 위험도 합리성

```bash
# 치명 위험의 발생 징후가 실제로 발생 가능한지 확인
# R-APPT-02 / R-APPT-03 — 현재 백엔드 차단 부재 → xfail 상태가 증거
grep -nE "백엔드 차단 미구현" tests/test_appointment_rules.py tests/test_therapist_leave.py
# R-AI-01 — should_call_llm 게이트 실제 코드 위치
grep -n "def should_call_llm\|should_call_llm" app/services/ai/ -r
# R-BAK-01 — db_guard 호출 위치
grep -n "assert_safe_db_path" tests/conftest.py tests/harness/db_guard.py
```

## 10. rollback 기준과 테스트 연결이 충분한지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| 각 Risk 항목에 rollback 기준 (RB-1 ~ RB-10 매핑) | §2 모든 위험 항목 |
| 각 Risk 항목에 필요한 테스트 (19-P-5 §4 보강 9개 + AI 하네스 6개 + 도메인별 회귀) | §2 모든 위험 항목 |
| 각 Risk 항목에 Codex 검증 포인트 | §2 모든 위험 항목 |
| 위험도별 우선 보강 / 리팩토링 전 확인 / rollback 기준 / Codex 집중 검증 | §3-A ~ §3-E |
| 19-0 ~ 19-14 세션별 위험 연결 (Risk ID 매핑) | §5 |

### Codex 검증 명령 — 테스트 / rollback 정합

```bash
# RB-1 ~ RB-10 매핑 (19-P-6 §7)
grep -n "RB-" docs/refactor/19_refactor_rollout_plan.md | head -15
# 19-P-5 §4 보강 9개 항목 정합
grep -nE "보강 필요|기존 일부|기존 테스트 있음" docs/refactor/19_refactor_test_strategy.md | head -20
```

## 11. 주석 / 문서화 기준이 위험 등록에 반영되었는지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| §6-1 적용 기준 8개 (COMPAT/SAFETY/NOTE/RISK/TODO/TEMP + 의미 없는 주석 ⊥ + 동작 변경 ⊥) | §6-1 |
| §6-2 위험 항목별 주석 태그 매트릭스 (약 70 Risk × 5 카테고리) | §6-2 |
| 각 §2 Risk 항목의 "필요한 주석 태그" 행이 §6-2 매트릭스와 정합 | §2 모든 위험 항목 + §6-2 |
| TODO 는 반드시 세션 번호 또는 제거 조건 포함 (19-P-6 §4-1 D-6 정합) | §6-1 |
| 주석 작성 때문에 기능 동작 변경 ⊥ | §6-1 |

### Codex 검증 명령 — 주석 태그 정합

```bash
grep -n "COMPAT\|SAFETY\|NOTE\|RISK\|TODO\|TEMP" docs/refactor/19_refactor_risk_register.md | wc -l   # 다수 기대
```

## 12. 다음 단계 (19-P-8 의사결정 기록 문서) 진입 가능 판단 기준

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 본 19-P-7 추가 변경분 0. 19-P-1 ~ 19-P-6 산출물 무수정. |
| G-2 핵심 위험 등록 정합 | 사용자 §2 의 모든 카테고리 (예약 / 환자·메모 / 치료사·의사 / 휴무 / 치료항목·완료체크 / 통계 / 문자 / 관리자·설정·권한 / 백업·복구 / AI·RAG / 캘린더 / 공통 구조 / 운영·배포) 가 §2-A ~ §2-W 에 매핑 |
| G-3 위험도 분류 현실성 | §3-A 치명 8 / §3-B 높음 14 / §3-C 중간 / §3-D 낮음 3 / §3-E 후속 14 모두 가능성 × 영향도 매트릭스 정합 |
| G-4 응답 키 / URL 후방호환 | R-APPT-01 / R-PAT-02 / R-STAT-01-02 / R-SMS-01-02 / R-ADM-* / R-AUDIT-01 / R-EXIM-01-02 / R-CORE-04-05 등에 응답 키 보호 명시 |
| G-5 AI/RAG local-first | R-AI-01 ~ R-AI-07 + R-LOCK-02-03 + R-DOC-02 (의사 가드 후속) — 7+ 위험 등록 |
| G-6 doctors / medical_staff 부재 단정 X | §2-D R-DOC-01~02 + §3-E + §4 카테고리 후속 분류 명시. 부재 항목 grep 회귀 명시. |
| G-7 19-P-4 caveat (`am`/`pm`/`full` 백엔드 차단) 위험 등록 | R-APPT-02 / R-APPT-03 / R-APPT-04 (xfail 7건 + skip 1건 정방향 전환 명시) |
| G-8 운영 DB / 외부 API / API key / 개인정보 안전 위험 | R-BAK-01 / R-AI-06 / R-SMS-04 / R-ADM-02 / R-AI-07 / R-PAT-01 / R-AUDIT-02 / R-OPS-01~03 등 등록 |
| G-9 PyInstaller / 빌드 위험 | R-OPS-04~06 등록. 53 hidden imports / exe smoke / requirements 무수정 명시 |
| G-10 후속 검토 단정 X | §3-E 후속 14개 + §4 모든 후속 카테고리 + §2-D / §2-O 명시 |
| G-11 주석 / 문서화 기준 정합 | §6-1 D-1~D-8 + §6-2 매트릭스 (약 70 Risk × 5 카테고리) |
| G-12 세션별 위험 연결 정합 | §5 19-0 ~ 19-14 모두 매핑. 19-4 / 19-9 / 19-13 / 19-14 핵심 위험 명시 |

→ G-1 ~ G-12 전부 통과 시 **yes — 19-P-8 진입 가능**.

## 13. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 무수정 | §5 / §6 |
| `docs/refactor/19_refactor_risk_register.md` 작성 또는 수정 | §3 신규 |
| `reports/refactor/{19-P-7,latest}_codex_review_request.md` 작성 | §3 신규 |
| 예약/휴무/완료체크/통계/문자/AI/RAG 관련 핵심 위험이 빠지지 않았는가 | §8 / 본 검증 요청서 §8 |
| 운영 DB / 외부 API / API key / 개인정보 관련 안전 위험이 충분히 등록되었는가 | §12 G-8 + 본 §8 (R-BAK-01 / R-AI-06 / R-SMS-04 / R-ADM-02 / R-AI-07 / R-PAT-01 / R-AUDIT-02 / R-OPS-01~03) |
| 현재 기능이 없는 doctors / recurring / resources / notifications / printing 등은 후속 검토 위험으로 분류 | §12 G-10 + §3-E + §4 |
| 각 위험에 방지 방법, 테스트, rollback 기준, Codex 검증 포인트가 있는가 | §10 + §2 모든 위험 항목 (14 필드) |
| 향후 코드 이동 시 필요한 COMPAT / SAFETY / NOTE / RISK / TODO 주석 지점 반영 | §11 + §6-2 매트릭스 (약 70 Risk × 5 카테고리) |
| 다음 단계 19-P-8 의사결정 기록 문서로 넘어가도 되는가 | §12 G-1 ~ G-12 |

## 14. Codex 검증 결과 기록 위치

- [reports/refactor/19-P-7_codex_review.md](19-P-7_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-P-7 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- G-1 ~ G-12: {결과 + 근거}

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-P-8 진입 권고
{yes / no + 근거}
```

## 15. Claude Code 자체 판단

**yes (19-P-8 진입 권고)** — Codex 검증 후 다음 세션 진입 가능.

근거:
1. 본 세션은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `19_refactor_risk_register.md` 9개 섹션 (§0~§8) — 위험 등록 기준 14 필드 + **위험 항목 77 단독 Risk ID 제목 + 통합 메모 4개 (LOCK-04 + notes / FF / PRIV 섹션) — §1-3 표 23행 (단독 prefix 20 + 통합 키 3) / §2 섹션 23개** (r3 실측 정합) + 위험도 5 분류 + 모듈별 21 카테고리 + 세션별 19-0~19-14 매핑 + 주석 매트릭스 = 사용자 §1~§6 모두 커버.
3. 19-P-6 r1+r2 Codex caveat 모두 반영 — "14단계" 표현 정정 (본 §5) + 영구 근거 링크 (본 §0).
4. 19-P-4 caveat (`am`/`pm`/`full` 백엔드 차단) 본 R-APPT-02 / R-APPT-03 / R-APPT-04 + R-LEAVE-03 등록 — `xfail` 7건 + `skip` 1건 정방향 전환 위험으로 명시.
5. 의사 / 진료진 부재 항목 7개 — R-DOC-01 / R-DOC-02 + §3-E 후속 검토 + §4 카테고리 분리. 단정 ⊥.
6. AI/RAG local-first 보존 — R-AI-01 ~ R-AI-07 + R-LOCK-02-03 + R-DOC-02 (의사 가드 후속) 7+ 위험 등록.
7. 응답 키 보호 — R-APPT-01 / R-PAT-02 / R-STAT-01-02 / R-SMS-01-02 / R-ADM-* / R-AUDIT-01 / R-EXIM-01-02 / R-CORE-04-05 등.
8. 운영 DB / 외부 API / API key / PII 안전 위험 — R-BAK-01 / R-AI-06 / R-SMS-04 / R-ADM-02 / R-AI-07 / R-PAT-01 / R-AUDIT-02 / R-OPS-01~03 등록.
9. PyInstaller / 빌드 위험 — R-OPS-04~06 + 53 hidden imports / exe smoke / requirements 무수정.
10. 후속 검토 14개 모두 §3-E + §4 + §2-D / §2-O 단정 ⊥ 명시.
11. 18-8 baseline 회귀 보호 100%.
12. 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 산출물 무수정.

남은 위험:
- T-1 ~ T-15 (19-P-2) 의사결정 항목 — 19-P-8 의사결정 기록에서 정리.
- 비-AI 86 endpoint contract 미작성 (C-1 ~ C-7) — 본 19-P-7 은 위험 등록만, 실제 보강은 각 19-x 분리 직전.
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 19-0 또는 별도 세션.

다음 세션:
- 19-P-8 의사결정 기록 문서 (`docs/refactor/19_refactor_decision_record.md`) — 19-P-1~7 전 과정에서 합의된 의사결정 (T-1 ~ T-15 등) + 향후 결정 필요 항목 정리.
