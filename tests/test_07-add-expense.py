"""Tests for Step 7 — Add Expense, written from .claude/specs/07-add-expense.md.

Test scope (per spec):
- insert_expense(user_id, amount, category, date, description) DB helper
- GET/POST /expenses/add auth guard, rendering, and validation contract
- Category dropdown contract (exactly the 7 fixed categories)
- Sticky form values + error message on validation failure
- Successful insert redirects to /profile and is reflected there
- "Add Expense" affordances: profile button and navbar link (shown only when logged in)
"""
from database.db import CATEGORIES, get_db
from database.queries import insert_expense


def _expense_count(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["c"]
    finally:
        conn.close()


def _latest_expense(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# insert_expense — DB helper                                          #
# ------------------------------------------------------------------ #

def test_insert_expense_inserts_row_with_given_fields(new_user_id):
    insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    row = _latest_expense(new_user_id)
    assert row is not None, "insert_expense should create a row"
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_stores_null_description_when_none(new_user_id):
    insert_expense(new_user_id, 20.0, "Bills", "2026-03-20", None)

    row = _latest_expense(new_user_id)
    assert row is not None
    assert row["description"] is None, "description=None should be stored as NULL"


# ------------------------------------------------------------------ #
# GET /expenses/add                                                   #
# ------------------------------------------------------------------ #

def test_get_add_expense_unauthenticated_redirects_to_login(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302, "unauthenticated GET must redirect, not render the form"
    assert "/login" in response.headers["Location"]


def test_get_add_expense_authenticated_returns_form(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/expenses/add")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "<form" in body
    assert "POST" in body.upper()
    assert "<select" in body, "category must be a dropdown, per spec"


def test_get_add_expense_category_dropdown_has_exactly_seven_fixed_categories(client, seeded_user_id):
    expected = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
    assert CATEGORIES == expected, (
        "Spec pins the category list to exactly these 7 values in this order; "
        "database/db.py CATEGORIES has drifted from the spec"
    )

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/expenses/add")
    body = response.get_data(as_text=True)
    for category in expected:
        assert category in body, f"category '{category}' missing from the add-expense form"


# ------------------------------------------------------------------ #
# POST /expenses/add — auth guard                                     #
# ------------------------------------------------------------------ #

def test_post_add_expense_unauthenticated_redirects_to_login(client):
    response = client.post("/expenses/add", data={
        "amount": "50.0", "category": "Food", "date": "2026-03-20", "description": "Lunch",
    })
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ------------------------------------------------------------------ #
# POST /expenses/add — happy path                                     #
# ------------------------------------------------------------------ #

def test_post_add_expense_valid_data_redirects_to_profile_and_persists(client, new_user_id):
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

    row = _latest_expense(new_user_id)
    assert row is not None
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_post_add_expense_no_description_saves_with_null_description(client, new_user_id):
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

    row = _latest_expense(new_user_id)
    assert row is not None
    assert row["description"] is None


def test_post_add_expense_new_expense_appears_on_profile_page(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    client.post("/expenses/add", data={
        "amount": "77.25",
        "category": "Health",
        "date": "2026-03-20",
        "description": "Pharmacy run",
    })

    profile_response = client.get("/profile")
    body = profile_response.get_data(as_text=True)
    assert "Pharmacy run" in body, "the newly added expense must show up in the profile transaction list"


# ------------------------------------------------------------------ #
# POST /expenses/add — validation errors                              #
# ------------------------------------------------------------------ #

def test_post_add_expense_missing_amount_rerenders_with_error_and_no_insert(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    before = _expense_count(new_user_id)
    response = client.post("/expenses/add", data={
        "amount": "",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })

    assert response.status_code == 200, "validation failure must re-render the form, not redirect"
    assert _expense_count(new_user_id) == before, "no row should be inserted on validation failure"


def test_post_add_expense_zero_amount_rerenders_with_error(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    before = _expense_count(new_user_id)
    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })

    assert response.status_code == 200
    assert _expense_count(new_user_id) == before, "amount must be strictly greater than 0"


def test_post_add_expense_negative_amount_rerenders_with_error(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    before = _expense_count(new_user_id)
    response = client.post("/expenses/add", data={
        "amount": "-5",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })

    assert response.status_code == 200
    assert _expense_count(new_user_id) == before


def test_post_add_expense_non_numeric_amount_rerenders_with_error(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    before = _expense_count(new_user_id)
    response = client.post("/expenses/add", data={
        "amount": "abc",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })

    assert response.status_code == 200
    assert _expense_count(new_user_id) == before


def test_post_add_expense_invalid_category_rerenders_with_error(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    before = _expense_count(new_user_id)
    response = client.post("/expenses/add", data={
        "amount": "50.0",
        "category": "NotARealCategory",
        "date": "2026-03-20",
        "description": "",
    })

    assert response.status_code == 200
    assert _expense_count(new_user_id) == before, "only the 7 fixed categories are valid"


def test_post_add_expense_invalid_date_rerenders_with_error(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    before = _expense_count(new_user_id)
    response = client.post("/expenses/add", data={
        "amount": "50.0",
        "category": "Food",
        "date": "not-a-real-date",
        "description": "",
    })

    assert response.status_code == 200
    assert _expense_count(new_user_id) == before


def test_post_add_expense_malformed_date_does_not_500(client, new_user_id):
    """Edge case: an unparsable date must be handled as a validation error, not crash the app."""
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.post("/expenses/add", data={
        "amount": "50.0",
        "category": "Food",
        "date": "2026-13-45",
        "description": "",
    })

    assert response.status_code == 200
    assert response.status_code != 500


# ------------------------------------------------------------------ #
# POST /expenses/add — sticky values on validation failure             #
# ------------------------------------------------------------------ #

def test_post_add_expense_error_retains_previously_entered_values(client, new_user_id):
    """Spec definition-of-done: 'Submitting with a missing or zero amount re-renders
    the form with an error and previously entered values retained.'"""
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Bills",
        "date": "2026-03-20",
        "description": "Groceries",
    })

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Bills" in body
    assert "2026-03-20" in body
    assert "Groceries" in body


# ------------------------------------------------------------------ #
# Navigation affordances                                               #
# ------------------------------------------------------------------ #

def test_profile_page_has_add_expense_link(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert "/expenses/add" in body, "profile page must link to the add-expense form"


def test_navbar_shows_add_expense_link_when_logged_in(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert "Add Expense" in body


def test_navbar_hides_add_expense_link_when_logged_out(client):
    response = client.get("/")
    body = response.get_data(as_text=True)
    assert "Add Expense" not in body, "Add Expense nav link must only show for logged-in users"


# ------------------------------------------------------------------ #
# Edge case — parameterised queries must handle unusual input safely   #
# ------------------------------------------------------------------ #

def test_post_add_expense_description_with_sql_special_characters_is_stored_safely(client, new_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    tricky = "Lunch'; DROP TABLE expenses; --"
    response = client.post("/expenses/add", data={
        "amount": "12.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": tricky,
    })

    assert response.status_code == 302, "parameterised queries must not choke on quotes/semicolons"
    row = _latest_expense(new_user_id)
    assert row is not None
    assert row["description"] == tricky
