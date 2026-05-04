# 19-12 admin / backup / audit / export_import 경계 정리 — 테스트 결과

## 세션 이름

`19-12_admin_backup_audit_export_import_boundary` — 관리자 / 백업 / 감사 로그 /
export_import 후보 helper (schemas / service) 분리. 라우터 본체 *완전 무수정*.

## 실행 명령

```
venv\Scripts\python.exe -m pytest tests -q
venv\Scripts\python.exe -m pytest tests/test_19_12_admin.py -v
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -v
venv\Scripts\python.exe -m pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q
venv\Scripts\python.exe -m pytest tests/test_admin_auth_required.py tests/test_admin_ui_smoke.py tests/test_db_restore_safety.py -q
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
```

## 환경

- OS: Windows 11
- Python: venv\Scripts\python.exe (한글 경로 venv)
- pytest: 8.4.2
- ruff: venv\Scripts\ruff.exe
- 시각: 2026-05-04

## 실행 결과 요약

| 검증 | 결과 |
|---|---|
| `tests -q` (전체) | **1487 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `tests/test_19_12_admin.py -v` (신규) | **128 passed** |
| `tests/test_pyinstaller_hidden_imports.py -v` | **179 passed** |
| `tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | **144 passed, 1351 deselected, 21 warnings** |
| `tests/test_admin_auth_required.py` | **21 passed** |
| `tests/test_admin_ui_smoke.py` | **14 passed** |
| `tests/test_db_restore_safety.py` | **6 passed** |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | **exit 0** (운영 DB 단독 안내만 INFO 레벨) |

19-11 baseline (1335 passed) → 19-12 (1487 passed). **152 케이스 증가**:

- `tests/test_19_12_admin.py` — 128 cases (admin/backup/audit/export_import contract)
- `tests/test_pyinstaller_hidden_imports.py` — 24 cases (12 신규 모듈 × 2 — spec 등록 + 실제 import)

## 자동 수정 루프

| 회차 | 가설 | 변경 | 결과 |
|---|---|---|---|
| 1 | 신규 contract test 작성 후 실행 | 4 모듈 × `__init__/schemas/service` + spec 등록 + hidden imports test 등록 + contract test | 2 fail (audit/service docstring 의 `db.add(` 토큰, audit_call 정규식이 inner `)` 까지 매칭) |
| 2 | docstring 토큰 + 정규식 두 건 수정 | `audit/service.py` 의 docstring 문구 변경 + 정규식 → 괄호 균형 카운트 | 128 / 128 통과 |
| 3 | ruff 자동 보정 | 미사용 `inspect` import 제거 + import block 정렬 | All checks passed |

**총 2회차 코드 수정** — 5회 한도 내. 5회 실패 미해당.

## 실패 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB (`%APPDATA%\도수치료예약\clinic.db`) 직접 open 부재.
- 외부 API 호출 부재 (urllib/requests/httpx import 부재 단위 테스트).
- DB schema / migration 무수정.
- 라우터 본체 무수정 (라우터 시그니처 검증 6 케이스 통과).

## 기존 회귀 보호

| 영역 | 결과 |
|---|---|
| 관리자 인증 / 5회 잠금 / 세션 (`test_admin_auth_required.py`) | 21/21 통과 |
| 관리자 UI smoke (`test_admin_ui_smoke.py`) | 14/14 통과 |
| 백업 / 복구 안전성 (`test_db_restore_safety.py`) | 6/6 통과 |
| AI SMS validate / sms draft | 통과 |
| AI manual QA / RAG / Safety | 통과 |
| AI action_leave (휴무 AI) | 통과 |
| API contract (manual/search 3키 + manual/ask 9키 + sources 3키 + health 9키) | 통과 |

## 확인된 환경 잔여물 / 비-issue

- `tests/test_ai_sms_validate.py` 의 27 warnings (`PytestReturnNotNoneWarning`) —
  19-12 변경과 무관. 19-11 baseline 에서도 동일.
- `docs/ai/` untracked — 19-12 변경 범위 밖 (기존 계획 문서).
