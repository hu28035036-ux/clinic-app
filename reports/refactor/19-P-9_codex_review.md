# 19-P-9 Codex 검증 결과

- 검증 대상: `reports/refactor/latest_codex_review_request.md` / `reports/refactor/19-P-9_codex_review_request.md` / `docs/refactor/19_refactor_checklists.md`
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 판정: **pass with caveat**
- 다음 단계: **yes — 19-P 최종 점검 또는 19-0 baseline 재고정 진입 가능**

## 1. 검증 방식

Claude Code 요약은 신뢰 근거로 사용하지 않고, 실제 파일 구조와 문서 본문을 직접 대조했다.

- `reports/refactor/19-P-9_codex_review_request.md` 와 `reports/refactor/latest_codex_review_request.md` 를 `Compare-Object` 로 비교: 차이 없음.
- `docs/refactor/19_refactor_checklists.md` 의 섹션 / 체크박스 / 모듈별 항목 / gate 항목을 직접 카운트.
- 19-P-8 caveat 3개가 §0-1, §0-2, §5-12, §9-4에 반영됐는지 확인.
- `app/routers/api.py`, `app/routers/ai.py`, `app/templates/main.html`, `app/static/css/app.css`, `tests/`, `app/models/models.py`, `app/migrations/` 의 실제 구조를 직접 대조.
- `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 로 코드 변경 범위를 확인.

## 2. 확인 결과

| 항목 | 결과 | 근거 |
|---|---:|---|
| 19-P-9 요청서와 latest 요청서 동일성 | pass | `Compare-Object` 결과 차이 없음 |
| 신규 산출물 존재 | pass | `docs/refactor/19_refactor_checklists.md`, `reports/refactor/19-P-9_codex_review_request.md`, `reports/refactor/latest_codex_review_request.md` 존재 |
| §1 세션 시작 전 | pass | `### 1-1` ~ `### 1-8` = 8개 |
| §2 코드 수정 전 | pass | `### 2-1` ~ `### 2-9` = 9개 |
| §3 코드 이동 / 분리 | pass | `### 3-1` ~ `### 3-8` = 8개 |
| §4 주석 / 문서화 | pass | `### 4-1` ~ `### 4-9` = 9개, COMPAT/SAFETY/NOTE/RISK/TODO/TEMP 포함 |
| §5 테스트 | pass | `### 5-1` ~ `### 5-12` = 12개 |
| §6 모듈별 특수 | pass | `### 6-1` ~ `### 6-8` = 8개 |
| §7 실패 대응 | pass | `### 7-1` ~ `### 7-7` = 7개 |
| §8 완료 | pass | `### 8-1` ~ `### 8-12` = 12개 |
| §9 Codex 검증 요청 | pass | `### 9-1` ~ `### 9-6` = 6개 |
| 체크박스 수 | pass | `- [ ]` = 328개로 요청서의 79+ 기대 초과 |
| 19-P-8 caveat 1 반영 | pass | `latest_codex_review.md` 대신 `19-P-7_codex_review.md` / `19-P-8_codex_review.md` 영구 보존본 링크 사용 원칙 명시 |
| 19-P-8 caveat 2 반영 | pass | `api.py` 5127(bash) / 5128(PowerShell) drift 명시, endpoint 86개 영향 없음 명시 |
| 19-P-8 caveat 3 반영 | pass | PyInstaller 53 tests 산출 공식: 15 non-parametrized + 19×2 parametrized 명시 |
| 실제 API 구조 | pass | `app/routers/api.py` endpoint 86개, PowerShell line count 5128 / `app/routers/ai.py` endpoint 13개, line count 929 |
| 실제 파일 구조 | pass | `main.html` 7331줄, `app.css` 3626줄, `tests/test_*.py` 40개, ORM 모델 19개, migration `m0*.py` 13개 |
| 부재 항목 단정 금지 | pass | 모델에 Doctor/Department/Room/DoctorSchedule/Order/Prescription/Resource class 0개, `Patient.doctor_id` 0개, `no_show` 0개, `/api/health` 0개 |
| 코드 무수정 범위 | pass with caveat | diff stat은 기존 18-x dirty 변경과 동일한 5개 tracked 파일만 표시. 19-P-9 신규 코드 변경은 확인되지 않음 |

## 3. Caveats

1. 요청서의 섹션 카운트 명령 `grep -nE "^## [0-9]+\\." ... | wc -l # 11 기대` 는 그대로 실행하면 `docs/refactor/19_refactor_checklists.md` §9-5 안의 fenced markdown 예시 (`## 1. 종합 판정` 등)까지 잡아 15개로 계산될 수 있다. 본문 구조 자체는 §0~§10 11개가 맞지만, 자동 검증 명령은 코드블록 제외 방식으로 보정하는 편이 안전하다.
2. PyInstaller “53 tests” 산출 공식은 정적 구조로 확인했다. 다만 현재 로컬 Python / venv 런처 문제로 pytest collection 실행은 하지 못했다. 19-0 baseline 재고정 시 실제 `pytest --collect-only` 또는 테스트 실행으로 재확인하는 것이 좋다.
3. 요청서의 2차 대조 기준 일부에 `19-P-5 r2` 표기가 있으나 현재 review 계보와 문서 메타는 `19-P-5 r3` 기준이다. 실질 링크와 문서 존재에는 문제가 없어 진행 차단 사유는 아니다.

## 4. G-1 ~ G-12 판정

| Gate | 판정 | 근거 |
|---|---|---|
| G-1 코드 무수정 | pass with caveat | 대상 코드 diff stat은 기존 dirty 변경과 동일. 19-P-9 문서 외 신규 코드 변경 증거 없음 |
| G-2 §1 세션 시작 전 | pass | §1-1 ~ §1-8 |
| G-3 §2 코드 수정 전 | pass | §2-1 ~ §2-9 |
| G-4 §3 코드 이동 | pass | §3-1 ~ §3-8 |
| G-5 §4 주석 / 문서화 | pass | §4-1 ~ §4-9, 6개 주석 카테고리 포함 |
| G-6 §5 테스트 | pass | §5-1 ~ §5-12, pytest/ruff/check_db_path/run_check/PyInstaller 포함 |
| G-7 §6 모듈별 특수 | pass | appointments/leaves/treatments/stats/sms/patients/admin+settings/ai+rag 8개 |
| G-8 §7 실패 대응 | pass | 5회 루프, latest_failure_report, 땜질 금지, rollback, Codex 요청 포함 |
| G-9 §8 완료 | pass | 변경 파일, wrapper, 응답 key, 테스트, 영구 보존본, Codex 게이트 포함 |
| G-10 §9 Codex 검증 요청 | pass | 작성 문서 2개, 14항목 표준, 검증 명령, 결과 위치, 응답 형식, 최소 문구 포함 |
| G-11 19-P-8 caveat 3개 반영 | pass | 영구 링크 / api.py line drift / PyInstaller 53 산출 공식 반영 |
| G-12 19-P-1 ~ 19-P-8 충돌 없음 | pass with caveat | 주요 원칙과 정합. 단, 자동 grep 명령과 19-P-5 r2/r3 표기는 보정 권장 |

## 5. 최종 판단

**pass with caveat**. 19-P-9 공통 체크리스트는 19-x 실제 코드 리팩토링 세션에서 반복 사용할 수 있을 만큼 충분히 구체적이며, 19-P-8 caveat 3개도 반영되어 있다.

다음 단계는 **yes — 19-P 최종 점검 또는 19-0 baseline 재고정 진입 가능**이다. 19-0으로 바로 가기 전에는 Python / venv 실행 경로를 복구해 PyInstaller 53 tests collection을 실제로 재확인하는 것을 권장한다.
