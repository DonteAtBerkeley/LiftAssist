# Feature 7 — Dashboard (feature/dashboard)

## Prompt

Read PLAN.md (sections 2, 4, 6), CLAUDE.md, and schema.md. This branch is Feature 7: the dashboard, plus required test #2 from PLAN.md section 4.

Build a Dashboard page (add "Dashboard" to the nav), using only the logged-in user's data:
1. Four stat cards: Workouts this month; Total volume this month (lb, where volume = weight × reps summed over all sets); Average workouts per week over the last 8 weeks (one decimal); Best month by volume (month name + lb).
2. A Chart.js chart (loaded from CDN) covering the last 8 weeks (Mon–Sun): bars for weekly volume (lb) and a line for weekly miles run, with two y-axes and clear labels. Use the accent color #F26B1D for one series and a neutral color for the other. It must look good on phone and desktop.
3. A friendly empty state if I have no workouts yet.

Put each stat calculation in its own small Python function in a separate module (e.g. app/stats.py) so it can be tested on its own, separate from the page.

Write the required dashboard test exactly as PLAN.md section 4 describes:
Given a user logged one workout this month with 3 sets of back squat at 100 lb × 5 reps and 2 sets of lunges at 50 lb × 10 reps, when the dashboard calculates this month's total volume, then it equals 2,500. Name it test_monthly_volume_is_correct and add a clear comment explaining it. Also add a check that another user's workouts don't count toward this user's volume.

Save this prompt to prompts/dashboard.md with a summary. Run the tests, then commit. Don't push to main. Explain in plain English how total volume is calculated, step by step, from the database to the number on screen.

## Summary of what was built

- **`app/stats.py`** (new): one small function per stat. Each takes `user_id` (and a `today` date that tests can pin) and only reads that user's workouts.
  - `volume_this_month` → `volume_between`: `SUM(sets.weight_lb * sets.reps)` over sets joined to their workout, filtered by `workouts.user_id` and the month's dates. Bodyweight sets are 0 lb, so they add 0.
  - `workouts_this_month`: counts lifts and runs in the calendar month.
  - `avg_workouts_per_week`: workouts in the last 8 Mon–Sun weeks (the current week counts as one) ÷ 8, to one decimal.
  - `best_month_by_volume`: groups volume by year + month and returns the top month and its lb (ties go to the more recent month). Returns `None` if no lifting has been logged.
  - `weekly_series`: 8 Monday-start buckets, oldest first, with volume and miles. Empty weeks show as 0, so the chart has no gaps.
  - Date helpers: `month_start`, `next_month_start`, `week_start`, `last_weeks_start`.
- **`app/dashboard.py`** (new blueprint, `GET /dashboard`, login required): gathers the stats for `current_user.id` and renders `dashboard.html`. If you have no workouts yet, it shows the empty state instead.
- **`dashboard.html`**:
  - Stat cards: 2×2 on phones, one row of 4 from 768px up.
  - Chart.js 4.4.1 from cdnjs: orange (#F26B1D) bars for volume on the left axis (lb, shown as "4k"), and a neutral gray line for miles on the right axis. Axis titles are hidden on phones, where the legend above the chart explains the series. The line uses straight segments, because a smoothed line dipped below 0. The neutral color has a light and a dark variant.
  - A "Show as a table" fallback gives the same numbers for screen readers, or if the CDN is blocked.
- **Nav**: a "Dashboard" link. On phones the nav's "+ New" link is hidden so the nav fits on one line; the list and dashboard pages have their own "+ New workout" button.
- **`lb` template filter**: 2500.0 → "2,500".
- **Tests** (`tests/test_stats.py`):
  - `test_monthly_volume_is_correct`: required test #2 from PLAN.md, giving 2,500 lb, plus a second user whose lifting doesn't change it.
  - One test for each stat function: month boundaries; runs and bodyweight count as 0 volume; avg/week window edges; best month across years and users; weekly buckets; date helpers.
  - Page tests: login required; the empty state; the page shows "2,500 lb" for User A, and User B sees only the empty state.
- **Checked visually** at 375, 768 and 1280px, in light and dark mode, with no horizontal overflow.
- **No schema change**, no migration.
