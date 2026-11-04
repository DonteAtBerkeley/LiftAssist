from app.models import User


def test_signup_logout_login(client):
    email, password = "lifter@example.com", "squat-1234"

    r = client.post(
        "/signup",
        data={"email": email, "password": password, "confirm_password": password},
        follow_redirects=True,
    )
    assert f"Welcome, {email}".encode() in r.data

    user = User.query.filter_by(email=email).one()
    assert user.password_hash != password  # stored hashed, not plain text

    r = client.post("/logout", follow_redirects=True)
    assert b"Log in" in r.data
    assert client.get("/").status_code == 302  # home now redirects to login

    r = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )
    assert f"Welcome, {email}".encode() in r.data
