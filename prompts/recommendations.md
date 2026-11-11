# Feature 10 — Weight and rep recommendations (feature/recommendations)

## Prompt

Read PLAN.md (feature 10), CLAUDE.md, and schema.md. This branch is Feature 10 ONLY: weight and rep recommendations using "double progression."

Definitions:
- Each exercise has a target rep range (rep_min, rep_max; default 8–12, already in the exercises table).
- "Last session" for an exercise = the most recent workout (by date) that has sets of that exercise, excluding the workout currently being edited.
- "Last weight" = the heaviest weight used for that exercise in the last session.

Rules for WEIGHTED exercises, checked in this order:
1. No history yet → no suggestion; show "Log a session to get a recommendation."
2. Deload: if ANY set fell below rep_min in BOTH of the last 2 sessions → suggest last weight × 0.9, rounded to the nearest 5 lb, at rep_min reps. Message: "Tough couple of sessions — drop to X lb × rep_min and build back up."
3. Level up: if EVERY set in the last session reached rep_max or more → suggest last weight + 5 lb at rep_min reps. Message: "You hit 12 on every set — go up to X lb × 8."
4. Otherwise → same weight, target reps = (lowest reps in last session) + 1, capped at rep_max. Message: "Same weight, aim for X reps per set."

Rules for BODYWEIGHT exercises (is_bodyweight = true): no weight changes. Suggest (best set reps from last session) + 1 rep. Message: "Beat your best: aim for X reps."

Build:
1. Put all logic in a separate module (e.g. app/recommendations.py) as small, testable functions, with the 5 lb increment, 10% deload, and default rep range as named constants.
2. In the new/edit workout form: as soon as an exercise is chosen for a set, show the suggestion under it ("💡 Next: 140 lb × 8") with a "Use this" button that fills in the weight and reps. Never auto-overwrite what I typed. Use a small JSON endpoint that only returns the logged-in user's data (another user's exercise → 404).
3. An "Exercises" page (in the nav or linked from My PRs) listing my exercises, each with its current recommendation and an editable rep range (rep_min must be at least 1 and less than rep_max; show friendly validation messages).
4. Only the logged-in user's data, always. Looks good on phone and desktop, accent color #F26B1D.

Add pytest tests: no history → no suggestion; all sets at rep_max → +5 lb at rep_min; mixed reps → same weight, lowest reps + 1; reps capped at rep_max; below rep_min two sessions in a row → 10% deload rounded to 5 lb; below rep_min only once → no deload; bodyweight → +1 rep, no weight; editing a workout ignores itself as "last session"; a custom rep range (e.g. 5–8) is respected; another user's history is ignored.

Save this prompt to prompts/recommendations.md with a summary. Run the tests, then commit. Don't push to main. Explain in plain English how the app decides what to recommend, with one worked example.

## Summary of what was built

- **`app/recommendations.py`** (new): all the rules. Nothing is stored; suggestions are recalculated from saved sets, so edits and deletes stay correct.
  - Constants: `WEIGHT_INCREMENT_LB`, `DELOAD_PERCENT`, `DEFAULT_REP_MIN`, `DEFAULT_REP_MAX`. `app/models.py` reads its column defaults from these, so the range lives in one place.
  - Small pure functions (`deload_weight`, `needs_deload`, `next_reps`, ...) feed `recommend`, which takes plain data and needs no database.
  - `load_sessions` is the one query, filtered by `user_id`. The Exercises page uses it once for every exercise.
- **`app/exercises.py`** (new): the Exercises page, the rep-range save, and the JSON endpoint `GET /exercises/<id>/recommendation?exclude_workout=<id>`. Another user's exercise or workout is a 404.
- **`workouts/form.html`, `app/workouts.py`**: the hint under each set's exercise and the "Use this" button. Only that button writes to the weight and reps boxes. The page only receives the logged-in user's exercise ids.
- **`exercises.html`, `forms.py` (`RepRangeForm`), `base.html`**: the page, the friendly validation messages, the nav link, and styles.
- **Decisions the prompt left open**
  - Same-day workouts: the one logged later counts as more recent.
  - Halves round up, matching PRs (112.5 lb → 115 lb).
  - A deload never suggests 0 lb or more than the last weight (2.5 lb stays 2.5, 9 lb stays 9).
  - 0 lb sets on a weighted exercise are skipped, as they are for PRs, so a forgotten weight can't produce "0 lb × 9".
  - "Every set" means every logged set, as the prompt says, so a light warm-up set counts.
  - Exercises in the catalog that were never logged, and new custom names, show the "Log a session" message.
  - "Use this" on a bodyweight exercise fills reps only.
  - The rep range form also caps max reps at 1000, the same limit as logged sets.
  - The rep range stays editable for bodyweight exercises, with a note that it doesn't change their target.
  - A hint triggered by leaving the exercise box waits 300 ms. Without that, it appeared mid-tap and pushed "+ Add set" out from under the finger, so the tap was lost.
- **Tests** (`tests/test_recommendations.py`, 63 tests): the requested rules, rounding, session grouping and ordering, the endpoint, the form, the page, validation, and other users' data.
- **Checked in headless Chrome** on a throwaway database: every suggestion type, "Use this", typed values being left alone, Add set, the edit page, and rep-range saving with real CSRF. No sideways scrolling at 320, 375, 768 or 1280px, in light and dark mode.
- **No schema change**, no migration.
