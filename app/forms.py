import math
from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    BooleanField,
    EmailField,
    FieldList,
    FloatField,
    Form,
    FormField,
    IntegerField,
    PasswordField,
    RadioField,
    SelectChoice,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


class SignupForm(FlaskForm):
    email = EmailField(
        "Email",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Please enter a valid email address."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, message="Password must be at least 8 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Sign up")


class LoginForm(FlaskForm):
    email = EmailField(
        "Email", validators=[DataRequired(message="Email is required.")]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(message="Password is required.")]
    )
    submit = SubmitField("Log in")


# --- Workouts (Features 3 + 4) ----------------------------------------------
# These checks run on the server every time the form is submitted, so bad data
# is rejected even if someone skips the browser form (or edits its HTML).
# Every message is written to be shown right next to the field it's about.

MSG_DATE = "Pick a date — today or earlier."
MSG_TITLE_LONG = "Keep the name to 120 characters or fewer."
MSG_TYPE = "Choose lift or run."
MSG_EFFORT = "Effort must be a whole number from 1 to 5."
MSG_DURATION = "Duration must be more than 0 minutes."
MSG_DURATION_NUMBER = "Duration must be a whole number of minutes."
MSG_DURATION_MAX = "That's more than a day — check the duration."
MSG_DISTANCE = "How far did you run?"
MSG_DISTANCE_POSITIVE = "Distance must be more than 0 miles."
MSG_DISTANCE_NUMBER = "Distance must be a number, like 3.1."
MSG_NO_SETS = "Add at least one set."
MSG_EXERCISE = "Add the exercise name."
MSG_EXERCISE_LONG = "Keep exercise names to 120 characters or fewer."
MSG_REPS = "Reps must be at least 1."
MSG_REPS_MISSING = "How many reps?"
MSG_REPS_NUMBER = "Reps must be a whole number."
MSG_REPS_MAX = "That's a lot of reps — check this number."
MSG_WEIGHT = "Weight can't be negative."
MSG_WEIGHT_NUMBER = "Weight must be a number (leave it blank for bodyweight)."
MSG_SUMMARY = "Please fix the highlighted fields."
MSG_BLANK_WEIGHT = "Some sets have no weight. Is this a bodyweight exercise?"

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MAX_DURATION_MIN = 24 * 60
MAX_REPS = 1000


def number_check(ok, message):
    """Reject a number that fails `ok(value)`, or isn't finite ("inf" and "nan" parse as floats!).

    Blank or unreadable values are skipped: "required" and "not a number" have their own messages.
    """

    def _check(form, field):
        if field.data is None:
            return
        if not math.isfinite(field.data) or not ok(field.data):
            raise ValidationError(message)

    return _check


def _effort(value):
    """"" -> None (effort is optional); "3" -> 3; anything else ("6" fails the choice check, "abc" raises)."""
    if value in (None, ""):
        return None
    return int(value)


def _has_input(field):
    return bool(field.raw_data and str(field.raw_data[0]).strip())


class SetForm(Form):
    """One row on the workout form. A plain Form (not FlaskForm) so rows don't each get a CSRF token."""

    needs_weight = False  # set by the view: blank weight on a weighted exercise (see the warning)

    exercise = StringField(
        "Exercise",
        filters=[lambda v: " ".join(v.split()) if isinstance(v, str) else v],
        validators=[Optional(), Length(max=120, message=MSG_EXERCISE_LONG)],
    )
    weight_lb = FloatField(
        "Weight (lb)",
        invalid_value_message=MSG_WEIGHT_NUMBER,
        validators=[Optional(), number_check(lambda x: x >= 0, MSG_WEIGHT)],
    )
    reps = IntegerField(
        "Reps",
        invalid_value_message=MSG_REPS_NUMBER,
        validators=[
            Optional(),
            number_check(lambda x: x >= 1, MSG_REPS),
            number_check(lambda x: x <= MAX_REPS, MSG_REPS_MAX),
        ],
    )

    def weight_is_blank(self):
        return not _has_input(self.weight_lb)

    def is_blank(self):
        """True if the user typed nothing at all in this row (such rows are skipped, not errors)."""
        return not any(_has_input(f) for f in (self.exercise, self.weight_lb, self.reps))

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if self.is_blank():
            return True
        if not self.exercise.data:
            self.exercise.errors.append(MSG_EXERCISE)
            ok = False
        if self.reps.data is None and not self.reps.errors:
            self.reps.errors.append(MSG_REPS_MISSING)
            ok = False
        return ok

    def clear_errors(self):
        for f in self:
            f.errors = []


class WorkoutForm(FlaskForm):
    date = DateField(
        "Date",
        default=date.today,
        invalid_value_message=MSG_DATE,
        validators=[DataRequired(message=MSG_DATE)],
    )
    title = StringField(
        "Title",
        filters=[lambda v: v.strip() if isinstance(v, str) else v],
        # Optional: a blank title becomes e.g. "Wednesday, Nov 4 — Lift" (see default_title).
        validators=[Optional(), Length(max=120, message=MSG_TITLE_LONG)],
    )
    workout_type = RadioField(
        "Type",
        choices=[SelectChoice("lift", "Lift"), SelectChoice("run", "Run")],
        default="lift",
        invalid_choice_message=MSG_TYPE,
        validators=[DataRequired(message=MSG_TYPE)],
    )
    duration_min = IntegerField(
        "Duration (min)",
        invalid_value_message=MSG_DURATION_NUMBER,
        validators=[
            Optional(),
            number_check(lambda x: x > 0, MSG_DURATION),
            number_check(lambda x: x <= MAX_DURATION_MIN, MSG_DURATION_MAX),
        ],
    )
    effort = SelectField(
        "Effort (1–5)",
        choices=[SelectChoice("", "—")] + [SelectChoice(str(n), str(n)) for n in range(1, 6)],
        coerce=_effort,
        invalid_value_message=MSG_EFFORT,
        invalid_choice_message=MSG_EFFORT,
        validators=[Optional()],
    )
    distance_mi = FloatField(
        "Distance (mi)",
        invalid_value_message=MSG_DISTANCE_NUMBER,
        validators=[Optional(), number_check(lambda x: x > 0, MSG_DISTANCE_POSITIVE)],
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    sets = FieldList(FormField(SetForm), min_entries=0)
    submit = SubmitField("Save workout")
    # Sent only by the "Save anyway" button on the blank-weight warning.
    confirm_blank_weight = BooleanField()

    # Form-wide errors that don't belong to a single input.
    sets_error = None
    summary_error = None

    def validate_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError(MSG_DATE)

    def validate(self, extra_validators=None):
        super().validate(extra_validators)
        self.sets_error = None

        if self.workout_type.data == "run":
            # Set rows are hidden for runs and never saved, so they can't block the save.
            for row in self.sets:
                row.form.clear_errors()
            self.sets.errors = []
            if self.distance_mi.data is None and not self.distance_mi.errors:
                self.distance_mi.errors.append(MSG_DISTANCE)
        else:
            # Distance is hidden for lifts and never saved.
            self.distance_mi.errors = []
            if self.workout_type.data == "lift" and not self.filled_sets():
                self.sets_error = MSG_NO_SETS

        has_errors = bool(self.errors) or bool(self.sets_error)
        self.summary_error = MSG_SUMMARY if has_errors else None
        return not has_errors

    def default_title(self):
        """e.g. "Wednesday, Nov 4 — Lift". Used when the title is left blank."""
        d = self.date.data
        return f"{DAY_NAMES[d.weekday()]}, {MONTH_ABBR[d.month - 1]} {d.day} — {self.workout_type.data.title()}"

    def filled_sets(self):
        """The set rows the user actually typed into (fully blank rows are ignored)."""
        return [row.form for row in self.sets if not row.form.is_blank()]


# --- Exercises (Feature 10) --------------------------------------------------

MSG_REP_MIN_MISSING = "Enter the lowest reps you're aiming for."
MSG_REP_MAX_MISSING = "Enter the highest reps you're aiming for."
MSG_REP_RANGE_NUMBER = "Reps must be a whole number."
MSG_REP_MIN = "Min reps must be at least 1."
MSG_REP_MAX_ORDER = "Max reps must be more than min reps."


class RepRangeForm(FlaskForm):
    rep_min = IntegerField(
        "Min reps",
        invalid_value_message=MSG_REP_RANGE_NUMBER,
        validators=[InputRequired(message=MSG_REP_MIN_MISSING)],
    )
    rep_max = IntegerField(
        "Max reps",
        invalid_value_message=MSG_REP_RANGE_NUMBER,
        validators=[InputRequired(message=MSG_REP_MAX_MISSING)],
    )

    def validate_rep_min(self, field):
        if field.data is not None and field.data < 1:
            raise ValidationError(MSG_REP_MIN)

    def validate_rep_max(self, field):
        if field.data is None:
            return
        if field.data > MAX_REPS:
            raise ValidationError(MSG_REPS_MAX)
        if self.rep_min.data is not None and field.data <= self.rep_min.data:
            raise ValidationError(MSG_REP_MAX_ORDER)
