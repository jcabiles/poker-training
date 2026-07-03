"""owner_id seam: owner column on drill_attempt + srs_item, srs_item PK -> (owner_id, signature)

Empty string '' = the local user (sentinel, no accounts). Existing rows backfill
via the server default. srs_item needs a batch table rebuild for the PK change.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _srs_item_copy_from(with_owner: bool) -> sa.Table:
    """Current srs_item shape, PK omitted so batch mode can (re)define it."""
    cols = [
        sa.Column("signature", sa.String(), nullable=False),
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
        sa.Column("villain_type", sa.String(), nullable=True),
        sa.Column("street", sa.String(), nullable=True),
        sa.Column("texture_class", sa.String(), nullable=True),
        sa.Column("spr_bucket", sa.String(), nullable=True),
        sa.Column("faced_bet_bucket", sa.String(), nullable=True),
    ]
    if with_owner:
        cols.append(
            sa.Column("owner_id", sa.String(), nullable=False, server_default=sa.text("''"))
        )
    return sa.Table("srs_item", sa.MetaData(), *cols, sa.Index("ix_srs_item_due_date", "due_date"))


def upgrade() -> None:
    op.add_column(
        "drill_attempt",
        sa.Column("owner_id", sa.String(), nullable=False, server_default=sa.text("''")),
    )
    with op.batch_alter_table(
        "srs_item", copy_from=_srs_item_copy_from(with_owner=False), recreate="always"
    ) as batch:
        batch.add_column(
            sa.Column("owner_id", sa.String(), nullable=False, server_default=sa.text("''"))
        )
        batch.create_primary_key("pk_srs_item", ["owner_id", "signature"])


def downgrade() -> None:
    with op.batch_alter_table(
        "srs_item", copy_from=_srs_item_copy_from(with_owner=True), recreate="always"
    ) as batch:
        batch.drop_column("owner_id")
        batch.create_primary_key("pk_srs_item", ["signature"])
    with op.batch_alter_table("drill_attempt") as batch:
        batch.drop_column("owner_id")
