"""Feature 6: search, filter, and sort the workouts list (and the Starred page)."""

import html
import re
from datetime import date, timedelta

from tests.test_workouts import create, lift_data, signup


def lift(title, exercise="Bench press", **kw):
    """A one-exercise lift (two sets, so a matching search would duplicate it if we joined naively)."""
    data = lift_data(title=title, notes="", **kw)
    data.update({
        "sets-0-exercise": exercise, "sets-1-exercise": exercise,
        "sets-2-exercise": "", "sets-2-weight_lb": "", "sets-2-reps": "",
    })
    return data


def ago(days):
    """An ISO date `days` before today (workout dates can't be in the future)."""
    return (date.today() - timedelta(days=days)).isoformat()


def run(title, **kw):
    return lift_data(title=title, notes="", workout_type="run", distance_mi="3", **kw)


def titles(client, url):
    """Workout titles in the order the page shows them."""
    body = client.get(url).get_data(as_text=True)
    return [html.unescape(t) for t in re.findall(r'class="card-link" href="[^"]*">([^<]*)</a>', body)]


def test_search_by_exercise_name_finds_the_workout_once(client):
    signup(client, "a@example.com")
    create(client, lift("Leg Day", exercise="Back squat"))
    create(client, lift("Push Day", exercise="Bench press"))

    # Partial, case-insensitive: "SQU" finds "Back Squat". Two matching sets, one result.
    assert titles(client, "/?q=SQU") == ["Leg Day"]


def test_search_matches_title_and_notes(client):
    signup(client, "a@example.com")
    create(client, lift("Heavy pull day", exercise="Deadlift"))
    create(client, lift_data(title="Tuesday", notes="Knee felt tight", **{"sets-0-exercise": "Curl",
                             "sets-1-exercise": "Curl", "sets-2-exercise": "Curl"}))
    create(client, lift("Other", exercise="Bench press"))

    assert titles(client, "/?q=pull") == ["Heavy pull day"]
    assert titles(client, "/?q=knee") == ["Tuesday"]


def test_search_treats_percent_literally(client):
    signup(client, "a@example.com")
    create(client, lift("Leg Day"))
    assert titles(client, "/?q=%25") == []  # "%" is not a wildcard


def test_type_filter_excludes_the_other_type(client):
    signup(client, "a@example.com")
    create(client, lift("Squat session"))
    create(client, run("Easy run"))

    assert titles(client, "/?type=run") == ["Easy run"]
    assert titles(client, "/?type=lift") == ["Squat session"]
    assert sorted(titles(client, "/?type=")) == ["Easy run", "Squat session"]


def test_date_range_filter(client):
    signup(client, "a@example.com")
    create(client, lift("Oldest", date=ago(30)))
    create(client, lift("Middle", date=ago(10)))
    create(client, lift("Newest", date=ago(1)))

    assert titles(client, f"/?from={ago(15)}&to={ago(5)}") == ["Middle"]
    assert titles(client, f"/?from={ago(15)}") == ["Newest", "Middle"]
    assert titles(client, f"/?to={ago(15)}") == ["Oldest"]
    assert titles(client, f"/?from={ago(5)}&to={ago(15)}") == ["Middle"]  # reversed range is swapped
    assert titles(client, "/?from=not-a-date") == ["Newest", "Middle", "Oldest"]  # ignored


def test_sort_by_effort_orders_highest_first(client):
    signup(client, "a@example.com")
    create(client, lift("Medium", effort="3", date=ago(3)))
    create(client, lift("Hardest", effort="5", date=ago(30)))
    create(client, lift("No rating", effort="", date=ago(0)))
    create(client, lift("Easy", effort="1", date=ago(1)))

    assert titles(client, "/?sort=effort") == ["Hardest", "Medium", "Easy", "No rating"]


def test_other_sorts(client):
    signup(client, "a@example.com")
    create(client, lift("Short new", duration_min="30", date=ago(1)))
    create(client, lift("Long old", duration_min="90", date=ago(30)))

    assert titles(client, "/") == ["Short new", "Long old"]  # default: newest first
    assert titles(client, "/?sort=oldest") == ["Long old", "Short new"]
    assert titles(client, "/?sort=duration") == ["Long old", "Short new"]
    assert titles(client, "/?sort=bogus") == ["Short new", "Long old"]  # unknown -> default


def test_search_as_user_b_never_returns_user_a_workouts(client):
    signup(client, "a@example.com")
    a_id = create(client, lift("A's Squat Day", exercise="Back squat"))
    client.post(f"/workouts/{a_id}/star")
    client.post("/logout")

    signup(client, "b@example.com")
    create(client, run("B's run"))
    for url in ["/?q=squat", "/?q=A", "/?type=lift", "/?q=", "/?sort=effort",
                "/starred?q=squat", "/starred"]:
        body = client.get(url).get_data(as_text=True)
        assert "Squat Day" not in body, url
    assert titles(client, "/?q=squat") == []


def test_controls_keep_current_choices_and_clear_link(client):
    signup(client, "a@example.com")
    create(client, lift("Leg Day", exercise="Back squat"))

    body = client.get("/?q=squat&type=lift&sort=effort&from=2026-11-01").get_data(as_text=True)
    assert 'value="squat"' in body
    assert '<option value="lift" selected>' in body
    assert '<option value="effort" selected>' in body
    assert 'name="from" autocomplete="off"\n             value="2026-11-01"' in body
    assert 'name="to" autocomplete="off"\n             value=""' in body  # unset stays empty
    assert '<a href="/" role="button" class="secondary">Clear</a>' in body
    assert "1 workout found" in body


def test_date_fields_start_empty_and_blank_dates_do_not_filter(client):
    signup(client, "a@example.com")
    create(client, lift("Old one", date=ago(400)))
    create(client, lift("New one", date=ago(0)))

    body = client.get("/").get_data(as_text=True)
    assert 'name="from" autocomplete="off"\n             value=""' in body
    assert 'name="to" autocomplete="off"\n             value=""' in body
    # What the form sends when the date boxes are left empty: nothing is filtered out.
    assert titles(client, "/?q=&type=&sort=newest&from=&to=") == ["New one", "Old one"]


def test_empty_state_when_nothing_matches(client):
    signup(client, "a@example.com")
    assert "No workouts yet" in client.get("/").get_data(as_text=True)

    create(client, lift("Leg Day"))
    body = client.get("/?q=zzz").get_data(as_text=True)
    assert "No workouts match — try a different search." in body
    assert "No workouts yet" not in body


def test_starred_page_search_and_sort(client):
    signup(client, "a@example.com")
    leg = create(client, lift("Leg Day", exercise="Back squat", effort="2"))
    push = create(client, lift("Push Day", exercise="Bench press", effort="5"))
    create(client, lift("Unstarred squats", exercise="Back squat"))
    client.post(f"/workouts/{leg}/star")
    client.post(f"/workouts/{push}/star")

    assert titles(client, "/starred?q=squat") == ["Leg Day"]
    assert titles(client, "/starred?sort=effort") == ["Push Day", "Leg Day"]
    assert "No workouts match" in client.get("/starred?q=zzz").get_data(as_text=True)


def test_star_from_search_results_returns_to_same_search(client):
    signup(client, "a@example.com")
    wid = create(client, lift("Leg Day", exercise="Back squat"))
    body = client.get("/?q=squat").get_data(as_text=True)
    assert 'name="next" value="/?q=squat"' in body

    r = client.post(f"/workouts/{wid}/star", data={"next": "/?q=squat"})
    assert r.headers["Location"].endswith(f"/?q=squat#workout-{wid}")
