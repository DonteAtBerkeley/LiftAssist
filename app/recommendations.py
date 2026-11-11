"""Feature 10: what to lift next, using "double progression".

Add reps at the same weight until every set reaches the top of the rep range, then add
weight and drop back to the bottom of the range.

Nothing is stored. Every suggestion is worked out from the sets already saved, so editing
or deleting a workout can never leave a stale one behind.

Rules for a weighted exercise, checked in this order:
1. No history: no suggestion.
2. Deload: a set fell below rep_min in both of the last 2 sessions.
3. Level up: every set in the last session reached rep_max.
4. Otherwise: same weight, lowest reps from last session + 1 (never above rep_max).

A bodyweight exercise never changes weight: it suggests the best set from last session + 1 rep.

A "session" is one workout's sets of one exercise. 0 lb sets on a weighted exercise are
skipped, as they are for PRs: a forgotten weight says nothing about what to lift next.

Every query is filtered by `user_id`. Sets belong to a user through their workout.
"""

import math
from collections import namedtuple
from dataclasses import dataclass

from . import db

WEIGHT_INCREMENT_LB = 5
DELOAD_PERCENT = 10
DEFAULT_REP_MIN = 8
DEFAULT_REP_MAX = 12
SESSIONS_NEEDED_FOR_DELOAD = 2

NO_HISTORY_MESSAGE = "Log a session to get a recommendation."

NONE, DELOAD, LEVEL_UP, SAME_WEIGHT, BODYWEIGHT = "none", "deload", "level_up", "same_weight", "bodyweight"

LoggedSet = namedtuple("LoggedSet", ["weight", "reps"])


@dataclass(frozen=True)
class Recommendation:
    kind: str
    message: str
    weight: float | None = None  # None means "leave the weight alone"
    reps: int | None = None

    @property
    def has_suggestion(self):
        return self.kind != NONE

    @property
    def display(self):
        """ "140 lb × 8", "13 reps", or None when there's nothing to suggest."""
        if not self.has_suggestion:
            return None
        if self.weight is None:
            return f"{self.reps} reps"
        return f"{self.weight:g} lb × {self.reps}"

    def as_dict(self):
        return {
            "kind": self.kind,
            "has_suggestion": self.has_suggestion,
            "weight": self.weight,
            "reps": self.reps,
            "display": self.display,
            "message": self.message,
        }


# --- The rules ---------------------------------------------------------------
# A session is a list of LoggedSet. `sessions` is a list of sessions, newest first.

def round_to_increment(weight):
    """To the nearest 5 lb (halves round up)."""
    return math.floor(weight / WEIGHT_INCREMENT_LB + 0.5) * WEIGHT_INCREMENT_LB


def deload_weight(weight):
    """10% lighter, rounded to the nearest 5 lb. Never 0, and never heavier than `weight`."""
    rounded = round_to_increment(weight * (100 - DELOAD_PERCENT) / 100)
    return rounded if 0 < rounded <= weight else weight


def last_weight(session):
    return max(s.weight for s in session)


def lowest_reps(session):
    return min(s.reps for s in session)


def best_reps(session):
    return max(s.reps for s in session)


def fell_below(session, rep_min):
    return lowest_reps(session) < rep_min


def reached_top(session, rep_max):
    return lowest_reps(session) >= rep_max


def needs_deload(sessions, rep_min):
    recent = sessions[:SESSIONS_NEEDED_FOR_DELOAD]
    return len(recent) == SESSIONS_NEEDED_FOR_DELOAD and all(fell_below(s, rep_min) for s in recent)


def next_reps(session, rep_max):
    return min(lowest_reps(session) + 1, rep_max)


def recommend(sessions, rep_min=DEFAULT_REP_MIN, rep_max=DEFAULT_REP_MAX, is_bodyweight=False):
    """The Recommendation for one exercise, given its sessions (newest first)."""
    if not sessions:
        return Recommendation(NONE, NO_HISTORY_MESSAGE)

    last = sessions[0]
    if is_bodyweight:
        reps = best_reps(last) + 1
        return Recommendation(BODYWEIGHT, f"Beat your best: aim for {reps} reps.", reps=reps)

    weight = last_weight(last)
    if needs_deload(sessions, rep_min):
        target = deload_weight(weight)
        return Recommendation(
            DELOAD,
            f"Tough couple of sessions — drop to {target:g} lb × {rep_min} and build back up.",
            target,
            rep_min,
        )
    if reached_top(last, rep_max):
        target = weight + WEIGHT_INCREMENT_LB
        return Recommendation(
            LEVEL_UP,
            f"You hit {rep_max} on every set — go up to {target:g} lb × {rep_min}.",
            target,
            rep_min,
        )
    reps = next_reps(last, rep_max)
    return Recommendation(SAME_WEIGHT, f"Same weight, aim for {reps} reps per set.", weight, reps)


# --- Reading the user's history ----------------------------------------------

def load_sessions(user_id, exclude_workout_id=None, exercise_id=None):
    """{exercise_id: [session, ...]} for this user, newest session first.

    "Newest" is by workout date; two workouts on the same day go by which was logged later.
    `exclude_workout_id` is the workout being edited, which can't be its own "last session".
    """
    from .models import Exercise, Set, Workout  # local import: models.py imports this module

    query = (
        db.select(Set.exercise_id, Set.workout_id, Set.weight_lb, Set.reps, Exercise.is_bodyweight)
        .select_from(Set)
        .join(Workout, Workout.id == Set.workout_id)
        .join(Exercise, Exercise.id == Set.exercise_id)
        .where(Workout.user_id == user_id, Exercise.user_id == user_id)
        .order_by(Workout.date.desc(), Workout.id.desc(), Set.set_number)
    )
    if exclude_workout_id is not None:
        query = query.where(Workout.id != exclude_workout_id)
    if exercise_id is not None:
        query = query.where(Exercise.id == exercise_id)

    grouped = {}
    for ex_id, workout_id, weight, reps, is_bodyweight in db.session.execute(query):
        if weight > 0 or is_bodyweight:
            grouped.setdefault(ex_id, {}).setdefault(workout_id, []).append(LoggedSet(weight, reps))
    return {ex_id: list(by_workout.values()) for ex_id, by_workout in grouped.items()}


def _recommend_exercise(exercise, sessions):
    return recommend(sessions, exercise.rep_min, exercise.rep_max, exercise.is_bodyweight)


def for_exercise(user_id, exercise, exclude_workout_id=None):
    """The Recommendation for one exercise."""
    sessions = load_sessions(user_id, exclude_workout_id, exercise.id).get(exercise.id, [])
    return _recommend_exercise(exercise, sessions)


def for_exercises(user_id, exercises):
    """{exercise_id: Recommendation} for a list of the user's exercises, in one query."""
    sessions = load_sessions(user_id)
    return {e.id: _recommend_exercise(e, sessions.get(e.id, [])) for e in exercises}
