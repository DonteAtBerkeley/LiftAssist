# Feature 1 — Sign up and login (feature/auth)

## Prompt

I'm building LiftAssist, a workout log web app for my class. Read PLAN.md first — it's the blueprint. This branch (feature/auth) is Feature 1 ONLY: sign up and login. Don't build workouts, stars, or the dashboard yet.

Tech stack (from PLAN.md section 5):
- Python 3.12, Flask using an app factory, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Werkzeug password hashing, gunicorn
- Pico CSS via CDN, mobile-first, accent color #F26B1D
- Database: read DATABASE_URL from the environment (convert "postgres://" to "postgresql://"); fall back to a local SQLite file if it's not set. Read SECRET_KEY from the environment with a dev fallback.

Build:
1. Project structure: app/__init__.py, app/models.py, app/auth.py (blueprint), app/main.py (home page), templates/base.html with a nav bar (logged out: "Log in" / "Sign up"; logged in: user's email + "Log out"), run.py, requirements.txt, .gitignore (venv, .env, instance/, __pycache__, *.db), .env.example.
2. A users table exactly as in PLAN.md section 3 (id, email, password_hash, created_at). Set up Flask-Migrate and create the first migration.
3. Sign up page: email, password, confirm password. Friendly error messages: email required and valid; "An account with that email already exists"; password at least 8 characters; passwords must match. Store only the hashed password. Log the user in after signing up.
4. Log in page: wrong email or password shows "Email or password is incorrect." Log out link works.
5. Home page requires login and says "Welcome, <email>". Logged-out visitors get redirected to log in.
6. pytest setup: tests/conftest.py with an app using in-memory SQLite and CSRF disabled for tests, plus one test: sign up → log out → log in succeeds.
7. Create CLAUDE.md with project rules for all future work: never commit to main; one feature per branch; every database query for user data must be filtered by the logged-in user; save key prompts to prompts/<feature>.md; run pytest before committing.
8. Save this exact prompt into prompts/auth.md, followed by a short summary of what you built.

When done: run the tests, tell me the exact commands to run the app locally so I can try it, and explain in plain English (for a non-engineer) how sign up and login work in this app: what happens to the password, and how the app knows who is logged in. Then commit to feature/auth. Do NOT push to main or merge anything.

## Summary of what was built

- **App factory** (`app/__init__.py`): sets up SQLAlchemy, Flask-Migrate, Flask-Login and CSRF protection. Reads `DATABASE_URL` (rewrites `postgres://` → `postgresql://`) or falls back to `instance/liftassist.db`; reads `SECRET_KEY` with a dev fallback; loads `.env` if present.
- **`users` table** (`app/models.py`): `id`, `email` (unique, indexed, stored lowercase), `password_hash`, `created_at`. First Alembic migration in `migrations/versions/`.
- **Sign up** (`/signup`): email, password, confirm password, with the requested friendly errors. Password hashed with Werkzeug before saving; user is logged in right after.
- **Log in** (`/login`): shows "Email or password is incorrect." for any wrong combo (doesn't reveal which part was wrong). Honors `?next=` but only for links within this site.
- **Log out** (`/logout`): a POST form styled as a link in the nav, so it's CSRF-protected.
- **Home** (`/`): login required, says "Welcome, <email>"; logged-out visitors are redirected to log in.
- **UI**: `base.html` with Pico CSS (CDN), orange `#F26B1D` accent, nav that changes when logged in.
- **Tests**: `tests/conftest.py` (in-memory SQLite, CSRF off) + `tests/test_auth.py` (sign up → log out → log in).
- **Notes**: Postgres driver is `psycopg` v3 (the default for the pinned SQLAlchemy 2.1). Code targets Python 3.12 (`.python-version`); it was tested locally on 3.13 because 3.12 isn't installed on this laptop.
