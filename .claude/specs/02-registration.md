# Spec: Registration

## Overview
This step implements account creation for Spendly. `GET /register` already renders `register.html` with a working form, but the form POSTs to `/register` with no handler behind it, so submissions currently 405. This step adds the `POST /register` handler: validate the submitted name/email/password, hash the password, insert a new row into `users` via `database/db.py`, start a logged-in session for the new user, and redirect them into the app. It is the first step in the roadmap that writes to the database from a live request, and it establishes the session pattern that later steps (login, logout, profile, expense CRUD) will reuse.

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `init_db()`, `users` table). Already implemented on `master`.

## Routes
- `POST /register` — validate form input, create the user, log them in, redirect to `/` — public

`GET /register` already exists and is unchanged.

## Database changes
No database changes. The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already exists in `database/db.py` and has every column this feature needs. This step adds a `create_user(name, email, password_hash)` function to `database/db.py` that performs a parameterised `INSERT` and returns the new user id, reusing `get_db()`.

## Templates
Create: none.

Modify:
- `templates/register.html` — no structural changes; it already posts to `/register`, already renders `{{ error }}` via the `auth-error` block, and already has `name`/`email`/`password` fields with `required`. No edits expected unless field-level validation messages need extra markup.

## Files to change
- `app.py` — add `POST` to the `/register` route (or a separate handler), add `app.secret_key` config (required for Flask `session` to work — currently unset), read form fields, validate, call `database/db.py` to create the user, set `session["user_id"]`, redirect to `/` on success, re-render `register.html` with `error` on failure.
- `database/db.py` — add `create_user(name, email, password_hash)` using a parameterised `INSERT INTO users (...) VALUES (...)`.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already used in `database/db.py`'s `seed_db()` and covers hashing here too.

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` via `database/db.py` only.
- Parameterised queries only — never format user input into SQL strings.
- Passwords hashed with `werkzeug.security.generate_password_hash`; never store or log plaintext passwords.
- Validate on the server even though the form has `required`/`type=email`/etc. client-side: name and password non-empty, password minimum 8 characters (matches the placeholder text "Min. 8 characters"), email looks like an email, email not already registered (catch the `UNIQUE` constraint on `users.email` or pre-check with a `SELECT`).
- On any validation failure, re-render `register.html` with `error` set to a user-facing message and HTTP 200 (don't redirect away from the filled-in form) — do not leak whether a specific email exists beyond a generic "Email already registered" message.
- On success, set `session["user_id"]` to log the new user in immediately, then redirect (302) to `/` — don't render a template directly from a POST.
- Use CSS variables — never hardcode hex values — if any new markup/styling is added.
- All templates extend `base.html`.

## Definition of done
- [ ] Submitting `register.html` with a valid name, a new email, and an 8+ character password creates a row in the `users` table with a hashed (not plaintext) password.
- [ ] After successful registration, the browser is redirected to `/` and a session cookie is set (`session["user_id"]` matches the new user's id).
- [ ] Submitting with an email that's already registered re-renders `register.html` with an error message and does not create a duplicate row.
- [ ] Submitting with a password under 8 characters re-renders `register.html` with an error message and does not create a row.
- [ ] Submitting with an empty name or malformed email re-renders `register.html` with an error message and does not create a row.
- [ ] `GET /register` still renders the form as before (unaffected by the new POST handler).
- [ ] `venv/Scripts/python.exe app.py` starts without errors and `POST /register` no longer returns a 405.
