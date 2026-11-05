# Feature 3 — Create / read / update / delete workouts (feature/workouts-crud)

## Prompt

Read PLAN.md and CLAUDE.md. This branch is Feature 3 ONLY: create, read, update, and delete workouts.

Build:
1. Workouts list page (the home page after login): the logged-in user's workouts as cards, newest first, showing date, title, type, and a quick summary (number of sets, or distance for runs).
2. "New workout" form: date (default today), title, type (lift or run), duration in minutes, effort 1–5, notes. If type is "run", show distance in miles. If type is "lift", let me add multiple sets on the same form: exercise name, weight (lb), reps. Exercise names should autocomplete from my own exercises, and typing a new name creates that exercise for me.
3. Workout detail page showing everything, with sets grouped by exercise.
4. Edit page (same form, prefilled), including adding or removing sets.
5. Delete button with an "Are you sure?" confirmation step before anything is deleted.

Security: every query must be filtered by the logged-in user. If anyone opens another user's workout URL (view, edit, or delete), return 404.

Keep it mobile-friendly (I log at the gym on my phone). Basic required fields are fine for now; full validation messages come in Feature 4.

Save this prompt to prompts/workouts-crud.md with a short summary. Run the tests, then commit to this branch. Don't push to main. Explain in plain English how a new workout goes from the form into the database.

## Summary of what was built

- **Branch base**: Feature 2's tables live on `feature/datamodel` (PR #6, not yet merged), so this branch is stacked on top of it. Nothing was merged. Merge PR #6 first, then this branch's PR.
- **Routes** (`app/workouts.py`, blueprint `workouts`): `/workouts/new`, `/workouts/<id>`, `/workouts/<id>/edit`, `/workouts/<id>/delete` (GET = "Are you sure?" page, POST = delete). Every lookup filters by `id` **and** `current_user.id`, so someone else's workout returns 404 for view, edit, and delete.
- **Home** (`/`, `app/main.py`): your workouts as cards, newest first (date, title, type badge, "N sets" or "X mi", duration).
- **Form** (`WorkoutForm` + `SetForm` in `app/forms.py`, template `workouts/form.html`): same form for new and edit. Lift/Run radio buttons show sets or distance. Set rows can be added or removed; "+ Add set" copies the previous row so a repeat set is one tap. Exercise names autocomplete from *your* exercises (`<datalist>`). A new name creates the exercise, and names match ignoring case and extra spaces ("back squat " = "Back squat"). A blank weight means bodyweight (0 lb), and fully blank rows are skipped. Date defaults to today in the phone's own time zone.
- **Editing sets**: on save, the workout's set list is rebuilt from the form in order (set numbers 1, 2, 3…). Removed rows are deleted. Switching a lift to a run drops its sets; switching to lift clears distance.
- **Detail page**: date, title, type, distance/sets, duration, effort, notes, and sets grouped by exercise (in the order first logged) with set #, weight, and reps. Edit and Delete buttons.
- **Validation (basic)**: date and type required; a set row with an exercise needs reps; numbers can't be negative and reps must be at least 1. Full friendly messages are Feature 4.
- **Other**: pinned `WTForms==3.3.2` (it wasn't pinned, and 3.4 drops the choices format), removed the placeholder `home.html`, updated the auth test for the new home page.
- **Tests** (`tests/test_workouts.py`, 15 tests): create lift/run, exercise reuse and creation per user, autocomplete list, blank rows, edit adding/removing sets, lift→run, delete confirmation, and PLAN.md test 1 (User B sees an empty list and gets 404 on User A's view/edit/delete URLs, GET and POST). 32 tests pass in total.
