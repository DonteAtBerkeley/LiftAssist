# Feature 9 — Streak counter (feature/streak)

## Prompt

Read PLAN.md (feature 9), CLAUDE.md, and schema.md. This branch is Feature 9 ONLY: the weekly streak counter.

Rules:
- A week is Monday–Sunday, based on each workout's date.
- A week "counts" if it has at least 3 workouts (lifts and runs both count).
- Current streak = number of consecutive counting weeks ending with the most recent completed week. The current, in-progress week should NOT break the streak: if this week already has 3+ workouts, include it; if not, don't count it yet and don't reset the streak because of it.
- Longest streak = the most consecutive counting weeks ever.
- Put the threshold (3) in one named constant so it's easy to change.

Build:
1. Put the calculations in a separate module (e.g. app/streaks.py) as small testable functions.
2. A streak card at the top of the Dashboard: "🔥 Current streak: X weeks", "Longest: Y weeks", and this week's progress "This week: 2 / 3 workouts" with a simple progress bar in the accent color #F26B1D.
3. A small streak badge on the workouts list page header ("🔥 X-week streak"), hidden when the streak is 0.
4. Encouraging empty state for 0 ("Log 3 workouts this week to start a streak.").
5. Only the logged-in user's data. Looks good on phone and desktop.

Add pytest tests: 3 consecutive weeks of 3 workouts = streak of 3; a week with only 2 workouts breaks the streak; the in-progress week with fewer than 3 workouts doesn't reset the current streak; longest streak is remembered after a break; multiple workouts on the same day each count; another user's workouts never count.

Save this prompt to prompts/streak.md with a summary. Run the tests, then commit. Don't push to main. Explain in plain English how the streak is calculated, including how the current week is handled.

## Summary of what was built

- **`app/streaks.py`** (new): all the streak logic. Nothing is stored; streaks are recalculated from the user's workouts, so edits and deletes stay correct.
  - `WORKOUTS_PER_WEEK = 3` is the one place the threshold lives. The pages read it too.
  - `weekly_counts` (filtered by `user_id`), `counting_weeks`, `current_streak`, `longest_streak`, and `streak_summary`, which gathers what the pages show.
- **`app/dashboard.py`, `dashboard.html`**: the streak card sits at the top of the Dashboard, including for a brand-new user with no workouts.
- **`app/main.py`, `workouts/list.html`**: the "🔥 X-week streak" badge, hidden at 0. It ignores search filters, since a streak is about all your workouts.
- **`base.html`**: streak card and badge styles. The card stacks on phones and goes side by side from tablet up. On phones the badge sits under the page title so "+ New workout" keeps its place.
- **Decisions the prompt left open**
  - "1 week" is singular.
  - If the streak is 0 but this week has started, the message counts down ("Log 2 more workouts this week to start a streak.").
  - Going past the target shows the real count ("4 / 3") with a full bar.
  - Workouts dated after today are ignored. The form already blocks them.
  - Longest streak includes the in-progress week once it counts, so longest is never less than current.
- **Tests** (`tests/test_streaks.py`, 30 tests): the requested rules, Monday/Sunday and New Year boundaries, the week rolling over, other users' data, the card, the badge, and the empty states.
- **Checked visually** at 320, 375 and 1280px, in light and dark mode.
- **No schema change**, no migration.
