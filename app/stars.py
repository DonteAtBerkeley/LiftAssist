"""Feature 5: star standout workouts and list them on a "Starred" page.

Every star is one row in the single `stars` table: (user_id, workout_id), and the
pair is unique. Starring is a POST (a form button, never a plain link), and you can
only star your own workouts: `_get_own_workout` returns 404 for anyone else's.
"""

from urllib.parse import urlsplit

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from . import db
from .models import Star, Workout
from .workouts import _get_own_workout

bp = Blueprint("stars", __name__)


# --- Queries (all scoped to the logged-in user) ------------------------------

def starred_ids():
    """Ids of the workouts the logged-in user has starred, as a set (for drawing ☆ / ★)."""
    return set(
        db.session.execute(
            db.select(Star.workout_id).filter_by(user_id=current_user.id)
        ).scalars()
    )


def _own_star(workout_id):
    return db.session.execute(
        db.select(Star).filter_by(user_id=current_user.id, workout_id=workout_id)
    ).scalar()


def _back_to(workout_id):
    """Send the user back where they clicked, scrolled to the same card.

    Only same-site paths are followed, so a crafted form can't bounce you to another site.
    """
    target = request.form.get("next", "")
    if not target.startswith("/") or target.startswith("//") or "\\" in target or urlsplit(target).netloc:
        target = url_for("workouts.detail", workout_id=workout_id)
    return redirect(f"{target.split('#')[0]}#workout-{workout_id}")


# --- Routes ------------------------------------------------------------------

@bp.route("/workouts/<int:workout_id>/star", methods=["POST"])
@login_required
def star(workout_id):
    workout = _get_own_workout(workout_id)  # 404 if it isn't yours
    if _own_star(workout.id) is None:  # already starred → nothing to do (no duplicate row)
        db.session.add(Star(user_id=current_user.id, workout_id=workout.id))
        db.session.commit()
    return _back_to(workout.id)


@bp.route("/workouts/<int:workout_id>/unstar", methods=["POST"])
@login_required
def unstar(workout_id):
    workout = _get_own_workout(workout_id)  # 404 if it isn't yours
    existing = _own_star(workout.id)
    if existing is not None:
        db.session.delete(existing)
        db.session.commit()
    return _back_to(workout.id)


@bp.route("/starred")
@login_required
def starred():
    """Only the workouts I've starred, newest workout first."""
    workouts = db.session.execute(
        db.select(Workout)
        .join(Star, Star.workout_id == Workout.id)
        .filter(Star.user_id == current_user.id, Workout.user_id == current_user.id)
        .options(selectinload(Workout.sets))
        .order_by(Workout.date.desc(), Workout.id.desc())
    ).scalars().all()
    return render_template(
        "workouts/starred.html", workouts=workouts, starred={w.id for w in workouts}
    )
