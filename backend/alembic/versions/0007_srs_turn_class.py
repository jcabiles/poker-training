"""srs_item turn_class column (S6 turn SRS dimension)

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("srs_item", sa.Column("turn_class", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("srs_item") as batch:
        batch.drop_column("turn_class")
