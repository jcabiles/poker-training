"""drill_attempt hand_class column (Challenge mode T1)

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("drill_attempt", sa.Column("hand_class", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("drill_attempt") as batch:
        batch.drop_column("hand_class")
