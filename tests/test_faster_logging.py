"""Faster logging: fewer required fields, smart defaults, and "Repeat last workout".

From a stranger test: logging took too long. Only exercise + reps (lift) or distance (run)
should be needed; everything else has a default or is optional.
"""

import re
from datetime import date

from app import db
from app.models import Workout
from tests.test_data_isolation import log_in, log_out, sign_up
from tests.test_workouts import create, lift_data, signup

WARNING = b"Some sets have no weight. Is this a bodyweight exercise?"


def count_workouts():
    return db.session.execute(db.select(db.func.count(Workout.id))).scalar()


def only_workout():
    return db.session.execute(db.select(Workout)).scalar_one()


def browser_defaults(**fields):
    """What the new-workout form sends when you touch nothing but the given fields:
    date prefilled to today, Lift selected, effort 3, everything else blank."""
    data = {
        "date": date.today().isoformat(),
        "title": "",
        "workout_type": "lift",
        "duration_min": "",
        "effort": "3",
        "notes": "",
        "distance_mi": "",
        "sets-0-exercise": "",
        "sets-0-weight_lb": "",
        "sets-0-reps": "",
    }
    data.update(fields)
    return data


def checked_type(body):
    return re.search(r'<input checked[^>]*value="(lift|run)"', body).group(1)


# --- Only exercise + reps are required -------------------------------------------

def test_lift_saves_with_only_exercise_and_reps(client):
    signup(client, "a@example.com")
    create(client, browser_defaults(**{"sets-0-exercise": "Push-up", "sets-0-reps": "20"}))

    w = only_workout()
    assert w.date == date.today()
    assert w.workout_type == "lift"
    assert w.effort == 3
    assert w.duration_min is None and w.notes is None
    assert w.title.endswith("— Lift")  # auto title, e.g. "Friday, Nov 13 — Lift"
    assert [(s.exercise.name, s.weight_lb, s.reps) for s in w.sets] == [("Push-Up", 0, 20)]


def test_lift_saves_even_if_only_exercise_and_reps_are_sent_at_all(client):
    # A request with no other fields at all: date, type and effort fall back to their defaults.
    signup(client, "a@example.com")
    create(client, {"sets-0-exercise": "Pull-up", "sets-0-reps": "8"})
    w = only_workout()
    assert (w.date, w.workout_type, w.effort) == (date.today(), "lift", 3)


def test_weighted_lift_with_only_exercise_and_reps_asks_once_then_saves(client):
    # Weight isn't required. On a weighted exercise a blank weight is still double-checked
    # (Feature 4), and one tap on "Save anyway" saves it.
    signup(client, "a@example.com")
    data = browser_defaults(**{"sets-0-exercise": "Bench press", "sets-0-reps": "8"})
    r = client.post("/workouts/new", data=data)
    assert r.status_code == 200 and WARNING in r.data and count_workouts() == 0
    create(client, {**data, "confirm_blank_weight": "y"})
    assert [(s.weight_lb, s.reps) for s in only_workout().sets] == [(0, 8)]


def test_run_saves_with_only_distance(client):
    signup(client, "a@example.com")
    create(client, browser_defaults(workout_type="run", distance_mi="3.1"))
    w = only_workout()
    assert (w.workout_type, w.distance_mi, w.effort, w.sets) == ("run", 3.1, 3, [])


def test_lift_still_needs_reps(client):
    signup(client, "a@example.com")
    r = client.post("/workouts/new", data=browser_defaults(**{"sets-0-exercise": "Push-up"}))
    assert b"How many reps?" in r.data and count_workouts() == 0


# --- The form ----------------------------------------------------------------------

def test_new_form_defaults_effort_3_and_tucks_extras_into_more_details(client):
    signup(client, "a@example.com")
    body = client.get("/workouts/new").get_data(as_text=True)
    assert '<option selected value="3">' in body
    assert "More details" in body
    details = body[body.index('<details class="more-details"'):body.index("</details>")]
    assert "<details class=\"more-details\">" in details  # collapsed
    for name in ('name="duration_min"', 'name="effort"', 'name="notes"'):
        assert name in details
    assert "+ Same again" in body


def test_more_details_opens_when_something_inside_needs_fixing(client):
    signup(client, "a@example.com")
    r = client.post("/workouts/new", data=lift_data(duration_min="0"))
    assert b'<details class="more-details" open>' in r.data


def test_editing_a_workout_with_no_effort_keeps_it_blank(client):
    signup(client, "a@example.com")
    wid = create(client, lift_data(effort=""))
    body = client.get(f"/workouts/{wid}/edit").get_data(as_text=True)
    assert '<option selected value="">' in body


# --- Type remembers your last choice -----------------------------------------------

def test_type_defaults_to_lift_then_remembers_last_choice(client):
    signup(client, "a@example.com")
    assert checked_type(client.get("/workouts/new").get_data(as_text=True)) == "lift"
    create(client, lift_data(workout_type="run", distance_mi="5"))
    assert checked_type(client.get("/workouts/new").get_data(as_text=True)) == "run"
    create(client, lift_data())
    assert checked_type(client.get("/workouts/new").get_data(as_text=True)) == "lift"


def test_remembered_type_is_only_from_my_own_workouts(client):
    sign_up(client, "a@example.com")
    create(client, lift_data(workout_type="run", distance_mi="5"))
    log_out(client)
    sign_up(client, "b@example.com")
    assert checked_type(client.get("/workouts/new").get_data(as_text=True)) == "lift"


# --- Repeat last workout -----------------------------------------------------------

def test_repeat_prefills_most_recent_workout_dated_today(client):
    signup(client, "a@example.com")
    create(client, lift_data(date="2026-11-01", title="Old day", **{"sets-0-exercise": "Deadlift"}))
    create(client, lift_data(date="2026-11-03", title="", **{
        "sets-0-exercise": "Bench press", "sets-0-weight_lb": "135", "sets-0-reps": "8",
        "sets-1-exercise": "Bench press", "sets-1-weight_lb": "135", "sets-1-reps": "8",
        "sets-2-exercise": "Bench press", "sets-2-weight_lb": "135", "sets-2-reps": "7",
    }))
    r = client.get("/workouts/repeat")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'action="/workouts/new"' in body  # saving makes a NEW workout
    assert f'value="{date.today().isoformat()}"' in body
    assert checked_type(body) == "lift"
    assert 'name="sets-0-exercise" value="Bench Press"' in body
    assert 'name="sets-2-reps" value="7"' in body
    assert 'name="sets-1-weight_lb" value="135"' in body
    assert "Deadlift" not in body.split('<datalist')[0]  # the older workout isn't used
    assert 'Tuesday, Nov 3' not in body.split('id="workout-form"')[1].split('</form>')[0]  # old auto title dropped


def test_repeat_keeps_a_title_i_chose_and_a_runs_distance(client):
    signup(client, "a@example.com")
    create(client, lift_data(title="Easy loop", workout_type="run", distance_mi="4.2"))
    body = client.get("/workouts/repeat").get_data(as_text=True)
    assert 'value="Easy loop"' in body and 'value="4.2"' in body and checked_type(body) == "run"


def test_saving_a_repeat_creates_a_new_workout_and_leaves_the_old_one(client):
    signup(client, "a@example.com")
    old = create(client, lift_data(date="2026-11-03"))
    new = create(client, browser_defaults(**{
        "sets-0-exercise": "Back Squat", "sets-0-weight_lb": "185", "sets-0-reps": "5",
    }))
    assert new != old and count_workouts() == 2
    assert db.session.get(Workout, old).date.isoformat() == "2026-11-03"


def test_repeat_only_uses_my_own_workouts(client):
    # A logs an older workout; B logs a newer one. A's repeat must use A's, never B's.
    sign_up(client, "a@example.com")
    create(client, lift_data(date="2026-11-01", title="A bench day",
                             **{"sets-0-exercise": "Bench press"}))
    log_out(client)
    sign_up(client, "b@example.com")
    create(client, lift_data(date="2026-11-05", title="B secret session",
                             **{"sets-0-exercise": "Zercher carry", "sets-1-exercise": "Zercher carry",
                                "sets-2-exercise": "Zercher carry"}))
    log_out(client)

    log_in(client, "a@example.com")
    body = client.get("/workouts/repeat").get_data(as_text=True)
    assert "A bench day" in body and 'value="Bench Press"' in body
    assert "B secret session" not in body and "Zercher carry" not in body
    log_out(client)

    # C has no workouts: nothing to repeat, and nobody else's workout is offered.
    sign_up(client, "c@example.com")
    r = client.get("/workouts/repeat")
    assert r.status_code == 302 and r.headers["Location"].endswith("/workouts/new")
    body = client.get("/workouts/new").get_data(as_text=True)
    assert "B secret session" not in body and "A bench day" not in body and "Zercher carry" not in body


def test_repeat_button_shows_only_once_there_is_something_to_repeat(client):
    signup(client, "a@example.com")
    assert b"Repeat last workout" not in client.get("/").data
    create(client, lift_data())
    assert b"Repeat last workout" in client.get("/").data


def test_repeat_requires_login(client):
    assert client.get("/workouts/repeat").status_code == 302
