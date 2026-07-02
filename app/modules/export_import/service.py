"""data-convert (환자 import) / Excel export 응답 dict 빌더 + 정책 helper (19-12 신규).

19-11 stats.service / 19-10 sms.service 와 동일 패턴 — *byte-equivalent helper*.
실제 파싱 (``openpyxl`` / ``csv``) / 중복 판정 / 헤더 스캔 / 응답 본체 조립은
``app/routers/api.py`` 가 그대로 보유. 라우터 무수정.

# COMPAT: 본 모듈의 모든 ``build_*`` 응답 빌더는 ``app/routers/api.py:
#         data_convert_preview`` / ``data_convert_apply`` 의 인라인 dict 와
#         *byte-equivalent*. 응답 key / 타입 보존.

# SAFETY: 본 모듈은 *응답 dict 조립 / 정책 상수* 만 — 외부 API 호출 ⊥, 외부
#         시스템 import / export ⊥. ``openpyxl`` / ``csv`` import ⊥ (실제 파싱은
#         ``app/routers/api.py:_dc_parse_excel`` / ``_dc_parse_csv_fallback`` 가
#         보유).

# SAFETY: 본 빌더는 *환자 PII 마스킹 ⊥* — 환자탭 모달이 검토 UI 로 PII 평문을
#         사용. 본 19-12 가 정책 변경 ⊥. audit / 로그 노출은 *별도 정책*
#         (``app/modules/audit/service.py:cap_detail`` + caller 의 카운트 only).

# RISK: 본 모듈은 *응답 빌더 helper* — 라우터 채택 ⊥. ``app/routers/api.py``
#       의 인라인 dict 가 단일 진실 원천. byte-equivalent 검증은 19-12 contract
#       테스트가 보유.

# NOTE: 본 모듈은 *읽기 / 응답 dict 조립* 만 — DB 변경 ⊥, 파일 시스템 변경 ⊥.
"""
from __future__ import annotations

from typing import Any, Mapping

from .schemas import DATA_CONVERT_FILE_SIZE_MAX


def is_file_size_within_limit(size_bytes: int) -> bool:
    """파일 크기 cap helper — ``app/routers/api.py:data_convert_preview`` 의
    ``len(content) > 10 * 1024 * 1024`` 와 byte-equivalent.

    RISK: 본 cap 변경 ⊥ — 메모리 부담 / 첨부 거부 정책.
    """
    try:
        return 0 < int(size_bytes) <= DATA_CONVERT_FILE_SIZE_MAX
    except (TypeError, ValueError):
        return False


# ──────────────── 응답 dict 빌더 ────────────────

def build_data_convert_preview_response(
    *,
    total: int,
    new_count: int,
    existing_count: int,
    error_count: int,
    header: list[Any] | None,
    new_patients: list[Mapping[str, Any]],
    review_list: list[Mapping[str, Any]],
    review_count: int,
    errors: list[Any],
    file_name: str | None,
    parse_info: Mapping[str, Any] | None,
    existing_patients: list[Mapping[str, Any]] | None = None,
    dup_in_file_count: int = 0,
) -> dict[str, Any]:
    """``POST /api/data-convert/preview`` 응답 dict — byte-equivalent.

    NOTE: ``app/routers/api.py:data_convert_preview`` 의 인라인 dict 와 byte-equivalent.
    응답 key 13개 (v1.3.51+: existing_patients / dup_in_file_count 추가).
    """
    return {
        "total": int(total),
        "new_count": int(new_count),
        "existing_count": int(existing_count),
        "existing_patients": [dict(p) for p in (existing_patients or [])],
        "dup_in_file_count": int(dup_in_file_count),
        "error_count": int(error_count),
        "header": list(header) if header is not None else None,
        "new_patients": [dict(p) for p in new_patients],
        "review_list": [dict(p) for p in review_list],
        "review_count": int(review_count),
        "errors": list(errors),
        "file_name": file_name,
        "parse_info": dict(parse_info) if parse_info is not None else None,
    }


def build_data_convert_apply_response(
    *,
    inserted: int,
    review_inserted: int,
    skipped: int,
    inserted_patients: list[Mapping[str, Any]],
    skipped_items: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """``POST /api/data-convert/apply`` 응답 dict — byte-equivalent.

    NOTE: ``app/routers/api.py:data_convert_apply`` 의 인라인 dict 와 byte-equivalent.
    응답 key 5개.

    SAFETY: 응답에 환자 PII 평문 포함 — 환자탭 모달이 사용. audit detail 은
    카운트만 (정책 단일 원천).
    """
    return {
        "inserted": int(inserted),
        "review_inserted": int(review_inserted),
        "skipped": int(skipped),
        "inserted_patients": [dict(p) for p in inserted_patients],
        "skipped_items": [dict(s) for s in skipped_items],
    }


def build_audit_detail_for_bulk_import(
    *,
    inserted: int,
    review_inserted: int,
    skipped: int,
) -> str:
    """``patient.bulk_import`` audit detail 문자열 빌더 — ``app/routers/api.py:
    data_convert_apply`` 의 ``audit(... f"AI 데이터변환 {len(inserted)}명 추가
    (검토필요 {review_inserted}) / {len(skipped)}건 건너뜀")`` 와 byte-equivalent.

    SAFETY: detail 에 *환자 PII 평문 부재 보장* — 카운트만. 본 19-12 가 정책 변경 ⊥.
    """
    return (
        f"AI 데이터변환 {int(inserted)}명 추가 "
        f"(검토필요 {int(review_inserted)}) / {int(skipped)}건 건너뜀"
    )


# ──────────────── 후속 검토 (현재 미구현 — 단정 ⊥) ────────────────

# TODO(후속 검토): 비트U차트 / EMR import — 현재 미구현. 응답 빌더 / 헬퍼 부재.
# TODO(후속 검토): CSV export — 현재 미구현.
# TODO(19-13+): Excel export 응답 헤더 / StreamingResponse 빌더 — 19-13+ 에서 검토.
# TODO(19-13+): ``_dc_*`` 헬퍼 12개 (~400줄) byte-equivalent 분리 — 19-13+ 에서 검토.
