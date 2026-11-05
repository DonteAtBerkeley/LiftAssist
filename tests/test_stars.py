"""Feature 5: stars. One row per user per starred workout, POST only, own workouts only."""

from app import db
from app.models import Star

from tests.test_workouts import create, lift_data, signup


def star_count(workout_id=None):
    q = db.select(db.func.count()).select_from(Star)
    if workout_id is not None:
        q = q.filter(Star.workout_id == workout_id)
    return db.session.execute(q).scalar()


def test_starring_adds_exactly_one_row(client):
    signup(client, "a@example.com")
    wid = create(client, lift_data())

    r = client.post(f"/workouts/{wid}/star", data={"next": "/"})

    assert r.status_code == 302
    assert r.headers["Location"].endswith(f"/#workout-{wid}")  # back to the same card
    assert star_count() == 1
    assert star_count(wid) == 1


def test_starring_twice_does_not_duplicate(client):
    signup(client, "a@example.com")
    wid = create(client, lift_data())

    client.post(f"/workouts/{wid}/star")
    client.post(f"/workouts/{wid}/star")

    assert star_count() == 1


def test_unstarring_removes_the_row(client):
    signup(client, "a@example.com")
    wid = create(client, lift_data())
    client.post(f"/workouts/{wid}/star")

    r = client.post(f"/workouts/{wid}/unstar")

    assert r.status_code == 302
    assert star_count() == 0


def test_cannot_star_another_users_workout(client):
    signup(client, "a@example.com")
    wid = create(client, lift_data(title="A's Leg Day"))
    client.post("/logout")

    signup(client, "b@example.com")
    assert client.post(f"/workouts/{wid}/star").status_code == 404
    assert client.post(f"/workouts/{wid}/unstar").status_code == 404
    assert star_count() == 0
    assert b"A&#39;s Leg Day" not in client.get("/starred").data


def test_starring_requires_post(client):
    signup(client, "a@example.com")
    wid = create(client, lift_data())
    assert client.get(f"/workouts/{wid}/star").status_code == 405
    assert star_count() == 0


def test_starred_page_lists_only_starred_newest_first(client):
    signup(client, "a@example.com")
    r = client.get("/starred")
    assert b"No starred workouts yet" in r.data

    old = create(client, lift_data(title="Old PR day", date="2026-10-01"))
    new = create(client, lift_data(title="New PR day", date="2026-11-01"))
    create(client, lift_data(title="Meh session", date="2026-10-15"))
    client.post(f"/workouts/{old}/star")
    client.post(f"/workouts/{new}/star")

    page = client.get("/starred").data
    assert b"Meh session" not in page
    assert page.index(b"New PR day") < page.index(b"Old PR day")
    assert "★".encode() in page


def test_unsafe_next_falls_back_to_detail_page(client):
    signup(client, "a@example.com")
    wid = create(client, lift_data())
    r = client.post(f"/workouts/{wid}/star", data={"next": "//evil.example.com/"})
    assert r.headers["Location"].endswith(f"/workouts/{wid}#workout-{wid}")
