"""modules.admin — 관리자 / 인증 / 시스템 설정 도메인 후보 구조 (19-12 신규).

19-12 본 세션 범위:
  - **service.py** : 관리자 / about / config / system-settings 응답 dict 빌더 +
    공개 config 정제 helper (``sync_secret`` / ``admin_password_hash`` 제거 정책 상수)
    + AI api_key 마스킹 helper (단일 진실 원천).
  - **schemas.py** : 관리자 / about / config / system-settings 응답 키 contract
    상수 (frozenset).

19-12 본 세션 범위 *외* (라우터 본체 / 관리자 흐름 무수정):
  - ``app/routers/api.py`` 의 모든 관리자 / about / config / system-settings 핸들러
    *완전 무수정* — 본 패키지는 *byte-equivalent helper* 만 제공. 라우터 채택 ⊥.
  - ``app/services/auth.py`` (PBKDF2 + 5회 잠금 + 세션 TTL) *완전 무수정*.
  - ``app/routers/ai.py`` 의 AI 설정 / settings put 핸들러 *완전 무수정*.
  - 자동 업데이트 (about/check-update / download-update / apply-update) 흐름 *완전 무수정*.
  - 예약 / 환자 / 치료사 / 휴무 / 치료항목 / 통계 / 문자 / AI / RAG 흐름 *완전 무수정*.
  - DB schema / migration *완전 무수정*.
  - UI / API URL / 응답 key *완전 무수정*.

# COMPAT: 기존 ``app/routers/api.py`` 의 모든 관리자 핸들러 (`/admin/{status,login,
#         logout,change-password}` / `/about` / `/about/{check-update,download-update,
#         apply-update,update-log}` / `/config[/sync-secret/regenerate-sync-secret]` /
#         `/mode` / `/system-settings`) 그대로 동작. 본 패키지는 *helper 만* 제공
#         — 라우터에서 채택 ⊥. 19-12 contract 테스트가 인라인 동작과 본 helper
#         결과의 byte-equivalent 검증.

# COMPAT: 기존 ``app/routers/ai.py`` 의 ``GET/PUT /api/ai/settings`` 응답 key 9개 + AI
#         api_key 마스킹 정책 (``key[:4] + "****"``) 그대로 동작. 본 패키지의
#         ``mask_api_key`` 는 단일 진실 원천 helper — 라우터에서 채택 ⊥.

# SAFETY: 공개 config 응답에는 ``admin_password_hash`` / ``sync_secret`` *원문 노출 ⊥*
#         — `service.PUBLIC_CONFIG_DROP_KEYS` 상수가 정책 단일 원천. 19-12 가
#         이 정책 변경 ⊥.

# SAFETY: AI ``api_key`` 는 ``api_key_set`` 등록 여부 + ``api_key_masked``
#         (앞 4자 + ``****``) 만 응답. *원문 노출 ⊥*. 본 정책은
#         ``app/routers/ai.py`` 의 ``_mask_api_key`` 와 byte-equivalent.

# SAFETY: 문자나라 (``SmsSetting.munjanara_*``) 계정 / 비밀번호 / API key 응답
#         마스킹 정책 (등록 여부 + 앞 4자 마스킹) 은 ``app/routers/api.py`` 의
#         ``sms_get`` 과 ``app/modules/sms/`` 의 단일 원천. 본 19-12 admin 모듈은
#         재정의 ⊥ — *원문 노출 가드만 명시*.

# RISK: 자동 업데이트 흐름 (``download-update`` / ``apply-update``) 은 PyInstaller
#       프로그램 폴더 교체 + ``updater.bat`` 실행 + ``engine.dispose()`` + 직전 DB
#       자동 백업 (``_backup_db_before_update``) 정책. 본 19-12 가 *변경 ⊥*.

# RISK: 관리자 인증 정책 (PBKDF2 200_000 / 5회 잠금 / 세션 TTL 8시간) 은
#       ``app/services/auth.py`` 단일 원천. 본 19-12 가 *변경 ⊥*.

# NOTE: ``system-settings`` 응답 key 6개 (``manual_slot_limit`` /
#       ``treatment_minutes`` / ``sms_template`` / ``auto_backup_*`` 3개) 는
#       UI 관리자탭 / 백업 모듈 / SMS 템플릿 모듈이 의존. 본 19-12 가 *변경 ⊥*.

# NOTE: ``/api/audit-logs`` 응답 key 7개 (``id`` / ``ts`` / ``node_id`` / ``actor`` /
#       ``action`` / ``entity_id`` / ``detail``) 는 ``app/modules/audit/`` 가 단일 원천
#       — admin 모듈은 *재정의 ⊥*, 관리자탭 표시 정책만 명시.
"""
