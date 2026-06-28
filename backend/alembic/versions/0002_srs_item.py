"""srs_item

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "srs_item",
        sa.Column("signature", sa.String(), primary_key=True),
        sa.Column("node_context", sa.String(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
        sa.Column("facing", sa.String(), nullable=True),
        sa.Column("limper_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leak_category", sa.Integer(), nullable=True),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("last_grade", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_srs_item_due_date", "srs_item", ["due_date"])


def downgrade() -> None:
    op.drop_index("ix_srs_item_due_date", table_name="srs_item")
    op.drop_table("srs_item")
