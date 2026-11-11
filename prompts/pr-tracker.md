# Feature 8 — PR tracker (feature/pr-tracker)

## Prompt

Read PLAN.md (feature 8), CLAUDE.md, and schema.md. This branch is Feature 8 ONLY: the PR (personal record) tracker.

Rules:
- Weighted exercises: track heaviest weight lifted, and best estimated 1-rep max using Epley: weight × (1 + reps/30), rounded to the nearest lb.
- Bodyweight exercises (is_bodyweight = true): track most reps in a single set instead (weight is 0, so Epley doesn't apply).
- Runs of 1 mile or more: track fastest pace (minutes per mile, shown as m:ss /mi) and longest run (miles).

Build:
1. Calculate PRs from the existing sets and workouts data rather than storing them in a new table, so editing or deleting a workout always keeps PRs correct. Put the calculations in a separate module (e.g. app/prs.py) as small testable functions.
2. After saving a new or edited workout, if it set any new PR, show a celebratory message ("🏆 New PR: Bench Press — 185 lb!"). A first-ever log of an exercise should NOT count as a PR (nothing to beat yet).
3. On the workout detail page, show a small 🏆 badge next to any set that is currently an all-time PR.
4. A "My PRs" page (add to nav): one row per exercise with the best weight / est. 1RM (or max reps for bodyweight) and the date it was set, linking to that workout; plus run PRs at the top. Friendly empty state. Looks good on phone and desktop, using the accent color #F26B1D.
5. Only the logged-in user's data, always.

Add pytest tests: Epley calculation (e.g. 200 lb × 5 reps = 233); a heavier set becomes the new PR; first log isn't flagged as a PR; bodyweight PR uses reps; fastest pace ignores runs under 1 mile; another user's lifts never count.

Save this prompt to prompts/pr-tracker.md with a summary. Run the tests, then commit. Don't push to main. Explain in plain English how the app decides something is a new PR.

## Summary of what was built

- **`app/prs.py`** (new): all the PR logic as small functions. Nothing is stored; every answer is recalculated from the user's sets and workouts.
  - Math: `epley_1rm` (halves round up), `pace_seconds`, `format_pace`, `format_value`.
  - Which records something competes for: `set_metrics`, `run_metrics`, and `beats` (lower wins for pace, higher for the rest).
  - History: `performances` (filtered by `user_id`) and `best_records` (the earliest holder keeps a tie).
  - Detecting a new PR: `take_snapshot` before the save, `new_prs` after it, `pr_messages` for the text.
  - Pages: `set_badges`, `pr_summary`.
- **`app/workouts.py`**: takes a snapshot before saving, flashes any new PRs after saving, and passes badges to the detail page.
- **`app/pr_views.py`** (new blueprint, `GET /prs`, login required) and **`prs.html`**: run PR cards on top, then one row per exercise with the value, date, and a link to the workout. Friendly empty state.
- **`detail.html`**: a 🏆 badge in the Reps cell of a set holding a record, with a tooltip naming which record.
- **`base.html`**: "My PRs" nav link, an orange-tinted style for PR messages, PR page and badge styles. The phone nav is slightly tighter so four links stay on one line.
- **Decisions the prompt left open**
  - A tie isn't a new PR. The first set to reach a number holds the record, so only that set gets the badge.
  - The first log of an exercise gets no celebration, but its best set does get a badge, because it is currently the all-time best.
  - Re-saving a workout that already holds a PR doesn't celebrate again. An edit only counts if it improves on that workout's old numbers and beats every other workout.
  - PRs are all-time, regardless of workout date, so backfilling an old workout that beats everything counts as a new PR.
  - A 0 lb set on a weighted exercise is ignored. A run with no duration counts for longest run but not pace.
  - Est. 1RM and pace are compared as displayed (whole lb, whole seconds), so a new PR is always visibly better.
- **Tests** (`tests/test_prs.py`, 35 tests): Epley, record selection, bodyweight, run rules, ties, other users' data, new-PR detection through real saves and edits, badges, and the My PRs page.
- **Checked visually** at 375 and 1280px, in light and dark mode, with no horizontal overflow.
- **No schema change**, no migration.
