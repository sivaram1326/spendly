# Spec: Login and Logout

## Overview
This step implements session-based authentication for existing users. `GET /login` already renders `login.html` with a working form that POSTs to `/login`, but there is no `POST` handler behind it, so submissions currently 405. `/logout` is a placeholder route that returns plain text ("Logout — coming in Step 3"). This step adds the `POST /login` handler — look up the user by email, verify the password hash, start a logged-in session, and redirect into the app — and a real `/logout` route that clears the session and redirects to the landing page. It also updates the shared nav in `base.html` to reflect session state (showing "Sign in" to guests and a "Logout" link to signed-in users), since without that there is no way for a user to reach `/logout` or see that they're logged in. This builds directly on the session pattern established in Step 2 (registration) and is a prerequisite for Step 4 (profile) and the expense CRUD steps, which all require `session["user_id"]` to identify the current user.

## Depends on
- Step 1 — Database setup (`database/db.py`: `get_db()`, `init_db()`, `users` table). Already implemented on `master`.
- Step 2 — Registration (`create_user`, `session["user_id"]` pattern, `app.secret_key` config). Already implemented on `master`.

## Routes
- `POST /login` — validate submitted email/password against the `users` table, start a session, redirect to `/` — public
- `GET /logout` — clear the session and redirect to `/` — logged-in (safe to call even if not logged in; simply redirects)

`GET /login` already exists and is unchanged.

## Database changes
No database changes. The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already has every column this feature needs. This step adds a `get_user_by_email(email)` function to `database/db.py` that performs a parameterised `SELECT` and returns the matching row (or `None`), reusing `get_db()`.

## Templates
Create: none.

Modify:
- `templates/login.html` — no structural changes; it already posts to `/login`, already renders `{{ error }}` via the `auth-error` block, and already has `email`/`password` fields with `required`. No edits expected.
- `templates/base.html` — update `.nav-links` to conditionally render based on `session`: if `session.get("user_id")` is set, show a "Logout" link pointing to `{{ url_for('logout') }}` (and drop "Sign in" / "Get started"); otherwise show the existing "Sign in" / "Get started" links unchanged.

## Files to change
- `app.py` — add a `POST` handler to the `/login` route (alongside the existing `GET`): read form fields, validate, look up the user via `database/db.py`, verify the password with `werkzeug.security.check_password_hash`, set `session["user_id"]` on success and redirect (302) to `/`, or re-render `login.html` with a generic `error` on failure. Replace the placeholder `/logout` route body with `session.clear()` (or `session.pop("user_id", None)`) followed by a redirect (302) to `/`.
- `database/db.py` — add `get_user_by_email(email)` using a parameterised `SELECT * FROM users WHERE email = ?`.
- `templates/base.html` — conditional nav links as described above.

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` is part of the `werkzeug` package already installed (used for `generate_password_hash` in `database/db.py` and `app.py`).

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` via `database/db.py` only.
- Parameterised queries only — never format user input into SQL strings.
- Passwords verified with `werkzeug.security.check_password_hash`; never store, log, or compare plaintext passwords.
- On invalid credentials (unknown email OR wrong password), re-render `login.html` with **one generic** error message such as "Invalid email or password." — never reveal whether the email exists in the system.
- On success, set `session["user_id"]` to the matching user's id, then redirect (302) to `/` — don't render a template directly from a POST.
- `/logout` must clear the entire session (not just `user_id`) so no stale state leaks to the next visitor, then redirect (302) to `/`.
- Use CSS variables — never hardcode hex values — for any new/modified nav markup styling.
- All templates extend `base.html`.

## Definition of done
- [ ] Submitting `login.html` with the seeded demo account (`demo@spendly.com` / `demo123`) redirects to `/` and sets `session["user_id"]` to that user's id.
- [ ] Submitting `login.html` with a correct email but wrong password re-renders `login.html` with a generic "Invalid email or password" error and does not set a session.
- [ ] Submitting `login.html` with an email that doesn't exist re-renders `login.html` with the same generic error message (indistinguishable from a wrong-password failure).
- [ ] After logging in, the nav bar shows a "Logout" link instead of "Sign in" / "Get started".
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/`, after which the nav bar shows "Sign in" / "Get started" again.
- [ ] Visiting `/logout` while not logged in does not error — it redirects to `/` without issue.
- [ ] `GET /login` still renders the form as before (unaffected by the new POST handler).
- [ ] `venv/Scripts/python.exe app.py` starts without errors and `POST /login` no longer returns a 405.
