# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a Flask expense-tracker web app, structured as a step-by-step learning project (code comments reference "Step 1", "Step 3", etc. — placeholder routes note which step will implement them). Python 3.12, Flask 3.1.3, SQLite (planned), pytest for tests.

**Directory note:** this repo root (`expense-tracker/expense-tracker/` relative to `C:\expense-tracker`) is nested one level inside a parent folder that also contains unrelated extraction cruft (`__MACOSX/`, a stray `claude.exe`). Only this directory is the actual git repository and Flask project — run all commands from here.

## Environment setup (Windows)

- Virtualenv lives at `venv/` in the repo root (Windows layout: `venv/Scripts/`, not `venv/bin/`).
- In a persistent Bash session, shell state (like a `source venv/Scripts/activate`) does not carry over between tool calls — either re-activate every command or call the venv binaries directly: `venv/Scripts/python.exe`, `venv/Scripts/pip.exe`.
- If `python`/`python3` resolve to the Microsoft Store stub instead of a real interpreter, PATH wasn't picked up by the current shell — use the venv's `python.exe` directly rather than relying on PATH.

## Common commands

```bash
# install dependencies
venv/Scripts/pip.exe install -r requirements.txt

# run the dev server (http://localhost:5001)
venv/Scripts/python.exe app.py

# run tests
venv/Scripts/python.exe -m pytest
```

There is no lint/format tooling configured yet.

## Architecture

- `app.py` — single Flask app instance and all routes (no blueprints). Routes are split into two groups by comment header: implemented pages (`/`, `/register`, `/login`, `/terms`, `/privacy`, all GET-only, template rendering) and placeholder routes awaiting implementation (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`), which currently just return a plain string.
- `database/db.py` — intended to hold `get_db()` (SQLite connection with row_factory + foreign keys enabled), `init_db()` (CREATE TABLE IF NOT EXISTS), `seed_db()` (dev sample data). Currently a stub with no implementation; this is the next step in the course sequence.
- `templates/` — Jinja2 templates, all extending `base.html` (nav + footer chrome, Google Fonts, links to `static/css/style.css` and `static/js/main.js`). Forms in `register.html`/`login.html` POST to `/register`/`/login` directly (not yet handled by `app.py` — will 405 until those handlers are added).
- `static/` — plain CSS/JS, no build step or bundler.
- `.gitignore` excludes `venv/`, `expense_tracker.db` (the eventual SQLite file), and `.claude/plans/`.

## Current implementation state

Working: landing, register (GET/UI only), login (GET/UI only), terms, privacy pages; shared base template; CSS/JS static assets.

Not yet implemented: POST handlers for `/register` and `/login`; `database/db.py` (empty stub); `/logout` and `/profile` (placeholder text); all expense CRUD routes under `/expenses/` (placeholder text). Follow the "Step N" comments in `app.py` and `database/db.py` for the intended build order — database setup (Step 1) comes before auth POST handlers and expense CRUD.
