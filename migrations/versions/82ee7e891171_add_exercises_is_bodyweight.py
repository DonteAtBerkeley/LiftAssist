"""add exercises.is_bodyweight

Revision ID: 82ee7e891171
Revises: abfe6ec09ba8
Create Date: 2026-11-04 17:06:28.061707

"""
from alembic import op
import sqlalchemy as sa

# Snapshot of the bodyweight exercises in app/catalog.py when this migration was written
# (copied, not imported, so this migration keeps working if the catalog changes later).
BODYWEIGHT_NAMES = [
    'ab wheel rollout',
    'air squat',
    'back extension',
    'bear crawl',
    'bench dip',
    'bicycle crunch',
    'bird dog',
    'box jump',
    'burpee',
    'calf raise',
    'chin-up',
    'crunch',
    'dead bug',
    'decline push-up',
    'diamond push-up',
    'dip',
    'flutter kick',
    'glute bridge',
    'handstand push-up',
    'hanging leg raise',
    'high knees',
    'hollow hold',
    'inverted row',
    'jump squat',
    'jumping jack',
    'l-sit',
    'lunge',
    'lying leg raise',
    'mountain climber',
    'muscle-up',
    'nordic curl',
    'pike push-up',
    'pistol squat',
    'plank',
    'pull-up',
    'push-up',
    'russian twist',
    'side plank',
    'sit-up',
    'step-up',
    'superman',
    'v-up',
    'walking lunge',
    'wall sit',
]


# revision identifiers, used by Alembic.
revision = '82ee7e891171'
down_revision = 'abfe6ec09ba8'
branch_labels = None
depends_on = None


def upgrade():
    # A plain ADD COLUMN, not batch mode: on SQLite, batch mode rebuilds the table by dropping
    # it, which the foreign key from sets.exercise_id refuses once any sets exist.
    op.add_column('exercises', sa.Column('is_bodyweight', sa.Boolean(), server_default=sa.false(), nullable=False))

    # Existing exercises that match a bodyweight catalog name (ignoring case) get tagged.
    exercises = sa.table("exercises", sa.column("name", sa.String), sa.column("is_bodyweight", sa.Boolean))
    op.execute(
        exercises.update()
        .where(sa.func.lower(sa.func.trim(exercises.c.name)).in_(BODYWEIGHT_NAMES))
        .values(is_bodyweight=True)
    )


def downgrade():
    # Plain DROP COLUMN (Postgres, and SQLite 3.35+) for the same reason as above.
    op.drop_column('exercises', 'is_bodyweight')
