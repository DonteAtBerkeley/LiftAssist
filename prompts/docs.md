# Docs — README, schema, Plan vs. Reality (docs/readme-reality)

## Prompt

Stay on the current branch. Don't create a new one. Don't change any app code.

1. Create README.md in the repo root for someone who has never seen this project:
   - What LiftAssist does (2–3 sentences) and its main features
   - Live URL: YOUR-LIVE-URL (note the free tier may take ~60 seconds to wake up)
   - Tools used: Claude Code, Python/Flask, Flask-SQLAlchemy/Migrate/Login/WTF, Neon Postgres, Render, Chart.js, Pico CSS, pytest
   - How to run it locally, step by step (clone, virtual environment, install requirements, .env from .env.example, flask db upgrade, flask run)
   - How to run the tests
   - Links to PLAN.md and schema.md

2. Make sure schema.md is up to date with the actual database, including the is_bodyweight column. At the bottom, add a short "Plan vs. built" note comparing it with PLAN.md section 3.

3. Do NOT edit any existing text in PLAN.md. Add a new section at the very bottom titled "## Plan vs. Reality" with this table:
   | Planned feature | Shipped / Changed / Cut | Status (Done/Backlogged) | Learning | What changed and why (one line) |
   One row per feature (1–10) from section 2. Use the git history, merged PRs, and prompts/ folder to fill in the Shipped/Changed/Cut, Status, and "What changed and why" columns accurately and honestly. Include the real changes: optional title with a default, the exercise catalog and bodyweight weight warning, bodyweight PRs tracked by reps, PRs calculated instead of stored, the Exercises page with editable rep ranges, deload rounding to 5 lb, and the layout fix bundled into the search PR. Leave the Learning column as "TODO" in every row — I'll write those myself.

Save this prompt to prompts/docs.md. Commit to this branch. Don't push to main.

## Summary of what was built

- **`README.md`** (rewritten): what LiftAssist does, its main features, the live URL placeholder with the free-tier wake-up note, the tools used, step-by-step local setup (`flask --app run.py db upgrade` / `run`, since there's no `.flaskenv`), how to run `pytest`, and links to PLAN.md and schema.md.
- **`schema.md`**: checked against a fresh database built from all three migrations; it already matched, including `exercises.is_bodyweight`. Added the migration list, the indexes note, that emails are stored lowercase, and the Exercises page's stricter rep-range rule. Added a "Plan vs. built" section comparing it with PLAN.md section 3.
- **`PLAN.md`**: existing text untouched. Appended "## Plan vs. Reality" with one row per feature (1–10), filled in from the git history, PRs #4–#24 and `prompts/`. Learning is "TODO" in every row. A closing line notes that nothing on the section 7 cut list was cut.
- No app code changed.
