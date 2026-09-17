"""alertes (recherches sauvegardees + notifications)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-19

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    alert_frequency = postgresql.ENUM("instant", "daily", name="alert_frequency")
    alert_frequency.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "saved_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "channels", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "frequency",
            postgresql.ENUM("instant", "daily", name="alert_frequency", create_type=False),
            nullable=False,
            server_default="instant",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_saved_searches_user_id", "saved_searches", ["user_id"])

    op.create_table(
        "alert_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "saved_search_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("saved_searches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channels_sent", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "saved_search_id", "job_id", name="uq_alert_notifications_search_job"
        ),
    )
    op.create_index(
        "ix_alert_notifications_saved_search_id", "alert_notifications", ["saved_search_id"]
    )
    op.create_index("ix_alert_notifications_job_id", "alert_notifications", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_alert_notifications_job_id", table_name="alert_notifications")
    op.drop_index("ix_alert_notifications_saved_search_id", table_name="alert_notifications")
    op.drop_table("alert_notifications")

    op.drop_index("ix_saved_searches_user_id", table_name="saved_searches")
    op.drop_table("saved_searches")

    postgresql.ENUM(name="alert_frequency").drop(op.get_bind(), checkfirst=True)
