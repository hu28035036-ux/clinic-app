# 20-2 그룹 B Codex 검증 요청서

## 1. 세션 이름

`20-2_group_b` — F-13 /api/health 신설 + F-12 modules/notes/service + F-14 calendar 회귀.

## 2. 작업 목표

20-P-1 마스터 플랜 §4-B 사용자 권장값 정합:
- F-13: `/api/health` 신설 — 6키 (db_ok / migration_version / backup_age / disk_free / version / uptime).
- F-12: `app/modules/notes/service.py` 신설 — Patient.memo / Appointment.memo 통합 read/write 헬퍼 (19-7 rules.py 보존).
- F-14: 19-3 view_models.py 보존 회귀 단언 — main.html JS 무수정 (사용자 권장 (b)).

## 3. 변경 파일 목록

### 신규 (4개)

```
app/modules/health/service.py        (110줄, F-13 snapshot)
app/modules/health/router.py         (23줄, F-13 endpoint)
app/modules/notes/service.py         (117줄, F-12 헬퍼)
tests/test_20_2_group_b.py           (244줄, 24 cases)
```

### 수정 (5개)

```
app/modules/health/__init__.py       (+14/-7, 19-2 facade 보존 + 20-2 export)
app/modules/notes/__init__.py        (+6/-1, service 명시)
app/main.py                          (+5/-3, health_router include + set_startup_time)
dosu_clinic.spec                     (+7, hidden_imports 3)
tests/test_pyinstaller_hidden_imports.py (+4, EXPECTED_19_X_MODULES_MODULES)
```

### 삭제

없음.

## 4. 수정 가능 범위

- `app/modules/health/{service,router}.py` 신규.
- `app/modules/health/__init__.py` 19-2 facade 보존 + 20-2 추가.
- `app/modules/notes/service.py` 신규 (19-7 rules.py 보존).
- `app/main.py` health_router include + set_startup_time 호출.
- `dosu_clinic.spec` hidden_imports 3개 추가.
- `tests/test_pyinstaller_hidden_imports.py` 3개 추가.
- `tests/test_20_2_group_b.py` 신규.

## 5. 수정 금지였던 범위

- 기존 `/api/admin/status` / `/api/ai/status` / `/api/ai/health/public` endpoint 변경 ⊥.
- 기존 `app/modules/health/__init__.py` 19-2 facade re-export 보존.
- 기존 `app/modules/notes/rules.py` (19-7) 변경 ⊥.
- 기존 `app/modules/calendar/view_models.py` (19-3) 변경 ⊥ — F-14 회귀 단언만.
- m001~m013 마이그레이션 변경 ⊥.
- main.html / FullCalendar JS 변경 ⊥.

## 6. 실제 변경 요약

- **F-13**: `app.modules.health.{service,router}`. service 의 6키 snapshot (db_ok = SQLAlchemy ping / migration_version = SCHEMA_VERSION / backup_age = backups/clinic_*.db mtime / disk_free = shutil.disk_usage / version = APP_VERSION / uptime = time.time() - _STARTUP_TIME). router 의 GET `/api/health` (인증 ⊥ public).
- **F-12**: `app.modules.notes.service`. `update_patient_memo` / `get_patient_memo` / `update_appointment_memo` / `get_appointment_memo` / `apply_cancel_memo_prefix` (rules.append_cancel_memo 활용) / `get_memo_by_kind` (NOTE_KIND_* enum 분기).
- **F-14**: 코드 신설 0. 19-3 view_models.py 의 helper 보존 단언 8 cases (UNASSIGNED 색 / status opacity / therapist_color / leave 라벨 / callable 함수).
- 신규 contract = `tests/test_20_2_group_b.py` 24 cases.

## 7. 실행한 테스트

```
venv\Scripts\python.exe -m ruff check app tests scripts
venv\Scripts\python.exe scripts/check_db_path.py
venv\Scripts\python.exe -m pytest tests/test_20_2_group_b.py -v
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q
venv\Scripts\python.exe -m pytest tests -q
```

## 8. 테스트 결과 요약

| 검증 | 결과 |
|---|---|
| ruff | All checks passed (3 autofix) |
| check_db_path | exit 0 |
| `test_20_2_group_b.py` | **24 passed** in 0.17s |
| `test_pyinstaller_hidden_imports.py` | **211 passed** (신설 3 모듈 × 2 = +6) |
| `pytest tests -q` 전체 | **1726 passed / 1 skipped / 10 xfailed** in 14.03s |

20-1 baseline 1696 → 20-2 baseline **1726** (+30, 회귀 0).

## 9. 수정 루프 횟수

1회차 (코드 작성 + ruff autofix + pytest 단위) → 24 passed.
2회차 (PyInstaller) → 211 passed.
3회차 (전체 회귀) → 1726 passed.

5회 루프 안에 통과.

## 10. 실제 기능 작동확인 수행 여부 (19-C §3 ~ §17 영향 범위 기준)

- 19-C §14 K Health: F-13 `/api/health` TestClient 호출 + 6키 응답 단언.
- 19-C §7 D 환자·메모: F-12 service 의 read/write 헬퍼 회귀.
- 19-C §9 F 캘린더: F-14 view-model helper 보존 회귀.

## 11. 자동 테스트로 확인한 항목

- F-13 health snapshot 단위 7 + endpoint 2 = 9 cases.
- F-12 notes service 5 cases.
- F-14 calendar view-model 회귀 8 cases.
- 보안 회귀 2 cases.
- PyInstaller 신설 3 모듈 등록 + import 가능 6 cases.

## 12. 테스트 클라이언트 / API 호출로 확인한 항목

- F-13 GET /api/health → 200 + 6키 응답 dict 정합 + PII / API key / password / phone 부재 단언.

## 13. 수동 확인 필요 항목

- 운영 환경에서 `/api/health` 가 외부 모니터링에 통합되는 시점 — 후속 결정.
- F-12 service 가 기존 api.py 호출지에서 점진 위임되는 시점 — 후속 세션.

## 14. 이번 세션 영향 없음으로 판단한 항목

- 19-C §4 A 예약 / B 휴무 / C 치료항목·완료체크 / G SMS / H 통계: 영향 0.
- DB schema (m001~m013): 변경 0.
- main.html / FullCalendar JS: 변경 0.

## 15. 확인하지 못한 항목과 이유

- PyInstaller 실제 빌드 + exe smoke — Codex 빌드 검증으로 미룸.
- 운영 환경 backup_age / disk_free 실제 값 정합성 — 운영 DB 접근 ⊥.

## 16. 운영 DB 접근 여부

**없음.** check_db_path exit 0 + 4단계 격리.

## 17. 외부 API 호출 여부

**없음.** F-13 health = 로컬 (DB ping / 파일시스템 / config) 만. 외부 모니터링 호출 없음.

## 18. 실제 문자 발송 여부

**없음.** sms 모듈 무영향.

## 19. 개인정보 / API key 원문 노출 여부

**없음.** `/api/health` 응답 6키만 — API key / password / PII / phone 부재 단언 통과 (`test_get_health_no_pii_in_response` / `test_health_response_no_api_key_substring`).

## 20. 기존 API 응답 key 유지 여부

**유지.** 본 20-2 = 신설 1개 endpoint (`/api/health`) + 기존 endpoint 변경 0. 33+ 응답 key 셋 보존.

## 21. 기능 작동확인 누락 여부

- 자동 테스트 + TestClient 호출 + 함수 단위 모두 완료.
- UI 수동 확인 = main.html JS 무수정이라 영향 0 (F-14 회귀 단언으로 검증).

## 22. 다음 세션 진행 가능 여부

**yes** — Codex 검증 통과 시. caveat 후보:
- F-13 외부 모니터링 통합 시점 — 후속 세션.
- F-12 service 점진 위임 시점 (기존 api.py:update_patient_memo 호출지) — 후속 세션.
- 그룹 C/D 진입 전 상세 기획 (Codex 20-P-1 caveat 정합) — 20-P-2 / 20-P-3.

## 23. Codex 가 직접 검증할 명령

```bash
# 코드 변경 범위 확인
git diff --stat HEAD~0 -- app/modules/health app/modules/notes app/main.py dosu_clinic.spec tests/test_pyinstaller_hidden_imports.py tests/test_20_2_group_b.py

# F-13 health endpoint 확인
grep -nE "collect_health_snapshot|HEALTH_SNAPSHOT_KEYS|GET.*health" app/modules/health/

# F-12 notes service 확인
grep -nE "update_patient_memo|update_appointment_memo|get_memo_by_kind" app/modules/notes/service.py

# F-14 calendar view_models 보존 (19-3 회귀)
grep -nE "UNASSIGNED_THERAPIST_COLOR|status_to_opacity|therapist_color" app/modules/calendar/view_models.py

# 자체 회귀 baseline
venv\Scripts\python.exe -m pytest tests -q   # 1726/1/10 예상
venv\Scripts\python.exe -m pytest tests/test_20_2_group_b.py -v   # 24 passed
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py -q   # 211 passed

# /api/health endpoint 직접 확인
curl http://localhost:8000/api/health   # 6키 JSON 응답 (서버 기동 시)

# DB / 외부 API 보호
venv\Scripts\python.exe scripts/check_db_path.py   # exit 0
```

## 24. Codex 검증 결과 기록 위치

- [reports/refactor/20-2_codex_review.md](20-2_codex_review.md) (영구 보존본)
- [reports/refactor/latest_codex_review.md](latest_codex_review.md) (덮어쓰기)

## 25. 사용자가 Codex 에게 전달할 최소 문구

> "reports/refactor/latest_codex_review_request.md 20-2 그룹 B 검증 시작해줘. Claude Code 요약만 믿지 말고 신설 4개 파일 (`app/modules/health/{service,router}.py`, `app/modules/notes/service.py`, `tests/test_20_2_group_b.py`) + 수정 5개 파일 (`health/__init__.py`, `notes/__init__.py`, `main.py`, `dosu_clinic.spec`, `test_pyinstaller_hidden_imports.py`) 을 직접 비교해서 검증해줘. 검증 결과는 reports/refactor/latest_codex_review.md 와 reports/refactor/20-2_codex_review.md 에 남겨줘."
