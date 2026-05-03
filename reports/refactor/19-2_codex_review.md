# 19-2 Codex 검증 결과

- 검증 대상: `reports/refactor/latest_codex_review_request.md` / `reports/refactor/19-2_codex_review_request.md` / `reports/refactor/19-2_test_report.md` / `reports/refactor/19-2_fix_summary.md` / `app/modules/*`
- 검증일: 2026-05-03
- 기준 브랜치: `ai-rag-v1-integration`
- 판정: **pass with caveat**
- 다음 단계: **yes — 19-3 calendar / schedule_view 표시용 view-model 분리 검토 진입 가능**

## 1. 검증 방식

Claude Code 요약은 신뢰 근거로 사용하지 않고, 실제 파일 구조와 문서 본문을 직접 대조했다.

- `reports/refactor/19-2_codex_review_request.md` 와 `reports/refactor/latest_codex_review_request.md` 를 비교했다. 결과는 동일했다.
- `reports/refactor/19-2_test_report.md` 와 `latest_test_report.md`, `19-2_fix_summary.md` 와 `latest_fix_summary.md` 를 비교했다. 결과는 동일했다.
- `app/modules` 신규 파일, `app/core/feature_flags.py`, `app/core/responses.py`, `dosu_clinic.spec`, `tests/test_pyinstaller_hidden_imports.py`, `tests/test_19_2_settings_health_boundary.py` 를 실제 파일 기준으로 확인했다.
- 전체 테스트, ruff, DB 경로 체크, PyInstaller hidden imports 테스트를 현재 환경에서 직접 재실행했다.
- PyInstaller spec/test의 `app.modules*` 등록 여부와 `app.core`/`app.modules` 의존 방향을 실제 문자열 기준으로 확인했다.

## 2. 명령 재실행 결과

| 명령 | 실제 결과 | 판정 |
|---|---|---:|
| `venv/Scripts/python.exe -m pytest tests -q` | **585 passed, 1 skipped, 7 xfailed, 27 warnings** (10.95초) | pass |
| `venv/Scripts/python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q` | **77 passed** (0.35초) | pass |
| `venv/Scripts/python.exe -m ruff check app tests scripts` | **All checks passed!** | pass |
| `venv/Scripts/python.exe scripts/check_db_path.py` | exit 0, 운영 DB 경로 감지 메시지 출력 | pass |

단일 `tests/test_19_2_settings_health_boundary.py -q` 실행은 이 환경의 venv 런처 문제로 실패했지만, 전체 테스트 실행 안에서 해당 파일 32개가 모두 통과했다.

## 3. 구조 대조

| 항목 | 실제 확인 | 판정 |
|---|---:|---:|
| 신규 `app/modules/*.py` 본체 파일 | 4개 | pass |
| `app.modules*` spec hiddenimports 등록 | 4/4 | pass |
| `app.modules*` PyInstaller 테스트 등록 | 4/4 | pass |
| `app.modules.health` re-export | `app.services.ai.health` 참조 확인 | pass |
| `HEALTH_PUBLIC_KEYS` | `enabled / ready / provider / api_key_set` | pass |
| `app.core` → `app.modules` import | 0건 | pass |
| `modules.settings.serializers` ORM/DB 직접 의존 | 테스트로 검증됨 | pass |

## 4. 실제 라인/변경량

| 파일 | 요청서 주장 | 실제 확인 | 판정 |
|---|---:|---:|---:|
| `app/modules/__init__.py` | 14 lines | 14 | pass |
| `app/modules/settings/__init__.py` | 27 lines | 22 | caveat |
| `app/modules/settings/serializers.py` | 183 lines | 196 | caveat |
| `app/modules/health/__init__.py` | 57 lines | 74 | caveat |
| `tests/test_19_2_settings_health_boundary.py` | 351 lines | 487 | caveat |
| `app/core/feature_flags.py` diff | +114 lines | +134 / -7, stat +141 display | caveat |
| `app/core/responses.py` diff | -1 / +9 | +9 / -5, stat 14 changed | caveat |
| `dosu_clinic.spec` diff | +5 lines | +6 | caveat |
| `tests/test_pyinstaller_hidden_imports.py` diff | +22 lines | +32 | caveat |

위 caveat는 문서 수치와 diff 표기 문제다. 실제 테스트와 구조 검증은 통과했다.

## 5. 게이트 결과

| 게이트 | 결과 | 근거 |
|---|---:|---|
| 본체 이동 0 | pass | 라우터/서비스 주요 본체 무수정, 신규 facade/helper 중심 |
| API 응답 키 보존 | pass | 라우터 무수정 + health/status 관련 테스트 통과 |
| API key 원문 비노출 | pass | serializer/mask 테스트 포함 전체 테스트 통과 |
| 운영 DB 보호 | pass | `check_db_path.py` exit 0 + 전체 테스트 통과 |
| 외부 API 호출 0 | pass | local_only/provider 관련 테스트 포함 전체 테스트 통과 |
| 단방향 경계 D-4 | pass | core → modules import 0, contract 통과 |
| PyInstaller 안전성 | pass | 77 passed |
| 19-1 baseline 회귀 0 | pass | 545 + 신규 40 = 585 passed |
| 5회 루프 | pass with caveat | 최종 결과는 1회차 통과로 기록. 단, report 자체에 ruff I001 자동 fix 1건이 있었다고 적혀 있음 |

## 6. 남은 Caveats

1. 요청서와 fix/test report의 line count 및 diff stat 일부가 실제 파일과 맞지 않는다. 특히 `tests/test_19_2_settings_health_boundary.py` 는 실제 487 lines로, 요청서의 351 lines와 차이가 크다.
2. `reports/refactor/19-2_test_report.md` §3의 신규 테스트 산술 설명은 중간 계산이 혼재되어 있다. 실제 기준으로는 전체 테스트 593 collected 중 `585 passed + 1 skipped + 7 xfailed`, 19-1 대비 passed +40, PyInstaller 19-2 추가 8, contract 파일 32로 정리하는 것이 명확하다.
3. 단일 contract 테스트 명령은 이 환경에서 venv launcher 프로세스 생성 오류가 났다. 전체 테스트에서는 해당 파일이 실행되어 통과했으므로 기능 실패는 아니다.
4. `app/modules/**/__pycache__` 가 생성되어 있다. 소스 검증 대상은 아니지만 커밋 전 제외/정리가 필요하다.
5. 현재 변경은 modified/untracked 상태다. 19-3 진입 전 커밋/유지 방침을 확정하는 것이 좋다.

## 7. 종합 판정

19-2의 핵심 목표인 settings/health facade 신설, feature flag pure-input helper 보강, health public response key 보정, PyInstaller modules 등록, API/DB/외부 호출 회귀 보호는 실제 파일과 재실행 테스트로 확인됐다.

따라서 판정은 **pass with caveat** 이다. caveat는 문서 수치와 단일 명령 재현성, `__pycache__` 정리 문제이며, 19-3 진입을 차단하지 않는다.

다음 단계는 **yes — 19-3 calendar / schedule_view 표시용 view-model 분리 검토 진입 가능** 이다.
