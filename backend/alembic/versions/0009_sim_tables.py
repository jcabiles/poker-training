"""sim_session + sim_seat + sim_hand tables (S9 hero plays / session persistence)

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sim_session",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), nullable=False, server_default=""),
        sa.Column("button_seat", sa.Integer(), nullable=False),
        sa.Column("hand_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sim_session_owner_id", "sim_session", ["owner_id"])
    op.create_table(
        "sim_seat",
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("sim_session.id"),
            primary_key=True,
        ),
        sa.Column("seat_index", sa.Integer(), primary_key=True),
        sa.Column("is_hero", sa.Boolean(), nullable=False),
        sa.Column("persona_type", sa.String(), nullable=True),
        sa.Column("stack_bb", sa.Float(), nullable=False),
        sa.Column("buyins_bb", sa.Float(), nullable=False),
    )
    op.create_table(
        "sim_hand",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("sim_session.id"), nullable=False),
        sa.Column("hand_no", sa.Integer(), nullable=False),
        sa.Column("button_seat", sa.Integer(), nullable=False),
        sa.Column("rng_seed", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="in_progress"),
        sa.Column("state_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sim_hand_session_id", "sim_hand", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_sim_hand_session_id", table_name="sim_hand")
    op.drop_table("sim_hand")
    op.drop_table("sim_seat")
    op.drop_index("ix_sim_session_owner_id", table_name="sim_session")
    op.drop_table("sim_session")
