"""ai_parser — 사용자 자연어 명령 → 구조화 JSON (Phase 2).

역할:
- 한국어 자연어 명령 문자열을 ParsedCommand 로 변환.
- intent / patient_name / chart_number / date_text / time_text / therapist_name /
  treatment_text / treatment_items / memo 의 9 필드 추출 (DB 매칭 전).
- 외부 AI provider 가 있으면 호출, 없으면 정규식 fallback.
- AI 에 보내는 정보는 최소화 (환자 전체 / 생년월일 / 연락처 미전송).

주의:
- 본 모듈은 **추출만** 담당. DB 조회는 ai_resolver.py 가, 검증은 ai_validator.py 가.
- 추출이 불확실하면 None 으로 두고 caller (resolver / validator) 가 needs_clarification 처리.
- 외부 AI API 호출 실패 시 정규식 fallback 으로 우회 (기존 프로그램 보호).

cross-reference:
- 9 추출 필드 → AI_FEATURE_MASTER_PLAN.md § 6.1
- intent 10 종 → AI_FEATURE_MASTER_PLAN.md § 5
- 외부 AI API 정책 → AI_SAFETY_POLICY.md § 3

하네스: tests/test_phase02_ai_parser.py
"""

from __future__ import annotations

import re

from app.ai.ai_command_schema import (
    AiIntent,
    DataSourceState,
    ParsedCommand,
    ParserContext,
    TreatmentItem,
    TreatmentItemStatus,
)
from app.ai.ai_provider import AIProvider, MockProvider, ProviderError


# ────────────────────────────── 공개 API ──────────────────────────────


def parse_command(
    raw_text: str,
    *,
    context: ParserContext,
    provider: AIProvider | None = None,
) -> ParsedCommand:
    """자연어 명령 → ParsedCommand 변환.

    1) provider 가 주어지면 호출 시도. 실패 시 정규식 fallback.
    2) provider 가 없거나 MockProvider 면 정규식 직접 사용.
    """
    # provider 시도
    if provider is not None and not isinstance(provider, MockProvider):
        try:
            result = provider.parse_command(raw_text, context)
            # provider 가 빈 결과를 줘도 정규식 보강
            return _fill_with_regex(result, raw_text, context)
        except ProviderError:
            # 실패 시 정규식 fallback (기존 프로그램 보호)
            pass

    # 정규식 fallback (Phase 2 의 기본 동작) — context 의 DB 약어 우선 사용
    return _parse_with_regex(raw_text, context)


# ────────────────────────────── 정규식 추출 ──────────────────────────────


def _parse_with_regex(raw_text: str, context: ParserContext | None = None) -> ParsedCommand:
    """한국어 자연어 명령에서 9 필드 추출.

    Phase 2 는 정규식 기반 — 단순한 명령은 정확, 복잡한 명령은 needs_clarification.
    context.treatment_aliases / context.treatment_names 가 주어지면 DB 의 *실제 약어* 를
    우선 사용해 토큰 추출. 없으면 하드코딩 정규식 fallback (후방 호환).
    """
    cmd = ParsedCommand(raw_text=raw_text)
    aliases = list(context.treatment_aliases) if context else []
    names = list(context.treatment_names) if context else []

    cmd.intent = _extract_intent(raw_text)
    cmd.chart_number = _extract_chart_number(raw_text)
    cmd.date_text = _extract_date_text(raw_text)
    cmd.time_text = _extract_time_text(raw_text)
    cmd.therapist_name = _extract_therapist_name(raw_text)
    cmd.patient_name = _extract_patient_name(raw_text)
    cmd.treatment_text = _extract_treatment_text(raw_text, aliases=aliases, names=names)
    cmd.treatment_items = _extract_treatment_items(cmd.treatment_text or "")
    cmd.memo = _extract_memo(raw_text)

    return cmd


def _fill_with_regex(
    parsed: ParsedCommand, raw_text: str, context: ParserContext | None = None
) -> ParsedCommand:
    """provider 결과의 빈 필드만 정규식으로 보강."""
    fallback = _parse_with_regex(raw_text, context)
    if not parsed.intent:
        parsed.intent = fallback.intent
    if not parsed.patient_name:
        parsed.patient_name = fallback.patient_name
    if not parsed.chart_number:
        parsed.chart_number = fallback.chart_number
    if not parsed.date_text:
        parsed.date_text = fallback.date_text
    if not parsed.time_text:
        parsed.time_text = fallback.time_text
    if not parsed.therapist_name:
        parsed.therapist_name = fallback.therapist_name
    if not parsed.treatment_text:
        parsed.treatment_text = fallback.treatment_text
    if not parsed.treatment_items:
        parsed.treatment_items = fallback.treatment_items
    if not parsed.memo:
        parsed.memo = fallback.memo
    if not parsed.raw_text:
        parsed.raw_text = raw_text
    return parsed


# ────────────────────────────── 필드별 추출 (단일 책임) ──────────────────────────────


_INTENT_KEYWORDS: dict[AiIntent, tuple[str, ...]] = {
    AiIntent.UPDATE_APPOINTMENT: ("변경", "수정", "옮기"),
    AiIntent.CANCEL_APPOINTMENT: ("취소", "삭제", "지우"),
    AiIntent.CREATE_LEAVE: ("휴무", "반차", "연차", "오프"),
    AiIntent.PREPARE_SMS: ("문자", "SMS"),
    AiIntent.SUMMARIZE_TODAY: ("오늘 예약 요약", "오늘 요약", "오늘 예약 정리"),
    AiIntent.SUMMARIZE_TOMORROW: ("내일 예약 요약", "내일 요약", "내일 예약 정리"),
    AiIntent.ANALYZE_STATS: ("통계", "분석", "완료율"),
    AiIntent.DATA_QUALITY_CHECK: ("중복 의심", "누락 환자", "데이터 품질"),
    AiIntent.OPS_ASSISTANT: ("빈 시간", "과부하", "빈 슬롯"),
    AiIntent.CREATE_APPOINTMENT: ("예약",),
}


def _extract_intent(text: str) -> AiIntent | None:
    """우선순위 순으로 키워드 매칭. 모호하면 가장 구체적인 것 선택."""
    # 변경 / 취소 / 휴무 가 "예약" 보다 우선 (예약 변경 / 예약 취소)
    for intent, keywords in _INTENT_KEYWORDS.items():
        if intent == AiIntent.CREATE_APPOINTMENT:
            continue
        for kw in keywords:
            if kw in text:
                return intent
    # 마지막으로 "예약"
    if "예약" in text:
        return AiIntent.CREATE_APPOINTMENT
    return None


def _extract_chart_number(text: str) -> str | None:
    """차트번호 — "차트번호 N", "N번 환자", "차트 N", "차트번호: N"."""
    patterns = [
        r"차트번호\s*[:：]?\s*(\d+)",
        r"차트\s*[:：]?\s*(\d+)",
        r"(\d{4,})\s*번\s*환자",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def _extract_date_text(text: str) -> str | None:
    """날짜 텍스트 — 오늘 / 내일 / 모레 / 이번주 X / 다음주 X / M월 D일 / D일."""
    # 명확한 키워드 (긴 것 우선)
    for kw in ("이번 주 ", "이번주 ", "다음 주 ", "다음주 ", "오늘", "내일", "모레"):
        if kw.strip() in text:
            # 요일 패턴이면 끝까지 포함
            if "주" in kw:
                m = re.search(rf"({re.escape(kw.strip())}\s*[월화수목금토일](?:요일)?)", text)
                if m:
                    return m.group(1).strip()
                continue
            return kw.strip()

    # M월 D일
    m = re.search(r"(\d{1,2}\s*월\s*\d{1,2}\s*일)", text)
    if m:
        return m.group(1).replace(" ", "")

    # D일 (단독, 월 / 시 키워드와 충돌 안 함)
    # "30일 9시" 같이 "일" 뒤에 시간이 오는 패턴 허용
    m = re.search(r"(?<![월\d])(\d{1,2})\s*일(?!요)", text)
    if m:
        return m.group(1) + "일"

    return None


def _extract_time_text(text: str) -> str | None:
    """시간 텍스트 — 오전/오후 N시 / N시 M분 / HH:MM."""
    patterns = [
        r"((?:오전|오후|am|pm|AM|PM)\s*\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?)",
        r"(\d{1,2}:\d{2})",
        r"(\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).replace(" ", "")
    return None


def _extract_therapist_name(text: str) -> str | None:
    """치료사명 — "X치료사" / "X 치료사" (X 는 1~4 글자 한글 성)."""
    m = re.search(r"([가-힣]{1,4})\s*치료사", text)
    if m:
        return m.group(1) + "치료사"
    # 의사
    m = re.search(r"([가-힣]{1,4})\s*의사", text)
    if m:
        return m.group(1) + "의사"
    return None


def _extract_patient_name(text: str) -> str | None:
    """환자명 — 한글 2~4자 + (선택) "환자" / 공백 / 차트번호 직전.

    주의: 치료사명, 의사명, 치료항목 약어와 충돌하지 않도록 우선 제거 후 추출.
    Phase 6 통합 하네스에서 발견: "차트번호 12345 ... 도수30 예약" 처럼 환자명
    미입력 + 치료항목이 한글로 시작하는 경우 fallback 정규식이 "도수" 를 환자명으로
    오인했음. 치료항목 키워드를 사전 제거해 false positive 차단.
    """
    # 치료사 / 의사 / 차트번호 / 시간 / 날짜 키워드 제거
    clean = text
    clean = re.sub(r"[가-힣]{1,4}\s*(치료사|의사)", "", clean)
    clean = re.sub(r"차트번호\s*[:：]?\s*\d+", "", clean)
    clean = re.sub(r"\d+\s*번\s*환자", "", clean)
    clean = re.sub(r"\d{1,2}\s*월\s*\d{1,2}\s*일", "", clean)
    clean = re.sub(r"\d{1,2}\s*일", "", clean)
    clean = re.sub(r"\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?", "", clean)
    clean = re.sub(r"(오전|오후)", "", clean)
    # 치료항목 키워드 제거 (Phase 6 보강) — 명령어 / 메모 / 단일 약어 토큰
    clean = re.sub(r"도수치료\s*\d*\s*분?", "", clean)
    clean = re.sub(r"도수\s*\d+\s*분?", "", clean)
    clean = re.sub(r"도\s*\d+", "", clean)
    clean = re.sub(r"체외(?:충격파)?", "", clean)
    clean = re.sub(r"충격파", "", clean)
    clean = re.sub(r"(?i)eswt", "", clean)
    clean = re.sub(r"운동", "", clean)
    clean = re.sub(r"물리", "", clean)
    clean = re.sub(r"주사", "", clean)
    clean = re.sub(r"(?:^|\s)[주충](?=\s|$)", " ", clean)
    clean = re.sub(r"\b예약\b", "", clean)
    clean = re.sub(r"메모\s*[:：].*$", "", clean)

    # "X환자" 또는 한글 2~4자 + 공백 + 시간/날짜/명령 키워드
    m = re.search(r"^\s*([가-힣]{2,4})(?:\s|환자|님)", clean)
    if m:
        return m.group(1)

    # 첫 한글 단어
    m = re.search(r"([가-힣]{2,4})", clean)
    if m:
        return m.group(1)
    return None


def _extract_treatment_text(
    text: str,
    *,
    aliases: list[str] | None = None,
    names: list[str] | None = None,
) -> str | None:
    """치료항목 텍스트 추출.

    우선순위:
    1) DB 의 약어 / 풀네임 (context 의 aliases + names) — 문자열 그대로 검색.
    2) 정규식 fallback — context 가 비어있을 때만 (후방 호환).

    DB 의존이 없는 *순수 추출* 이라 매칭은 resolver 가 다시 처리.
    """
    seen: list[str] = []

    # 1) DB 약어 / 이름 우선 검색 (긴 것 우선 — 짧은 것이 부분 매칭으로 가려지지 않게)
    db_terms: list[str] = []
    for t in (aliases or []):
        if t and t not in db_terms:
            db_terms.append(t)
    for t in (names or []):
        if t and t not in db_terms:
            db_terms.append(t)
    db_terms.sort(key=len, reverse=True)

    # 사용된 위치 기록 — 중복 매칭 방지용
    consumed_spans: list[tuple[int, int]] = []

    def _conflicts(start: int, end: int) -> bool:
        return any(not (end <= s or e <= start) for s, e in consumed_spans)

    for term in db_terms:
        # 단일 한글 글자 (예: "주", "충") 는 단어 경계 강제 — 공백 / 시작 / 끝
        is_short = len(term) == 1
        if is_short:
            pattern = rf"(?:^|\s)({re.escape(term)})(?=\s|$|[.,!?])"
        else:
            pattern = re.escape(term)
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            # 그룹 1 이 있으면 그것, 아니면 0
            try:
                span = m.span(1) if m.groups() else m.span(0)
                tok = m.group(1) if m.groups() else m.group(0)
            except IndexError:
                span = m.span(0)
                tok = m.group(0)
            if _conflicts(*span):
                continue
            consumed_spans.append(span)
            normalized = tok.strip()
            if normalized and normalized not in seen:
                seen.append(normalized)

    # 2) 정규식 fallback — DB 약어 미주입 시 (후방 호환). 이미 매칭된 위치는 제외.
    if not (aliases or names):
        # 알려진 키워드 / 약어 (하드코딩 — DB 약어 없을 때만 사용)
        for m in re.finditer(
            r"(도수\s*\d+|도\d+|체외(?:충격파)?|충격파|ESWT|eswt|주사|운동|물리|도수치료\s*\d+\s*분)",
            text,
            flags=re.IGNORECASE,
        ):
            tok = m.group(0).replace(" ", "")
            if tok and tok not in seen:
                seen.append(tok)
        # 단일 글자 약어 — 단어 경계
        for m in re.finditer(r"(?:^|\s)([주충])(?=\s|$|[.,!?])", text):
            tok = m.group(1)
            if tok and tok not in seen:
                seen.append(tok)

    return " ".join(seen) if seen else None


def _extract_treatment_items(treatment_text: str) -> list[TreatmentItem]:
    """treatment_text 를 TreatmentItem 목록으로 분리. DB 매칭은 resolver 가."""
    if not treatment_text:
        return []
    tokens = [t for t in re.split(r"[\s,]+", treatment_text.strip()) if t]
    return [
        TreatmentItem(
            raw_text=t,
            source=DataSourceState.AI_EXTRACTED,
            status=TreatmentItemStatus.NEEDS_CLARIFICATION,
        )
        for t in tokens
    ]


def _extract_memo(text: str) -> str | None:
    """메모 — "메모: ..." / "(...)" — Phase 2 는 단순 추출."""
    m = re.search(r"메모\s*[:：]\s*(.+?)(?:$|\n)", text)
    if m:
        return m.group(1).strip()
    return None
