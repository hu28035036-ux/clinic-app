# 19-P-8 Codex 검증 결과

- 검증 대상: `reports/refactor/latest_codex_review_request.md` / `reports/refactor/19-P-8_codex_review_request.md` / `docs/refactor/19_refactor_decision_record.md`
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 판정: **pass with caveat**
- 다음 단계: **yes — 19-P-9 진입 가능**

## 1. 검증 방식

Claude Code 요약은 신뢰 근거로 사용하지 않고, 실제 파일 구조와 문서 본문을 직접 대조했다.

- `reports/refactor/19-P-8_codex_review_request.md` 와 `reports/refactor/latest_codex_review_request.md` 를 `Compare-Object` 로 비교: 차이 없음.
- `docs/refactor/19_refactor_decision_record.md` 의 섹션 / 표 / 결정 ID / 대안 / 재검토 기준을 직접 카운트.
- `docs/refactor/19_refactor_risk_register.md` 의 실제 `#### R-*` Risk ID heading 수를 직접 카운트.
- `app/routers/api.py`, `app/routers/ai.py`, `app/templates/main.html`, `app/static/css/app.css`, `tests/` 의 실제 파일 구조를 직접 대조.
- `git diff --stat bcd74a7 -- app tests app/migrations dosu_clinic.spec requirements.txt requirements-dev.txt app/templates app/static pyproject.toml` 로 코드 변경 범위를 확인.

## 2. 확인 결과

| 항목 | 결과 | 근거 |
|---|---:|---|
| 19-P-8 요청서와 latest 요청서 동일성 | pass | `Compare-Object` 결과 차이 없음 |
| §2 핵심 의사결정 | pass | `### 2-A` ~ `### 2-T` = 20개, `DEC-A` ~ `DEC-T` 결정 ID row = 20개 |
| 각 결정 10필드 | pass | §2-A ~ §2-T 모두 결정 ID / 내용 / 이유 / 대안 / 미선택 이유 / 효과 / 위험 / 관련 문서 / 테스트 / Codex 검증 포인트 포함 |
| §3 선택하지 않은 대안 | pass | `### 3-1` ~ `### 3-9` = 9개, 각 항목에 위험 및 후속 검토 가능성 포함 |
| §4 위험 등록 연결 | pass | 19-P-7 risk register 실제 `#### R-*` heading = 77개, §4 DEC-A ~ DEC-T 매핑 존재 |
| §5 테스트 전략 연결 | pass | DEC-C/D/G/H/I/J/K/L/M/N/O/P/R/T = 14개 매핑, 사용자 예시 6개 §5-1에 존재 |
| §6 주석 / 문서화 연결 | pass | §6-1 DEC-A ~ DEC-T = 20행, 6개 카테고리(COMPAT/SAFETY/NOTE/RISK/TODO/TEMP), §6-2 위치 row = 16개 |
| §7 재검토 기준 | pass | 트리거 1~10 = 10개, 사용자 6개 + 추가 4개 구조 명시 |
| §8 종합 및 19-P-9 | pass | 결정 20 / 대안 9 / Risk 77 / 테스트 14 / 주석 16 / 재검토 10 / 19-P-9 진입 권고 명시 |
| 지원 문서 존재 | pass | 19-P-1 ~ 19-P-7 refactor 문서, 18 release 문서, AI working/protocol 문서 모두 존재 |
| 실제 API 구조 | pass | `app/routers/api.py` endpoint decorator 86개, `app/routers/ai.py` endpoint decorator 13개 |
| 실제 테스트 구조 | pass | `tests/test_*.py` 40개, xfail marker 7개, skip marker 1개 |
| 코드 무수정 범위 | pass with caveat | diff stat은 기존 18-x dirty 변경과 동일한 5개 tracked 파일만 표시. 19-P-8 신규 코드 변경은 확인되지 않음 |

## 3. Caveats

1. `docs/refactor/19_refactor_decision_record.md` §0 line 17 과 요청서 line 20 은 19-P-7 r3 근거를 `latest_codex_review.md` 로 링크한다. 이 파일은 본 19-P-8 리뷰 작성으로 19-P-8 결과를 가리키게 되므로, 장기 추적성 기준으로는 `reports/refactor/19-P-7_codex_review.md` 영구 보존본 링크가 더 정확하다. 요청서에는 별도로 `19-P-7_codex_review.md` 영구 링크가 존재하므로 진행 차단 사유는 아니다.
2. `docs/refactor/19_refactor_decision_record.md` 는 `app/routers/api.py` 를 5127줄로 반복 표기하지만, 현재 작업 파일은 PowerShell `Get-Content` 기준 5128줄이다. endpoint 수 86개와 구조 판단에는 영향이 없는 1줄 drift 이지만, 19-P-9에서 체크리스트화할 때 숫자를 재측정하는 편이 좋다.
3. PyInstaller “53 tests” 표현은 이번 검증에서 pytest collect-only 로 독립 확인하지 못했다. 현재 `.venv` Python 런처가 존재하지 않는 Python 경로를 가리키고, `python` / `py -3` 도 실행 가능한 인터프리터를 제공하지 않았다. 정적 파일 구조상 hidden import 검증 파일과 parametrized 항목은 존재하지만, 실제 collection/test 실행은 미실시다.

## 4. G-1 ~ G-12 판정

| Gate | 판정 | 근거 |
|---|---|---|
| G-1 코드 무수정 | pass with caveat | 대상 코드 diff stat은 기존 dirty 변경과 동일. 19-P-8 문서 외 신규 코드 변경 증거 없음 |
| G-2 핵심 의사결정 20개 | pass | DEC-A ~ DEC-T 20개 |
| G-3 선택하지 않은 대안 9개 | pass | §3-1 ~ §3-9 |
| G-4 위험 등록 매핑 | pass | risk register 실제 Risk ID 77개, §4 매핑 및 §4-1 예시 존재 |
| G-5 테스트 전략 매핑 | pass | §5 14개 결정 매핑 + §5-1 예시 6개 |
| G-6 주석 매트릭스 | pass | §6-1 20 × 6, §6-2 위치 16개 |
| G-7 재검토 기준 10개 | pass | §7 트리거 10개 |
| G-8 19-P-1 ~ 19-P-7 충돌 없음 | pass with caveat | 주요 결정은 정합. 단, 19-P-7 결과 링크는 `latest` 대신 영구 링크 권장 |
| G-9 appointments 마지막 분리 | pass | DEC-F + 19-P-2/3/4/6/7 근거 연결 |
| G-10 절대 원칙 명확 | pass | DEC-C/D/N/T 에 응답 키 / DB / local-first / Codex 게이트 명시 |
| G-11 부재 항목 단정 금지 | pass | doctors / EMR / no-show / 반복예약 / resources / notifications / `/api/health` 후속 검토 분류 |
| G-12 주석 매트릭스 정합 | pass | §6-1 + §6-2 정합, 코드 주석 작성은 하지 않음 |

## 5. 최종 판단

**pass with caveat**. 19-P-8 의사결정 기록은 19-P-1 ~ 19-P-7 준비 문서와 실제 파일 구조를 기준으로 큰 충돌 없이 작성되어 있으며, 19-P-9 공통 체크리스트 문서로 넘어가도 된다.

다만 19-P-9 작성 전 또는 작성 중에 다음 보정이 권장된다.

- 19-P-7 r3 결과 링크는 `latest_codex_review.md` 가 아니라 `19-P-7_codex_review.md` 로 고정.
- `api.py` line count는 현재 파일 기준으로 재측정.
- PyInstaller “53 tests” 표현은 실제 pytest collection 또는 기존 테스트 리포트 기준으로 정확히 재확인.
