"""026 - backfill settlement records whose price snapshots were saved as zero."""

MIGRATION_ID = 26
DESCRIPTION = "backfill zero settlement price snapshots from current treatment settings"


def _incentive_snapshot(row):
    amount = row["incentive_amount"]
    pct = row["incentive_pct"]
    if amount is not None and int(amount or 0) > 0:
        return "fixed", int(amount)
    if pct is not None and float(pct or 0) > 0:
        return "percent", float(pct)
    return "none", 0


def _calculate_incentive(price: int, rule: str, value, quantity: int) -> int:
    qty = max(0, int(quantity or 0))
    if qty <= 0:
        return 0
    if rule == "fixed":
        return int(value or 0) * qty
    if rule == "percent":
        return round(int(price or 0) * float(value or 0) / 100 * qty)
    return 0


def up(conn):
    conn.row_factory = None
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT
            sr.id,
            sr.quantity,
            t.code,
            t.name,
            t.short,
            t.price,
            t.incentive_pct,
            t.incentive_amount
        FROM settlement_records sr
        JOIN treatments t ON t.id = sr.treatment_id
        WHERE COALESCE(sr.price_snapshot, 0) <= 0
          AND COALESCE(t.price, 0) > 0
        """
    ).fetchall()
    for row in rows:
        data = {
            "id": row[0],
            "quantity": row[1],
            "code": row[2],
            "name": row[3],
            "short": row[4],
            "price": int(row[5] or 0),
            "incentive_pct": row[6],
            "incentive_amount": row[7],
        }
        rule, value = _incentive_snapshot(data)
        incentive = _calculate_incentive(data["price"], rule, value, data["quantity"])
        cur.execute(
            """
            UPDATE settlement_records
               SET treatment_code = COALESCE(NULLIF(treatment_code, ''), ?),
                   treatment_code_snapshot = COALESCE(NULLIF(treatment_code_snapshot, ''), ?),
                   treatment_name_snapshot = COALESCE(NULLIF(treatment_name_snapshot, ''), ?),
                   treatment_short_snapshot = COALESCE(NULLIF(treatment_short_snapshot, ''), ?),
                   price_snapshot = ?,
                   incentive_type_snapshot = ?,
                   incentive_value_snapshot = ?,
                   incentive_amount = ?,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
            """,
            (
                data["code"] or "",
                data["code"] or "",
                data["name"] or "",
                data["short"] or "",
                data["price"],
                rule,
                value,
                incentive,
                data["id"],
            ),
        )
    conn.commit()
