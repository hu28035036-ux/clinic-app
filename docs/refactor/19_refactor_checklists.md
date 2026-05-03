# 19-P-9 단위화 리팩토링 — 공통 체크리스트 (19_refactor_checklists)

> 19-P-1 [현재 구조](19_refactor_current_state.md), 19-P-2 [목표 아키텍처](19_refactor_target_architecture.md),
> 19-P-3 [모듈 매핑](19_refactor_module_map.md), 19-P-4 [의존성 맵](19_refactor_dependency_map.md),
> 19-P-5 [테스트 전략](19_refactor_test_strategy.md), 19-P-6 [롤아웃 계획](19_refactor_rollout_plan.md),
> 19-P-7 [위험 등록](19_refactor_risk_register.md), 19-P-8 [의사결정 기록](19_refactor_decision_record.md) 의 후속 문서.
>
> 19-x (19-0 ~ 19-14) **실제 코드 리팩토링 세션마다 반복 사용** 할 공통 체크리스트.
> 본 문서는 *체크리스트* 문서 — 실제 코드 / 테스트 / 폴더 / 파일 / fixture / mock / 마이그레이션 미생성.

## 0. 메타

- 작성일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 기준 커밋 (HEAD): `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed** ([reports/ai_dev_loop/18-8_test_report.md](../../reports/ai_dev_loop/18-8_test_report.md))
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 / 19-P-8 r1 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-9 진입 가능)** ([reports/refactor/19-P-8_codex_review.md](../../reports/refactor/19-P-8_codex_review.md))
- 본 세션 정책: **읽기 전용** — `app/`, `tests/`, `app/migrations/`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/`, `app/static/`, `pyproject.toml` 1바이트도 수정 금지.
- 본 문서는 *체크리스트* 문서 — 새 폴더 / 파일 / 테스트 / fixture / 마이그레이션 미생성.

### 0-1. 19-P-8 r1 Codex caveat 본 19-P-9 반영

| caveat | 19-P-9 반영 |
|---|---|
| 19-P-7 r3 결과 링크는 `latest_codex_review.md` 가 아니라 [reports/refactor/19-P-7_codex_review.md](../../reports/refactor/19-P-7_codex_review.md) 영구 보존본으로 고정 권장 | 본 19-P-9 § 메타 (§0) 의 19-P-1 ~ 19-P-8 판정 링크는 모두 영구 보존본 (`{19-P-N}_codex_review.md`) 사용. `latest_codex_review.md` 는 *진행 중 진입점* 으로만 사용. **§5 Codex 검증 체크리스트** 에 "결과 링크는 영구 보존본 (`{19-P-N}_codex_review.md`) 으로 고정" 명시. |
| `app/routers/api.py` 라인 수 5127 (bash `wc -l`) vs 5128 (PowerShell `Get-Content`) 의 1줄 drift | 본 §0-2 에 라인 수 측정 도구 / 결과 명시. 19-P-1 §1-2 + 19-P-8 §2-A 의 5127줄 표기는 bash 기준 (newline-terminated). PowerShell 기준 5128. 19-x 코드 세션에서 라인 수 인용 시 측정 도구 명시. endpoint 86개 / 도메인 분류는 영향 0. |
| PyInstaller "53 tests" 표현 — Codex 가 collect-only 독립 확인 못함 (.venv Python 런처 부재) | 본 §0-2 에 "53 tests" 산출 근거 명시 — `tests/test_pyinstaller_hidden_imports.py` 안 def test_ 함수 17개 중 15개 = non-parametrized + 2개 = parametrized (`EXPECTED_18_X_MODULES` 19개) → 15 + 19 + 19 = **53 tests** 실측. **§5 PyInstaller 체크리스트** 에 "53 tests" 산출 공식 명시. |

### 0-2. 본 19-P-9 측정 사실 (caveat 정합)

| 항목 | 값 | 측정 도구 / 근거 |
|---|---|---|
| `app/routers/api.py` 라인 수 (newline-terminated) | **5127** | bash `wc -l app/routers/api.py` |
| `app/routers/api.py` 라인 수 (PowerShell line count) | 5128 | Codex PowerShell `Get-Content` (19-P-8 caveat 2) |
| `app/routers/api.py` endpoint 수 | **86** | bash `grep -cE "^@router\." app/routers/api.py` |
| `app/routers/ai.py` 라인 수 | **929** | bash `wc -l app/routers/ai.py` |
| `app/routers/ai.py` endpoint 수 | **13** | bash `grep -cE "^@router\." app/routers/ai.py` |
| `app/templates/main.html` 라인 수 | **7331** | bash `wc -l app/templates/main.html` |
| `app/static/css/app.css` 라인 수 | **3626** | bash `wc -l app/static/css/app.css` |
| `tests/test_*.py` 파일 수 | **40** | `ls tests/test_*.py \| wc -l` |
| PyInstaller hidden imports 테스트 수 | **53 tests** = 15 non-parametrized + 19×2 parametrized | `tests/test_pyinstaller_hidden_imports.py` (def test_ 17개 + `EXPECTED_18_X_MODULES` 19 모듈 × 2 parametrized) |
| ORM 모델 수 | **19** | bash `grep -cE "^class \w+\(Base\)" app/models/models.py` |
| 마이그레이션 수 | **m001 ~ m013 (13개)** | `ls app/migrations/m0*.py` |

> **19-x 코드 세션에서 본 §0-2 표를 baseline 으로 사용**. 측정 도구가 다르면 1줄 drift 가능 — endpoint 수 / 도메인 분류는 영향 0.

### 0-3. 본 문서가 다루지 않는 범위

- 실제 코드 이동 / 테스트 작성 — 19-0 이후 별도 세션.
- m014+ 마이그레이션 도입 결정 — 본 19-P 비-목표 (19-P-2 P-4 정합).
- v1.4.0 배포 절차 — [docs/releases/18_ai_rag_final_checklist.md](../releases/18_ai_rag_final_checklist.md) 별도 게이트.
- 19-x 세션별 *세부* 계획 — 19-P-6 §3-0 ~ §3-14 가 이미 다룸. 본 문서는 *공통* 체크리스트만.

### 0-4. 본 문서의 위치

- 19-P-1 ~ 19-P-8 = 단위화 리팩토링 *준비 단계* 문서들 (8개).
- **19-P-9 (본 문서) = 19-x 실제 코드 세션이 매 세션 적용할 *체크리스트* 정리.**
- 다음 단계 = **19-P 최종 점검** (또는 **19-0 baseline 재고정**) — 19-P-1 ~ 19-P-9 산출물 cross-check + 진입 준비 완료 확인.

---

## 1. 세션 시작 전 체크리스트

> 19-x 세션 *진입 즉시* 다음 항목을 모두 확인 후 작업 시작. 한 항목이라도 실패 시 작업 중단 + 사용자 통보.

### 1-1. 공통 베이스 문서 확인

- [ ] [docs/AI_WORKING_RULES.md](../AI_WORKING_RULES.md) 읽음 (절대 원칙 + local-first)
- [ ] [docs/ai_code_session_protocol.md](../ai_code_session_protocol.md) 읽음 (14단계 절차)
- [ ] [docs/ai_docs_index.md](../ai_docs_index.md) 읽음 (문서 목차)
- [ ] [docs/ai_rag_current_state.md](../ai_rag_current_state.md) 읽음 (AI/RAG 현재 상태 — stale caveat 인지)
- [ ] [CLAUDE.md](../../CLAUDE.md) 읽음 (작업 규칙 + 배포 규칙)

### 1-2. 19-P 베이스 문서 확인

- [ ] [19_refactor_current_state.md](19_refactor_current_state.md) 읽음 (§0-2 baseline 측정값)
- [ ] [19_refactor_target_architecture.md](19_refactor_target_architecture.md) §1 P-1 ~ P-12 읽음
- [ ] [19_refactor_module_map.md](19_refactor_module_map.md) §2 모듈 매핑 읽음
- [ ] [19_refactor_dependency_map.md](19_refactor_dependency_map.md) §1 D-1 ~ D-13 + §2 의존성 맵 읽음
- [ ] [19_refactor_test_strategy.md](19_refactor_test_strategy.md) §1 T-1 ~ T-15 + §3 모듈별 전략 읽음
- [ ] [19_refactor_rollout_plan.md](19_refactor_rollout_plan.md) §1 R-1 ~ R-14 + §3-N (해당 세션) 읽음
- [ ] [19_refactor_risk_register.md](19_refactor_risk_register.md) §2 (해당 모듈 카테고리) 읽음
- [ ] [19_refactor_decision_record.md](19_refactor_decision_record.md) §2 (관련 DEC-*) 읽음

### 1-3. 해당 세션 목표 확인

- [ ] 세션 이름 = `{SESSION_NAME}` 추출 (예: `19-1_core`, `19-5_leaves`)
- [ ] 사용자 지시문에서 작업 목표 (한 문장) 추출
- [ ] 사용자 지시문에서 수정 가능한 파일 / 모듈 범위 추출
- [ ] 사용자 지시문에서 명시적 금지 항목 추출
- [ ] 추출 결과를 세션 첫 응답에 한국어 3 ~ 5줄 요약 후 작업 시작

### 1-4. 수정 가능 / 수정 금지 범위 확인

수정 가능 기본 범위 (사용자 지시문 명시):
- [ ] `app/modules/<domain>/` 신규 폴더 (해당 세션)
- [ ] `app/core/` 신규 폴더 (19-1 한정)
- [ ] `app/routers/api.py` / `app/routers/ai.py` 위임 wrapper (해당 세션)
- [ ] `dosu_clinic.spec` hidden imports 갱신 (신규 모듈 추가 시)
- [ ] 신규 contract 테스트 (`tests/test_<domain>_contract.py`)
- [ ] [docs/refactor/](.) 보정 (현재 구조 측정 변경 시)

자동 금지 범위 (사용자 지시문 명시 없으면 항상 금지):
- [ ] 운영 DB 경로 코드 (`app/config.py:get_db_path` / `app/core/config.py:get_db_path` 우선순위)
- [ ] [tests/conftest.py](../../tests/conftest.py) 4단계 격리 약화
- [ ] [tests/harness/](../../tests/harness/) 격리 로직 약화
- [ ] [pyproject.toml](../../pyproject.toml) `app/**` per-file-ignores 풀기
- [ ] 기존 AI 라우터 응답 스키마 (필드 제거 / 이름 변경 / 타입 변경)
- [ ] 기존 마이그레이션 파일 (역행 / 수정 — m001 ~ m013 diff 0)
- [ ] [app/models/models.py](../../app/models/models.py) ORM 19개 클래스명 / 컬럼명 / UNIQUE 제약 변경
- [ ] [app/templates/main.html](../../app/templates/main.html) JS / FullCalendar / Alpine 코드
- [ ] [app/static/](../../app/static/) CSS / vendor JS

### 1-5. 이전 세션 Codex 검증 결과 확인

- [ ] [reports/refactor/{직전 세션}_codex_review.md](../../reports/refactor/) 영구 보존본 읽음
- [ ] 직전 세션 caveat 본 세션 반영 여부 확인
- [ ] 직전 세션 판정이 **pass** 또는 **pass with caveat (yes 진입 가능)** 인지 확인
- [ ] 판정이 **fail** 또는 **no 진입** 이면 작업 중단 + 사용자 통보
- [ ] 검증 결과 링크는 영구 보존본 (`{19-P-N}_codex_review.md`) 사용 — `latest_codex_review.md` 는 진행 중 진입점 (덮어쓰기) 이므로 인용 ⊥

### 1-6. 관련 모듈의 현재 위치 확인

- [ ] 해당 도메인의 *현재* 코드 위치 확인 ([api.py](../../app/routers/api.py) / [ai.py](../../app/routers/ai.py) / [services/](../../app/services/))
- [ ] [19_refactor_module_map.md](19_refactor_module_map.md) §2-N (해당 모듈) 의 *현재 관련 파일* / *현재 관련 API* / *현재 DB* / *현재 UI* 항목과 실제 코드 일치 확인
- [ ] 일치 ⊥ 이면 *실제 구조와 문서 다름* 트리거 (19-P-8 §7 트리거 6) — 작업 중단 + 사용자 통보 + [19_refactor_current_state.md](19_refactor_current_state.md) 보정

### 1-7. 관련 API / DB / UI 영향 범위 확인

- [ ] 분리 대상 endpoint 카운트 ([19_refactor_current_state.md §3](19_refactor_current_state.md))
- [ ] 분리 대상 ORM 모델 + 컬럼 ([19_refactor_current_state.md §4](19_refactor_current_state.md))
- [ ] 분리 대상 main.html JS 의존 키 ([19_refactor_target_architecture.md §7-2](19_refactor_target_architecture.md))
- [ ] 분리 대상 sync `ENTITY_MAP` 키 영향 ([T-9](19_refactor_target_architecture.md))
- [ ] 외부 노드 호환 (sync) 영향 0 확인

### 1-8. rollback 가능성 확인

- [ ] `git revert <분리 commit>` 1회로 이전 상태 복원 가능
- [ ] 신규 폴더 / 파일 추가 + import 변경 + wrapper 만 — DB 마이그레이션 / 응답 키 / 동작 변경 동반 ⊥
- [ ] [19_refactor_rollout_plan.md §7](19_refactor_rollout_plan.md) RB-1 ~ RB-10 매핑
- [ ] 해당 세션의 위험도 (낮음 / 중간 / 높음) 확인

---

## 2. 코드 수정 전 체크리스트

> 코드 수정 *직전* (5회 루프 1회차 시작 직전) 다음 항목을 모두 확인.

### 2-1. 기존 API URL 유지

- [ ] 분리 대상 endpoint URL 그대로 — `/api/appointments/*`, `/api/ai/*`, `/api/sms/*` 등 [19_refactor_target_architecture.md §7-1](19_refactor_target_architecture.md) 표 정합
- [ ] FastAPI APIRouter `prefix` 만 모듈별 재할당 — URL 변경 0
- [ ] 호환 alias (`/api/therapists`, `/api/therapist-leaves[/bulk-set]`) 보존
- [ ] **DEC-C 절대 원칙** 위반 ⊥

### 2-2. 기존 응답 key 유지

- [ ] [19_refactor_current_state.md §21](19_refactor_current_state.md) 의 33+ 키 셋 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9 + 비-AI alias) 보존
- [ ] 해당 도메인의 응답 dict 키 dict 단위 비교 (분리 전후)
- [ ] **추가만 허용**, 제거 / rename / 타입 변경 ⊥
- [ ] 비-AI 86 endpoint contract 부재 (C-1) → **분리 직전 contract 테스트 신규 추가 필수**

### 2-3. 프론트 JS 의존성 확인

- [ ] [main.html](../../app/templates/main.html) 7331줄 + 인라인 JS 의존 키 (특히 `not_found` / `answer` / `confidence` / `sources[].title,path` / `version` / `treatment_codes` / `is_new_patient`) 보존
- [ ] FullCalendar event ID / start / end / status / version / treatment_codes 필드 보존
- [ ] Alpine bind 의존 응답 키 보존
- [ ] **DEC-C / P-3 / R-5** — UI 분리 ⊥ (19-P 비-목표)

### 2-4. DB schema 변경 필요 여부

- [ ] m001 ~ m013 diff 0 유지
- [ ] 컬럼 rename / 타입 변경 / 삭제 ⊥
- [ ] 신규 마이그레이션 m014+ 필요 시 → **본 세션 비-목표** + 별도 세션 분리 + 사용자 결정 (19-P-8 §7 트리거 4)
- [ ] **DEC-D 절대 원칙** 위반 ⊥

### 2-5. migration 필요 여부

- [ ] m014+ 마이그레이션 신규 필요 ⊥ (본 19-P 기간 내)
- [ ] 필요하다고 판단되면 → 작업 중단 + 사용자 결정
- [ ] [dosu_clinic.spec](../../dosu_clinic.spec) `hiddenimports` 의 마이그레이션 경로만 갱신 (자동 글롭)

### 2-6. 운영 DB 접근 위험 확인

- [ ] `%APPDATA%\도수치료예약\clinic.db` 미접근 — [scripts/check_db_path.py](../../scripts/check_db_path.py) 통과
- [ ] [tests/conftest.py](../../tests/conftest.py) 4단계 격리 약화 ⊥
- [ ] [tests/harness/db_guard.py](../../tests/harness/db_guard.py) `assert_safe_db_path()` 우회 ⊥
- [ ] **DEC-D / R-OPS-01 ~ R-OPS-03** 정합

### 2-7. 외부 API 호출 위험 확인

- [ ] [tests/conftest.py](../../tests/conftest.py) `_block_sdk_modules` (openai / anthropic SDK 차단) 우회 ⊥
- [ ] FakeProvider / FakeEmbeddingProvider 만 사용
- [ ] 실제 OpenAI / Anthropic / 문자나라 API 호출 ⊥
- [ ] **DEC-N / R-AI-06 / R-SMS-04** 정합

### 2-8. 기존 하네스 / 테스트 영향 확인

- [ ] AI 하네스 6개 (Full / RAG / Safety / Chunk / Reindex / Vector / Hybrid) 회귀 0 예상 확인
- [ ] 기존 SMS AI / 휴무 AI / 매뉴얼 Q&A 테스트 회귀 0 예상 확인
- [ ] [test_appointment_rules.py](../../tests/test_appointment_rules.py) xfail 3건 + skip 1건, [test_therapist_leave.py](../../tests/test_therapist_leave.py) xfail 4건 = 19-P 안에서 정방향 전환 시점 (19-4 / 19-5)
- [ ] 실패 테스트를 `xfail` / `skip` 으로 덮지 않는다 (원인 수정) — T-10 위반 ⊥

### 2-9. PyInstaller import 영향 확인

- [ ] 신규 modules 폴더 추가 시 [dosu_clinic.spec](../../dosu_clinic.spec) `hiddenimports` 갱신
- [ ] [test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) 53 tests (15 non-parametrized + 19×2 parametrized = 53) 통과 확인
- [ ] `collect_submodules` 실패 가드 / migrations 자동 글롭 / updater.bat post-build copy 정책 보존
- [ ] excludes (tkinter / matplotlib / numpy / pandas / PyQt5 / 6) 보존

---

## 3. 코드 이동 / 분리 체크리스트

> 코드 이동 / 분리 *진행 중* 다음 항목을 모두 만족.

### 3-1. router / service / repository / rules / schemas 책임 분리

- [ ] `router.py` = API endpoint 정의 + Depends 주입 + HTTPException raise — *비즈니스 로직 ⊥*
- [ ] `service.py` = 비즈니스 로직 + 트랜잭션 경계 — *DB 쿼리 ⊥* (repository 위임)
- [ ] `repository.py` = SQLAlchemy 쿼리 + ORM 접근 — *다른 모듈 service / repository 호출 ⊥*
- [ ] `schemas.py` = Pydantic In/Out 타입 — *순수 타입 정의*, DB / 외부 호출 ⊥
- [ ] `rules.py` = 업무 규칙 / 검증 — *순수 함수* / DB 미접근
- [ ] `availability.py` = 예약 가능 여부 / 충돌 — repository 만 (read-only)
- [ ] `completion_rules.py` = 완료체크 / 카운트 규칙 (manual60=1)
- [ ] `aggregators.py` = 통계 집계 함수 — repository 만
- [ ] `provider.py` = 외부 서비스 client — 외부 API 단일 경계
- [ ] `templates.py` = SMS 템플릿 CRUD — repository 만

### 3-2. repository 가 service 를 참조하지 않는지 확인

- [ ] D-3 위반 ⊥ — repository → models 만 import
- [ ] repository 가 다른 모듈 service / repository 호출 ⊥
- [ ] repository 가 router / rules / schemas 호출 ⊥

### 3-3. core 가 modules 를 참조하지 않는지 확인

- [ ] D-4 위반 ⊥ — core → modules import ⊥ (단방향)
- [ ] `core/config.py`, `core/database.py`, `core/security.py`, `core/feature_flags.py`, `core/time_utils.py`, `core/responses.py`, `core/errors.py` 모두 modules 미참조

### 3-4. 순환참조 위험 확인

- [ ] D-1 ~ D-13 의존성 방향 ([19_refactor_dependency_map.md §1](19_refactor_dependency_map.md)) 준수
- [ ] from → to 허용 / 금지 ([§6-1](19_refactor_target_architecture.md)) 정합
- [ ] `python -c "import app.main"` 정상 import 확인
- [ ] `dosu_clinic.spec` hidden imports 추가 후 `pytest tests/test_pyinstaller_hidden_imports.py -v` 53 tests 통과

### 3-5. 기존 import 경로 호환 wrapper

- [ ] 기존 `app.config` / `app.database` / `app.services.auth` import 경로 그대로 동작 (wrapper 보유)
- [ ] 신규 위치 (`app.core.config` / `app.core.database` / `app.core.security`) 도 동시 동작
- [ ] wrapper 에 `# COMPAT:` + `# TODO(19-x):` 주석 추가 (제거 시점 명시)

### 3-6. 기존 endpoint 유지

- [ ] FastAPI 라우터 prefix 만 재할당 — URL 변경 0
- [ ] 같은 URL 두 router 가 동시 등록되지 않도록 — 분리 *직전* / *직후* 한쪽만 활성 (T-12)
- [ ] 호환 alias (`therapist_id` 이중 키, `/api/therapists` alias) 보존

### 3-7. 내부 구현만 이동

- [ ] 응답 키 dict 빌드 위치만 이동 — 키 자체는 무변경
- [ ] 비즈니스 로직 함수 시그니처 무변경 (`_upsert_employee_leave_core`, `_bump_patient_count`, `_check_lunch_block`, `_check_version`, `_bump_version`, `_serialize_appointment` 등)
- [ ] 단순 위치 이동 + import 경로 갱신 + wrapper 추가 — 동작 변경 ⊥

### 3-8. 이동 전후 결과 동치

- [ ] 같은 입력 → 같은 응답 (dict 단위 비교)
- [ ] 회귀 테스트 (529 passed baseline) 100% 통과 유지
- [ ] 응답 키 33+ 셋 보존
- [ ] 사용자 PR 리뷰 시 *동작 변경 0* 입증 가능

---

## 4. 주석 / 문서화 체크리스트

> 19-P-8 DEC-S + 19-P-7 §6-1 / §6-2 + 19-P-3 §0-2 정합. 코드 주석 카테고리 = **COMPAT / SAFETY / NOTE / RISK / TODO / TEMP** (6종).

### 4-1. 새로 생성 / 분리한 파일

- [ ] 파일 상단에 1줄 docstring (역할 + 책임)
- [ ] 모듈명 / 책임 / 의존하는 다른 모듈 명시
- [ ] [CLAUDE.md](../../CLAUDE.md) "Default to writing no comments" — 의미 있는 주석만, *모든 줄 주석 ⊥*

### 4-2. 주요 service / rules / repository 함수

- [ ] 핵심 헬퍼 (`_upsert_employee_leave_core`, `_bump_patient_count`, `_check_lunch_block`, `_check_version`, `_serialize_appointment`, `_doctor_codes_set` 등) 에 1줄 docstring
- [ ] 함수 시그니처 보존 사실 명시 (해당 시)
- [ ] 다른 모듈에서 호출되는 단일 진실원천 함수는 *호출자* 명시

### 4-3. 기존 API / UI 호환 wrapper — `# COMPAT:`

- [ ] 기존 import 경로 wrapper (config / database / auth) 에 `# COMPAT:` + 호환 사유
- [ ] 응답 dict 빌더 (`_serialize_appointment` 등) 에 `# COMPAT:` + 응답 키 보존 명시
- [ ] alias 응답 (`therapist_id` 이중 키) 에 `# COMPAT:` + 프론트 의존 명시
- [ ] sync `ENTITY_MAP` 9개 키 위치에 `# COMPAT:` + 외부 노드 호환 명시
- [ ] FullCalendar event 형식 / version 필드 / status 필드 에 `# COMPAT:`

### 4-4. 개인정보 / 운영 DB / 외부 API 차단 부분 — `# SAFETY:`

- [ ] `core/config.py:get_db_path` 운영 DB 경로 차단 → `# SAFETY:`
- [ ] `core/security.py` PBKDF2 + 세션 + 5회 잠금 → `# SAFETY:`
- [ ] `modules/patients/notes_service.py` PII 비노출 → `# SAFETY:`
- [ ] `modules/audit/service.py` PII 원문 audit_log 부재 → `# SAFETY:`
- [ ] `modules/sms/provider.py` 외부 API 차단 / 자동 발송 트리거 ⊥ → `# SAFETY:`
- [ ] `modules/ai/router.py` provider 호출 게이트 → `# SAFETY:`
- [ ] `modules/ai/commands/action_leave.py` AI → 도메인 write 제한 → `# SAFETY:`
- [ ] `modules/settings/service.py` API key 원문 부재 → `# SAFETY:`
- [ ] `tests/conftest.py` `_block_sdk_modules` (수정 ⊥) → `# SAFETY:`

### 4-5. 업무 규칙 / 정책 — `# NOTE:` 또는 `# RISK:`

- [ ] 점심창 정책 ([api.py:64-107](../../app/routers/api.py:64) `_lunch_window` / `_check_lunch_block`) → `# NOTE:` 점심창 정책
- [ ] 휴무 차단 정책 (`leave_type=full/am/pm` 12:00 기준) → `# NOTE:` + `# RISK:` (devtools 우회 — 백엔드 검증 필수)
- [ ] 반차 허용 시간대 (오전반차의 오후 / 오후반차의 오전) → `# NOTE:`
- [ ] 도수 중복 차단 (manual30 / manual60 같은 슬롯 두 번째 차단) → `# NOTE:` + `# RISK:`
- [ ] manual60 = 1 카운트 정책 ([CLAUDE.md](../../CLAUDE.md)) → `# NOTE:` + 해당 정책 출처 명시
- [ ] approve / revert 시 done_count ±N → `# NOTE:` 완료체크 정책
- [ ] 통계 read-only (D-7) → `# NOTE:` read-only 정책
- [ ] SMS 자동 트리거 ⊥ (D-8) → `# NOTE:` 자동 트리거 ⊥ 정책
- [ ] AI / RAG → 도메인 DB 임의 생성 ⊥ (D-6) → `# NOTE:` local-first 절대 원칙
- [ ] 낙관적 락 TOCTOU (`_check_version` / `_bump_version`) → `# RISK:` TOCTOU
- [ ] AI commands HMAC 토큰 위변조 / TOCTOU → `# RISK:` TOCTOU
- [ ] reindex lock / backup atomic rename → `# RISK:` 동시성

### 4-6. TODO 는 세션 번호 / 제거 조건 포함 — `# TODO(19-x):`

- [ ] wrapper 보유 / 제거 시점 → `# TODO(19-x): wrapper 제거`
- [ ] xfail 정방향 전환 시점 → `# TODO(19-4): 도수 중복 차단 백엔드 코드 추가 + xfail → 정방향`
- [ ] post-19-P 후속 → `# TODO(post-19-P): modules/notes/ 통합` 등
- [ ] 단순 `# TODO:` (조건 없음) ⊥ — 19-P-7 §6-1 D-6 정합

### 4-7. 임시 wrapper / adaptor — `# TEMP:`

- [ ] 분리 직후 wrapper 가 동시 활성인 기간 → `# TEMP:` + `# TODO(19-x): 제거 시점`
- [ ] 임시 helper 함수 → `# TEMP:` + 영구 함수 위치 명시

### 4-8. 의미 없는 모든 줄 주석 ⊥

- [ ] 코드 자체가 자명한 부분에 설명 주석 ⊥
- [ ] 변수명 / 함수명이 의미를 표현하면 별도 주석 ⊥
- [ ] [CLAUDE.md](../../CLAUDE.md) "Don't explain WHAT the code does" 정합

### 4-9. 주석과 실제 코드 동작 일치

- [ ] 주석에 명시된 동작 / 정책이 실제 코드 동작과 일치
- [ ] 주석 변경 시 코드도 변경 (또는 반대) — 둘 사이 drift ⊥
- [ ] 본 세션 종료 시 grep `# COMPAT:` / `# SAFETY:` / `# NOTE:` / `# RISK:` / `# TODO\(` / `# TEMP:` 결과 검토

---

## 5. 테스트 체크리스트

> 19-P-5 §2 + §3 + §4 보강 9개 + AI 하네스 6개 통합. 5회 루프 내에서 실행.

### 5-1. 관련 모듈 테스트 실행

- [ ] 해당 도메인 회귀 테스트 ([test_<domain>_*.py](../../tests/))
- [ ] 분리 *직전* 신규 추가한 contract 테스트
- [ ] xfail 3건 + skip 1건 (appointments) / xfail 4건 (leaves) 는 해당 세션에서 정방향 전환 (19-4 / 19-5 한정)

### 5-2. API contract 테스트

- [ ] manual_qa contract — [test_ai_manual_rag_contract.py](../../tests/test_ai_manual_rag_contract.py), [test_ai_contract_manual.py](../../tests/test_ai_contract_manual.py)
- [ ] health contract — [test_ai_health_public.py](../../tests/test_ai_health_public.py), [test_ai_health_status.py](../../tests/test_ai_health_status.py)
- [ ] 비-AI 86 endpoint contract — 각 19-x 분리 *직전* 도메인별 신규 추가 (C-1)

### 5-3. 운영 DB 보호 검사

- [ ] `venv\Scripts\python.exe scripts/check_db_path.py` 통과 (운영 DB 경로 차단)
- [ ] [tests/conftest.py](../../tests/conftest.py) 4단계 격리 통과 (APPDATA + DOSU_DB_PATH + 워커 no-op + SDK block)
- [ ] [tests/harness/db_guard.py](../../tests/harness/db_guard.py) `assert_safe_db_path()` 통과 (import-time 1회 + session-scope fixture 1회)

### 5-4. 외부 API 호출 금지 확인

- [ ] [tests/conftest.py](../../tests/conftest.py) `_block_sdk_modules` 활성 확인
- [ ] `local_only` 모드에서 `len(provider.calls) == 0` + `len(embedding_provider.calls) == 0`
- [ ] 실제 OpenAI / Anthropic / 문자나라 API 호출 0

### 5-5. AI / RAG 하네스 유지

- [ ] 18-0 RAG / Safety / Full — [test_full_harness.py](../../tests/test_full_harness.py), [test_ai_full_harness.py](../../tests/test_ai_full_harness.py), [test_rag_pipeline.py](../../tests/test_rag_pipeline.py), [test_rag_safety.py](../../tests/test_rag_safety.py), [test_ai_safety_harness.py](../../tests/test_ai_safety_harness.py)
- [ ] 18-3 Chunker — [test_ai_chunker_harness.py](../../tests/test_ai_chunker_harness.py)
- [ ] 18-4 Reindex — [test_ai_reindex_harness.py](../../tests/test_ai_reindex_harness.py)
- [ ] 18-5 Vector — [test_ai_vector_harness.py](../../tests/test_ai_vector_harness.py)
- [ ] 18-6 Hybrid — [test_hybrid_retriever.py](../../tests/test_hybrid_retriever.py)
- [ ] 18-7 관리자 상태 — [test_ai_health_status.py](../../tests/test_ai_health_status.py), [test_admin_ui_smoke.py](../../tests/test_admin_ui_smoke.py)

### 5-6. 기존 SMS AI 테스트

- [ ] [test_ai_sms_validate.py](../../tests/test_ai_sms_validate.py)
- [ ] [test_ai_sms_draft.py](../../tests/test_ai_sms_draft.py)
- [ ] [test_ai_sms_draft_hallucination.py](../../tests/test_ai_sms_draft_hallucination.py)

### 5-7. 기존 휴무 AI 테스트

- [ ] [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) (parse / preview / execute + HMAC + TOCTOU + `_upsert_employee_leave_core` 호출 회귀)

### 5-8. pytest tests -v 실행

- [ ] 큰 모듈 분리 완료 직후 `venv\Scripts\python.exe -m pytest tests -v` (전체 회귀)
- [ ] 18-8 baseline 일치 확인 (529 passed, 1 skipped, 7 xfailed) — 또는 19-4 / 19-5 정방향 전환 후 baseline 갱신
- [ ] 작은 단위 변경 시는 `pytest tests/test_<domain>_*.py -v` 만 가능

### 5-9. ruff lint

- [ ] `venv\Scripts\python.exe -m ruff check app tests scripts` 통과
- [ ] [pyproject.toml](../../pyproject.toml) `app/**` per-file-ignores 보존 — *수정 ⊥* (T-14)

### 5-10. check_db_path

- [ ] `venv\Scripts\python.exe scripts/check_db_path.py` 통과
- [ ] 머지 게이트 — 실패 시 머지 ⊥

### 5-11. 통합 명령

- [ ] `run_check.bat` (pytest + ruff + check_db_path 통합) 통과
- [ ] 세션 시작 + 종료 시점에 모두 실행

### 5-12. PyInstaller 검증

- [ ] [test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) **53 tests** 통과 (산출 = 15 non-parametrized + 19×2 parametrized = 53, `EXPECTED_18_X_MODULES` 19개)
- [ ] [test_migration_spec_discovery.py](../../tests/test_migration_spec_discovery.py) 통과 (신규 마이그레이션 / 폴더 구조 변경 시)
- [ ] 실제 `pyinstaller --noconfirm dosu_clinic.spec` 빌드는 **주요 리팩토링 묶음 완료 후** + 19-14 종료 게이트 + 사용자 명시 승인 시 ([CLAUDE.md](../../CLAUDE.md) 배포 규칙)
- [ ] exe smoke (5 endpoint, 18-8 시점에 입증) 는 19-P 종료 시점 + v1.4.0 배포 직전

---

## 6. 모듈별 특수 체크리스트

### 6-1. appointments (19-9 + 19-4 availability)

- [ ] 예약 생성 / 수정 / 삭제 / 조회 결과 유지 (응답 dict 단위 비교)
- [ ] 예약 중복 방지 유지 — 도수 (manual30 / 60) 같은 슬롯 두 번째 차단 (R-APPT-02 — 19-4 백엔드 차단 코드 추가 + xfail 3건 → 정방향)
- [ ] 휴무 차단 유지 — `leave_type=full/am/pm` (R-APPT-03 — 19-4 / 19-5 백엔드 차단 코드 + xfail 4건 → 정방향)
- [ ] 반차 기준 12:00 유지 — `am` < 12:00 / `pm` >= 12:00 (R-APPT-04)
- [ ] API 응답 key 유지 (`id` / `patient_id` / `therapist_id` / `start_at` / `end_at` / `treatment_codes` / `status` / `version` / `memo` / `is_new_patient`) — R-APPT-01
- [ ] 점심창 차단 (`_check_lunch_block`) 유지 (R-APPT-05)
- [ ] devtools / manual POST 우회 방지 — 백엔드 검증 필수 (R-APPT-06)
- [ ] 낙관적 락 TOCTOU (`version` 컬럼) 유지 (R-LOCK-01)
- [ ] FullCalendar event 형식 / status / version 필드 보존
- [ ] [test_appointment_rules.py](../../tests/test_appointment_rules.py) xfail 3건 + skip 1건 → 정방향 (19-4)

### 6-2. leaves (19-5)

- [ ] 종일 (`full`) / 오전반차 (`am`) / 오후반차 (`pm`) 규칙 유지 (R-LEAVE-01)
- [ ] 휴무 표시와 예약 차단 *불일치 ⊥* (R-LEAVE-03 — 표시 leaves 모듈 / 차단 appointments.availability 모듈)
- [ ] devtools / manual POST 우회 방지 — 백엔드 검증 필수
- [ ] `_upsert_employee_leave_core` 시그니처 보존 — AI action_leave 가 같은 헬퍼 호출 (단일 진실원천)
- [ ] `(employee_id, leave_date)` UNIQUE (m011) 보존 (R-LEAVE-02)
- [ ] sync `ENTITY_MAP[employee_leave]` 키 보존 (외부 노드 호환)
- [ ] [test_therapist_leave.py](../../tests/test_therapist_leave.py) xfail 4건 → 정방향 (19-5)
- [ ] [test_employee_leave_unique_violation.py](../../tests/test_employee_leave_unique_violation.py) (m011 UNIQUE 회귀)
- [ ] [test_ai_action_leave.py](../../tests/test_ai_action_leave.py) (AI 호출 회귀)

### 6-3. treatments / completion_rules (19-6)

- [ ] 치료항목별 *개별 완료체크* 유지 — manual60 = 1 카운트 정책 ([CLAUDE.md](../../CLAUDE.md) 명시)
- [ ] *시간 가중치 방식* 으로 되돌아가지 않음 — `count_increment=2` 절대 ⊥ (R-TX-01)
- [ ] 통계 집계와 불일치 ⊥ (R-TX-04 — done_count 0 미만 방지 / Lazy 생성)
- [ ] approve / revert 흐름 유지 — `_bump_patient_count` ±N
- [ ] [app/models/constants.py:20](../../app/models/constants.py:20) `count_increment` dict 보존
- [ ] 의사 항목 (Treatment.role="doctor") / 도수치료 / 체외충격파 분기 유지

### 6-4. stats (19-11)

- [ ] 예약 기준 / 완료 기준 분리 유지 (R-STAT-01)
- [ ] 치료사별 / 치료항목별 / 시간대 / 요일별 집계 기준 유지 (R-STAT-02 ~ R-STAT-04)
- [ ] 신환 수 집계 유지 (`Appointment.is_new_patient`) (R-STAT-05)
- [ ] 의사 필터 (`is_doctor_filter`) 분기 유지 — staff.doctors_service 호출
- [ ] ManualCount upsert UNIQUE `(count_date, therapist_id, treatment_code)` 보존 (m006)
- [ ] read-only 정책 (D-7) — write ⊥
- [ ] 8 endpoint contract 부재 — 19-11 분리 직전 신규 추가
- [ ] 엑셀 export (manual-schedule.xlsx, stats.xlsx) 데이터 조립 stats / 파일 생성 export_import

### 6-5. sms (19-10)

- [ ] 문자 대상 추출 (`tomorrow-targets`) 유지 (R-SMS-01)
- [ ] 문자 템플릿 CRUD 유지 (R-SMS-02 — sort_order=1 기본 템플릿)
- [ ] 테스트 중 *실제 외부 발송 ⊥* (R-SMS-04 — 외부 HTTP mock + `_block_sdk_modules` 정합)
- [ ] 문자나라 계정 / API key 노출 ⊥ — `munjanara_key` 마스킹 보존 (R-SMS-03)
- [ ] 자동 발송 트리거 ⊥ — 예약 변경 시 SMS 자동 발송 ⊥ (D-8 / R-SMS-05)
- [ ] `provider.py` 외부 HTTP 단일 경계 — timeout / 응답 디코딩 / `_smart_decode_response` 정책 보존
- [ ] `_normalize_phone_for_sms` / `_is_valid_kr_mobile` / `_mask_phone_for_log` / `_sms_sanitize` 보존

### 6-6. patients / notes (19-7)

- [ ] 개인정보 로그 노출 ⊥ — PII 원문 audit_log / AiUsageLog / 응답 부재 (R-PAT-01)
- [ ] 신환 체크 유지 (`Appointment.is_new_patient`)
- [ ] 당일 메모 / 지속 메모 경계 유지 — `Patient.memo` (지속) / `Appointment.memo` (당일) (R-PAT-04 ~ R-PAT-05)
- [ ] 환자 검색 (이름 / 연락처 / 차트번호 인덱스) 유지 (R-PAT-03)
- [ ] 중복 검사 (`_check_patient_duplicate`) 유지
- [ ] counts dict 키 보존 (R-PAT-02)
- [ ] data-convert (~600줄 `_dc_*` 헬퍼) 는 export_import 로 분리 (M-12)
- [ ] 통합 `modules/notes/` 신설은 post-19-P 후속 (M-27)

### 6-7. admin / settings (19-2 + 19-12)

- [ ] 관리자 전용 기능 노출 주의 — `require_admin` 의존 86 endpoint 중 분리 도메인 영향 0 (R-ADM-01)
- [ ] API key 원문 노출 ⊥ — 모든 응답에 `api_key_set` boolean 만 / `api_key_masked` 부재 (R-ADM-02)
- [ ] feature flag 분산 ⊥ — `core/feature_flags.py` 단일 진입점 (T-8 / R-ADM-04)
- [ ] PBKDF2 / `SESSION_TTL_SEC` / `MAX_FAILURES` 정책 보존 (`core/security.py`)
- [ ] AI 모드 (`local_only` / `local_first` / `ai_assist`) 단일 진입점 (R-ADM-03)
- [ ] `auto_backup_keep_count` / `manual_slot_limit` 정책 보존 (R-ADM-05)
- [ ] 자동 업데이트 (about/check/download/apply) 보존 (M-16)

### 6-8. ai / rag (19-13)

- [ ] **local-first 유지** — 외부 API 토큰 최소, 내부 처리 우선 (DEC-N / R-AI-01)
- [ ] `local_only` 모드에서 LLM / Embedding 호출 0 — `len(provider.calls) == 0` + `len(embedding_provider.calls) == 0` (R-AI-02)
- [ ] sources 없음 / low_confidence / PII / unknown_feature 에서 **provider 호출 0** (R-AI-03)
- [ ] should_call_llm() 다층 게이트 (provider_disabled / pii / local_only / no_sources / low_confidence) 보존 (R-AI-04)
- [ ] AI / RAG → 도메인 DB 임의 생성 ⊥ (D-6 / R-AI-05)
- [ ] AI commands → leaves.service (write) 만 허용 / appointments / patients (write) ⊥ (DEC-O)
- [ ] HMAC 토큰 + TOCTOU 보존 (action_leave parse / preview / execute)
- [ ] PII 원문 audit_log / AiUsageLog 부재 — sha256 해시만 저장 (R-AI-07)
- [ ] 기존 RAG / Safety / Vector / Hybrid 하네스 유지 (5-5)
- [ ] LOW_SCORE_THRESHOLD=2 / HIGH/LOW THRESHOLD 0.7/0.3/0.3 / QUERY_MIN_CHARS=2 보존
- [ ] AI 의사 가드 (`_RE_MEDICAL_CLAIM` 등) 강화는 post-19-P 후속 (M-36)

---

## 7. 실패 대응 체크리스트

> [docs/AI_WORKING_RULES.md §3](../AI_WORKING_RULES.md) 5회 루프 정책 + DEC-T Codex 게이트.

### 7-1. 테스트 실패 원인 기록

- [ ] 실패 메시지 / 로그 / 관련 파일 분석 → 가설 작성
- [ ] 회차별 가설 / 변경 / 결과를 임시 메모로 보존

### 7-2. 수정 루프 횟수 기록

- [ ] 1회차 / 2회차 / 3회차 / 4회차 / 5회차 명시적 카운트
- [ ] 1회차 = 테스트 + 분석 + 수정
- [ ] 2~5회차 = 가설 기반 최소 수정 + 다시 테스트

### 7-3. 최대 5회까지만 수정

- [ ] 5회 초과 ⊥ — 부분 수정 즉시 중단
- [ ] 땜질식 수정 ⊥ — 5회 안에 통과 못하면 *원인 재분석*

### 7-4. 5회 실패 시 latest_failure_report.md

- [ ] [reports/ai_dev_loop/latest_failure_report.md](../../reports/ai_dev_loop/) 작성
- [ ] [reports/ai_dev_loop/{19-x}_failure_report.md](../../reports/ai_dev_loop/) 영구 보존본 작성
- [ ] 시도 회차별 가설 / 변경 / 결과
- [ ] 마지막 테스트 출력
- [ ] 코드 재작성 / 설계 재검토 권고

### 7-5. 땜질식 수정 중단

- [ ] 실패 테스트를 `xfail` / `skip` 으로 덮지 않는다 — 원인 수정 (T-10)
- [ ] 격리 / 시드 / 가드를 우회하지 않는다
- [ ] [pyproject.toml](../../pyproject.toml) `app/**` per-file-ignores 풀지 않는다 (T-14)
- [ ] DB 컬럼 / API URL / 응답 키 임의 변경 ⊥

### 7-6. rollback 또는 재작성 판단

- [ ] [19_refactor_rollout_plan.md §7](19_refactor_rollout_plan.md) RB-1 ~ RB-10 매핑
- [ ] rollback = `git revert <분리 commit>` 1회로 복원
- [ ] 재작성 = 원인 분석 + 설계 변경 + 별도 세션 (사용자 결정)
- [ ] 본 세션 종료 + 사용자 통보 + 19-x 계획 재조정

### 7-7. Codex 검증 요청 문서 작성

- [ ] [reports/refactor/latest_codex_review_request.md](../../reports/refactor/) 작성 (성공 / 실패 무관)
- [ ] [reports/refactor/{19-x}_codex_review_request.md](../../reports/refactor/) 영구 보존본 작성
- [ ] **Codex 검증 통과 전 다음 세션 진입 ⊥** (DEC-T)

---

## 8. 완료 체크리스트

> 5회 루프 안에 통과 시 본 체크리스트 적용. 실패 시 §7 적용.

### 8-1. 변경 파일 목록 기록

- [ ] `git diff --stat` 결과 기록
- [ ] 신규 / 수정 / 삭제 파일 분류
- [ ] 신규 폴더 (`app/modules/<domain>/`, `app/core/`) 명시

### 8-2. 이동한 로직 기록

- [ ] 함수 / 클래스 단위로 *이동 전 위치 → 이동 후 위치* 매핑
- [ ] 헬퍼 함수 (`_lunch_window`, `_check_version`, `_bump_patient_count` 등) 이동 정합
- [ ] [19_refactor_module_map.md](19_refactor_module_map.md) §2-N 의 매핑과 일치

### 8-3. 유지한 wrapper / adaptor 기록

- [ ] 기존 import 경로 wrapper 위치
- [ ] wrapper 보유 기간 (다음 세션 / 19-14 종료 게이트)
- [ ] `# COMPAT:` + `# TODO(19-x):` 주석 추가 확인

### 8-4. API 응답 key 유지 확인

- [ ] 응답 dict 키 dict 단위 비교 (분리 전후) — 동일
- [ ] 33+ 키 셋 ([19_refactor_current_state.md §21](19_refactor_current_state.md)) 보존
- [ ] 비-AI alias (`therapist_id` 이중 키) 보존
- [ ] sync `ENTITY_MAP` 키 보존

### 8-5. 테스트 결과 기록

- [ ] `run_check.bat` 결과 (pass/fail + 카운트)
- [ ] `pytest tests -v` 결과 (529 passed baseline 또는 갱신값)
- [ ] AI 하네스 6개 결과
- [ ] 분리 직전 신규 추가한 contract 테스트 결과
- [ ] PyInstaller 53 tests 결과
- [ ] [reports/ai_dev_loop/latest_test_report.md](../../reports/ai_dev_loop/) 작성
- [ ] [reports/ai_dev_loop/{19-x}_test_report.md](../../reports/ai_dev_loop/) 영구 보존본 작성

### 8-6. 남은 위험 기록

- [ ] [19_refactor_risk_register.md](19_refactor_risk_register.md) §2 의 영향 Risk ID 중 본 세션에서 *완화* 된 항목
- [ ] *남은* Risk ID — 다음 세션 / post-19-P 후속
- [ ] 본 세션에서 *발견* 한 신규 위험 — 19-P-7 갱신 후보

### 8-7. 주석 / 문서화 기준 적용 여부 기록

- [ ] §4 체크리스트 (4-1 ~ 4-9) 모두 통과
- [ ] grep `# COMPAT:` / `# SAFETY:` / `# NOTE:` / `# RISK:` / `# TODO\(` / `# TEMP:` 결과 검토
- [ ] 본 세션에서 추가한 주석 위치 / 카테고리 / 근거 결정 ID 기록
- [ ] [19_refactor_decision_record.md §6-2](19_refactor_decision_record.md) 의 위치 16개와 매핑

### 8-8. latest_test_report.md 작성

- [ ] [reports/ai_dev_loop/latest_test_report.md](../../reports/ai_dev_loop/) — 실행 명령 / 환경 / 통과/실패 카운트 / 주요 로그 발췌

### 8-9. latest_fix_summary.md 작성

- [ ] [reports/ai_dev_loop/latest_fix_summary.md](../../reports/ai_dev_loop/) — 변경 파일 목록 / 파일별 변경 요약 / 의도 / 이유

### 8-10. latest_codex_review_request.md 작성

- [ ] [reports/refactor/latest_codex_review_request.md](../../reports/refactor/) 작성 (§9 검증 요청 체크리스트 정합)
- [ ] [reports/refactor/{19-x}_codex_review_request.md](../../reports/refactor/) 영구 보존본 작성

### 8-11. 세션별 리포트 작성

- [ ] [reports/ai_dev_loop/{19-x}_test_report.md](../../reports/ai_dev_loop/) (영구)
- [ ] [reports/ai_dev_loop/{19-x}_fix_summary.md](../../reports/ai_dev_loop/) (영구)
- [ ] [reports/refactor/{19-x}_codex_review_request.md](../../reports/refactor/) (영구)
- [ ] *덮어쓰기 방지* — `latest_*` 와 `{19-x}_*` 둘 다 보존

### 8-12. Codex 검증 전 다음 세션 진행 ⊥

- [ ] 본 세션 종료 = Claude Code 자체 통과 확인 — *최종 완료 ⊥* (DEC-T)
- [ ] Codex 가 [reports/refactor/latest_codex_review_request.md](../../reports/refactor/) 시작점으로 *실제 diff / 파일 / 결과 / 로그* 독립 확인 후에만 다음 세션 진입
- [ ] Codex 판정 = **pass** 또는 **pass with caveat (yes 진입 가능)** 일 때만 다음 세션 진입
- [ ] **fail** 또는 **no 진입** 이면 본 절차 §4 / §7 1 ~ 10 다시 실행

---

## 9. Codex 검증 요청 체크리스트

> 각 19-x 실제 리팩토링 세션 완료 후 작성할 Codex 검증 요청 문서 표준.

### 9-1. 작성할 문서 (2개)

- [ ] [reports/refactor/latest_codex_review_request.md](../../reports/refactor/) (Codex 진입점 — 덮어쓰기)
- [ ] [reports/refactor/{19-x}_codex_review_request.md](../../reports/refactor/) (영구 보존본)

> *두 파일 내용 동일* — `Compare-Object` / `diff` 결과 0이어야 함.

### 9-2. 검증 요청 문서에 포함할 14개 항목

| # | 항목 | 본문 위치 |
|---|---|---|
| 1 | 세션 이름 (`19-x_<domain>`) | §1 |
| 2 | 작업 목표 (한 문장) | §2 |
| 3 | 변경 파일 목록 (신규 / 수정 / 삭제 분류) | §3 |
| 4 | 수정 가능 범위 | §4 |
| 5 | 수정 금지 범위 (11개 + 추가) | §5 |
| 6 | 실제 변경 요약 (이동한 로직 / wrapper / 새 contract 테스트) | §6 |
| 7 | 실행한 테스트 (run_check.bat / pytest / AI 하네스 / PyInstaller 53 / S-1~S-5) | §7 |
| 8 | 테스트 결과 요약 (529 passed baseline 또는 갱신값) | §8 |
| 9 | 수정 루프 횟수 (1 ~ 5) | §9 |
| 10 | API 응답 key 유지 여부 | §10 |
| 11 | 운영 DB 보호 여부 (check_db_path / 4단계 격리 / db_guard) | §11 |
| 12 | 외부 API 호출 여부 (`_block_sdk_modules` / FakeProvider) | §12 |
| 13 | 주석 / 문서화 기준 적용 여부 (COMPAT / SAFETY / NOTE / RISK / TODO / TEMP grep 결과) | §13 |
| 14 | 남은 위험 (19-P-7 Risk ID 매핑 + 신규 위험) | §14 |
| (15) | 다음 세션 진행 가능 여부 (yes / no + 근거) | §15 |

### 9-3. Codex 가 직접 검증할 명령 (권장)

```bash
# 코드 무수정 범위 확인
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 응답 키 / endpoint 카운트
grep -cE "^@router\." app/routers/api.py app/routers/ai.py
# 핵심 헬퍼 위치
grep -nE "_upsert_employee_leave_core|_bump_patient_count|_check_lunch_block|_check_version|_serialize_appointment|_doctor_codes_set|is_doctor_filter" app/ -r
# xfail / skip 카운트
grep -nE "xfail|skip" tests/test_appointment_rules.py tests/test_therapist_leave.py
# 응답 키 보호
grep -nE "sources|masked_question|top_score|confidence|not_found|blocked" app/services/ai/rag/pipeline.py
# 부재 항목 단정 ⊥
grep -nE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py   # 0건 기대
grep -n "doctor_id" app/models/models.py   # Patient 에 0건 기대
grep -n "no_show" app/models/models.py     # 0건 기대
# 주석 카테고리 grep
grep -nE "# (COMPAT|SAFETY|NOTE|RISK|TODO|TEMP):" app/ -r | head -30
# PyInstaller hidden imports 53 tests
venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -v --collect-only | head -60
```

### 9-4. Codex 검증 결과 기록 위치

- [ ] [reports/refactor/{19-x}_codex_review.md](../../reports/refactor/) (영구 보존본)
- [ ] [reports/refactor/latest_codex_review.md](../../reports/refactor/) (덮어쓰기)

> **인용 시 영구 보존본 (`{19-x}_codex_review.md`) 사용** — `latest_codex_review.md` 는 진행 중 진입점이라 다음 세션 검증으로 덮어쓰여짐 (19-P-8 caveat 1 정합).

### 9-5. 응답 형식 권장

```markdown
# {19-x} Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- G-1 ~ G-N: {결과 + 근거}

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 다음 세션 진입 권고
{yes / no + 근거}
```

### 9-6. 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

---

## 10. 종합

- 본 19-P-9 = 19-x 실제 코드 리팩토링 세션이 매 세션 적용할 *공통 체크리스트* 9개 섹션 (§1 ~ §9).
- §1 세션 시작 전 (8 항목) / §2 코드 수정 전 (9 항목) / §3 코드 이동 (8 항목) / §4 주석·문서화 (9 항목) / §5 테스트 (12 항목) / §6 모듈별 특수 (8 모듈) / §7 실패 대응 (7 항목) / §8 완료 (12 항목) / §9 Codex 검증 요청 (6 항목) = **총 79+ 체크 단위**.
- 모든 체크리스트는 19-P-1 ~ 19-P-8 산출물의 P-1 ~ P-12 / R-1 ~ R-14 / D-1 ~ D-13 / T-1 ~ T-15 / RB-1 ~ RB-10 / Risk ID 77 / DEC-A ~ DEC-T 와 정합.
- §6 모듈별 특수 체크리스트 = appointments / leaves / treatments / stats / sms / patients-notes / admin-settings / ai-rag (8 모듈) — 각 모듈의 핵심 위험 + 절대 보존 항목 명시.
- §4 주석 / 문서화 = COMPAT / SAFETY / NOTE / RISK / TODO / TEMP 6 카테고리 + DEC-S 정합.
- §7 실패 대응 = 5회 루프 정책 + rollback 기준 + latest_failure_report.md.
- §8 완료 = latest_test_report.md / latest_fix_summary.md / latest_codex_review_request.md + 영구 보존본 + Codex 검증 게이트.
- §9 Codex 검증 요청 = 14 항목 표준 + 검증 명령 + 응답 형식 + 영구 링크 권장 (19-P-8 caveat 1 정합).
- 19-P-8 caveat 3개 본 §0-1 + §0-2 + §5-12 반영 — 영구 링크 / api.py 라인 수 (5127 bash / 5128 PowerShell) / PyInstaller 53 tests 산출 공식 (15 + 19×2 = 53).
- 다음 단계 = **19-P 최종 점검** (19-P-1 ~ 19-P-9 cross-check + 19-0 진입 준비) 또는 **19-0 baseline 재고정** (사용자 결정 필요).
