"""Tests for Step 7 — Add Expense, from .claude/specs/07-add-expense.md."""
from database.db import get_db
from database.queries import insert_expense


# ------------------------------------------------------------------ #
# Unit tests — insert_expense                                         #
# ------------------------------------------------------------------ #

def test_insert_expense_creates_row(new_user_id):
    insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (new_user_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_null_description(new_user_id):
    insert_expense(new_user_id, 20.0, "Bills", "2026-03-20", None)

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (new_user_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["description"] is None


# ------------------------------------------------------------------ #
# Route tests — GET /expenses/add                                     #
# ------------------------------------------------------------------ #

def test_get_add_expense_unauthenticated_redirects(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_add_expense_authenticated(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/expenses/add")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "<select" in body
    assert '<form method="POST" action="/expenses/add">' in body
    for category in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
        assert category in body


# ------------------------------------------------------------------ #
# Route tests — POST /expenses/add                                    #
# ------------------------------------------------------------------ #

def test_post_add_expense_unauthenticated_redirects(client):
    response = client.post("/expenses/add", data={
        "amount": "50.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch",
    })
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_add_expense_valid_data(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.post("/expenses/add", data={
        "amount": "50.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch",
    })
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (new_user_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_post_add_expense_missing_amount(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post("/expenses/add", data={
        "amount": "",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_add_expense_zero_amount(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_add_expense_non_numeric_amount(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post("/expenses/add", data={
        "amount": "abc",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_add_expense_invalid_category(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post("/expenses/add", data={
        "amount": "50.0",
        "category": "NotACategory",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_add_expense_invalid_date(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post("/expenses/add", data={
        "amount": "50.0",
        "category": "Food",
        "date": "not-a-date",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_add_expense_no_description(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.post("/expenses/add", data={
        "amount": "15.0",
        "category": "Shopping",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (new_user_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["description"] is None
