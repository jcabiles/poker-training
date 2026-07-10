"""srs_item river_class column (S7 river SRS dimension)

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("srs_item", sa.Column("river_class", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("srs_item") as batch:
        batch.drop_column("river_class")
