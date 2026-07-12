"""sim_decision table + drill_attempt.source column (S10 grading wired in)

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sim_decision",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "session_id",
            sa.String(),
            sa.ForeignKey("sim_session.id"),
            nullable=False,
        ),
        sa.Column(
            "sim_hand_id",
            sa.Integer(),
            sa.ForeignKey("sim_hand.id"),
            nullable=False,
        ),
        sa.Column("street", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("chosen_action", sa.String(), nullable=False),
        sa.Column("correctness", sa.String(), nullable=True),
        sa.Column("ev_loss_bb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("leak_category", sa.Integer(), nullable=True),
        sa.Column("coverage", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sim_decision_session_id", "sim_decision", ["session_id"])
    op.create_index("ix_sim_decision_sim_hand_id", "sim_decision", ["sim_hand_id"])
    # Nullable-with-default: historical Practice rows read back 'practice'.
    op.add_column(
        "drill_attempt",
        sa.Column("source", sa.String(), nullable=True, server_default="practice"),
    )


def downgrade() -> None:
    with op.batch_alter_table("drill_attempt") as batch:
        batch.drop_column("source")
    op.drop_index("ix_sim_decision_sim_hand_id", table_name="sim_decision")
    op.drop_index("ix_sim_decision_session_id", table_name="sim_decision")
    op.drop_table("sim_decision")
