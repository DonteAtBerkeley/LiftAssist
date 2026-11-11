"""Feature 10: double-progression rules (app/recommendations.py), the JSON endpoint, the form, and the Exercises page."""

from datetime import date

import pytest

from app import db, recommendations as rec
from app.forms import MSG_REP_MAX_ORDER, MSG_REP_MIN
from app.models import Exercise, User

from tests.test_prs import exercise, lift
from tests.test_stats import make_user
from tests.test_workouts import signup

D1, D2, D3 = date(2026, 10, 1), date(2026, 10, 8), date(2026, 10, 15)
BENCH = "Bench Press"


# --- Helpers -----------------------------------------------------------------

def session(weight, *reps):
    return [rec.LoggedSet(weight, r) for r in reps]


def bench(user, day, weight, *reps):
    """Log a workout of bench sets, all at one weight."""
    return lift(user, day, *[(BENCH, weight, r) for r in reps])


def bench_exercise(user):
    return db.session.execute(db.select(Exercise).filter_by(user_id=user.id, name=BENCH)).scalar_one()


def suggestion(user, name=BENCH, exclude=None):
    found = db.session.execute(db.select(Exercise).filter_by(user_id=user.id, name=name)).scalar_one()
    return rec.for_exercise(user.id, found, exclude)


@pytest.fixture
def me(client):
    """A signed-up, logged-in user."""
    signup(client, "me@example.com")
    return db.session.execute(db.select(User).filter_by(email="me@example.com")).scalar_one()


# --- Rules -------------------------------------------------------------------

def test_no_history_means_no_suggestion():
    result = rec.recommend([])
    assert result.kind == rec.NONE
    assert not result.has_suggestion
    assert (result.weight, result.reps, result.display) == (None, None, None)
    assert result.message == "Log a session to get a recommendation."


def test_every_set_at_rep_max_goes_up_5_lb_at_rep_min():
    result = rec.recommend([session(135, 12, 12, 12)])
    assert result.kind == rec.LEVEL_UP
    assert (result.weight, result.reps) == (140, 8)
    assert result.display == "140 lb × 8"
    assert result.message == "You hit 12 on every set — go up to 140 lb × 8."


def test_sets_above_rep_max_also_level_up():
    assert rec.recommend([session(135, 12, 15, 13)]).kind == rec.LEVEL_UP


def test_mixed_reps_keep_the_weight_and_add_one_to_the_lowest():
    result = rec.recommend([session(135, 10, 9, 8)])
    assert result.kind == rec.SAME_WEIGHT
    assert (result.weight, result.reps) == (135, 9)
    assert result.message == "Same weight, aim for 9 reps per set."


def test_target_reps_are_capped_at_rep_max():
    result = rec.recommend([session(135, 12, 12, 11)])
    assert (result.kind, result.weight, result.reps) == (rec.SAME_WEIGHT, 135, 12)
    assert rec.next_reps(session(135, 12, 13), 12) == 12  # the cap itself


def test_below_rep_min_two_sessions_running_deloads_10_percent_rounded_to_5():
    result = rec.recommend([session(135, 8, 6), session(135, 7, 8)])
    assert result.kind == rec.DELOAD
    assert (result.weight, result.reps) == (120, 8)  # 135 × 0.9 = 121.5
    assert result.message == "Tough couple of sessions — drop to 120 lb × 8 and build back up."


def test_below_rep_min_only_last_session_is_no_deload():
    result = rec.recommend([session(135, 8, 6), session(135, 9, 9)])
    assert (result.kind, result.weight, result.reps) == (rec.SAME_WEIGHT, 135, 7)


def test_below_rep_min_only_the_session_before_is_no_deload():
    assert rec.recommend([session(135, 9, 9), session(135, 8, 6)]).kind == rec.SAME_WEIGHT


def test_one_bad_session_with_no_earlier_history_is_no_deload():
    assert rec.recommend([session(135, 6, 6)]).kind == rec.SAME_WEIGHT


def test_deload_is_checked_before_level_up():
    # A valid range can't match both rules, so force it: 5 reps is >= rep_max and < rep_min here.
    assert rec.recommend([session(100, 5), session(100, 5)], rep_min=6, rep_max=5).kind == rec.DELOAD


def test_last_weight_is_the_heaviest_set():
    sets = [rec.LoggedSet(95, 12), rec.LoggedSet(135, 9), rec.LoggedSet(115, 10)]
    result = rec.recommend([sets])
    assert (result.weight, result.reps) == (135, 10)


@pytest.mark.parametrize(
    "weight, expected",
    [(100, 90), (135, 120), (225, 205), (125, 115), (132.5, 120), (9, 9), (2.5, 2.5)],
)
def test_deload_weight(weight, expected):
    assert rec.deload_weight(weight) == expected


def test_custom_rep_range_is_respected():
    level_up = rec.recommend([session(200, 8, 8, 8)], rep_min=5, rep_max=8)
    assert (level_up.kind, level_up.weight, level_up.reps) == (rec.LEVEL_UP, 205, 5)
    assert level_up.message == "You hit 8 on every set — go up to 205 lb × 5."

    same = rec.recommend([session(200, 7, 6)], rep_min=5, rep_max=8)
    assert (same.kind, same.reps) == (rec.SAME_WEIGHT, 7)

    # 6 reps is fine in 5–8, but would count as "below" the default 8–12.
    assert rec.recommend([session(200, 6), session(200, 6)], rep_min=5, rep_max=8).kind == rec.SAME_WEIGHT
    deload = rec.recommend([session(200, 4), session(200, 4)], rep_min=5, rep_max=8)
    assert (deload.kind, deload.reps) == (rec.DELOAD, 5)


def test_bodyweight_adds_one_to_the_best_set_and_no_weight():
    result = rec.recommend([session(0, 10, 15, 12)], is_bodyweight=True)
    assert result.kind == rec.BODYWEIGHT
    assert (result.weight, result.reps) == (None, 16)
    assert result.display == "16 reps"
    assert result.message == "Beat your best: aim for 16 reps."


def test_bodyweight_ignores_the_rep_range_and_deload():
    result = rec.recommend([session(0, 2), session(0, 2)], rep_min=8, rep_max=12, is_bodyweight=True)
    assert (result.kind, result.reps) == (rec.BODYWEIGHT, 3)


# --- History from the database -----------------------------------------------

def test_no_sets_logged_yet(app):
    user = make_user("a@example.com")
    exercise(user, BENCH)
    db.session.commit()
    assert suggestion(user).kind == rec.NONE


def test_last_session_is_the_most_recent_by_date_not_by_entry_order(app):
    user = make_user("a@example.com")
    bench(user, D3, 135, 12, 12)
    bench(user, D1, 100, 9, 9)  # logged later, but an older date
    result = suggestion(user)
    assert (result.kind, result.weight) == (rec.LEVEL_UP, 140)


def test_same_day_workouts_use_the_one_logged_later(app):
    user = make_user("a@example.com")
    bench(user, D1, 100, 9)
    bench(user, D1, 135, 12)
    assert suggestion(user).weight == 140


def test_only_sessions_with_this_exercise_count(app):
    user = make_user("a@example.com")
    bench(user, D1, 135, 6)
    lift(user, D2, ("Back Squat", 200, 6))  # not bench, so it can't be bench's "last session"
    bench(user, D3, 135, 6)
    assert suggestion(user).kind == rec.DELOAD


def test_sets_in_one_workout_are_one_session(app):
    user = make_user("a@example.com")
    bench(user, D1, 135, 6, 6, 6)  # three bad sets in one workout aren't two sessions
    assert suggestion(user).kind == rec.SAME_WEIGHT


def test_two_bad_sessions_from_the_database_deload(app):
    user = make_user("a@example.com")
    bench(user, D1, 135, 6)
    bench(user, D2, 135, 7)
    result = suggestion(user)
    assert (result.kind, result.weight, result.reps) == (rec.DELOAD, 120, 8)


def test_editing_a_workout_ignores_itself_as_last_session(app):
    user = make_user("a@example.com")
    bench(user, D1, 100, 9, 9)
    being_edited = bench(user, D2, 135, 12, 12)
    assert suggestion(user).weight == 140
    result = suggestion(user, exclude=being_edited.id)
    assert (result.kind, result.weight, result.reps) == (rec.SAME_WEIGHT, 100, 10)


def test_editing_the_only_workout_means_no_history(app):
    user = make_user("a@example.com")
    only = bench(user, D1, 135, 12)
    assert suggestion(user, exclude=only.id).kind == rec.NONE


def test_editing_a_workout_excludes_it_from_the_deload_check(app):
    user = make_user("a@example.com")
    bench(user, D1, 135, 9)
    bench(user, D2, 135, 6)
    being_edited = bench(user, D3, 135, 6)
    assert suggestion(user).kind == rec.DELOAD
    assert suggestion(user, exclude=being_edited.id).kind == rec.SAME_WEIGHT


def test_custom_rep_range_from_the_database(app):
    user = make_user("a@example.com")
    bench(user, D1, 200, 8, 8)
    found = bench_exercise(user)
    found.rep_min, found.rep_max = 5, 8
    db.session.commit()
    result = suggestion(user)
    assert (result.kind, result.weight, result.reps) == (rec.LEVEL_UP, 205, 5)


def test_bodyweight_from_the_database(app):
    user = make_user("a@example.com")
    lift(user, D1, ("Push-Up", 0, 20), ("Push-Up", 0, 15), bodyweight=True)
    result = suggestion(user, "Push-Up")
    assert (result.kind, result.weight, result.reps) == (rec.BODYWEIGHT, None, 21)


def test_weighted_sets_with_no_weight_are_skipped(app):
    user = make_user("a@example.com")
    bench(user, D1, 135, 9)
    bench(user, D2, 0, 12)  # weight left blank and "Save anyway"
    result = suggestion(user)
    assert (result.kind, result.weight, result.reps) == (rec.SAME_WEIGHT, 135, 10)


def test_only_weightless_sets_count_as_no_history(app):
    user = make_user("a@example.com")
    bench(user, D1, 0, 12)
    assert suggestion(user).kind == rec.NONE


def test_another_users_history_is_ignored(app):
    mine = make_user("a@example.com")
    theirs = make_user("b@example.com")
    exercise(mine, BENCH)
    db.session.commit()
    bench(theirs, D1, 300, 12, 12)
    assert suggestion(mine).kind == rec.NONE
    assert rec.load_sessions(mine.id) == {}


def test_another_users_exercise_is_not_read_through_your_id(app):
    mine = make_user("a@example.com")
    theirs = make_user("b@example.com")
    bench(theirs, D1, 300, 12, 12)
    assert rec.for_exercise(mine.id, bench_exercise(theirs)).kind == rec.NONE


def test_for_exercises_gives_one_per_exercise(app):
    user = make_user("a@example.com")
    lift(user, D1, (BENCH, 135, 12), ("Back Squat", 200, 9))
    exercises = db.session.execute(db.select(Exercise).filter_by(user_id=user.id)).scalars().all()
    by_name = {e.name: rec.for_exercises(user.id, exercises)[e.id] for e in exercises}
    assert (by_name[BENCH].weight, by_name[BENCH].reps) == (140, 8)
    assert (by_name["Back Squat"].weight, by_name["Back Squat"].reps) == (200, 10)


def test_new_exercises_get_the_default_rep_range(app):
    user = make_user("a@example.com")
    bench(user, D1, 100, 8)
    found = bench_exercise(user)
    assert (found.rep_min, found.rep_max) == (rec.DEFAULT_REP_MIN, rec.DEFAULT_REP_MAX)


# --- JSON endpoint -----------------------------------------------------------

def test_endpoint_returns_the_suggestion(client, me):
    bench(me, D1, 135, 12, 12)
    r = client.get(f"/exercises/{bench_exercise(me).id}/recommendation")
    assert r.status_code == 200
    assert r.get_json() == {
        "kind": rec.LEVEL_UP,
        "has_suggestion": True,
        "weight": 140,
        "reps": 8,
        "display": "140 lb × 8",
        "message": "You hit 12 on every set — go up to 140 lb × 8.",
    }


def test_endpoint_with_no_history(client, me):
    exercise(me, BENCH)
    db.session.commit()
    body = client.get(f"/exercises/{bench_exercise(me).id}/recommendation").get_json()
    assert body["has_suggestion"] is False
    assert body["message"] == "Log a session to get a recommendation."


def test_endpoint_excludes_the_workout_being_edited(client, me):
    bench(me, D1, 100, 9)
    edited = bench(me, D2, 135, 12)
    url = f"/exercises/{bench_exercise(me).id}/recommendation"
    assert client.get(url).get_json()["weight"] == 140
    assert client.get(f"{url}?exclude_workout={edited.id}").get_json()["weight"] == 100


def test_endpoint_404s_on_another_users_exercise(client, me):
    other = make_user("b@example.com")
    bench(other, D1, 300, 12)
    r = client.get(f"/exercises/{bench_exercise(other).id}/recommendation")
    assert r.status_code == 404
    assert b"300" not in r.data


def test_endpoint_404s_on_another_users_workout(client, me):
    bench(me, D1, 135, 12)
    other = make_user("b@example.com")
    theirs = bench(other, D1, 300, 12)
    url = f"/exercises/{bench_exercise(me).id}/recommendation?exclude_workout={theirs.id}"
    assert client.get(url).status_code == 404


def test_endpoint_requires_login(client, app):
    user = make_user("a@example.com")
    bench(user, D1, 135, 12)
    r = client.get(f"/exercises/{bench_exercise(user).id}/recommendation")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


# --- Workout form ------------------------------------------------------------

def test_form_has_the_hint_and_use_this_button(client, me):
    page = client.get("/workouts/new").get_data(as_text=True)
    assert "data-set-hint" in page
    assert "Use this" in page
    assert "exclude_workout" not in page


def test_form_only_knows_your_own_exercise_ids(client, me):
    bench(me, D1, 135, 12)
    other = make_user("b@example.com")
    lift(other, D1, ("Secret Lift", 300, 12))
    page = client.get("/workouts/new").get_data(as_text=True)
    assert f'"bench press": {bench_exercise(me).id}' in page
    assert "secret lift" not in page


def test_edit_form_excludes_its_own_workout(client, me):
    workout = bench(me, D1, 135, 12)
    page = client.get(f"/workouts/{workout.id}/edit").get_data(as_text=True)
    assert f"?exclude_workout={workout.id}" in page


# --- Exercises page ----------------------------------------------------------

def test_page_lists_each_exercise_with_its_recommendation(client, me):
    lift(me, D1, (BENCH, 135, 12), ("Back Squat", 200, 9))
    exercise(me, "Leg Press")
    db.session.commit()
    page = client.get("/exercises").get_data(as_text=True)
    assert "💡 Next: 140 lb × 8" in page
    assert "💡 Next: 200 lb × 10" in page
    assert "Leg Press" in page
    assert "Log a session to get a recommendation." in page


def test_page_is_in_the_nav(client, me):
    assert 'href="/exercises"' in client.get("/prs").get_data(as_text=True)


def test_page_empty_state(client, me):
    assert "No exercises yet" in client.get("/exercises").get_data(as_text=True)


def test_page_shows_only_your_exercises(client, me):
    other = make_user("b@example.com")
    lift(other, D1, ("Secret Lift", 300, 12))
    assert "Secret Lift" not in client.get("/exercises").get_data(as_text=True)


def test_page_requires_login(client):
    assert client.get("/exercises").status_code == 302


def post_range(client, exercise_id, rep_min, rep_max, **kwargs):
    return client.post(
        f"/exercises/{exercise_id}/rep-range", data={"rep_min": rep_min, "rep_max": rep_max}, **kwargs
    )


def test_rep_range_can_be_changed_and_updates_the_target(client, me):
    bench(me, D1, 200, 8, 8)
    found = bench_exercise(me)
    r = post_range(client, found.id, "5", "8", follow_redirects=True)
    assert r.status_code == 200
    page = r.get_data(as_text=True)
    assert "Saved." in page
    assert "💡 Next: 205 lb × 5" in page
    db.session.refresh(found)
    assert (found.rep_min, found.rep_max) == (5, 8)


@pytest.mark.parametrize(
    "rep_min, rep_max, message",
    [
        ("0", "12", MSG_REP_MIN),
        ("-3", "12", MSG_REP_MIN),
        ("12", "8", MSG_REP_MAX_ORDER),
        ("8", "8", MSG_REP_MAX_ORDER),
        ("", "12", "Enter the lowest reps"),
        ("8", "", "Enter the highest reps"),
        ("abc", "12", "whole number"),
        ("8", "5000", "check this number"),
        ("9" * 400, "12", "Max reps must be more than min reps."),
    ],
)
def test_rep_range_validation(client, me, rep_min, rep_max, message):
    bench(me, D1, 135, 9)
    found = bench_exercise(me)
    r = post_range(client, found.id, rep_min, rep_max)
    assert r.status_code == 200
    assert message in r.get_data(as_text=True)
    db.session.refresh(found)
    assert (found.rep_min, found.rep_max) == (8, 12)


def test_rep_range_404s_on_another_users_exercise(client, me):
    other = make_user("b@example.com")
    bench(other, D1, 300, 12)
    found = bench_exercise(other)
    assert post_range(client, found.id, "5", "8").status_code == 404
    db.session.refresh(found)
    assert (found.rep_min, found.rep_max) == (8, 12)
