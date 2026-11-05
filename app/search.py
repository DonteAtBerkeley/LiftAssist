"""Feature 6: search, filter, and sort a list of workouts.

Everything comes from the URL's query string (?q=squat&type=lift&from=...&to=...&sort=effort),
so a filtered list can be bookmarked and the browser's back button works.

These helpers only *narrow* or *reorder* a query you hand them. The caller always starts
from a query that's already filtered to the logged-in user (`Workout.user_id == current_user.id`),
so search can never reach another user's workouts.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import or_

from . import db
from .models import Exercise, Set, Workout

TYPES = {"": "All", "lift": "Lift", "run": "Run"}
SORTS = {
    "newest": "Newest first",
    "oldest": "Oldest first",
    "effort": "Highest effort",
    "duration": "Longest duration",
}
DEFAULT_SORT = "newest"
MAX_QUERY_LENGTH = 100


@dataclass
class Filters:
    q: str = ""
    type: str = ""
    date_from: date | None = None
    date_to: date | None = None
    sort: str = DEFAULT_SORT

    @property
    def narrowing(self):
        """True if anything hides workouts (search text, type, or dates). Sort alone doesn't."""
        return bool(self.q or self.type or self.date_from or self.date_to)

    @property
    def active(self):
        """True if anything differs from the default view, so a "Clear" link is worth showing."""
        return self.narrowing or self.sort != DEFAULT_SORT

    @property
    def filter_count(self):
        """How many of the tucked-away filters are set (shown on the mobile "Filters" toggle)."""
        return sum([bool(self.type), bool(self.date_from), bool(self.date_to), self.sort != DEFAULT_SORT])


def _parse_date(value):
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return None  # a bad date is ignored rather than shown as an error


def read_filters(args):
    """Turn request.args into a Filters. Anything unknown or malformed falls back to the default."""
    q = " ".join((args.get("q") or "").split())[:MAX_QUERY_LENGTH]
    kind = args.get("type", "")
    sort = args.get("sort", DEFAULT_SORT)
    date_from, date_to = _parse_date(args.get("from")), _parse_date(args.get("to"))
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from  # "from Nov 30 to Nov 1" clearly means Nov 1–30
    return Filters(
        q=q,
        type=kind if kind in TYPES else "",
        date_from=date_from,
        date_to=date_to,
        sort=sort if sort in SORTS else DEFAULT_SORT,
    )


def _like_pattern(text):
    """'squ' -> '%squ%' (contains). %, _ and \\ typed by the user are matched literally."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _matches_text(q):
    """Title, notes, or any exercise in the workout's sets contains q (ignoring case)."""
    pattern = _like_pattern(q)
    # EXISTS (...) asks "does at least one matching set exist?" instead of joining every set,
    # so a workout with five matching sets still comes back exactly once.
    has_matching_exercise = (
        db.select(Set.id)
        .join(Exercise, Exercise.id == Set.exercise_id)
        .where(Set.workout_id == Workout.id, Exercise.name.ilike(pattern, escape="\\"))
        .exists()
    )
    return or_(
        Workout.title.ilike(pattern, escape="\\"),
        Workout.notes.ilike(pattern, escape="\\"),
        has_matching_exercise,
    )


def _order_by(sort):
    newest = (Workout.date.desc(), Workout.id.desc())
    if sort == "oldest":
        return (Workout.date.asc(), Workout.id.asc())
    if sort == "effort":
        # Workouts with no effort logged go last; ties are broken newest first.
        return (Workout.effort.is_(None), Workout.effort.desc(), *newest)
    if sort == "duration":
        return (Workout.duration_min.is_(None), Workout.duration_min.desc(), *newest)
    return newest


def apply_filters(query, f):
    """Narrow and sort a Workout query. `query` must already be limited to the current user."""
    if f.q:
        query = query.where(_matches_text(f.q))
    if f.type:
        query = query.where(Workout.workout_type == f.type)
    if f.date_from:
        query = query.where(Workout.date >= f.date_from)
    if f.date_to:
        query = query.where(Workout.date <= f.date_to)
    return query.order_by(*_order_by(f.sort))
