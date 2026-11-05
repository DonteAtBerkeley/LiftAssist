from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
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


# --- Workouts (Feature 3) ---------------------------------------------------
# Only the basics are checked here (required fields, and nothing the database
# would reject). Friendlier, fuller validation messages come in Feature 4.

class SetForm(Form):
    """One row on the workout form. A plain Form (not FlaskForm) so rows don't each get a CSRF token."""

    exercise = StringField("Exercise", validators=[Optional()])
    weight_lb = FloatField("Weight (lb)", validators=[Optional(), NumberRange(min=0)])
    reps = IntegerField("Reps", validators=[Optional(), NumberRange(min=1)])

    def is_blank(self):
        return not (self.exercise.data or "").strip() and self.weight_lb.data is None and self.reps.data is None

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if self.is_blank():
            return ok
        if not (self.exercise.data or "").strip():
            self.exercise.errors.append("Exercise is required.")
            ok = False
        if self.reps.data is None and not self.reps.errors:
            self.reps.errors.append("Reps are required.")
            ok = False
        return ok


class WorkoutForm(FlaskForm):
    date = DateField("Date", default=date.today, validators=[DataRequired(message="Date is required.")])
    title = StringField("Title", validators=[Optional(), Length(max=120)])
    workout_type = RadioField(
        "Type",
        choices=[SelectChoice("lift", "Lift"), SelectChoice("run", "Run")],
        default="lift",
        validators=[DataRequired(message="Pick lift or run.")],
    )
    duration_min = IntegerField("Duration (min)", validators=[Optional(), NumberRange(min=0)])
    effort = SelectField(
        "Effort (1–5)",
        choices=[SelectChoice("", "—")] + [SelectChoice(str(n), str(n)) for n in range(1, 6)],
        validators=[Optional()],
        coerce=lambda v: int(v) if v not in (None, "") else None,
    )
    distance_mi = FloatField("Distance (mi)", validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField("Notes", validators=[Optional()])
    sets = FieldList(FormField(SetForm), min_entries=0)
    submit = SubmitField("Save workout")

    def filled_sets(self):
        """The set rows the user actually typed into (fully blank rows are ignored)."""
        return [row.form for row in self.sets if not row.form.is_blank()]
