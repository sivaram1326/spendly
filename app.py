import os
import re
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import CATEGORIES, create_user, get_db, get_user_by_email, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    insert_expense,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Full name is required.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return render_template("register.html", error="Enter a valid email address.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    try:
        user_id = create_user(name, email, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email already registered.")

    session["user_id"] = user_id
    return redirect(url_for("landing"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    return redirect(url_for("landing"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

def _fmt_inr(amount):
    """Format a numeric amount as an Indian Rupee currency string."""
    return f"₹{amount:,.2f}"


_VALID_RANGES = {"all", "this_month", "last_30", "last_90", "custom"}


def _compute_date_range(range_param, start_date_param, end_date_param):
    """(start_date, end_date, error) as ISO strings, or (None, None, err) for all-time."""
    today = date.today()

    if range_param == "this_month":
        return today.replace(day=1).isoformat(), today.isoformat(), None
    if range_param == "last_30":
        return (today - timedelta(days=29)).isoformat(), today.isoformat(), None
    if range_param == "last_90":
        return (today - timedelta(days=89)).isoformat(), today.isoformat(), None

    if range_param == "custom":
        if not start_date_param or not end_date_param:
            return None, None, "Please provide both a start and end date for a custom range."
        try:
            start_dt = datetime.strptime(start_date_param, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date_param, "%Y-%m-%d").date()
        except ValueError:
            return None, None, "Invalid date format — please use the date picker."
        if start_dt > end_dt:
            return None, None, "Start date must be on or before the end date."
        return start_dt.isoformat(), end_dt.isoformat(), None

    return None, None, None  # "all" or unrecognized -> all-time, no error


def _resolve_filter_params():
    """Read range/start_date/end_date from the query string and resolve the
    effective (start_date, end_date, error, selected_range, is_filtered) state."""
    range_param = request.args.get("range", "all")
    start_date_param = request.args.get("start_date", "")
    end_date_param = request.args.get("end_date", "")

    start_date, end_date, filter_error = _compute_date_range(
        range_param, start_date_param, end_date_param
    )
    selected_range = range_param if range_param in _VALID_RANGES else "all"

    return {
        "start_date": start_date,
        "end_date": end_date,
        "filter_error": filter_error,
        "selected_range": selected_range,
        "start_date_value": start_date_param if range_param == "custom" else "",
        "end_date_value": end_date_param if range_param == "custom" else "",
        "is_filtered": start_date is not None,
    }


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    filter_state = _resolve_filter_params()
    start_date = filter_state["start_date"]
    end_date = filter_state["end_date"]

    user_row = get_user_by_id(user_id)
    user = {
        "name": user_row["name"],
        "email": user_row["email"],
        "member_since": user_row["member_since"],
        "initials": "".join(p[0].upper() for p in user_row["name"].split()[:2]),
    }

    raw_stats = get_summary_stats(user_id, start_date=start_date, end_date=end_date)
    stats = {
        "total_spent": _fmt_inr(raw_stats["total_spent"]),
        "transaction_count": raw_stats["transaction_count"],
        "top_category": raw_stats["top_category"],
    }

    raw_transactions = get_recent_transactions(user_id, start_date=start_date, end_date=end_date)
    transactions = [
        {**tx, "amount": _fmt_inr(tx["amount"])} for tx in raw_transactions
    ]

    raw_breakdown = get_category_breakdown(user_id, start_date=start_date, end_date=end_date)
    category_breakdown = [
        {"category": row["name"], "amount": _fmt_inr(row["amount"]), "percent": row["pct"]}
        for row in raw_breakdown
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        category_breakdown=category_breakdown,
        selected_range=filter_state["selected_range"],
        start_date_value=filter_state["start_date_value"],
        end_date_value=filter_state["end_date_value"],
        filter_error=filter_state["filter_error"],
        is_filtered=filter_state["is_filtered"],
    )


def _render_add_expense_form(error=None, values=None):
    return render_template(
        "add_expense.html",
        categories=CATEGORIES,
        today=date.today().isoformat(),
        error=error,
        values=values,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return _render_add_expense_form()

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description_raw = request.form.get("description", "").strip()

    form_values = {
        "amount": amount_raw,
        "category": category,
        "date": date_raw,
        "description": description_raw,
    }

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return _render_add_expense_form(
            error="Enter a valid amount greater than 0.", values=form_values
        )

    if category not in CATEGORIES:
        return _render_add_expense_form(
            error="Select a valid category.", values=form_values
        )

    try:
        datetime.strptime(date_raw, "%Y-%m-%d")
    except ValueError:
        return _render_add_expense_form(
            error="Enter a valid date.", values=form_values
        )

    if len(description_raw) > 200:
        return _render_add_expense_form(
            error="Description must be 200 characters or fewer.", values=form_values
        )

    description = description_raw if description_raw else None
    insert_expense(session["user_id"], amount, category, date_raw, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
