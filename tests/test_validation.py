"""Feature 4: server-side validation on the workout form (new and edit).

Every rejected submission must save nothing, show a message next to the field,
show the summary at the top, and keep what the user typed.
"""

from datetime import date, timedelta

import pytest

from app import db
from app.models import Exercise, Set, Workout
from tests.test_workouts import create, lift_data, signup

SUMMARY = b"Please fix the highlighted fields."


@pytest.fixture
def logged_in(client):
    signup(client, "a@example.com")


def run_data(**overrides):
    data = lift_data(title="Long run", workout_type="run", distance_mi="6.2")
    data.update(overrides)
    return data


def count(model):
    return db.session.execute(db.select(db.func.count(model.id))).scalar()


def assert_rejected(client, data, message, url="/workouts/new"):
    r = client.post(url, data=data)
    assert r.status_code == 200  # form shown again, not a redirect
    assert message.encode() in r.data, r.data.decode()
    assert SUMMARY in r.data
    return r


# --- The three required tests -------------------------------------------------

def test_blank_title_is_rejected_and_nothing_saved(client, logged_in):
    assert_rejected(client, lift_data(title="   "), "Give this workout a name.")
    assert (count(Workout), count(Set), count(Exercise)) == (0, 0, 0)


def test_run_without_distance_is_rejected_and_nothing_saved(client, logged_in):
    assert_rejected(client, run_data(distance_mi=""), "How far did you run?")
    assert count(Workout) == 0


def test_set_with_zero_reps_is_rejected_and_nothing_saved(client, logged_in):
    assert_rejected(client, lift_data(**{"sets-1-reps": "0"}), "Reps must be at least 1.")
    assert (count(Workout), count(Set), count(Exercise)) == (0, 0, 0)


# --- Every other rule ---------------------------------------------------------

@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"date": ""}, "Pick a date — today or earlier."),
        ({"date": "not-a-date"}, "Pick a date — today or earlier."),
        ({"date": (date.today() + timedelta(days=1)).isoformat()}, "Pick a date — today or earlier."),
        ({"workout_type": "swim"}, "Choose lift or run."),
        ({"workout_type": ""}, "Choose lift or run."),
        ({"effort": "0"}, "Effort must be a whole number from 1 to 5."),
        ({"effort": "6"}, "Effort must be a whole number from 1 to 5."),
        ({"effort": "3.5"}, "Effort must be a whole number from 1 to 5."),
        ({"effort": "abc"}, "Effort must be a whole number from 1 to 5."),
        ({"duration_min": "0"}, "Duration must be more than 0 minutes."),
        ({"duration_min": "-30"}, "Duration must be more than 0 minutes."),
        ({"duration_min": "45.5"}, "Duration must be a whole number of minutes."),
        ({"sets-0-exercise": ""}, "Add the exercise name."),
        ({"sets-0-reps": "-3"}, "Reps must be at least 1."),
        ({"sets-0-reps": "five"}, "Reps must be a whole number."),
        ({"sets-0-weight_lb": "-5"}, "Weight can&#39;t be negative."),
        ({"sets-0-weight_lb": "inf"}, "Weight can&#39;t be negative."),
        ({"sets-0-weight_lb": "heavy"}, "Weight must be a number"),
    ],
)
def test_lift_rules(client, logged_in, overrides, message):
    assert_rejected(client, lift_data(**overrides), message)
    assert count(Workout) == 0


@pytest.mark.parametrize(
    "distance, message",
    [("0", "Distance must be more than 0 miles."), ("-2", "Distance must be more than 0 miles."),
     ("nan", "Distance must be more than 0 miles."), ("far", "Distance must be a number")],
)
def test_run_distance_rules(client, logged_in, distance, message):
    assert_rejected(client, run_data(distance_mi=distance), message)
    assert count(Workout) == 0


def test_lift_needs_at_least_one_set(client, logged_in):
    data = {k: v for k, v in lift_data().items() if not k.startswith("sets-")}
    data.update({"sets-0-exercise": "", "sets-0-weight_lb": "", "sets-0-reps": ""})
    assert_rejected(client, data, "Add at least one set.")
    assert count(Workout) == 0


def test_today_and_blank_optional_fields_are_fine(client, logged_in):
    wid = create(client, lift_data(date=date.today().isoformat(), duration_min="", effort="",
                                   notes="", **{"sets-0-weight_lb": "0"}))
    w = db.session.get(Workout, wid)
    assert (w.duration_min, w.effort, w.sets[0].weight_lb) == (None, None, 0)


def test_hidden_fields_for_the_other_type_are_ignored(client, logged_in):
    # A run with a junk set row still saves (sets aren't shown or saved for runs)...
    wid = create(client, run_data(**{"sets-0-reps": "0", "sets-1-weight_lb": "-5"}))
    assert db.session.get(Workout, wid).sets == []
    # ...and a lift with junk in the hidden distance box still saves.
    wid = create(client, lift_data(distance_mi="-1"))
    assert db.session.get(Workout, wid).distance_mi is None


def test_errors_keep_everything_typed(client, logged_in):
    r = assert_rejected(client, lift_data(title="", effort="2", notes="Knee felt off",
                                          **{"sets-2-reps": "0"}), "Give this workout a name.")
    body = r.data.decode()
    assert 'value="2026-11-03"' in body
    assert 'value="60"' in body
    assert '<option selected value="2">' in body
    assert "Knee felt off" in body
    assert 'name="sets-0-exercise" value="Back squat"' in body
    assert 'name="sets-2-exercise" value="Lunge"' in body
    assert 'name="sets-2-reps" value="0"' in body
    assert 'aria-invalid="true"' in body  # the bad fields are highlighted


def test_message_appears_next_to_its_field(client, logged_in):
    body = assert_rejected(client, lift_data(**{"sets-1-reps": "0"}), "Reps must be at least 1.").data.decode()
    row = body.index('name="sets-1-reps"')
    assert row < body.index("Reps must be at least 1.") < body.index('name="sets-2-exercise"')


def test_no_summary_on_a_fresh_form(client, logged_in):
    assert SUMMARY not in client.get("/workouts/new").data


def test_bad_edit_leaves_workout_unchanged(client, logged_in):
    wid = create(client, lift_data())
    assert_rejected(client, lift_data(title="", **{"sets-0-reps": "0"}),
                    "Give this workout a name.", url=f"/workouts/{wid}/edit")
    assert_rejected(client, lift_data(workout_type="run", distance_mi=""),
                    "How far did you run?", url=f"/workouts/{wid}/edit")
    db.session.expire_all()
    w = db.session.get(Workout, wid)
    assert (w.title, w.workout_type, len(w.sets), w.sets[0].reps) == ("Leg Day", "lift", 3, 5)
