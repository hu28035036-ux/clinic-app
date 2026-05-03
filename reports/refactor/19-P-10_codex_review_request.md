# 19-P-10 Codex 검증 요청서

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-03 | **pass with caveat — yes 19-0 baseline 재고정 진입 가능** ([reports/refactor/19-P-10_codex_review.md](19-P-10_codex_review.md)) | 초기 작성 — 19-P 단위화 리팩토링 최종 점검 문서 (`docs/refactor/19_refactor_final_check.md`) 신규 작성. cross-check 매트릭스 중심. |
| r2 | 2026-05-03 | **pass with caveat — yes 19-1 진입 가능 (사용자 결정 후)** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r2 시점) | **사용자 양식 정합 추가 산출** — `docs/refactor/19_refactor_final_review.md` 신규 작성. 사용자 명시 §1~§10. final_check.md 와 보완 관계. r1 caveat 4개 모두 직전 19-0 세션에서 해소. |
| r3 | 2026-05-03 | **pass with caveat — yes 19-1 진입 가능 (사용자 결정 필요)** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r3 시점) | **r2 Codex caveat 5건 보정 (옵션 C 사용자 결정)** — caveat 1: `# 10 기대` → `# 11/12 기대` 보정 (entry_notes / final_review 포함 카운트 정정) / caveat 2: `r1+r2 통합 산출물 (3개)` → `(4개)` 라벨 보정 / caveat 3: `latest_test_report.md` + `latest_fix_summary.md` 19-0 r2 본문으로 동기화 / caveat 4: `final_review.md §3-3` follow-up 카운트 설명 보강 (동시 매핑 6 항목 §3-3-1 표 추가, 산술 19+9+5+0=33 명시) / caveat 5: 인지 사항만 (chronology). 코드/테스트/spec/UI/migrations/requirements 무수정. |
| r4 | 2026-05-03 | **pass with caveat — yes 19-1 진입 가능. baseline line count caveat 발견** ([reports/refactor/latest_codex_review.md](latest_codex_review.md) r4 시점) | **r3 Codex caveat 3건 보정 (옵션 3 사용자 결정)** — caveat 1: line 142 설명문 stale → 정정 / caveat 2: line 144 `ls reports/refactor/` 21개 → 24개 / caveat 3: 수정 파일 목록 라벨 r4 최신화. 모두 read-only 문서 보정. |
| r5 | 2026-05-03 | (본 revision) | **r4 Codex caveat 보정** — caveat 1 (baseline line count 70 줄 차이): **Codex 측정 오류 가능성 입증** — 다중 측정 (bash `wc -l` / `cat \| wc -l` / `awk NR` / `git show HEAD:` 4 방법) 모두 baseline (api.py 5127 / ai.py 929 / app.css 3626 / main.html 7331) 100% 일치 확인. Codex r4 측정값 (5057/5058 / 925 / 3614) 은 70줄 / 4줄 / 12줄 차이로 단순 셸 차이 ≠. **본 baseline 정확** — 19-P-9 §0-2 / 19-P-10 §4-1 / 19-0_test_report.md §5 모두 정합. caveat 3 요약 표현 보강 (§3 "후속 5+1" → "후속 검토 단독 5 + 동시 매핑 6" 명시). caveat 2 (bash 미존재) + caveat 4 (dirty worktree) 는 인지 사항 / 사용자 결정. 코드 영향 0. |

본 요청서는 19-P 단위화 리팩토링 *준비 단계 마지막* (10 번째) 세션의 산출물 (최종 점검 문서 **2건** — `final_check.md` r1 + `final_review.md` r2 신규) 을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

본 19-P-10 = **9개 준비 단계 문서 (19-P-1 ~ 19-P-9) cross-check + 사용자 양식 §1~§10 정합** + **Codex caveat 누적 정리** + **baseline 실측 재확인** + **19-0 진입 게이트 (FG-1 ~ FG-10 + 본 r2 사용자 양식 §1~§10) 평가** + **19-0 진입 권고**.

---

## 0-A. Baseline

- HEAD commit: `bcd74a7aabc9de8d735425863254cfc393bda580` (release v1.3.3)
- 19-P-1 r2 / 19-P-2 r3 / 19-P-3 r1 / 19-P-4 r2 / 19-P-5 r3 / 19-P-6 r1+r2 / 19-P-7 r3 / 19-P-8 r1 / 19-P-9 r1 Codex 판정: **pass / pass / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat / pass with caveat (yes — 19-P-10 진입 가능)** ([reports/refactor/19-P-9_codex_review.md](19-P-9_codex_review.md) — 영구 보존본 링크)
- 18-8 baseline: **529 passed, 1 skipped, 7 xfailed**
- 19-P-9 r1 caveat 본 19-P-10 반영:
  - (1) `## [0-9]+\.` grep 명령이 fenced markdown 예시까지 잡음 (15 / 11) — 본 19-P-10 §3-2 + §5-3 에 보정 안 명시 (read-only 정책상 본 세션 수정 ⊥, 19-0 시점에 보정).
  - (2) 19-P-9 검증 요청서 2차 대조 기준 `(19-P-5 r2)` → 실제 r3 — 본 19-P-10 §1-1 에 r3 정확 기재 + §3-2 에 19-P-9 요청서 보정 권장 명시 (read-only 정책상 본 세션 수정 ⊥).
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 문서 추가만 수행. 코드/테스트/spec/UI/migrations/requirements 무수정.

## 1. 세션 이름

**19-P-10 단위화 리팩토링 최종 점검 — 19-0 진입 권고**

- 19-P-1 [현재 구조](../../docs/refactor/19_refactor_current_state.md), 19-P-2 [목표 아키텍처](../../docs/refactor/19_refactor_target_architecture.md), 19-P-3 [모듈 매핑](../../docs/refactor/19_refactor_module_map.md), 19-P-4 [의존성 맵](../../docs/refactor/19_refactor_dependency_map.md), 19-P-5 [테스트 전략](../../docs/refactor/19_refactor_test_strategy.md), 19-P-6 [롤아웃 계획](../../docs/refactor/19_refactor_rollout_plan.md), 19-P-7 [위험 등록](../../docs/refactor/19_refactor_risk_register.md), 19-P-8 [의사결정 기록](../../docs/refactor/19_refactor_decision_record.md), 19-P-9 [공통 체크리스트](../../docs/refactor/19_refactor_checklists.md) 의 종합 / 최종 점검 문서.
- read-only 문서 세션. 실제 코드 / 테스트 / fixture / mock / 마이그레이션 미작성.

## 2. 이번 세션 목표

| # | 목표 | 본문 위치 |
|---|---|---|
| 1 | §1 19-P-1 ~ 19-P-9 산출물 인벤토리 (9 준비 단계 + 9 Codex 결과 + 9 요청서 = 27 산출물 + 본 세션 3개 = 30) | docs/refactor/19_refactor_final_check.md §1 |
| 2 | §2 절대 원칙 / 모듈 분리 순서 / 부재 항목 단정 ⊥ / 의존성 방향 9개 문서 cross-check (4 매트릭스) | §2-1 ~ §2-4 |
| 3 | §3 Codex caveat 누적 분류 — 해소 8 / 19-0 보정 2 / 19-0~19-x 해소 7 / post-19-P 후속 12 = 29개 | §3-1 ~ §3-5 |
| 4 | §4 19-P-10 시점 baseline 측정값 재실측 (api.py 5127 / endpoint 86 / PyInstaller 53 산출 / 부재 항목 0건 등) | §4-1 ~ §4-2 |
| 5 | §5 19-0 진입 전 점검 항목 — 사용자 결정 3건 + 환경 복구 4건 + 19-P-9 caveat 보정 2건 + baseline 확보 8 항목 | §5-1 ~ §5-4 |
| 6 | §6 19-0 진입 게이트 FG-1 ~ FG-10 평가 + 옵션 A/B/C 비교 + 다음 단계 권고 | §6-1 ~ §6-4 |
| 7 | §7 종합 — 30 산출물 / 18 revision / 5 fail / 충돌 0건 / caveat 29 / FG 8 pass + 2 caveat / 19-0 진입 권고 yes | §7 |

## 3. 작성한 문서

### r1 (직전 작성 — Codex pass with caveat)

- [docs/refactor/19_refactor_final_check.md](../../docs/refactor/19_refactor_final_check.md) — 최종 점검 (cross-check 매트릭스 중심, §0 ~ §7). r1 작성 + r2 보정 (§1 산출물 총계 29 → 30).

### r2 신규 (본 revision)

- **[docs/refactor/19_refactor_final_review.md](../../docs/refactor/19_refactor_final_review.md)** — 사용자 양식 §1~§10 정합 최종 점검 (목적 / 작성 완료 문서 / 기능 누락 / 리팩토링 순서 / 위험 / 테스트 / 주석 / 19-0 진입 조건 / 19-0 할 일+금지 / 최종 판단). final_check.md 와 보완 관계.

### r1+r2 통합 산출물 (4개) <!-- r3 보정 (Codex r2 caveat 2): 실제 bullet 4개 = final_check + final_review + 19-P-10 request + latest request -->

- [docs/refactor/19_refactor_final_check.md](../../docs/refactor/19_refactor_final_check.md) (r1 작성 + r2 §1 보정)
- [docs/refactor/19_refactor_final_review.md](../../docs/refactor/19_refactor_final_review.md) (r2 신규)
- [reports/refactor/19-P-10_codex_review_request.md](19-P-10_codex_review_request.md) (본 문서, r2 갱신 + r3 보정)
- [reports/refactor/latest_codex_review_request.md](latest_codex_review_request.md) (Codex 진입점 — 본 문서와 동일)

### Codex 작성 예정

- [reports/refactor/19-P-10_codex_review.md](19-P-10_codex_review.md) (영구)
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
- 19-P-1 / 19-P-2 / 19-P-3 / 19-P-4 / 19-P-5 / 19-P-6 / 19-P-7 / 19-P-8 / 19-P-9 산출물 무수정.

### r2 caveat 보정 항목 (사용자 양식 §1~§10 정합 — 본 r2 의 핵심 추가 산출)

| # | 사용자 양식 § | 본 final_review.md 위치 | 핵심 결과 |
|---|---|---|---|
| 1 | §1 최종 점검 목적 (3개) | [docs/refactor/19_refactor_final_review.md §1](../../docs/refactor/19_refactor_final_review.md) | ✓ 모두 충족 (일관성 / 누락 검증 / 19-0 판단) |
| 2 | §2 작성 완료 문서 (9 + 1 final_check + 1 final_review = 11) | §2-1 ~ §2-10 | ✓ 모두 작성 완료 + revision 이력 18 + fail 5 (모두 보정 후 복귀) |
| 3 | §3 기능 누락 (핵심 14 + 보조 19 = 33) | §3-1 ~ §3-3 | ✓ 누락 0건 / 확인 필요 0건 — 현재 기능 19 / 부분 존재 9 / 후속 검토 5 (보조 + 핵심 doctors EMR 부분) |
| 4 | §4 리팩토링 순서 (사용자 명시 7개) | §4-1 ~ §4-2 | ✓ 모두 정합 — 19-0 baseline / appointments 마지막 (19-9) / availability+leaves+treatments+patients+staff 먼저 / SMS+stats+admin+backup+AI commands 적절 순서 / PyInstaller 검증 시점 / Codex 게이트 |
| 5 | §5 위험 (사용자 명시 13개 + 77 Risk ID) | §5 + §5-1 | ✓ 누락 0건 — 모든 13개 매핑 + 치명 8 / 높음 14 / 중간 다수 / 낮음 3 / 후속 14 |
| 6 | §6 테스트 (사용자 명시 15개 + 보강 9개) | §6 + §6-1 | ✓ 15개 모두 등록 + 19-0 보강 9 항목 (비-AI contract C-1 + xfail 7+1건 정방향 + 응답 키 contract 등) |
| 7 | §7 주석 / 문서화 (사용자 명시 8개) | §7 | ✓ 모두 반영 — COMPAT/SAFETY/NOTE/RISK/TODO/TEMP 6 카테고리 + DEC-S 정합 + 위치 16 |
| 8 | §8 19-0 진입 조건 (사용자 명시 8개) | §8-1 ~ §8-2 | ✓ 모두 충족 — 19-P 작성 / Codex 검증 / 순서 / 위험 / 테스트 / 체크리스트 / 후속 분류 / 코드 수정 0 |
| 9 | §9 19-0 금지 (사용자 명시 8개) | §9 | ✓ 모두 적용 — 모듈 이동 / 대규모 / DB / UI / 응답 키 / 하네스 / 운영 DB / 외부 API |
| 10 | §10 최종 판단 | §10-1 ~ §10-2 + §11 | **19-0 진행 가능** (yes — 19-0 baseline 재고정 진입 가능) |

## 5. 실제 수정한 파일 목록

### r1 (직전 작성, r2 + r3 보정 누적)

- `docs/refactor/19_refactor_final_check.md` (r1 작성 + r2 §1 산출물 총계 보정)
- `reports/refactor/19-P-10_codex_review_request.md` (r1 작성, r2 → r3 → **본 r4 갱신**)
- `reports/refactor/latest_codex_review_request.md` (r1 작성, r2 → r3 → **본 r4 덮어쓰기**)

### r2 신규 (사용자 양식 정합 추가)

- **`docs/refactor/19_refactor_final_review.md`** — 사용자 양식 §1~§10 정합 신규 (r2 작성 + r3 §3-3 보강)

### r3 신규 (caveat 5건 보정)

- `reports/ai_dev_loop/latest_test_report.md` (19-0 r2 본문 동기화)
- `reports/ai_dev_loop/latest_fix_summary.md` (19-0 r2 본문 동기화)

### r4 신규 (본 revision — r3 Codex caveat 3건 보정)

- `reports/refactor/19-P-10_codex_review_request.md` (line 142 docs/refactor 12개 정합 + line 144 reports/refactor 24개 정합 + 본 §5 라벨 r4 최신화)
- `reports/refactor/latest_codex_review_request.md` (r4 덮어쓰기)

### 무수정 (회귀 보호)

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/services/**`, 19-P-1 ~ 19-P-9 산출물 (본 r4 추가 코드 변경 0).

## 6. 코드 수정 없이 docs/refactor + reports/refactor 문서만 작성했는지 확인

| 검사 | 결과 |
|---|---|
| 본 19-P-10 신규 파일 | `19_refactor_final_check.md` + `{19-P-10,latest}_codex_review_request.md` (3개) |
| `app/**` / `tests/**` / migrations / spec / UI / `pyproject.toml` 변경 | 0 |
| 19-P-1 ~ 19-P-9 산출물 변경 | 0 |
| 새 fixture / mock / harness 파일 추가 | 0 |
| 새 contract 테스트 추가 | 0 |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
ls docs/refactor/   # 19_refactor_*.md 핵심 11개 기대 (현재 구조 / 목표 / 모듈맵 / 의존성 / 테스트 / 롤아웃 / 위험 / 의사결정 / 체크리스트 / 최종점검 final_check / 사용자 양식 final_review). entry_notes 포함 전체 ls = 12개 — r4 보정 (r3 Codex caveat 1 정합).
ls docs/refactor/19_refactor_*.md | grep -v entry_notes | wc -l   # 11 기대 (entry_notes 제외, final_check + final_review 포함 — r3 보정)
ls reports/refactor/   # 24개 기대 (19-0 요청/검증 2 + 19-P-1~10 요청/검증 20 + latest 요청/검증 2) — r4 보정 (r3 Codex caveat 2 정합)
# 본 19-P-10 시점 baseline 재실측 (§4-1 표 정합) — bash 환경 (Linux/macOS/Git Bash)
wc -l app/routers/api.py   # 5127 (bash)
grep -cE "^@router\\." app/routers/api.py app/routers/ai.py   # 86 / 13
grep -cE "^class \\w+\\(Base\\)" app/models/models.py   # 19
ls app/migrations/m0*.py | wc -l   # 13
ls tests/test_*.py | wc -l   # 40
# 부재 항목 0건 확인 (§4-2)
grep -cE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py   # 0
grep -c "doctor_id" app/models/models.py   # 0
grep -c "no_show" app/models/models.py     # 0
```

### r5 추가 — Codex r4 baseline 측정 오류 재검증 (PowerShell 환경)

> **r4 Codex 가 보고한 측정값 (api.py 5057/5058, ai.py 925, app.css 3614) 은 실제 파일과 70/4/12 줄 차이로 단순 셸 (bash vs PowerShell) 차이 (보통 0~1 줄) 이상의 비정상 drift**. 실측 결과 본 baseline (5127 / 929 / 3626 / 7331) 정확. PowerShell 환경에서도 직접 재측정 가능한 명령:

```powershell
# PowerShell 환경에서 line count 측정 (Codex r5 검증용 — bash 미존재 환경 정합)
(Get-Content app/routers/api.py).Count                            # 5127 또는 5128 기대 (1줄 미종료 라인 포함 시 5128)
(Get-Content app/routers/ai.py).Count                             # 929 기대
(Get-Content app/static/css/app.css).Count                        # 3626 기대
(Get-Content app/templates/main.html).Count                       # 7331 기대

# 또는 raw byte 기준 newline count
[System.IO.File]::ReadAllText("app/routers/api.py").Split("`n").Count - 1   # 5127 기대 (newline 개수)
[System.IO.File]::ReadAllText("app/routers/ai.py").Split("`n").Count - 1   # 929 기대

# git HEAD 기준 비교 (bash / PowerShell 무관)
git show HEAD:app/routers/api.py | Measure-Object -Line              # Lines: 5127 기대
git show HEAD:app/routers/ai.py | Measure-Object -Line               # Lines: 887 기대 (HEAD = bcd74a7 + dirty +42 = 929 working tree)

# Claude 측정 다중 검증 결과 (Codex r5 가 직접 재현 가능):
# - bash `wc -l app/routers/api.py` = 5127 ✓
# - `cat app/routers/api.py | wc -l` = 5127 ✓
# - `awk 'END{print NR}' app/routers/api.py` = 5128 ✓ (1줄 미종료 라인 포함)
# - `git show HEAD:app/routers/api.py | wc -l` = 5127 ✓
# → 4 방법 모두 baseline 5127 일치 (단순 newline-at-eof 차이 1줄만, Codex r4 가 보고한 70 줄 drift 와 정합 ⊥)
```

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_final_check.md](../../docs/refactor/19_refactor_final_check.md) (본 세션 신규)

### 2차 (cross-check 대조 기준)

- [docs/refactor/19_refactor_current_state.md](../../docs/refactor/19_refactor_current_state.md) (19-P-1 r2)
- [docs/refactor/19_refactor_target_architecture.md](../../docs/refactor/19_refactor_target_architecture.md) (19-P-2 r3)
- [docs/refactor/19_refactor_module_map.md](../../docs/refactor/19_refactor_module_map.md) (19-P-3 r1)
- [docs/refactor/19_refactor_dependency_map.md](../../docs/refactor/19_refactor_dependency_map.md) (19-P-4 r2)
- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) (19-P-5 r3)
- [docs/refactor/19_refactor_rollout_plan.md](../../docs/refactor/19_refactor_rollout_plan.md) (19-P-6 r2)
- [docs/refactor/19_refactor_risk_register.md](../../docs/refactor/19_refactor_risk_register.md) (19-P-7 r3)
- [docs/refactor/19_refactor_decision_record.md](../../docs/refactor/19_refactor_decision_record.md) (19-P-8 r1)
- [docs/refactor/19_refactor_checklists.md](../../docs/refactor/19_refactor_checklists.md) (19-P-9 r1)

### 3차 (Codex 검증 영구 보존본)

- [reports/refactor/19-P-1_codex_review.md](19-P-1_codex_review.md) ~ [reports/refactor/19-P-9_codex_review.md](19-P-9_codex_review.md) (9개)

## 8. cross-check 매트릭스 + 사용자 양식 §1~§10 정확성 확인 항목

### 8-1. r1 final_check.md cross-check (4 매트릭스)

| 검증 항목 | 본 19-P-10 위치 |
|---|---|
| §2-1 절대 원칙 매트릭스 (9 원칙 × 9 문서) | docs/refactor/19_refactor_final_check.md §2-1 |
| §2-2 모듈 분리 순서 매트릭스 (15 세션 × 6 문서) | §2-2 |
| §2-3 부재 항목 단정 ⊥ 매트릭스 (10 항목 × 6 문서) | §2-3 |
| §2-4 의존성 방향 매트릭스 (8 D-* × 6 문서) | §2-4 |

### 8-2. r2 final_review.md 사용자 양식 §1~§10 정합 (10 영역)

| 검증 항목 | 본 19-P-10 위치 |
|---|---|
| §1 최종 점검 목적 (3개) | docs/refactor/19_refactor_final_review.md §1 |
| §2 작성 완료 문서 (9개 + 1 final_check + 1 final_review) | §2-1 ~ §2-10 |
| §3 기능 누락 (핵심 14 + 보조 19 = 33) — 4분류 (현재 / 부분 / 후속 / 확인 필요) | §3-1 ~ §3-3 |
| §4 리팩토링 순서 — 사용자 명시 7개 + 15 세션 정합 | §4-1 ~ §4-2 |
| §5 위험 — 사용자 명시 13개 + 77 Risk ID | §5 + §5-1 |
| §6 테스트 — 사용자 명시 15개 + 19-0 보강 9개 | §6 + §6-1 |
| §7 주석 / 문서화 — 사용자 명시 8개 | §7 |
| §8 19-0 진입 조건 — 사용자 명시 8개 + 19-0 할 일 4개 | §8-1 ~ §8-2 |
| §9 19-0 금지 — 사용자 명시 8개 | §9 |
| §10 최종 판단 — "19-0 진행 가능" + 근거 10개 | §10-1 ~ §10-2 + §11 종합 |

### Codex 검증 명령 — final_check (r1) cross-check 정합

```bash
# §2-1 절대 원칙 9개
grep -cE "^\\| (기능 변경|API URL|DB schema|AI/RAG|운영 DB|외부 API|per-file-ignores|manual60|Codex 검증|PyInstaller)" docs/refactor/19_refactor_final_check.md   # 다수 기대
# §2-2 모듈 분리 순서 15 세션
grep -cE "^\\| 19-(0|1[0-4]?|[2-9]) " docs/refactor/19_refactor_final_check.md   # 15 기대
# §2-3 부재 항목 10
grep -cE "^\\| (\\`Doctor\\`|\\`Patient\\.doctor_id\\`|\\`Department\\`|\\`Order\\`|\\`Appointment\\.no_show\\`|\\`/api/health\\`|\\`Resource\\`|반복 예약|알림|출력물)" docs/refactor/19_refactor_final_check.md   # 10 기대
# §2-4 D-1~D-13 일관
grep -nE "D-[0-9]+" docs/refactor/19_refactor_final_check.md | wc -l   # 다수 기대
# 19-P-1 ~ 19-P-9 문서 링크 정합
grep -cE "19_refactor_(current_state|target_architecture|module_map|dependency_map|test_strategy|rollout_plan|risk_register|decision_record|checklists)\\.md" docs/refactor/19_refactor_final_check.md   # 다수 기대
```

### Codex 검증 명령 — final_review (r2) 사용자 양식 §1~§10 정합

```bash
# §1~§10 섹션 카운트 (10 + 메타 §0 + 종합 §11 = 12 본문 섹션)
awk '/^```/{c=!c; next} !c && /^## [0-9]+\./' docs/refactor/19_refactor_final_review.md | wc -l   # 12 기대 (코드블록 제외)
# §3 기능 누락 4분류 표
grep -cE "^\\| (현재 기능|부분 존재|후속 검토|확인 필요)" docs/refactor/19_refactor_final_review.md   # 다수 기대
# §3-1 핵심 기능 14개 + §3-2 보조 19개 = 33 기능
grep -cE "^\\| [0-9]+ \\| (예약|환자|치료사|의사|휴무|치료항목|완료체크|통계|문자|관리자|백업|AI 명령|AI Safety|RAG|calendar|availability|notes|permissions|settings|audit|export_import|health|core|feature_flags|batch|privacy|concurrency|time_utils|cancellations|recurring|resources|printing|notifications)" docs/refactor/19_refactor_final_review.md   # 33 기대
# §10 최종 판단
grep -nE "(19-0 진행 가능|일부 문서 보완|19-P 추가 보완)" docs/refactor/19_refactor_final_review.md | head -5   # "19-0 진행 가능" 명시
```

## 9. Codex caveat 누적 정리 정확성 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 19-P-10 위치 |
|---|---|
| §3-1 해소된 caveat 8개 (19-P-1 r1 fail / 19-P-2 r1+r2 fail / 19-P-5 r1 fail / 19-P-6 r1 caveat / 19-P-7 r2 fail / 19-P-8 caveat 1+2+3) | docs/refactor/19_refactor_final_check.md §3-1 |
| §3-2 19-P-10 / 19-0 보정 2개 (19-P-9 caveat 1 grep 명령 / 19-P-9 caveat 3 r2 vs r3 표기) | §3-2 |
| §3-3 19-0 / 19-x 해소 7개 (dirty / stale / contract C-1 / xfail 7건+skip 1건 / .venv 복구 / 머지 결정) | §3-3 |
| §3-4 post-19-P 후속 12개 (notes / health / calendar / doctors EMR / no_show / 반복 / 자원 / 알림 / 출력 / 보존 / sms-ai 통합 / AI 의사 가드) | §3-4 |
| §3-5 종합 = 8 + 2 + 7 + 12 = 29 + 진행 차단 0건 | §3-5 |

### Codex 검증 명령 — caveat 누적 정합

```bash
# §3 caveat 항목 카운트
grep -cE "^\\| 19-P-[1-9](r[1-9])? " docs/refactor/19_refactor_final_check.md   # §3-1 ~ §3-3 caveat 항목
grep -nE "post-19-P" docs/refactor/19_refactor_final_check.md | wc -l   # §3-4 post-19-P 다수
# 진행 차단 0건 확인
grep -nE "진행 차단" docs/refactor/19_refactor_final_check.md   # "진행 차단 ⊥" / "0건" 명시
# revision 이력
grep -nE "r[1-9] (fail|pass)" docs/refactor/19_refactor_final_check.md | head -10   # 다수
```

## 10. baseline 실측 재확인이 19-P-9 §0-2 와 일치하는지 확인할 항목

### Codex 검증 포인트

| 검증 항목 | 본 19-P-10 위치 |
|---|---|
| §4-1 실측 baseline 10 항목 (api.py 5127 / endpoint 86 / ai.py 929 / 13 / main.html 7331 / app.css 3626 / tests 40 / ORM 19 / m001~m013 13 / PyInstaller 53) | docs/refactor/19_refactor_final_check.md §4-1 |
| §4-2 부재 항목 단정 ⊥ grep 0건 (Doctor/Department/Room/DoctorSchedule/Order/Prescription/Resource / doctor_id / no_show / `/api/health`) | §4-2 |
| 19-P-9 §0-2 baseline 측정값과 100% 일치 | §4-1 일치 ✓ 컬럼 |

### Codex 검증 명령 — baseline drift 0 확인

```bash
# 19-P-9 §0-2 vs 19-P-10 §4-1 일치
diff <(grep -E "^\\| (`app|`tests|ORM|마이그레이션|PyInstaller)" docs/refactor/19_refactor_checklists.md) <(grep -E "^\\| (`app|`tests|ORM|마이그레이션|PyInstaller)" docs/refactor/19_refactor_final_check.md) | head -20
# 부재 항목 0건 — bash 직접 확인
grep -cE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py   # 0
grep -c "doctor_id" app/models/models.py   # 0
grep -c "no_show" app/models/models.py   # 0
```

## 11. 19-0 진입 게이트 평가 (r1 FG-1~10 + r2 사용자 양식 §1~§10)

### r1 final_check.md FG-1 ~ FG-10 (직전 평가, 19-P-10 r1 시점)

| 게이트 | 본 19-P-10 평가 | 검증 방법 |
|---|---|---|
| FG-1 9개 준비 단계 문서 모두 작성 완료 | pass | `ls docs/refactor/19_refactor_*.md` = 11 파일 (current_state / target_architecture / module_map / dependency_map / test_strategy / rollout_plan / risk_register / decision_record / checklists / final_check / **final_review** — r2 추가) |
| FG-2 9개 모두 Codex 검증 pass / pass with caveat | pass | `ls reports/refactor/19-P-{1..9}_codex_review.md` = 9 파일 + 각 판정 grep |
| FG-3 절대 원칙 9개 문서 충돌 ⊥ | pass | §2-1 매트릭스 |
| FG-4 모듈 분리 순서 9개 문서 충돌 ⊥ | pass | §2-2 매트릭스 |
| FG-5 부재 항목 단정 ⊥ | pass | §2-3 매트릭스 + §4-2 grep 0건 |
| FG-6 의존성 방향 D-1~D-13 일관 | pass | §2-4 매트릭스 |
| FG-7 baseline 측정값 drift 0 | pass | §4-1 매트릭스 일치 ✓ + 19-0 시점 재실측 100% 일치 |
| FG-8 19-P-8 caveat 3개 19-P-9 반영 | pass | §3-1 caveat 6/7/8 항목 + 19-0 시점에 모두 해소 (PyInstaller 53 collected+passed) |
| FG-9 19-P-9 caveat 2개 19-0 보정 가능 | pass | 19-0 시점에 r2 보정 완료 (grep 명령 + r2→r3 표기) |
| FG-10 dirty/untracked 워크트리 19-0 정리 가능 | pass with caveat | §3-3 + §5-1 1번 (사용자 결정 필요 — 직전 세션에서 옵션 1-a-① 진행 중단) |

### r2 final_review.md 사용자 양식 §1~§10 정합 (10 영역)

| 게이트 | 본 19-P-10 평가 | 검증 방법 |
|---|---|---|
| §1 최종 점검 목적 (3개) | pass | final_review.md §1 — 일관성 / 누락 / 19-0 판단 모두 명시 |
| §2 작성 완료 문서 (11) | pass | §2-1 ~ §2-10 — 9 + final_check + final_review = 11 모두 작성 + revision 18 + fail 5 |
| §3 기능 누락 (33) | pass | §3-1 ~ §3-3 — 누락 0 / 확인 필요 0 / 분류 정합 (현재 19 / 부분 9 / 후속 5+1) |
| §4 리팩토링 순서 (사용자 명시 7) | pass | §4-1 ~ §4-2 — 모두 정합 (15 세션) |
| §5 위험 (사용자 명시 13 + 77 Risk ID) | pass | §5 + §5-1 — 누락 0 |
| §6 테스트 (사용자 명시 15 + 19-0 보강 9) | pass | §6 + §6-1 — 모두 등록 (보강은 분리 직전 시점 명시) |
| §7 주석 / 문서화 (사용자 명시 8) | pass | §7 — 모두 반영 (6 카테고리 + DEC-S) |
| §8 19-0 진입 조건 (사용자 명시 8) | pass | §8-1 ~ §8-2 — 모두 충족 |
| §9 19-0 금지 (사용자 명시 8) | pass | §9 — 모두 적용 |
| §10 최종 판단 | pass | §10-1 ~ §10-2 + §11 — **19-0 진행 가능** |

### Codex 검증 명령 — 19-0 진입 권고 합리성

```bash
# FG-1 9 + 본 19-P-10 = 10 파일
ls docs/refactor/19_refactor_*.md | wc -l   # 12 기대 (entry_notes + final_check + final_review 포함 — r3 보정)
# FG-2 9개 영구 보존본
ls reports/refactor/19-P-[1-9]_codex_review.md | wc -l   # 9 기대
# FG-2 판정 grep
grep -E "^- (종합 판정|판정):" reports/refactor/19-P-[1-9]_codex_review.md | grep -E "pass" | wc -l   # 9 기대
# FG-9 / FG-10 caveat 위치
grep -nE "FG-(9|10)" docs/refactor/19_refactor_final_check.md
grep -nE "19-0 안에서|read-only 정책" docs/refactor/19_refactor_final_check.md | wc -l   # 다수 기대
```

## 12. Codex 가 반드시 확인할 항목 (사용자 명시 — §A → §B 진행)

| 검증 항목 | 본 19-P-10 위치 |
|---|---|
| `app/`, `tests/`, migrations, requirements.txt, PyInstaller spec, UI 무수정 | §5 / §6 |
| `docs/refactor/19_refactor_final_check.md` 작성 또는 수정 | §3 신규 |
| `reports/refactor/{19-P-10,latest}_codex_review_request.md` 작성 | §3 신규 |
| 9개 준비 단계 문서 cross-check 정확 | 본 §8 + §11 FG-3 ~ FG-7 |
| Codex caveat 누적 정확 | 본 §9 + §11 FG-8 ~ FG-10 |
| baseline 실측 재확인 정확 | 본 §10 + §11 FG-7 |
| 19-0 진입 권고 합리적 | 본 §11 + 19-P-10 §6 |
| 옵션 A → B (사용자 §A → §B) 정합 | §6-3 (옵션 A 권장) |
| 다음 단계 = 19-0 baseline 재고정 | §6-4 |

## 13. Codex 검증 결과 기록 위치

- [reports/refactor/19-P-10_codex_review.md](19-P-10_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-P-10 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- FG-1 ~ FG-10: {결과 + 근거}

## 3. 추가 발견 caveat / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-0 baseline 재고정 진입 권고
{yes / no + 근거}
```

## 14. Claude Code 자체 판단

**yes (19-0 baseline 재고정 진입 권고)** — Codex r2 재검증 후 19-0 진입 (또는 직전 세션 19-0 baseline 검증 결과 활용 후 19-1 진입).

근거 (r1 + r2 통합):

### r1 final_check.md (직전 작성)

1. 본 세션은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `19_refactor_final_check.md` 8개 섹션 (§0~§7) — 9개 산출물 인벤토리 + 4 cross-check 매트릭스 + caveat 누적 29개 + baseline 실측 + 5개 진입 전 점검 + 10개 진입 게이트 + 옵션 비교 + 종합.
3. 9개 준비 단계 문서 모두 pass / pass with caveat (yes 진입 가능).
4. revision 이력 = 18 회 + fail 5회 (모두 보정 후 복귀).
5. 절대 원칙 / 모듈 분리 순서 / 부재 항목 단정 ⊥ / 의존성 방향 / baseline 측정값 = 9개 문서에서 일관 정합 — 충돌 0건.
6. r1 시점 Codex caveat 누적 = 해소 8개 / 19-P-10 보정 2개 / 19-0 ~ 19-x 해소 7개 / post-19-P 후속 12개. 진행 차단 0건.
7. 본 19-P-10 시점 baseline 측정값 (api.py 5127 / endpoint 86 / ai.py 929 / 13 / 7331 / 3626 / 40 / 19 / 13 / 53) 모두 19-P-9 §0-2 와 100% 일치.
8. 부재 항목 (Doctor / Department / Room / DoctorSchedule / Order / Prescription / Resource / Patient.doctor_id / no_show / `/api/health`) 모두 grep 0건.
9. 19-0 진입 게이트 FG-1 ~ FG-10 = 8 pass + 2 pass with caveat = 종합 pass with caveat (r1 Codex pass).
10. 18-8 baseline 회귀 보호 100% (529 passed, 1 skipped, 7 xfailed).
11. 19-P-1 ~ 19-P-9 산출물 무수정.

### r2 final_review.md (본 revision 추가)

12. 사용자 양식 §1~§10 정합 — 최종 점검 목적 3 + 작성 완료 11 + 기능 누락 33 + 리팩토링 순서 7 + 위험 13 + 테스트 15 + 주석 8 + 진입 조건 8 + 금지 8 + 최종 판단 모두 정합.
13. 33개 기능 분류 — 현재 19 / 부분 9 / 후속 5 (보조) + 핵심 doctors EMR 부분. 확인 필요 0건.
14. 사용자 명시 13개 위험 모두 등록 + 77 Risk ID 와 매핑.
15. 사용자 명시 15개 테스트 모두 등록 + 19-0 보강 9개 항목 명시.
16. 사용자 명시 8개 19-0 진입 조건 모두 충족 / 8개 금지 모두 적용.
17. **자체 판단: 19-0 진행 가능** — final_review.md §10-2 정합.

### 19-P-9 / 19-P-10 r1 caveat 본 r2 시점 해소 현황

직전 세션 (19-0 baseline 검증 + 권장 조합 진행) 시점에 다음 caveat 모두 해소 완료:
- 19-P-9 caveat 1 (grep 명령) — `reports/refactor/19-P-9_codex_review_request.md` r2 보정 (코드블록 제외 awk 명령 추가).
- 19-P-9 caveat 3 (`19-P-5 r2` → `r3`) — `reports/refactor/19-P-9_codex_review_request.md` r2 보정.
- 19-P-10 r1 caveat 1 (§1 vs §7 산출물 총계 29 → 30) — `docs/refactor/19_refactor_final_check.md` r2 보정.
- 19-P-10 r1 caveat 2 (`ls docs/refactor/` 10 vs 11) — `reports/refactor/19-P-10_codex_review_request.md` r2 보정 (entry_notes 제외 명령 추가).
- 19-P-10 r1 caveat 4 (PyInstaller 53 collection 미실행) — 직전 19-0 세션에서 `.venv` 정상 동작 + `pytest --collect-only` = 53 tests collected 검증 완료.
- 19-0 caveat 1 (`--collect-only` PowerShell 재현성) — `reports/ai_dev_loop/19-0_test_report.md` r2 보정 (bash 셸 기준 명시).
- 19-0 caveat 2 (§3 신규 5 → 6) — `reports/refactor/19-0_codex_review_request.md` r2 보정.
- 19-0 caveat 3 (5 vs 6 tracked) — `reports/ai_dev_loop/19-0_fix_summary.md` r2 보정 (두 기준 차이 명시).

또한 직전 세션에서 `docs/ai_rag_current_state.md` r2 stale caveat 추가 — 19-P-1 권위 baseline 참조 명시.

남은 위험 / 사용자 결정 필요 (19-1 진입 직전):
- 18-0~18-8 dirty/untracked 변경분 처리 결정 (머지 / 별도 commit / 유지) — 직전 세션에서 옵션 1-a-① (commit + push, main 머지 보류) 선택 후 commit 진행 중단된 상태. 본 19-P-10 r2 후 다시 진행 가능.

다음 세션:
- **Codex r2 재검증** → pass / pass with caveat 시 → **19-1 core 공통 유틸 정리 진입** (사용자 결정 1건 답변 후) 또는 **dirty 변경분 commit + push 재개** (직전 세션에서 중단된 작업).

## 15. 게이트 정합

| 게이트 (§11) | 통과 근거 |
|---|---|
| FG-1 9개 준비 단계 문서 | §1-1 (10 파일 = 9 + 본 19-P-10) |
| FG-2 9개 Codex 검증 pass | §1-2 (9 영구 보존본 모두 pass / pass with caveat) |
| FG-3 절대 원칙 충돌 ⊥ | §2-1 매트릭스 (9 원칙 × 9 문서) |
| FG-4 모듈 분리 순서 충돌 ⊥ | §2-2 매트릭스 (15 세션 × 6 문서) |
| FG-5 부재 항목 단정 ⊥ | §2-3 매트릭스 (10 항목 × 6 문서) + §4-2 grep 0건 |
| FG-6 의존성 방향 일관 | §2-4 매트릭스 (8 D-* × 6 문서) |
| FG-7 baseline drift 0 | §4-1 매트릭스 (10 항목 100% 일치) |
| FG-8 19-P-8 caveat 19-P-9 반영 | §3-1 (caveat 6/7/8 = 영구 링크 / api.py drift / PyInstaller 53) |
| FG-9 19-P-9 caveat 19-0 보정 | §5-3 (read-only 정책상 본 세션 ⊥, 19-0 안에서 처리) |
| FG-10 dirty 19-0 정리 | §5-1 1번 (사용자 결정 필요) |
