"""srs_item postflop columns (postflop SRS review)

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("srs_item", sa.Column("street", sa.String(), nullable=True))
    op.add_column("srs_item", sa.Column("texture_class", sa.String(), nullable=True))
    op.add_column("srs_item", sa.Column("spr_bucket", sa.String(), nullable=True))
    op.add_column("srs_item", sa.Column("faced_bet_bucket", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("srs_item") as batch:
        batch.drop_column("faced_bet_bucket")
        batch.drop_column("spr_bucket")
        batch.drop_column("texture_class")
        batch.drop_column("street")
