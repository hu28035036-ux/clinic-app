# 19-12 admin / backup / audit / export_import 분리 — 변경 요약

## 세션 이름

`19-12_admin_backup_audit_export_import_boundary` — 관리자 / 백업 / 감사 로그 /
export_import 후보 helper (schemas / service) 분리. 라우터 본체 *완전 무수정*.
**API key / 문자나라 계정 / sync_secret / admin_password_hash / 개인정보 원문
비노출** + **운영 DB 보호 (engine.dispose + atomic rename) 정책 가드** 명시.

## 작업 목표 (한 문장)

`api.py` / `ai.py` / `services/backup.py` 의 관리자 (4 핸들러) + about (5 핸들러) +
config (4 핸들러) + system-settings (2 핸들러) + 백업/복구 (8 핸들러) + audit-logs
(1 핸들러) + data-convert (2 핸들러) 응답 dict / 마스킹 정책 / 파일명 규약 / detail
500자 cap / 비밀 값 제거 정책을 `app/modules/{admin,backup,audit,export_import}/`
후보 구조에 byte-equivalent 로 분리. **API key 등록 여부만 노출 + 문자나라 계정
원문 비노출 + 개인정보 원문 audit/log/응답 비노출 + 운영 DB 보호 정책 보존**.
*라우터 본체 / 응답 key 완전 무수정*.

## 변경 파일 목록

| 파일 | 변경 종류 | 줄 수 |
|---|---|---:|
| `app/modules/admin/__init__.py` | 신규 | 58 |
| `app/modules/admin/schemas.py` | 신규 | 175 |
| `app/modules/admin/service.py` | 신규 | 230 |
| `app/modules/backup/__init__.py` | 신규 | 64 |
| `app/modules/backup/schemas.py` | 신규 | 142 |
| `app/modules/backup/service.py` | 신규 | 180 |
| `app/modules/audit/__init__.py` | 신규 | 52 |
| `app/modules/audit/schemas.py` | 신규 | 76 |
| `app/modules/audit/service.py` | 신규 | 101 |
| `app/modules/export_import/__init__.py` | 신규 | 63 |
| `app/modules/export_import/schemas.py` | 신규 | 128 |
| `app/modules/export_import/service.py` | 신규 | 129 |
| `tests/test_19_12_admin.py` | 신규 (128 cases) | 869 |
| `dosu_clinic.spec` | 수정 (+17) | — |
| `tests/test_pyinstaller_hidden_imports.py` | 수정 (+13) | — |

(라우터 본체 / 서비스 본체 / 모델 / 마이그레이션 무수정.)

## 파일별 변경 요약

### `app/modules/admin/__init__.py` (신규, 58줄)

패키지 docstring — 본 세션 범위 / 범위 외 / COMPAT / SAFETY / RISK / NOTE.
- COMPAT: 17 관리자/about/config/system-settings/audit-logs 핸들러 무수정.
- SAFETY: 공개 config 응답 ⇒ admin_password_hash / sync_secret 부재 보장. AI api_key
  등록 여부 + 마스킹 (앞 4자 + ****) 만 노출. 문자나라 계정 / 비번 / API key 마스킹.
- RISK: 자동 업데이트 흐름 (PyInstaller 폴더 교체 + updater.bat) 변경 ⊥.
- RISK: 관리자 인증 정책 (PBKDF2 / 5회 잠금 / 세션 TTL 8시간) 변경 ⊥.

### `app/modules/admin/schemas.py` (신규, 175줄)

응답 키 contract 상수 (frozenset).
- `ADMIN_STATUS_RESPONSE_KEYS` (2키) / `ADMIN_LOGIN_RESPONSE_KEYS` (2키) /
  `ADMIN_LOGOUT_RESPONSE_KEYS` (1키) / `ADMIN_CHANGE_PW_RESPONSE_KEYS` (2키).
- `ABOUT_RESPONSE_KEYS` (8키) / `ABOUT_CHECK_UPDATE_BASE_KEYS` (2키) /
  `ABOUT_DOWNLOAD_UPDATE_RESPONSE_KEYS` (6키) / `ABOUT_APPLY_UPDATE_RESPONSE_KEYS` (4키) /
  `ABOUT_UPDATE_LOG_KEYS` (6키).
- `PUBLIC_CONFIG_DROP_KEYS` (admin_password_hash, sync_secret) — **비밀 key 정책 단일 원천**.
- `CONFIG_SYNC_SECRET_RESPONSE_KEYS` (1키) / `CONFIG_REGEN_SYNC_SECRET_RESPONSE_KEYS` (2키).
- `SYSTEM_SETTINGS_RESPONSE_KEYS` (6키) / `SYSTEM_SETTINGS_UPDATE_RESPONSE_KEYS` (1키).
- `AI_SETTINGS_RESPONSE_KEYS` (9키) / `AI_SETTINGS_FORBIDDEN_KEYS` (api_key — 평문 부재 가드).
- `ADMIN_ALL_CONTRACT_SETS` cross-check dict.

### `app/modules/admin/service.py` (신규, 230줄)

응답 dict 빌더 + 마스킹 / 비밀 값 제거 helper.
- `redact_public_config(cfg)` — admin_password_hash / sync_secret 제거 (단일 원천).
- `mask_api_key(key)` — `ai.py:_mask_api_key` byte-equivalent (앞 4자 + ****).
- `mask_munjanara_pw(pw)` — `api.py:sms_get` byte-equivalent (`****` / `""`).
- `mask_munjanara_key(key)` — `api.py:sms_get` byte-equivalent (앞 4자 + ****).
- `audit_detail_cap(detail)` (500자) — `api.py:audit` byte-equivalent.
- `build_admin_status_response` / `build_admin_login_response` /
  `build_admin_logout_response` / `build_admin_change_password_response` /
  `build_about_response` / `build_system_settings_response` /
  `serialize_ai_setting`.
- 후속 검토 표기 (about check/download/apply update 응답 빌더 — 19-13+).

### `app/modules/backup/__init__.py` (신규, 64줄)

패키지 docstring.
- COMPAT: services/backup.py + api.py 의 8 백업/복구 핸들러 무수정.
- SAFETY: 본 모듈은 메타데이터 직렬화 + 정책 상수만 — 운영 DB read/write ⊥.
- RISK: 복구 시 engine.dispose() 필수 (Windows DB 락 회피) — 정책 변경 ⊥.
- RISK: 복구 직전 안전망 백업 자동 생성 — 정책 변경 ⊥.
- RISK: 자동 업데이트 직전 SQLite online-backup — 정책 변경 ⊥.
- NOTE: 자동 백업 타이머 daemon=True / conftest 람다 교체 호환 — 무력화 가능성 변경 ⊥.

### `app/modules/backup/schemas.py` (신규, 142줄)

백업/복구 응답 키 contract + 파일명 정책 상수.
- `BACKUP_LIST_ROW_KEYS` (4키) / `BACKUP_NOW_OK_RESPONSE_KEYS` (3키) /
  `BACKUP_NOW_ERROR_RESPONSE_KEYS` (2키) / `BACKUP_RESTORE_OK_RESPONSE_KEYS` (3키) /
  `BACKUP_RESTORE_ERROR_RESPONSE_KEYS` (2키) / `BACKUP_DIR_RESPONSE_KEYS` (1키) /
  `RESTORE_OK_RESPONSE_KEYS` (2키) / `APPLY_UPDATE_BACKUP_OK_KEYS` (4키) /
  `APPLY_UPDATE_BACKUP_ERROR_KEYS` (2키).
- `BACKUP_PREFIX = "clinic_"` / `BACKUP_SUFFIX = ".db"` —
  services/backup.py 와 byte-equivalent.
- `SAFETY_BACKUP_BEFORE_RESTORE_PREFIX` / `SAFETY_BACKUP_BEFORE_UPDATE_PREFIX`.
- `AUTO_BACKUP_INTERVAL_MIN_FLOOR = 5` / `AUTO_BACKUP_INTERVAL_MIN_DEFAULT = 60` /
  `AUTO_BACKUP_KEEP_COUNT_DEFAULT = 30` (정책 단일 원천).

### `app/modules/backup/service.py` (신규, 180줄)

백업/복구 응답 dict 빌더 + 파일명 helper + 정규화 helper.
- `is_backup_filename(name)` / `make_backup_filename(ts)` /
  `make_before_restore_filename(ts)` / `make_before_update_filename(ver, ts)` —
  services/backup.py byte-equivalent.
- `build_backup_list_row` / `build_make_backup_ok_response` /
  `build_make_backup_error_response` / `build_restore_ok_response` /
  `build_restore_error_response` / `build_backup_dir_response` /
  `build_legacy_restore_ok_response`.
- `normalize_auto_backup_interval_min(v)` (max(5, v)) /
  `normalize_auto_backup_keep_count(v)` (max(1, v or 30)) —
  api.py:system_settings_set byte-equivalent.

### `app/modules/audit/__init__.py` (신규, 52줄)

패키지 docstring.
- COMPAT: audit() 시그니처 / list_audit_logs 응답 7키 무수정.
- SAFETY: AuditLog.detail = PII / API key / 비밀번호 원문 부재 보장 (호출지 책임).
- SAFETY: detail[:500] cap = 정책 단일 원천.
- SAFETY: actor = "system" / "admin" 만.
- NOTE: AI 전용 AiUsageLog 는 services/ai/ai_logging.py 단일 원천 (별도 모듈).
- TODO(후속 검토): AuditLog retention 정책 — 미구현, 19-x 검토.

### `app/modules/audit/schemas.py` (신규, 76줄)

audit 응답 키 + 정책 상수.
- `AUDIT_LOG_ROW_KEYS` (7키 — id/ts/node_id/actor/action/entity_id/detail).
- `AUDIT_DETAIL_CAP = 500` (PII / payload 폭주 방지 정책 단일 원천).
- `AUDIT_DEFAULT_ACTOR = "system"` / `AUDIT_KNOWN_ACTORS` (system, admin).
- `AUDIT_KNOWN_ACTION_PREFIXES` (admin./appointment./patient./treatment./...).

### `app/modules/audit/service.py` (신규, 101줄)

audit 직렬화 + 정규화 helper.
- `cap_detail(detail)` (500자) — api.py:audit byte-equivalent.
- `serialize_audit_log_row(row)` — list_audit_logs 인라인 dict byte-equivalent.
- `serialize_audit_log_rows(rows)` — 리스트 변형.
- `normalize_actor(actor)` / `normalize_action(action)` / `normalize_entity_id(eid)`.

### `app/modules/export_import/__init__.py` (신규, 63줄)

패키지 docstring.
- COMPAT: api.py:data_convert_preview / data_convert_apply 응답 12 + 5 키 무수정.
- COMPAT: api.py 의 `_dc_*` 헬퍼 12개 (~600줄) + Excel export 2개 (~800줄) 무수정.
- SAFETY: 환자 PII 평문 = 응답에 포함 (환자탭 모달이 사용) — 정책 변경 ⊥.
  audit / log 에는 카운트만.
- SAFETY: 본 19-12 모듈 = 응답 dict 빌더만 — openpyxl/csv 의존 ⊥.
- RISK: 파일 크기 cap (10MB) / BULK_CHUNK (2000) 정책 변경 ⊥.
- TODO(19-13+): _dc_* 헬퍼 + Excel export byte-equivalent 분리.
- TODO(후속 검토): 비트U차트 / EMR import / CSV export — 미구현.

### `app/modules/export_import/schemas.py` (신규, 128줄)

data-convert 응답 키 + 정책 상수.
- `DATA_CONVERT_PREVIEW_RESPONSE_KEYS` (11키).
- `DATA_CONVERT_APPLY_RESPONSE_KEYS` (5키).
- `DATA_CONVERT_PREVIEW_NEW_PATIENT_MIN_KEYS` (6키 — 최소 필드).
- `DATA_CONVERT_APPLY_INSERTED_PATIENT_KEYS` (8키).
- `DATA_CONVERT_FILE_SIZE_MAX = 10*1024*1024` /
  `DATA_CONVERT_BULK_CHUNK = 2000` /
  `DATA_CONVERT_HEADER_SCAN_ROWS = 10` /
  `PATIENT_DUPE_PHONE_TAIL_LEN = 4` (정책 단일 원천).
- `CURRENT_EXPORT_ENDPOINTS` / `CURRENT_IMPORT_ENDPOINTS` (현재 구현 분류).

### `app/modules/export_import/service.py` (신규, 129줄)

응답 dict 빌더 + 파일 크기 cap helper + audit detail 빌더.
- `is_file_size_within_limit(size)` (10MB) — api.py byte-equivalent.
- `build_data_convert_preview_response(...)` / `build_data_convert_apply_response(...)`.
- `build_audit_detail_for_bulk_import(inserted, review_inserted, skipped)` —
  api.py byte-equivalent. **detail 에 환자 PII 부재 가드**.

### `tests/test_19_12_admin.py` (신규, 869줄, 128 cases)

contract 검증.

1. admin schemas — 응답 key 셋 정합 (status/login/about/system-settings/ai-settings).
2. admin schemas — AI api_key 평문 부재 가드 + public_config_drop_keys 정합.
3. admin service — mask_api_key / mask_munjanara_pw / mask_munjanara_key
   byte-equivalent (16 케이스).
4. admin service — redact_public_config 비밀 key 제거 + 원본 mapping 무수정.
5. admin service — audit_detail_cap = 500.
6. admin service — build_* 응답 빌더 7개 byte-equivalent.
7. backup schemas — 응답 key 셋 정합 (list/now/restore/dir + apply-update.backup).
8. backup schemas — BACKUP_PREFIX/SUFFIX = services/backup.py 정합.
9. backup schemas — interval_floor=5 / keep_count_default=30 / interval_default=60.
10. backup service — 파일명 빌더 3종 + is_backup_filename 7 케이스.
11. backup service — build_* 응답 빌더 7개 byte-equivalent.
12. backup service — normalize_interval_min / normalize_keep_count 12 케이스.
13. audit schemas — AUDIT_LOG_ROW_KEYS 7키 + AUDIT_DETAIL_CAP=500 + actors.
14. audit service — cap_detail / serialize_audit_log_row(s) / normalize_actor 12 케이스.
15. export_import schemas — preview 11키 / apply 5키 / 정책 상수.
16. export_import service — is_file_size_within_limit 6 케이스 + build_*
    + build_audit_detail_for_bulk_import (PII 부재 가드).
17. **단방향 경계 (D-4)** — 4 모듈 × app.routers 미참조.
18. **외부 / DB 의존성 가드** — 8 파일 × urllib/requests/httpx/shutil/sqlite3 부재.
19. **DB 변경 가드** — 8 파일 × db.commit/add/delete/flush 부재.
20. **라우터 시그니처 무수정** — admin (17) / backup (7) / data-convert (2) /
    export (2) / ai/settings (2) + ai._mask_api_key 본체 검증.
21. **운영 DB 보호** — engine.dispose() / clinic_before_restore_/v* /
    _backup_db_before_update / "안전을 위해 업데이트를 중단합니다" 가드.
22. **공개 config 비밀 값 보호** — pop("admin_password_hash") / pop("sync_secret")
    + sms_get 마스킹 패턴.
23. **AuditLog detail 500자 cap + bulk_import detail PII 부재 가드** (괄호 균형 추출).

### `dosu_clinic.spec` (수정, +17줄)

`hidden` 리스트에 19-12 신규 12개 모듈 + 5줄 주석/공백 등록.
- `app.modules.admin` + service + schemas
- `app.modules.backup` + service + schemas
- `app.modules.audit` + service + schemas
- `app.modules.export_import` + service + schemas

### `tests/test_pyinstaller_hidden_imports.py` (수정, +13줄)

`EXPECTED_19_X_MODULES_MODULES` 에 12개 모듈 추가 (spec 등록 + 실제 import 두 검증).

## 의도 / 이유

- **byte-equivalent 분리** — 인라인 응답 dict / 마스킹 / 파일명 / 정책 상수가
  `api.py` (~3800줄) / `ai.py` (~929줄) / `services/backup.py` (~180줄) 안에 분산.
  19-13+ 라우터 채택 시점에 본 helper 채택.
- **API key / 문자나라 계정 / sync_secret / admin_password_hash 원문 노출 ⊥** —
  단일 원천 helper (`mask_api_key` / `mask_munjanara_*` / `redact_public_config`)
  + frozenset 가드 (`AI_SETTINGS_FORBIDDEN_KEYS` / `PUBLIC_CONFIG_DROP_KEYS`)
  로 회귀 보호.
- **AuditLog detail 500자 cap + PII 부재** — `AUDIT_DETAIL_CAP` 단일 원천 +
  bulk_import audit 호출에서 PII 변수 (`it.get("name")` / `p.phone` 등) 부재
  검증 (괄호 균형 추출).
- **운영 DB 보호 정책 가드** — `engine.dispose()` / 안전망 백업 (복구 직전 +
  업데이트 직전) / "업데이트 중단" 메시지 회귀 검출.
- **계약 회귀 보호** — `schemas.py` 의 frozenset 응답 키 셋이 임의 변경 검출.
  관리자탭 / 자동 업데이트 UI / 백업 섹션 / 환자탭 데이터 변환 / AI 설정 모달
  의존 키 보호.
- **단방향 경계 (D-4) 보존** — `admin/backup/audit/export_import` 모두
  `app.routers` 미참조. read-only / 응답 dict 조립 / 정책 상수 만.

## compatibility wrapper / 라우터 무수정

- `app/routers/api.py` 본체 *완전 무수정* — 26 관리자/백업/audit/data-convert/export
  핸들러 그대로 동작.
- `app/routers/ai.py` 본체 *완전 무수정* — `_mask_api_key` / `_serialize_setting` /
  `ai_settings_get/put` 그대로 동작.
- `app/services/backup.py` 본체 *완전 무수정* — `list_backups` / `make_backup` /
  `restore_*` / `_timer_loop` / `start/stop_auto_backup` 그대로 동작.
- `app/services/auth.py` 본체 *완전 무수정* — PBKDF2 + 5회 잠금 + 세션 TTL.
- `tests/test_19_12_admin.py` 의 라우터 시그니처 검증 30+ 케이스가 본체 무수정 확증.
- 응답 dict 키 / 타입 *완전 보존*.

## 수정 금지 범위 준수

| 금지 항목 | 준수 |
|---|---|
| DB schema 변경 | ✅ 무수정 |
| migration 생성 | ✅ 무수정 |
| 운영 DB 직접 접근 | ✅ 부재 검증 (urllib/sqlite3/shutil import 부재) |
| 백업/복구 실제 동작 방식 변경 | ✅ services/backup.py / api.py:restore 본체 무수정 |
| 관리자 UI 디자인 변경 | ✅ main.html 무수정 |
| 기존 관리자 API 응답 key 변경 | ✅ schemas.py contract 가 검출 |
| API key / 계정 / 비밀번호 원문 노출 | ✅ AI_SETTINGS_FORBIDDEN_KEYS / mask_* helper |
| 개인정보 원문 로그 저장 | ✅ AUDIT_DETAIL_CAP=500 + bulk_import detail PII 부재 가드 |
| 예약/환자/치료사/휴무/치료항목/통계/문자 로직 변경 | ✅ 19-1 ~ 19-11 무수정 |
| AI/RAG 핵심 로직 변경 | ✅ services/ai/* 무수정 |
| 실제 외부 API 호출 | ✅ urllib/requests/httpx import 부재 |
| 실제 외부 문자 발송 | ✅ FakeSmsProvider 정책 그대로 |
| 하네스/테스트 약화 | ✅ conftest.py 무수정 / pyproject.toml per-file-ignores 무수정 |
| requirements.txt / PyInstaller spec 불필요 수정 | ✅ spec 은 12 신규 모듈 hidden import 등록만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 회귀 테스트 통과 |

## 자동 수정 루프 횟수

**2 회차 코드 수정** — 1회차에서 2 fail (audit/service docstring `db.add(` 토큰 +
audit_call 정규식), 2회차에서 통과. 3회차에서 ruff 자동 보정 (미사용 import 제거).
**5회 한도 내**.

## 5회 실패 여부

**미해당** — 2회차 통과.

## 위반 / 우회 없음

- `pyproject.toml` per-file-ignores 무수정.
- 운영 DB 직접 open 없음.
- 외부 API 호출 없음.
- `app.routers` / `app.services.backup` / `app.services.auth` 본체 무수정.
- DB schema / migration 무수정.
- API key / 문자나라 계정 / sync_secret / admin_password_hash / 환자 PII 원문 노출 없음.
