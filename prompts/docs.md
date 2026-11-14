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

---

# Docs, second run: live URL and Learning column (docs/readme-reality)

## Prompt

Stay on the current branch. Don't create a new one. Don't change any app code. If any of the files or sections below already exist from an earlier run, update them instead of duplicating them.

1. README.md in the repo root, for someone who has never seen this project:
   - What LiftAssist does (2–3 sentences) and its main features
   - Live URL: https://liftassist.onrender.com (note the free tier may take ~60 seconds to wake up)
   - Tools used: Claude Code, Python/Flask, Flask-SQLAlchemy/Migrate/Login/WTF, Neon Postgres, Render, Chart.js, Pico CSS, pytest
   - How to run it locally, step by step (clone, virtual environment, install requirements, .env from .env.example, flask db upgrade, flask run)
   - How to run the tests
   - Links to PLAN.md and schema.md

2. schema.md: make sure it matches the actual database, including the is_bodyweight column. At the bottom, add a short "Plan vs. built" note comparing it with PLAN.md section 3.

3. PLAN.md: do NOT edit any existing text in the original plan. At the very bottom, add (or update) a section titled "## Plan vs. Reality" with this table:
   | Planned feature | Shipped / Changed / Cut | Status (Done/Backlogged) | Learning | What changed and why (one line) |
   One row per feature (1–10) from section 2. Fill in Shipped/Changed/Cut, Status, and "What changed and why" accurately and honestly from the git history, merged PRs, and prompts/ folder. Include the real changes: optional title with a default, the exercise catalog and bodyweight weight warning, bodyweight PRs tracked by reps, PRs calculated instead of stored, the Exercises page with editable rep ranges, deload rounding to 5 lb, and the layout fix bundled into the search PR.

   For the Learning column, use EXACTLY this text for each feature. Don't reword it:
   1: Nothing surprised me about getting the login working and deployed. It was normal.
   2: It's really important to have data in your workout app, and to have data that only applies to what it should apply to.
   3: You really need to pay attention when building and testing the main workout form.
   4: You really need to use the app to see how effective it is. Something can work in theory, but that doesn't mean it will be used the way you intend. Actually using it is extremely important.
   5: Super important feature. You can star your workouts, create favorites, and easily go back to see them.
   6: You always need to check your work.
   7: Color coordination is important. Color needs to pop so the dashboard can be read and assessed easily, so it actually tells the story you want it to tell.
   8: You can't treat every kind of workout the same. It has to fit the workout, like calisthenics versus lifting weights.
   9: A weekly streak is more realistic and keeps people more engaged than a daily streak.
   10: It's extremely helpful to not have to think about what your next rep is going to be when you're working out. It looks at your previous reps and weight and tells you how much to add on top of that, which is super good and important.

4. Save this prompt to prompts/docs.md (append if the file exists).

Then commit everything to this branch with the message "Add README, update schema, add Plan vs. Reality". Don't push to main. When done, show me the final Plan vs. Reality table.

## Summary of what was built

- **`README.md`**: already existed from the first run; replaced the `YOUR-LIVE-URL` placeholder with https://liftassist.onrender.com. Nothing else needed changing.
- **`schema.md`**: already matched `app/models.py` and the three migrations, including `exercises.is_bodyweight`, and already had its "Plan vs. built" section. No changes.
- **`PLAN.md`**: the original plan is untouched. In the existing "## Plan vs. Reality" table, replaced each "TODO" in the Learning column with the exact text given. The other columns were checked again against PRs #4–#24 and still hold.
- No app code changed.
