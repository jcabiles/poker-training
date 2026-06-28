"""srs_item.villain_type (exploit drills)

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("srs_item", sa.Column("villain_type", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("srs_item") as batch:
        batch.drop_column("villain_type")
