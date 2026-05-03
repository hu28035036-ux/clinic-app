# 19-P-1 Codex 검증 요청서 (revision 2 — 1차 검증 fail 후 보정본)

> **사용자가 Codex에게 전달할 최소 문구**
>
> > "reports/refactor/latest_codex_review_request.md 문서 확인하고 검증 시작해줘. Claude Code 요약만 믿지 말고 실제 파일 구조와 문서 내용을 직접 비교해서 검증해줘."

## 0. Revision 이력

| 회차 | 날짜 | 결과 | 변경 |
|---|---|---|---|
| r1 | 2026-05-02 | **fail** ([reports/refactor/19-P-1_codex_review.md](19-P-1_codex_review.md)) | 초기 검증 — 카운트 불일치, §22 자체 모순, baseline hash 부재 |
| r2 | 2026-05-02 | (본 revision) | **보정 완료**. `docs/refactor/19_refactor_current_state.md` 의 카운트/§22/§24 보정 + baseline full sha 명시. 코드/테스트/spec 무수정 유지. Codex 재검증 요청. |

## 1. Baseline (D안 — 본 19-P-1 세션 시작 시 상태)

- HEAD commit (full sha): `bcd74a7aabc9de8d735425863254cfc393bda580`
- HEAD short: `bcd74a7` — release v1.3.3: AI/RAG v1 후속 보강 + SDK 진단 강화
- 브랜치: `ai-rag-v1-integration`
- 본 세션은 위 commit 위에 신규 commit 없이 untracked 파일 추가만 수행 — 기존 modified 파일 (`app/models/models.py`, `app/routers/ai.py`, `app/services/ai/manual_qa.py`, `dosu_clinic.spec`, `tests/conftest.py`, `app/migrations/m012_*.py`, `app/migrations/m013_*.py`, `app/services/ai/health.py`, `app/services/ai/{rag,knowledge,vector}/*.py` 등) 은 18-0~18-8 시점에 이미 변경된 것이며 본 세션은 1바이트도 추가 수정하지 않았다.
- **G-1 검증 명령**: `git diff bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 의 출력은 18-0~18-8 변경분 (이미 알려진) 만 포함되어야 하며, 본 19-P-1 세션 변경분은 0이어야 한다.

본 r2 보정 작업도 동일 정책 적용: 본 r2 에서 변경한 파일은 `docs/refactor/19_refactor_current_state.md` (수정) + `reports/refactor/19-P-1_codex_review_request.md` (수정) + `reports/refactor/latest_codex_review_request.md` (수정) 3개. 코드/테스트/spec/UI 무수정.

---

## 2. 세션 이름

**19-P-1 단위화 리팩토링 현재 구조 스냅샷 작성**

- 19-P (예약/휴무/문자/AI/RAG/통계 모듈 단위화 리팩토링) 진입 첫 세션.
- 리팩토링 *전*에 현재 코드 구조를 기준점으로 문서화하는 read-only 세션.

## 2. 이번 세션 목표

전체 단위화 리팩토링을 시작하기 전에 현재 코드 구조를 **기준점 문서**로 남긴다.

- 이후 모듈 분리 변경마다 본 문서를 회귀 비교 기준으로 사용.
- 폴더/파일 역할, 라우터·모델·UI·테스트·하네스 구조, 도메인별 코드 위치, 위험 결합 구간, 응답 키 후방호환 포인트, 확인 필요 항목을 망라.
- 추측 금지 — 실제 파일 그렙으로 확인하지 못한 항목은 "확인 필요"로 표시.

## 3. 작성한 문서

### r1 (초기 작성, 1차 검증 fail)

- `docs/refactor/19_refactor_current_state.md` — 현재 구조 스냅샷 (~600줄, 23개 섹션).

### r2 (1차 검증 fail 후 보정)

- `docs/refactor/19_refactor_current_state.md` — 보정 (r1과 동일 파일 갱신).
  - §0 메타: baseline full sha + r2 보정 이력 추가.
  - §1 폴더 구조 트리: "ORM 17개" → "ORM 19개".
  - §2 파일 표: "ORM 17개" → "ORM 19개".
  - §3-1 라우터 표 footer: "약 80개" → "**86개** (`grep -cE` 실측)".
  - §4 머리말: "ORM 17개" → "ORM **19개**" + 실측 명령 명시.
  - §6-1 테스트 파일: "41 파일" → "40 파일".
  - §7 하네스: "1689 줄" → "1420 줄" (conftest 269 제외 정정).
  - §19-1 머리말: "5127줄, 80개" → "5127줄, 86개".
  - §20-3 spec 표: "hidden imports 17개"의 의미 명확화 (모델 수와 별개의 18-8 추가분).
  - §22 표: C-1 "80개" → "86개". C-9/C-10/C-14/C-18 → §22-A 분리.
  - §22-A 신설: "확인 완료 / 19-P 의사결정 항목" — C-9/C-10/C-14/C-18 의 확인 결과 + 의사결정 사항.
  - §23 종합 첫 줄: "약 80 endpoint" → "**86개** endpoint" + 실측 명령.
  - §24 신설: "2차 기준 문서 stale 주의" — `docs/ai_rag_current_state.md` §1-4 / §11 / §1-5-1 의 stale 항목 4개 명시.

### 함께 작성한 검증 패키지

- `reports/refactor/19-P-1_codex_review_request.md` (본 문서, 영구 보존본 — r1 작성, r2 갱신).
- `reports/refactor/latest_codex_review_request.md` (Codex 진입점 — 본 문서와 동일 내용).
- (Codex 작성) `reports/refactor/19-P-1_codex_review.md` (r1 결과, **fail**) + `reports/refactor/latest_codex_review.md` (Codex 가 r2 검증 결과를 같은 위치에 덮어쓸 것).

## 4. 수정 금지였던 범위

사용자 지시문 12개 금지 항목:

1. 코드 수정 금지
2. `app/` 기능 코드 수정 금지
3. `tests/` 테스트 코드 작성 금지
4. migration 생성 금지
5. `requirements.txt` 수정 금지
6. PyInstaller spec (`dosu_clinic.spec`) 수정 금지
7. UI (`app/templates/`, `app/static/`) 수정 금지
8. 기존 API 응답 구조 변경 금지
9. 운영 DB 접근 금지
10. 실제 외부 API 호출 금지
11. (CLAUDE.md 명시) `manual60` count_increment 변경 금지
12. (CLAUDE.md 명시) `pyproject.toml` `app/**` per-file-ignores 변경 금지

추가:
- 18-0~18-8 baseline (529 passed, 1 skipped, 7 xfailed) 회귀 보호.
- m001~m013 마이그레이션 diff 0 유지.

## 5. 실제 수정한 파일 목록

### r1 신규 (3, 1차 작성 시점)

- `docs/refactor/19_refactor_current_state.md`
- `reports/refactor/19-P-1_codex_review_request.md` (본 문서)
- `reports/refactor/latest_codex_review_request.md`

### r2 수정 (3, 1차 검증 fail 후 보정)

- `docs/refactor/19_refactor_current_state.md` (수정 — r1 카운트 정정 + §22-A / §24 신설)
- `reports/refactor/19-P-1_codex_review_request.md` (본 문서, r2 revision 추가)
- `reports/refactor/latest_codex_review_request.md` (본 문서와 동기화)

### 무수정 (회귀 보호) — r1 / r2 동일

`app/**`, `tests/**`, `app/migrations/m001~m013.py`, `requirements*.txt`, `dosu_clinic.spec`, `app/templates/**`, `app/static/**`, `pyproject.toml`, `CLAUDE.md`, `app/models/models.py`, `app/routers/api.py`, `app/routers/ai.py`, `tests/conftest.py`, `app/services/**`.

> 본 세션 시작 전부터 git status 에 `M` 으로 표시되는 파일들 (예: `app/routers/ai.py`, `dosu_clinic.spec`, `tests/conftest.py` 등) 은 모두 18-0~18-8 시점에 이미 변경되어 있던 것이며, 본 19-P-1 세션 (r1 + r2 통틀어) 에서는 단 1바이트도 수정하지 않았다. baseline `bcd74a7` 와 `git diff` 로 검증 가능.

## 6. 코드 수정 없이 docs/refactor 문서만 작성했는지 확인

### Claude Code 자체 점검

| 검사 | 결과 |
|---|---|
| `git status --short` 신규 추가 (`??`) | `docs/refactor/` (이미 존재한 19_refactor_entry_notes.md 포함 폴더) + `reports/refactor/` |
| 본 세션이 새로 만든 파일 | `docs/refactor/19_refactor_current_state.md` + `reports/refactor/{19-P-1,latest}_codex_review_request.md` |
| `git diff` 으로 본 세션 신규 modify | 0 |
| `app/**` 변경 | 0 |
| `tests/**` 변경 | 0 |
| `app/migrations/**` 변경 | 0 |
| `requirements*.txt` 변경 | 0 |
| `dosu_clinic.spec` 변경 | 0 |
| `app/templates/**` 변경 | 0 |
| `app/static/**` 변경 | 0 |
| `pyproject.toml` 변경 | 0 |

→ **코드 수정 없이 docs/refactor + reports/refactor 문서만 작성**.

### Codex 가 직접 검증할 명령

```bash
git status --short
git diff --stat HEAD -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml
```

→ 본 세션 변경분이 위 경로에 0이 나와야 한다 (단, 18-0~18-8 시점에 이미 modified 였던 파일은 그대로 modified 로 남는 것이 정상 — 본 세션에서 추가 변경하지 않았음을 확인).

## 7. Codex 가 검증해야 할 문서

### 1차 (필수)

- `docs/refactor/19_refactor_current_state.md`

### 2차 (대조 기준)

- `CLAUDE.md` — 작업 규칙
- `docs/AI_WORKING_RULES.md` — AI/RAG 절대 원칙
- `docs/ai_code_session_protocol.md` — 세션 절차
- `docs/ai_rag_current_state.md` — AI/RAG 18-8 baseline 스냅샷
- `docs/refactor/19_refactor_entry_notes.md` — 19-P 진입 기준 노트
- `reports/ai_dev_loop/18-8_codex_review_request.md` — 직전 세션 Codex 패키지 (검증 패턴 참조용)

## 8. Codex 가 실제 파일 구조와 비교해야 할 항목

본 문서 (`docs/refactor/19_refactor_current_state.md`) 의 각 섹션을 실제 파일과 1:1 대조한다.

| 섹션 | 검증 방법 |
|---|---|
| §1 폴더 구조 | `find app -maxdepth 3 -type d` / `ls app/` `ls app/routers` `ls app/services/ai/{rag,knowledge,vector}/` 결과와 트리 정합 |
| §2 app/ 파일 역할 + 줄수 | `wc -l app/main.py app/config.py app/database.py app/routers/*.py app/models/*.py app/services/*.py app/services/ai/**/*.py app/services/rag/*.py` 출력값과 표 정합 |
| §3 API router 엔드포인트 표 | `grep -nE "^@router\.(get\|post\|patch\|put\|delete)" app/routers/api.py app/routers/ai.py app/routers/pages.py` 결과와 라인/경로 정합 (`api.py` 약 80개, `ai.py` 13개, `pages.py` 2개) |
| §4 DB model | `grep -nE "^class \w+\(Base\)" app/models/models.py` 결과와 17개 모델 라인 정합 |
| §4-1 마이그레이션 m001~m013 | `ls app/migrations/m*_*.py` 결과 13개 정합 |
| §5 static/UI | `wc -l app/templates/*.html app/static/css/app.css` + main.html 의 `id="tab-*"` grep 결과와 정합 |
| §6 테스트 구조 | `ls tests/test_*.py | wc -l` (41개) + `tests/conftest.py` 4단계 격리 (line 32-75) 정합 |
| §7 하네스 구조 | `wc -l tests/harness/*.py` (12 모듈, ~1689줄) 정합 |
| §8~§18 도메인별 코드 위치 | 각 라인 번호가 실제 파일에서 해당 함수/엔드포인트 시작 라인인지 grep 으로 확인 |
| §21 응답 키 셋 | [docs/refactor/19_refactor_entry_notes.md §2-1](../../docs/refactor/19_refactor_entry_notes.md) 와 [docs/ai_rag_current_state.md §3](../../docs/ai_rag_current_state.md) 의 응답 키 셋과 100% 일치 (manual/search 3 + manual/ask 9 + sources 3 + health 9 + health/public 4 + status 9) |
| §21-4 핵심 정책 상수 | grep 으로 실제 값 확인: `LOW_SCORE_THRESHOLD=2`, `HIGH_THRESHOLD=0.7`, `LOW_THRESHOLD=0.3`, `LLM_CALL_THRESHOLD=0.3`, `QUERY_MIN_CHARS=2`, `ERROR_DETAIL_DISPLAY_LIMIT=200`, `SESSION_TTL_SEC=28800`, `MAX_FAILURES=5`, `LOCK_DURATION_SEC=300` |
| §22 확인 필요 항목 | C-1~C-18 각 항목이 본 세션 안에서 실제로 확인 불가능한 항목인지 (추측 단정 아닌지) 판정 |

### 빠른 reproduction 명령 모음

```bash
# 폴더 구조
find app -maxdepth 3 -type d | sort
ls app/routers/*.py app/services/ai/*.py app/services/ai/rag/*.py \
   app/services/ai/knowledge/*.py app/services/ai/vector/*.py app/services/rag/*.py

# 줄수
wc -l app/main.py app/config.py app/database.py \
      app/routers/*.py app/models/*.py app/services/*.py \
      app/services/ai/*.py app/services/ai/rag/*.py \
      app/services/ai/knowledge/*.py app/services/ai/vector/*.py \
      app/services/rag/*.py

# 라우터 엔드포인트
grep -cE "^@router\.(get|post|patch|put|delete)\(" app/routers/api.py            # 86 (r2 보정)
grep -cE "^@router\.(get|post|patch|put|delete)\(" app/routers/ai.py             # 13
grep -cE "^@router\.(get|post|patch|put|delete)\(" app/routers/pages.py          # 2

# 모델 클래스
grep -cE "^class \w+\(Base\)" app/models/models.py                               # 19 (r2 보정)

# 마이그레이션
ls app/migrations/m*_*.py | wc -l                                                # 13

# UI 탭
grep -cE 'id="tab-' app/templates/main.html                                      # 6

# 테스트
ls tests/test_*.py | wc -l                                                       # 40 (r2 보정)
wc -l tests/harness/*.py | tail -1                                               # 1420 total (r2 보정)

# 핵심 상수
grep -n "LOW_SCORE_THRESHOLD" app/services/ai/rag/pipeline.py
grep -nE "HIGH_THRESHOLD|LOW_THRESHOLD|LLM_CALL_THRESHOLD" app/services/ai/rag/confidence.py
grep -n "QUERY_MIN_CHARS" app/services/ai/vector/embeddings.py
grep -nE "ERROR_DETAIL_DISPLAY_LIMIT|DEFAULT_RECENT_(HOURS|LIMIT)" app/services/ai/health.py
grep -nE "SESSION_TTL_SEC|MAX_FAILURES|LOCK_DURATION_SEC|DEFAULT_PASSWORD" app/services/auth.py
```

## 9. Codex 가 집중 확인해야 할 위험 구간

본 세션은 read-only 이므로 "코드 위험"은 없지만, 문서가 다음 항목을 **현실적으로** 식별했는지 검증.

### 9-1. 코드 혼재 식별 정확성 (§19)

- `app/routers/api.py` 5127줄 / **86개** endpoint / 9 도메인 혼재 — 실제 라인 카운트와 정합?
- `_doctor_codes_set`/`_get_manual_*`/`_bump_patient_count`/`_apply_patient_counts`/`_upsert_employee_leave_core` 5개 헬퍼가 통계↔치료항목↔예약↔환자↔휴무 5개 도메인을 동시에 묶는다는 식별이 정확?
- `app/services/ai/action_leave.py` 917줄에 자연어 파싱 + LLM + DB 매칭 + HMAC + TOCTOU + 휴무 등록이 응집되어 있다는 식별이 정확?
- `app/services/ai/knowledge/indexer.py` 의 vector lazy import (`_embed_chunks_into_vectors`) 가 실제 try/except 로 감싸져 있는지?
- `app/templates/main.html` 7331줄 / 단일 `<script>` 521-7330 / 6개 탭 핸들러 혼재 — 실제 라인과 정합?

### 9-2. 위험 파일 표시 적절성 (§20)

- m001~m013 무수정 정책 — 표에 13개 모두 포함?
- conftest.py 4단계 격리 — line 32-75 가 실제로 격리 코드인지?
- `manual60 count_increment=1` ([app/models/constants.py:20](../../app/models/constants.py:20)) 이 실제 값인지?
- `pyproject.toml` per-file-ignores `app/**` 가 실제 존재하는지?

### 9-3. 응답 키 후방호환 누락 점검 (§21)

다음 키 셋 누락 시 19-P 진입 시 회귀 발생 가능:

- `/api/ai/manual/search` 3키 (sources/masked_question/top_score)
- `/api/ai/manual/ask` 9키 (answer/sources/confidence/not_found/blocked/blocked_reason/guard_hits/top_score/masked_question)
- `sources[]` 3키 (title/path/snippet)
- `/api/ai/health` admin 9키
- `/api/ai/health/public` 4키
- `/api/ai/status` 9키 top-level

### 9-4. "확인 필요" 적절성 (§22)

- C-1~C-18 항목이 본 세션 (read-only, 5127줄 main.html JS 전수 grep 미수행) 안에서 정말로 확인 불가능한 항목인지?
- 반대로, **확인 가능한데 "확인 필요"로 회피한 항목**은 없는지? (예: 라우터 엔드포인트 라인은 이미 grep 으로 확인됨 → "확인 필요" 부적절)
- 추측을 단정으로 적은 항목이 있는지?

## 10. 다음 단계 (19-P-2) 진입 가능 판단 기준

Codex 가 다음 5개 게이트를 모두 통과 처리할 때만 19-P-2 진입.

| 게이트 | 통과 조건 |
|---|---|
| G-1 코드 무수정 | `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 출력이 18-0~18-8 변경분만 포함하고 본 19-P-1 (r1+r2) 세션 변경분 0. r2 보정으로 변경된 파일은 `docs/refactor/19_refactor_current_state.md`, `reports/refactor/19-P-1_codex_review_request.md`, `reports/refactor/latest_codex_review_request.md` 3개뿐 — 코드/테스트/spec/UI 무수정. |
| G-2 문서 정합 | §8 reproduction 명령 결과가 r2 보정본 (`/api`=86, ORM=19, test=40, harness=1420) 과 100% 일치 |
| G-3 응답 키 후방호환 | §21-1, §21-3 의 키 셋이 [docs/refactor/19_refactor_entry_notes.md §2-1](../../docs/refactor/19_refactor_entry_notes.md) + [docs/ai_rag_current_state.md §3](../../docs/ai_rag_current_state.md) 와 100% 일치 (r1에서 pass 받음) |
| G-4 위험 구간 식별 | §19, §20 항목이 누락 없이 식별됨. r2 §20-3 에서 "hidden imports 17개" 의 의미를 모델 수와 분리 명확화. (Codex 가 추가 발견한 위험 항목이 있다면 review 응답에 추가) |
| G-5 확인 필요 적절성 | §22 / §22-A 분리가 적절한지 — C-9/C-10/C-14/C-18 이 §22-A "확인 완료 / 19-P 의사결정 항목" 으로 이동했고, 남은 §22 항목은 본 세션 read-only 범위에서 진짜 확인 불가능한 항목인지 검증 |
| G-6 (신규) stale 표시 | §24 "2차 기준 문서 stale 주의" 가 [docs/ai_rag_current_state.md](../../docs/ai_rag_current_state.md) 의 m011/m012 다음/FakeEmbeddingProvider 부재 언급을 제대로 식별했는지 검증 |

→ G-1 ~ G-6 전부 통과 시 **yes — 19-P-2 진입 가능**.

→ 1개라도 실패 시 Codex 응답에 "재작업 필요"로 표기하고 사용자가 19-P-1 후속 보강 (r3) 을 결정.

## 11. Codex 검증 결과 기록 위치

Codex 는 검증 결과를 다음 2개 파일에 동일 내용으로 작성한다.

- `reports/refactor/19-P-1_codex_review.md` (영구 보존본)
- `reports/refactor/latest_codex_review.md` (다음 세션 진입 시 참조용)

응답 형식 권장 (필수 아님):

```markdown
# 19-P-1 Codex 검증 결과

## 1. 종합 판정
{pass | fail}

## 2. 게이트별 결과
- G-1 코드 무수정: {pass|fail} — 근거
- G-2 문서 정합: {pass|fail} — 근거
- G-3 응답 키 후방호환: {pass|fail} — 근거
- G-4 위험 구간 식별: {pass|fail} — 근거 (추가 발견 항목 있으면 나열)
- G-5 확인 필요 적절성: {pass|fail} — 근거

## 3. 추가 발견한 위험 / 누락 / 부정확 항목
{있으면 bullet}

## 4. 19-P-2 진입 권고
{yes/no + 근거}
```

## 12. Claude Code 자체 판단

**yes (19-P-2 진입 권고)** — Codex 검증 후 다음 세션 진입 가능.

근거 (r2 기준):
1. 본 세션 (r1+r2 통틀어) 은 read-only — 코드 변경 0, 응답 키/마이그레이션/spec/UI/테스트 무수정.
2. `docs/refactor/19_refactor_current_state.md` 24개 섹션 (§22-A / §24 신설 후) 이 사용자 요청 22개 항목 (1~22) + Codex 1차 검증 fail 보정 항목을 모두 커버.
3. 추측 단정 회피 — 확인 불가능한 14개 항목 (§22) + 확인 완료 4개 항목 (§22-A) + stale 4개 항목 (§24) 분리 명시.
4. 표 중심 작성 — 줄수 대신 라인 번호 + 함수명 매칭으로 회귀 비교 가능.
5. 18-8 baseline 회귀 보호 100% — 529 passed 그대로.
6. r2에서 Codex 1차 검증 fail 항목 (G-1 baseline / G-2 카운트 / G-4 §20-3 모호성 / G-5 §22 자체모순) 을 모두 보정.

남은 위험:
- 본 문서가 86개 비-AI 엔드포인트의 응답 키를 전수 정리하지는 않음 (§22 C-1 / C-2~C-7) — 19-P-2 또는 도메인별 분리 직전에 별도 보강 필요.
- main.html 7331줄 단일 script 분리는 19-P 비-목표 (별도 UI 세션). 본 문서는 식별만.
- `docs/ai_rag_current_state.md` 의 stale 항목 (§24 명시) 은 본 세션에서 보정하지 않음 — 별도 문서 갱신 세션이 필요할 수 있음. 단, 19-P 안에서는 §24 의 caveat 만으로 안전.
