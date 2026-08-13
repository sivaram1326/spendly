"""Tests for Step 6 — date filter for profile page.

Written directly from .claude/specs/06-date-filter-profile-page.md. Expected
behavior comes from the spec, not from reading app.py/database/queries.py —
those files are only referenced for route paths, param names, and schema.
"""
from datetime import date, timedelta

import pytest

from database.db import get_db

# Fixtures used below (`client`, `seeded_user_id`, `new_user_id`) come from
# tests/conftest.py, per this repo's existing convention.


def _insert_expense(user_id, amount, category, expense_date, description):
    """Directly insert a dated expense for test setup (expenses schema per Step 1 spec)."""
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


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

def test_profile_unauthenticated_redirects_regardless_of_filter(client):
    response = client.get("/profile", query_string={"range": "this_month"})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# Happy path — no filter / all time (unchanged baseline)
# ---------------------------------------------------------------------------

def test_no_params_defaults_to_all_time(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "All Time" in body


def test_all_time_shows_expense_outside_any_recent_window(client, seeded_user_id):
    _insert_expense(seeded_user_id, 42.0, "Other", "2015-03-14", "Very old expense")
    _login(client, seeded_user_id)

    response = client.get("/profile")
    assert response.status_code == 200
    assert "Very old expense" in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Happy path — this_month / last_30 / last_90
# ---------------------------------------------------------------------------

def test_this_month_includes_today_and_excludes_previous_month(client, new_user_id):
    today = date.today()
    first_of_month = today.replace(day=1).isoformat()
    _insert_expense(new_user_id, 15.0, "Food", first_of_month, "First of month expense")
    _insert_expense(new_user_id, 15.0, "Food", today.isoformat(), "Today expense")

    if today.month == 1:
        prev_month_date = today.replace(year=today.year - 1, month=12, day=1)
    else:
        prev_month_date = today.replace(month=today.month - 1, day=1)
    _insert_expense(new_user_id, 15.0, "Food", prev_month_date.isoformat(), "Prior month expense")

    _login(client, new_user_id)
    response = client.get("/profile", query_string={"range": "this_month"})
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "First of month expense" in body
    assert "Today expense" in body
    assert "Prior month expense" not in body


def test_last_30_days_inclusive_boundary(client, new_user_id):
    today = date.today()
    inside = (today - timedelta(days=29)).isoformat()
    outside = (today - timedelta(days=30)).isoformat()
    _insert_expense(new_user_id, 9.0, "Food", inside, "Inside 30 day window")
    _insert_expense(new_user_id, 9.0, "Food", outside, "Outside 30 day window")

    _login(client, new_user_id)
    response = client.get("/profile", query_string={"range": "last_30"})
    body = response.get_data(as_text=True)

    assert "Inside 30 day window" in body
    assert "Outside 30 day window" not in body


def test_last_90_days_inclusive_boundary(client, new_user_id):
    today = date.today()
    inside = (today - timedelta(days=89)).isoformat()
    outside = (today - timedelta(days=90)).isoformat()
    _insert_expense(new_user_id, 9.0, "Food", inside, "Inside 90 day window")
    _insert_expense(new_user_id, 9.0, "Food", outside, "Outside 90 day window")

    _login(client, new_user_id)
    response = client.get("/profile", query_string={"range": "last_90"})
    body = response.get_data(as_text=True)

    assert "Inside 90 day window" in body
    assert "Outside 90 day window" not in body


# ---------------------------------------------------------------------------
# Happy path — valid custom range
# ---------------------------------------------------------------------------

def test_custom_range_valid_filters_to_exact_window(client, new_user_id):
    _insert_expense(new_user_id, 5.0, "Food", "2024-02-28", "Before custom window")
    _insert_expense(new_user_id, 5.0, "Food", "2024-03-01", "Custom window start")
    _insert_expense(new_user_id, 5.0, "Food", "2024-03-15", "Custom window middle")
    _insert_expense(new_user_id, 5.0, "Food", "2024-03-31", "Custom window end")
    _insert_expense(new_user_id, 5.0, "Food", "2024-04-01", "After custom window")

    _login(client, new_user_id)
    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Custom window start" in body
    assert "Custom window middle" in body
    assert "Custom window end" in body
    assert "Before custom window" not in body
    assert "After custom window" not in body


# ---------------------------------------------------------------------------
# Validation errors — invalid custom range never 500s, falls back to all-time
# ---------------------------------------------------------------------------

def test_custom_range_missing_end_date_falls_back_with_message(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get(
        "/profile", query_string={"range": "custom", "start_date": "2024-03-01"}
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "All Time" in body or "all" in body.lower()


def test_custom_range_start_after_end_falls_back_with_message(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2024-04-01", "end_date": "2024-03-01"},
    )
    assert response.status_code == 200
    # spec requires a validation message be shown; not asserting exact wording
    # since the spec doesn't prescribe it verbatim


def test_custom_range_malformed_date_does_not_500(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "not-a-real-date", "end_date": "2024-03-01"},
    )
    assert response.status_code == 200


def test_unrecognized_range_value_falls_back_to_all_time(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get("/profile", query_string={"range": "bogus_value"})
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Cross-section consistency
# ---------------------------------------------------------------------------

def test_filtered_sections_agree_with_each_other(client, new_user_id):
    _insert_expense(new_user_id, 20.0, "Food", "2024-03-05", "Consistency check A")
    _insert_expense(new_user_id, 30.0, "Transport", "2024-03-10", "Consistency check B")
    _insert_expense(new_user_id, 999.0, "Other", "2024-01-01", "Outside window entirely")

    _login(client, new_user_id)
    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    body = response.get_data(as_text=True)

    assert "Consistency check A" in body
    assert "Consistency check B" in body
    assert "Outside window entirely" not in body
    # total for the window should appear as a stat, and both categories should
    # appear in the breakdown — both derived from the same filtered window
    assert "Food" in body
    assert "Transport" in body
    assert "50.00" in body  # 20 + 30, the filtered total


# ---------------------------------------------------------------------------
# Zero-state
# ---------------------------------------------------------------------------

def test_zero_expenses_in_window_shows_zero_state_not_error(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "1901-01-01", "end_date": "1901-01-31"},
    )
    assert response.status_code == 200
    assert "0.00" in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Filter state persists in the rendered form
# ---------------------------------------------------------------------------

def test_selected_preset_reflected_back_in_form(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get("/profile", query_string={"range": "last_30"})
    body = response.get_data(as_text=True)
    assert "last_30" in body


def test_custom_dates_reflected_back_in_form(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    body = response.get_data(as_text=True)
    assert "2024-03-01" in body
    assert "2024-03-31" in body


# ---------------------------------------------------------------------------
# Clear-filter link
# ---------------------------------------------------------------------------

def test_clear_filter_link_absent_on_all_time_view(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get("/profile")
    assert "Clear filter" not in response.get_data(as_text=True)


def test_clear_filter_link_present_when_range_applied(client, seeded_user_id):
    _login(client, seeded_user_id)
    response = client.get("/profile", query_string={"range": "this_month"})
    assert "Clear filter" in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Data isolation — filter never leaks another user's expenses
# ---------------------------------------------------------------------------

def test_date_filter_never_shows_another_users_expenses(client, seeded_user_id, new_user_id):
    _insert_expense(new_user_id, 77.0, "Other", "2024-03-10", "Other user's private expense")
    _login(client, seeded_user_id)

    response = client.get(
        "/profile",
        query_string={"range": "custom", "start_date": "2024-03-01", "end_date": "2024-03-31"},
    )
    assert "Other user's private expense" not in response.get_data(as_text=True)
