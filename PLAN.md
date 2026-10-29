# PLAN.md — LiftAssist

## 1. Pitch

I'm building **LiftAssist**, a workout log for lifting sessions and runs, because my training is currently scattered across phone notes and memory. I never know what I lifted last week, so I guess at weights instead of progressing on purpose. I'll use it **4–5 times a week**, right after every workout, mostly from my phone at the gym.

## 2. Features (in build order)

**Spine**

1. **Sign up and login.** As a new visitor, I want to create an account with my email and a password, then log in and log out, so that my training history is private to me.
2. **Data model.** As a user, I want my workouts, exercises, and sets stored in connected tables, so that I can see every set I've done for a given lift across all my sessions.
3. **Create / read / update / delete workouts.** As a lifter, I want to log a workout with a date, type (lift or run), duration, effort rating (1–5), and notes, then add sets (exercise, weight in lb, reps) or run details (distance in miles), so that I have a full record of each session. I can view my list, open one workout's detail page, edit it, and delete it after an "Are you sure?" confirmation.
4. **Validation.** As a user, I want a friendly message if I leave out a required field (date, type, exercise, reps, or a run's distance) or enter something impossible (negative weight, 0 reps, effort outside 1–5), so that bad data never gets saved.
5. **Stars.** As a lifter, I want to star standout workouts (a great leg day, a race) and see them in a "Starred" view, so that I can repeat sessions that went well.
6. **Find things.** As a user, I want to search workouts by title, notes, or exercise name, filter by type (lift / run) and date range, and sort by newest, oldest, or highest effort, so that I can find a specific session fast.
7. **Dashboard.** As a lifter, I want a dashboard with a chart of weekly training volume (lb lifted) and miles run over the last 8 weeks, plus stats for workouts this month, total volume this month, average workouts per week (last 8 weeks), and my best month by volume, so that I can see whether I'm actually training consistently.

**My 3 features**

8. **PR tracker.** As a lifter, I want the app to flag a new personal record when I save a workout (heaviest weight for an exercise, best estimated 1-rep max using the Epley formula `weight × (1 + reps/30)`, or fastest pace on a run of 1+ mile), and show a "My PRs" page with my current best for each exercise, so that I see my progress without digging through history.
9. **Streak counter.** As a user, I want to see my current and longest **weekly** streak (consecutive Mon–Sun weeks with at least 3 workouts), so that I stay consistent without being punished for rest days.
10. **Weight and rep recommendations.** As a lifter, I want each exercise to suggest my next target before I log it, so that I progress on purpose instead of guessing. Each exercise has a target rep range (default 8–12). The rule ("double progression"):
    - If **every** working set last session hit the top of the range → suggest **+5 lb** and drop to the bottom of the range.
    - If **any** set fell below the bottom of the range for **2 sessions in a row** → suggest **−10%** weight (deload).
    - Otherwise → suggest the **same weight, +1 rep** per set.
    - No history yet → no suggestion ("Log a session to get a recommendation").

## 3. Database

| Table | Column | Type | Notes |
|---|---|---|---|
| **users** | id | number | **Primary key** |
| | email | text | Unique, required |
| | password_hash | text | Hashed, never plain text |
| | created_at | date | |
| **workouts** (main item) | id | number | **Primary key** |
| | user_id | number | → users.id |
| | date | date | Required |
| | title | text | e.g., "Push day", "Long run" |
| | workout_type | text | "lift" or "run" |
| | duration_min | number | |
| | distance_mi | number | Runs only, otherwise empty |
| | effort | number | 1–5 |
| | notes | text | Optional |
| | created_at | date | |
| **exercises** | id | number | **Primary key** |
| | user_id | number | → users.id (each user has their own exercise list) |
| | name | text | e.g., "Back squat"; unique per user |
| | rep_min | number | Default 8 (used by recommendations) |
| | rep_max | number | Default 12 |
| **sets** | id | number | **Primary key** |
| | workout_id | number | → workouts.id |
| | exercise_id | number | → exercises.id |
| | set_number | number | 1, 2, 3… |
| | weight_lb | number | 0 allowed for bodyweight |
| | reps | number | Must be ≥ 1 |
| **stars** (junction) | id | number | **Primary key** |
| | user_id | number | → users.id |
| | workout_id | number | → workouts.id |
| | created_at | date | One star per user per workout (unique pair) |

**Relationships**

- users → workouts: **one-to-many** (a user has many workouts)
- users → exercises: **one-to-many**
- workouts → sets: **one-to-many** (deleting a workout deletes its sets)
- workouts ↔ exercises: **many-to-many**, through `sets`
- users ↔ workouts: **many-to-many**, through `stars`

```
users ──< workouts ──< sets >── exercises >── users
  │          │
  └──< stars >┘
```

## 4. Tests

1. **Data isolation.** Given User A has logged a workout titled "Leg Day", when User B logs in and opens the workouts list and tries to open Leg Day's URL directly, then User B's list is empty and the direct URL returns "Not found" (404).
2. **Dashboard stat (monthly volume).** Given a user logged one workout this month with 3 sets of back squat at 100 lb × 5 reps and 2 sets of lunges at 50 lb × 10 reps, when the dashboard calculates this month's total volume, then it shows **2,500 lb** (3×100×5 + 2×50×10).

## 5. Technologies

| Choice | Why |
|---|---|
| **Claude Code** (coding agent) | Works directly in my repo and terminal, so it can make branches, run tests, and push. |
| **Python 3.12 + Flask** (web framework) | Small and readable, so I can follow how each page gets and saves data. |
| **Flask-SQLAlchemy + Flask-Migrate** | Defines tables as Python classes and tracks schema changes safely. |
| **PostgreSQL on Neon** (live database), **SQLite** (on my laptop) | Neon's free tier doesn't expire; SQLite needs zero setup for local testing. |
| **Flask-Login + Werkzeug password hashing** (sign up / login) | Email + password accounts; passwords are stored only as hashes; every query is filtered to the logged-in user. |
| **Flask-WTF** (forms) | Handles form validation messages and protects forms from cross-site attacks (CSRF). |
| **Render** (hosting, via gunicorn) | Deploys automatically from `main` on GitHub, so every merged PR updates the live URL. |
| **Chart.js** (dashboard charts) | One script tag, no build step. |
| **Pico CSS** (styling) | Clean, mobile-friendly defaults without writing much CSS. |
| **pytest** (tests) | Python's standard test tool, and it runs in one command. |

## 6. Design

- **Feel:** fast, minimal, built for one hand at the gym. Big tap targets; logging a set takes no more than 3 taps.
- **Colors:** charcoal `#1F2328` text, off-white `#FAFAF7` background, one energetic orange accent `#F26B1D` for buttons, stars, and PR badges. Dark mode follows the phone's setting.
- **Style:** card-based workout list, bold numbers on the dashboard, a small 🏆 badge on PR sets.
- **Inspiration:** **Strong** (fast set-by-set logging) and **Strava** (clean stats and weekly charts).

## 7. Risks and cuts

- **Least sure I can build:** the **recommendations** feature. The rule needs "last session" and "two sessions in a row" per exercise, which is the trickiest query in the app, and edge cases (skipped weeks, changing rep ranges) could break it.
- **Cut first if short on time:** (1) run pace PRs (keep lift PRs only), (2) the deload rule in recommendations (keep only +5 lb / +1 rep), (3) dark mode.
