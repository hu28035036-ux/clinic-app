# 19-P-9 Codex 검증 요청서

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-03 | (본 revision) | 초기 작성 — 19-P-9 단위화 리팩토링 공통 체크리스트 문서 신규 작성. 19-P-8 r1 Codex `pass with caveat (yes — 19-P-9 진입 가능)` 위에서 진행. **19-P-8 caveat 3개 본 19-P-9 §0-1 + §0-2 + §5-12 반영**. 코드/테스트/spec/UI/migrations/requirements 무수정. |

본 요청서는 19-P 단위화 리팩토링 아홉 번째 (마지막 준비 단계) 세션의 산출물 (공통 체크리스트 문서) 1건을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

---

## 0-A. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 / 19-P-8 r1 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-9 진입 가능)** ([reports/refactor/19-P-8_codex_review.md](19-P-8_codex_review.md) — 영구 보존본 링크, 19-P-8 caveat 1 정합)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 본 19-P-9 산출 측정 사실 (19-P-8 caveat 2/3 정합):
  - `app/routers/api.py` = 5127줄 (bash `wc -l`) / 5128줄 (PowerShell `Get-Content`) — 1줄 drift, endpoint 86개 / 도메인 분류 영향 0.
  - PyInstaller "53 tests" = 15 non-parametrized + 19×2 parametrized (`EXPECTED_18_X_MODULES` 19개) = **53 ✓** ([test_pyinstaller_hidden_imports.py](../../tests/test_pyinstaller_hidden_imports.py) 정적 검증).
- 19-P-8 r1 caveat 본 19-P-9 반영:
  - (1) 영구 링크 권장 — 본 §0-A + 본 19-P-9 산출 [docs/refactor/19_refactor_checklists.md §5-12 / §9-4](../../docs/refactor/19_refactor_checklists.md) 명시.
  - (2) api.py 5127 vs 5128 — 본 19-P-9 산출 [docs/refactor/19_refactor_checklists.md §0-2](../../docs/refactor/19_refactor_checklists.md) baseline 측정값 표 명시.
  - (3) PyInstaller "53 tests" 산출 공식 — 본 19-P-9 산출 [docs/refactor/19_refactor_checklists.md §5-12](../../docs/refactor/19_refactor_checklists.md) 명시.
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가만 수행. 코드/테스트/spec/UI/migrations/requirements 무수정.

## 1. 세션 이름

**19-P-9 단위화 리팩토링 공통 체크리스트 문서 작성**

- 19-P-1 [현재 구조](../../docs/refactor/19_refactor_current_state.md), 19-P-2 [목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md), 19-P-3 [모듈 매핑](../../docs/refactor/19_refactor_module_map.md), 19-P-4 [의존성 맵](../../docs/refactor/19_refactor_dependency_map.md), 19-P-5 [테스트 전략](../../docs/refactor/19_refactor_test_strategy.md), 19-P-6 [롤아웃 계획](../../docs/refactor/19_refactor_rollout_plan.md), 19-P-7 [위험 등록](../../docs/refactor/19_refactor_risk_register.md), 19-P-8 [의사결정 기록](../../docs/refactor/19_refactor_decision_record.md) 의 후속 문서.
- 19-x (19-0 ~ 19-14) **실제 코드 리팩토링 세션마다 반복 사용** 할 공통 체크리스트.
- read-only 문서 세션. 실제 코드 / 테스트 / fixture / mock / 마이그레이션 미작성.

## 2. 이번 세션 목표

| # | 목표 | 본문 위치 |
|---|---|---|
| 1 | §1 세션 시작 전 체크리스트 — 공통 베이스 / 19-P 베이스 / 세션 목표 / 수정 가능·금지 범위 / 직전 Codex 결과 / 모듈 위치 / API·DB·UI 영향 / rollback 가능성 (8 항목) | docs/refactor/19_refactor_checklists.md §1 |
| 2 | §2 코드 수정 전 체크리스트 — API URL / 응답 key / 프론트 JS / DB schema / migration / 운영 DB / 외부 API / 하네스 / PyInstaller (9 항목) | §2 |
| 3 | §3 코드 이동 / 분리 체크리스트 — router/service/repository/rules/schemas / D-3 / D-4 / 순환참조 / wrapper / endpoint 유지 / 내부 구현 이동 / 결과 동치 (8 항목) | §3 |
| 4 | §4 주석 / 문서화 체크리스트 — 파일 docstring / service docstring / COMPAT / SAFETY / NOTE / RISK / TODO / TEMP / 의미 없는 주석 ⊥ / 주석-코드 일치 (9 항목) | §4 |
| 5 | §5 테스트 체크리스트 — 모듈 회귀 / API contract / 운영 DB / 외부 API / AI 하네스 6개 / SMS AI / 휴무 AI / pytest -v / ruff / check_db_path / run_check.bat / PyInstaller 53 tests (12 항목) | §5 |
| 6 | §6 모듈별 특수 체크리스트 — appointments / leaves / treatments+completion_rules / stats / sms / patients+notes / admin+settings / ai+rag (8 모듈) | §6 |
| 7 | §7 실패 대응 체크리스트 — 원인 기록 / 루프 횟수 / 5회 한도 / latest_failure_report / 땜질 ⊥ / rollback / Codex 요청 (7 항목) | §7 |
| 8 | §8 완료 체크리스트 — 변경 파일 / 이동 로직 / wrapper / 응답 key / 테스트 결과 / 남은 위험 / 주석 적용 / latest_*.md / 영구 보존본 / Codex 게이트 (12 항목) | §8 |
| 9 | §9 Codex 검증 요청 체크리스트 — 작성 문서 2개 / 14 항목 표준 / 검증 명령 / 결과 기록 위치 / 응답 형식 / 최소 문구 (6 항목) | §9 |

## 3. 작성한 문서

### 신규 (3)

- [docs/refactor/19_refactor_checklists.md](../../docs/refactor/19_refactor_checklists.md) — 공통 체크리스트 (§0 ~ §10). 본 19-P-9 신규.
- [reports/refactor/19-P-9_codex_review_request.md](19-P-9_codex_review_request.md) (본 문서, 영구 보존본)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### Codex 작성 예정

- [reports/refactor/19-P-9_codex_review.md](19-P-9_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 4. 수정 금지였던 범위

11개 금지 항목 (사용자 명시):
1. 코드 수정
2. `app/` 기능 코드 수정
3. `tests/` 테스트 코드 작성
4. migration 생성
5. `requirements.txt` 수정
6. PyInstaller spec 수정
7. UI 수정
8. 기존 API 응답 구조 변경
9. 운영 DB 접근
10. 실제 외부 API 호출
11. 하네스/테스트 약화

추가:
- 18-8 baseline 회귀 보호 (529 passed, 1 skipped, 7 xfailed).
- m001~m013 diff 0.
- 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 / 19-P-7 / 19-P-8 산출물 무수정.

## 5. 실제 수정한 파일 목록

### 신규 (3)

- `docs/refactor/19_refactor_checklists.md`
- `reports/refactor/19-P-9_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1 ~ 19-P-8 산출물.

> `latest_codex_review_request.md` 는 19-P-9 진입점으로 덮어쓰여진다 (19-P-8 본문은 [19-P-8_codex_review_request.md](19-P-8_codex_review_request.md) r1 영구 보존).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

| 검사 | 결과 |
|---|---|
| 본 19-P-9 신규 파일 | `19_refactor_checklists.md` + `{19-P-9,latest}_codex_review_request.md` (3개) |
| `app/**` / `tests/**` / migrations / spec / UI / `pyproject.toml` 변경 | 0 |
| 19-P-1 ~ 19-P-8 산출물 변경 | 0 |
| 새 fixture / mock / harness 파일 추가 | 0 |
| 새 contract 테스트 추가 | 0 (체크리스트만 — 19-x 분리 직전 보강) |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
# 결과: 18-0~18-8 변경분만 + 본 19-P-9 추가 변경분 0
ls docs/refactor/
ls reports/refactor/
# 본 19-P-9 산출 측정 사실 재확인 (caveat 2/3 정합)
wc -l app/routers/api.py   # 5127 (bash) / PowerShell Get-Content 5128
grep -cE "^@router\\." app/routers/api.py app/routers/ai.py   # 86 / 13
grep -cE "^def test_" tests/test_pyinstaller_hidden_imports.py   # 17 (non-parametrized 15 + parametrized 2)
# EXPECTED_18_X_MODULES 19개 → parametrized 19×2 = 38, 합계 = 15 + 38 = 53 tests
```

> **dirty/untracked 표현 (19-P-3 caveat 반영)**: 본 19-P-9 산출 = 신규 문서 3개. 18-0~18-8 변경분은 작업트리에 dirty/untracked 로 남아 있지만 본 세션과 무관 — 19-0 시점에 정리 (19-P-6 §0-1 / §2 / §5-2 명시).

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_checklists.md](../../docs/refactor/19_refactor_checklists.md) (본 세션 신규)

### 2차 (대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3)
- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (19-P-3)
- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) (19-P-4 r2)
- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) (19-P-5 r3) <!-- r2 보정: 19-P-9 caveat 3 정합 — 실제 메타는 r3 (r1 fail → r2 → r3 보정) -->

- [docs/refactor/19_refactor_rollout_plan.md](../../docs/refactor/19_refactor_rollout_plan.md) (19-P-6 r2)
- [docs/refactor/19_refactor_risk_register.md](../../docs/refactor/19_refactor_risk_register.md) (19-P-7 r3)
- [docs/refactor/19_refactor_decision_record.md](../../docs/refactor/19_refactor_decision_record.md) (19-P-8 r1)
- [docs/AI_WORKING_RULES.md](../../docs/AI_WORKING_RULES.md) (절대 원칙 + local-first)
- [docs/ai_code_session_protocol.md](../../docs/ai_code_session_protocol.md) (14단계 절차 + 검증 요청서 20항목)
- [reports/refactor/19-P-8_codex_review.md](19-P-8_codex_review.md) (직전 r1 pass with caveat — yes 진입 가능, 영구 보존본)

## 8. 체크리스트가 실제 19-x 리팩토링 세션에서 바로 사용 가능한지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| §1 세션 시작 전 8 항목 — 공통 베이스 5 / 19-P 베이스 8 / 목표 / 가능·금지 범위 / 직전 Codex / 모듈 위치 / API·DB·UI / rollback | docs/refactor/19_refactor_checklists.md §1-1 ~ §1-8 |
| §2 코드 수정 전 9 항목 — URL / 응답 key / 프론트 JS / DB / migration / 운영 DB / 외부 API / 하네스 / PyInstaller | §2-1 ~ §2-9 |
| §3 코드 이동 8 항목 — 책임 분리 / D-3 / D-4 / 순환참조 / wrapper / endpoint / 내부 구현 / 결과 동치 | §3-1 ~ §3-8 |
| §5 테스트 12 항목 — 모듈 회귀 / contract / DB 보호 / 외부 API / AI 하네스 / SMS / 휴무 / pytest / ruff / check_db_path / run_check.bat / PyInstaller 53 tests | §5-1 ~ §5-12 |
| §6 모듈별 특수 — appointments / leaves / treatments+completion / stats / sms / patients+notes / admin+settings / ai+rag (8 모듈) | §6-1 ~ §6-8 |
| §7 실패 대응 7 항목 — 원인 / 루프 / 5회 한도 / latest_failure_report / 땜질 ⊥ / rollback / Codex 요청 | §7-1 ~ §7-7 |
| §8 완료 12 항목 — 변경 파일 / 이동 / wrapper / 응답 key / 테스트 / 남은 위험 / 주석 / latest_*.md / 영구 보존본 / Codex 게이트 | §8-1 ~ §8-12 |

### Codex 검증 명령 — 체크리스트 사용 가능성

```bash
# 체크리스트 항목 카운트 (체크박스 [ ] grep)
grep -cE "^- \[ \]" docs/refactor/19_refactor_checklists.md   # 79+ 기대
# 섹션 카운트 (§1 ~ §9 = 9개 + §10 종합 = 본문 11개) — r2 보정 (19-P-9 caveat 1 정합)
# 단순 grep은 §9-5 fenced markdown 예시 (`## 1. 종합 판정` 등) 까지 잡아 15개로 표시 가능 → awk 로 코드블록 제외:
awk '/^```/{c=!c; next} !c && /^## [0-9]+\./' docs/refactor/19_refactor_checklists.md | wc -l   # 11 기대 (정확)
# 또는 ripgrep:
# rg -n "^## [0-9]+\." docs/refactor/19_refactor_checklists.md --no-multiline   # 코드블록 안 라인도 잡지만 문맥 확인 가능
# (참고용 단순 grep, 부정확 — 코드블록 포함):
grep -nE "^## [0-9]+\." docs/refactor/19_refactor_checklists.md | wc -l   # 15 (코드블록 포함 — 본문 11이 정확)
# 모듈별 특수 8 모듈
grep -nE "^### 6-[1-8]" docs/refactor/19_refactor_checklists.md | wc -l   # 8 기대
# 19-P-1 ~ 19-P-8 문서 링크 정합
grep -nE "19_refactor_(current_state|target_architecture|module_map|dependency_map|test_strategy|rollout_plan|risk_register|decision_record)\.md" docs/refactor/19_refactor_checklists.md | wc -l   # 다수 기대
```

## 9. 주석 / 문서화 기준이 포함되었는지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| §4 주석 / 문서화 9 항목 (4-1 ~ 4-9) | §4-1 ~ §4-9 |
| 6 카테고리 — COMPAT / SAFETY / NOTE / RISK / TODO / TEMP | §4-3 ~ §4-7 + 19-P-8 §6-1 정합 |
| 4-1 새 파일 docstring / 4-2 service docstring / 4-3 COMPAT / 4-4 SAFETY / 4-5 NOTE+RISK / 4-6 TODO / 4-7 TEMP / 4-8 의미 없는 주석 ⊥ / 4-9 주석-코드 일치 | §4-1 ~ §4-9 |
| TODO 는 세션 번호 / 제거 조건 포함 | §4-6 |
| 주석 작성으로 동작 변경 ⊥ | §4 머리말 + §0-3 |

### Codex 검증 명령 — 주석 카테고리 정합

```bash
# 6 주석 카테고리 grep
grep -nE "(COMPAT|SAFETY|NOTE|RISK|TODO|TEMP)" docs/refactor/19_refactor_checklists.md | wc -l   # 다수 기대
# §4 9 하위 항목 (4-1 ~ 4-9)
grep -nE "^### 4-[1-9]" docs/refactor/19_refactor_checklists.md | wc -l   # 9 기대
# DEC-S 정합 (19-P-8)
grep -nE "DEC-S" docs/refactor/19_refactor_checklists.md   # 다수 기대
```

## 10. 실패 대응 / rollback / Codex 검증 게이트가 포함되었는지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 문서 위치 |
|---|---|
| §7 실패 대응 7 항목 (7-1 ~ 7-7) | §7-1 ~ §7-7 |
| 5회 루프 한도 — 5회 초과 ⊥ | §7-2 + §7-3 |
| 5회 실패 시 latest_failure_report.md | §7-4 |
| 땜질식 수정 ⊥ — xfail / skip 으로 덮지 않는다 | §7-5 + T-10 정합 |
| rollback = git revert <분리 commit> 1회 | §7-6 |
| RB-1 ~ RB-10 매핑 | §7-6 + 19-P-6 §7 정합 |
| Codex 검증 요청 문서 작성 (성공 / 실패 무관) | §7-7 + §9 |
| Codex 검증 게이트 — 다음 세션 진입 ⊥ | §8-12 + §9-4 + DEC-T 정합 |
| 영구 보존본 (`{19-x}_codex_review.md`) 인용 권장 — `latest` 는 진입점 (19-P-8 caveat 1) | §9-4 + §0-A |

### Codex 검증 명령 — 실패 대응 / 게이트 정합

```bash
# §7 7개 항목
grep -nE "^### 7-[1-7]" docs/refactor/19_refactor_checklists.md | wc -l   # 7 기대
# 5회 루프 표현
grep -nE "5회|루프|latest_failure_report" docs/refactor/19_refactor_checklists.md | wc -l   # 다수 기대
# Codex 게이트
grep -nE "Codex 검증 (전|게이트|통과)" docs/refactor/19_refactor_checklists.md | wc -l   # 다수 기대
# 영구 보존본 권장
grep -nE "영구 보존본|영구 링크|덮어쓰기" docs/refactor/19_refactor_checklists.md | wc -l   # 다수 기대
```

## 11. 다음 단계 (19-P 최종 점검 또는 19-0 baseline 재고정) 진입 가능 판단 기준

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 본 19-P-9 추가 변경분 0. 19-P-1 ~ 19-P-8 산출물 무수정. |
| G-2 §1 세션 시작 전 (8 항목) | 공통 베이스 5 / 19-P 베이스 8 / 목표 / 가능·금지 범위 / 직전 Codex / 모듈 위치 / API·DB·UI / rollback 모두 등록 |
| G-3 §2 코드 수정 전 (9 항목) | URL / 응답 key / 프론트 JS / DB schema / migration / 운영 DB / 외부 API / 하네스 / PyInstaller 모두 등록 |
| G-4 §3 코드 이동 (8 항목) | 책임 분리 / D-3 / D-4 / 순환참조 / wrapper / endpoint / 내부 구현 / 결과 동치 모두 등록 |
| G-5 §4 주석 / 문서화 (9 항목) | 6 카테고리 (COMPAT/SAFETY/NOTE/RISK/TODO/TEMP) + 의미 없는 주석 ⊥ + 주석-코드 일치 모두 등록 |
| G-6 §5 테스트 (12 항목) | run_check.bat / pytest / ruff / check_db_path / 4단계 격리 / db_guard / `_block_sdk_modules` / AI 하네스 6개 / SMS AI / 휴무 AI / contract / PyInstaller 53 tests 모두 등록 |
| G-7 §6 모듈별 특수 (8 모듈) | appointments / leaves / treatments+completion / stats / sms / patients+notes / admin+settings / ai+rag 모두 핵심 위험 + 절대 보존 항목 명시 |
| G-8 §7 실패 대응 (7 항목) | 5회 루프 / latest_failure_report / 땜질 ⊥ / rollback / Codex 요청 모두 등록 |
| G-9 §8 완료 (12 항목) | 변경 파일 / 이동 / wrapper / 응답 key / 테스트 / 남은 위험 / 주석 / latest_*.md / 영구 보존본 / Codex 게이트 모두 등록 |
| G-10 §9 Codex 검증 요청 (6 항목) | 작성 문서 2개 / 14 항목 표준 / 검증 명령 / 결과 기록 위치 / 응답 형식 / 최소 문구 모두 등록 |
| G-11 19-P-8 caveat 3개 반영 | (1) 영구 링크 권장 §0-A + §9-4. (2) api.py 라인 수 §0-2 baseline 측정값. (3) PyInstaller 53 tests 산출 공식 §5-12. |
| G-12 19-P-1 ~ 19-P-8 충돌 ⊥ | 본 체크리스트가 P-1 ~ P-12 / R-1 ~ R-14 / D-1 ~ D-13 / T-1 ~ T-15 / RB-1 ~ RB-10 / Risk ID 77 / DEC-A ~ DEC-T 모두 정합 |

→ G-1 ~ G-12 전부 통과 시 **yes — 19-P 최종 점검 또는 19-0 baseline 재고정 진입 가능**.

## 12. Codex 가 반드시 확인할 항목 (사용자 명시)

| 검증 항목 | 본 문서 위치 |
|---|---|
| `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 무수정 | §5 / §6 |
| `docs/refactor/19_refactor_checklists.md` 작성 또는 수정 | §3 신규 |
| `reports/refactor/{19-P-9,latest}_codex_review_request.md` 작성 | §3 신규 |
| 세션 시작 전 / 코드 수정 전 / 코드 이동 / 테스트 / 실패 대응 / 완료 체크리스트 충분 | §11 G-2 ~ G-9 |
| 모듈별 특수 체크리스트가 예약 / 휴무 / 완료체크 / 통계 / 문자 / AI / RAG 위험 반영 | §11 G-7 + 본 §8 |
| COMPAT / SAFETY / NOTE / RISK / TODO 주석 기준 포함 | §11 G-5 + 본 §9 |
| Codex 검증 전 다음 세션 진행 ⊥ 원칙 명확 | §11 G-10 + 본 §10 + §8-12 + DEC-T |
| 다음 단계로 넘어가도 되는가 | §11 G-1 ~ G-12 |

### Codex 검증 명령 — 부재 항목 단정 ⊥ 정합

```bash
# 부재 항목 grep — 0건 기대
grep -nE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py
grep -n "doctor_id" app/models/models.py   # Patient 에 0건 기대
grep -n "no_show" app/models/models.py     # 0건 기대
# 본 체크리스트의 후속 검토 표현
grep -nE "post-19-P|후속 검토|m014\+|미목표" docs/refactor/19_refactor_checklists.md | wc -l   # 다수 기대
```

## 13. Codex 검증 결과 기록 위치

- [reports/refactor/19-P-9_codex_review.md](19-P-9_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-P-9 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- G-1 ~ G-12: {결과 + 근거}

## 3. 추가 발견 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 다음 단계 진입 권고
{yes / no + 다음 단계 (19-P 최종 점검 또는 19-0 baseline 재고정) + 근거}
```

## 14. Claude Code 자체 판단

**yes (다음 단계 진입 권고)** — Codex 검증 후 다음 단계 진입 가능. 다음 단계 후보 = **19-P 최종 점검** (19-P-1 ~ 19-P-9 cross-check) 또는 **19-0 baseline 재고정** (코드 세션 진입 직전 baseline 확보) — 사용자 결정 필요.

근거:
1. 본 세션은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `19_refactor_checklists.md` 11개 섹션 (§0~§10) — 9개 카테고리 체크리스트 (§1 ~ §9) + 종합 = 사용자 §1~§9 모두 커버. 총 79+ 체크 단위.
3. **19-P-8 caveat 3개 모두 반영** — (1) 영구 링크 §0-A + §9-4 / (2) api.py 5127 vs 5128 §0-2 baseline 측정값 / (3) PyInstaller 53 tests 산출 공식 §5-12.
4. §6 모듈별 특수 체크리스트 8 모듈 — appointments / leaves / treatments+completion / stats / sms / patients+notes / admin+settings / ai+rag — 모두 핵심 위험 (R-APPT-* / R-LEAVE-* / R-TX-* / R-STAT-* / R-SMS-* / R-PAT-* / R-ADM-* / R-AI-*) + 절대 보존 항목 (DEC-C / D / N / O / R / S 정합) 명시.
5. §4 주석 / 문서화 — 6 카테고리 (COMPAT/SAFETY/NOTE/RISK/TODO/TEMP) + DEC-S 정합 + 19-P-8 §6-1 매트릭스 / §6-2 위치 16개 정합.
6. §7 실패 대응 — 5회 루프 / latest_failure_report / 땜질 ⊥ (T-10) / rollback (RB-1 ~ RB-10) / Codex 요청 모두 등록.
7. §8 완료 — latest_test_report.md / latest_fix_summary.md / latest_codex_review_request.md + 영구 보존본 + Codex 게이트 (DEC-T) 모두 등록.
8. §9 Codex 검증 요청 — 14 항목 표준 + 검증 명령 + 결과 기록 위치 + 응답 형식 + 최소 문구 모두 등록.
9. 19-P-1 ~ 19-P-8 산출물과 충돌 ⊥ — P-1 ~ P-12 / R-1 ~ R-14 / D-1 ~ D-13 / T-1 ~ T-15 / RB-1 ~ RB-10 / Risk ID 77 / DEC-A ~ DEC-T 모두 정합.
10. 18-8 baseline 회귀 보호 100% (529 passed, 1 skipped, 7 xfailed).
11. 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 / 19-P-7 / 19-P-8 산출물 무수정.

남은 위험 / caveat:
- 비-AI 86 endpoint contract 부재 (C-1) — 본 체크리스트는 *분리 직전 보강* 으로 명시. 실제 보강은 각 19-x 분리 직전.
- 18-0~18-8 변경분 main 머지 / `docs/ai_rag_current_state.md` stale 보정 — 19-0 또는 별도 세션.
- T-1 ~ T-15 (19-P-2 확인 필요 항목) 일부는 19-x 코드 세션 진입 시점 결정 — 본 체크리스트는 *방향성* 만 합의.
- PyInstaller "53 tests" 는 산출 공식 (15 + 19×2 = 53) 은 정확하지만, Codex 가 실제 pytest collect-only 로 독립 확인하려면 .venv Python 런처 필요 — 19-0 시점에 확인.

다음 단계:
- **옵션 A: 19-P 최종 점검** — 19-P-1 ~ 19-P-9 산출물 cross-check + 진입 준비 완료 확인. read-only 문서 세션. 본 19-P-1 ~ 19-P-9 의 P-* / R-* / D-* / T-* / RB-* / Risk ID / DEC-* 모두 정합 최종 검증.
- **옵션 B: 19-0 baseline 재고정** — 19-x 코드 세션 진입 직전 baseline 확보. (a) 18-8 baseline 529/1/7 통과 재확인 / (b) 워크트리 dirty/untracked 정리 (18-0~18-8 변경분 main 머지 또는 별도 commit) / (c) 19-P-1~9 캐비엇 / 후속 / 보강 9개 항목 인덱싱 / (d) 19-1 진입 직전 깨끗한 baseline.
- 사용자 결정 후 진입.

## 15. 게이트 정합

| 게이트 (§11) | 통과 근거 |
|---|---|
| G-1 코드 무수정 | §5 + §6 — `app/**`, `tests/**`, migrations, spec, UI, requirements 변경 0 |
| G-2 §1 세션 시작 전 | §1-1 ~ §1-8 = 8 영역 (공통 베이스 / 19-P 베이스 / 목표 / 가능·금지 범위 / 직전 Codex / 모듈 위치 / API·DB·UI / rollback) |
| G-3 §2 코드 수정 전 | §2-1 ~ §2-9 = 9 영역 (URL / 응답 key / 프론트 JS / DB / migration / 운영 DB / 외부 API / 하네스 / PyInstaller) |
| G-4 §3 코드 이동 | §3-1 ~ §3-8 = 8 영역 (책임 분리 / D-3 / D-4 / 순환참조 / wrapper / endpoint / 내부 구현 / 결과 동치) |
| G-5 §4 주석 / 문서화 | §4-1 ~ §4-9 = 9 영역 (6 카테고리 + 의미 없는 주석 ⊥ + 주석-코드 일치) |
| G-6 §5 테스트 | §5-1 ~ §5-12 = 12 영역 (모듈 / contract / DB / 외부 API / AI 하네스 / SMS / 휴무 / pytest / ruff / check_db_path / run_check.bat / PyInstaller 53) |
| G-7 §6 모듈별 특수 | §6-1 ~ §6-8 = 8 모듈 (appointments / leaves / treatments+completion / stats / sms / patients+notes / admin+settings / ai+rag) |
| G-8 §7 실패 대응 | §7-1 ~ §7-7 = 7 영역 (원인 / 루프 / 5회 / latest_failure_report / 땜질 ⊥ / rollback / Codex 요청) |
| G-9 §8 완료 | §8-1 ~ §8-12 = 12 영역 (변경 파일 / 이동 / wrapper / 응답 key / 테스트 / 남은 위험 / 주석 / latest_*.md / 영구 보존본 / Codex 게이트) |
| G-10 §9 Codex 검증 요청 | §9-1 ~ §9-6 = 6 영역 (작성 문서 2개 / 14 항목 표준 / 검증 명령 / 결과 기록 위치 / 응답 형식 / 최소 문구) |
| G-11 19-P-8 caveat 3개 반영 | §0-A + §0-2 + §5-12 — 영구 링크 / api.py 5127↔5128 / PyInstaller 53 산출 공식 |
| G-12 19-P-1 ~ 19-P-8 충돌 ⊥ | §0 + §10 종합 + 본 8 검증 항목 표 = P-1 ~ P-12 / R-1 ~ R-14 / D-1 ~ D-13 / T-1 ~ T-15 / RB-1 ~ RB-10 / Risk ID 77 / DEC-A ~ DEC-T 모두 정합 |
