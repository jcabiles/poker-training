"""sim_decision spot-dim columns (N5 — by-spot dashboard drill-down)

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Additive nullable — existing rows read back with NULL, no backfill.
    op.add_column("sim_decision", sa.Column("position", sa.String(), nullable=True))
    op.add_column(
        "sim_decision", sa.Column("facing_position", sa.String(), nullable=True)
    )
    op.add_column(
        "sim_decision", sa.Column("players_in_pot", sa.Integer(), nullable=True)
    )
    op.add_column("sim_decision", sa.Column("node_context", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sim_decision") as batch:
        batch.drop_column("node_context")
        batch.drop_column("players_in_pot")
        batch.drop_column("facing_position")
        batch.drop_column("position")
