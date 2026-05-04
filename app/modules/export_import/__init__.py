"""modules.export_import — Excel export / data-convert (환자 import) 도메인 후보 구조 (19-12 신규).

19-12 본 세션 범위:
  - **service.py** : ``data-convert/preview`` / ``data-convert/apply`` 응답 dict
    빌더 + 정책 상수 (파일 크기 cap / bulk insert chunk / 헤더 alias).
  - **schemas.py** : ``data-convert/preview/apply`` 응답 키 contract 상수
    (frozenset).

19-12 본 세션 범위 *외* (export/import 본체 무수정):
  - ``app/routers/api.py`` 의 ``data_convert_preview`` / ``data_convert_apply``
    핸들러 *완전 무수정*.
  - ``app/routers/api.py`` 의 ``_dc_*`` 헬퍼 (~600줄: ``_dc_normalize_gender`` /
    ``_dc_find_header_row`` / ``_dc_normalize_phone`` / ``_dc_is_valid_mobile`` /
    ``_dc_split_phones`` / ``_dc_normalize_date`` / ``_dc_dupe_key_in_file`` /
    ``_dc_is_duplicate_in_db`` / ``_dc_classify_review`` / ``_dc_log`` /
    ``_dc_parse_csv_fallback`` / ``_dc_parse_excel``) *완전 무수정*.
  - ``app/routers/api.py`` 의 Excel export 핸들러 ``export_manual_schedule`` /
    ``export_stats_xlsx`` (~800줄) *완전 무수정* — *후속 검토*.
  - ``app/routers/api.py`` 의 ``patient.bulk_import`` audit 호출 *완전 무수정*.
  - DB schema / migration *완전 무수정*.
  - UI / API URL / 응답 key *완전 무수정*.

19-12 본 세션 *비-목표* (현재 미구현 / 후속 검토):
  - 비트U차트 / EMR import (현재 미구현 — 후속 19-x).
  - CSV / 외부 시스템 export (현재 Excel만 — 후속 19-x).
  - 대량 import 트랜잭션 정책 강화 (현재 ``BULK_CHUNK = 2000`` 그대로).

# COMPAT: 기존 ``app/routers/api.py`` 의 ``data-convert/preview`` 응답 12개 key
#         (``total`` / ``new_count`` / ``existing_count`` / ``error_count`` /
#         ``header`` / ``new_patients`` / ``review_list`` / ``review_count`` /
#         ``errors`` / ``file_name`` / ``parse_info``) + ``data-convert/apply``
#         응답 5개 key (``inserted`` / ``review_inserted`` / ``skipped`` /
#         ``inserted_patients`` / ``skipped_items``) — 환자탭 데이터 변환 모달
#         의존. 본 19-12 가 key 변경 ⊥.

# SAFETY: 환자 PII 원문 (이름 / 차트번호 / 전화 / 생년월일) 은 *현재 응답에 그대로
#         포함* — 환자탭 모달이 미리보기 / 검토 UI 로 사용. 본 19-12 가 *마스킹
#         정책 변경 ⊥* — 다만 *로그 / audit 에는 부재 보장* (``audit("patient.
#         bulk_import")`` 의 detail 은 카운트만).

# SAFETY: 본 19-12 모듈은 *응답 dict 빌더* 만 — 외부 API 호출 ⊥, 외부 시스템
#         실제 import / export ⊥. ``openpyxl`` / ``csv`` 의존 ⊥ (실제 파싱은
#         라우터 본체 ``_dc_parse_excel`` / ``_dc_parse_csv_fallback`` 가 보유).

# RISK: 대량 import 시 ``BULK_CHUNK = 2000`` 청크 단위 ``bulk_insert_mappings`` +
#       청크별 ``db.commit()`` — 트랜잭션 격리 약함. 동시 import 시 부분 적용
#       가능. 본 19-12 가 *변경 ⊥* — 현재 정책 그대로.

# RISK: 파일 크기 cap (10MB) 은 ``app/routers/api.py:data_convert_preview`` 의
#       ``len(content) > 10 * 1024 * 1024`` 와 byte-equivalent. 본 19-12 가
#       *변경 ⊥*.

# NOTE: ``_dc_*`` 헬퍼 12개 (~400줄) 는 *후속 검토* — 19-13+ 에서 본 모듈에
#       byte-equivalent 분리 검토. 본 19-12 는 schemas / 응답 dict 빌더만.

# NOTE: Excel export (``/api/export/manual-schedule.xlsx`` / ``/api/export/stats.
#       xlsx``, ~800줄) 은 *후속 검토* — 19-13+ 에서 본 모듈에 byte-equivalent
#       분리 검토. 본 19-12 는 schemas / 응답 dict 빌더만.

# TODO(후속 검토): 비트U차트 / EMR import (현재 미구현) — 향후 19-x 에서 검토.
# TODO(후속 검토): CSV / 외부 시스템 export — 향후 19-x 에서 검토.
# TODO(19-13+): ``_dc_*`` 헬퍼 12개 분리 + Excel export 분리.
"""
