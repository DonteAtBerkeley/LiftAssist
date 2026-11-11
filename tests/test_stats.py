"""Feature 7: dashboard stats (app/stats.py) and the Dashboard page.

Most tests call the stat functions directly with a fixed `today`, so the answers
don't depend on when the tests run.
"""

from datetime import date

import pytest

from app import db, stats
from app.models import Exercise, Set, User, Workout

from tests.test_workouts import create, lift_data, signup

TODAY = date(2026, 11, 10)  # a Tuesday


# --- Helpers: build data straight in the database ----------------------------

def make_user(email):
    user = User(email=email)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def exercise(user, name):
    found = db.session.execute(db.select(Exercise).filter_by(user_id=user.id, name=name)).scalar()
    if found is None:
        found = Exercise(user_id=user.id, name=name)
        db.session.add(found)
    return found


def lift(user, day, *sets):
    """lift(user, date, ("Back Squat", 100, 5), ...) -> one lift workout with those sets."""
    w = Workout(user_id=user.id, date=day, workout_type="lift")
    db.session.add(w)
    for number, (name, weight, reps) in enumerate(sets, start=1):
        w.sets.append(Set(exercise=exercise(user, name), set_number=number, weight_lb=weight, reps=reps))
    db.session.commit()
    return w


def run(user, day, miles):
    w = Workout(user_id=user.id, date=day, workout_type="run", distance_mi=miles)
    db.session.add(w)
    db.session.commit()
    return w


@pytest.fixture
def alice(app):
    return make_user("alice@example.com")


@pytest.fixture
def bob(app):
    return make_user("bob@example.com")


# --- Required test #2 (PLAN.md section 4) ------------------------------------

def test_monthly_volume_is_correct(alice, bob):
    """PLAN.md §4, test 2 — Dashboard stat (monthly volume).

    Given  a user logged ONE workout this month with
             3 sets of back squat at 100 lb × 5 reps, and
             2 sets of lunges     at  50 lb × 10 reps,
    When   the dashboard calculates this month's total volume,
    Then   it equals 2,500 lb:
             back squat: 3 sets × (100 lb × 5 reps)  = 3 × 500 = 1,500
             lunges:     2 sets × ( 50 lb × 10 reps) = 2 × 500 = 1,000
             total                                             = 2,500

    Volume of one set is weight × reps; the month's volume is the sum over every set
    in every workout dated this month.
    """
    lift(alice, date(2026, 11, 3),
         ("Back Squat", 100, 5), ("Back Squat", 100, 5), ("Back Squat", 100, 5),
         ("Lunge", 50, 10), ("Lunge", 50, 10))

    assert stats.volume_this_month(alice.id, TODAY) == 2500

    # Another user's lifting this month must not count toward Alice's volume...
    lift(bob, date(2026, 11, 5), ("Deadlift", 400, 5), ("Back Squat", 300, 3))
    assert stats.volume_this_month(alice.id, TODAY) == 2500
    # ...and Bob only sees his own: 400×5 + 300×3 = 2,900.
    assert stats.volume_this_month(bob.id, TODAY) == 2900


# --- Each stat on its own ----------------------------------------------------

def test_monthly_volume_only_counts_this_calendar_month(alice):
    lift(alice, date(2026, 10, 31), ("Bench Press", 100, 10))  # last month
    lift(alice, date(2026, 11, 1), ("Bench Press", 100, 10))   # first day of this month
    lift(alice, date(2026, 11, 10), ("Bench Press", 50, 2))    # today
    assert stats.volume_this_month(alice.id, TODAY) == 1100


def test_monthly_volume_is_zero_with_only_runs_or_bodyweight(alice):
    run(alice, date(2026, 11, 2), 5)
    lift(alice, date(2026, 11, 4), ("Push-up", 0, 20))  # bodyweight sets are saved as 0 lb
    assert stats.volume_this_month(alice.id, TODAY) == 0


def test_workouts_this_month_counts_lifts_and_runs(alice, bob):
    lift(alice, date(2026, 11, 2), ("Bench Press", 100, 5))
    run(alice, date(2026, 11, 9), 3)
    run(alice, date(2026, 10, 30), 3)  # last month
    run(bob, date(2026, 11, 9), 3)     # someone else
    assert stats.workouts_this_month(alice.id, TODAY) == 2


def test_avg_workouts_per_week_over_last_8_weeks(alice, bob):
    # This week (Mon Nov 9 – today) is week 8; week 1 starts Mon Sep 21.
    for day in [date(2026, 9, 21), date(2026, 10, 1), date(2026, 10, 15), date(2026, 11, 9), date(2026, 11, 10)]:
        run(alice, day, 3)
    run(alice, date(2026, 9, 20), 3)  # Sunday before the window: not counted
    run(bob, date(2026, 11, 9), 3)    # someone else: not counted
    assert stats.avg_workouts_per_week(alice.id, TODAY) == round(5 / 8, 1)  # 0.6


def test_best_month_by_volume(alice, bob):
    lift(alice, date(2026, 9, 5), ("Back Squat", 100, 10))   # Sep: 1,000
    lift(alice, date(2026, 10, 5), ("Back Squat", 200, 10))  # Oct: 2,000 + 500 = 2,500
    lift(alice, date(2026, 10, 20), ("Lunge", 50, 10))
    lift(alice, date(2025, 10, 5), ("Back Squat", 100, 5))   # Oct of LAST year stays separate
    lift(bob, date(2026, 9, 5), ("Deadlift", 500, 10))       # Bob's 5,000 isn't Alice's
    assert stats.best_month_by_volume(alice.id) == (date(2026, 10, 1), 2500)


def test_best_month_is_none_without_lifts(alice):
    run(alice, date(2026, 11, 2), 5)
    assert stats.best_month_by_volume(alice.id) is None


def test_weekly_series_buckets_by_monday(alice, bob):
    lift(alice, date(2026, 11, 9), ("Bench Press", 100, 10))   # Mon, this week
    lift(alice, date(2026, 11, 10), ("Bench Press", 100, 5))   # Tue, this week
    run(alice, date(2026, 11, 8), 6.2)                         # Sun, last week
    run(alice, date(2026, 11, 2), 3.1)                         # Mon, last week
    lift(alice, date(2026, 9, 1), ("Bench Press", 999, 1))     # outside the 8 weeks
    run(bob, date(2026, 11, 9), 10)                            # someone else

    series = stats.weekly_series(alice.id, TODAY)

    assert len(series) == 8
    assert series[0]["week_start"] == date(2026, 9, 21)
    assert series[-1]["week_start"] == date(2026, 11, 9)
    assert all(w["week_start"].weekday() == 0 for w in series)  # all Mondays
    assert series[-1] == {"week_start": date(2026, 11, 9), "volume": 1500, "miles": 0}
    assert series[-2] == {"week_start": date(2026, 11, 2), "volume": 0, "miles": 9.3}
    assert sum(w["volume"] for w in series[:-1]) == 0


def test_date_helpers():
    assert stats.month_start(date(2026, 12, 31)) == date(2026, 12, 1)
    assert stats.next_month_start(date(2026, 12, 31)) == date(2027, 1, 1)
    assert stats.next_month_start(date(2026, 2, 28)) == date(2026, 3, 1)
    assert stats.week_start(date(2026, 11, 15)) == date(2026, 11, 9)  # Sunday -> its Monday
    assert stats.last_weeks_start(TODAY) == date(2026, 9, 21)


# --- The page ----------------------------------------------------------------

def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302


def test_dashboard_empty_state(client):
    signup(client, "a@example.com")
    body = client.get("/dashboard").get_data(as_text=True)
    assert "Nothing to chart yet." in body
    assert "weekly-chart" not in body


def test_dashboard_page_shows_own_stats_only(client):
    # User A logs the PLAN.md workout today...
    signup(client, "a@example.com")
    sets = {"sets-0-exercise": "Back squat", "sets-0-weight_lb": "100", "sets-0-reps": "5",
            "sets-1-exercise": "Back squat", "sets-1-weight_lb": "100", "sets-1-reps": "5",
            "sets-2-exercise": "Back squat", "sets-2-weight_lb": "100", "sets-2-reps": "5",
            "sets-3-exercise": "Lunge", "sets-3-weight_lb": "50", "sets-3-reps": "10",
            "sets-4-exercise": "Lunge", "sets-4-weight_lb": "50", "sets-4-reps": "10"}
    create(client, lift_data(date=date.today().isoformat(), **sets))
    body = client.get("/dashboard").get_data(as_text=True)
    assert 'data-stat="volume-this-month">2,500 <span class="unit">lb</span>' in body
    assert "weekly-chart" in body and "chart.umd.min.js" in body
    client.post("/logout")

    # ...and User B, with no workouts, sees the empty state, not A's numbers.
    signup(client, "b@example.com")
    body = client.get("/dashboard").get_data(as_text=True)
    assert "Nothing to chart yet." in body
    assert "2,500" not in body


def test_nav_has_dashboard_link(client):
    signup(client, "a@example.com")
    assert 'href="/dashboard"' in client.get("/").get_data(as_text=True)
