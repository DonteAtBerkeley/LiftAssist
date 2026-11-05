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


# --- Required tests -------------------------------------------------------------

def test_blank_title_saves_with_day_date_and_type(client, logged_in):
    # 2026-11-03 is a Tuesday; 2026-11-04 a Wednesday.
    wid = create(client, lift_data(title="   "))
    assert db.session.get(Workout, wid).title == "Tuesday, Nov 3 — Lift"
    wid = create(client, run_data(title="", date="2026-11-04"))
    assert db.session.get(Workout, wid).title == "Wednesday, Nov 4 — Run"


def test_clearing_title_on_edit_uses_default(client, logged_in):
    wid = create(client, lift_data())
    client.post(f"/workouts/{wid}/edit", data=lift_data(title=""))
    db.session.expire_all()
    assert db.session.get(Workout, wid).title == "Tuesday, Nov 3 — Lift"


def test_run_without_distance_is_rejected_and_nothing_saved(client, logged_in):
    assert_rejected(client, run_data(distance_mi=""), "How far did you run?")
    assert count(Workout) == 0


def test_run_without_distance_is_rejected_even_if_field_is_missing(client, logged_in):
    """The reported bug: a run with no distance must never save, however it's sent."""
    data = run_data()
    del data["distance_mi"]  # e.g. a hand-made request that skips the field
    assert_rejected(client, data, "How far did you run?")
    assert_rejected(client, run_data(distance_mi="   "), "How far did you run?")
    assert count(Workout) == 0


def test_editing_lift_into_run_without_distance_is_rejected(client, logged_in):
    wid = create(client, lift_data())
    assert_rejected(client, lift_data(workout_type="run"), "How far did you run?",
                    url=f"/workouts/{wid}/edit")
    db.session.expire_all()
    w = db.session.get(Workout, wid)
    assert (w.workout_type, w.distance_mi, len(w.sets)) == ("lift", None, 3)


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
    r = assert_rejected(client, lift_data(duration_min="0", effort="2", notes="Knee felt off",
                                          **{"sets-2-reps": "0"}), "Reps must be at least 1.")
    body = r.data.decode()
    assert 'value="2026-11-03"' in body
    assert 'value="0"' in body  # the bad duration is kept so you can see what to fix
    assert 'value="Leg Day"' in body
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
    assert_rejected(client, lift_data(title="Changed", **{"sets-0-reps": "0"}),
                    "Reps must be at least 1.", url=f"/workouts/{wid}/edit")
    assert_rejected(client, lift_data(workout_type="run", distance_mi=""),
                    "How far did you run?", url=f"/workouts/{wid}/edit")
    db.session.expire_all()
    w = db.session.get(Workout, wid)
    assert (w.title, w.workout_type, len(w.sets), w.sets[0].reps) == ("Leg Day", "lift", 3, 5)


def test_effort_is_checked_on_the_server_not_just_by_the_dropdown(client, logged_in):
    for bad in ["6", "0", "-1", "10", "2.5"]:
        assert_rejected(client, lift_data(effort=bad), "Effort must be a whole number from 1 to 5.")
    assert count(Workout) == 0


# --- Exercise catalog -------------------------------------------------------------

def test_catalog_has_about_100_tagged_exercises():
    from app.catalog import BODYWEIGHT, CATALOG, WEIGHTED, lookup

    assert 90 <= len(CATALOG) <= 130
    assert {kind for _, kind in CATALOG} == {WEIGHTED, BODYWEIGHT}
    assert len({name.lower() for name, _ in CATALOG}) == len(CATALOG)  # no duplicates
    assert lookup("  bench   PRESS ") == ("Bench Press", False)
    assert lookup("push-up") == ("Push-Up", True)
    assert lookup("Zercher carry") is None


def test_dropdown_suggests_catalog_and_my_exercises(client, logged_in):
    body = client.get("/workouts/new").data.decode()
    assert 'list="exercise-options"' in body  # typed input linked to the suggestions
    assert '<option value="Bench Press">' in body
    assert '<option value="Pull-Up" label="Bodyweight">' in body
    create(client, lift_data(**{"sets-0-exercise": "Zercher carry"}))
    assert '<option value="Zercher carry">' in client.get("/workouts/new").data.decode()


def test_first_use_copies_bodyweight_tag_from_catalog(client, logged_in):
    create(client, lift_data(**{
        "sets-0-exercise": "pull-up", "sets-0-weight_lb": "0",
        "sets-1-exercise": "bench press",
        "sets-2-exercise": "Zercher carry",  # custom: weighted by default
    }))
    tags = dict(db.session.execute(db.select(Exercise.name, Exercise.is_bodyweight)).all())
    assert tags == {"Pull-Up": True, "Bench Press": False, "Zercher carry": False}


def test_names_match_ignoring_case(client, logged_in):
    create(client, lift_data(**{"sets-0-exercise": "bench press", "sets-1-exercise": "BENCH PRESS",
                                "sets-2-exercise": "Bench  Press"}))
    create(client, lift_data(**{"sets-0-exercise": "Bench Press"}))
    names = db.session.execute(db.select(Exercise.name)).scalars().all()
    assert sorted(names) == ["Back Squat", "Bench Press", "Lunge"]  # one Bench Press, not four


# --- Blank weight -----------------------------------------------------------------

WARNING = b"Some sets have no weight. Is this a bodyweight exercise?"


def test_blank_weight_on_bodyweight_exercise_saves_as_0_without_warning(client, logged_in):
    wid = create(client, lift_data(**{"sets-0-exercise": "Push-up", "sets-0-weight_lb": ""}))
    assert db.session.get(Workout, wid).sets[0].weight_lb == 0


def test_blank_weight_on_weighted_exercise_asks_first(client, logged_in):
    data = lift_data(**{"sets-1-weight_lb": ""})  # back squat, no weight
    r = client.post("/workouts/new", data=data)
    assert r.status_code == 200 and WARNING in r.data
    assert b"Save anyway" in r.data and b"Go back and edit" in r.data
    assert b'class="needs-weight"' in r.data  # the empty weight box is highlighted
    assert b'name="sets-2-exercise" value="Lunge"' in r.data  # what you typed is kept
    assert SUMMARY not in r.data  # it's a question, not an error
    assert count(Workout) == 0

    # "Save anyway" sends the same form plus the confirmation.
    wid = create(client, {**data, "confirm_blank_weight": "y"})
    assert [s.weight_lb for s in db.session.get(Workout, wid).sets] == [185, 0, 50]


def test_blank_weight_on_custom_exercise_asks_first(client, logged_in):
    r = client.post("/workouts/new", data=lift_data(**{"sets-0-exercise": "Zercher carry",
                                                         "sets-0-weight_lb": ""}))
    assert WARNING in r.data and count(Workout) == 0


def test_my_saved_bodyweight_tag_is_used(client, logged_in):
    # A custom exercise I've already logged as bodyweight doesn't trigger the warning.
    create(client, lift_data(**{"sets-0-exercise": "Zercher carry", "sets-0-weight_lb": "",
                                "confirm_blank_weight": "y"}))
    db.session.execute(db.update(Exercise).filter_by(name="Zercher carry").values(is_bodyweight=True))
    db.session.commit()
    create(client, lift_data(**{"sets-0-exercise": "zercher carry", "sets-0-weight_lb": ""}))


def test_blank_weight_warning_on_edit(client, logged_in):
    wid = create(client, lift_data())
    r = client.post(f"/workouts/{wid}/edit", data=lift_data(**{"sets-0-weight_lb": ""}))
    assert WARNING in r.data
    db.session.expire_all()
    assert db.session.get(Workout, wid).sets[0].weight_lb == 185  # unchanged until confirmed


def test_errors_come_before_the_weight_question(client, logged_in):
    r = client.post("/workouts/new", data=lift_data(**{"sets-0-weight_lb": "", "sets-1-reps": "0"}))
    assert SUMMARY in r.data and WARNING not in r.data


def test_save_anyway_never_allows_negative_weight(client, logged_in):
    data = lift_data(**{"sets-0-weight_lb": "", "sets-1-weight_lb": "-10", "confirm_blank_weight": "y"})
    assert_rejected(client, data, "Weight can&#39;t be negative.")
    assert count(Workout) == 0


def test_runs_never_get_the_weight_question(client, logged_in):
    create(client, run_data(**{"sets-0-weight_lb": ""}))
