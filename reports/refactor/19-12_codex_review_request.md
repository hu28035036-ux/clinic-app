# 19-12 Codex 검증 요청서

## 1. 세션 이름

`19-12_admin_backup_audit_export_import_boundary` — 관리자 / 백업 / 감사 로그 /
export_import 후보 helper 분리. 라우터 본체 *완전 무수정*. **API key / 문자나라
계정 / 개인정보 원문 비노출 + 운영 DB 보호 정책 가드** 명시.

## 2. 이번 세션 목표

`api.py` (`~3800줄`) / `ai.py` (`~929줄`) / `services/backup.py` (`~180줄`) 의
관리자 / about / config / system-settings / 백업 / 복구 / audit-logs / data-convert
응답 dict / 마스킹 정책 / 파일명 / detail cap / 비밀 값 제거 정책을
`app/modules/{admin,backup,audit,export_import}/` 후보 구조에 byte-equivalent 로
분리. **API key 등록 여부만 노출 / 문자나라 계정 비노출 / sync_secret 비노출 /
환자 PII audit/log 비노출 / 운영 DB 보호 (engine.dispose + atomic rename) 정책
보존**. *라우터 본체 / 응답 key / DB schema 완전 무수정*.

## 3. 변경 파일 목록

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

## 4. 실제 이동 / 분리한 admin 로직

- 공개 config 비밀 값 제거 정책 (`admin_password_hash` / `sync_secret`) →
  `admin/service.py:redact_public_config` + `admin/schemas.py:PUBLIC_CONFIG_DROP_KEYS`.
- AI api_key 마스킹 (앞 4자 + ****) → `admin/service.py:mask_api_key`.
- 문자나라 비밀번호 마스킹 (****) → `admin/service.py:mask_munjanara_pw`.
- 문자나라 API key 마스킹 (앞 4자 + ****) → `admin/service.py:mask_munjanara_key`.
- AuditLog detail 500자 cap → `admin/service.py:audit_detail_cap`
  (`audit/service.py:cap_detail` 와 정합).
- 관리자 / about / system-settings 응답 dict 빌더 7개 →
  `admin/service.py:build_*` / `serialize_ai_setting`.
- 응답 키 contract → `admin/schemas.py:*_RESPONSE_KEYS` (frozenset, 14 셋).
- AI 설정 응답 평문 부재 가드 → `AI_SETTINGS_FORBIDDEN_KEYS = {"api_key"}`.

라우터 본체 (`api.py:get_config`/`update_config`/`admin_status`/.../`ai.py:_mask_api_key`/
`_serialize_setting`/`ai_settings_get`/`ai_settings_put`) 무수정 — 본 helper 는
별도 정의된 byte-equivalent 후보. 라우터 채택 ⊥.

## 5. 실제 이동 / 분리한 backup 로직

- 백업 파일명 정책 (`BACKUP_PREFIX = "clinic_"` / `BACKUP_SUFFIX = ".db"` /
  `before_restore_` / `before_update_v`) → `backup/schemas.py` 단일 원천 +
  `backup/service.py:make_*_filename` / `is_backup_filename`.
- 자동 백업 정책 상수 (interval_floor=5 / interval_default=60 / keep_count_default=30)
  → `backup/schemas.py` + `backup/service.py:normalize_*`.
- `make_backup` / `restore_latest` / `restore_by_name` / `backup_dir` / `restore`
  응답 dict 빌더 7개 → `backup/service.py:build_*`.
- 응답 키 contract → `backup/schemas.py:BACKUP_*_KEYS` (frozenset, 9 셋).

`services/backup.py` (180줄, `list_backups` / `make_backup` / `restore_latest` /
`restore_by_name` / `_enforce_keep_limit` / `_timer_loop` / `start/stop_auto_backup` /
`auto_backup_once_at_startup`) + `api.py:restore` / `_backup_db_before_update` 는
**완전 무수정**.

## 6. audit / export_import 처리 방식

### audit (현재 기능)

- AuditLog row 직렬화 (7키 — id/ts/node_id/actor/action/entity_id/detail) →
  `audit/service.py:serialize_audit_log_row(s)`.
- detail 500자 cap → `audit/service.py:cap_detail` + `audit/schemas.py:AUDIT_DETAIL_CAP`.
- actor 정규화 (빈값 → "system") + action / entity_id 정규화 → `audit/service.py:normalize_*`.
- 알려진 actor / action prefix 셋 → `audit/schemas.py:AUDIT_KNOWN_ACTORS` /
  `AUDIT_KNOWN_ACTION_PREFIXES` (참고용 — 강제 ⊥).
- AI 전용 `AiUsageLog` 는 `services/ai/ai_logging.py` 단일 원천 — audit 모듈 재정의 ⊥.
- AuditLog retention 정책 (예: 90일 자동 정리) — **현재 미구현, 19-x 후속 검토**
  로 명시.

### export_import (현재 부분 + 후속)

- **현재 기능**: data-convert/preview (응답 11키) + data-convert/apply (응답 5키) +
  Excel export 2개 (`/api/export/manual-schedule.xlsx` / `/api/export/stats.xlsx`).
- 응답 dict 빌더 (preview / apply) + 파일 크기 cap (10MB) helper +
  audit detail 빌더 (PII 부재) → `export_import/service.py`.
- 응답 키 contract + 정책 상수 (file_size_max / bulk_chunk / header_scan_rows /
  phone_tail_len) → `export_import/schemas.py`.
- 현재 endpoint 셋 (`CURRENT_EXPORT_ENDPOINTS` / `CURRENT_IMPORT_ENDPOINTS`).
- **후속 검토**: 비트U차트 / EMR import / CSV export — 현재 미구현으로 명시 +
  `_dc_*` 헬퍼 12개 (~600줄) + Excel export 본체 (~800줄) byte-equivalent 분리는
  19-13+ TODO 로 표기.

## 7. 현재 기능 / 후속 검토 분류

### 현재 기능 (helper 분리 대상)

- 관리자 인증 (`/api/admin/{status,login,logout,change-password}`)
- 자동 업데이트 (`/api/about/{check,download,apply}-update`, `/about/update-log`)
- 설정 (`/api/config[/sync-secret/regenerate]`, `/api/mode`, `/api/system-settings`,
  `/api/ai/settings`)
- 백업 / 복구 (`/api/backup`, `/api/restore`, `/api/backup/{list,now,dir,
  restore-latest,restore-by-name}`)
- 감사 로그 (`/api/audit-logs`)
- data-convert (`/api/data-convert/{preview,apply}`)
- Excel export (`/api/export/{manual-schedule,stats}.xlsx`) — 응답 키 contract 부재
  (이진 파일 응답), endpoint 셋만 기록.

### 후속 검토 (비-목표)

- 비트U차트 / EMR import (현재 미구현).
- CSV / 외부 시스템 export (현재 Excel만).
- AuditLog retention 정책.
- about check/download/apply update 응답 빌더 (분기 多, 부수효과 — PyInstaller 폴더
  교체 + updater.bat 실행 + engine.dispose() 동반 — 19-13+).
- `_dc_*` 헬퍼 12개 + Excel export 본체 (~1400줄) byte-equivalent 분리 (19-13+).
- 직원 / 관리자 다중 등급 권한 (현재 admin or guest).

## 8. compatibility wrapper 유지 여부

- 라우터 본체 *완전 무수정* — 26 관리자/백업/audit/data-convert/export 핸들러 +
  AI settings 2 핸들러 그대로 동작.
- `services/backup.py` 본체 *완전 무수정*.
- `services/auth.py` 본체 *완전 무수정*.
- `app/routers/__init__.py` 무수정 — import 경로 그대로.
- 본 helper 패키지는 *전적으로 추가* — 기존 import 경로 / 함수 시그니처 / 응답
  dict / 응답 key / 마스킹 패턴 *어느 것도 변경 ⊥*.
- `tests/test_19_12_admin.py` 의 라우터 시그니처 검증 30+ 케이스가 본체 무수정 확증.

## 9. 수정 금지 범위 준수 여부

| 금지 항목 | 준수 |
|---|---|
| DB schema 변경 | ✅ 무수정 |
| migration 생성 | ✅ 무수정 |
| 운영 DB 직접 접근 | ✅ 부재 검증 |
| 백업/복구 실제 동작 변경 | ✅ services/backup.py / api.py:restore 본체 무수정 |
| 관리자 UI 디자인 변경 | ✅ main.html 무수정 |
| 기존 관리자 API 응답 key 변경 | ✅ schemas.py contract |
| API key / 계정 / 비밀번호 원문 노출 | ✅ AI_SETTINGS_FORBIDDEN_KEYS + mask_* + 라우터 sms_get/get_config 마스킹 정책 검증 |
| 개인정보 원문 로그 저장 | ✅ AUDIT_DETAIL_CAP=500 + bulk_import audit detail PII 부재 가드 |
| 예약/환자/치료사/휴무/치료항목/통계/문자 로직 변경 | ✅ 19-1~19-11 무수정 |
| AI/RAG 핵심 로직 변경 | ✅ services/ai/* 무수정 |
| 실제 외부 API 호출 | ✅ urllib/requests/httpx import 부재 |
| 실제 외부 문자 발송 | ✅ FakeSmsProvider 정책 그대로 |
| 하네스/테스트 약화 | ✅ conftest.py / pyproject.toml 무수정 |
| requirements.txt / PyInstaller spec 불필요 수정 | ✅ spec 은 12 신규 모듈 hidden import 등록만 |
| 기존 SMS AI / 휴무 AI 동작 변경 | ✅ 회귀 테스트 통과 |

## 10. 기존 관리자 API 응답 key 유지 여부

✅ 유지. 본 19-12 가 라우터 본체 / 응답 dict / 응답 key 변경 ⊥.

- `/api/admin/status` (2키) / `/api/admin/login` (2키) / `/api/admin/logout` (1키) /
  `/api/admin/change-password` (2키)
- `/api/about` (8키) / `/api/about/check-update` (분기 별) /
  `/api/about/download-update` (6키) / `/api/about/apply-update` (4키) /
  `/api/about/update-log` (6키)
- `/api/config` (공개 — 비밀 제거 후) / `/api/config/sync-secret` (1키) /
  `/api/config/regenerate-sync-secret` (2키)
- `/api/system-settings` (6키)
- `/api/ai/settings` (9키 — api_key_masked / api_key_set 포함, **api_key 평문 부재**)
- `/api/audit-logs` (row 7키)

응답 키 contract 검증 케이스 14 + 라우터 시그니처 검증 케이스 30+ = **44+ 케이스
모두 통과**.

## 11. API key / 계정 / 비밀번호 원문 노출 여부

**노출 부재.**

- `AI_SETTINGS_FORBIDDEN_KEYS = {"api_key"}` — `AI_SETTINGS_RESPONSE_KEYS` 와
  isdisjoint 검증 통과.
- `mask_api_key` byte-equivalent 8 케이스 통과 (4자 이하 → ****, 그 외 → 앞 4자 + ****).
- `mask_munjanara_pw` byte-equivalent 4 케이스 통과 (값 있으면 **** / 없으면 "").
- `mask_munjanara_key` byte-equivalent 4 케이스 통과 (앞 4자 + ****).
- `redact_public_config` 가 admin_password_hash + sync_secret 제거 + 원본
  mapping 무수정 검증 통과.
- 라우터 `api.py:get_config` / `update_config` / `sms_get` 의 마스킹 패턴 본체
  무수정 검증 통과.

## 12. 개인정보 원문 로그 / 응답 노출 여부

**노출 부재.**

- `AUDIT_DETAIL_CAP = 500` 정책 가드 통과.
- `cap_detail` byte-equivalent 4 케이스 통과.
- `audit/service.py:serialize_audit_log_row` 가 row.detail 그대로 반환 (호출지
  책임으로 PII 원문 부재).
- `bulk_import` audit detail 빌더 (`build_audit_detail_for_bulk_import`) →
  "AI 데이터변환 N명 추가 (검토필요 K) / S건 건너뜀" — 카운트만, 환자명 / 차트 /
  전화 부재 검증 통과.
- 라우터 `api.py:data_convert_apply` 의 audit 호출 (괄호 균형 추출) → PII 변수
  (`it.get("name")` / `p.phone` / `p.chart_no` 등) 부재 검증 통과.

## 13. 운영 DB 보호 여부

**보호.**

- `engine.dispose()` 호출 검증 — `api.py:restore` + `services/backup.py:
  restore_latest` / `restore_by_name` 모두 통과.
- 안전망 백업 (`clinic_before_restore_*`) 자동 생성 검증 통과.
- 자동 업데이트 직전 SQLite online-backup (`_backup_db_before_update` +
  `clinic_before_update_v*`) + 실패 시 "안전을 위해 업데이트를 중단합니다" 가드
  검증 통과.
- 본 19-12 helper 는 `shutil` / `sqlite3` / `engine` 의존 ⊥ — DB 변경 패턴
  (`db.commit/add/delete/flush`) 부재 검증 통과 (8 파일).
- `scripts/check_db_path.py` exit 0.

## 14. 외부 API 호출 여부

**호출 부재.**

- 본 19-12 helper 8 파일 × `urllib.request` / `requests` / `httpx` import 부재
  검증 통과.
- 라우터 본체 무수정 — `api.py` 의 `urllib.request` 사용 (about/check-update /
  download-update) 그대로.
- 본 19-12 가 외부 manifest URL / 다운로드 URL 호출 추가 ⊥.

## 15. 실제 문자 발송 여부

**발송 부재.**

- 19-10 의 `app/modules/sms/provider.py:FakeSmsProvider` 정책 그대로.
- 본 19-12 helper 는 SMS 로직 미참조 — 문자나라 계정 마스킹 helper 만 추가
  (응답 노출 차단).
- `tests -k "ai_sms"` 통과 (회귀 부재).

## 16. 기존 예약 / 문자 / 통계 / AI 영향 여부

**영향 부재.** 회귀 테스트 모두 통과:

- 19-1~19-11 모듈 (`appointments` / `leaves` / `treatments` / `patients` /
  `notes` / `therapists` / `sms` / `stats`) — 무수정.
- 예약 / 휴무 / 치료항목 / 환자 / 치료사 / 통계 / 문자 라우터 본체 — 무수정.
- AI / RAG / Safety 라우터 + 서비스 본체 — 무수정.
- `tests -k "ai_sms or ai_leave or rag or safety or contract"` — 144 통과.
- 전체 1487 / 1 skipped / 7 xfailed.

## 17. 순환참조 위험 여부

**위험 부재.**

- `app/modules/admin/` / `backup/` / `audit/` / `export_import/` 모두 D-4 단방향:
  `app.routers` 미참조 검증 통과 (4 모듈).
- 본 helper 는 `app.models` / `app.config` 도 직접 참조 ⊥ — caller 가 primitives
  주입 (Path / str / int / dict).
- `audit/service.py` / `backup/service.py` / `export_import/service.py` 의 lazy
  import 도 부재 (정적 분석으로 충분).
- 8 파일 모두 `import app.routers` / `from app.routers` 부재.

## 18. 주석 / 문서화 기준 적용 여부

**적용.**

- 4 모듈 × `__init__.py` 패키지 docstring (본 세션 범위 / 범위 외 / COMPAT /
  SAFETY / RISK / NOTE / TODO).
- 12 파일 모두 모듈 docstring (본 세션 범위 + COMPAT / SAFETY / RISK / NOTE 마커).
- 함수 / 상수 단위 주석:
  - `# COMPAT:` — 응답 키 / 시그니처 보존
  - `# SAFETY:` — API key / 계정 / sync_secret / PII / 운영 DB / 외부 API 차단
  - `# RISK:` — engine.dispose / atomic rename / 시간 가중치 / detail cap / 자동 업데이트 흐름
  - `# NOTE:` — 정책 / 임계치 / fallback / 정합 위치
  - `# TODO(후속 검토):` / `# TODO(19-13+):` — 본 세션 비-목표 명시
- 의미 없는 줄 주석 부재.
- 주석 작성 때문에 기능 동작 변경 부재.

## 19. 실행한 테스트와 결과

| 검증 | 결과 |
|---|---|
| `pytest tests -q` | **1487 passed, 1 skipped, 7 xfailed, 27 warnings** |
| `pytest tests/test_19_12_admin.py -v` | **128 passed** |
| `pytest tests/test_pyinstaller_hidden_imports.py -v` | **179 passed** |
| `pytest tests -k "ai_sms or ai_leave or rag or safety or contract" -q` | **144 passed** |
| `pytest tests/test_admin_auth_required.py` | **21 passed** |
| `pytest tests/test_admin_ui_smoke.py` | **14 passed** |
| `pytest tests/test_db_restore_safety.py` | **6 passed** |
| `ruff check app tests scripts` | **All checks passed!** |
| `scripts/check_db_path.py` | **exit 0** |

## 20. 실패 / 수정 루프 횟수

**2 회차 코드 수정** + ruff 자동 보정 1회. 5회 한도 내. **5회 실패 미해당**.

| 회차 | 가설 | 변경 | 결과 |
|---|---|---|---|
| 1 | 신규 contract test 작성 후 1회차 실행 | 4 모듈 12 파일 + spec + hidden imports test + contract test | 2 fail (audit/service docstring `db.add(` 토큰 + audit_call 정규식이 inner `)` 까지) |
| 2 | docstring 토큰 + 정규식 두 건 수정 | docstring 문구 변경 + 괄호 균형 카운트로 정규식 교체 | 128 / 128 통과 |
| (보정) | ruff 자동 보정 | 미사용 `inspect` import 제거 + import block 정렬 | All checks passed |

## 21. 19-13 AI commands 와 기존 예약 / 휴무 / 문자 연결부 정리로 넘어가도 되는지 판단 기준

**Claude Code 자체 판단: yes (조건부).**

근거:
- 1487 / 1 skipped / 7 xfailed — 신규 152 케이스 추가 + 기존 회귀 0건.
- ruff All checks passed.
- 운영 DB 보호 검사 통과 (exit 0).
- 응답 key contract 14 셋 + 라우터 시그니처 검증 30+ 케이스 통과.
- 단방향 경계 (D-4) 4 모듈 통과.
- API key / 계정 / sync_secret / PII 비노출 가드 통과.
- 외부 API / DB 변경 / 외부 문자 발송 / 라우터 본체 변경 부재.

**조건**: Codex 가 다음을 독립 검증 후 19-13 진입 권고.

1. `app/modules/admin/__init__.py` / `service.py` / `schemas.py` 가 라우터 본체와
   별도 정의된 byte-equivalent helper 인지 (라우터 채택 부재).
2. `redact_public_config` / `mask_api_key` / `mask_munjanara_*` 가 단일 원천 helper
   정책으로 작동하는지 (라우터 본체와 byte-equivalent).
3. `AI_SETTINGS_FORBIDDEN_KEYS = {"api_key"}` 가 `AI_SETTINGS_RESPONSE_KEYS` 와
   isdisjoint.
4. `audit/service.py:cap_detail` 와 `admin/service.py:audit_detail_cap` 의 500
   정책 정합.
5. `services/backup.py:list_backups` / `make_backup` / `restore_*` 본체 무수정
   확인 (git diff 직접 검사).
6. `api.py:audit` / `list_audit_logs` / `data_convert_*` 본체 무수정 확인.
7. `dosu_clinic.spec` 의 hidden imports 12 개 모듈 등록 정합.
8. `tests/test_pyinstaller_hidden_imports.py` 의 EXPECTED_19_X_MODULES 확장 정합.
9. `tests/test_19_12_admin.py` 128 케이스 재실행 통과.
10. 전체 `pytest tests -q` 재실행 — 1487 통과 (warnings 27 = 19-11 baseline 동일).
11. 단방향 경계 (D-4) 4 모듈 검증 — `app.routers` import 부재.
12. 19-12 본 모듈 8 파일 × `db.commit/add/delete/flush` + `urllib/requests/httpx/
    shutil/sqlite3` 부재 검증.

## 18 (참고). Codex 가 집중 검토할 파일

1. `app/modules/admin/service.py` (마스킹 / 비밀 값 제거 / 응답 빌더 — 정책 단일 원천)
2. `app/modules/audit/service.py` (detail cap / row 직렬화 — PII 부재 가드)
3. `app/modules/backup/service.py` (파일명 정책 / 응답 빌더 / interval 정규화)
4. `app/modules/export_import/service.py` (audit detail PII 부재 빌더 / 파일 크기 cap)
5. `tests/test_19_12_admin.py` 의 §10~§13 라우터 시그니처 + 비밀 값 보호 + PII
   부재 가드 케이스
6. `app/routers/api.py` / `app/routers/ai.py` git diff = 0 확인
7. `app/services/backup.py` / `app/services/auth.py` git diff = 0 확인

## 19 (참고). Codex 가 반드시 확인할 체크리스트

- [ ] 19-12 본 모듈 8 파일 × `app.routers` 미참조
- [ ] 19-12 본 모듈 8 파일 × `urllib.request` / `requests` / `httpx` / `shutil` /
  `sqlite3` 미참조
- [ ] 19-12 본 모듈 8 파일 × `db.commit(` / `db.add(` / `db.delete(` / `db.flush(`
  미참조 (docstring 포함 → 토큰 검증)
- [ ] `AI_SETTINGS_FORBIDDEN_KEYS` 와 `AI_SETTINGS_RESPONSE_KEYS` isdisjoint
- [ ] `PUBLIC_CONFIG_DROP_KEYS` 가 `admin_password_hash` + `sync_secret` 포함
- [ ] `AUDIT_DETAIL_CAP == 500` (admin/service + audit/schemas 정합)
- [ ] `BACKUP_PREFIX == "clinic_"` / `BACKUP_SUFFIX == ".db"` (services/backup.py 정합)
- [ ] `bulk_import` audit detail = 카운트만 (환자명 / 차트 / 전화 부재)
- [ ] `dosu_clinic.spec` hidden imports 에 12 신규 모듈
- [ ] `tests/test_pyinstaller_hidden_imports.py` EXPECTED_19_X_MODULES 에 12 추가
- [ ] `tests -q` 재실행 — 1487 통과
- [ ] `ruff check app tests scripts` — clean
- [ ] `scripts/check_db_path.py` — exit 0

## 20. 다음 세션으로 넘어가도 되는지에 대한 Claude Code 의 자체 판단

**yes** — 위 §21 기준 충족. Codex 가 §18 집중 검토 + §19 체크리스트 확인 후
19-13 (AI commands / 예약·휴무·문자 연결부 정리) 진입 가능.

남은 위험 요소:
- `_dc_*` 헬퍼 12개 (~600줄) + Excel export (~800줄) byte-equivalent 분리는 19-13+ 로 연기.
- `about/check-update` / `download-update` / `apply-update` 응답 빌더는 분기 多 +
  부수효과 (PyInstaller 폴더 교체) 동반 — 19-13+ 로 연기.
- 비트U차트 / EMR import / CSV export / AuditLog retention 정책은 미구현
  (후속 19-x).
