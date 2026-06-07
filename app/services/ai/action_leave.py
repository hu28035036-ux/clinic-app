"""AI 자연어 치료사 휴무 등록 — 백엔드 코어 (세션 13).

[docs/specs/04_ai_action_leave.md] 의 § 4·5·6·7·8 을 코드로 옮긴 모듈.

원칙 (절대 위반 X):
  - parse / preview 는 DB 를 절대 수정하지 않는다 (read-only).
  - execute 는 confirm=True + 직전 preview 의 HMAC 토큰 검증을 통과해야만 실행된다.
  - LLM 응답은 후보값일 뿐. 모든 값은 코드가 다시 검증/매칭한다.
  - 동일 (employee_id, leave_date) 키 → upsert. 기존 휴무 API 와 동일 헬퍼 호출.
  - LLM hint 는 참고만. 코드 키워드 룰이 우선.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from time import monotonic, time
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..ai import ai_logging as ai_log
from ..ai import pii as pii_mod
from ..ai.date_resolver import KST, resolve_date
from ..ai.provider import AiProvider, AiResult, AiUnavailable

# ──────────── 상수 ────────────

# spec § 7.2: 프로세스 시작 시 1회 생성, 메모리 only. 재시작 시 모든 토큰 무효화.
_SERVER_SECRET: bytes = secrets.token_bytes(32)
TOKEN_TTL_SEC = 120
TOKEN_VERSION = 1

INTENT_NAME = "create_therapist_leave"     # 사용자 결정 (plan § 1)

# spec § 1: 입력 사전 게이트
_LEAVE_KEYWORDS = ("휴무", "연차", "월차", "반차", "휴가", "쉼", "쉬는")
_MAX_INPUT_LEN = 200
_MIN_INPUT_LEN = 1

# 다중 명령 차단 — "와", "과", "및", "," 가 있고 동시에 휴무 키워드가 2회 이상이면 다중
_MULTI_TOKENS = ("및", ",")
_MULTI_PARTICLE = re.compile(r"(?:과|와)\s")

# 환자/차트 PII 의심 키워드 — 휴무 등록 명령에는 절대 등장하면 안 됨.
# 사용자가 실수로 환자 정보를 같이 적어도 LLM 으로 prompt 가 새지 않게 사전 차단.
_PATIENT_INDICATORS = ("환자", "차트", "카르테", "차트번호", "내원", "방문", "chart")

# 한국어 사용자 메시지 (spec § 12)
USER_MESSAGES = {
    "ok": "",
    "no_leave_keyword": "휴무 관련 키워드가 없습니다 (휴무·연차·월차·반차·휴가)",
    "multi_command": "한 번에 한 명, 한 건만 등록할 수 있습니다",
    "input_too_short": "입력이 너무 짧습니다",
    "input_too_long": "입력이 너무 깁니다 (200자 이내)",
    "parse_fail": "AI 응답을 이해할 수 없습니다. 다시 시도해주세요",
    "intent_mismatch": "휴무 등록 명령이 아닌 것 같습니다",
    "hallucinated_name": "AI 응답이 입력과 일치하지 않아 거부되었습니다",
    "hallucinated_date": "AI 응답이 입력과 일치하지 않아 거부되었습니다",
    "low_confidence": "AI 가 확신하지 못해 실행할 수 없습니다. 더 명확하게 입력해주세요",
    "ambiguous_date": "날짜가 모호합니다 — 구체적인 날짜를 입력해주세요",
    "invalid_date": "유효하지 않은 날짜입니다",
    "out_of_range_date": "과거 90일 ~ 미래 365일 안의 날짜만 등록 가능합니다",
    "ambiguous_half_day": "오전/오후 반차 중 어느 것인지 명시해주세요",
    "no_match": "치료사를 찾을 수 없습니다",
    "multi_match": "동명이인이 있어 자동 등록할 수 없습니다 — 다른 식별자로 입력해주세요",
    "inactive_therapist": "퇴사/비활성 치료사입니다",
    "not_therapist": "치료사가 아닙니다",
    "invalid_name": "치료사 이름이 유효하지 않습니다",
    "provider_error": "AI 서비스에 일시적 문제가 있습니다",
    "pii_blocked": "입력에 개인정보로 보이는 내용이 있어 차단되었습니다",
    "not_confirmed": "확인이 필요합니다",
    "overwrite_not_acknowledged": "기존 휴무 덮어쓰기를 확인해주세요",
    "token_format": "요청이 유효하지 않습니다 — 다시 분석해주세요",
    "token_signature": "요청이 유효하지 않습니다 — 다시 분석해주세요",
    "token_unsafe": "요청이 유효하지 않습니다 — 다시 분석해주세요",
    "token_mismatch": "요청이 유효하지 않습니다 — 다시 분석해주세요",
    "token_expired": "분석 결과가 만료되었습니다 (2분 초과) — 다시 분석해주세요",
    "conflict_changed": "다른 사용자가 동시에 변경했습니다 — 다시 분석해주세요",
    "therapist_changed": "다른 사용자가 동시에 변경했습니다 — 다시 분석해주세요",
    "db_error": "저장 중 오류가 발생했습니다",
    "no_leave_date": "날짜 정보를 찾을 수 없습니다",
    "feature_disabled": "AI 기능이 비활성화되어 있습니다",
}


def _msg(outcome: str) -> str:
    return USER_MESSAGES.get(outcome, USER_MESSAGES["parse_fail"])


# ──────────── Pydantic 스키마 (LLM 응답) ────────────

class ParsedAction(BaseModel):
    """LLM 의 strict JSON 응답 스키마. 추가 필드 금지."""
    model_config = ConfigDict(extra="forbid")

    intent: Literal["create_therapist_leave"]
    employee_name_raw: str
    original_date_text: str
    leave_type_hint: Literal["full", "morning", "afternoon", "unknown"]
    leave_kind_hint: Literal["annual", "monthly", "unknown"]
    confidence: Literal["high", "low"]


# ──────────── 결과 컨테이너 ────────────

@dataclass
class ParseResult:
    ok: bool
    outcome: str
    parsed: Optional[dict]
    warnings: list[str]
    safe_to_continue: bool
    message: str = ""


@dataclass
class PreviewResult:
    ok: bool
    outcome: str
    candidate: Optional[dict]
    mode: Optional[str]                    # create | overwrite | noop | None
    existing: Optional[dict]
    appointments_count: int
    warnings: list[str]
    safe_to_execute: bool
    preview_token: Optional[str]
    preview_token_exp: Optional[int]
    message: str = ""


@dataclass
class ExecuteResult:
    ok: bool
    outcome: str
    leave_id: Optional[str]
    mode: Optional[str]
    message: str


@dataclass
class _MatchResult:
    status: str                            # ok | no_match | multi_match | inactive_therapist | not_therapist | invalid_name
    employee: Any = None                   # 매칭된 Employee (status=ok 일 때)
    candidates: list = field(default_factory=list)


@dataclass
class _ConflictReport:
    mode: str                              # create | overwrite | noop
    existing_id: Optional[str]
    existing_dict: Optional[dict]
    overwrite_warning: Optional[str]


class _InvalidToken(Exception):
    def __init__(self, outcome: str):
        super().__init__(outcome)
        self.outcome = outcome


# ──────────── 시간 (테스트 monkeypatch 가능) ────────────

def _now_provider() -> datetime:
    """현재 시각 (KST). 테스트에서 monkeypatch 로 고정 가능."""
    return datetime.now(KST)


# ──────────── 가드 1·2: 입력 사전 게이트 ────────────

def _pre_gate(text: str) -> Optional[str]:
    """길이·휴무 키워드·다중 명령·PII 차단. None=통과, 문자열=차단 outcome."""
    if not text or not text.strip():
        return "input_too_short"
    if len(text) < _MIN_INPUT_LEN:
        return "input_too_short"
    if len(text) > _MAX_INPUT_LEN:
        return "input_too_long"
    if not any(k in text for k in _LEAVE_KEYWORDS):
        return "no_leave_keyword"
    # PII 강한 차단 — 전화번호 / 주민등록번호 발견 시 LLM 호출 자체 안 함.
    # 휴무 날짜 (2026-04-30) 는 birth 패턴과 형식이 같으므로 1건은 통과시키되,
    # 2건 이상이면 환자 생년월일 동반으로 보고 차단.
    # 차트번호 의심 (5+자리 순수 숫자) / 환자 키워드는 휴무 컨텍스트에 나올 일 없음 → 즉시 차단.
    scan = pii_mod.scan(text)
    if scan.found.get("phone") or scan.found.get("rrn"):
        return "pii_blocked"
    if scan.found.get("chart_no_maybe"):
        return "pii_blocked"
    if any(k in text for k in _PATIENT_INDICATORS):
        return "pii_blocked"
    if len(scan.found.get("birth", [])) >= 2:
        return "pii_blocked"
    # 다중 명령 — "," 또는 "및" 또는 "과/와" 가 보이는데 휴무 키워드가 2회 이상 등장
    leave_kw_count = sum(text.count(k) for k in _LEAVE_KEYWORDS)
    has_separator = any(t in text for t in _MULTI_TOKENS) or bool(_MULTI_PARTICLE.search(text))
    if has_separator and leave_kw_count >= 2:
        return "multi_command"
    return None


# ──────────── 가드 3: LLM 호출 + Pydantic strict ────────────

def _build_system_prompt() -> str:
    """spec § 2.1 의 요지를 한국어로 명확히."""
    return (
        "너는 한국 도수치료 클리닉의 휴무 등록 명령 분석기다.\n"
        "입력은 한국어 한 문장이며, 한 명의 치료사에 대한 한 건의 휴무 등록 명령이다.\n"
        "다음 JSON 스키마로만 응답하고 다른 텍스트는 출력하지 마라. 추가 필드 금지.\n"
        "입력에 없는 정보를 만들어내지 마라. 모르면 \"unknown\" 으로 응답하라.\n"
        "\n"
        "스키마:\n"
        "{\n"
        '  "intent": "create_therapist_leave",\n'
        '  "employee_name_raw": "<입력에서 발췌한 치료사 이름 토큰 그대로>",\n'
        '  "original_date_text": "<입력에서 발췌한 날짜 표현 그대로>",\n'
        '  "leave_type_hint": "full" | "morning" | "afternoon" | "unknown",\n'
        '  "leave_kind_hint": "annual" | "monthly" | "unknown",\n'
        '  "confidence": "high" | "low"\n'
        "}\n"
    )


def _extract_json_object(text: str) -> Optional[dict]:
    """LLM 응답 텍스트에서 첫 번째 JSON object 를 robust 하게 추출.

    LLM 이 ```json ... ``` 코드 블록으로 감싸도, 앞뒤 짧은 인사말이 붙어도 시도.
    실패 시 None.
    """
    if not text:
        return None
    # 1) 단순 json.loads
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else None
    except Exception:
        pass
    # 2) 첫 '{' 부터 마지막 '}' 까지
    a = text.find("{")
    b = text.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return None
    try:
        v = json.loads(text[a:b + 1])
        return v if isinstance(v, dict) else None
    except Exception:
        return None


def _call_llm_parse(provider: AiProvider, text: str) -> tuple[ParsedAction, AiResult]:
    """LLM 호출 → JSON 파싱 → Pydantic strict.

    실패 케이스:
      - AiUnavailable / 일반 Exception → 호출자가 catch
      - JSON 파싱 실패 / Pydantic 검증 실패 → ValidationError 또는 ValueError raise
    """
    system = _build_system_prompt()
    user = f"입력: {text}"
    result = provider.generate(user, system=system)
    obj = _extract_json_object(result.text)
    if obj is None:
        raise ValueError("json_decode_fail")
    parsed = ParsedAction.model_validate(obj)
    return parsed, result


# ──────────── 가드 6·7: substring 검증 ────────────

def _validate_substring(text: str, parsed: ParsedAction) -> Optional[str]:
    """LLM 이 입력에 없는 토큰을 만들어냈는지. None=통과."""
    norm_text = text.replace(" ", "")
    if parsed.employee_name_raw and parsed.employee_name_raw.replace(" ", "") not in norm_text:
        return "hallucinated_name"
    if parsed.original_date_text and parsed.original_date_text.replace(" ", "") not in norm_text:
        return "hallucinated_date"
    return None


# ──────────── 가드 9: 치료사 매칭 (spec § 5) ────────────

def _normalize_name(s: str) -> str:
    """공백 제거 + 호칭 접미사 제거 ("선생님", "쌤")."""
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace("선생님", "")
    s = s.replace("쌤", "")
    return s


def _match_therapist(db: Session, raw_name: str) -> _MatchResult:
    """DB 에서 정확 1명 매칭. 0명 / 2명 이상 차단."""
    from ...models import models as _m

    norm_input = _normalize_name(raw_name)
    if len(norm_input) < 2 or len(norm_input) > 20:
        return _MatchResult(status="invalid_name")

    # 1) active=True employee
    active = db.query(_m.Employee).filter(
        _m.Employee.active == True,    # noqa: E712 — SQLAlchemy boolean comparison
    ).all()
    matches = [e for e in active if _normalize_name(e.name) == norm_input]
    if len(matches) == 1:
        return _MatchResult(status="ok", employee=matches[0])
    if len(matches) >= 2:
        return _MatchResult(status="multi_match", candidates=matches)

    # 2) active=False employee
    inactive = db.query(_m.Employee).filter(
        _m.Employee.active == False,    # noqa: E712
    ).all()
    if any(_normalize_name(e.name) == norm_input for e in inactive):
        return _MatchResult(status="inactive_therapist")

    return _MatchResult(status="no_match")


# ──────────── 가드 8·10: 휴무 유형 매핑 (spec § 4) ────────────

def _map_leave(text: str, hint_type: str, hint_kind: str) -> tuple[Optional[str], Optional[str], Optional[str], list[str]]:
    """text 와 LLM hint 로 (leave_type, leave_kind) 결정. 코드 우선, hint 는 참고.

    반환: (leave_type, leave_kind, error_outcome, mismatch_logs)
    """
    norm = text.replace(" ", "")
    leave_type: Optional[str] = None
    leave_kind: Optional[str] = None
    mismatch: list[str] = []

    # 1) leave_type — DB 표준은 am/pm/full (기존 캘린더 / fetchLeavesOn 호환)
    if "오전반차" in norm or "오전휴무" in norm:
        leave_type = "am"
    elif "오후반차" in norm or "오후휴무" in norm:
        leave_type = "pm"
    elif any(k in norm for k in ("종일", "하루", "풀데이", "하루휴무")):
        leave_type = "full"
    elif "반차" in norm:
        return None, None, "ambiguous_half_day", []
    elif any(k in norm for k in ("연차", "월차", "휴무", "휴가", "쉼", "쉬는")):
        leave_type = "full"
    else:
        return None, None, "no_leave_keyword", []

    # 2) leave_kind
    if "월차" in norm:
        leave_kind = "monthly"
    else:
        leave_kind = "annual"

    # 3) hint 와 코드 결과 mismatch 로깅용 카운트
    if hint_type and hint_type != "unknown" and hint_type != leave_type:
        mismatch.append(f"leave_type:{hint_type}->{leave_type}")
    if hint_kind and hint_kind != "unknown" and hint_kind != leave_kind:
        mismatch.append(f"leave_kind:{hint_kind}->{leave_kind}")

    return leave_type, leave_kind, None, mismatch


# ──────────── 충돌 / 예약 체크 (spec § 6) ────────────

def _check_conflict(db: Session, employee_id: str, leave_date: str,
                    leave_type: str, leave_kind: str) -> _ConflictReport:
    """동일 (employee_id, leave_date) 기존 휴무가 있는지. read-only."""
    from ...models import models as _m

    existing = db.query(_m.EmployeeLeave).filter(
        _m.EmployeeLeave.employee_id == employee_id,
        _m.EmployeeLeave.leave_date == leave_date,
    ).first()

    if existing is None:
        return _ConflictReport(mode="create", existing_id=None,
                               existing_dict=None, overwrite_warning=None)

    ex_dict = {
        "id": existing.id,
        "leave_type": existing.leave_type or "full",
        "leave_kind": existing.leave_kind or "annual",
        "memo": existing.memo or "",
    }

    same_type = (existing.leave_type or "full") == leave_type
    same_kind = (existing.leave_kind or "annual") == leave_kind
    if same_type and same_kind:
        return _ConflictReport(mode="noop", existing_id=existing.id,
                               existing_dict=ex_dict,
                               overwrite_warning="이미 같은 내용으로 등록되어 있습니다")

    ex_label = _leave_label(existing.leave_type or "full", existing.leave_kind or "annual")
    new_label = _leave_label(leave_type, leave_kind)
    return _ConflictReport(
        mode="overwrite", existing_id=existing.id, existing_dict=ex_dict,
        overwrite_warning=f"기존 휴무({ex_label})를 {new_label}로 덮어씁니다",
    )


def _leave_label(leave_type: str, leave_kind: str) -> str:
    type_kr = {"full": "종일", "am": "오전반차", "pm": "오후반차"}.get(leave_type, leave_type)
    kind_kr = {"annual": "연차", "monthly": "월차"}.get(leave_kind, leave_kind)
    return f"{type_kr}/{kind_kr}"


def _count_appointments(db: Session, therapist_id: str, leave_date: str) -> int:
    """해당 치료사의 해당 날짜 예약 수 (canceled 제외).

    spec § 6.2: status != "canceled" (실제 DB 값, 미국식 1L).
    """
    from ...models import models as _m

    return db.query(_m.Appointment).filter(
        _m.Appointment.therapist_id == therapist_id,
        func.date(_m.Appointment.start_at) == leave_date,
        _m.Appointment.status != "canceled",
    ).count()


def _make_warnings(conflict: _ConflictReport, appt_count: int,
                   assumption: Optional[str]) -> list[str]:
    out: list[str] = []
    if assumption:
        out.append(assumption)
    if conflict.overwrite_warning:
        out.append(conflict.overwrite_warning)
    if appt_count > 0:
        out.append(
            f"해당 날짜에 예약 {appt_count}건이 있습니다. 자동 이동/취소는 하지 않습니다 "
            "— 운영자가 별도 처리하세요"
        )
    return out


# ──────────── preview_token (HMAC-SHA256, spec § 7) ────────────

def _b64_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _b64_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _issue_token(payload: dict) -> tuple[str, int]:
    """HMAC 서명된 preview_token 발급. (token, exp_unix) 반환."""
    body = {**payload, "v": TOKEN_VERSION, "exp": int(time()) + TOKEN_TTL_SEC}
    body_json = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    body_b64 = _b64_encode(body_json.encode("utf-8"))
    sig = hmac.new(_SERVER_SECRET, body_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body_b64}.{sig}", body["exp"]


_REQUIRED_TOKEN_KEYS = (
    "v", "intent", "employee_id", "leave_date", "leave_type", "leave_kind",
    "mode", "safe_to_execute", "exp",
)
_VALID_LEAVE_TYPE = ("full", "am", "pm")
_VALID_LEAVE_KIND = ("annual", "monthly")
_VALID_MODE = ("create", "overwrite", "noop")


def _verify_token(token: str, *, now_unix: int) -> dict:
    """token 무결성·만료·필수키 검증. 실패 시 _InvalidToken raise."""
    if not token or not isinstance(token, str):
        raise _InvalidToken("token_format")
    parts = token.split(".")
    if len(parts) != 2:
        raise _InvalidToken("token_format")
    body_b64, sig = parts
    expected = hmac.new(_SERVER_SECRET, body_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise _InvalidToken("token_signature")
    try:
        body_json = _b64_decode(body_b64).decode("utf-8")
        payload = json.loads(body_json)
    except Exception as exc:
        raise _InvalidToken("token_format") from exc
    if not isinstance(payload, dict):
        raise _InvalidToken("token_format")
    for k in _REQUIRED_TOKEN_KEYS:
        if k not in payload:
            raise _InvalidToken("token_mismatch")
    if payload.get("v") != TOKEN_VERSION:
        raise _InvalidToken("token_mismatch")
    if payload.get("intent") != INTENT_NAME:
        raise _InvalidToken("token_mismatch")
    if payload.get("leave_type") not in _VALID_LEAVE_TYPE:
        raise _InvalidToken("token_mismatch")
    if payload.get("leave_kind") not in _VALID_LEAVE_KIND:
        raise _InvalidToken("token_mismatch")
    if payload.get("mode") not in _VALID_MODE:
        raise _InvalidToken("token_mismatch")
    if int(payload.get("exp") or 0) < now_unix:
        raise _InvalidToken("token_expired")
    if payload.get("safe_to_execute") is not True:
        raise _InvalidToken("token_unsafe")
    return payload


# ──────────── 로깅 헬퍼 ────────────

def _safe_detail(s: str, n: int = 500) -> str:
    """PII 마스킹 + 길이 컷."""
    if not s:
        return ""
    try:
        cleaned = pii_mod.scan(s).cleaned
    except Exception:
        cleaned = s
    return cleaned[:n]


def _commit_silent(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


# ──────────── parse() — LLM 추출만, DB 미접근 ────────────

def parse(db: Session, *, text: str, provider: AiProvider, settings: Any,
          actor: str = "admin") -> ParseResult:
    """LLM 호출 + 가드 1~7. DB 매칭/검증 없음. 토큰 발급 없음.

    사용자 결정 (plan § 1): 이 엔드포인트는 디버깅/투명성용 read-only 진입점.
    preview/execute 는 이 결과를 신뢰하지 않고 다시 검증한다.
    """
    t0 = monotonic()
    prov_name = getattr(provider, "name", "") or ""
    model_name = getattr(provider, "model", "") or ""

    # [가드 1·2]
    gate = _pre_gate(text)
    if gate:
        ai_log.log_ai_blocked(db, feature="action_leave_parse",
                              reason=gate, provider=prov_name, model=model_name,
                              prompt_text=text, actor=actor)
        ai_log.log_ai_usage(db, feature="action_leave_parse",
                            provider=prov_name, model=model_name,
                            outcome=gate, prompt_text=text, actor=actor,
                            latency_ms=int((monotonic() - t0) * 1000),
                            error_detail=_safe_detail(_msg(gate)))
        _commit_silent(db)
        return ParseResult(ok=False, outcome=gate, parsed=None,
                           warnings=[_msg(gate)], safe_to_continue=False,
                           message=_msg(gate))

    # provider readiness
    if not getattr(settings, "enabled", False) or not provider.is_ready():
        ai_log.log_ai_usage(db, feature="action_leave_parse",
                            provider=prov_name, model=model_name,
                            outcome="provider_error", prompt_text=text,
                            actor=actor,
                            latency_ms=int((monotonic() - t0) * 1000),
                            error_detail=_safe_detail("provider_not_ready"))
        _commit_silent(db)
        return ParseResult(ok=False, outcome="provider_error", parsed=None,
                           warnings=[_msg("provider_error")],
                           safe_to_continue=False,
                           message=_msg("provider_error"))

    # [가드 3·4·5]
    try:
        parsed, ai_result = _call_llm_parse(provider, text)
    except (json.JSONDecodeError, ValidationError, ValueError):
        ai_log.log_ai_usage(db, feature="action_leave_parse",
                            provider=prov_name, model=model_name,
                            outcome="parse_fail", prompt_text=text,
                            actor=actor,
                            latency_ms=int((monotonic() - t0) * 1000),
                            error_detail=_safe_detail(_msg("parse_fail")))
        _commit_silent(db)
        return ParseResult(ok=False, outcome="parse_fail", parsed=None,
                           warnings=[_msg("parse_fail")], safe_to_continue=False,
                           message=_msg("parse_fail"))
    except AiUnavailable:
        ai_log.log_ai_usage(db, feature="action_leave_parse",
                            provider=prov_name, model=model_name,
                            outcome="provider_error", prompt_text=text,
                            actor=actor,
                            latency_ms=int((monotonic() - t0) * 1000),
                            error_detail=_safe_detail("AiUnavailable"))
        _commit_silent(db)
        return ParseResult(ok=False, outcome="provider_error", parsed=None,
                           warnings=[_msg("provider_error")], safe_to_continue=False,
                           message=_msg("provider_error"))
    except Exception:
        ai_log.log_ai_usage(db, feature="action_leave_parse",
                            provider=prov_name, model=model_name,
                            outcome="provider_error", prompt_text=text,
                            actor=actor,
                            latency_ms=int((monotonic() - t0) * 1000),
                            error_detail=_safe_detail("provider_exception"))
        _commit_silent(db)
        return ParseResult(ok=False, outcome="provider_error", parsed=None,
                           warnings=[_msg("provider_error")], safe_to_continue=False,
                           message=_msg("provider_error"))

    if parsed.confidence == "low":
        ai_log.log_ai_usage(db, feature="action_leave_parse",
                            provider=prov_name, model=model_name,
                            outcome="low_confidence", prompt_text=text,
                            response_text=ai_result.text, actor=actor,
                            latency_ms=int((monotonic() - t0) * 1000),
                            error_detail=_safe_detail(_msg("low_confidence")))
        _commit_silent(db)
        return ParseResult(ok=False, outcome="low_confidence", parsed=None,
                           warnings=[_msg("low_confidence")], safe_to_continue=False,
                           message=_msg("low_confidence"))

    # [가드 6·7]
    sub_err = _validate_substring(text, parsed)
    if sub_err:
        ai_log.log_ai_usage(db, feature="action_leave_parse",
                            provider=prov_name, model=model_name,
                            outcome=sub_err, prompt_text=text,
                            response_text=ai_result.text, actor=actor,
                            latency_ms=int((monotonic() - t0) * 1000),
                            error_detail=_safe_detail(_msg(sub_err)),
                            hallucination_guard_hits=1)
        _commit_silent(db)
        return ParseResult(ok=False, outcome=sub_err, parsed=None,
                           warnings=[_msg(sub_err)], safe_to_continue=False,
                           message=_msg(sub_err))

    # 정상
    parsed_dict = parsed.model_dump()
    ai_log.log_ai_usage(db, feature="action_leave_parse",
                        provider=prov_name, model=model_name,
                        outcome="ok", prompt_text=text,
                        response_text=ai_result.text, actor=actor,
                        prompt_tokens=ai_result.prompt_tokens,
                        completion_tokens=ai_result.completion_tokens,
                        latency_ms=int((monotonic() - t0) * 1000))
    _commit_silent(db)
    return ParseResult(ok=True, outcome="ok", parsed=parsed_dict,
                       warnings=[], safe_to_continue=True, message="")


# ──────────── preview() — LLM 재호출 + DB 매칭/검증 + 토큰 발급 ────────────

def preview(db: Session, *, text: str, provider: AiProvider, settings: Any,
            actor: str = "admin", now: Optional[datetime] = None) -> PreviewResult:
    """LLM 추출 + DB 매칭 + 충돌 체크 + HMAC 토큰. DB write 없음."""
    t0 = monotonic()
    now = now or _now_provider()
    prov_name = getattr(provider, "name", "") or ""
    model_name = getattr(provider, "model", "") or ""

    def _block(outcome: str, *, ai_result: Optional[AiResult] = None,
               warnings: Optional[list[str]] = None,
               extra_warning: str = "") -> PreviewResult:
        warns = list(warnings or [])
        if not warns:
            warns = [_msg(outcome)]
        if extra_warning:
            warns.append(extra_warning)
        ai_log.log_ai_usage(
            db, feature="action_leave_preview",
            provider=prov_name, model=model_name,
            outcome=outcome, prompt_text=text,
            response_text=(ai_result.text if ai_result else ""),
            prompt_tokens=(ai_result.prompt_tokens if ai_result else 0),
            completion_tokens=(ai_result.completion_tokens if ai_result else 0),
            latency_ms=int((monotonic() - t0) * 1000),
            error_detail=_safe_detail(_msg(outcome)),
            actor=actor,
        )
        _commit_silent(db)
        return PreviewResult(
            ok=False, outcome=outcome, candidate=None, mode=None,
            existing=None, appointments_count=0, warnings=warns,
            safe_to_execute=False, preview_token=None, preview_token_exp=None,
            message=_msg(outcome),
        )

    # [가드 1·2]
    gate = _pre_gate(text)
    if gate:
        return _block(gate)

    # provider readiness
    if not getattr(settings, "enabled", False) or not provider.is_ready():
        return _block("provider_error")

    # [가드 3·4·5]
    try:
        parsed, ai_result = _call_llm_parse(provider, text)
    except (json.JSONDecodeError, ValidationError, ValueError):
        return _block("parse_fail")
    except AiUnavailable:
        return _block("provider_error")
    except Exception:
        return _block("provider_error")

    if parsed.confidence == "low":
        return _block("low_confidence", ai_result=ai_result)

    # [가드 6·7]
    sub_err = _validate_substring(text, parsed)
    if sub_err:
        return _block(sub_err, ai_result=ai_result)

    # [가드 8·10] 날짜
    dr = resolve_date(text, now=now)
    if dr.outcome != "ok":
        wmsg = dr.assumption or _msg(dr.outcome)
        return _block(dr.outcome, ai_result=ai_result, warnings=[wmsg])

    # 휴무 유형 매핑
    leave_type, leave_kind, lt_err, mismatch_logs = _map_leave(
        text, parsed.leave_type_hint, parsed.leave_kind_hint,
    )
    if lt_err:
        return _block(lt_err, ai_result=ai_result)
    assert leave_type is not None and leave_kind is not None

    # [가드 9] 매칭
    match = _match_therapist(db, parsed.employee_name_raw)
    if match.status != "ok":
        return _block(match.status, ai_result=ai_result)

    employee = match.employee
    # 충돌 (read-only)
    conflict = _check_conflict(db, employee.id, dr.resolved_date, leave_type, leave_kind)
    appt_count = _count_appointments(db, employee.id, dr.resolved_date)
    warnings = _make_warnings(conflict, appt_count, dr.assumption)

    # 토큰 발급
    token, exp = _issue_token({
        "intent": INTENT_NAME,
        "employee_id": employee.id,
        "leave_date": dr.resolved_date,
        "leave_type": leave_type,
        "leave_kind": leave_kind,
        "mode": conflict.mode,
        "existing_id": conflict.existing_id,
        "safe_to_execute": True,
    })

    candidate = {
        "intent": INTENT_NAME,
        "employee_name_raw": parsed.employee_name_raw,
        "employee_id": employee.id,
        "employee_name": employee.name,
        "original_date_text": parsed.original_date_text,
        "resolved_date": dr.resolved_date,
        "assumption": dr.assumption,
        "leave_type": leave_type,
        "leave_kind": leave_kind,
        "memo": "",
    }

    # 성공 로그
    ai_log.log_ai_usage(
        db, feature="action_leave_preview",
        provider=prov_name, model=model_name,
        outcome="ok", prompt_text=text, response_text=ai_result.text,
        prompt_tokens=ai_result.prompt_tokens,
        completion_tokens=ai_result.completion_tokens,
        latency_ms=int((monotonic() - t0) * 1000),
        hallucination_guard_hits=len(mismatch_logs),
        actor=actor,
    )
    _commit_silent(db)

    return PreviewResult(
        ok=True, outcome="ok", candidate=candidate, mode=conflict.mode,
        existing=conflict.existing_dict, appointments_count=appt_count,
        warnings=warnings, safe_to_execute=True, preview_token=token,
        preview_token_exp=exp, message="",
    )


# ──────────── execute() — confirm + 토큰 검증 + DB upsert ────────────

def _toctou_recheck(db: Session, payload: dict) -> Optional[str]:
    """트랜잭션 안에서 재조회. spec § 6.3 표.

    - 치료사 active 비활성화됐으면 therapist_changed
    - 기존 휴무 상태가 토큰 발급 시점과 다르면 conflict_changed
    - 이상 없으면 None
    """
    from ...models import models as _m

    emp = db.query(_m.Employee).filter(_m.Employee.id == payload["employee_id"]).first()
    if emp is None or not emp.active:
        return "therapist_changed"

    existing = db.query(_m.EmployeeLeave).filter(
        _m.EmployeeLeave.employee_id == payload["employee_id"],
        _m.EmployeeLeave.leave_date == payload["leave_date"],
    ).first()
    existing_id_now = existing.id if existing else None
    existing_id_at_preview = payload.get("existing_id")

    if existing_id_now != existing_id_at_preview:
        return "conflict_changed"
    return None


def _do_upsert(db: Session, payload: dict, memo: str):
    """기존 휴무 헬퍼 _upsert_employee_leave_core 를 호출 — 단일 진실원천."""
    from ...models import schemas as _s
    from ...routers.api import _upsert_employee_leave_core

    p = _s.EmployeeLeaveIn(
        employee_id=payload["employee_id"],
        leave_date=payload["leave_date"],
        leave_type=payload["leave_type"],
        leave_kind=payload["leave_kind"],
        memo=memo or "",
    )
    return _upsert_employee_leave_core(db, p)


def execute(db: Session, *, preview_token: str, confirm: bool,
            overwrite_acknowledged: bool, memo: str,
            actor: str = "admin",
            now: Optional[datetime] = None) -> ExecuteResult:
    """confirm + 토큰 검증 + TOCTOU 재조회 + upsert + AuditLog.

    LLM 호출 없음. provider/model 필드는 빈 문자열로 기록.
    """
    t0 = monotonic()
    now = now or _now_provider()
    now_unix = int(now.timestamp())

    def _exec_log(outcome: str, error_detail: str = "") -> None:
        ai_log.log_ai_usage(
            db, feature="action_leave_execute",
            provider="", model="",
            outcome=outcome, actor=actor,
            latency_ms=int((monotonic() - t0) * 1000),
            error_detail=_safe_detail(error_detail or _msg(outcome)),
        )

    def _fail(outcome: str) -> ExecuteResult:
        _exec_log(outcome)
        _commit_silent(db)
        return ExecuteResult(ok=False, outcome=outcome, leave_id=None,
                             mode=None, message=_msg(outcome))

    # [가드 13a]
    if confirm is not True:
        return _fail("not_confirmed")

    # [가드 11]
    try:
        payload = _verify_token(preview_token, now_unix=now_unix)
    except _InvalidToken as e:
        return _fail(e.outcome)

    # [가드 13b]
    if payload.get("mode") == "overwrite" and not overwrite_acknowledged:
        return _fail("overwrite_not_acknowledged")

    # [가드 12] TOCTOU + upsert
    try:
        rc = _toctou_recheck(db, payload)
        if rc:
            return _fail(rc)

        obj = _do_upsert(db, payload, memo or "")

        from ...models import models as _m
        audit_detail = (
            f"mode={payload['mode']} "
            f"employee_id={payload['employee_id']} "
            f"date={payload['leave_date']} "
            f"type={payload['leave_type']} "
            f"kind={payload['leave_kind']}"
        )
        db.add(_m.AuditLog(
            actor=(actor or "admin")[:50],
            action="ai.leave.create"[:50],
            entity_id=(obj.id or "")[:32],
            detail=audit_detail[:500],
        ))

        ai_log.log_ai_usage(
            db, feature="action_leave_execute",
            provider="", model="", outcome="ok", actor=actor,
            latency_ms=int((monotonic() - t0) * 1000),
        )
        db.commit()
        return ExecuteResult(ok=True, outcome="ok", leave_id=obj.id,
                             mode=payload["mode"], message="휴무가 등록되었습니다")
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        # rollback 후 별도 세션처럼 silent 로그
        _exec_log("db_error", "execute_db_exception")
        _commit_silent(db)
        return ExecuteResult(ok=False, outcome="db_error", leave_id=None,
                             mode=None, message=_msg("db_error"))
