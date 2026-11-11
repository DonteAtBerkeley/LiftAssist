"""Feature 8: the My PRs page. The math lives in app/prs.py; this only gathers and shows it."""

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from . import prs

bp = Blueprint("prs", __name__)


@bp.route("/prs")
@login_required
def my_prs():
    return render_template("prs.html", summary=prs.pr_summary(current_user.id))
