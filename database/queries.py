"""Pure DB query helpers for expenses and the profile page. No Flask imports here."""
from datetime import datetime

from database.db import get_db


def _date_filter_clause(start_date, end_date):
    """(sql_fragment, params) for optional inclusive date filtering.
    Only applied when both bounds are given — preserves all-time behavior otherwise."""
    if start_date is not None and end_date is not None:
        return " AND date BETWEEN ? AND ?", (start_date, end_date)
    return "", ()


def insert_expense(user_id, amount, category, expense_date, description):
    """Insert a new expense row. Returns the new row's id."""
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    """Return a single expense row if it belongs to user_id, else None."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
    finally:
        conn.close()
    return row


def update_expense(expense_id, user_id, amount, category, expense_date, description):
    """Update an expense row, scoped to id AND user_id. No-ops if not owned."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, expense_date, description, expense_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


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


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """Return list of dicts (date, description, category, amount), newest first."""
    date_sql, date_params = _date_filter_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + date_sql + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *date_params, limit),
        ).fetchall()
    finally:
        conn.close()

    transactions = []
    for row in rows:
        d = datetime.strptime(row["date"], "%Y-%m-%d")
        transactions.append({
            "id": row["id"],
            "date": f"{d.strftime('%b')} {d.day}, {d.year}",
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        })
    return transactions


def get_summary_stats(user_id, start_date=None, end_date=None):
    """Return dict with total_spent (raw number), transaction_count, top_category."""
    date_sql, date_params = _date_filter_clause(start_date, end_date)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ?" + date_sql,
            (user_id, *date_params),
        ).fetchone()

        if totals["cnt"] == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

        top = conn.execute(
            "SELECT category, SUM(amount) AS cat_total FROM expenses "
            "WHERE user_id = ?" + date_sql + " GROUP BY category ORDER BY cat_total DESC LIMIT 1",
            (user_id, *date_params),
        ).fetchone()
    finally:
        conn.close()

    return {
        "total_spent": totals["total"],
        "transaction_count": totals["cnt"],
        "top_category": top["category"],
    }


def get_category_breakdown(user_id, start_date=None, end_date=None):
    """Return list of dicts (name, amount, pct), ordered by amount desc, pct sums to 100."""
    date_sql, date_params = _date_filter_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + date_sql + " GROUP BY category ORDER BY total DESC",
            (user_id, *date_params),
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
