# CLAUDE.md — LiftAssist project rules

PLAN.md is the blueprint. Read it before starting any feature.

## Rules for all work
1. **Never commit to `main`.** Never push to `main` or merge anything unless explicitly asked.
2. **One feature per branch** (e.g. `feature/auth`, `feature/workouts`). Build only the feature the branch is for.
3. **Every database query for user data must be filtered by the logged-in user** (`current_user.id`). Looking up another user's record by ID must return 404, never their data.
4. **Save key prompts** to `prompts/<feature>.md`, with a short summary of what was built.
5. **Run `pytest` before committing.** Do not commit with failing tests.

## Stack
- Python 3.12, Flask (app factory in `app/__init__.py`), Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Werkzeug hashing, gunicorn.
- Pico CSS via CDN, mobile-first, accent `#F26B1D`.
- `DATABASE_URL` from env (`postgres://` is rewritten to `postgresql://`); falls back to `instance/liftassist.db` (SQLite). `SECRET_KEY` from env with a dev fallback.

## Layout
- `app/models.py` tables · `app/forms.py` forms · `app/auth.py` auth blueprint · `app/main.py` home
- `app/templates/` Jinja templates (`base.html` has the nav)
- `migrations/` Alembic migrations — after changing models run `flask --app run.py db migrate -m "..."` and commit the new file.
- `tests/` pytest; `conftest.py` gives an in-memory SQLite app with CSRF disabled.

## Commands
```
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
flask --app run.py db upgrade
flask --app run.py run --debug
pytest
```
