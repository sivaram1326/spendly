"""Shared pytest fixtures. Patches the DB path before `app` is ever imported."""
import atexit
import os
import tempfile
import uuid

import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module

_tmp_dir = tempfile.TemporaryDirectory()
atexit.register(_tmp_dir.cleanup)
db_module.DB_PATH = os.path.join(_tmp_dir.name, "test_expense_tracker.db")

import app as app_module  # noqa: E402  (must import AFTER DB_PATH is patched)
from database.db import create_user, get_user_by_email  # noqa: E402


@pytest.fixture
def app():
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return app_module.app


@pytest.fixture
def seeded_user_id():
    """id of the demo@spendly.com user created by seed_db()."""
    return get_user_by_email("demo@spendly.com")["id"]


@pytest.fixture
def new_user_id():
    """A freshly created user with zero expenses, unique email per test."""
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    return create_user("Test User", email, generate_password_hash("password123"))
