## Spec: Date Filter for Profile Page

### Overview

Add a date-range filter to the `/profile` page so a user can narrow the "Recent Transactions" table, the summary stats, and the category breakdown to a specific time window instead of always seeing all-time data. This builds directly on Step 5 (profile page backend routes), which introduced `get_recent_transactions`, `get_summary_stats`, and `get_category_breakdown` — all currently unfiltered. This step adds an optional date range to each of those, plus a simple filter control in the UI, laying groundwork for the later expense CRUD steps where users will manage individual dated expenses.

---

### Depends on

- Step 1 — Database Setup (`expenses.date` column, `YYYY-MM-DD` format)
- Step 5 — Profile Page Backend Routes (`/profile` route, `database/queries.py` helpers, `seeded_user_id` / `new_user_id` test fixtures)

---

### Routes

- `GET /profile` — now additionally accepts optional query params `range`, `start_date`, `end_date` — logged-in only (unchanged access level; unauthenticated still redirects to `/login`)
- No new routes

---

### Database changes

No database changes. `expenses.date` already stores `YYYY-MM-DD` text, which is directly comparable with `BETWEEN ? AND ?` in SQLite. No new tables or columns.

---

### Filter behavior

- Query params on `GET /profile`:
    - `range` — one of `all`, `this_month`, `last_30`, `last_90`, `custom`. Defaults to `all` when absent or unrecognized.
    - `start_date`, `end_date` — `YYYY-MM-DD` strings, only read/required when `range=custom`.
- Server computes the effective `(start_date, end_date)` window from `range`:
    - `all` → no filtering (both `None`)
    - `this_month` → first day of current month through today
    - `last_30` → today minus 29 days through today
    - `last_90` → today minus 89 days through today
    - `custom` → the provided `start_date` / `end_date`, inclusive. If either is missing or `start_date > end_date`, fall back to `all` and show a validation message on the page (do not raise a 500).
- The resolved window is applied identically to `get_recent_transactions`, `get_summary_stats`, and `get_category_breakdown` for that request, so the three sections of the page always agree with each other.
- The selected filter must be reflected back in the rendered form (selected `<option>`, filled-in date inputs) so the page state survives a reload.

---

### Templates

**Create:** none

**Modify:**
- `templates/profile.html` — add a filter form above "Recent Transactions": a `<select name="range">` with the five options above, and two `<input type="date">` fields (`start_date`, `end_date`) that are only relevant when "Custom range" is selected, plus a submit button. Method `GET`, no JS required (page reload on submit). Show the validation message when the server fell back to `all` due to bad custom input. If the resolved range is not "all time", show an "All time" / "Clear filter" link back to `/profile` with no query params.

---

### Files to change

- `app.py` — read/validate the `range`/`start_date`/`end_date` query params in `profile()`, compute the effective window, pass it to the three query functions, and pass the current filter state back to the template
- `database/queries.py` — add an optional `start_date=None, end_date=None` keyword pair to `get_recent_transactions`, `get_summary_stats`, and `get_category_breakdown`; when both are `None`, behavior is unchanged from Step 5 (no filtering)
- `templates/profile.html` — add the filter form and the validation/clear-filter UI described above
- `static/css/style.css` — style the new filter form using existing CSS variables (spacing/colors already defined for `.mock-stats`, `.profile-table-card`, etc.)

---

### Files to create

- None

---

### New dependencies

No new dependencies.

---

### Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — date bounds passed as bind parameters, never string-formatted into SQL
- Passwords hashed with werkzeug (unchanged, no auth work in this step)
- Use CSS variables — never hardcode hex values in `style.css`
- All templates extend `base.html`
- Date comparisons rely on `expenses.date` being consistently `YYYY-MM-DD` — do not reformat it before filtering
- Invalid/malformed `start_date` or `end_date` must never raise an unhandled exception or 500 — fall back to `all` and surface a validation message instead

---

### Definition of done

- [ ]  Visiting `/profile` with no query params shows all-time data, identical to Step 5 behavior
- [ ]  Selecting "This Month" shows only transactions/stats/breakdown from the 1st of the current month onward
- [ ]  Selecting "Last 30 Days" / "Last 90 Days" shows the correct rolling window ending today
- [ ]  Selecting "Custom Range" with valid `start_date <= end_date` filters to exactly that inclusive window
- [ ]  Submitting a custom range with `start_date > end_date`, or a missing bound, falls back to all-time data and shows a validation message — no 500 error
- [ ]  Recent Transactions, summary stats, and Category Breakdown all reflect the same filtered window on a given request
- [ ]  A user with zero expenses in the selected window sees the existing zero-state (₹0.00, empty table, empty breakdown), not an error
- [ ]  Reloading the page after selecting a filter keeps that filter selected in the form (`range` selected, date inputs filled)
- [ ]  A "Clear filter" / "All time" link returns to the unfiltered view
- [ ]  Filtering another user's data is impossible — the filter only ever narrows the logged-in user's own `user_id` scope
