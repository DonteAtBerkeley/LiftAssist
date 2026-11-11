from datetime import datetime, timezone

from flask_login import UserMixin
import sqlalchemy as sa
from sqlalchemy import CheckConstraint, UniqueConstraint, event
from sqlalchemy.engine import Engine
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager
from .recommendations import DEFAULT_REP_MAX, DEFAULT_REP_MIN


def _utcnow():
    return datetime.now(timezone.utc)


@event.listens_for(Engine, "connect")
def _sqlite_enforce_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked. Postgres always enforces them."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    workouts = db.relationship(
        "Workout", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    exercises = db.relationship(
        "Exercise", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    stars = db.relationship(
        "Star", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    # Convenience: the workouts this user has starred (read-only; add/remove via Star rows).
    starred_workouts = db.relationship(
        "Workout", secondary="stars", viewonly=True, order_by="Workout.date.desc()"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Workout(db.Model):
    __tablename__ = "workouts"
    __table_args__ = (
        CheckConstraint("workout_type IN ('lift', 'run')", name="ck_workouts_type"),
        CheckConstraint("effort IS NULL OR (effort BETWEEN 1 AND 5)", name="ck_workouts_effort"),
        CheckConstraint("duration_min IS NULL OR duration_min >= 0", name="ck_workouts_duration"),
        CheckConstraint("distance_mi IS NULL OR distance_mi >= 0", name="ck_workouts_distance"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(120))
    workout_type = db.Column(db.String(10), nullable=False)
    duration_min = db.Column(db.Integer)
    distance_mi = db.Column(db.Float)  # runs only
    effort = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship("User", back_populates="workouts")
    sets = db.relationship(
        "Set",
        back_populates="workout",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Set.set_number",
    )
    stars = db.relationship(
        "Star", back_populates="workout", cascade="all, delete-orphan", passive_deletes=True
    )
    # Convenience: the distinct exercises done in this workout (many-to-many through sets).
    exercises = db.relationship("Exercise", secondary="sets", viewonly=True)


class Exercise(db.Model):
    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_exercises_user_name"),
        CheckConstraint("rep_min >= 1", name="ck_exercises_rep_min"),
        CheckConstraint("rep_max >= rep_min", name="ck_exercises_rep_range"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    rep_min = db.Column(db.Integer, nullable=False, default=DEFAULT_REP_MIN, server_default=str(DEFAULT_REP_MIN))
    rep_max = db.Column(db.Integer, nullable=False, default=DEFAULT_REP_MAX, server_default=str(DEFAULT_REP_MAX))
    # True for exercises done without added weight (push-ups, pull-ups...). Copied from the
    # built-in catalog (app/catalog.py) when the user first logs the exercise; custom names are weighted.
    is_bodyweight = db.Column(db.Boolean, nullable=False, default=False, server_default=sa.false())

    user = db.relationship("User", back_populates="exercises")
    sets = db.relationship("Set", back_populates="exercise")
    # Convenience: every workout this exercise appears in (many-to-many through sets).
    workouts = db.relationship("Workout", secondary="sets", viewonly=True)


class Set(db.Model):
    __tablename__ = "sets"
    __table_args__ = (
        CheckConstraint("reps >= 1", name="ck_sets_reps"),
        CheckConstraint("weight_lb >= 0", name="ck_sets_weight"),
        CheckConstraint("set_number >= 1", name="ck_sets_set_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer, db.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # No cascade: the database refuses to delete an exercise that still has sets logged.
    exercise_id = db.Column(
        db.Integer, db.ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    set_number = db.Column(db.Integer, nullable=False)
    weight_lb = db.Column(db.Float, nullable=False, default=0)
    reps = db.Column(db.Integer, nullable=False)

    workout = db.relationship("Workout", back_populates="sets")
    exercise = db.relationship("Exercise", back_populates="sets")


class Star(db.Model):
    __tablename__ = "stars"
    __table_args__ = (UniqueConstraint("user_id", "workout_id", name="uq_stars_user_workout"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workout_id = db.Column(
        db.Integer, db.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship("User", back_populates="stars")
    workout = db.relationship("Workout", back_populates="stars")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
