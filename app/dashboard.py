"""Feature 7: the Dashboard page. The math lives in app/stats.py; this only gathers and shows it."""

from datetime import date

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from . import stats
from .workouts import has_any_workouts

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    if not has_any_workouts():
        return render_template("dashboard.html", empty=True)

    today = date.today()
    uid = current_user.id  # every stat below is for the logged-in user only
    weeks = stats.weekly_series(uid, today)
    return render_template(
        "dashboard.html",
        empty=False,
        today=today,
        workouts_this_month=stats.workouts_this_month(uid, today),
        volume_this_month=stats.volume_this_month(uid, today),
        avg_per_week=stats.avg_workouts_per_week(uid, today),
        best_month=stats.best_month_by_volume(uid),
        chart={
            "labels": [w["week_start"].strftime("%b %-d") for w in weeks],
            "volume": [w["volume"] for w in weeks],
            "miles": [w["miles"] for w in weeks],
        },
        weeks=weeks,
    )
