from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def settlement_lock_before(today: date | None = None) -> date:
    """정산 확정(잠금) 경계 — performed_on 이 이 날짜보다 **이전(<)** 이면 확정.

    확정된 정산은 집계 자동 반영이 수량·금액을 다시 계산하지 않는다
    (이미 지급한 급여의 근거를 그대로 보존하기 위함).

    규칙: 매월 1일 기준으로 '2달 전' 달부터 확정, '1달 전' 달은 계속 수정 가능.
      예) 7/16 → 경계 6/1 → 5월 이하 확정 / 6월·7월 수정 가능
          8/1  → 경계 7/1 → 6월이 자동으로 확정됨
    즉 경계 = (이번 달 1일) - 1개월. 별도 배치 없이 날짜만으로 자동 확정된다.
    """
    today = today or date.today()
    first = today.replace(day=1)  # 이번 달 1일
    if first.month == 1:
        return date(first.year - 1, 12, 1)
    return date(first.year, first.month - 1, 1)


def _as_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception as exc:
        raise ValueError("invalid numeric value") from exc


def _round_won(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def incentive_snapshot_for_treatment(treatment) -> tuple[str, float]:
    amount = getattr(treatment, "incentive_amount", None)
    if amount is not None and amount > 0:
        return "fixed", float(amount)
    pct = getattr(treatment, "incentive_pct", None)
    if pct is not None and pct > 0:
        return "percent", float(pct)
    return "none", 0.0


def calculate_incentive_amount(
    price,
    incentive_type: str,
    incentive_value,
    quantity,
) -> int:
    try:
        qty = int(quantity)
    except Exception as exc:
        raise ValueError("quantity must be a positive integer") from exc
    if qty <= 0:
        raise ValueError("quantity must be a positive integer")

    rule = (incentive_type or "none").strip().lower()
    value = _as_decimal(incentive_value)
    if rule == "fixed":
        return _round_won(value * qty)
    if rule == "percent":
        return _round_won(_as_decimal(price) * value / Decimal("100") * qty)
    if rule == "none":
        return 0
    raise ValueError("unknown incentive type")
