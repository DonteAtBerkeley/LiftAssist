"""Feature 7: dashboard numbers. One small function per stat, testable on its own.

Every function takes the user's id and only ever reads that user's workouts
(`Workout.user_id == user_id`). Sets have no user_id of their own: they belong to a
user *through* their workout, so every volume query joins sets to workouts and
filters on the workout's owner.

Definitions
- Volume of a set = weight_lb × reps. Bodyweight sets are saved with 0 lb, so they add 0.
- "This month" = the calendar month containing `today`.
- Weeks run Monday–Sunday. "The last 8 weeks" = this week (so far) plus the 7 before it.

`today` is a parameter (default: the server's date) so tests can pin it.
"""

from datetime import date, timedelta

from sqlalchemy import extract, func

from . import db
from .models import Set, Workout

WEEKS = 8


# --- Date helpers ------------------------------------------------------------

def month_start(day):
    return day.replace(day=1)


def next_month_start(day):
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1)


def week_start(day):
    """The Monday on or before `day`."""
    return day - timedelta(days=day.weekday())


def last_weeks_start(today, weeks=WEEKS):
    """Monday of the first of the last `weeks` Mon–Sun weeks (the current week counts as one)."""
    return week_start(today) - timedelta(weeks=weeks - 1)


# --- Building blocks ----------------------------------------------------------

def _set_volume():
    """SQL for one set's volume: weight × reps."""
    return Set.weight_lb * Set.reps


def volume_between(user_id, start, end):
    """Total lb lifted (weight × reps over every set) in workouts dated start <= date < end."""
    total = db.session.execute(
        db.select(func.coalesce(func.sum(_set_volume()), 0))
        .select_from(Set)
        .join(Workout, Workout.id == Set.workout_id)
        .where(Workout.user_id == user_id, Workout.date >= start, Workout.date < end)
    ).scalar()
    return float(total)


def workouts_between(user_id, start, end):
    """How many workouts (lifts and runs) are dated start <= date < end."""
    return db.session.execute(
        db.select(func.count(Workout.id))
        .where(Workout.user_id == user_id, Workout.date >= start, Workout.date < end)
    ).scalar()


# --- The four stat cards -----------------------------------------------------

def workouts_this_month(user_id, today=None):
    today = today or date.today()
    return workouts_between(user_id, month_start(today), next_month_start(today))


def volume_this_month(user_id, today=None):
    """Total volume (lb) of every set in this calendar month's workouts."""
    today = today or date.today()
    return volume_between(user_id, month_start(today), next_month_start(today))


def avg_workouts_per_week(user_id, today=None, weeks=WEEKS):
    """Workouts in the last `weeks` Mon–Sun weeks, divided by `weeks`, to one decimal."""
    today = today or date.today()
    count = workouts_between(user_id, last_weeks_start(today, weeks), today + timedelta(days=1))
    return round(count / weeks, 1)


def best_month_by_volume(user_id):
    """(first day of the month, volume) for the user's highest-volume month ever, or None.

    Ties go to the more recent month. Months with only runs (0 lb) don't count.
    """
    year = extract("year", Workout.date)
    month = extract("month", Workout.date)
    volume = func.sum(_set_volume())
    row = db.session.execute(
        db.select(year, month, volume)
        .select_from(Set)
        .join(Workout, Workout.id == Set.workout_id)
        .where(Workout.user_id == user_id)
        .group_by(year, month)
        .having(volume > 0)
        .order_by(volume.desc(), year.desc(), month.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    return date(int(row[0]), int(row[1]), 1), float(row[2])


# --- The chart ---------------------------------------------------------------

def weekly_series(user_id, today=None, weeks=WEEKS):
    """One entry per Mon–Sun week, oldest first: {"week_start", "volume", "miles"}.

    Weeks with nothing logged are still included (as 0) so the chart has no gaps.
    """
    today = today or date.today()
    start = last_weeks_start(today, weeks)
    end = today + timedelta(days=1)
    buckets = {start + timedelta(weeks=i): {"volume": 0.0, "miles": 0.0} for i in range(weeks)}

    # Volume per workout date, then add each day into its week.
    for day, volume in db.session.execute(
        db.select(Workout.date, func.sum(_set_volume()))
        .select_from(Set)
        .join(Workout, Workout.id == Set.workout_id)
        .where(Workout.user_id == user_id, Workout.date >= start, Workout.date < end)
        .group_by(Workout.date)
    ):
        buckets[week_start(day)]["volume"] += float(volume or 0)

    for day, miles in db.session.execute(
        db.select(Workout.date, func.sum(Workout.distance_mi))
        .where(Workout.user_id == user_id, Workout.workout_type == "run",
               Workout.date >= start, Workout.date < end)
        .group_by(Workout.date)
    ):
        buckets[week_start(day)]["miles"] += float(miles or 0)

    return [
        {"week_start": monday, "volume": round(b["volume"]), "miles": round(b["miles"], 1)}
        for monday, b in sorted(buckets.items())
    ]
