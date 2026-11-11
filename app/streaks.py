"""Feature 9: the weekly streak. Small functions, testable on their own.

Nothing is stored: streaks are recalculated from the user's workouts, so editing or
deleting a workout always keeps them correct.

Definitions
- A week runs Monday–Sunday and is identified by its Monday. A workout belongs to the
  week of its `date`, not the day it was typed in.
- A week "counts" if it has at least WORKOUTS_PER_WEEK workouts. Lifts and runs both
  count, and so does each workout on the same day.
- Current streak: consecutive counting weeks, walking back from the most recent completed
  week. The in-progress week joins the streak once it counts; until then it's skipped, so
  it can never break the streak.
- Longest streak: the most consecutive counting weeks ever.

`today` is a parameter (default: the server's date) so tests can pin it.
"""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import func

from . import db
from .models import Workout
from .stats import week_start

WORKOUTS_PER_WEEK = 3  # how many workouts make a week count toward a streak

ONE_WEEK = timedelta(weeks=1)


def weekly_counts(user_id, today):
    """{Monday: number of workouts that week} for this user, up to and including `today`."""
    counts = Counter()
    for day, workouts in db.session.execute(
        db.select(Workout.date, func.count(Workout.id))
        .where(Workout.user_id == user_id, Workout.date <= today)
        .group_by(Workout.date)
    ):
        counts[week_start(day)] += workouts
    return counts


def counting_weeks(counts, threshold=WORKOUTS_PER_WEEK):
    """The Mondays of the weeks that reached the threshold."""
    return {monday for monday, workouts in counts.items() if workouts >= threshold}


def current_streak(counting, today):
    """Consecutive counting weeks, ending this week if it counts, otherwise last week."""
    this_week = week_start(today)
    week = this_week if this_week in counting else this_week - ONE_WEEK
    streak = 0
    while week in counting:
        streak += 1
        week -= ONE_WEEK
    return streak


def longest_streak(counting):
    """The longest run of back-to-back counting weeks."""
    longest = run = 0
    previous = None
    for week in sorted(counting):
        run = run + 1 if previous is not None and week - previous == ONE_WEEK else 1
        longest = max(longest, run)
        previous = week
    return longest


def streak_summary(user_id, today=None):
    """Everything the pages show: current, longest, this_week (workouts so far), threshold."""
    today = today or date.today()
    counts = weekly_counts(user_id, today)
    counting = counting_weeks(counts)
    return {
        "current": current_streak(counting, today),
        "longest": longest_streak(counting),
        "this_week": counts[week_start(today)],
        "threshold": WORKOUTS_PER_WEEK,
    }
