"""Tests for Step 8 — Edit Expense, from .claude/specs/08-edit-expense.md."""
from database.db import get_db
from database.queries import get_expense_by_id, insert_expense, update_expense


# ------------------------------------------------------------------ #
# Unit tests — get_expense_by_id                                      #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_correct_user(new_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    row = get_expense_by_id(expense_id, new_user_id)

    assert row is not None
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_get_expense_by_id_wrong_user(new_user_id, seeded_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    row = get_expense_by_id(expense_id, seeded_user_id)

    assert row is None


def test_get_expense_by_id_nonexistent(seeded_user_id):
    row = get_expense_by_id(999999, seeded_user_id)

    assert row is None


# ------------------------------------------------------------------ #
# Unit tests — update_expense                                         #
# ------------------------------------------------------------------ #

def test_update_expense_correct_user(new_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    update_expense(expense_id, new_user_id, 99.0, "Bills", "2026-04-01", "Updated")

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row["amount"] == 99.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-04-01"
    assert row["description"] == "Updated"


def test_update_expense_wrong_user_no_op(new_user_id, seeded_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    update_expense(expense_id, seeded_user_id, 99.0, "Bills", "2026-04-01", "Updated")

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


# ------------------------------------------------------------------ #
# Route tests — GET /expenses/<id>/edit                               #
# ------------------------------------------------------------------ #

def test_get_edit_expense_unauthenticated_redirects(client):
    response = client.get("/expenses/1/edit")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_edit_expense_authenticated_own_expense(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert 'value="50.0"' in body
    assert 'value="2026-03-20"' in body
    assert 'value="Lunch"' in body
    assert '<option value="Food" selected>' in body


def test_get_edit_expense_other_user_expense_404(client, new_user_id, seeded_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 404


def test_get_edit_expense_nonexistent_404(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get("/expenses/999999/edit")
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# Route tests — POST /expenses/<id>/edit                              #
# ------------------------------------------------------------------ #

def test_post_edit_expense_unauthenticated_redirects(client):
    response = client.post("/expenses/1/edit", data={
        "amount": "50.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch",
    })
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_edit_expense_valid_data(client, new_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "99.0",
        "category": "Bills",
        "date": "2026-04-01",
        "description": "Updated",
    })
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row["amount"] == 99.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-04-01"
    assert row["description"] == "Updated"


def test_post_edit_expense_other_user_expense_404(client, new_user_id, seeded_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "99.0",
        "category": "Bills",
        "date": "2026-04-01",
        "description": "Updated",
    })
    assert response.status_code == 404


def test_post_edit_expense_missing_amount(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_edit_expense_zero_amount(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_edit_expense_non_numeric_amount(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "abc",
        "category": "Food",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_edit_expense_invalid_category(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "50.0",
        "category": "NotACategory",
        "date": "2026-03-20",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_edit_expense_invalid_date(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
        "amount": "50.0",
        "category": "Food",
        "date": "not-a-date",
        "description": "",
    })
    assert response.status_code == 200
    assert "auth-error" in response.get_data(as_text=True)


def test_post_edit_expense_no_description(client, new_user_id):
    expense_id = insert_expense(new_user_id, 15.0, "Shopping", "2026-03-20", "Shoes")

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.post(f"/expenses/{expense_id}/edit", data={
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
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row["description"] is None
