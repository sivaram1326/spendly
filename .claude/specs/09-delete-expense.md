Spec: Delete Expense

Overview
Step 9 lets a logged-in user permanently delete one of their own expenses. A "Delete" action is added next to the existing "Edit" action in the profile page's transactions table. Because deletion is destructive and must not be triggerable by a simple GET link (crawlers, prefetching, or an accidental click should never delete data), the delete action is a small POST-only form with a client-side confirmation prompt, submitting to /expenses/<id>/delete. Ownership is enforced identically to edit: a user can only delete expenses that belong to them. One new query helper, delete_expense, is added to database/queries.py.

Depends on
Step 1: Database setup (expenses table exists)
Step 3: Login / Logout (session["user_id"] is set and enforced)
Step 5: Profile page renders transactions (the delete action lives there)
Step 8: Edit Expense (establishes the ownership-scoped mutation pattern and the Actions column this step extends)

Routes
POST /expenses/<int:id>/delete — delete the expense if owned by the current user, then redirect to /profile — logged-in only

Note: the existing placeholder route is GET-only (`@app.route("/expenses/<int:id>/delete")`, defaulting to GET). This step replaces it with a POST-only route. There is no GET form for delete — the action is triggered directly from the profile page table via a small inline form, matching the pattern of a destructive, non-idempotent action.

Database changes
No new tables or columns. No database changes.

Templates
Create: No new templates.

Modify: templates/profile.html
- In the Actions cell (currently `<td><a href="{{ url_for('edit_expense', id=tx.id) }}" class="filter-clear-link">Edit</a></td>`), add a small inline `<form>` after the Edit link:
  - `method="POST"` and `action="{{ url_for('delete_expense', id=tx.id) }}"`
  - A submit `<button type="submit">` labeled "Delete", styled to match `filter-clear-link` (reuse the existing class/CSS variables — no new hardcoded styles)
  - `onsubmit="return confirm('Delete this expense?')"` on the form to guard against accidental clicks (this is a plain browser confirm, not a custom modal — no new JS files needed)

Files to change
database/queries.py
- Add `delete_expense(expense_id, user_id)` — issues a parameterised `DELETE FROM expenses WHERE id = ? AND user_id = ?` for ownership safety; no-ops (0 rows affected) if not owned or not found

app.py
- Import `delete_expense` from `database.queries`
- Replace the placeholder `delete_expense` view:
  - Change the route decorator to `@app.route("/expenses/<int:id>/delete", methods=["POST"])`
  - Redirect unauthenticated requests to `/login`
  - Call `delete_expense(id, session["user_id"])` (no existence check needed beforehand — the scoped DELETE is a safe no-op if the expense doesn't exist or isn't owned by the current user)
  - Redirect to `url_for("profile")` on completion

templates/profile.html
- Add the inline delete form to the Actions cell as described above

Files to create
No new files.

New dependencies
No new dependencies.

Rules for implementation
- No SQLAlchemy or ORMs — raw sqlite3 only via get_db()
- Parameterised queries only — never string-format values into SQL
- Foreign keys PRAGMA must be enabled on every connection (already done in get_db())
- delete_expense must scope its query to id = ? AND user_id = ? to prevent one user deleting another user's expense
- The delete route must only accept POST — no GET handler, so the action cannot be triggered by a plain link or prefetch
- Unauthenticated POST to /expenses/<id>/delete must redirect to /login
- Deleting a non-existent id or another user's expense must not error — it's a safe no-op that still redirects to /profile
- Use CSS variables — never hardcode hex values
- All templates extend base.html
- No inline styles
- Currency must always display as ₹ — never £ or $

Tests to write
File: tests/test_delete_expense.py

Unit tests
Function | Input | Expected output
delete_expense | valid expense_id, correct user_id | row removed from DB
delete_expense | valid expense_id, wrong user_id | row unchanged, still present in DB
delete_expense | non-existent expense_id | no error raised, no rows affected

Route tests
POST /expenses/<id>/delete — unauthenticated:
- Redirects to /login (302)
- Expense row still exists in DB

POST /expenses/<id>/delete — authenticated, own expense:
- Redirects to /profile (302)
- Expense no longer appears in the transaction list
- Row removed from DB

POST /expenses/<id>/delete — authenticated, other user's expense:
- Redirects to /profile (302) (safe no-op, not a 404 — matches the no-op semantics of delete_expense)
- Row still exists in DB, unchanged

POST /expenses/<id>/delete — authenticated, non-existent id:
- Redirects to /profile (302)
- No error raised

GET /expenses/<id>/delete — any user:
- Returns 405 (method not allowed), since the route only accepts POST

Definition of done
- [ ] Visiting /expenses/<id>/delete with GET returns 405
- [ ] POSTing to /expenses/<id>/delete while logged out redirects to /login and does not delete the row
- [ ] Each row in the profile transaction table has a "Delete" action next to "Edit"
- [ ] Clicking Delete prompts a browser confirmation before submitting
- [ ] Confirming delete removes the expense from the database and the row disappears from the profile transaction list
- [ ] POSTing to delete another user's expense id does not remove that expense and redirects safely to /profile
- [ ] POSTing to delete a non-existent expense id does not error and redirects to /profile
