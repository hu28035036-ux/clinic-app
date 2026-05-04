# 20-2 그룹 B 변경 요약

## 변경 파일 목록

### 신규 (4개)

| 파일 | 줄 수 | 내용 |
|---|---:|---|
| `app/modules/health/service.py` | 110 | F-13 health snapshot — 6키 + DB ping / 백업 / 디스크 / uptime |
| `app/modules/health/router.py` | 23 | F-13 GET /api/health endpoint |
| `app/modules/notes/service.py` | 117 | F-12 Patient.memo / Appointment.memo read/write 헬퍼 |
| `tests/test_20_2_group_b.py` | 244 | 24 cases (F-13 9 + F-12 5 + F-14 8 + 보안 2) |

### 수정 (4개)

| 파일 | diff | 의도 |
|---|---:|---|
| `app/modules/health/__init__.py` | +14 / -7 | 19-2 facade 보존 + 20-2 router/service re-export 추가 |
| `app/modules/notes/__init__.py` | +6 / -1 | 20-2 service.py 추가 명시 |
| `app/main.py` | +5 / -3 | health_router include + set_startup_time 호출 |
| `dosu_clinic.spec` | +7 | hidden_imports 3개 (health.service / health.router / notes.service) |
| `tests/test_pyinstaller_hidden_imports.py` | +4 | EXPECTED_19_X_MODULES_MODULES 3개 추가 |

### 삭제

없음.

## 파일별 변경 의도

### F-13 /api/health 신설 (post-19-P)

- `app/modules/health/service.py` 신설 — `collect_health_snapshot` 6키 (db_ok / migration_version / backup_age / disk_free / version / uptime).
- `app/modules/health/router.py` 신설 — `GET /api/health` public endpoint (인증 ⊥).
- `app/main.py` 에 `app.include_router(health_router)` + `set_startup_time()` 추가.
- 사용자 §4-B 권장값 정합: 6개 키 모두 포함.

### F-12 modules/notes/service.py 신설

- 19-7 의 `notes/rules.py` (분류 / PII 마스킹) 위에 read/write 헬퍼 추가.
- `update_patient_memo` / `get_patient_memo` / `update_appointment_memo` / `get_appointment_memo` / `apply_cancel_memo_prefix` / `get_memo_by_kind`.
- 사용자 §4-B 권장값 (a) 정합 — 통합 모듈 신설.
- 기존 `api.py:update_patient_memo` (PATCH /api/patients/{pid}/memo) 동작 보존 — 본 service 는 *별도 헬퍼* 진입점.

### F-14 calendar 회귀 단언

- 코드 신설 0 — 19-3 에서 이미 `app/modules/calendar/view_models.py` 신설 완료.
- 본 20-2 에서는 *helper 보존* 회귀 단언 8 cases 추가 (UNASSIGNED 색 / status opacity / therapist_color / leave 라벨 / callable).
- 사용자 §4-B 권장값 (b) 정합 — main.html JS 무수정.

### PyInstaller spec / test 갱신

- 신설 3 모듈 (`app.modules.health.service` / `.router` / `app.modules.notes.service`) 등록.
- `EXPECTED_19_X_MODULES_MODULES` 에 3개 추가 — parametrized 테스트 자동 생성 (3 × 2 = 6 cases).

## 호환성 보존

- 20-1 baseline 1696 cases 회귀 0.
- 응답 dict / API URL / DB schema / UI: 변경 0 (F-13 만 신설 endpoint, 기존 `/api/admin/status` / `/api/ai/status` / `/api/ai/health/public` 보존).
- 33+ 응답 key 셋: 보존.
- main.html / FullCalendar JS: 무수정.

## 주석 카테고리 적용

- `# NOTE:` — health/service.py 사용자 §4-B 결정값 / notes/service.py 통합 헬퍼 명시
- `# SAFETY:` — health endpoint 인증 ⊥ public + API key/PII 비포함 / notes service 평문 메모 read/write (마스킹은 rules.py 별도)
- `# COMPAT:` — notes service.py 가 기존 api.py:update_patient_memo 와 byte-equivalent

## 5회 루프 횟수

- **1회차** — 코드 작성 + ruff (3 fix 자동 적용 — unused import / import order) + pytest 단위 → 24 passed
- **2회차** — PyInstaller hidden imports → 211 passed
- **3회차** — 전체 회귀 → 1726 passed (회귀 0)

총 1회차 작성 + 2회차 검증으로 5회 루프 안에 통과.
