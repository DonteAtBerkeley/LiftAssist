# LiftAssist database schema

Five tables. Every table except `users` belongs to a user through a `user_id` column (or, for `sets`, through its workout), so every query for user data can be filtered by the logged-in user.

Defined in `app/models.py`; created by the migrations in `migrations/versions/`.

Migrations, in order:
1. `58b9e7417e17`: create `users`
2. `abfe6ec09ba8`: add `workouts`, `exercises`, `sets`, `stars`
3. `82ee7e891171`: add `exercises.is_bodyweight`

Every `user_id`, `workout_id` and `exercise_id` column has an index.

## Tables

### users
| Column | Type | Rules |
|---|---|---|
| id | integer | primary key |
| email | varchar(255) | required, unique (indexed); stored lowercase |
| password_hash | varchar(255) | required; a hash, never the plain password |
| created_at | datetime | required, set automatically |

### workouts — one training session
| Column | Type | Rules |
|---|---|---|
| id | integer | primary key |
| user_id | integer | required → `users.id` (deleting the user deletes their workouts) |
| date | date | required |
| title | varchar(120) | optional, e.g. "Push day"; the form fills a blank one with day, date, and type, e.g. "Wednesday, Nov 4 — Lift" |
| workout_type | varchar(10) | required; must be `'lift'` or `'run'` |
| duration_min | integer | optional; ≥ 0 |
| distance_mi | float | optional (runs only); ≥ 0 |
| effort | integer | optional; 1–5 |
| notes | text | optional |
| created_at | datetime | required, set automatically |

### exercises — a user's personal list of movements
| Column | Type | Rules |
|---|---|---|
| id | integer | primary key |
| user_id | integer | required → `users.id` |
| name | varchar(120) | required; unique **per user** (two users can each have "Back squat") |
| rep_min | integer | required, default 8; ≥ 1 |
| rep_max | integer | required, default 12; ≥ rep_min (the Exercises page form is stricter: min must be less than max, and max ≤ 1000) |
| is_bodyweight | boolean | required, default false. Copied from the built-in catalog (`app/catalog.py`) the first time the user logs that exercise; custom names are `false` (weighted). Added in migration `82ee7e891171`, which also tags existing exercises whose names match a bodyweight catalog entry. |

The built-in exercise catalog (about 100 common exercises, each "weighted" or "bodyweight") lives in code, not in this table. It's only a list of suggestions: a row is created here when a user actually logs one. Names match ignoring case and extra spaces, so "bench press" and "Bench Press" are the same exercise, and a catalog exercise is saved with the catalog's spelling.

### sets — one set of one exercise inside one workout
| Column | Type | Rules |
|---|---|---|
| id | integer | primary key |
| workout_id | integer | required → `workouts.id` (deleting the workout deletes its sets) |
| exercise_id | integer | required → `exercises.id` (an exercise with logged sets can't be deleted) |
| set_number | integer | required; ≥ 1 |
| weight_lb | float | required; ≥ 0. A blank weight is saved as 0: silently for bodyweight exercises, and only after a "Save anyway" confirmation for weighted ones |
| reps | integer | required; ≥ 1 |

### stars — "I starred this workout" (junction table)
| Column | Type | Rules |
|---|---|---|
| id | integer | primary key |
| user_id | integer | required → `users.id` |
| workout_id | integer | required → `workouts.id` (deleting the workout deletes its stars) |
| created_at | datetime | required, set automatically |
| | | the pair (user_id, workout_id) is unique: one star per user per workout |

## How the tables connect

- **users → workouts: one-to-many.** One user has many workouts; each workout has exactly one owner.
- **users → exercises: one-to-many.** Each user builds their own exercise list.
- **workouts → sets: one-to-many.** A workout is made of many sets. Delete the workout and its sets go with it.
- **exercises → sets: one-to-many.** Every set is "of" one exercise, so an exercise collects every set ever done for it, across all workouts.
- **workouts ↔ exercises: many-to-many, through `sets`.** A workout includes many exercises, and an exercise shows up in many workouts. There's no direct link between them — the `sets` table *is* the link, and it carries extra facts (weight, reps, set number).
- **users ↔ workouts: many-to-many, through `stars`.** Each `stars` row says "this user starred this workout". Today you can only star your own workouts, but the table is shaped so it doesn't care.

## Diagram

```
                    ┌─────────────┐
                    │    users    │
                    └─────────────┘
          1 │             1 │             1 │
            │               │               │
          * ▼             * ▼             * ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │  exercises  │   │  workouts   │   │    stars    │
   └─────────────┘   └─────────────┘   └─────────────┘
          1 │         1 │       1 │           ▲ *
            │           │         └───────────┘
          * ▼         * ▼
          ┌───────────────┐
          │     sets      │   each set = 1 workout + 1 exercise
          └───────────────┘

1 ──▶ * means "one … has many …"
```

Compact version (`──<` = one-to-many, read left to right):

```
users ──< workouts ──< sets >── exercises >── users
  │          │
  └──< stars >┘
```

## In the code (SQLAlchemy relationships)

| From | Attribute | Gives you |
|---|---|---|
| `User` | `.workouts`, `.exercises`, `.stars` | that user's rows |
| `User` | `.starred_workouts` | workouts the user starred (read-only shortcut) |
| `Workout` | `.user`, `.sets` (ordered by set_number), `.stars` | |
| `Workout` | `.exercises` | distinct exercises in the workout (read-only, via sets) |
| `Exercise` | `.user`, `.sets` | every set ever logged for it |
| `Exercise` | `.workouts` | every workout it appears in (read-only, via sets) |
| `Set` | `.workout`, `.exercise` | |
| `Star` | `.user`, `.workout` | |

Deletes cascade both in Python (SQLAlchemy `cascade="all, delete-orphan"`) and in the database (`ON DELETE CASCADE`). SQLite only enforces foreign keys when asked, so `app/models.py` turns on `PRAGMA foreign_keys=ON` for every SQLite connection.

## Plan vs. built

Compared with PLAN.md section 3, the tables, columns and relationships are the same, with these differences:

- **`exercises.is_bodyweight` is new.** It wasn't in the plan. It was added in Feature 4 (validation, round 2) along with the built-in exercise catalog. It lets the app treat a blank weight as 0 lb without a warning, track bodyweight PRs by reps, and give bodyweight exercises a "+1 rep" recommendation instead of a weight change.
- **`workouts.title` is optional and gets a default.** The plan gave only examples. The form fills a blank title with the day, date and type.
- **No PR or recommendation tables.** As in the plan, PRs, streaks, stats and recommendations are not stored. They're calculated from `workouts` and `sets` every time, so editing or deleting a workout always keeps them correct.
- **More rules in the database than planned.** There are check constraints (type is lift/run, effort 1–5, reps ≥ 1, weight ≥ 0, set_number ≥ 1, rep_min ≥ 1, rep_max ≥ rep_min, duration/distance ≥ 0) and cascade deletes. `ON DELETE RESTRICT` stops an exercise with logged sets from being deleted.
- **Concrete types.** The plan's "number" became `integer`, or `float` for `distance_mi` and `weight_lb`. "date" became `date` for `workouts.date` and `datetime` for the `created_at` columns.
