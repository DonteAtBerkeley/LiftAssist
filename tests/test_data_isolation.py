"""PLAN.md section 4, required test #1: data isolation.

Given User A has logged a workout titled "Leg Day",
when User B logs in, opens the workouts list, and tries to open Leg Day's URL directly,
then User B's list is empty (no "Leg Day") and the direct URL returns 404.

The test drives the real app through HTTP requests, the same way a browser would:
real sign-up, real new-workout form, real logout and login. No rows are inserted
into the database by hand.
"""

from app import db
from app.models import Workout

PASSWORD = "password123"


def sign_up(client, email):
    """Fill in and submit the sign-up page. A successful sign-up logs the user in."""
    response = client.post(
        "/signup",
        data={"email": email, "password": PASSWORD, "confirm_password": PASSWORD},
    )
    assert response.status_code == 302, "sign-up should succeed and redirect home"


def log_in(client, email):
    """Fill in and submit the login page."""
    response = client.post("/login", data={"email": email, "password": PASSWORD})
    assert response.status_code == 302, "login should succeed and redirect home"


def log_out(client):
    """Press the Log out button in the nav (it submits a POST form)."""
    response = client.post("/logout")
    assert response.status_code == 302, "logout should redirect to the login page"


def test_user_b_cannot_see_user_a_workouts(client):
    # --- Given: User A has logged a workout titled "Leg Day" -----------------

    # Step 1: User A signs up through the sign-up page (this also logs them in).
    sign_up(client, "user.a@example.com")

    # Step 2: User A fills in the "New workout" form and saves it.
    response = client.post(
        "/workouts/new",
        data={
            "date": "2026-11-03",
            "title": "Leg Day",
            "workout_type": "lift",
            "duration_min": "60",
            "effort": "4",
            "sets-0-exercise": "Back squat",
            "sets-0-weight_lb": "185",
            "sets-0-reps": "5",
        },
    )
    # Saving redirects to the new workout's page, e.g. /workouts/1.
    # That address is "Leg Day's URL", the one User B will later try to open.
    assert response.status_code == 302, "the workout form should save and redirect"
    leg_day_url = response.headers["Location"]
    leg_day_id = int(leg_day_url.rstrip("/").split("/")[-1])

    # Sanity check: User A really can see Leg Day, both in the list and on its own page.
    # Without this, the checks below could pass just because the workout was never saved.
    assert b"Leg Day" in client.get("/").data
    assert client.get(f"/workouts/{leg_day_id}").status_code == 200

    # Step 3: User A logs out.
    log_out(client)

    # --- When: User B logs in and looks around -------------------------------

    # Step 4: User B creates an account, logs out, then logs in through the login page.
    sign_up(client, "user.b@example.com")
    log_out(client)
    log_in(client, "user.b@example.com")

    # Step 5: User B opens the workouts list (the home page).
    workouts_list = client.get("/")

    # Step 6: User B pastes Leg Day's URL straight into the address bar,
    # and also tries Leg Day's edit and delete pages.
    detail_page = client.get(f"/workouts/{leg_day_id}")
    edit_page = client.get(f"/workouts/{leg_day_id}/edit")
    delete_page = client.get(f"/workouts/{leg_day_id}/delete")
    # User B also tries submitting those forms directly (renaming Leg Day, and actually deleting it).
    edit_submit = client.post(
        f"/workouts/{leg_day_id}/edit",
        data={"date": "2026-11-03", "title": "Hacked", "workout_type": "lift", "effort": "3"},
    )
    delete_submit = client.post(f"/workouts/{leg_day_id}/delete")

    # --- Then: User B sees nothing of User A's --------------------------------

    # User B's list loads fine but is empty: no "Leg Day", just the empty-state message.
    assert workouts_list.status_code == 200
    assert b"Leg Day" not in workouts_list.data
    assert b"No workouts yet." in workouts_list.data

    # Every direct URL for Leg Day answers "Not found" (404), as if it doesn't exist.
    assert detail_page.status_code == 404
    assert edit_page.status_code == 404
    assert delete_page.status_code == 404
    assert edit_submit.status_code == 404
    assert delete_submit.status_code == 404

    # And User B's visits changed nothing: Leg Day is still saved, unchanged, for User A.
    db.session.expire_all()
    leg_day = db.session.get(Workout, leg_day_id)
    assert leg_day is not None and leg_day.title == "Leg Day"
