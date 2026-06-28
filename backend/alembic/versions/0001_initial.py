"""initial — drill_attempt

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drill_attempt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("spot_signature", sa.String(), nullable=False),
        sa.Column("leak_category", sa.Integer(), nullable=True),
        sa.Column("chosen_action", sa.String(), nullable=False),
        sa.Column("correctness", sa.String(), nullable=True),
        sa.Column("ev_loss_bb", sa.Float(), nullable=False, server_default="0"),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_drill_attempt_spot_signature", "drill_attempt", ["spot_signature"])


def downgrade() -> None:
    op.drop_index("ix_drill_attempt_spot_signature", table_name="drill_attempt")
    op.drop_table("drill_attempt")
