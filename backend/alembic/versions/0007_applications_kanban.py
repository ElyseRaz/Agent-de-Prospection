"""suivi de candidature (kanban CRM)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-18

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    application_stage = postgresql.ENUM(
        "spotted",
        "to_apply",
        "applied",
        "in_discussion",
        "proposal",
        "won",
        "lost",
        name="application_stage",
    )
    application_stage.create(op.get_bind(), checkfirst=True)

    application_event_type = postgresql.ENUM(
        "stage_changed", "note_updated", "followup_scheduled", name="application_event_type"
    )
    application_event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stage",
            postgresql.ENUM(
                "spotted",
                "to_apply",
                "applied",
                "in_discussion",
                "proposal",
                "won",
                "lost",
                name="application_stage",
                create_type=False,
            ),
            nullable=False,
            server_default="spotted",
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_followup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("outcome", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("profile_id", "job_id", name="uq_applications_profile_job"),
    )
    op.create_index("ix_applications_profile_id", "applications", ["profile_id"])
    op.create_index("ix_applications_job_id", "applications", ["job_id"])

    op.create_table(
        "application_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            postgresql.ENUM(
                "stage_changed",
                "note_updated",
                "followup_scheduled",
                name="application_event_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_application_events_application_id", "application_events", ["application_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_application_events_application_id", table_name="application_events")
    op.drop_table("application_events")

    op.drop_index("ix_applications_job_id", table_name="applications")
    op.drop_index("ix_applications_profile_id", table_name="applications")
    op.drop_table("applications")

    postgresql.ENUM(name="application_event_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="application_stage").drop(op.get_bind(), checkfirst=True)
