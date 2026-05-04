"""modules.backup — 백업 / 복구 도메인 후보 구조 (19-12 신규).

19-12 본 세션 범위:
  - **service.py** : 백업 / 복구 응답 dict 빌더 (``list_backups`` row 포맷 +
    ``make_backup`` / ``restore_*`` 결과 dict) + 운영 DB 보호 정책 상수 +
    파일명 prefix/suffix 상수 (단일 원천).
  - **schemas.py** : 백업 / 복구 응답 키 contract 상수 (frozenset).

19-12 본 세션 범위 *외* (백업 본체 / 운영 DB 흐름 무수정):
  - ``app/services/backup.py`` 의 ``list_backups`` / ``make_backup`` /
    ``restore_latest`` / ``restore_by_name`` / ``_enforce_keep_limit`` /
    ``_timer_loop`` / ``start_auto_backup`` / ``stop_auto_backup`` /
    ``auto_backup_once_at_startup`` *완전 무수정*.
  - ``app/routers/api.py`` 의 ``/backup`` / ``/restore`` / ``/backup/{list,now,
    dir,restore-latest,restore-by-name}`` 핸들러 *완전 무수정*.
  - ``app/routers/api.py`` 의 ``/about/apply-update`` 의 ``_backup_db_before_update``
    *완전 무수정* (자동 업데이트 직전 SQLite online-backup API 사용).
  - 자동 백업 타이머 스레드 (``daemon=True``) 동작 *완전 무수정* — conftest 람다
    교체 호환 유지.
  - DB schema / migration *완전 무수정*.
  - UI / API URL / 응답 key *완전 무수정*.

# COMPAT: 기존 ``app/services/backup.py`` 의 ``BACKUP_PREFIX`` / ``BACKUP_SUFFIX``
#         상수와 byte-equivalent. 본 패키지는 *helper 만* 제공 — 라우터에서 채택 ⊥.
#         19-12 contract 테스트가 인라인 동작과 본 helper 결과의 byte-equivalent 검증.

# COMPAT: ``GET /api/backup/list`` 응답 row key (``name`` / ``path`` / ``size`` /
#         ``mtime``) + ``POST /api/backup/now`` 응답 key (``ok`` / ``name`` / ``size``
#         또는 ``error``) + ``POST /api/backup/restore-{latest,by-name}`` 응답 key
#         (``ok`` / ``restored_from`` / ``msg`` 또는 ``error``) + ``GET /api/backup/dir``
#         응답 key (``path``) — 관리자탭 백업 섹션 의존.

# SAFETY: 본 모듈은 *백업 메타데이터 직렬화* + *정책 상수* 만 노출 — 운영 DB 파일
#         직접 read/write ⊥. 실제 ``shutil.copy2`` / ``engine.dispose()`` /
#         ``Path.replace`` 는 ``app/services/backup.py`` 와 ``app/routers/api.py``
#         의 ``restore`` 핸들러가 보유.

# SAFETY: 실제 운영 DB 경로 (``%APPDATA%/도수치료예약/clinic.db``) 는 ``app/config.py:
#         get_db_path`` 가 단일 원천. 본 19-12 가 경로 / 백업 폴더 정책 변경 ⊥.

# RISK: 복구 시 운영 DB 교체 직전 ``engine.dispose()`` 필수 — Windows 에서
#       SQLAlchemy connection pool 이 DB 파일 lock 한 상태로 ``Path.replace`` 하면
#       ``PermissionError``. 본 정책은 ``app/routers/api.py:restore`` /
#       ``app/services/backup.py:restore_latest`` / ``restore_by_name`` 단일 원천.
#       본 19-12 가 *변경 ⊥*.

# RISK: 복구 직전 안전망 백업 1회 자동 생성 (``clinic_before_restore_<ts>.db``) —
#       복구 후 되돌리기 가능. 본 정책은 ``app/services/backup.py`` 단일 원천.
#       본 19-12 가 *변경 ⊥*.

# RISK: 자동 업데이트 (``apply-update``) 직전 SQLite online-backup API 로 ``clinic_
#       before_update_v<ver>_<ts>.db`` 생성. 본 19-12 가 *변경 ⊥*.

# NOTE: 자동 백업 정책 (``SystemSetting.auto_backup_*``) 은 ``app/modules/admin/``
#       service 의 ``build_system_settings_response`` 가 응답 노출. 본 19-12 가
#       정책 / interval 최소값 (5분) 변경 ⊥.

# NOTE: 백업 보관 정책 (``auto_backup_keep_count`` 초과 시 오래된 파일 삭제) 은
#       ``app/services/backup.py:_enforce_keep_limit`` 단일 원천. 본 19-12 가
#       *변경 ⊥*.

# NOTE: 자동 백업 타이머 스레드 (``daemon=True``) 는 ``conftest.py`` 가 람다 교체로
#       무력화. 본 19-12 가 타이머 / 무력화 가능성 변경 ⊥ — 테스트 약화 ⊥.
"""
