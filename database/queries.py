"""Pure DB query helpers for the profile page. No Flask imports here."""
from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    """Return dict with name, email, member_since (or None if not found)."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created.strftime("%B %Y"),
    }


def get_recent_transactions(user_id, limit=10):
    """Return list of dicts (date, description, category, amount), newest first."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    transactions = []
    for row in rows:
        d = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append({
            "date": f"{d.strftime('%b')} {d.day}, {d.year}",
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        })
    return transactions


def get_summary_stats(user_id):
    """Return dict with total_spent (raw number), transaction_count, top_category."""
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if totals["cnt"] == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

        top = conn.execute(
            "SELECT category, SUM(amount) AS cat_total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY cat_total DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": totals["total"],
        "transaction_count": totals["cnt"],
        "top_category": top["category"],
    }


def get_category_breakdown(user_id):
    """Return list of dicts (name, amount, pct), ordered by amount desc, pct sums to 100."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    breakdown = [
        {"name": row["category"], "amount": row["total"], "pct": round(row["total"] / grand_total * 100)}
        for row in rows
    ]

    remainder = 100 - sum(item["pct"] for item in breakdown)
    breakdown[0]["pct"] += remainder

    return breakdown
