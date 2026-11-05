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
