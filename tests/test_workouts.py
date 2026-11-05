"""Feature 3: create / read / update / delete workouts, and per-user data isolation."""

from datetime import date

import pytest

from app import db
from app.models import Exercise, Set, User, Workout


def signup(client, email):
    client.post(
        "/signup",
        data={"email": email, "password": "password123", "confirm_password": "password123"},
    )


def lift_data(**overrides):
    data = {
        "date": "2026-11-03",
        "title": "Leg Day",
        "workout_type": "lift",
        "duration_min": "60",
        "effort": "4",
        "notes": "Felt strong",
        "sets-0-exercise": "Back squat",
        "sets-0-weight_lb": "185",
        "sets-0-reps": "5",
        "sets-1-exercise": "back squat ",  # same exercise, different case/spacing
        "sets-1-weight_lb": "185",
        "sets-1-reps": "5",
        "sets-2-exercise": "Lunge",
        "sets-2-weight_lb": "50",
        "sets-2-reps": "10",
    }
    data.update(overrides)
    return data


def create(client, data):
    r = client.post("/workouts/new", data=data)
    assert r.status_code == 302, r.data
    return int(r.headers["Location"].rstrip("/").split("/")[-1])


@pytest.fixture
def user_a(client):
    signup(client, "a@example.com")
    return db.session.execute(db.select(User).filter_by(email="a@example.com")).scalar_one()


def test_pages_require_login(client):
    for url in ["/", "/workouts/new", "/workouts/1", "/workouts/1/edit", "/workouts/1/delete"]:
        assert client.get(url).status_code == 302


def test_new_form_defaults(client, user_a):
    r = client.get("/workouts/new")
    assert r.status_code == 200
    assert date.today().isoformat().encode() in r.data  # date defaults to today
    assert b'name="sets-0-exercise"' in r.data  # one empty set row to start


def test_create_lift_with_sets(client, user_a):
    wid = create(client, lift_data())
    w = db.session.get(Workout, wid)
    assert w.user_id == user_a.id
    assert (w.title, w.workout_type, w.duration_min, w.effort, w.notes) == (
        "Leg Day", "lift", 60, 4, "Felt strong"
    )
    assert w.distance_mi is None
    assert [(s.set_number, s.exercise.name, s.weight_lb, s.reps) for s in w.sets] == [
        (1, "Back squat", 185, 5),
        (2, "Back squat", 185, 5),
        (3, "Lunge", 50, 10),
    ]
    # Typing a new name created the exercise for this user; case/spacing variants reuse it.
    names = db.session.execute(db.select(Exercise.name).filter_by(user_id=user_a.id)).scalars().all()
    assert sorted(names) == ["Back squat", "Lunge"]


def test_existing_exercise_reused_and_offered_for_autocomplete(client, user_a):
    create(client, lift_data())
    create(client, lift_data(**{"sets-0-exercise": "LUNGE"}))
    assert db.session.execute(db.select(db.func.count(Exercise.id))).scalar() == 2
    r = client.get("/workouts/new")
    assert b'<option value="Back squat">' in r.data
    assert b'<option value="Lunge">' in r.data


def test_blank_set_rows_ignored_and_blank_weight_is_bodyweight(client, user_a):
    wid = create(client, lift_data(**{
        "sets-1-exercise": "", "sets-1-weight_lb": "", "sets-1-reps": "",  # empty row
        "sets-2-exercise": "Pull-up", "sets-2-weight_lb": "", "sets-2-reps": "8",
    }))
    w = db.session.get(Workout, wid)
    assert [(s.set_number, s.exercise.name, s.weight_lb) for s in w.sets] == [
        (1, "Back squat", 185), (2, "Pull-up", 0),
    ]


def test_set_with_exercise_but_no_reps_is_not_saved(client, user_a):
    r = client.post("/workouts/new", data=lift_data(**{"sets-0-reps": ""}))
    assert r.status_code == 200
    assert b"Reps are required." in r.data
    assert db.session.execute(db.select(db.func.count(Workout.id))).scalar() == 0


def test_missing_date_is_not_saved(client, user_a):
    r = client.post("/workouts/new", data=lift_data(date=""))
    assert r.status_code == 200
    assert db.session.execute(db.select(db.func.count(Workout.id))).scalar() == 0


def test_create_run_ignores_sets(client, user_a):
    wid = create(client, lift_data(title="Long run", workout_type="run", distance_mi="6.2"))
    w = db.session.get(Workout, wid)
    assert w.workout_type == "run" and w.distance_mi == 6.2 and w.sets == []


def test_list_newest_first_with_summaries(client, user_a):
    create(client, lift_data(date="2026-11-01", title="Older lift"))
    create(client, lift_data(date="2026-11-03", title="Newest run", workout_type="run", distance_mi="3.1"))
    r = client.get("/")
    body = r.data.decode()
    assert body.index("Newest run") < body.index("Older lift")
    assert "3.1 mi" in body
    assert "3 sets" in body
    assert "Nov 3, 2026" in body


def test_detail_groups_sets_by_exercise(client, user_a):
    wid = create(client, lift_data(**{
        # interleaved: squat, lunge, squat -> shown as Back squat (2 sets), Lunge (1 set)
        "sets-1-exercise": "Lunge", "sets-1-weight_lb": "50", "sets-1-reps": "10",
        "sets-2-exercise": "Back squat", "sets-2-weight_lb": "195", "sets-2-reps": "3",
    }))
    body = client.get(f"/workouts/{wid}").data.decode()
    assert body.count("<h3") == 3  # two exercise groups + Notes
    assert body.index("Back squat") < body.index("195 lb") < body.index("Lunge")
    assert "Felt strong" in body and "4/5" in body and "60 min" in body


def test_edit_prefills_and_updates_sets(client, user_a):
    wid = create(client, lift_data())
    r = client.get(f"/workouts/{wid}/edit")
    assert b'value="Leg Day"' in r.data
    assert b'name="sets-2-exercise" value="Lunge"' in r.data

    # Remove the 2nd set (index 1) and add a new one with a gap in the indexes.
    data = lift_data(title="Leg Day (edited)", **{"sets-5-exercise": "Leg press",
                                                  "sets-5-weight_lb": "300", "sets-5-reps": "12"})
    for k in ["sets-1-exercise", "sets-1-weight_lb", "sets-1-reps"]:
        del data[k]
    r = client.post(f"/workouts/{wid}/edit", data=data)
    assert r.status_code == 302

    db.session.expire_all()
    w = db.session.get(Workout, wid)
    assert w.title == "Leg Day (edited)"
    assert [(s.set_number, s.exercise.name) for s in w.sets] == [
        (1, "Back squat"), (2, "Lunge"), (3, "Leg press")
    ]
    assert db.session.execute(db.select(db.func.count(Set.id))).scalar() == 3  # old sets gone


def test_switching_lift_to_run_drops_sets(client, user_a):
    wid = create(client, lift_data())
    client.post(f"/workouts/{wid}/edit", data=lift_data(workout_type="run", distance_mi="5"))
    db.session.expire_all()
    w = db.session.get(Workout, wid)
    assert w.workout_type == "run" and w.distance_mi == 5 and w.sets == []


def test_delete_asks_first_then_deletes(client, user_a):
    wid = create(client, lift_data())
    r = client.get(f"/workouts/{wid}/delete")
    assert b"Are you sure?" in r.data
    assert db.session.get(Workout, wid) is not None  # looking at the page deletes nothing

    r = client.post(f"/workouts/{wid}/delete")
    assert r.status_code == 302
    db.session.expire_all()
    assert db.session.get(Workout, wid) is None
    assert db.session.execute(db.select(db.func.count(Set.id))).scalar() == 0
    # Exercises stay in the user's list for next time.
    assert db.session.execute(db.select(db.func.count(Exercise.id))).scalar() == 2


def test_other_users_workout_is_404_everywhere(client, user_a):
    """PLAN.md test 1: User A logs "Leg Day"; User B sees an empty list and gets 404 on its URLs."""
    wid = create(client, lift_data())
    client.post("/logout")
    signup(client, "b@example.com")

    home = client.get("/")
    assert b"Leg Day" not in home.data and b"No workouts yet." in home.data
    assert b"Back squat" not in client.get("/workouts/new").data  # A's exercises aren't offered

    assert client.get(f"/workouts/{wid}").status_code == 404
    assert client.get(f"/workouts/{wid}/edit").status_code == 404
    assert client.post(f"/workouts/{wid}/edit", data=lift_data(title="Hacked")).status_code == 404
    assert client.get(f"/workouts/{wid}/delete").status_code == 404
    assert client.post(f"/workouts/{wid}/delete").status_code == 404

    db.session.expire_all()
    w = db.session.get(Workout, wid)
    assert w is not None and w.title == "Leg Day" and len(w.sets) == 3


def test_new_exercise_names_are_per_user(client, user_a):
    create(client, lift_data())
    client.post("/logout")
    signup(client, "b@example.com")
    create(client, lift_data())
    b = db.session.execute(db.select(User).filter_by(email="b@example.com")).scalar_one()
    # B got their own "Back squat", not A's.
    owners = db.session.execute(
        db.select(Exercise.user_id).filter_by(name="Back squat")
    ).scalars().all()
    assert sorted(owners) == sorted([user_a.id, b.id])
