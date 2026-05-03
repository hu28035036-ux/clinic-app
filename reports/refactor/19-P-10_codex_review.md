# 19-P-10 r5 Codex 검증 결과

- 검증 대상: `reports/refactor/latest_codex_review_request.md` / `reports/refactor/19-P-10_codex_review_request.md` / `docs/refactor/19_refactor_final_check.md` / `docs/refactor/19_refactor_final_review.md`
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 판정: **pass with caveat**
- 다음 단계: **yes — 19-1 진입 가능. 단, dirty worktree 처리 방침은 사용자 결정 필요**

## 1. 검증 방식

Claude Code 요약은 신뢰 근거로 사용하지 않고, 실제 파일 구조와 문서 본문을 직접 대조했다.

- `reports/refactor/19-P-10_codex_review_request.md` 와 `reports/refactor/latest_codex_review_request.md` 를 비교했다. 결과는 동일했다.
- r5 revision 이력의 "r4 Codex baseline line count caveat 보정" 주장을 실제 파일의 raw newline / `.NET ReadLines` 기준으로 재측정했다.
- `docs/refactor/`, `reports/refactor/`, `reports/ai_dev_loop/` 의 실제 파일 수와 latest 포인터 동기화를 재확인했다.
- endpoint / ORM / migration / test 파일 수와 부재 항목 grep 결과를 실제 코드 기준으로 확인했다.
- `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 로 코드 변경 범위를 확인했다.

## 2. r5 보정 검증 결과

| 항목 | 문서 주장 | 실제 확인 | 판정 |
|---|---:|---:|---:|
| `app/routers/api.py` baseline | `wc -l` 5127 / 미종료 라인 포함 5128 | raw newline 5127 / `.NET ReadLines` 5128 | pass |
| `app/routers/ai.py` baseline | working tree 929 | raw newline 929 / `.NET ReadLines` 929 | pass |
| `app/static/css/app.css` baseline | 3626 | raw newline 3626 / `.NET ReadLines` 3626 | pass |
| `app/templates/main.html` baseline | 7331 | raw newline 7331 / `.NET ReadLines` 7331 | pass |
| API endpoint | 86 | 86 | pass |
| AI endpoint | 13 | 13 | pass |
| ORM models | 19 | 19 | pass |
| migrations `m0*.py` | 13 | 13 | pass |
| `tests/test_*.py` | 40 | 40 | pass |
| 부재 항목 grep | 0 | 0 | pass |

이전 r4 검증에서 사용한 PowerShell `Get-Content` 단순 count는 이 저장소의 현재 파일에서 raw newline 기준과 다르게 나왔다. r5가 제시한 baseline 숫자는 raw newline / `.NET ReadLines` 기준으로는 맞다.

## 3. 실제 구조 대조

| 항목 | 실제값 | 판정 |
|---|---:|---|
| `docs/refactor` 파일 수 | 12 | pass |
| `docs/refactor/19_refactor_*.md` | 12 | pass |
| `19_refactor_entry_notes.md` 제외 `19_refactor_*.md` | 11 | pass |
| `reports/refactor` 파일 수 | 24 | pass |
| `reports/refactor/19-P-*_codex_review_request.md` | 10 | pass |
| `reports/refactor/19-P-*_codex_review.md` | 10 | pass |
| `reports/ai_dev_loop/latest_test_report.md` 동기화 | pass | `19-0_test_report.md` 와 차이 없음 |
| `reports/ai_dev_loop/latest_fix_summary.md` 동기화 | pass | `19-0_fix_summary.md` 와 차이 없음 |

## 4. 코드 변경 범위

`git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 결과는 기존 18-x tracked 변경 범위와 동일했다.

```text
app/models/models.py         | 123 +++++++++++++++++-
app/routers/ai.py            |  42 ++++++
app/services/ai/manual_qa.py | 298 +++++++------------------------------------
dosu_clinic.spec             |  30 ++++-
tests/conftest.py            | 132 +++++++++++++++++++
5 files changed, 373 insertions(+), 252 deletions(-)
```

따라서 19-P-10 r5 보정은 문서/latest 포인터 중심이며, app/tests/spec/UI/migrations/requirements 범위의 신규 코드 변경은 확인되지 않았다.

## 5. 남은 Caveats

1. r5 요청서의 PowerShell 예시 중 `(Get-Content ...).Count` 는 이 환경에서 그대로 재현되지 않았다. 예를 들어 `app/routers/api.py` 는 `Get-Content` 단순 count 5058이지만 raw newline은 5127, `.NET ReadLines`는 5128이다. baseline 자체는 raw newline 기준으로 정합하지만, 검증 명령 예시는 `.NET ReadLines` 또는 raw newline 방식으로 고정하는 편이 안전하다.
2. r5 요청서의 `git show HEAD:... | Measure-Object -Line` 예시는 이 PowerShell 파이프라인에서 신뢰 가능한 값으로 재현되지 않았다. 다만 `git hash-object app/routers/api.py` 와 `git rev-parse HEAD:app/routers/api.py` 는 동일하여 `api.py` working tree와 HEAD blob이 같다는 점은 확인했다.
3. 요청서 §5의 일부 소제목이 아직 "r2 신규 (본 revision)", "r4 신규 (본 revision)"처럼 과거 revision 표현을 포함한다. 의미는 추적 가능하지만 r5 문서로는 라벨이 조금 stale이다.
4. 현재 worktree는 여전히 dirty 상태다. modified tracked 6개와 다수 untracked 파일이 있으며, 19-1 시작 전 사용자 결정이 필요하다.

## 6. 종합 판정

19-P-10 r5가 목표로 한 baseline line count 보정은 핵심적으로 확인됐다. r4에서 잡았던 line count caveat는 `Get-Content` 단순 count 방식 때문에 생긴 측정 기준 문제였고, raw newline / `.NET ReadLines` 기준으로는 문서의 baseline과 맞는다.

다만 요청서 안의 일부 검증 명령 예시와 revision 라벨은 여전히 다듬을 여지가 있어 판정은 **pass with caveat** 로 둔다. 이 caveat들은 구조계획 자체나 19-1 진입 가능성을 차단하지 않는다.

다음 단계는 **yes — 19-1 진입 가능** 이다. 단, dirty worktree 처리 방침은 19-1 시작 전에 확정하는 것이 좋다.
