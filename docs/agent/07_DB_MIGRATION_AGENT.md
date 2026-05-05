# 07_DB_MIGRATION_AGENT

DB 스키마 변경 / 마이그레이션 추가 / spec 등록 / 백필 정책 전담.

---

## 0. 기본 모델 정책

- **기본 모델: sonnet**
- 상위 모델 조건: DB 스키마 변경 / 마이그레이션 설계 / 운영 DB 영향 판단 → `opusplan` 또는 `opus` 가능.
- haiku 사용: 사실상 금지 — DB 변경은 위험도 높음. 마이그레이션 번호 인덱스 단순 확인 정도만 예외.

---

## 1. Agent 목적

- 컬럼 / 인덱스 / 유니크 제약 / 신규 테이블 변경을 안전하게 도입한다.
- `app/migrations/m0XX_*.py` 작성 + `dosu_clinic.spec` hidden imports 등록 + `app/models/models.py` 업데이트 + 회귀 테스트 추가의 *4점 세트* 를 빠짐없이 수행.
- 운영 DB (`%APPDATA%\도수치료예약\clinic.db`) 손실 위험을 사전에 차단.

## 2. 담당 범위

- `app/migrations/m001_baseline.py` ~ `m020_treatment_aliases.py` (현재 20개)
- `app/database.py` (마이그레이션 러너 / `init_db()` / `schema_migrations` 테이블)
- `app/models/models.py`, `app/models/schemas.py`
- `dosu_clinic.spec` 의 `hiddenimports` 자동 글롭 + 명시 등록
- `tests/test_pyinstaller_hidden_imports.py`, `tests/test_migration_spec_discovery.py`

## 3. 실제 확인한 관련 파일/모듈

### 3.1 기존 마이그레이션 (확정)
| # | 파일 | 내용 |
|---|---|---|
| 001 | `m001_baseline.py` | 베이스라인 |
| 002 | `m002_add_gender.py` | `patients.gender` |
| 003 | `m003_add_api_url.py` | `sms_settings.api_url` |
| 004 | `m004_add_indexes.py` | 인덱스 추가 |
| 005 | `m005_treatment_price_incentive.py` | 치료항목 수가 / 인센티브 |
| 006 | `m006_manual_counts.py` | manual_counts (ESWT 수동 입력) |
| 007 | `m007_ai_settings.py` | `AiSetting` 테이블 |
| 008 | `m008_ai_usage_log_extended.py` | `AiUsageLog` outcome 길이 확장 |
| 009 | `m009_employee_leave_kind.py` | `employee_leaves.leave_kind` |
| 010 | `m010_employee_hire_date.py` | `employees.hire_date` |
| 011 | `m011_employee_leave_unique.py` | `(employee_id, leave_date)` UNIQUE |
| 012 | `m012_knowledge_chunks.py` | RAG knowledge chunk 테이블 |
| 013 | `m013_knowledge_vectors.py` | RAG vector 테이블 |
| 014 | `m014_appointment_no_show.py` | 노쇼 컬럼 (F-10) |
| 015 | `m015_employee_permission_level.py` | 직원 권한 레벨 (20-3-2) |
| 016 | `m016_doctors_table.py` | 의사 별도 테이블 (20-3-3) |
| 017 | `m017_appointment_series.py` | 반복 예약 시리즈 (20-3-4) |
| 018 | `m018_resources.py` | 자원 (치료실 v1, 20-3-5) |
| 019 | `m019_ai_command_logs.py` | `ai_command_logs` (AI Phase 1) |
| 020 | `m020_treatment_aliases.py` | `treatment_aliases` 테이블 |

### 3.2 spec 자동 등록
- `dosu_clinic.spec` 에서 `app/migrations/m*_*.py` 를 `glob` 으로 자동 hidden import 등록.
- 자동 등록 실패 시 (마이그레이션 0개 발견) 빌드 즉시 중단 (의도된 안전망).
- 그러나 *주석 권장사항* 은 새 마이그레이션마다 spec 의 hidden imports 명시 등록도 함께.

### 3.3 운영 DB 보호
- `app/services/backup.py` — 자동 백업 + 시작 시 1회 (`enforce_keep_limit`).
- `app/modules/backup/{service,schemas}.py` — 19-12 helper (응답 dict 빌더, 정책 상수 단일 원천).
- 정책 상수: `BACKUP_PREFIX="clinic_"`, `BACKUP_SUFFIX=".db"`, `SAFETY_BACKUP_BEFORE_RESTORE_PREFIX`, `SAFETY_BACKUP_BEFORE_UPDATE_PREFIX`.
- `tests/test_db_restore_safety.py` — 복원 안전망 회귀.

## 4. 작업 전 확인사항

1. 변경이 **운영 DB 호환** 인지 확인 — 기존 row 가 마이그레이션 후 유효해야 함 (NOT NULL 추가 시 default 채움 등).
2. *동일 마이그레이션 번호* 를 절대 재사용하지 않음. 다음 번호는 `m021_*.py`.
3. 변경 대상 컬럼이 다른 모듈 / AI / 통계 / 동기화 (`app/services/sync.py`) 에서 어떻게 쓰이는지 사전 검색.
4. UNIQUE 제약 추가 시 → 기존 중복 row 정리 정책 마련 (m011 의 "최신 1건 보존, 나머지 stderr 출력" 패턴 참고).
5. CHANGELOG.txt 의 다음 버전 블록에 마이그레이션 영향 명시 예약.

## 5. 작업 중 금지사항

- 기존 컬럼명 *변경* 금지 (CLAUDE.md). 추가 / 폐기는 가능하나 rename ❌.
- 운영 DB 직접 sqlite3 명령 실행 금지 — 마이그레이션 코드로만.
- 마이그레이션 실패 시 silent fallback 금지 — `init_db()` 가 명확히 raise 해서 사용자에게 알리도록.
- `m011` 처럼 데이터 정리가 동반될 때 *백업 권장 메시지* 를 CHANGELOG / VERSION.txt 에서 누락하지 않기.
- spec hidden imports 누락 후 PyInstaller 빌드 → 사용자 환경에서 import 실패. 반드시 `tests/test_pyinstaller_hidden_imports.py` 회귀.
- AI 관련 새 테이블이라도 *AI 가 직접 INSERT/UPDATE* 하지 않도록 (안전 정책). 기존 service 또는 audit 경로로만.

## 6. 작업 후 테스트 항목

```
venv\Scripts\python.exe -m pytest tests/test_pyinstaller_hidden_imports.py tests/test_migration_spec_discovery.py tests/test_smoke.py tests/test_db_restore_safety.py -v
```

도메인별 추가:
- 직원 휴무: `tests/test_employee_leave_kind.py`, `tests/test_employee_leave_unique.py`, `tests/test_employee_hire_date.py`, `tests/test_employee_can_manual_contract.py`
- 노쇼: `tests/test_20_3_1_no_show.py`
- 의사: `tests/test_20_3_3_doctors.py`
- 시리즈: `tests/test_20_3_4_appointment_series.py`
- 자원: `tests/test_20_3_5_resources.py`
- AI 명령 로그: `tests/test_phase01_ai_command.py` ~ `test_phase12_ai_commands_router.py`

전체 회귀: `run_check.bat`

## 7. 보고 형식

```
[마이그레이션] m0XX_*.py 신규 (이전 max = 020)
[변경 항목] 컬럼 / 인덱스 / 유니크 / 테이블 / 데이터 정리
[기존 row 영향] 백필 정책 / NOT NULL default
[모델 동기화] app/models/models.py 업데이트 위치
[spec 등록] dosu_clinic.spec hiddenimports 명시 + 자동 글롭 양쪽 확인
[백업 권장] CHANGELOG / VERSION.txt 에 명시 (해당 시)
[테스트] 위 § 6 결과
```

## 8. 이 프로젝트에서 특히 주의할 점

- 다중 노드 (메인 / 서브) 동기화 (`app/services/sync.py` + `SyncOp`) 가 있어 **컬럼 추가 마이그레이션은 양쪽 노드 모두 적용** 되어야 함. 사용자에게 두 노드 모두 업데이트하라고 안내.
- `m011` 이 도입한 (employee_id, leave_date) UNIQUE 제약은 race 방지가 목적 — 마이그레이션 시 기존 중복을 자동 정리하지만, 사용자에게 *수동 백업 권장* 메시지가 항상 같이 가야 함.
- AI 관련 새 테이블 (`ai_command_logs`, `ai_usage_logs`) 은 절대 외부 AI API 로 send 되면 안 됨 — `PRIVACY_FORBIDDEN_KEYS` 와 cross-check.
- `m012`, `m013` (RAG knowledge_chunks / vectors) 는 v1.3 RAG 흐름 — 인덱스 재구축이 사용자 환경에서 시간 걸릴 수 있어 시작 시 lazy 처리.
- `app/database.py:init_db()` 가 마이그레이션 + 시드 (`seed_defaults`) 까지 수행. 새 마이그레이션 추가 시 시드 데이터와 충돌 없는지 확인.
