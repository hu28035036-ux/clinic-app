"""자연어 날짜 해석기 (세션 13).

[docs/specs/04_ai_action_leave.md] § 3 표를 코드 결정론으로 옮긴 모듈.
DB / LLM 의존성 없음. 시간대 Asia/Seoul 고정.

해석 규칙 요약:
  - "오늘" / "내일" / "모레" → 상대일
  - "M월D일" → current_year + M + D (연도 추론 안 함)
  - "D일" (월 토큰 미선행) → current_month, D ≥ today.day 면 ok + assumption,
                              D < today.day 면 ambiguous_date (다음달 자동 보정 X)
  - "다음달 D일" / "지난달 D일" → 명시 월 ± 1
  - "이번주/다음주 X요일" → ISO 주 (월요일 시작)
  - "YYYY-MM-DD" → 그대로
  - 모호 키워드 ("말일쯤", "이번주 중", "다음에", "곧", "다음주"(요일無)) → ambiguous_date
  - 해당 월에 없는 날짜 (예: 2월30일) / 윤년 위반 → invalid_date
  - 과거 90일 이전 / 미래 365일 초과 → out_of_range_date
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:
    # Windows + Python 3.9~3.12 에 tzdata 가 없을 때의 fallback.
    # 한국은 DST 가 없으므로 고정 +09:00 가 항상 정답.
    KST = timezone(timedelta(hours=9))
PAST_LIMIT_DAYS = 90
FUTURE_LIMIT_DAYS = 365

_DOW_MAP = {
    "월": 1, "화": 2, "수": 3, "목": 4, "금": 5, "토": 6, "일": 7,
}

# 정규식 (우선순위 = 더 구체적인 패턴 먼저)
_RE_ABS_ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_RE_NEXT_WEEK_DOW = re.compile(r"다음주\s*([월화수목금토일])요일?")
_RE_THIS_WEEK_DOW = re.compile(r"이번주\s*([월화수목금토일])요일?")
_RE_NEXT_MONTH = re.compile(r"다음달\s*(\d{1,2})일")
_RE_PREV_MONTH = re.compile(r"지난달\s*(\d{1,2})일")
_RE_EXPLICIT_MD = re.compile(r"(\d{1,2})월\s*(\d{1,2})일")
_RE_DAY_ONLY = re.compile(r"(?<!\d)(\d{1,2})일")  # 앞에 숫자 없을 때만

# 모호 키워드 — 해당 토큰이 발견되면 무조건 ambiguous_date
_AMBIGUOUS_KEYWORDS = ("말일쯤", "말일 쯤", "이번주 중", "이번주중",
                       "다음에", "곧", "적당한 때", "적당한때")


@dataclass
class DateResolution:
    """resolve_date() 결과.

    resolved_date: "YYYY-MM-DD" (성공 시) 또는 None
    date_basis: 어떤 패턴으로 해석됐는지 (today | relative_day | explicit_md |
                day_only | next_month | prev_month | this_week_dow | next_week_dow |
                absolute_iso | none)
    assumption: 한국어 안내 문자열 (일자만 / 상대 / 요일 케이스에서 채움)
    outcome: ok | ambiguous_date | invalid_date | out_of_range_date
    """
    resolved_date: Optional[str]
    date_basis: str
    assumption: Optional[str]
    outcome: str


def _now_kst(now: Optional[datetime] = None) -> datetime:
    if now is not None:
        return now
    return datetime.now(KST)


def _within_range(d: date, today: date) -> bool:
    delta = (d - today).days
    return -PAST_LIMIT_DAYS <= delta <= FUTURE_LIMIT_DAYS


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    m0 = (month - 1) + delta
    y = year + m0 // 12
    m = (m0 % 12) + 1
    return y, m


def _try_make_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _check_range(d: date, today: date, basis: str,
                 raw: str, *, base_assumption: Optional[str] = None) -> DateResolution:
    if not _within_range(d, today):
        delta = (d - today).days
        if delta < -PAST_LIMIT_DAYS:
            msg = "과거 90일 이전은 등록할 수 없습니다"
        else:
            msg = "미래 365일을 넘는 날짜는 등록할 수 없습니다"
        return DateResolution(None, basis, msg, "out_of_range_date")
    return DateResolution(d.isoformat(), basis, base_assumption, "ok")


def resolve_date(text: str, *, now: Optional[datetime] = None) -> DateResolution:
    """자연어 → DateResolution.

    text: 사용자 입력 전체 (날짜 토큰만이 아니어도 됨 — 정규식이 알아서 추출)
    now: 테스트에서 시간 고정용. None 이면 현재 KST.
    """
    if not text:
        return DateResolution(None, "none",
                              "날짜가 모호합니다 — 구체적인 날짜를 입력해주세요",
                              "ambiguous_date")

    base = _now_kst(now)
    today = base.date()

    # 1) 절대 ISO (YYYY-MM-DD)
    m = _RE_ABS_ISO.search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        dt = _try_make_date(y, mo, d)
        if dt is None:
            return DateResolution(None, "absolute_iso",
                                  "유효하지 않은 날짜입니다", "invalid_date")
        return _check_range(dt, today, "absolute_iso", m.group(0))

    # 2) 다음주 X요일
    m = _RE_NEXT_WEEK_DOW.search(text)
    if m:
        dow = _DOW_MAP[m.group(1)]
        # 이번주 월요일 (ISO weekday=1) 부터 dow 까지의 오프셋, 그리고 +7일
        # ISO weekday: today.isoweekday() (월=1..일=7)
        days_to_this_mon = today.isoweekday() - 1
        next_week_mon = today - timedelta(days=days_to_this_mon) + timedelta(days=7)
        target = next_week_mon + timedelta(days=dow - 1)
        return _check_range(target, today, "next_week_dow", m.group(0),
                            base_assumption=f"다음주 {m.group(1)}요일 = {target.isoformat()}")

    # 3) 이번주 X요일
    m = _RE_THIS_WEEK_DOW.search(text)
    if m:
        dow = _DOW_MAP[m.group(1)]
        days_to_this_mon = today.isoweekday() - 1
        this_week_mon = today - timedelta(days=days_to_this_mon)
        target = this_week_mon + timedelta(days=dow - 1)
        return _check_range(target, today, "this_week_dow", m.group(0),
                            base_assumption=f"이번주 {m.group(1)}요일 = {target.isoformat()}")

    # 4) 다음달 D일
    m = _RE_NEXT_MONTH.search(text)
    if m:
        d_val = int(m.group(1))
        y, mo = _add_months(today.year, today.month, 1)
        dt = _try_make_date(y, mo, d_val)
        if dt is None:
            return DateResolution(None, "next_month",
                                  "해당 월에 없는 날짜입니다", "invalid_date")
        return _check_range(dt, today, "next_month", m.group(0),
                            base_assumption=f"다음달 = {y:04d}-{mo:02d} 기준 {dt.isoformat()}")

    # 5) 지난달 D일
    m = _RE_PREV_MONTH.search(text)
    if m:
        d_val = int(m.group(1))
        y, mo = _add_months(today.year, today.month, -1)
        dt = _try_make_date(y, mo, d_val)
        if dt is None:
            return DateResolution(None, "prev_month",
                                  "해당 월에 없는 날짜입니다", "invalid_date")
        return _check_range(dt, today, "prev_month", m.group(0),
                            base_assumption=f"지난달 = {y:04d}-{mo:02d} 기준 {dt.isoformat()}")

    # 6) M월D일
    m = _RE_EXPLICIT_MD.search(text)
    if m:
        mo, d_val = int(m.group(1)), int(m.group(2))
        if mo < 1 or mo > 12:
            return DateResolution(None, "explicit_md",
                                  "유효하지 않은 날짜입니다", "invalid_date")
        dt = _try_make_date(today.year, mo, d_val)
        if dt is None:
            return DateResolution(None, "explicit_md",
                                  "해당 월에 없는 날짜입니다", "invalid_date")
        return _check_range(dt, today, "explicit_md", m.group(0))

    # 7) D일 (월 토큰 미선행). 단, 모호 키워드가 먼저 나오면 차단.
    if any(k in text for k in _AMBIGUOUS_KEYWORDS):
        return DateResolution(None, "none",
                              "날짜가 모호합니다 — 구체적인 날짜를 입력해주세요",
                              "ambiguous_date")
    # "다음주" 가 들어있는데 위의 next_week_dow 매칭에 실패했으면 → 모호
    if "다음주" in text and not _RE_NEXT_WEEK_DOW.search(text):
        return DateResolution(None, "none",
                              "날짜가 모호합니다 — 구체적인 날짜를 입력해주세요",
                              "ambiguous_date")

    m = _RE_DAY_ONLY.search(text)
    if m:
        d_val = int(m.group(1))
        if d_val < 1 or d_val > 31:
            return DateResolution(None, "day_only",
                                  "유효하지 않은 날짜입니다", "invalid_date")
        # D < today.day 면 ambiguous_date (다음달 자동 보정 안 함)
        if d_val < today.day:
            return DateResolution(None, "day_only",
                                  "날짜가 모호합니다 — 구체적인 날짜를 입력해주세요",
                                  "ambiguous_date")
        dt = _try_make_date(today.year, today.month, d_val)
        if dt is None:
            return DateResolution(None, "day_only",
                                  "해당 월에 없는 날짜입니다", "invalid_date")
        return _check_range(dt, today, "day_only", m.group(0),
                            base_assumption=f"월이 생략되어 현재 월 기준 {dt.isoformat()} 로 해석했습니다")

    # 8) 오늘 / 내일 / 모레
    if "오늘" in text:
        return _check_range(today, today, "today", "오늘")
    if "내일" in text:
        target = today + timedelta(days=1)
        return _check_range(target, today, "relative_day", "내일",
                            base_assumption=f"내일 = {target.isoformat()} 로 해석했습니다")
    if "모레" in text:
        target = today + timedelta(days=2)
        return _check_range(target, today, "relative_day", "모레",
                            base_assumption=f"모레 = {target.isoformat()} 로 해석했습니다")

    return DateResolution(None, "none",
                          "날짜가 모호합니다 — 구체적인 날짜를 입력해주세요",
                          "ambiguous_date")
