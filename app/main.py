from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from .search import SORTS, TYPES, read_filters
from .stars import starred_ids
from .streaks import streak_summary
from .workouts import has_any_workouts, own_workouts

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def home():
    """Home page after login: the logged-in user's workouts as cards, searchable via ?q=&type=&from=&to=&sort=."""
    filters = read_filters(request.args)
    workouts = own_workouts(filters)
    return render_template(
        "workouts/list.html",
        workouts=workouts,
        starred=starred_ids(),
        filters=filters,
        types=TYPES,
        sorts=SORTS,
        # Only worth asking when the list is empty: "nothing matches" vs "nothing logged yet".
        has_any=bool(workouts) or has_any_workouts(),
        streak=streak_summary(current_user.id),
    )
