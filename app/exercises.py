"""Feature 10: the Exercises page and the suggestion endpoint. The rules live in app/recommendations.py.

Security rule: every lookup goes through the logged-in user, so another user's exercise
or workout simply "doesn't exist" (404) for you.
"""

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from . import db, recommendations
from .forms import RepRangeForm
from .models import Exercise, Workout

bp = Blueprint("exercises", __name__)


def _own_exercises():
    return db.session.execute(
        db.select(Exercise).filter_by(user_id=current_user.id).order_by(func.lower(Exercise.name))
    ).scalars().all()


def _get_own_exercise(exercise_id):
    exercise = db.session.execute(
        db.select(Exercise).filter_by(id=exercise_id, user_id=current_user.id)
    ).scalar()
    if exercise is None:
        abort(404)
    return exercise


def _require_own_workout(workout_id):
    found = db.session.execute(
        db.select(Workout.id).filter_by(id=workout_id, user_id=current_user.id)
    ).first()
    if found is None:
        abort(404)


def _render_list(failed_form=None, failed_id=None):
    """The page. `failed_form` replaces one row's form, so its errors and typed values show."""
    exercises = _own_exercises()
    suggestions = recommendations.for_exercises(current_user.id, exercises)
    rows = [
        {
            "exercise": e,
            "recommendation": suggestions[e.id],
            "form": failed_form if e.id == failed_id else RepRangeForm(formdata=None, obj=e),
        }
        for e in exercises
    ]
    return render_template("exercises.html", rows=rows, saved=request.args.get("saved", type=int))


@bp.route("/exercises")
@login_required
def index():
    return _render_list()


@bp.route("/exercises/<int:exercise_id>/rep-range", methods=["POST"])
@login_required
def update_rep_range(exercise_id):
    exercise = _get_own_exercise(exercise_id)
    form = RepRangeForm()
    if not form.validate_on_submit():
        return _render_list(form, exercise.id)
    exercise.rep_min = form.rep_min.data
    exercise.rep_max = form.rep_max.data
    db.session.commit()
    return redirect(url_for("exercises.index", saved=exercise.id, _anchor=f"exercise-{exercise.id}"))


@bp.route("/exercises/<int:exercise_id>/recommendation")
@login_required
def recommendation(exercise_id):
    """JSON for the workout form. `?exclude_workout=<id>` is the workout being edited."""
    exercise = _get_own_exercise(exercise_id)
    exclude = request.args.get("exclude_workout", type=int)
    if exclude is not None:
        _require_own_workout(exclude)
    return jsonify(recommendations.for_exercise(current_user.id, exercise, exclude).as_dict())
