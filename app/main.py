from flask import Blueprint, render_template
from flask_login import login_required

from .stars import starred_ids
from .workouts import own_workouts

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def home():
    """Home page after login: the logged-in user's workouts as cards, newest first."""
    return render_template("workouts/list.html", workouts=own_workouts(), starred=starred_ids())
