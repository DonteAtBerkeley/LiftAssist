"""Feature 8: PR calculations (app/prs.py), the new-PR message, the badge, and My PRs."""

from datetime import date

import pytest

from app import db, prs
from app.models import Exercise, Set, User, Workout

from tests.test_stats import make_user
from tests.test_workouts import create, signup

D1, D2, D3 = date(2026, 10, 1), date(2026, 10, 8), date(2026, 10, 15)


# --- Helpers -----------------------------------------------------------------

def exercise(user, name, bodyweight=False):
    found = db.session.execute(db.select(Exercise).filter_by(user_id=user.id, name=name)).scalar()
    if found is None:
        found = Exercise(user_id=user.id, name=name, is_bodyweight=bodyweight)
        db.session.add(found)
    return found


def lift(user, day, *sets, bodyweight=False):
    """lift(user, date, ("Bench Press", 185, 5), ...) -> a saved workout with those sets."""
    w = Workout(user_id=user.id, date=day, workout_type="lift")
    db.session.add(w)
    for number, (name, weight, reps) in enumerate(sets, start=1):
        w.sets.append(Set(exercise=exercise(user, name, bodyweight), set_number=number,
                          weight_lb=weight, reps=reps))
    db.session.commit()
    return w


def run(user, day, miles, minutes=None):
    w = Workout(user_id=user.id, date=day, workout_type="run", distance_mi=miles, duration_min=minutes)
    db.session.add(w)
    db.session.commit()
    return w


def records(user):
    """{(metric, exercise name or None): value} for the user's current records."""
    return {
        (r.metric, r.exercise_name): r.value
        for r in prs.best_records(prs.performances(user.id)).values()
    }


def lift_form(day, *sets, title="Push"):
    data = {"date": day, "title": title, "workout_type": "lift"}
    for i, (name, weight, reps) in enumerate(sets):
        data.update({f"sets-{i}-exercise": name, f"sets-{i}-weight_lb": str(weight), f"sets-{i}-reps": str(reps)})
    return data


def run_form(day, miles, minutes):
    return {"date": day, "title": "Run", "workout_type": "run",
            "distance_mi": str(miles), "duration_min": str(minutes)}


def save(client, data):
    """Post a new workout and return (workout id, the page shown after the redirect)."""
    wid = create(client, data)
    return wid, client.get(f"/workouts/{wid}").get_data(as_text=True)


def save_edit(client, wid, data):
    r = client.post(f"/workouts/{wid}/edit", data=data, follow_redirects=True)
    assert r.status_code == 200
    return r.get_data(as_text=True)


@pytest.fixture
def alice(app):
    return make_user("alice@example.com")


@pytest.fixture
def bob(app):
    return make_user("bob@example.com")


@pytest.fixture
def logged_in(client):
    signup(client, "a@example.com")
    return db.session.execute(db.select(User).filter_by(email="a@example.com")).scalar_one()


# --- Math --------------------------------------------------------------------

def test_epley_200_for_5_is_233():
    assert prs.epley_1rm(200, 5) == 233


def test_epley_rounds_halves_up():
    assert prs.epley_1rm(225, 1) == 233  # exactly 232.5


def test_pace_ignores_short_or_untimed_runs():
    assert prs.pace_seconds(30, 4) == 450
    assert prs.pace_seconds(5, 0.9) is None
    assert prs.pace_seconds(None, 4) is None
    assert prs.pace_seconds(0, 4) is None


def test_format_pace():
    assert prs.format_pace(465) == "7:45 /mi"
    assert prs.format_pace(425) == "7:05 /mi"


# --- Records -----------------------------------------------------------------

def test_heavier_set_becomes_the_new_record(alice):
    lift(alice, D1, ("Bench Press", 175, 5))
    assert records(alice)[("weight", "Bench Press")] == 175
    lift(alice, D2, ("Bench Press", 185, 3))
    assert records(alice)[("weight", "Bench Press")] == 185


def test_weight_and_1rm_are_separate_records(alice):
    heavy = lift(alice, D1, ("Bench Press", 200, 1))  # est. 1RM 207
    reps = lift(alice, D2, ("Bench Press", 180, 10))  # est. 1RM 240
    best = prs.best_records(prs.performances(alice.id))
    ex_id = heavy.sets[0].exercise_id
    assert (best[("weight", ex_id)].value, best[("weight", ex_id)].workout_id) == (200, heavy.id)
    assert (best[("e1rm", ex_id)].value, best[("e1rm", ex_id)].workout_id) == (240, reps.id)


def test_bodyweight_record_uses_reps_not_weight(alice):
    lift(alice, D1, ("Pull-Up", 0, 8), ("Pull-Up", 0, 12), ("Pull-Up", 0, 10), bodyweight=True)
    assert records(alice) == {("reps", "Pull-Up"): 12}


def test_zero_weight_on_weighted_exercise_is_not_a_record(alice):
    lift(alice, D1, ("Bench Press", 0, 20))
    assert records(alice) == {}


def test_fastest_pace_ignores_runs_under_1_mile(alice):
    run(alice, D1, 3, 27)  # 9:00 /mi
    run(alice, D2, 0.5, 3)  # 6:00 /mi, but too short to count
    result = records(alice)
    assert result[("pace", None)] == 540
    assert result[("distance", None)] == 3


def test_run_exactly_1_mile_counts(alice):
    run(alice, D1, 1, 7)
    assert records(alice)[("pace", None)] == 420


def test_run_without_duration_counts_for_distance_only(alice):
    run(alice, D1, 5)
    assert records(alice) == {("distance", None): 5}


def test_lower_pace_wins_higher_distance_wins(alice):
    run(alice, D1, 3, 30)  # 10:00 /mi
    run(alice, D2, 5, 45)  # 9:00 /mi
    run(alice, D3, 2, 20)  # 10:00 /mi
    assert records(alice) == {("pace", None): 540, ("distance", None): 5}


def test_tie_keeps_the_earliest_holder(alice):
    first = lift(alice, D1, ("Bench Press", 185, 5))
    lift(alice, D2, ("Bench Press", 185, 5))
    best = prs.best_records(prs.performances(alice.id))
    assert best[("weight", first.sets[0].exercise_id)].workout_id == first.id


def test_another_users_lifts_never_count(alice, bob):
    lift(bob, D1, ("Bench Press", 500, 5))
    run(bob, D1, 26, 120)
    assert records(alice) == {}
    lift(alice, D2, ("Bench Press", 135, 5))
    assert records(alice)[("weight", "Bench Press")] == 135
    assert prs.pr_summary(alice.id)["distance"] is None


def test_deleting_the_record_workout_restores_the_old_record(alice):
    lift(alice, D1, ("Bench Press", 175, 5))
    top = lift(alice, D2, ("Bench Press", 185, 5))
    db.session.delete(top)
    db.session.commit()
    assert records(alice)[("weight", "Bench Press")] == 175


# --- New-PR detection --------------------------------------------------------

def test_heavier_set_is_flagged_as_new_pr(alice):
    lift(alice, D1, ("Bench Press", 175, 5))
    before = prs.take_snapshot(alice.id)
    w = lift(alice, D2, ("Bench Press", 185, 5))
    assert {r.metric: r.value for r in prs.new_prs(alice.id, w.id, before)} == {"weight": 185, "e1rm": 216}


def test_first_log_is_not_a_new_pr(alice):
    before = prs.take_snapshot(alice.id)
    w = lift(alice, D1, ("Bench Press", 100, 5), ("Bench Press", 185, 5))
    assert prs.new_prs(alice.id, w.id, before) == []


def test_matching_the_record_is_not_a_new_pr(alice):
    lift(alice, D1, ("Bench Press", 185, 5))
    before = prs.take_snapshot(alice.id)
    w = lift(alice, D2, ("Bench Press", 185, 5))
    assert prs.new_prs(alice.id, w.id, before) == []


def test_another_users_lift_is_not_something_to_beat(alice, bob):
    lift(bob, D1, ("Bench Press", 100, 5))
    before = prs.take_snapshot(alice.id)
    w = lift(alice, D2, ("Bench Press", 185, 5))  # Alice's first log: still nothing to beat
    assert prs.new_prs(alice.id, w.id, before) == []


def test_messages():
    def item(metric, value, name=None, ex=None):
        return prs.Performance(metric, value, 1, D1, ex, name)

    assert prs.pr_messages([item("weight", 185.0, "Bench Press", 1)]) == ["🏆 New PR: Bench Press — 185 lb!"]
    assert prs.pr_messages([item("e1rm", 216, "Bench Press", 1)]) == ["🏆 New PR: Bench Press — 216 lb est. 1RM!"]
    assert prs.pr_messages([item("e1rm", 216, "Bench Press", 1), item("weight", 185.0, "Bench Press", 1)]) == [
        "🏆 New PR: Bench Press — 185 lb, 216 lb est. 1RM!"
    ]
    assert prs.pr_messages([item("reps", 15, "Pull-Up", 2)]) == ["🏆 New PR: Pull-Up — 15 reps!"]
    assert prs.pr_messages([item("pace", 465), item("distance", 6.2)]) == [
        "🏆 New PR: Fastest pace — 7:45 /mi!",
        "🏆 New PR: Longest run — 6.2 mi!",
    ]


# --- Saving through the app --------------------------------------------------

def test_saving_a_heavier_workout_shows_the_message(client, logged_in):
    _, first_page = save(client, lift_form("2026-10-01", ("Bench Press", 175, 5)))
    assert "New PR" not in first_page  # first-ever log
    _, page = save(client, lift_form("2026-10-08", ("Bench Press", 185, 5)))
    assert "🏆 New PR: Bench Press — 185 lb, 216 lb est. 1RM!" in page
    assert "flash-pr" in page


def test_saving_a_lighter_workout_shows_no_message(client, logged_in):
    save(client, lift_form("2026-10-01", ("Bench Press", 185, 5)))
    _, page = save(client, lift_form("2026-10-08", ("Bench Press", 135, 5)))
    assert "New PR" not in page


def test_editing_into_a_pr_shows_the_message(client, logged_in):
    save(client, lift_form("2026-10-01", ("Bench Press", 175, 5)))
    wid, _ = save(client, lift_form("2026-10-08", ("Bench Press", 135, 5)))
    page = save_edit(client, wid, lift_form("2026-10-08", ("Bench Press", 195, 5)))
    assert "🏆 New PR: Bench Press — 195 lb" in page


def test_resaving_a_pr_workout_does_not_celebrate_again(client, logged_in):
    save(client, lift_form("2026-10-01", ("Bench Press", 175, 5)))
    data = lift_form("2026-10-08", ("Bench Press", 185, 5))
    wid, first = save(client, data)
    assert "New PR" in first
    page = save_edit(client, wid, {**data, "notes": "fixed a typo"})
    assert "New PR" not in page


def test_editing_the_only_log_is_not_a_pr(client, logged_in):
    wid, _ = save(client, lift_form("2026-10-01", ("Bench Press", 135, 5)))
    page = save_edit(client, wid, lift_form("2026-10-01", ("Bench Press", 145, 5)))
    assert "New PR" not in page


def test_bodyweight_pr_message_through_the_form(client, logged_in):
    save(client, lift_form("2026-10-01", ("Push-Up", "", 20)))
    _, page = save(client, lift_form("2026-10-08", ("Push-Up", "", 25)))
    assert "🏆 New PR: Push-Up — 25 reps!" in page


def test_run_pr_messages(client, logged_in):
    save(client, run_form("2026-10-01", 3, 30))
    _, page = save(client, run_form("2026-10-08", 5, 40))
    assert "🏆 New PR: Fastest pace — 8:00 /mi!" in page
    assert "🏆 New PR: Longest run — 5 mi!" in page


def test_short_fast_run_is_not_a_pr(client, logged_in):
    save(client, run_form("2026-10-01", 3, 30))
    _, page = save(client, run_form("2026-10-08", 0.5, 3))
    assert "New PR" not in page


# --- Badge on the detail page ------------------------------------------------

def test_badge_marks_only_the_record_set(client, logged_in):
    wid, page = save(client, lift_form("2026-10-01", ("Bench Press", 135, 5), ("Bench Press", 185, 5)))
    assert page.count('class="pr-badge"') == 1
    w = db.session.get(Workout, wid)
    assert prs.set_badges(logged_in.id, wid) == {w.sets[1].id: ["Heaviest", "Est. 1RM"]}


def test_badge_disappears_once_the_record_is_beaten(client, logged_in):
    old, _ = save(client, lift_form("2026-10-01", ("Bench Press", 175, 5)))
    save(client, lift_form("2026-10-08", ("Bench Press", 185, 5)))
    assert 'class="pr-badge"' not in client.get(f"/workouts/{old}").get_data(as_text=True)


# --- My PRs page -------------------------------------------------------------

def test_prs_page_requires_login(client):
    assert client.get("/prs").status_code == 302


def test_prs_page_empty_state(client, logged_in):
    assert "No PRs yet." in client.get("/prs").get_data(as_text=True)


def test_nav_has_my_prs_link(client, logged_in):
    assert 'href="/prs"' in client.get("/").get_data(as_text=True)


def test_prs_page_shows_bests_with_links(client, logged_in):
    bench, _ = save(client, lift_form("2026-10-01", ("Bench Press", 185, 5)))
    pushups, _ = save(client, lift_form("2026-10-02", ("Push-Up", "", 30)))
    jog, _ = save(client, run_form("2026-10-03", 4, 30))
    page = client.get("/prs").get_data(as_text=True)
    for text in ["Bench Press", "185 lb", "216 lb", "Oct 1, 2026", "Push-Up", "30 reps", "Max reps",
                 "7:30 /mi", "4 mi", f'href="/workouts/{bench}"', f'href="/workouts/{pushups}"',
                 f'href="/workouts/{jog}"']:
        assert text in page
    assert page.index("Fastest pace") < page.index("Bench Press")  # run PRs on top


def test_prs_page_shows_only_your_own(client, logged_in):
    save(client, lift_form("2026-10-01", ("Bench Press", 315, 5)))
    client.post("/logout")
    signup(client, "b@example.com")
    page = client.get("/prs").get_data(as_text=True)
    assert "No PRs yet." in page
    assert "Bench Press" not in page and "315" not in page
