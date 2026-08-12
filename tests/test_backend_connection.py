"""Tests for Step 5 — profile page backend routes."""
import pytest

from database.db import get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

# Fixtures used below (`client`, `seeded_user_id`, `new_user_id`) come from tests/conftest.py


def test_get_recent_transactions_seed_user(seeded_user_id):
    result = get_recent_transactions(seeded_user_id)

    conn = get_db()
    try:
        expected_descriptions = [
            row["description"]
            for row in conn.execute(
                "SELECT description FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC",
                (seeded_user_id,),
            ).fetchall()
        ]
    finally:
        conn.close()

    assert [tx["description"] for tx in result] == expected_descriptions
    assert len(result) == len(expected_descriptions)
    for tx in result:
        assert set(tx.keys()) == {"date", "description", "category", "amount"}


def test_get_recent_transactions_new_user(new_user_id):
    assert get_recent_transactions(new_user_id) == []


def test_get_summary_stats_seed_user(seeded_user_id):
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (seeded_user_id,),
        ).fetchone()
        top = conn.execute(
            "SELECT category, SUM(amount) AS cat_total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY cat_total DESC LIMIT 1",
            (seeded_user_id,),
        ).fetchone()
    finally:
        conn.close()

    result = get_summary_stats(seeded_user_id)
    assert result["total_spent"] == pytest.approx(totals["total"])
    assert result["transaction_count"] == totals["cnt"]
    assert result["top_category"] == top["category"]


def test_get_summary_stats_new_user(new_user_id):
    assert get_summary_stats(new_user_id) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_get_category_breakdown_seed_user(seeded_user_id):
    result = get_category_breakdown(seeded_user_id)

    assert len(result) > 0
    assert all(result[i]["amount"] >= result[i + 1]["amount"] for i in range(len(result) - 1))
    assert all(isinstance(row["pct"], int) for row in result)
    assert sum(row["pct"] for row in result) == 100


def test_get_category_breakdown_new_user(new_user_id):
    assert get_category_breakdown(new_user_id) == []


def test_get_user_by_id_valid(seeded_user_id):
    result = get_user_by_id(seeded_user_id)
    assert result["name"] == "Demo User"
    assert result["email"] == "demo@spendly.com"
    assert result["member_since"]


def test_get_user_by_id_missing():
    assert get_user_by_id(999999) is None


def test_profile_unauthenticated_redirects_to_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_seed_user(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body

    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (seeded_user_id,),
        ).fetchone()
        categories = conn.execute(
            "SELECT DISTINCT category FROM expenses WHERE user_id = ?", (seeded_user_id,)
        ).fetchall()
    finally:
        conn.close()

    assert f"{totals['total']:,.2f}" in body
    assert str(totals["cnt"]) in body
    for row in categories:
        assert row["category"] in body


def test_profile_authenticated_new_user_zero_state(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.get("/profile")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "₹0.00" in body
