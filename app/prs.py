"""Feature 8: personal records (PRs), worked out from the sets and workouts already saved.

Nothing is stored. Every answer is recalculated from the user's current data, so editing
or deleting a workout can never leave a stale PR behind.

What counts
- Weighted exercise: heaviest weight, and best estimated 1-rep max (Epley). 0 lb sets are skipped.
- Bodyweight exercise: most reps in a single set.
- Run of 1 mile or more: longest distance, and fastest pace (which also needs a duration).

Ties: the first set to reach a number holds the record. Matching it isn't a new PR.

Numbers are compared as they're displayed (est. 1RM in whole lb, pace in whole seconds),
so a "new PR" is always visibly better than the old one.

Every query is filtered by `user_id`. Sets belong to a user through their workout.
"""

import math
from dataclasses import dataclass
from datetime import date

from . import db
from .models import Exercise, Set, Workout

MIN_RUN_MILES = 1

WEIGHT, E1RM, REPS, PACE, DISTANCE = "weight", "e1rm", "reps", "pace", "distance"
LABELS = {
    WEIGHT: "Heaviest",
    E1RM: "Est. 1RM",
    REPS: "Max reps",
    PACE: "Fastest pace",
    DISTANCE: "Longest run",
}


@dataclass(frozen=True)
class Performance:
    """One number that could be a record, and where it came from."""

    metric: str
    value: float
    workout_id: int
    date: date
    exercise_id: int | None = None  # None for runs
    exercise_name: str | None = None
    set_id: int | None = None

    @property
    def key(self):
        """What this competes against: the same metric on the same exercise."""
        return (self.metric, self.exercise_id)


@dataclass(frozen=True)
class Snapshot:
    """The records as they stood just before a save."""

    others: dict  # best of every workout except the one being saved
    own: dict  # best of the saved workout's previous version (empty for a new workout)


# --- Math --------------------------------------------------------------------

def epley_1rm(weight, reps):
    """weight × (1 + reps/30), rounded to the nearest lb (halves round up)."""
    return math.floor(weight * (30 + reps) / 30 + 0.5)


def pace_seconds(duration_min, distance_mi):
    """Seconds per mile, or None if the run is under 1 mile or has no duration."""
    if not duration_min or not distance_mi or distance_mi < MIN_RUN_MILES:
        return None
    return math.floor(duration_min * 60 / distance_mi + 0.5)


def format_pace(seconds):
    """465 -> "7:45 /mi"."""
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d} /mi"


def format_value(metric, value):
    if metric == PACE:
        return format_pace(value)
    if metric == DISTANCE:
        return f"{value:g} mi"
    if metric == REPS:
        return f"{value} rep{'' if value == 1 else 's'}"
    return f"{value:g} lb"


def set_metrics(weight, reps, is_bodyweight):
    """Which records one set competes for, as {metric: value}."""
    if is_bodyweight:
        return {REPS: reps}
    if weight <= 0:
        return {}
    return {WEIGHT: weight, E1RM: epley_1rm(weight, reps)}


def run_metrics(distance_mi, duration_min):
    """Which records one run competes for, as {metric: value}."""
    if not distance_mi or distance_mi < MIN_RUN_MILES:
        return {}
    metrics = {DISTANCE: round(distance_mi, 2)}
    pace = pace_seconds(duration_min, distance_mi)
    if pace is not None:
        metrics[PACE] = pace
    return metrics


def beats(metric, new, old):
    """Is `new` strictly better than `old`? Lower is better for pace, higher for the rest."""
    return new < old if metric == PACE else new > old


# --- Reading the user's history ----------------------------------------------

def performances(user_id, workout_id=None):
    """Every record-eligible number for this user, oldest first. Optionally one workout only."""
    lifts = (
        db.select(Set.id, Set.weight_lb, Set.reps, Exercise.id, Exercise.name,
                  Exercise.is_bodyweight, Workout.id, Workout.date)
        .select_from(Set)
        .join(Workout, Workout.id == Set.workout_id)
        .join(Exercise, Exercise.id == Set.exercise_id)
        .where(Workout.user_id == user_id, Exercise.user_id == user_id)
        .order_by(Workout.date, Workout.id, Set.set_number)
    )
    runs = (
        db.select(Workout.id, Workout.date, Workout.distance_mi, Workout.duration_min)
        .where(Workout.user_id == user_id, Workout.workout_type == "run")
        .order_by(Workout.date, Workout.id)
    )
    if workout_id is not None:
        lifts = lifts.where(Workout.id == workout_id)
        runs = runs.where(Workout.id == workout_id)

    found = []
    for set_id, weight, reps, ex_id, ex_name, bodyweight, w_id, day in db.session.execute(lifts):
        for metric, value in set_metrics(weight, reps, bodyweight).items():
            found.append(Performance(metric, value, w_id, day, ex_id, ex_name, set_id))
    for w_id, day, distance, duration in db.session.execute(runs):
        for metric, value in run_metrics(distance, duration).items():
            found.append(Performance(metric, value, w_id, day))
    return found


def best_records(items):
    """{key: best Performance}. `items` must be oldest first, so the earliest holder keeps a tie."""
    best = {}
    for item in items:
        current = best.get(item.key)
        if current is None or beats(item.metric, item.value, current.value):
            best[item.key] = item
    return best


# --- Did this save set a new PR? ---------------------------------------------

def take_snapshot(user_id, workout_id=None):
    """Call just before saving. `workout_id` is the workout being edited (None for a new one)."""
    others, own = [], []
    for item in performances(user_id):
        (own if item.workout_id == workout_id else others).append(item)
    return Snapshot(others=best_records(others), own=best_records(own))


def new_prs(user_id, workout_id, before):
    """The saved workout's bests that are new PRs, given the Snapshot from before the save.

    A best is a new PR only if it beats the user's other workouts (no other workouts with
    that exercise means nothing to beat) and improves on this workout's previous version
    (so re-saving a workout that already holds a PR doesn't celebrate it again).
    """
    found = []
    for key, record in best_records(performances(user_id, workout_id)).items():
        rival = before.others.get(key)
        if rival is None or not beats(record.metric, record.value, rival.value):
            continue
        previous = before.own.get(key)
        if previous is not None and not beats(record.metric, record.value, previous.value):
            continue
        found.append(record)
    return found


def pr_messages(records):
    """One celebratory line per exercise or run record."""
    lifts = {}
    messages = []
    for record in records:
        if record.exercise_id is None:
            messages.append(
                f"🏆 New PR: {LABELS[record.metric]} — {format_value(record.metric, record.value)}!"
            )
            continue
        text = format_value(record.metric, record.value)
        if record.metric == E1RM:
            text += " est. 1RM"
        lifts.setdefault(record.exercise_name, {})[record.metric] = text
    lift_messages = [
        f"🏆 New PR: {name} — {', '.join(parts[m] for m in (WEIGHT, E1RM, REPS) if m in parts)}!"
        for name, parts in lifts.items()
    ]
    return lift_messages + messages


# --- What the pages show -----------------------------------------------------

def set_badges(user_id, workout_id):
    """{set_id: [labels]} for the sets in this workout that currently hold an all-time record."""
    badges = {}
    for record in best_records(performances(user_id)).values():
        if record.workout_id == workout_id and record.set_id is not None:
            badges.setdefault(record.set_id, []).append(LABELS[record.metric])
    return badges


def _entry(record):
    return {
        "label": LABELS[record.metric],
        "display": format_value(record.metric, record.value),
        "date": record.date,
        "workout_id": record.workout_id,
    }


def pr_summary(user_id):
    """Everything the My PRs page needs: {"pace", "distance", "exercises"}.

    `pace` and `distance` are None until a qualifying run exists. `exercises` is one
    {"name", "metrics"} row per exercise, sorted by name.
    """
    records = best_records(performances(user_id))
    exercises = {}
    for metric in (WEIGHT, E1RM, REPS):
        for (key_metric, _), record in records.items():
            if key_metric == metric:
                row = exercises.setdefault(
                    record.exercise_id, {"name": record.exercise_name, "metrics": []}
                )
                row["metrics"].append(_entry(record))
    pace = records.get((PACE, None))
    distance = records.get((DISTANCE, None))
    return {
        "pace": _entry(pace) if pace else None,
        "distance": _entry(distance) if distance else None,
        "exercises": sorted(exercises.values(), key=lambda row: row["name"].lower()),
    }
