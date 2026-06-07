from decimal import Decimal, ROUND_HALF_UP


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
