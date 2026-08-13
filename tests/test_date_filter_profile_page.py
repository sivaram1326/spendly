"""Tests for Step 6 — date filter for profile page, from .claude/specs/06-date-filter-profile-page.md."""
from datetime import date, timedelta

import pytest

from database.db import get_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)


def _insert_expense(user_id, amount, category, expense_date, description):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        conn.commit()
    finally:
        conn.close()


def _totals(user_id, start_date=None, end_date=None):
    """Ground-truth total/count via direct SQL, mirroring tests/test_backend_connection.py."""
    conn = get_db()
    try:
        if start_date and end_date:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt FROM expenses "
                "WHERE user_id = ? AND date BETWEEN ? AND ?",
                (user_id, start_date, end_date),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt FROM expenses "
                "WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    finally:
        conn.close()
    return row["total"], row["cnt"]


# ---------------------------------------------------------------------------
# database/queries.py — direct unit-level coverage of the new kwargs
# ---------------------------------------------------------------------------

def test_get_recent_transactions_with_date_range(new_user_id):
    _insert_expense(new_user_id, 10.0, "Food", "2020-01-01", "Legacy ledger entry")
    _insert_expense(new_user_id, 20.0, "Food", "2026-06-15", "In-window purchase")

    result = get_recent_transactions(new_user_id, start_date="2026-06-01", end_date="2026-06-30")
    assert [tx["description"] for tx in result] == ["In-window purchase"]


def test_get_recent_transactions_no_range_matches_unfiltered(new_user_id):
    _insert_expense(new_user_id, 10.0, "Food", "2020-01-01", "Legacy ledger entry")
    assert get_recent_transactions(new_user_id) == get_recent_transactions(
        new_user_id, start_date=None, end_date=None
    )


def test_get_summary_stats_with_date_range(new_user_id):
    _insert_expense(new_user_id, 10.0, "Food", "2020-01-01", "Legacy ledger entry")
    _insert_expense(new_user_id, 20.0, "Food", "2026-06-15", "In-window purchase")

    result = get_summary_stats(new_user_id, start_date="2026-06-01", end_date="2026-06-30")
    assert result["total_spent"] == pytest.approx(20.0)
    assert result["transaction_count"] == 1


def test_get_summary_stats_no_range_matches_unfiltered(new_user_id):
    _insert_expense(new_user_id, 10.0, "Food", "2020-01-01", "Legacy ledger entry")
    assert get_summary_stats(new_user_id) == get_summary_stats(
        new_user_id, start_date=None, end_date=None
    )


def test_get_category_breakdown_with_date_range(new_user_id):
    _insert_expense(new_user_id, 10.0, "Food", "2020-01-01", "Legacy ledger entry")
    _insert_expense(new_user_id, 20.0, "Transport", "2026-06-15", "In-window purchase")

    result = get_category_breakdown(new_user_id, start_date="2026-06-01", end_date="2026-06-30")
    assert len(result) == 1
    assert result[0]["name"] == "Transport"


def test_date_filter_inclusive_boundaries(new_user_id):
    _insert_expense(new_user_id, 5.0, "Food", "2026-06-01", "Start boundary purchase")
    _insert_expense(new_user_id, 5.0, "Food", "2026-06-30", "End boundary purchase")

    result = get_recent_transactions(new_user_id, start_date="2026-06-01", end_date="2026-06-30")
    assert len(result) == 2


# ---------------------------------------------------------------------------
# GET /profile — route-level coverage
# ---------------------------------------------------------------------------

def test_no_query_params_matches_unfiltered_baseline(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    total, cnt = _totals(seeded_user_id)
    assert f"{total:,.2f}" in body
    assert str(cnt) in body
    assert '<option value="all" selected>' in body


def test_this_month_excludes_older_expense(client, seeded_user_id):
    _insert_expense(seeded_user_id, 999.0, "Other", "2020-01-01", "Ancient legacy expense")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile", query_string={"range": "this_month"})
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Ancient legacy expense" not in body


def test_last_30_boundary(client, new_user_id):
    today = date.today()
    in_range = (today - timedelta(days=29)).isoformat()
    out_of_range = (today - timedelta(days=30)).isoformat()
    _insert_expense(new_user_id, 5.0, "Food", in_range, "Just-inside-30 purchase")
    _insert_expense(new_user_id, 5.0, "Food", out_of_range, "Just-outside-30 purchase")

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.get("/profile", query_string={"range": "last_30"})
    body = response.get_data(as_text=True)
    assert "Just-inside-30 purchase" in body
    assert "Just-outside-30 purchase" not in body


def test_last_90_boundary(client, new_user_id):
    today = date.today()
    in_range = (today - timedelta(days=89)).isoformat()
    out_of_range = (today - timedelta(days=90)).isoformat()
    _insert_expense(new_user_id, 5.0, "Food", in_range, "Just-inside-90 purchase")
    _insert_expense(new_user_id, 5.0, "Food", out_of_range, "Just-outside-90 purchase")

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.get("/profile", query_string={"range": "last_90"})
    body = response.get_data(as_text=True)
    assert "Just-inside-90 purchase" in body
    assert "Just-outside-90 purchase" not in body


def test_custom_range_valid_exact_window(client, new_user_id):
    _insert_expense(new_user_id, 10.0, "Food", "2026-05-01", "Pre-window purchase")
    _insert_expense(new_user_id, 20.0, "Food", "2026-06-15", "In-window purchase")
    _insert_expense(new_user_id, 30.0, "Food", "2026-07-01", "Post-window purchase")

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2026-06-01", "end_date": "2026-06-30"},
    )
    body = response.get_data(as_text=True)
    assert "In-window purchase" in body
    assert "Pre-window purchase" not in body
    assert "Post-window purchase" not in body
    assert "₹20.00" in body


def test_custom_range_missing_bound_falls_back(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(
        "/profile", query_string={"range": "custom", "start_date": "2026-06-01", "end_date": ""}
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200

    total, _cnt = _totals(seeded_user_id)
    assert f"{total:,.2f}" in body  # fell back to all-time totals
    assert "Please provide both a start and end date" in body
    assert 'value="2026-06-01"' in body  # user's input preserved
    assert '<option value="custom" selected>' in body


def test_custom_range_start_after_end_falls_back(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2026-06-30", "end_date": "2026-06-01"},
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200

    total, _cnt = _totals(seeded_user_id)
    assert f"{total:,.2f}" in body
    assert "Start date must be on or before the end date" in body
    assert 'value="2026-06-30"' in body
    assert 'value="2026-06-01"' in body


def test_custom_range_malformed_date_no_500(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "not-a-date", "end_date": "2026-06-01"},
    )
    assert response.status_code == 200
    assert "Invalid date format" in response.get_data(as_text=True)


def test_cross_section_consistency_for_filtered_window(client, new_user_id):
    _insert_expense(new_user_id, 12.0, "Food", "2026-06-05", "Grocery run")
    _insert_expense(new_user_id, 8.0, "Transport", "2026-06-10", "Bus pass")

    stats = get_summary_stats(new_user_id, start_date="2026-06-01", end_date="2026-06-30")
    breakdown = get_category_breakdown(new_user_id, start_date="2026-06-01", end_date="2026-06-30")
    assert sum(row["amount"] for row in breakdown) == pytest.approx(stats["total_spent"])

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id
    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2026-06-01", "end_date": "2026-06-30"},
    )
    body = response.get_data(as_text=True)
    assert f"{stats['total_spent']:,.2f}" in body


def test_zero_expenses_in_window_shows_zero_state(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "1999-01-01", "end_date": "1999-01-31"},
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "₹0.00" in body


def test_filter_state_persists_after_reload_preset(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile", query_string={"range": "last_30"})
    assert '<option value="last_30" selected>' in response.get_data(as_text=True)


def test_filter_state_persists_after_reload_custom(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )
    body = response.get_data(as_text=True)
    assert '<option value="custom" selected>' in body
    assert 'value="2026-01-01"' in body
    assert 'value="2026-01-31"' in body


def test_clear_filter_link_hidden_when_all(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile")
    assert "Clear filter" not in response.get_data(as_text=True)


def test_clear_filter_link_shown_when_filtered(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile", query_string={"range": "last_30"})
    assert "Clear filter" in response.get_data(as_text=True)


def test_filter_never_leaks_other_users_data(client, seeded_user_id, new_user_id):
    _insert_expense(new_user_id, 500.0, "Other", "2026-06-15", "Someone elses private expense")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2026-06-01", "end_date": "2026-06-30"},
    )
    assert "Someone elses private expense" not in response.get_data(as_text=True)
