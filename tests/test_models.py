from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Exercise, Set, Star, User, Workout


def make_user(email="a@example.com"):
    user = User(email=email)
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def make_exercise(user, name):
    exercise = Exercise(user=user, name=name)
    db.session.add(exercise)
    return exercise


def make_workout(user, **kwargs):
    fields = {"date": date(2026, 11, 3), "workout_type": "lift", "title": "Leg day"}
    fields.update(kwargs)
    workout = Workout(user=user, **fields)
    db.session.add(workout)
    db.session.commit()
    return workout


def assert_rejected(obj):
    db.session.add(obj)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_relationships_connect_both_ways(app):
    user = make_user()
    squat = make_exercise(user, "Back squat")
    lunge = make_exercise(user, "Lunge")
    workout = make_workout(user)
    db.session.add_all([
        Set(workout=workout, exercise=squat, set_number=1, weight_lb=100, reps=5),
        Set(workout=workout, exercise=squat, set_number=2, weight_lb=100, reps=5),
        Set(workout=workout, exercise=lunge, set_number=3, weight_lb=50, reps=10),
    ])
    db.session.add(Star(user=user, workout=workout))
    db.session.commit()

    assert user.workouts == [workout]
    assert {e.name for e in user.exercises} == {"Back squat", "Lunge"}
    assert {e.name for e in workout.exercises} == {"Back squat", "Lunge"}
    assert squat.workouts == [workout]
    assert len(squat.sets) == 2 and squat.sets[0].workout is workout
    assert user.starred_workouts == [workout]
    assert workout.stars[0].user is user


def test_exercise_rep_range_defaults(app):
    user = make_user()
    ex = make_exercise(user, "Bench press")
    db.session.add(ex)
    db.session.commit()
    assert (ex.rep_min, ex.rep_max) == (8, 12)


def test_deleting_workout_deletes_its_sets_and_stars(app):
    user = make_user()
    squat = make_exercise(user, "Back squat")
    workout = make_workout(user)
    workout.sets.append(Set(exercise=squat, set_number=1, weight_lb=100, reps=5))
    db.session.add(Star(user=user, workout=workout))
    db.session.commit()

    db.session.delete(workout)
    db.session.commit()

    assert db.session.query(Set).count() == 0
    assert db.session.query(Star).count() == 0
    assert db.session.query(Exercise).count() == 1  # the exercise itself stays


def test_database_cascade_without_orm(app):
    """ON DELETE CASCADE also works at the database level (raw SQL delete)."""
    user = make_user()
    squat = make_exercise(user, "Back squat")
    workout = make_workout(user)
    workout.sets.append(Set(exercise=squat, set_number=1, weight_lb=100, reps=5))
    db.session.add(Star(user=user, workout=workout))
    db.session.commit()

    db.session.execute(db.delete(Workout).where(Workout.id == workout.id))
    db.session.commit()

    assert db.session.query(Set).count() == 0
    assert db.session.query(Star).count() == 0


def test_exercise_name_unique_per_user(app):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    db.session.add_all([Exercise(user=alice, name="Deadlift"), Exercise(user=bob, name="Deadlift")])
    db.session.commit()  # same name for different users is fine

    assert_rejected(Exercise(user_id=alice.id, name="Deadlift"))


def test_one_star_per_user_per_workout(app):
    user = make_user()
    workout = make_workout(user)
    db.session.add(Star(user=user, workout=workout))
    db.session.commit()

    assert_rejected(Star(user_id=user.id, workout_id=workout.id))


@pytest.mark.parametrize(
    "fields",
    [
        {"workout_type": "swim"},
        {"effort": 0},
        {"effort": 6},
        {"duration_min": -1},
        {"distance_mi": -0.5},
    ],
)
def test_workout_checks(app, fields):
    user = make_user()
    base = {"date": date(2026, 11, 3), "workout_type": "lift"}
    base.update(fields)
    assert_rejected(Workout(user_id=user.id, **base))


@pytest.mark.parametrize(
    "fields",
    [{"reps": 0}, {"weight_lb": -5}, {"set_number": 0}],
)
def test_set_checks(app, fields):
    user = make_user()
    ex = make_exercise(user, "Back squat")
    workout = make_workout(user)
    base = {"set_number": 1, "weight_lb": 100, "reps": 5}
    base.update(fields)
    assert_rejected(Set(workout_id=workout.id, exercise_id=ex.id, **base))


def test_bodyweight_set_allowed(app):
    user = make_user()
    ex = make_exercise(user, "Pull-up")
    workout = make_workout(user)
    workout.sets.append(Set(exercise=ex, set_number=1, weight_lb=0, reps=8))
    db.session.commit()
    assert workout.sets[0].weight_lb == 0


def test_exercise_rep_range_checks(app):
    user = make_user()
    assert_rejected(Exercise(user_id=user.id, name="Curl", rep_min=0, rep_max=10))
    assert_rejected(Exercise(user_id=user.id, name="Curl", rep_min=12, rep_max=8))
