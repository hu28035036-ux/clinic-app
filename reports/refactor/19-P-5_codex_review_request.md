# 19-P-5 Codex 검증 요청서 (revision 3 — r2 caveat 잔여 동기화)

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-02 | **fail** ([reports/refactor/19-P-5_codex_review.md](19-P-5_codex_review.md), G-2 fail — §3-1 예약/§3-5 휴무 차단 "있음" 과장 + §4/§9 분류 숫자 9/7/4 vs 실제 표 6/9/5 불일치 + §2-5 db_guard 표현 부정확) | 초기 작성 |
| r2 | 2026-05-02 | **pass with caveat** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r2 — G-2 본문 정정 pass, 단 요청서 §9/§13 잔여 9/7/4 문구 caveat) | **4개 항목 보정**. (1) §3-1 appointments 표 — 실제 [test_appointment_rules.py](../../tests/test_appointment_rules.py) 의 `xfail` 3건 / `skip` 1건 / 점심창·PUT·DELETE·409 부재 명시. (2) §3-5 leaves 표 — full/am/pm 차단 4건 모두 `xfail` 명시 ([test_therapist_leave.py](../../tests/test_therapist_leave.py)). (3) §4/§9 본문 종합 — 9/7/4 → **5 existing + 1 partial + 9 needed + 5 follow-up = 20** 정정. (4) §2-5 db_guard — "import-time 1회 + session fixture 1회" 정확 표기. |
| r3 | 2026-05-02 | (본 revision) | **r2 Codex caveat 잔여 동기화**. 본 요청서 §9 표 (9/7/4 → r2 정정 4분류) + §13 행 (`(20개 항목 9/7/4 분류)` → `(20개 항목 — r2 정정: 5 existing + 1 partial + 9 needed + 5 follow-up)`) 동기화. 전략 문서 본문은 r2 시점에 이미 정정됨 — 본 r3 는 요청서만 정합. 코드/테스트/spec/UI 무수정 유지. |

본 요청서는 19-P 단위화 리팩토링 다섯 번째 세션의 산출물 (테스트 전략 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0-A. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 Codex 판정: **pass / pass / pass with caveat / pass with caveat** ([reports/refactor/19-P-4_codex_review.md](19-P-4_codex_review.md))
- 19-P-5 r1 Codex 판정: **fail** ([reports/refactor/19-P-5_codex_review.md](19-P-5_codex_review.md))
- 19-P-5 r2 Codex 판정: **pass with caveat** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r2 — 본문 정정 pass, 요청서 §9/§13 잔여 9/7/4 문구 caveat)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 19-P-4 caveat 본 19-P-5 반영:
  - `leave_type=am/pm/full` 백엔드 차단 위치 미확인 → §3-1 / §3-5 / §4 / §6-A / §7-2-C 에서 **분리 직전 grep + contract 보강** 으로 명시. **r2 추가**: 현재 [test_therapist_leave.py](../../tests/test_therapist_leave.py) 에서 4건 모두 `xfail` 상태 — 백엔드 차단 코드 추가 + 정방향 전환 필요.
  - dependency_map 줄수 minor (620 vs 622) → 본 19-P-5 는 줄수 메타 무관 (실제 테스트 대상 우선).
  - pytest 미실행 → 본 19-P-5 도 read-only 문서 세션, pytest 실행은 19-P-6 이후 코드 이동 단계.
- 19-P-5 r1 caveat 본 r2 반영:
  - §3-1 / §3-5 표를 실제 `xfail`/`skip`/부재 상태에 맞게 재분류.
  - §4 / §9 종합 분류 숫자 정정 (5 existing + 1 partial + 9 needed + 5 follow-up = 20).
  - §2-5 `db_guard` 표현 정확화.
- 19-P-5 r2 caveat 본 r3 반영:
  - 본 요청서 §9 표 자체의 9/7/4 → 4분류 (r2 본문과 동기화).
  - §13 의 `(20개 항목 9/7/4 분류)` → `(20개 항목 — r2 정정: 5 existing + 1 partial + 9 needed + 5 follow-up)`.
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가/수정만 수행. 코드/테스트/spec/UI/migrations/requirements 무수정.

## 1. 세션 이름

**19-P-5 단위화 리팩토링 테스트 전략 문서 작성**

- 19-P-1 [현재 구조](../../docs/refactor/19_refactor_current_state.md), 19-P-2 [목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md), 19-P-3 [모듈 매핑](../../docs/refactor/19_refactor_module_map.md), 19-P-4 [의존성 맵](../../docs/refactor/19_refactor_dependency_map.md) 의 후속 문서.
- 단위화 리팩토링을 시작하기 전에, 기존 기능이 깨지지 않도록 **모듈별 테스트 전략과 필수 회귀 테스트 기준** 을 문서화.
- read-only 문서 세션. 실제 코드 / 테스트 / fixture / mock 미작성.

## 2. 이번 세션 목표

| # | 목표 | 본문 위치 |
|---|---|---|
| 1 | §1 테스트 전략 원칙 T-1 ~ T-15 (15개) — 구조 변경 / 동치 / API URL / 응답 key / DB schema / 한 세션 한 모듈 / 5회 루프 / Codex 게이트 / 하네스 약화 ⊥ / 운영 DB ⊥ / 외부 API ⊥ / local-first / per-file-ignores / `manual60=1` | docs/refactor/19_refactor_test_strategy.md §1 |
| 2 | §2 전체 공통 테스트 — run_check.bat + pytest + ruff + check_db_path + 18 시리즈 하네스 6개 + AI 회귀 7개 + API contract + 운영 DB 보호 5단계 + PyInstaller 검증 시점 | §2 |
| 3 | §3 모듈별 필수 테스트 전략 (16 영역) — appointments / patients / therapists / doctors(부분) / leaves / treatments / stats / sms / admin / backup / ai / calendar / notes / health / audit / export_import | §3 |
| 4 | §4 리팩토링 전 보강해야 할 테스트 20개 항목 분류 — 보강 필요 / 기존 테스트 있음 / 후속 검토 | §4 |
| 5 | §5 테스트 우선순위 — 최우선 6 / 중요 5 / 후속 10 | §5 |
| 6 | §6 테스트 실행 정책 — 세션 시작 / 종료 / 큰 모듈 이동 후 / PyInstaller 시점 / 5회 루프 | §6 |
| 7 | §7 주석 / 문서화 기준 (테스트 / 위험 지점) — COMPAT 8 / SAFETY 12 / NOTE+RISK 14 / 테스트 fixture 5 / TODO 11 | §7 |

## 3. 작성한 문서

### 신규 (r1, 1차 작성)

- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) — 테스트 전략 (§0 ~ §9). 19-P-5 r1 작성.
- [reports/refactor/19-P-5_codex_review_request.md](19-P-5_codex_review_request.md) (본 문서, 영구 보존본)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### r2 수정 (Codex r1 fail 보정)

- `docs/refactor/19_refactor_test_strategy.md` — 표제 r2 + §0 r2 보정 이력 + §0-2 r1 Codex 지적 반영 + §3-1 appointments 표 (`xfail` 3건 / `skip` 1건 / 점심창·PUT·DELETE·409 부재) + §3-5 leaves 표 (full/am/pm 차단 4건 모두 `xfail`) + §4-1 종합 분류 + §2-5 db_guard 표현 정확화 + §9 종합 정정.
- `reports/refactor/19-P-5_codex_review_request.md` — r2 revision 추가 + §0/§3/§5/§15 정합.
- `reports/refactor/latest_codex_review_request.md` — 본 문서와 동기화.

### Codex 작성 예정

- [reports/refactor/19-P-5_codex_review.md](19-P-5_codex_review.md) (영구) — r1 본문은 이미 작성됨 (fail 판정). r2 재검증 결과는 본 파일에 추가 또는 별도 r2 review 파일.
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 4. 수정 금지였던 범위

11개 금지 항목 (사용자 명시):
1. 코드 수정 / 2. `app/` 기능 코드 수정 / 3. `tests/` 테스트 코드 작성 / 4. migration 생성 / 5. `requirements.txt` 수정 / 6. PyInstaller spec 수정 / 7. UI 수정 / 8. 기존 API 응답 구조 변경 / 9. 운영 DB 접근 / 10. 실제 외부 API 호출 / 11. 하네스/테스트 약화

추가:
- 18-8 baseline 회귀 보호 (529 passed, 1 skipped, 7 xfailed).
- m001~m013 diff 0.
- 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 산출물 무수정.

## 5. 실제 수정한 파일 목록

### r1 신규 (3, 1차 작성)

- `docs/refactor/19_refactor_test_strategy.md`
- `reports/refactor/19-P-5_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### r2 수정 (3, Codex r1 fail 보정)

- `docs/refactor/19_refactor_test_strategy.md` — §0 r2 보정 이력 + §0-2 r1 Codex 지적 반영 + §3-1 / §3-5 표 실측 정합 + §2-5 db_guard 표현 + §4-1 종합 분류 + §9 종합 정정
- `reports/refactor/19-P-5_codex_review_request.md` — r2 revision 추가
- `reports/refactor/latest_codex_review_request.md` — 본 문서와 동기화

### r3 수정 (2, Codex r2 caveat 잔여 동기화)

- `reports/refactor/19-P-5_codex_review_request.md` — r3 revision + §0/§9/§13 정합
- `reports/refactor/latest_codex_review_request.md` — 본 문서와 동기화

> r3 는 요청서만 정합 — 전략 문서 본문 (`19_refactor_test_strategy.md`) 은 r2 시점에 이미 정정됨, 본 r3 단계에서 추가 수정 0.

### 무수정 (회귀 보호) — r1 / r2 / r3 동일

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1~19-P-4 산출물.

> `latest_codex_review_request.md` 는 19-P-5 진입점으로 덮어쓰여진다 (19-P-4 본문은 `19-P-4_codex_review_request.md` 영구 보존).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

| 검사 | 결과 |
|---|---|
| 본 19-P-5 신규 파일 | `19_refactor_test_strategy.md` + `{19-P-5,latest}_codex_review_request.md` (3개) |
| `app/**` / `tests/**` / migrations / spec / UI / `pyproject.toml` 변경 | 0 |
| 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 산출물 변경 | 0 |
| 새 fixture / mock / harness 파일 추가 | 0 |
| 새 contract 테스트 추가 | 0 (전략 문서만 — 19-P-6+ 에서 보강) |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 + 본 19-P-5 추가 변경분 0
ls docs/refactor/
ls reports/refactor/
```

> **dirty/untracked 표현 (19-P-3 caveat 반영)**: 본 19-P-5 산출 = 신규 문서 3개. 18-0~18-8 변경분 (m012/m013, AI RAG/knowledge/vector, harness/test) 은 작업트리에 dirty/untracked 로 남아 있지만 본 세션과 무관.

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3)
- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (19-P-3)
- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) (19-P-4 r2)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (local-first / 5회 루프 / Codex 게이트)
- [docs/ai_code_session_protocol.md](../../docs/ai_code_session_protocol.md) (14단계 절차)
- [docs/releases/18_ai_rag_final_checklist.md](../../docs/releases/18_ai_rag_final_checklist.md) (18-8 baseline)
- [docs/ai_rag_test_plan.md](../../docs/ai_rag_test_plan.md) (RAG 테스트 정책)
- [docs/harnesses/full_harness_plan.md](../../docs/harnesses/full_harness_plan.md) (Full Harness 설계)
- [reports/refactor/19-P-4_codex_review.md](19-P-4_codex_review.md) (직전 r2 pass with caveat)

## 8. 모듈별 테스트 전략이 빠짐없이 정리되었는지 확인할 항목

| 영역 | 본 문서 위치 | Codex 검증 포인트 |
|---|---|---|
| appointments | §3-1 | 점심창 / 낙관적 락 / 충돌 / 휴무 차단 / `am`/`pm`/`full` 백엔드 차단 / 응답 키 contract |
| patients | §3-2 | CRUD / 검색 / 메모 / 중복 검사 / PII 마스킹 |
| therapists | §3-3 | role=therapist 분기 / alias 이중 키 / `can_eswt` `can_manual` / `hire_date` |
| doctors / medical_staff | §3-4 | **부재 항목 단정 X** — `Patient.doctor_id` / `Department` / `Room` / `DoctorSchedule` / `Order` / `Prescription` / EMR 모두 후속 검토 |
| leaves | §3-5 | `leave_type=am/pm/full` 차단 / `leave_kind` annual/monthly / `_upsert_employee_leave_core` 단일 진실원천 / HMAC + TOCTOU |
| treatments | §3-6 | `manual60=1` 보존 / 완료체크 + revert / `count_increment` 정책 |
| stats | §3-7 | 8 endpoint contract (C-7) + 엑셀 export + manual_counts + 의사 분기 |
| sms | §3-8 | 응답 키 (C-2/C-3) + 외부 HTTP mock + API key 마스킹 + 자동 발송 트리거 ⊥ |
| admin / settings | §3-9 | system-settings + AI 모드 + API key 비노출 + 5회 잠금 + `/api/about/*` (C-5) |
| backup | §3-10 | 자동/수동 백업 + atomic rename + integrity_check + 운영 DB 격리 |
| ai / rag | §3-11 | local_first 게이트 / `local_only` 호출 0 / sources 없음 / low_confidence / PII / unknown_feature / API key 없어도 local 동작 |
| calendar / schedule_view | §3-12 | post-19-P 후속 검토 (UI 분리 비-목표) |
| notes | §3-13 | `Patient.memo` vs `Appointment.memo` / 통합 후속 |
| health / diagnostics | §3-14 | post-19-P 후속 (`/api/health` 부재) |
| audit / logs | §3-15 | PII 원문 ⊥ / 200자 cap / API key ⊥ / `audit()` 시그니처 보존 |
| export_import | §3-16 | 엑셀 export / `data-convert/preview/apply` (C-6) / `_dc_*` 정규화 |

### Codex 검증 명령

```bash
# 모듈별 테스트 파일 확인
ls tests/test_*.py | grep -E "appointment|employee|therapist|stats|patient|sms|backup|admin|ai_"
# 응답 키 contract 보강 위치 확인
grep -n "leave_type\|am\|pm\|full" app/routers/api.py app/services/ai/action_leave.py | head -20
grep -n "manual60\|count_increment" app/models/constants.py
grep -nE "^@router\." app/routers/api.py | wc -l   # 86 endpoint
grep -nE "^@router\." app/routers/ai.py | wc -l    # 13 endpoint
```

## 9. 리팩토링 전 보강해야 할 테스트가 현실적인지 확인할 항목

§4 의 20개 항목 분류 (본 문서 §4 / §4-1, **r2 정정 — r3 잔여 동기화**):

| 분류 | 개수 | 항목 # | 비고 |
|---|---|---|---|
| **기존 테스트 있음** (분리 직전 응답 키 contract / 단언만 추가) | 5 | 3 / 7 / 8 / 9 / 10 | 완료체크 / 프론트 키 (manual_qa) / AI 하네스 / 운영 DB 보호 / PyInstaller |
| **기존 일부 있음 + 보강 다수 필요** (`xfail`/`skip`/부재 다수) | 1 | 1 | 예약 핵심 — `test_appointment_rules.py` 의 도수 중복 차단 3건 `xfail`, 취소-후-중복 `skip`, 점심창/PUT/DELETE/409 부재 |
| **보강 필요** (분리 직전 신규 테스트 작성) | 9 | 2 / 4 / 5 / 6 / 11 / 12 / 13 / 14 / 15 | 휴무 차단 (am/pm/full 백엔드 — `xfail` 4건) / 통계 8 endpoint (C-7) / 문자 응답 키 (C-2) / 비-AI contract (C-1) / 환자 검색·메모 / 의사 분기 / about/check-update (C-5) / data-convert (C-6) / ai/action (C-4) |
| **후속 검토** (현재 부재 — post-19-P) | 5 | 16 / 17 / 18 / 19 / 20 | 노쇼·반복예약·자원 / 출력물·알림 / export 확장 (CSV/EMR) / 권한 다중 등급 / AI 의사 가드 |
| **합계** | **20** |  |  |

> r1 시점의 "9 existing / 7 needed / 4 follow-up" 표기는 폐기됨. r2 본문 §4-1 + §9 종합 정합. r3 에서 본 표 자체도 동기화 (Codex r2 caveat 1번 정합).

### Codex 검증 포인트

- 보강 필요 항목이 19-P-4 caveat (`am`/`pm`/`full`) + C-1~C-7 (19-P-1) + 의사 분기 (M-03b) + `data-convert` (C-6) 와 정합한지.
- 후속 검토 항목이 실제로 부재 (모델 / 응답 / endpoint) 한지 코드로 확인.

```bash
# 부재 항목 확인
grep -nE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription" app/models/models.py   # 0건 기대
grep -n "doctor_id" app/models/models.py   # Patient 에 0건 기대
```

## 10. 기존 하네스 / 테스트 약화 금지 원칙이 반영되었는지 확인할 항목

§1 T-10 / T-11 / T-12 / T-13 + §2-5 + §7-2-B 에 명시:

| 원칙 | 본 문서 위치 |
|---|---|
| `tests/conftest.py` 4단계 격리 (APPDATA + DOSU_DB_PATH + 워커 no-op + SDK block) 약화 ⊥ | §1 T-10 / §2-5 S-2 / §7-2-B |
| `_block_sdk_modules` 약화 ⊥ | §2-5 S-4 / §7-2-B |
| `tests/harness/db_guard.assert_safe_db_path()` 약화 ⊥ | §2-5 S-3 / §7-2-B |
| `scripts/check_db_path.py` 머지 게이트 | §2-1 C-4 / §2-5 S-1 / §7-2-B |
| 실패 테스트 `xfail`/`skip` 으로 덮지 X (원인 수정) | §1 T-10 |
| `pyproject.toml` `app/**` per-file-ignores 보존 | §1 T-14 / §7-2-C |
| `manual60` `count_increment=1` 보존 (CLAUDE.md 명시) | §1 T-15 / §3-6 / §7-2-C |
| `LOW_SCORE_THRESHOLD=2` / `HIGH_THRESHOLD=0.7` / `LOW_THRESHOLD=0.3` / `LLM_CALL_THRESHOLD=0.3` / `QUERY_MIN_CHARS=2` 보존 | §3-11 / §7-2-C |

## 11. 주석 / 문서화 기준이 테스트 전략에 반영되었는지 확인할 항목

§7 5개 주석 카테고리 + 적용 위치:

| 카테고리 | 위치 |
|---|---|
| `# COMPAT:` | §7-2-A — manual_qa wrapper / health 4키 9키 / status 9 top-level / pipeline 응답 키 / therapist alias / leaves alias / `ENTITY_MAP` (8 위치) |
| `# SAFETY:` | §7-2-B — conftest 격리 / SDK 차단 / db_guard / check_db_path / pii.scan / `_safe_error_detail` / sha256 해시 / phone/SMS 마스킹 / PBKDF2 / require_admin / api_key 비노출 / AI ⊥ 도메인 (12 위치) |
| `# NOTE:` + `# RISK:` | §7-2-C — 점심창 / 낙관적 락 / `_bump_patient_count` / `manual60=1` / `leave_type` / `_upsert_employee_leave_core` / `_get_manual_*` / 임계치 상수 / reindex lock / atomic rename / `ENTITY_MAP` / HMAC TOCTOU / spec hidden imports / daemon thread / per-file-ignores (14 위치) |
| `# NOTE:` (테스트 fixture) | §7-2-D — `FakeProvider.calls` 컨벤션 / harness fake_provider / seed_data / db_guard / contract (5 위치) |
| `# TODO(19-x):` | §7-2-E — C-1~C-7 / `am`/`pm`/`full` / 의사 분기 / AI 의사 가드 / `manual60` 직접 단언 (11 위치) |

> 본 19-P-5 세션은 코드 수정 X — 실제 코드 주석은 작성하지 않음. 후속 19-P-6+ 세션이 본 표를 가이드로 주석 추가.

## 12. 다음 단계 (19-P-6 롤아웃 계획) 진입 가능 판단 기준

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 본 19-P-5 추가 변경분 0. 19-P-1~19-P-4 산출물 무수정. |
| G-2 테스트 전략 정합 | §3 모듈별 16 영역의 현재 테스트 / 보강 필요 분류가 19-P-1 r2 (테스트 파일 40개, 하네스 12개) 와 100% 일치 |
| G-3 응답 키 / URL 후방호환 | §1 T-3 + §2-4 API contract + §7-2-A COMPAT 주석 지점에 33+ 키 셋 + alias 이중 키 명시 |
| G-4 AI/RAG local-first | §1 T-13 + §3-11 + §7-2-B SAFETY (AI ⊥ 도메인) 명시 |
| G-5 후속 검토 분류 | §3-4 doctors / §3-12 calendar / §3-14 health / §3-13 notes 통합 / §5-3 후속 10 모두 부재/후속 분류 |
| G-6 doctors / medical_staff 부재 항목 단정 X | §3-4 7개 부재 항목 (Department / Room / DoctorSchedule / Patient.doctor_id / Order / Prescription / EMR) 모두 후속 검토 |
| G-7 19-P-4 caveat 반영 | §0-1 / §3-1 / §3-5 / §4 / §6-A / §7-2-C 에서 `leave_type=am/pm/full` 백엔드 차단 grep + 보강 필수 명시 |
| G-8 PyInstaller 검증 시점 | §6-D 에 4단계 (53 hidden imports / migration spec / 실제 빌드 / exe smoke) + CLAUDE.md 배포 규칙 정합 |
| G-9 5회 루프 + Codex 게이트 | §1 T-7 / T-8 / T-9 + §6-E + §8 명시 |
| G-10 하네스 약화 ⊥ | §1 T-10 / §2-5 / §7-2-B 에 conftest 4단계 + SDK block + db_guard + check_db_path 보존 명시 |

→ G-1 ~ G-10 전부 통과 시 **yes — 19-P-6 롤아웃 계획 문서 진입 가능**.

## 13. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 무수정 | §5 / §6 |
| `docs/refactor/19_refactor_test_strategy.md` 작성 또는 수정 | §3 신규 |
| `reports/refactor/{19-P-5,latest}_codex_review_request.md` 작성 | §3 신규 |
| 예약/휴무/완료체크/통계/문자/AI/RAG 테스트 전략이 충분히 구체적인가 | §3-1, §3-5, §3-6, §3-7, §3-8, §3-11 |
| 의사/진료진 등 현재 기능이 없는 항목을 실제 구현된 것처럼 단정하지 않았는가 | §3-4 (7개 부재 항목 후속 검토) |
| local-first AI 테스트 기준이 유지되는가 | §3-11 / §1 T-13 / §7-2-B |
| 운영 DB 보호 / 외부 API 호출 금지 검사 포함되었는가 | §1 T-11 / T-12 + §2-5 + §7-2-B |
| PyInstaller 검증 시점 포함되었는가 | §2-6 / §6-D |
| 테스트 보강 필요 항목이 현실적으로 분류되었는가 | §4 (20개 항목 — r2 정정: 5 existing + 1 partial + 9 needed + 5 follow-up) |
| COMPAT / SAFETY / NOTE / RISK / TODO 주석 지점이 문서에 반영되었는가 | §7 (5 카테고리 + 위치 50개) |
| 다음 단계 19-P-6 롤아웃 계획 문서로 넘어가도 되는가 | §12 G-1 ~ G-10 |

## 14. Codex 검증 결과 기록 위치

- [reports/refactor/19-P-5_codex_review.md](19-P-5_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-P-5 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- G-1 ~ G-10: {결과 + 근거}

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-P-6 진입 권고
{yes / no + 근거}
```

## 15. Claude Code 자체 판단

**yes (19-P-6 진입 권고)** — Codex r2 가 이미 **pass with caveat — 진입 가능** 판정. 본 r3 는 r2 caveat 1개 (요청서 §9/§13 잔여 9/7/4) 동기화 보정만 — Codex 추가 재검증은 선택 사항 (19-P-6 진입 자체는 차단 X).

근거 (r3 기준):
1. 본 세션 (r1+r2+r3 통틀어) 은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `19_refactor_test_strategy.md` 9개 섹션 (§0~§9) — 원칙 15개 + 공통 테스트 + 모듈별 16 영역 + 보강 20 항목 + 우선순위 21 + 실행 정책 5 + 주석 지점 50 = 사용자 §1~§7 모두 커버.
3. 19-P-4 Codex r2 caveat 3개 모두 반영 — `am`/`pm`/`full` 보강 / 줄수 메타 무관 / pytest 미실행 (read-only 세션).
4. **r2 보정**: 19-P-5 r1 Codex G-2 fail 4개 항목 정정 — §3-1 appointments 표 (`xfail` 3 / `skip` 1 / 부재 다수 명시) / §3-5 leaves 표 (full·am·pm 차단 4건 모두 `xfail`) / §4 종합 (5+1+9+5=20) / §2-5 db_guard 표현 정확화.
5. 의사 / 진료진 부재 항목 7개 (§3-4) 모두 후속 검토 분류 — 실제 구현된 것처럼 단정 X (Codex r1 G-5/G-6 pass).
6. AI/RAG local-first 보존 — T-13 / §3-11 / §7-2-B (Codex r1 G-4 pass).
7. 응답 키 보호 — §1 T-3 + §2-4 + §7-2-A COMPAT (Codex r1 G-3 pass).
8. 운영 DB 보호 + 외부 API 차단 — §1 T-11 / T-12 + §2-5 (5단계) + §7-2-B (12 위치) (Codex r1 G-10 pass).
9. PyInstaller 검증 시점 — §2-6 / §6-D 에 4단계 명시 (Codex r1 G-8 pass).
10. 5회 루프 + Codex 게이트 — §1 T-7~T-9 + §6-E (Codex r1 G-9 pass).
11. 18-8 baseline 회귀 보호 100%.
12. 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 산출물 무수정.

남은 위험:
- T-1 ~ T-15 (19-P-2) 의사결정 항목 — 19-P-6 롤아웃 계획에서 점진 결정.
- 비-AI 86 endpoint contract 미작성 (C-1 ~ C-7) — 본 세션은 전략만, 실제 보강은 19-P-6+ 분리 직전.
- `leave_type=am/pm/full` 백엔드 차단 위치 미확인 + 현재 `xfail` 4건 — appointments / leaves 분리 직전 백엔드 차단 코드 + 정방향 전환 필수 (본 문서 §3-1 / §3-5 / §4 / §7-2-C 표시).
- 도수 중복 차단 `xfail` 3건 + 취소-후-중복 `skip` 1건 — appointments 분리 직전 백엔드 차단 코드 + 정방향 전환 필수 (본 문서 §3-1 표시).
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 별도 세션.
- 세션 경계 Git 검증 caveat — 18-0~18-8 미커밋 (이전 세션부터 알려진 사항).
