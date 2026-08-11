import os
import re
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

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


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Demo User",
        "initials": "DU",
        "email": "demo@spendly.com",
        "member_since": "August 2026",
    }
    stats = {
        "total_spent": "₹423.64",
        "transaction_count": 8,
        "top_category": "Food",
    }
    transactions = [
        {"date": "Aug 2, 2026", "description": "Lunch with coworkers", "category": "Food", "amount": "₹12.50"},
        {"date": "Aug 4, 2026", "description": "Monthly train pass top-up", "category": "Transport", "amount": "₹45.00"},
        {"date": "Aug 5, 2026", "description": "Electricity bill", "category": "Bills", "amount": "₹89.99"},
        {"date": "Aug 7, 2026", "description": "Dentist visit", "category": "Health", "amount": "₹150.00"},
        {"date": "Aug 9, 2026", "description": "Movie tickets", "category": "Entertainment", "amount": "₹25.00"},
    ]
    category_breakdown = [
        {"category": "Food", "amount": "₹144.90", "percent": 72},
        {"category": "Transport", "amount": "₹45.00", "percent": 22},
        {"category": "Bills", "amount": "₹89.99", "percent": 45},
        {"category": "Health", "amount": "₹150.00", "percent": 75},
        {"category": "Entertainment", "amount": "₹25.00", "percent": 12},
    ]

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        category_breakdown=category_breakdown,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
