# Feature 4 — Validation (feature/validation)

## Prompt

Read PLAN.md and CLAUDE.md. This branch is Feature 4 ONLY: validation on the workout forms (new and edit).

Rules, each with a friendly message shown next to the field, and the form keeps everything else I typed:
- Date is required and can't be in the future ("Pick a date — today or earlier.")
- Title is required ("Give this workout a name.")
- Type must be lift or run
- Effort must be a whole number from 1 to 5
- Duration, if entered, must be greater than 0
- Runs: distance is required and must be greater than 0 ("How far did you run?")
- Lifts: at least one set is required; each set needs an exercise name, reps of 1 or more, and weight of 0 or more ("Reps must be at least 1." / "Weight can't be negative.")
- Show a summary message at the top of the form when there are errors ("Please fix the highlighted fields.")

Validate on the server (not just in the browser), so bad data can never be saved even if someone bypasses the form. Add pytest tests: submitting a blank title, a run with no distance, and a set with 0 reps should each be rejected and save nothing.

Save this prompt to prompts/validation.md with a short summary. Run the tests, then commit to this branch. Don't push to main. Explain in plain English why validating on the server matters.

## Summary of what was built

- **All rules live in `app/forms.py`** (`WorkoutForm`, `SetForm`) and run on the server on every POST to `/workouts/new` and `/workouts/<id>/edit`. Nothing reaches the database unless `form.validate_on_submit()` passes. All messages are constants at the top of the workouts section.
- **Rules**: date required and not after today; title required (spaces only counts as blank, max 120 chars); type must be `lift` or `run`; effort optional but if given a whole number 1–5; duration optional but a whole number > 0 (and ≤ 24 h); runs need distance > 0; lifts need ≥ 1 set, and each filled-in row needs an exercise name, whole-number reps ≥ 1, and weight ≥ 0 (blank = bodyweight). Text like "abc", "inf", "nan" in number boxes gets a friendly message instead of a crash.
- **Type-aware**: distance is only checked for runs and set rows only for lifts, so junk in the hidden section can't block a save (it's never saved either).
- **Form UX** (`workouts/form.html`, `base.html`): "Please fix the highlighted fields." at the top, each message under its own input, bad inputs marked `aria-invalid` (Pico outlines them red), "Add at least one set." under the Sets heading, and every typed value is kept on re-render.
- **Tests** (`tests/test_validation.py`, 32 new): the three requested cases (blank title, run without distance, 0-rep set → rejected, nothing saved), plus every rule, hidden-section handling, kept input, message placement, and a bad edit leaving the saved workout unchanged. 64 tests pass in total.
- **Notes**: "today" is the server's date (UTC on Render), so in the evening in California the next day's date is briefly allowed. The database check constraints from Feature 2 still allow duration/distance of 0; tightening them would need a migration and is left out of this branch.

---

## Follow-up prompt (round 2)

I tested the validation locally. Here's what I found and what I want changed:

BUG: A run with no distance saves without any message. Fix it: distance is required for runs and must be greater than 0 ("How far did you run?"). Add a pytest test for this.

CHANGE 1 — Title is now optional. If left blank, default it to the day of the week, the date, and the type, e.g. "Wednesday, Nov 4 — Lift" or "Wednesday, Nov 4 — Run". Update the test that expected a blank title to be rejected: it should now save with this default title.

CHANGE 2 — Exercise catalog. Create a built-in list of about 100 common exercises (e.g. Back Squat, Bench Press, Deadlift, Overhead Press, Hang Clean, Pull-Up, Push-Up, Crunch, Burpee, Lunge, Plank, etc.), each tagged as "weighted" or "bodyweight". Store it as a Python list in the code, not as fake user data. In the set form, the exercise field should be a searchable dropdown that suggests from this catalog plus my own past exercises, but still lets me type a custom name. Add an is_bodyweight true/false column to the exercises table (with a migration) and set it from the catalog when a user first uses that exercise; custom exercises default to weighted. Match names case-insensitively so "bench press" and "Bench Press" are the same exercise.

CHANGE 3 — Blank weight. If a set's weight is blank on a bodyweight exercise, save it as 0 with no warning. If it's blank on a weighted exercise, don't save yet: show a warning "Some sets have no weight. Is this a bodyweight exercise?" with "Save anyway" and "Go back and edit" buttons. Weight still can't be negative.

Keep the server-side check that effort is 1–5 even though the form uses a dropdown.

Update schema.md for the new column. Append this prompt and a summary of the bug and changes to prompts/validation.md. Run all tests, then commit to this branch. Don't push to main. Explain in plain English how the catalog and the bodyweight warning work.

## Summary of round 2

- **The bug**: the app was being run from `main`, which doesn't have Feature 4 yet (it's only on `feature/validation`). On `main`, distance is still optional, so a run with no distance saved. On this branch the server rejects it with "How far did you run?". New tests cover a blank distance, a distance of only spaces, a request with no distance field at all, and editing a lift into a run with no distance.
- **Title optional**: a blank title is saved as e.g. "Wednesday, Nov 4 — Lift" or "Wednesday, Nov 4 — Run", on both new and edit (`WorkoutForm.default_title`). The blank-title test now checks for the default title.
- **Exercise catalog** (`app/catalog.py`): 116 exercises (72 weighted, 44 bodyweight) as a Python list, plus `normalize()` and `lookup()`. The exercise box is a `<datalist>`: a typing box whose suggestions are filtered as you type. It lists your own exercises plus the catalog, with no duplicates, and marks bodyweight ones. Any custom name still works. The first time you log a catalog exercise, your `exercises` row takes the catalog's spelling and `is_bodyweight`. Custom names are weighted. Names match ignoring case and extra spaces.
- **Migration** `82ee7e891171`: adds `exercises.is_bodyweight` (boolean, default false; works on SQLite and Postgres) and tags existing exercises whose names match a bodyweight catalog entry. It uses a plain `ADD COLUMN`. Alembic's SQLite "batch" mode (what autogenerate wrote at first) rebuilds the table by dropping it, which the foreign key from `sets` blocks as soon as any sets exist.
- **Blank weight**: on a bodyweight exercise it's saved as 0 with no message. On a weighted (or custom) exercise, nothing is saved yet. The form comes back with everything kept, the empty weight boxes highlighted, and "Some sets have no weight. Is this a bodyweight exercise?" with **Save anyway** (resubmits with `confirm_blank_weight=y` and saves those sets as 0 lb) and **Go back and edit** (closes the warning and jumps to the first empty weight). Real errors are shown first, and negative weight is always rejected, even with Save anyway.
- **Effort** is still checked on the server (whole number 1–5), with a test that sends values the dropdown can't produce.
- **Tests**: Feature 3 tests updated for catalog spelling ("Back squat" is now saved as "Back Squat"). 80 tests pass.
