"""sim_decision.sizing_correctness column (N3 preflop sizing grades)

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Additive nullable — existing rows read back with NULL, no backfill.
    op.add_column(
        "sim_decision",
        sa.Column("sizing_correctness", sa.String(), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table("sim_decision") as batch:
        batch.drop_column("sizing_correctness")
