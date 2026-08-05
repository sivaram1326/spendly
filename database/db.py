import os
import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, "expense_tracker.db")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        if row["c"] > 0:
            return

        password_hash = generate_password_hash("demo123")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cur.lastrowid

        month_start = datetime.now().replace(day=1)
        sample_expenses = [
            (12.50, "Food",          2,  "Lunch with coworkers"),
            (45.00, "Transport",     4,  "Monthly train pass top-up"),
            (89.99, "Bills",         5,  "Electricity bill"),
            (150.00, "Health",       7,  "Dentist visit"),
            (25.00, "Entertainment", 9,  "Movie tickets"),
            (60.75, "Shopping",      12, "New shoes"),
            (8.00,  "Other",         14, "Miscellaneous purchase"),
            (32.40, "Food",          20, "Groceries"),
        ]
        for amount, category, day_of_month, description in sample_expenses:
            expense_date = (month_start + timedelta(days=day_of_month - 1)).strftime("%Y-%m-%d")
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, expense_date, description),
            )
        conn.commit()
    finally:
        conn.close()
