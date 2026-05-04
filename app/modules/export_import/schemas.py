"""data-convert (환자 import) / Excel export API 응답 키 contract 상수 (19-12 신규).

frozenset 으로 응답 key 셋 보존. contract 테스트가 인라인 응답 dict 와 본 상수의
key 셋 비교 → 임의 변경 검출.

# COMPAT: 본 frozenset 상수의 *원소 변경 ⊥* — 환자탭 데이터 변환 모달 / 통계탭
#         엑셀 다운로드 의존. contract 테스트가 회귀 검출.

# SAFETY: 응답 row 의 환자 PII (``name`` / ``chart_no`` / ``phone`` / ``birth_date``)
#         는 *현재 정책에서 응답에 포함* — 환자탭 검토 UI 가 사용. 본 19-12 가
#         정책 변경 ⊥. audit / 로그에는 카운트만.

# RISK: 파일 크기 cap (10MB) / BULK_CHUNK (2000) 정책 변경 ⊥ — 메모리 / 트랜잭션
#       부담 직결.
"""
from __future__ import annotations


# ──────────────── /api/data-convert/preview ────────────────

# POST /api/data-convert/preview 응답 key 11개.
# COMPAT: ``app/routers/api.py:data_convert_preview`` 의 dict 와 byte-equivalent.
DATA_CONVERT_PREVIEW_RESPONSE_KEYS: frozenset[str] = frozenset({
    "total",
    "new_count",
    "existing_count",
    "error_count",
    "header",
    "new_patients",
    "review_list",
    "review_count",
    "errors",
    "file_name",
    "parse_info",
})


# ──────────────── /api/data-convert/apply ────────────────

# POST /api/data-convert/apply 응답 key 5개.
# COMPAT: ``app/routers/api.py:data_convert_apply`` 의 dict 와 byte-equivalent.
DATA_CONVERT_APPLY_RESPONSE_KEYS: frozenset[str] = frozenset({
    "inserted",
    "review_inserted",
    "skipped",
    "inserted_patients",
    "skipped_items",
})


# ──────────────── preview 응답 row (new_patients 항목) ────────────────

# preview 응답의 ``new_patients`` row 가 포함하는 key — review_reason / review_reasons
# 추가 후. ``app/routers/api.py:data_convert_preview`` 의 entry dict 와 정합.
# NOTE: ``_dc_parse_excel`` 이 추가하는 추가 필드 (``extra_phones`` /
#       ``invalid_phones`` / ``birth_format_bad`` / ``_has_gender_source`` 등) 는
#       parser 내부 — 본 contract 는 *최소 필드 셋* 만.
DATA_CONVERT_PREVIEW_NEW_PATIENT_MIN_KEYS: frozenset[str] = frozenset({
    "name",
    "chart_no",
    "phone",
    "birth_date",
    "review_reason",
    "review_reasons",
})


# ──────────────── apply 응답 row (inserted_patients 항목) ────────────────

# apply 응답의 ``inserted_patients`` row key.
# COMPAT: ``app/routers/api.py:data_convert_apply`` 의 dict 와 byte-equivalent.
DATA_CONVERT_APPLY_INSERTED_PATIENT_KEYS: frozenset[str] = frozenset({
    "id",
    "name",
    "chart_no",
    "phone",
    "birth_date",
    "gender",
    "extra_phones",
    "review_reasons",
})


# ──────────────── 정책 상수 (단일 원천) ────────────────

# RISK: 파일 크기 cap — ``app/routers/api.py:data_convert_preview`` 의
#       ``len(content) > 10 * 1024 * 1024`` 와 byte-equivalent.
DATA_CONVERT_FILE_SIZE_MAX: int = 10 * 1024 * 1024  # 10MB

# RISK: bulk insert chunk size — ``app/routers/api.py:data_convert_apply`` 의
#       ``BULK_CHUNK = 2000`` 와 byte-equivalent.
DATA_CONVERT_BULK_CHUNK: int = 2000

# 헤더 스캔 최대 행 — ``_dc_find_header_row`` 의 ``rows[:10]`` 와 byte-equivalent.
DATA_CONVERT_HEADER_SCAN_ROWS: int = 10

# 차트번호 / 이름+생일+전화뒤4자리 중복 판정 키 — ``_dc_dupe_key_in_file`` /
# ``_dc_is_duplicate_in_db`` 와 byte-equivalent.
PATIENT_DUPE_PHONE_TAIL_LEN: int = 4


# ──────────────── 후속 검토 (현재 미구현 — 단정 ⊥) ────────────────

# TODO(후속 검토): 비트U차트 / EMR import 응답 key — *현재 미구현*.
# TODO(후속 검토): CSV export 응답 / Excel export 응답 dict 빌더 — *현재 미구현*.

# 현재 구현된 export 엔드포인트 — *Excel 만, 응답 헤더는 ``Content-Disposition`` +
# StreamingResponse*. 본 19-12 는 *response key contract 부재* (이진 파일 응답).
CURRENT_EXPORT_ENDPOINTS: frozenset[str] = frozenset({
    "/api/export/manual-schedule.xlsx",
    "/api/export/stats.xlsx",
})

# 현재 구현된 import 엔드포인트.
CURRENT_IMPORT_ENDPOINTS: frozenset[str] = frozenset({
    "/api/data-convert/preview",
    "/api/data-convert/apply",
})


# ──────────────── 모든 export_import contract 셋 (cross-check 용) ────────────────

EXPORT_IMPORT_ALL_CONTRACT_SETS: dict[str, frozenset[str]] = {
    "data_convert_preview": DATA_CONVERT_PREVIEW_RESPONSE_KEYS,
    "data_convert_apply": DATA_CONVERT_APPLY_RESPONSE_KEYS,
    "data_convert_preview_new_patient_min": DATA_CONVERT_PREVIEW_NEW_PATIENT_MIN_KEYS,
    "data_convert_apply_inserted_patient": DATA_CONVERT_APPLY_INSERTED_PATIENT_KEYS,
}
