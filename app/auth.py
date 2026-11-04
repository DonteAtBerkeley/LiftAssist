from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .forms import LoginForm, SignupForm
from .models import User

bp = Blueprint("auth", __name__)


def _normalize(email):
    return email.strip().lower()


def _safe_next(target):
    # Only follow relative "next" links so a crafted URL can't bounce users to another site.
    if target and not urlsplit(target).netloc and target.startswith("/"):
        return target
    return url_for("main.home")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = SignupForm()
    if form.validate_on_submit():
        email = _normalize(form.email.data)
        if db.session.execute(db.select(User).filter_by(email=email)).scalar():
            form.email.errors.append("An account with that email already exists.")
        else:
            user = User(email=email)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to LiftAssist!", "success")
            return redirect(url_for("main.home"))
    return render_template("auth/signup.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    error = None
    if form.validate_on_submit():
        email = _normalize(form.email.data)
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(_safe_next(request.args.get("next")))
        error = "Email or password is incorrect."
    return render_template("auth/login.html", form=form, error=error)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("auth.login"))
