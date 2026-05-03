# 19-0 Codex 검증 요청서 — 단위화 리팩토링 전 기준 테스트/하네스 재확인

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md와 세션별 review 문서로 남겨줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-03 | (본 revision) | 초기 작성 — 19-0 단위화 리팩토링 전 기준 테스트/하네스 재확인 세션. 19-P-10 r5 Codex `pass with caveat — yes 19-1 진입 가능` 위에서 진행. **read-only 검증 — 코드/테스트/spec/UI/migrations/requirements 무수정**. 18-8 baseline (529 passed, 1 skipped, 7 xfailed) 100% 일치 + 9 AI/RAG 하네스 카테고리 + 8 기존 기능 회귀 카테고리 + PyInstaller 53 tests + 운영 DB 보호 5단계 + 외부 API 차단 + AI/RAG local-first 모두 검증. |

본 요청서는 19-0 baseline 재고정 세션 (실행 세션 #1) 의 산출물 (테스트 리포트 + baseline 결과 문서) 을 Codex 가 독립적으로 검증할 수 있도록 작성한 표준 패키지다.

본 19-0 = **19-x 실제 코드 리팩토링 진입 직전 baseline 확보**. 19-P-9 §1 (세션 시작 전) + §2 (코드 수정 전) + §5 (테스트) 체크리스트 정합. 코드 / 테스트 / migration / spec / UI / requirements 무수정 — 테스트 실행 + 결과 기록 + 보고서 작성만.

---

## 1. 세션 이름

**19-0 단위화 리팩토링 전 기준 테스트/하네스 재확인**

- 19-P-1 [현재 구조](../../docs/refactor/19_refactor_current_state.md) ~ 19-P-10 [최종 점검](../../docs/refactor/19_refactor_final_check.md) + [final_review](../../docs/refactor/19_refactor_final_review.md) 의 **후속 실행 세션 #1**.
- read-only 검증 세션. 실제 코드 / 테스트 / fixture / mock / 마이그레이션 미작성.

## 2. 이번 세션 목표

| # | 목표 | 본문 위치 |
|---|---|---|
| 1 | `pytest tests -v` 실행 — 18-8 baseline (529/1/7) 회귀 0 검증 | docs/refactor/19_refactor_baseline_test_result.md §2 |
| 2 | `ruff check app tests scripts` 통과 | §2-2 |
| 3 | `python scripts/check_db_path.py` 운영 DB 보호 | §2-2 |
| 4 | PyInstaller 53 tests | §2-2 |
| 5 | 9 AI/RAG 하네스 카테고리 모두 통과 (RAG / Safety / Chunker / Reindex / Vector / Hybrid / Health/Admin / ManualQA / AI-Mode) | §3-1 / §10 |
| 6 | 8 기존 기능 회귀 카테고리 모두 통과 (예약 / 휴무 / SMS / 통계 / 환자/치료사 / 관리자/백업 / 기존 SMS AI / 기존 휴무 AI) | §3-2 / §11 |
| 7 | 운영 DB 보호 5단계 + 외부 API 차단 + local_only 호출 0 검증 | §8 / §9 |
| 8 | API 응답 키 33+ 셋 보존 검증 | §10-1 |
| 9 | 부재 항목 단정 ⊥ (Doctor / doctor_id / no_show / `/api/health`) grep 0건 | §7-1 |
| 10 | 19-1 진입 권고 (BG-1 ~ BG-10 게이트 평가) | §12 |

## 3. 실행한 테스트 명령

| # | 명령 | 결과 |
|---|---|---|
| C-1 | `venv/Scripts/python.exe -m pytest tests -v --tb=short` | **529 passed, 1 skipped, 7 xfailed, 27 warnings** (11.74초) |
| C-2 | `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** (exit 0) |
| C-3 | `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0 (운영 DB 경로 감지 = 직접 실행 시 정상) |
| C-4 | `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **53 passed** (0.39초) |
| C-5 | (카테고리별) `pytest tests/test_<cat>*.py --tb=no -q` | 각 카테고리 모두 통과 ([19_refactor_baseline_test_result.md §3](../../docs/refactor/19_refactor_baseline_test_result.md) 정합) |

## 4. 테스트 결과

### 4-1. 종합

- **passed = 529** ✓ (18-8 baseline 정확 일치)
- **skipped = 1** ✓
- **xfailed = 7** ✓
- **failed = 0**
- **errors = 0**
- warnings = 27 (PytestReturnNotNoneWarning — 기존 알려진 패턴, 회귀 0)

### 4-2. AI/RAG 하네스 9 카테고리

RAG 49 / Safety 36 / Chunker 35 / Reindex 24 / Vector 36 / Hybrid 46 / Health-Admin 82 / ManualQA 19 / AI-Mode 19 — **모두 통과**.

### 4-3. 기존 기능 회귀 8 카테고리

Appointment 6+1+3xfail / Leaves 10+4xfail / SMS 6 / Stats 6 / Employee 4 / AI-SMS 27 / AI-ActionLeave 44 / AI-Logging 6 — **모두 통과**.

### 4-4. PyInstaller / 마이그레이션

PyInstaller hidden imports 53 + Migration spec discovery — **모두 통과**.

## 5. 실패한 테스트와 원인

**failed = 0 / errors = 0**.

xfail 7건 + skip 1건 = 백엔드 차단 미구현 (19-P-7 R-APPT-02 / R-APPT-03 / R-APPT-04 정합) — 19-4 / 19-5 정방향 전환 예정. **본 19-0 시점 해결 필수 ⊥**.

## 6. 코드 수정 여부

**0건** — 본 19-0 = read-only 검증 세션. `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements*.txt app/templates app/static pyproject.toml` = 18-0~18-8 기존 5 tracked dirty 만 (본 19-0 추가 변경 0).

수정한 파일 (모두 docs/ 또는 reports/ 영역):
- `docs/refactor/19_refactor_baseline_test_result.md` (신규)
- `reports/refactor/19-0_test_report.md` (신규)
- `reports/refactor/latest_test_report.md` (덮어쓰기)
- `reports/refactor/19-0_codex_review_request.md` (본 문서, 신규)
- `reports/refactor/latest_codex_review_request.md` (덮어쓰기)

## 7. 수정 금지 범위 준수 여부

11개 금지 항목 (사용자 명시) 모두 준수:
1. ✓ 기능 코드 리팩토링 0
2. ✓ app/ 구조 이동 0
3. ✓ 새 기능 추가 0
4. ✓ DB schema 변경 0
5. ✓ migration 생성 0
6. ✓ UI 변경 0
7. ✓ 기존 API 응답 key 변경 0 (33+ 키 셋 보존)
8. ✓ 하네스/테스트 약화 0 (529 passed 통과로 확인)
9. ✓ 운영 DB 접근 0
10. ✓ 실제 외부 API 호출 0
11. ✓ requirements.txt / PyInstaller spec 수정 0

추가:
- 18-8 baseline 회귀 보호 100%
- m001~m013 diff 0
- 19-P-1 ~ 19-P-10 산출물 무수정

## 8. 운영 DB 보호 여부

- ✓ S-1 ~ S-5 자동 통과 ([baseline_test_result.md §8](../../docs/refactor/19_refactor_baseline_test_result.md))
- ✓ `scripts/check_db_path.py` exit 0
- ✓ `tests/conftest.py` 4단계 격리 활성
- ✓ `tests/harness/db_guard.py` `assert_safe_db_path()` 호출 (import-time 1 + session-scope 1)
- ✓ `_block_sdk_modules` 활성

> 운영 DB `%APPDATA%\도수치료예약\clinic.db` 미접근 100% 정합.

## 9. 외부 API 호출 여부

- ✓ `_block_sdk_modules` 자동 활성 (openai / anthropic SDK 클래스 RuntimeError 로 교체)
- ✓ FakeProvider / FakeEmbeddingProvider 만 사용 (`tests/harness/fake_provider.py`)
- ✓ `local_only` 모드 LLM/Embedding 호출 0 (AI-Mode 19 passed)
- ✓ 실제 OpenAI / Anthropic / 문자나라 API 호출 0건
- ✓ API key 원문 응답/로그/audit 부재 (Safety 36 passed)

## 10. AI/RAG 하네스 결과

[docs/refactor/19_refactor_baseline_test_result.md §10](../../docs/refactor/19_refactor_baseline_test_result.md) 정합:
- 18-1 RAG 49 ✓
- 18-1 Safety 36 ✓
- 18-3 Chunker 35 ✓
- 18-4 Reindex 24 ✓
- 18-5 Vector 36 ✓
- 18-6 Hybrid 46 ✓
- 18-7 Health/Admin 82 ✓
- ManualQA / Contract 19 ✓
- AI-Mode (local-first) 19 ✓

응답 키 33+ 보존:
- `/api/ai/manual/search` (3 키) ✓
- `/api/ai/manual/ask` (9 키) ✓
- `sources[]` (3 키) ✓
- `/api/ai/health` admin 9 키 ✓
- `/api/ai/health/public` 4 키 ✓
- `/api/ai/status` 18-7 9 top-level ✓

## 11. 기존 기능 회귀 결과

[docs/refactor/19_refactor_baseline_test_result.md §11](../../docs/refactor/19_refactor_baseline_test_result.md) 정합:
- 예약 6 passed + 1 skipped + 3 xfailed (19-4 정방향 전환 예정)
- 휴무 10 passed + 4 xfailed (19-4/19-5 정방향 전환 예정)
- SMS 6 passed
- 통계 6 passed
- 환자/치료사 4 passed
- 관리자/백업 6 passed (admin_auth)
- 기존 SMS AI 27 passed (warnings 21)
- 기존 휴무 AI 44 passed
- AI-Logging 6 passed

> **회귀 0건**.

## 12. 19-1 core 공통 유틸 정리 진입 판단 기준

| 게이트 | 통과 조건 | 본 19-0 결과 |
|---|---|---|
| BG-1 코드 무수정 (read-only) | 본 19-0 추가 변경 0 | ✓ pass |
| BG-2 18-8 baseline 회귀 0 | 529 / 1 / 7 정확 일치 | ✓ pass |
| BG-3 ruff lint | All checks passed | ✓ pass |
| BG-4 운영 DB 보호 (S-1~S-5) | 모두 활성 | ✓ pass |
| BG-5 외부 API 차단 | _block_sdk_modules + FakeProvider | ✓ pass |
| BG-6 PyInstaller 53 tests | 53 passed | ✓ pass |
| BG-7 baseline 측정값 drift 0 | api.py 5127 / endpoint 86 / ORM 19 / migrations 13 / tests 40 | ✓ pass |
| BG-8 부재 항목 단정 ⊥ | Doctor / doctor_id / no_show / `/api/health` grep 0 | ✓ pass |
| BG-9 9 AI/RAG 하네스 + 8 기존 기능 회귀 모두 통과 | 모두 pass | ✓ pass |
| BG-10 사용자 결정 1건 (dirty worktree) | 사용자 결정 필요 | **(19-1 진입 직전)** |

→ BG-1 ~ BG-9 = **9 pass** + BG-10 사용자 결정 답변 후 = **종합 yes — 19-1 진입 가능**.

## 13. Codex 가 검증해야 할 문서

### 1차 (필수)

- [docs/refactor/19_refactor_baseline_test_result.md](../../docs/refactor/19_refactor_baseline_test_result.md) (본 세션 신규)
- [reports/refactor/19-0_test_report.md](19-0_test_report.md) (본 세션 신규)
- [reports/refactor/latest_test_report.md](latest_test_report.md) (덮어쓰기 — 본 세션과 동일)

### 2차 (대조 기준)

- [reports/ai_dev_loop/18-8_test_report.md](../ai_dev_loop/18-8_test_report.md) (18-8 baseline 비교)
- [docs/refactor/19_refactor_test_strategy.md](../../docs/refactor/19_refactor_test_strategy.md) (T-1~T-15 + 보강 9개)
- [docs/refactor/19_refactor_rollout_plan.md](../../docs/refactor/19_refactor_rollout_plan.md) §3-0 (19-0 세션 계획)
- [docs/refactor/19_refactor_checklists.md](../../docs/refactor/19_refactor_checklists.md) §1+§2+§5
- [docs/refactor/19_refactor_risk_register.md](../../docs/refactor/19_refactor_risk_register.md) (R-APPT-02 / R-APPT-03 등)
- [docs/refactor/19_refactor_final_review.md](../../docs/refactor/19_refactor_final_review.md) (19-P-10 r2)
- [reports/refactor/19-P-10_codex_review.md](19-P-10_codex_review.md) (직전 r5 Codex 결과)
- [docs/releases/18_ai_rag_final_checklist.md](../../docs/releases/18_ai_rag_final_checklist.md) (18-AI 최종 체크리스트)

### Codex 가 직접 검증할 명령

```bash
# 코드 무수정
git status --short | grep -v "^.test-tmp"
git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml

# 18-8 baseline 재실측
venv/Scripts/python.exe -m pytest tests -q   # 529 passed, 1 skipped, 7 xfailed 기대
venv/Scripts/python.exe -m ruff check app tests scripts   # All checks passed!
venv/Scripts/python.exe scripts/check_db_path.py   # exit 0
venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q   # 53 passed

# baseline 측정값 일치
wc -l app/routers/api.py app/routers/ai.py app/templates/main.html app/static/css/app.css   # 5127 / 929 / 7331 / 3626
grep -cE "^@router\\." app/routers/api.py app/routers/ai.py   # 86 / 13
grep -cE "^class \\w+\\(Base\\)" app/models/models.py   # 19
ls app/migrations/m0*.py | wc -l   # 13
ls tests/test_*.py | wc -l   # 40

# 부재 항목
grep -cE "class Doctor|class Department|class Room|class DoctorSchedule|class Order|class Prescription|class Resource" app/models/models.py   # 0
grep -c "doctor_id" app/models/models.py   # 0
grep -c "no_show" app/models/models.py   # 0
```

## 14. Codex 검증 결과 기록 위치

- [reports/refactor/19-0_codex_review.md](19-0_codex_review.md) (영구)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

응답 형식 권장:

```markdown
# 19-0 Codex 검증 결과

## 1. 종합 판정
{pass | pass with caveat | fail}

## 2. 게이트별 결과
- BG-1 ~ BG-10: {결과 + 근거}

## 3. 추가 발견 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-1 진입 권고
{yes / no + 근거 + 사용자 결정 1건 답변 후 / 답변 전 진행 여부}
```

## 15. Claude Code 자체 판단

**yes (19-1 진입 권고 — 사용자 dirty worktree 처리 결정 답변 후)**.

근거:
1. 본 세션 read-only 정책 100% 준수 — 코드/테스트/spec/UI/migrations/requirements 변경 0.
2. 18-8 baseline (529 passed, 1 skipped, 7 xfailed) 100% 정확 일치 — 회귀 0.
3. ruff / check_db_path / PyInstaller 53 tests 모두 통과.
4. 9 AI/RAG 하네스 카테고리 모두 통과 (RAG / Safety / Chunker / Reindex / Vector / Hybrid / Health-Admin / ManualQA / AI-Mode).
5. 8 기존 기능 회귀 카테고리 모두 통과 (예약 / 휴무 / SMS / 통계 / 환자/치료사 / 관리자 / 기존 SMS AI / 기존 휴무 AI).
6. 운영 DB 미접근 (S-1 ~ S-5) + 외부 API 호출 0 (`_block_sdk_modules` + FakeProvider) + local_only 호출 0 + API key 원문 / PII 비노출 100% 정합.
7. baseline 측정값 (api.py 5127 / endpoint 86 / ai.py 929 / 13 / main.html 7331 / app.css 3626 / tests 40 / ORM 19 / migrations 13 / PyInstaller 53) 모두 19-P-9 §0-2 와 정합.
8. 부재 항목 단정 ⊥ 100% 정합 (Doctor / doctor_id / no_show / `/api/health` grep 0건).
9. 응답 키 33+ 보존 (manual/search 3 / manual/ask 9 / sources 3 / health 9 / health/public 4 / status 9 + 비-AI alias).
10. xfail 7건 + skip 1건 = 19-4 / 19-5 정방향 전환 예정 (백엔드 차단 미구현 명시 — 19-P-7 R-APPT-02/03/04 정합).
11. 19-P-1 ~ 19-P-10 산출물 무수정.
12. 진입 게이트 BG-1 ~ BG-9 = 9 pass + BG-10 사용자 결정 답변 후.

남은 위험 / 사용자 결정 필요 (19-1 진입 직전):
- 18-0~18-8 dirty/untracked 변경분 처리 (머지 / commit / 유지) — 직전 19-P-10 시리즈에서 옵션 1-a-① 선택 후 commit 진행 중단된 상태. 19-1 진입 전 결정 필요.

다음 세션:
- **19-1 core 공통 유틸 정리** ([docs/refactor/19_refactor_rollout_plan.md §3-1](../../docs/refactor/19_refactor_rollout_plan.md)) — `app/core/` 신설 (config / database / errors / responses / time_utils / security / feature_flags). 19-P-9 §1+§2+§3+§5 체크리스트 적용.
