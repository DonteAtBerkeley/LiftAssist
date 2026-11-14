# LiftAssist

LiftAssist is a mobile-first workout log for lifting sessions and runs. You log each workout with its sets (exercise, weight, reps) or run distance. The app then shows how your training is going: weekly volume and miles, personal records, a weekly streak, and a suggested weight and rep target for your next session. Every account is private, so you only ever see your own data.

**Live app:** https://liftassist.onrender.com
> It runs on Render's free tier, so the first visit after a quiet period can take about 60 seconds while the server wakes up.

## Main features

- **Accounts:** sign up, log in and log out with email and password. Passwords are stored only as hashes.
- **Workouts:** create, view, edit and delete workouts (date, type lift/run, duration, effort 1–5, notes). Lifts have sets; runs have a distance. Deleting asks "Are you sure?" first.
- **Exercise catalog:** about 100 built-in exercises, each tagged weighted or bodyweight, suggested as you type. You can still type your own exercise names.
- **Validation:** friendly messages for missing or impossible values. A blank title gets a default (e.g. "Wednesday, Nov 4 — Lift"). If you leave the weight blank on a weighted exercise, the app asks you to confirm before saving it as 0 lb.
- **Stars:** star standout workouts and see them on a Starred page.
- **Search, filter and sort:** search titles, notes and exercise names. Filter by type and date range, and sort by newest, oldest, effort or duration.
- **Dashboard:** stats for this month, average workouts per week and your best month, plus a Chart.js chart of weekly volume (lb) and miles over the last 8 weeks.
- **PR tracker:** flags a new personal record when you save a workout (heaviest weight, Epley est. 1-rep max, most reps for bodyweight exercises, fastest pace and longest run). Includes a My PRs page.
- **Weekly streak:** current and longest streak of Mon–Sun weeks with at least 3 workouts.
- **Recommendations:** suggests a weight and reps for each exercise as you log it, using a "double progression" rule. The Exercises page lets you edit each exercise's target rep range.

## Tools used

- **Claude Code**: the coding agent that built the app, feature by feature (prompts saved in [`prompts/`](prompts/))
- **Python 3.12 / Flask**: the web framework
- **Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF**: database models, migrations, login sessions and forms with CSRF protection
- **Neon Postgres**: the live database (SQLite is used locally)
- **Render**: hosting (served with gunicorn)
- **Chart.js**: dashboard chart
- **Pico CSS**: styling
- **pytest**: tests

## Run it locally

You need Python 3.12 and git.

1. **Clone the repo**
   ```bash
   git clone https://github.com/DonteatBerkeley/liftassist.git
   cd liftassist
   ```
2. **Create and activate a virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```
3. **Install the requirements**
   ```bash
   pip install -r requirements.txt
   ```
4. **Create your `.env` file** from the example:
   ```bash
   cp .env.example .env
   ```
   Set `SECRET_KEY` to any long random string. Leave `DATABASE_URL` commented out to use a local SQLite file (`instance/liftassist.db`). To use Postgres instead, set it to your connection string.
5. **Create the database tables**
   ```bash
   flask --app run.py db upgrade
   ```
6. **Start the app**
   ```bash
   flask --app run.py run --debug
   ```
   Open http://127.0.0.1:5000 and sign up for an account.

## Run the tests

With the virtual environment active, from the repo root:

```bash
pytest
```

The tests use an in-memory SQLite database, so they never touch your local or live data.

## More documentation

- [PLAN.md](PLAN.md): the original blueprint (pitch, features, database, tests, technologies, design, risks) plus a "Plan vs. Reality" comparison at the bottom
- [schema.md](schema.md): every database table and column and how they connect
