"""Feature 9: the weekly streak (app/streaks.py), the Dashboard card, and the list badge.

Most tests call `streak_summary` with a fixed `today`, so the answers don't depend on
when the tests run.
"""

from datetime import date, timedelta

import pytest

from app import db, streaks
from app.models import User
from app.stats import week_start
from app.streaks import streak_summary

from tests.test_stats import alice, bob, lift, make_user, run  # noqa: F401 (fixtures)
from tests.test_workouts import signup

TODAY = date(2026, 11, 10)  # a Tuesday

# Mondays, counting back from the in-progress week.
THIS_WEEK = date(2026, 11, 9)
WEEK_1_AGO = date(2026, 11, 2)
WEEK_2_AGO = date(2026, 10, 26)
WEEK_3_AGO = date(2026, 10, 19)
WEEK_4_AGO = date(2026, 10, 12)
WEEK_5_AGO = date(2026, 10, 5)


def log_week(user, monday, workouts=streaks.WORKOUTS_PER_WEEK):
    """Log `workouts` runs in the week starting `monday`, one per day from Monday on."""
    for offset in range(workouts):
        run(user, monday + timedelta(days=offset), 3)


def current(user, today=TODAY):
    return streak_summary(user.id, today)["current"]


def longest(user, today=TODAY):
    return streak_summary(user.id, today)["longest"]


# --- The rules ---------------------------------------------------------------

def test_threshold_is_three():
    assert streaks.WORKOUTS_PER_WEEK == 3


def test_three_consecutive_weeks_is_a_streak_of_three(alice):
    for monday in (WEEK_3_AGO, WEEK_2_AGO, WEEK_1_AGO):
        log_week(alice, monday)
    assert current(alice) == 3
    assert longest(alice) == 3


def test_a_week_with_only_two_workouts_breaks_the_streak(alice):
    log_week(alice, WEEK_3_AGO)
    log_week(alice, WEEK_2_AGO, workouts=2)
    log_week(alice, WEEK_1_AGO)
    assert current(alice) == 1
    assert longest(alice) == 1


def test_a_week_with_no_workouts_breaks_the_streak(alice):
    log_week(alice, WEEK_3_AGO)
    log_week(alice, WEEK_1_AGO)
    assert current(alice) == 1


def test_missing_last_week_ends_the_current_streak(alice):
    log_week(alice, WEEK_3_AGO)
    log_week(alice, WEEK_2_AGO)
    log_week(alice, WEEK_1_AGO, workouts=2)
    assert current(alice) == 0
    assert longest(alice) == 2


# --- The in-progress week ----------------------------------------------------

@pytest.mark.parametrize("this_week", [0, 1, 2])
def test_in_progress_week_under_three_does_not_reset_the_streak(alice, this_week):
    log_week(alice, WEEK_2_AGO)
    log_week(alice, WEEK_1_AGO)
    log_week(alice, THIS_WEEK, workouts=this_week)
    summary = streak_summary(alice.id, date(2026, 11, 15))  # even on the week's last day
    assert summary["current"] == 2
    assert summary["this_week"] == this_week


def test_in_progress_week_with_three_is_included(alice):
    log_week(alice, WEEK_2_AGO)
    log_week(alice, WEEK_1_AGO)
    log_week(alice, THIS_WEEK)
    today = date(2026, 11, 11)  # Wednesday: all three workouts are done
    assert current(alice, today) == 3
    assert longest(alice, today) == 3


def test_in_progress_week_alone_starts_a_streak_of_one(alice):
    log_week(alice, WEEK_3_AGO)  # an old streak, then a gap
    log_week(alice, THIS_WEEK)
    assert current(alice, date(2026, 11, 11)) == 1


def test_a_short_week_breaks_the_streak_once_it_is_over(alice):
    log_week(alice, WEEK_1_AGO)
    log_week(alice, THIS_WEEK, workouts=2)
    assert current(alice, date(2026, 11, 15)) == 1  # Sunday: still in progress
    assert current(alice, date(2026, 11, 16)) == 0  # Monday: that week is now complete


# --- Longest streak ----------------------------------------------------------

def test_longest_streak_is_remembered_after_a_break(alice):
    for monday in (WEEK_5_AGO, WEEK_4_AGO, WEEK_3_AGO):
        log_week(alice, monday)
    # WEEK_2_AGO is skipped.
    log_week(alice, WEEK_1_AGO)
    assert current(alice) == 1
    assert longest(alice) == 3


def test_longest_streak_survives_a_current_streak_of_zero(alice):
    for monday in (WEEK_4_AGO, WEEK_3_AGO):
        log_week(alice, monday)
    assert current(alice) == 0
    assert longest(alice) == 2


# --- What counts as a workout, and in which week ------------------------------

def test_multiple_workouts_on_the_same_day_each_count(alice):
    for _ in range(3):
        run(alice, WEEK_1_AGO, 3)
    assert current(alice) == 1


def test_lifts_and_runs_both_count(alice):
    lift(alice, WEEK_1_AGO, ("Bench Press", 100, 5))
    run(alice, WEEK_1_AGO + timedelta(days=1), 3)
    lift(alice, WEEK_1_AGO + timedelta(days=2), ("Back Squat", 100, 5))
    assert current(alice) == 1


def test_weeks_run_monday_to_sunday(alice):
    sunday = WEEK_1_AGO - timedelta(days=1)  # belongs to the week before WEEK_1_AGO
    for _ in range(2):
        run(alice, sunday, 3)
    run(alice, WEEK_1_AGO, 3)
    assert longest(alice) == 0  # 2 + 1 across the boundary is not one week of 3


def test_a_week_can_span_new_year(alice):
    for day in (date(2026, 12, 30), date(2027, 1, 1), date(2027, 1, 3)):  # one Mon–Sun week
        run(alice, day, 3)
    log_week(alice, date(2027, 1, 4))
    assert current(alice, date(2027, 1, 12)) == 2


def test_future_dated_workouts_are_ignored(alice):
    log_week(alice, THIS_WEEK + timedelta(weeks=1))
    summary = streak_summary(alice.id, TODAY)
    assert (summary["current"], summary["longest"], summary["this_week"]) == (0, 0, 0)


def test_another_users_workouts_never_count(alice, bob):
    for monday in (WEEK_2_AGO, WEEK_1_AGO, THIS_WEEK):
        log_week(bob, monday)
    # Alice is one workout short last week; Bob's workouts must not top her up.
    log_week(alice, WEEK_1_AGO, workouts=2)
    summary = streak_summary(alice.id, date(2026, 11, 11))
    assert (summary["current"], summary["longest"], summary["this_week"]) == (0, 0, 0)
    assert current(bob, date(2026, 11, 11)) == 3


def test_no_workouts_at_all(alice):
    assert streak_summary(alice.id, TODAY) == {
        "current": 0, "longest": 0, "this_week": 0, "threshold": 3,
    }


# --- The pure functions ------------------------------------------------------

def test_counting_weeks_uses_the_threshold():
    counts = {WEEK_2_AGO: 2, WEEK_1_AGO: 3}
    assert streaks.counting_weeks(counts) == {WEEK_1_AGO}
    assert streaks.counting_weeks(counts, threshold=2) == {WEEK_2_AGO, WEEK_1_AGO}


def test_longest_streak_of_nothing_is_zero():
    assert streaks.longest_streak(set()) == 0


# --- The pages ---------------------------------------------------------------

def signed_up_user(client, email="a@example.com"):
    signup(client, email)
    return db.session.execute(db.select(User).filter_by(email=email)).scalar()


def this_monday():
    return week_start(date.today())


def weeks_ago(n):
    return this_monday() - timedelta(weeks=n)


def test_dashboard_card_shows_streak_and_progress(client):
    user = signed_up_user(client)
    log_week(user, weeks_ago(2))
    log_week(user, weeks_ago(1))
    for _ in range(2):
        run(user, this_monday(), 3)  # Monday is never in the future

    body = client.get("/dashboard").get_data(as_text=True)

    assert "🔥 Current streak: 2 weeks" in body
    assert "Longest: 2 weeks" in body
    assert "This week: 2 / 3 workouts" in body
    assert '<progress value="2" max="3"' in body
    assert "to start a streak" not in body
    assert body.index('class="streak-card"') < body.index('class="stats"')


def test_dashboard_card_says_one_week_not_one_weeks(client):
    user = signed_up_user(client)
    log_week(user, weeks_ago(1))
    body = client.get("/dashboard").get_data(as_text=True)
    assert "🔥 Current streak: 1 week<" in body
    assert "Longest: 1 week<" in body


def test_dashboard_empty_state_for_a_new_user(client):
    signup(client, "a@example.com")
    body = client.get("/dashboard").get_data(as_text=True)
    assert "🔥 Current streak: 0 weeks" in body
    assert "This week: 0 / 3 workouts" in body
    assert "Log 3 workouts this week to start a streak." in body


def test_dashboard_empty_state_counts_down_this_weeks_workouts(client):
    user = signed_up_user(client)
    run(user, this_monday(), 3)
    body = client.get("/dashboard").get_data(as_text=True)
    assert "Log 2 more workouts this week to start a streak." in body


def test_list_badge_shows_the_streak(client):
    user = signed_up_user(client)
    log_week(user, weeks_ago(2))
    log_week(user, weeks_ago(1))
    assert "🔥 2-week streak" in client.get("/").get_data(as_text=True)


def test_list_badge_is_hidden_at_zero(client):
    user = signed_up_user(client)
    run(user, weeks_ago(1), 3)
    body = client.get("/").get_data(as_text=True)
    assert "🔥" not in body
    assert 'class="streak-badge"' not in body


def test_list_badge_ignores_search_filters(client):
    user = signed_up_user(client)
    log_week(user, weeks_ago(1))
    assert "🔥 1-week streak" in client.get("/?q=nothing-matches").get_data(as_text=True)


def test_pages_only_show_the_logged_in_users_streak(client):
    other = make_user("other@example.com")
    log_week(other, weeks_ago(2))
    log_week(other, weeks_ago(1))

    signup(client, "a@example.com")

    assert "🔥 Current streak: 0 weeks" in client.get("/dashboard").get_data(as_text=True)
    assert "🔥" not in client.get("/").get_data(as_text=True)
