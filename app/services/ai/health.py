"""AI/RAG 관리자 상태 집계기 — 18-7.

목적:
  ``GET /api/ai/status`` 엔드포인트가 한 번의 read-only 호출로 다음을 조립할
  수 있도록 도메인 함수를 제공한다:

  - AI 모드 (local_only / local_first / ai_assist) — 현재 설정에서 파생
  - 검색 모드 (keyword / vector / hybrid / disabled) — pipeline 의 effective 모드
  - Knowledge 문서 / chunk / vector 카운트
  - 마지막 reindex 결과 (status / 시간 / 카운터 / failed_paths)
  - vector 사용 가능 여부 (api_key + flag + sdk)
  - 외부 API 사용 가능 여부 (sdk_installed + key + enabled)
  - prompt_version (단일 진실원천)
  - 최근 AI 호출 요약 (outcome / feature 카운트 + 최근 N건 메타)

원칙 (사용자 18-7 세션 지시문 + AI_WORKING_RULES §1-7):
  1. **외부 LLM/Embedding 호출 0** — 본 모듈은 read-only 집계. 어떤 분기에서도
     provider/embedding_provider 인스턴스화 / 호출 안 함.
  2. **API key / PII 노출 금지** —
     - api_key: ``api_key_set`` boolean 으로만 노출. 평문/마스킹 모두 미반환.
     - AI 로그: 이미 ``ai_logging.py`` 가 sha256 해시 + 마스킹 후 저장 — 본 집계는
       ``error_detail`` 200자 컷 + ``prompt_hash`` / ``response_hash`` 미노출.
  3. **운영 DB 직접 접근 금지** — 호출자가 주입한 SQLAlchemy ``Session`` 만 사용.
  4. **응답 키 변경 금지** — `/api/ai/manual/{search,ask}` 응답에는 영향 없음.
     본 모듈은 별도 엔드포인트 (`/api/ai/status`) 만 만든다.
  5. **회귀 0** — 호출자가 본 모듈을 사용하지 않아도 기존 동작 보존
     (router 가 본 모듈을 import 하지 않으면 영향 0).

결정성:
  - ``last_reindex.failed_paths`` / ``recent_logs.recent`` 는 caller 가 N 지정 가능.
  - 시간 필드는 ISO8601 문자열 (timezone-naive UTC, datetime.utcnow 와 일관).
  - 카운터는 모두 int. 필드 부재 시 ``0`` / ``None`` / ``""``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

# 의존 모듈 — 모두 외부 호출 0.
from ...models import models as _m
from . import pii as _pii
from .rag.prompts import DEFAULT_VERSIONS as _PROMPT_DEFAULT_VERSIONS

# ──────────────────────── 정책 상수 ────────────────────────

# 응답 메타 — UI 가 모드/검색 모드를 매핑할 때 참고.
AI_MODE_LOCAL_ONLY = "local_only"
AI_MODE_LOCAL_FIRST = "local_first"
AI_MODE_AI_ASSIST = "ai_assist"

SEARCH_MODE_KEYWORD = "keyword"
SEARCH_MODE_VECTOR = "vector"
SEARCH_MODE_HYBRID = "hybrid"
SEARCH_MODE_DISABLED = "disabled"

# 본 세션은 hybrid pipeline 미통합 (사용자 18-7 지시문: vector/hybrid 로직
# 재작성 금지 + 새 migration 금지). 따라서 production effective search_mode 는
# 항상 ``keyword`` (pipeline.run_manual_ask 가 keyword_retrieve 만 사용).
# vector path 도입은 18-8 또는 m014 시점에 결정.
_EFFECTIVE_SEARCH_MODE = SEARCH_MODE_KEYWORD

# 최근 AI 로그 lookback / 최대 표시 건수 (UI 부하 / DB 쿼리 비용 상한).
DEFAULT_RECENT_HOURS = 24
DEFAULT_RECENT_LIMIT = 5
MAX_RECENT_LIMIT = 20

# error_detail 표시 상한 — DB 컬럼은 500 자, 본 모듈은 admin 화면 표시용으로
# 200 자만 노출 (혹시라도 PII 누출 시 영향 최소화).
ERROR_DETAIL_DISPLAY_LIMIT = 200

# AI usage outcome — DB 에 기록된 표준값 (ai_logging.py 와 1:1).
_OUTCOMES = ("success", "warning", "blocked", "error")

# AI feature — 현재 사용 중 표준값. 본 집계에서 "by_feature" 키로 노출.
_FEATURES = (
    "manual_search", "manual_ask",
    "sms_validate", "sms_draft",
    "action_parse", "action_preview", "action_execute",
)


# ──────────────────────── dataclass ────────────────────────


@dataclass
class LastReindex:
    """``knowledge_index_runs`` MAX 행 요약 — UI 표시용."""
    id: Optional[int] = None
    started_at: Optional[str] = None      # ISO8601
    finished_at: Optional[str] = None     # ISO8601
    status: Optional[str] = None
    trigger: Optional[str] = None
    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    total_chunks: int = 0
    inserted_chunks: int = 0
    updated_chunks: int = 0
    skipped_chunks: int = 0
    failed_chunks: int = 0
    failed_paths: list[str] = field(default_factory=list)
    errors_count: int = 0


@dataclass
class RecentLogEntry:
    """``ai_usage_logs`` 단일 행 요약 — UI 표시용 메타만 (PII/원문 부재)."""
    ts: Optional[str] = None              # ISO8601
    feature: str = ""
    outcome: str = ""
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    pii_filter_hits: int = 0
    hallucination_guard_hits: int = 0
    error_detail: str = ""                # 200자 cap. 원문/PII 미포함 (insert 시 정책)


# ──────────────────────── 모드 / 검색 모드 / 가용성 ────────────────────────


def derive_ai_mode(setting: _m.AiSetting) -> str:
    """현재 ``AiSetting`` 으로부터 effective AI 모드 파생.

    AiSetting 에 ``ai_mode`` 컬럼이 아직 없으므로 다음 룰로 파생 (18-7 시점):
      - enabled=False                   → "local_only"
      - enabled + api_key 미설정         → "local_only"
      - enabled + model 미설정           → "local_only"
      - 그 외                           → "local_first" (기본 안전 모드)

    ``ai_assist`` 는 명시적 컬럼 도입 후 (m014 / 18-8) 운영자가 토글하는 모드.
    18-7 시점에는 자동 추론으로 ``ai_assist`` 가 되지 않는다.
    """
    if not bool(setting.enabled):
        return AI_MODE_LOCAL_ONLY
    if not (setting.api_key or "").strip():
        return AI_MODE_LOCAL_ONLY
    if not (setting.model or "").strip():
        return AI_MODE_LOCAL_ONLY
    return AI_MODE_LOCAL_FIRST


def derive_search_mode(setting: _m.AiSetting) -> str:
    """현재 effective 검색 모드.

    18-7 시점은 ``pipeline.run_manual_ask`` 가 ``keyword_retrieve`` 만 사용 →
    항상 ``keyword``. AI 자체가 disabled 라도 manual/search 는 keyword 로
    동작하므로 ``disabled`` 가 아닌 ``keyword`` 로 노출.

    18-8 이후 ``AI_RAG_HYBRID_ENABLED`` flag 컬럼 추가 시 본 함수에서 분기 추가.
    """
    _ = setting
    return _EFFECTIVE_SEARCH_MODE


def derive_vector_status(
    setting: _m.AiSetting,
    *,
    sdk_installed: dict[str, bool] | None = None,
) -> dict:
    """vector 사용 가능 여부 + 사유.

    반환 키:
      - ``enabled``    : 운영 토글 (현재 항상 False — m014 미도입)
      - ``available``  : 실제로 vector 경로 사용 가능한가 (sdk + key + enabled)
      - ``reason``     : 사용 불가 사유 (가능하면 빈 문자열)
                         ``"vector_disabled" | "api_key_missing" | "sdk_missing"``

    ``available`` 은 hybrid_enabled flag 가 도입되기 전까지 항상 False —
    본 세션 18-7 은 vector path 를 라우터/UI 어디에도 wire 하지 않음.
    """
    sdk_installed = sdk_installed or {}
    enabled = False  # m014 도입 전: 항상 False
    if not enabled:
        return {
            "enabled": False,
            "available": False,
            "reason": "vector_disabled",
        }
    # 아래는 m014 이후 path — 본 세션에서는 도달 안 함. 미래 확장 자리.
    api_key_set = bool((setting.api_key or "").strip())
    if not api_key_set:
        return {"enabled": True, "available": False, "reason": "api_key_missing"}
    provider_name = (setting.provider or "").strip().lower()
    if provider_name in ("openai", "anthropic") and not sdk_installed.get(provider_name, False):
        return {"enabled": True, "available": False, "reason": "sdk_missing"}
    return {"enabled": True, "available": True, "reason": ""}


def derive_external_api_status(
    setting: _m.AiSetting,
    *,
    sdk_installed: dict[str, bool] | None = None,
) -> dict:
    """외부 API 사용 가능 여부 — LLM / Embedding 분리.

    ``llm_available`` 조건:
      - enabled=True
      - api_key set
      - model set
      - provider 의 sdk 설치
    ``embedding_available`` :
      - 본 세션 18-7 은 항상 False (실제 외부 OpenAI/Anthropic embedding 미구현 — 18-8 이후).
    ``sdk_installed`` :
      - provider 별 import 가능 여부 boolean dict.
      - 운영 환경에서 어떤 provider 가 사용 가능한지 진단용.
    """
    sdk_installed = sdk_installed or {}
    api_key_set = bool((setting.api_key or "").strip())
    model_set = bool((setting.model or "").strip())
    provider_name = (setting.provider or "").strip().lower()
    provider_sdk_ok = bool(sdk_installed.get(provider_name, False))
    llm_available = bool(
        setting.enabled and api_key_set and model_set and provider_sdk_ok
    )
    return {
        "llm_available": llm_available,
        "embedding_available": False,  # 18-7 시점 항상 False (운영 미구현)
        "sdk_installed": dict(sdk_installed),
    }


# ──────────────────────── 카운트 ────────────────────────


def count_documents() -> int:
    """``knowledge/`` 의 문서 수 — loader 캐시 사용 (외부 호출 0)."""
    try:
        from .knowledge.loader import get_raw_documents
        return len(get_raw_documents())
    except Exception:
        return 0


def count_chunks(db: Session) -> int:
    """``knowledge_chunks`` row 수."""
    try:
        return int(db.query(func.count(_m.KnowledgeChunk.id)).scalar() or 0)
    except Exception:
        return 0


def count_vectors(db: Session) -> int:
    """``knowledge_vectors`` row 수."""
    try:
        return int(db.query(func.count(_m.KnowledgeVector.id)).scalar() or 0)
    except Exception:
        return 0


# ──────────────────────── 마지막 reindex ────────────────────────


def get_last_reindex(db: Session, *, max_failed_paths: int = 20) -> LastReindex:
    """``knowledge_index_runs`` 최신 1행 요약.

    행이 없으면 모든 필드 default — 호출자는 ``id is None`` 으로 부재 판정 가능.
    ``failed_paths`` 는 ``\\n`` 으로 join 되어 저장됨 — split 후 빈 줄 제거.
    ``errors`` 는 JSON 배열 — 길이만 ``errors_count`` 로 노출 (PII 보호).
    """
    out = LastReindex()
    try:
        row = (
            db.query(_m.KnowledgeIndexRun)
            .order_by(_m.KnowledgeIndexRun.id.desc())
            .first()
        )
    except Exception:
        return out
    if row is None:
        return out

    out.id = int(row.id)
    out.started_at = _iso_or_none(row.started_at)
    out.finished_at = _iso_or_none(row.finished_at)
    out.status = (row.status or None)
    out.trigger = (row.trigger or None)
    out.total_documents = int(row.total_documents or 0)
    out.processed_documents = int(row.processed_documents or 0)
    out.failed_documents = int(row.failed_documents or 0)
    out.total_chunks = int(row.total_chunks or 0)
    out.inserted_chunks = int(row.inserted_chunks or 0)
    out.updated_chunks = int(row.updated_chunks or 0)
    out.skipped_chunks = int(row.skipped_chunks or 0)
    out.failed_chunks = int(row.failed_chunks or 0)

    failed_raw = row.failed_paths or ""
    if failed_raw:
        paths = [p.strip() for p in failed_raw.split("\n") if p.strip()]
        if max_failed_paths > 0 and len(paths) > max_failed_paths:
            paths = paths[:max_failed_paths]
        out.failed_paths = paths

    errors_raw = row.errors or ""
    if errors_raw:
        try:
            import json as _json
            arr = _json.loads(errors_raw)
            if isinstance(arr, list):
                out.errors_count = len(arr)
        except Exception:
            out.errors_count = 0

    return out


# ──────────────────────── 최근 AI 로그 요약 ────────────────────────


def get_recent_logs(
    db: Session,
    *,
    hours: int = DEFAULT_RECENT_HOURS,
    limit: int = DEFAULT_RECENT_LIMIT,
) -> dict:
    """최근 ``hours`` 시간 내 AI 로그 요약.

    반환 키:
      ``lookback_hours`` : 조회 윈도우.
      ``total``          : 윈도우 내 총 row 수.
      ``by_outcome``     : outcome 별 카운트 (4개 표준 outcome 모두 0 으로 시드).
      ``by_feature``     : feature 별 카운트 (현재 사용 중인 feature 만).
      ``recent``         : 가장 최근 ``limit`` 건의 메타 (PII/원문 부재).

    PII 보호:
      - ``prompt_hash`` / ``response_hash`` 는 노출 안 함 (해시지만 진단 가치 0).
      - ``error_detail`` 는 ``ERROR_DETAIL_DISPLAY_LIMIT`` 까지만 노출.
      - ``recent`` 항목은 ``RecentLogEntry`` 필드 9개만 노출.
    """
    if limit < 0:
        limit = 0
    if limit > MAX_RECENT_LIMIT:
        limit = MAX_RECENT_LIMIT
    if hours <= 0:
        hours = DEFAULT_RECENT_HOURS

    out: dict[str, Any] = {
        "lookback_hours": int(hours),
        "total": 0,
        "by_outcome": {o: 0 for o in _OUTCOMES},
        "by_feature": {},
        "recent": [],
    }

    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        # total + by_outcome (단일 쿼리로 group by).
        rows = (
            db.query(_m.AiUsageLog.outcome, func.count(_m.AiUsageLog.id))
            .filter(_m.AiUsageLog.ts >= cutoff)
            .group_by(_m.AiUsageLog.outcome)
            .all()
        )
        total = 0
        for outcome, cnt in rows:
            outcome = outcome or ""
            cnt = int(cnt or 0)
            total += cnt
            if outcome in out["by_outcome"]:
                out["by_outcome"][outcome] = cnt
            else:
                # 표준 outcome 외 값도 카운트에 포함 (legacy 'ok' 등).
                out["by_outcome"][outcome] = cnt
        out["total"] = total

        # by_feature (group by).
        feature_rows = (
            db.query(_m.AiUsageLog.feature, func.count(_m.AiUsageLog.id))
            .filter(_m.AiUsageLog.ts >= cutoff)
            .group_by(_m.AiUsageLog.feature)
            .all()
        )
        by_feature: dict[str, int] = {}
        for feat, cnt in feature_rows:
            feat = feat or ""
            by_feature[feat] = int(cnt or 0)
        out["by_feature"] = by_feature

        # recent N 건 — ts 내림차순.
        if limit > 0:
            recent_rows = (
                db.query(_m.AiUsageLog)
                .filter(_m.AiUsageLog.ts >= cutoff)
                .order_by(_m.AiUsageLog.ts.desc())
                .limit(limit)
                .all()
            )
            out["recent"] = [_serialize_log_row(r) for r in recent_rows]
    except Exception:
        # 로깅 조회 실패는 본 흐름을 막지 않음 — 빈 요약 반환.
        pass

    return out


def _safe_error_detail(text: Optional[str]) -> str:
    """``error_detail`` 노출 직전 2차 PII 보호.

    저장 시점 정책 (``ai_logging.py``) 이 PII 원문을 차단하지만, 본 모듈은
    관리자 화면에 직접 노출되는 API 의 마지막 단계이므로 한 번 더 마스킹한다.
    Codex 18-7 검토 (M-1): "error_detail 반환 전 PII scan/mask 또는
    민감정보 샘플 테스트가 있으면 더 단단".

    절차:
      1. ``pii.scan(text).cleaned`` — 전화/주민번호/카드번호 등 패턴 마스킹.
      2. ``ERROR_DETAIL_DISPLAY_LIMIT`` (200자) cap.
      3. 마스킹 자체가 실패하면 빈 문자열 반환 (원문 누출 절대 방지).

    PII 가 들어가지 않은 일반 진단 메시지 (``"hits=3, top_score=5"`` 등) 는
    pii.scan 이 그대로 통과시킨다.
    """
    if not text:
        return ""
    try:
        masked = _pii.scan(text).cleaned
    except Exception:
        # 마스킹 실패 시 원문 노출 절대 금지 — 빈 문자열로 안전 fallback.
        return ""
    return _truncate(masked, ERROR_DETAIL_DISPLAY_LIMIT)


def _serialize_log_row(row: _m.AiUsageLog) -> dict:
    """``AiUsageLog`` 단일 행 → UI 표시 dict (PII/해시 미노출).

    PII 보호 (Codex 18-7 M-1 반영):
      - ``error_detail`` 은 ``_safe_error_detail`` 가 ``pii.scan`` 마스킹 + 200자 cap 적용.
      - ``prompt_hash`` / ``response_hash`` 컬럼은 응답 dict 에 포함하지 않음.
    """
    return asdict(RecentLogEntry(
        ts=_iso_or_none(row.ts),
        feature=str(row.feature or ""),
        outcome=str(row.outcome or row.status or ""),
        provider=str(row.provider or ""),
        model=str(row.model or ""),
        latency_ms=int(row.latency_ms or 0),
        pii_filter_hits=int(row.pii_filter_hits or 0),
        hallucination_guard_hits=int(row.hallucination_guard_hits or 0),
        error_detail=_safe_error_detail(row.error_detail or ""),
    ))


# ──────────────────────── prompt versions ────────────────────────


def get_prompt_versions() -> dict[str, str]:
    """현재 사용 중인 prompt 의 default 버전 매핑.

    ``rag/prompts.py`` 의 ``DEFAULT_VERSIONS`` 그대로 노출. UI 에서 어떤 버전이
    실제로 사용되는지 확인 가능.
    """
    # dict copy — 외부 변경 방지.
    return dict(_PROMPT_DEFAULT_VERSIONS)


# ──────────────────────── 통합 진입점 ────────────────────────


def build_admin_status(
    db: Session,
    *,
    setting: _m.AiSetting,
    sdk_installed: dict[str, bool] | None = None,
    recent_hours: int = DEFAULT_RECENT_HOURS,
    recent_limit: int = DEFAULT_RECENT_LIMIT,
    max_failed_paths: int = 20,
) -> dict:
    """``GET /api/ai/status`` 응답 본체 조립 — 단일 진입점.

    인자:
      db             : SQLAlchemy 세션 (read-only).
      setting        : 호출자가 미리 로드한 ``AiSetting`` (dependency 호환).
      sdk_installed  : ``router._check_sdk`` 로 미리 확인한 provider 별 boolean.
      recent_hours   : 최근 AI 로그 lookback (기본 24시간).
      recent_limit   : 최근 AI 로그 표시 건수 (기본 5건, 최대 20건).
      max_failed_paths : last_reindex.failed_paths 표시 상한.

    반환: dict (router 가 그대로 JSON 직렬화).

    PII / API key 보호:
      - api_key 평문/마스킹 모두 미반환. ``api_key_set`` boolean 만.
      - prompt_hash / response_hash 미노출.
      - error_detail 200자 cap.
      - 어떤 응답 필드에도 환자 PII 미포함 (insert 시 정책 + 본 모듈 추가 cap).
    """
    sdk_installed = dict(sdk_installed or {})

    return {
        # ── 모드 / 검색 모드 ──
        "ai_mode": derive_ai_mode(setting),
        "search_mode": derive_search_mode(setting),
        "version": "v1.3-stage1",
        # ── AI 설정 (api_key 평문/마스킹 모두 X) ──
        "ai_settings": {
            "enabled": bool(setting.enabled),
            "provider": setting.provider or "openai",
            "model": setting.model or "",
            "api_key_set": bool((setting.api_key or "").strip()),
            "max_tokens": int(setting.max_tokens or 512),
            "temperature": float(setting.temperature or 0.3),
            "pii_guard_enabled": bool(setting.pii_guard_enabled),
        },
        # ── vector 가용성 ──
        "vector_status": derive_vector_status(setting, sdk_installed=sdk_installed),
        # ── 외부 API 가용성 ──
        "external_api": derive_external_api_status(
            setting, sdk_installed=sdk_installed,
        ),
        # ── knowledge 카운트 + 마지막 reindex ──
        "knowledge": {
            "documents": count_documents(),
            "chunks": count_chunks(db),
            "vectors": count_vectors(db),
            "last_reindex": asdict(get_last_reindex(
                db, max_failed_paths=max_failed_paths,
            )),
        },
        # ── prompt 버전 매핑 ──
        "prompt_versions": get_prompt_versions(),
        # ── 최근 AI 로그 요약 ──
        "recent_ai_logs": get_recent_logs(
            db, hours=recent_hours, limit=recent_limit,
        ),
    }


# ──────────────────────── 유틸 ────────────────────────


def _iso_or_none(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return None


def _truncate(s: str, n: int) -> str:
    if not s:
        return ""
    if len(s) <= n:
        return s
    return s[:n] + "...[truncated]"


__all__ = [
    "AI_MODE_LOCAL_ONLY", "AI_MODE_LOCAL_FIRST", "AI_MODE_AI_ASSIST",
    "SEARCH_MODE_KEYWORD", "SEARCH_MODE_VECTOR", "SEARCH_MODE_HYBRID",
    "SEARCH_MODE_DISABLED",
    "DEFAULT_RECENT_HOURS", "DEFAULT_RECENT_LIMIT", "MAX_RECENT_LIMIT",
    "ERROR_DETAIL_DISPLAY_LIMIT",
    "LastReindex", "RecentLogEntry",
    "derive_ai_mode", "derive_search_mode",
    "derive_vector_status", "derive_external_api_status",
    "count_documents", "count_chunks", "count_vectors",
    "get_last_reindex", "get_recent_logs", "get_prompt_versions",
    "build_admin_status",
    "_safe_error_detail",  # PII 보호 helper — 테스트 가시성
]
