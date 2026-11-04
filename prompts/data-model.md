# Feature 2 — Data model (feature/datamodel)

## Prompt

Read PLAN.md and CLAUDE.md. This branch is Feature 2 ONLY: the data model. No new pages yet.

Add these tables exactly as described in PLAN.md section 3, with a Flask-Migrate migration:
- workouts (belongs to a user)
- exercises (belongs to a user; name unique per user; rep_min default 8, rep_max default 12)
- sets (belongs to a workout and an exercise)
- stars (junction table: user_id + workout_id, unique pair)

Set up SQLAlchemy relationships both ways. Deleting a workout should delete its sets and its stars. Add database-level checks where reasonable (workout_type is "lift" or "run", effort 1–5, reps >= 1, weight >= 0).

Also create schema.md in the repo root: list every table, its columns and types, and explain in plain English how the tables connect (one-to-many, many-to-many through sets and stars). Include a simple text diagram.

Save this prompt to prompts/data-model.md with a short summary. Run the migration locally and the tests, then commit to this branch. Don't push to main. Finally, explain in plain English how a workout, its sets, and its exercises connect.

## Summary of what was built

- **Models** (`app/models.py`): `Workout`, `Exercise`, `Set`, `Star`, matching PLAN.md section 3, with relationships both ways (`user.workouts` ↔ `workout.user`, `workout.sets` ↔ `set.workout`, `exercise.sets` ↔ `set.exercise`, `workout.stars` / `user.stars` ↔ `star.workout` / `star.user`), plus read-only shortcuts `workout.exercises`, `exercise.workouts`, and `user.starred_workouts`.
- **Deletes**: deleting a workout deletes its sets and stars, both in SQLAlchemy and in the database (`ON DELETE CASCADE`). Deleting a user removes all their data. An exercise that still has logged sets can't be deleted (`ON DELETE RESTRICT`) so history is never silently lost. SQLite foreign keys are switched on with `PRAGMA foreign_keys=ON`.
- **Database checks**: workout_type in ('lift','run'); effort 1–5; duration and distance ≥ 0; reps ≥ 1; weight ≥ 0; set_number ≥ 1; rep_min ≥ 1 and rep_max ≥ rep_min; exercise name unique per user; one star per (user, workout).
- **Migration**: `migrations/versions/abfe6ec09ba8_add_workouts_exercises_sets_stars.py`. Verified upgrade → downgrade to base → upgrade on SQLite, and checked the generated Postgres SQL offline.
- **Docs**: `schema.md` with every table, the connections in plain English, and a text diagram.
- **Tests**: `tests/test_models.py` (relationships, defaults, cascades via ORM and raw SQL, uniqueness, every check constraint, bodyweight sets). 17 tests pass.
