"""sources, scrape_runs, raw_documents + seed connecteur Remotive

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-14

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REMOTIVE_COMPLIANCE_NOTE = (
    "API publique documentee par Remotive (https://remotive.com/api/remote-jobs), "
    "sans authentification, destinee a un usage programmatique. Aucun scraping HTML, "
    "aucun contournement de protection anti-bot."
)


def upgrade() -> None:
    access_type = postgresql.ENUM("api", "rss", "html_public", name="access_type")
    access_type.create(op.get_bind(), checkfirst=True)

    scrape_run_status = postgresql.ENUM("running", "success", "failed", name="scrape_run_status")
    scrape_run_status.create(op.get_bind(), checkfirst=True)

    processing_status = postgresql.ENUM("pending", "processed", "failed", name="processing_status")
    processing_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column(
            "access_type",
            postgresql.ENUM("api", "rss", "html_public", name="access_type", create_type=False),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "schedule_cron", sa.String(length=100), nullable=False, server_default="0 * * * *"
        ),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("compliance_note", sa.Text(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_sources_slug", "sources", ["slug"], unique=True)

    op.create_table(
        "scrape_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "running", "success", "failed", name="scrape_run_status", create_type=False
            ),
            nullable=False,
            server_default="running",
        ),
        sa.Column("items_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_scrape_runs_source_id", "scrape_runs", ["source_id"])

    op.create_table(
        "raw_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scrape_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "processing_status",
            postgresql.ENUM(
                "pending", "processed", "failed", name="processing_status", create_type=False
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_documents_source_external"),
    )
    op.create_index("ix_raw_documents_source_id", "raw_documents", ["source_id"])
    op.create_index("ix_raw_documents_run_id", "raw_documents", ["run_id"])

    op.bulk_insert(
        sa.table(
            "sources",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("slug", sa.String),
            sa.column("name", sa.String),
            sa.column("kind", sa.String),
            sa.column("base_url", sa.String),
            sa.column("access_type", sa.String),
            sa.column("schedule_cron", sa.String),
            sa.column("rate_limit_rpm", sa.Integer),
            sa.column("compliance_note", sa.Text),
            sa.column("config", postgresql.JSONB),
        ),
        [
            {
                "id": uuid.uuid4(),
                "slug": "remotive",
                "name": "Remotive",
                "kind": "remotive",
                "base_url": "https://remotive.com/api/remote-jobs",
                "access_type": "api",
                "schedule_cron": "*/30 * * * *",
                "rate_limit_rpm": 20,
                "compliance_note": REMOTIVE_COMPLIANCE_NOTE,
                "config": {},
            }
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_raw_documents_run_id", table_name="raw_documents")
    op.drop_index("ix_raw_documents_source_id", table_name="raw_documents")
    op.drop_table("raw_documents")

    op.drop_index("ix_scrape_runs_source_id", table_name="scrape_runs")
    op.drop_table("scrape_runs")

    op.drop_index("ix_sources_slug", table_name="sources")
    op.drop_table("sources")

    postgresql.ENUM(name="processing_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="scrape_run_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="access_type").drop(op.get_bind(), checkfirst=True)
