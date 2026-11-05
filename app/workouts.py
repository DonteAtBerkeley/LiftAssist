"""Feature 3: create, read, update, and delete workouts.

Security rule: every lookup goes through the logged-in user. `_get_own_workout`
filters by both the workout id AND current_user.id, so another user's workout
simply "doesn't exist" (404) for you.
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from . import db
from .forms import WorkoutForm
from .models import Exercise, Set, Workout

bp = Blueprint("workouts", __name__, url_prefix="/workouts")


# --- Queries (all scoped to the logged-in user) ------------------------------

def own_workouts():
    """The logged-in user's workouts, newest first, with their sets preloaded."""
    return db.session.execute(
        db.select(Workout)
        .filter_by(user_id=current_user.id)
        .options(selectinload(Workout.sets))
        .order_by(Workout.date.desc(), Workout.id.desc())
    ).scalars().all()


def _get_own_workout(workout_id):
    workout = db.session.execute(
        db.select(Workout).filter_by(id=workout_id, user_id=current_user.id)
    ).scalar()
    if workout is None:
        abort(404)
    return workout


def _own_exercise_names():
    return db.session.execute(
        db.select(Exercise.name).filter_by(user_id=current_user.id).order_by(Exercise.name)
    ).scalars().all()


def _get_or_create_exercise(name, cache):
    """Find the user's exercise by name (ignoring case), or create it for them."""
    name = " ".join(name.split())  # trim and collapse inner spaces
    key = name.lower()
    if key not in cache:
        exercise = db.session.execute(
            db.select(Exercise).filter(
                Exercise.user_id == current_user.id, func.lower(Exercise.name) == key
            )
        ).scalar()
        if exercise is None:
            exercise = Exercise(user_id=current_user.id, name=name)
            db.session.add(exercise)
        cache[key] = exercise
    return cache[key]


# --- Form <-> workout --------------------------------------------------------

def _apply_form(form, workout):
    """Copy the submitted form onto the workout and rebuild its sets."""
    workout.date = form.date.data
    workout.title = (form.title.data or "").strip() or None
    workout.workout_type = form.workout_type.data
    workout.duration_min = form.duration_min.data
    workout.effort = form.effort.data
    workout.notes = (form.notes.data or "").strip() or None

    # Rebuild the set list from the form. delete-orphan removes any sets the user dropped.
    workout.sets.clear()
    if workout.workout_type == "run":
        workout.distance_mi = form.distance_mi.data
        return
    workout.distance_mi = None
    cache = {}
    # no_autoflush: don't let the exercise lookups save half-built sets mid-loop.
    with db.session.no_autoflush:
        for number, row in enumerate(form.filled_sets(), start=1):
            workout.sets.append(
                Set(
                    exercise=_get_or_create_exercise(row.exercise.data, cache),
                    set_number=number,
                    weight_lb=row.weight_lb.data or 0,  # blank weight = bodyweight
                    reps=row.reps.data,
                )
            )


def _prefill_sets(form, workout):
    for s in workout.sets:
        form.sets.append_entry(
            {"exercise": s.exercise.name, "weight_lb": s.weight_lb, "reps": s.reps}
        )


def _render_form(form, workout=None):
    # Always show at least one empty set row so the user can start typing.
    if not form.sets.entries:
        form.sets.append_entry()
    return render_template(
        "workouts/form.html",
        form=form,
        workout=workout,
        exercise_names=_own_exercise_names(),
    )


def group_sets_by_exercise(sets):
    """[(exercise, [sets...]), ...] in the order each exercise first appears."""
    groups = {}
    for s in sets:
        groups.setdefault(s.exercise_id, (s.exercise, []))[1].append(s)
    return list(groups.values())


# --- Routes ------------------------------------------------------------------

@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = WorkoutForm()
    if form.validate_on_submit():
        workout = Workout(user_id=current_user.id)
        db.session.add(workout)
        _apply_form(form, workout)
        db.session.commit()
        flash("Workout saved.")
        return redirect(url_for("workouts.detail", workout_id=workout.id))
    return _render_form(form)


@bp.route("/<int:workout_id>")
@login_required
def detail(workout_id):
    workout = _get_own_workout(workout_id)
    return render_template(
        "workouts/detail.html", workout=workout, groups=group_sets_by_exercise(workout.sets)
    )


@bp.route("/<int:workout_id>/edit", methods=["GET", "POST"])
@login_required
def edit(workout_id):
    workout = _get_own_workout(workout_id)
    if request.method == "GET":
        form = WorkoutForm(obj=workout)
        form.sets.entries = []  # obj= can't fill the set rows; do it by hand below
        form.sets.last_index = -1
        _prefill_sets(form, workout)
    else:
        form = WorkoutForm()
        if form.validate_on_submit():
            _apply_form(form, workout)
            db.session.commit()
            flash("Workout updated.")
            return redirect(url_for("workouts.detail", workout_id=workout.id))
    return _render_form(form, workout)


@bp.route("/<int:workout_id>/delete", methods=["GET", "POST"])
@login_required
def delete(workout_id):
    workout = _get_own_workout(workout_id)
    if request.method == "POST":
        db.session.delete(workout)  # its sets and stars go with it (cascade)
        db.session.commit()
        flash("Workout deleted.")
        return redirect(url_for("main.home"))
    # GET = the "Are you sure?" page. Nothing is deleted until that page's form is submitted.
    return render_template("workouts/confirm_delete.html", workout=workout)
