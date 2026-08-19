"""Tests for Step 9 — Delete Expense, from .claude/specs/09-delete-expense.md."""
from database.db import get_db
from database.queries import delete_expense, insert_expense


# ------------------------------------------------------------------ #
# Unit tests — delete_expense                                         #
# ------------------------------------------------------------------ #

def test_delete_expense_correct_user(new_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    delete_expense(expense_id, new_user_id)

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is None


def test_delete_expense_wrong_user_no_op(new_user_id, seeded_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    delete_expense(expense_id, seeded_user_id)

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["amount"] == 50.0


def test_delete_expense_nonexistent_no_error(seeded_user_id):
    delete_expense(999999, seeded_user_id)  # should not raise


# ------------------------------------------------------------------ #
# Route tests — POST /expenses/<id>/delete                            #
# ------------------------------------------------------------------ #

def test_post_delete_expense_unauthenticated_redirects(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is not None


def test_post_delete_expense_own_expense(client, new_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = new_user_id

    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is None


def test_post_delete_expense_other_user_expense_no_op(client, new_user_id, seeded_user_id):
    expense_id = insert_expense(new_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["amount"] == 50.0


def test_post_delete_expense_nonexistent_id(client, seeded_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.post("/expenses/999999/delete")
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_get_delete_expense_method_not_allowed(client, seeded_user_id):
    expense_id = insert_expense(seeded_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    with client.session_transaction() as sess:
        sess["user_id"] = seeded_user_id

    response = client.get(f"/expenses/{expense_id}/delete")
    assert response.status_code == 405
