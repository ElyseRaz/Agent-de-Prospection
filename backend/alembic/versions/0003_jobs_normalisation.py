"""companies, skills, jobs, job_skills, llm_extraction_cache, llm_calls

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    contract_type = postgresql.ENUM("freelance", "cdi", "mission", name="contract_type")
    contract_type.create(op.get_bind(), checkfirst=True)

    seniority_level = postgresql.ENUM(
        "junior", "intermediate", "senior", "lead", "expert", name="seniority_level"
    )
    seniority_level.create(op.get_bind(), checkfirst=True)

    remote_type = postgresql.ENUM(
        "full_remote", "remote_zone_restricted", "hybrid", "onsite", name="remote_type"
    )
    remote_type.create(op.get_bind(), checkfirst=True)

    rate_period = postgresql.ENUM("hour", "day", "month", "year", "fixed", name="rate_period")
    rate_period.create(op.get_bind(), checkfirst=True)

    job_status = postgresql.ENUM("active", "expired", "archived", name="job_status")
    job_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("normalized_name", name="uq_companies_normalized_name"),
    )
    op.create_index("ix_companies_normalized_name", "companies", ["normalized_name"])

    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=150), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("aliases", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.UniqueConstraint("slug", name="uq_skills_slug"),
    )
    op.create_index("ix_skills_slug", "skills", ["slug"])

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "canonical_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "raw_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description_clean", sa.Text(), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="autre"),
        sa.Column(
            "contract_type",
            postgresql.ENUM("freelance", "cdi", "mission", name="contract_type", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "seniority",
            postgresql.ENUM(
                "junior",
                "intermediate",
                "senior",
                "lead",
                "expert",
                name="seniority_level",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("rate_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("rate_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("rate_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "rate_period",
            postgresql.ENUM(
                "hour", "day", "month", "year", "fixed", name="rate_period", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("rate_eur_normalized", sa.Numeric(12, 2), nullable=True),
        sa.Column("duration_months", sa.Numeric(5, 2), nullable=True),
        sa.Column("workload_days_week", sa.Numeric(3, 1), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column(
            "remote_type",
            postgresql.ENUM(
                "full_remote",
                "remote_zone_restricted",
                "hybrid",
                "onsite",
                name="remote_type",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("timezone_constraint", sa.String(length=255), nullable=True),
        sa.Column(
            "required_languages", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
        sa.Column("billing_mode", sa.String(length=100), nullable=True),
        sa.Column("application_channel", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "status",
            postgresql.ENUM("active", "expired", "archived", name="job_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_jobs_source_external"),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_source_id", "jobs", ["source_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_detected_at", "jobs", ["detected_at"])

    op.create_table(
        "job_skills",
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weight", sa.Numeric(4, 2), nullable=False, server_default="1.0"),
    )

    op.create_table(
        "llm_extraction_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("response_json", postgresql.JSONB(), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("content_hash", "prompt_version", "purpose", name="uq_llm_cache_key"),
    )
    op.create_index("ix_llm_extraction_cache_content_hash", "llm_extraction_cache", ["content_hash"])

    op.create_table(
        "llm_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_llm_calls_content_hash", "llm_calls", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_content_hash", table_name="llm_calls")
    op.drop_table("llm_calls")

    op.drop_index("ix_llm_extraction_cache_content_hash", table_name="llm_extraction_cache")
    op.drop_table("llm_extraction_cache")

    op.drop_table("job_skills")

    op.drop_index("ix_jobs_detected_at", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_source_id", table_name="jobs")
    op.drop_index("ix_jobs_company_id", table_name="jobs")
    op.drop_table("jobs")

    op.drop_index("ix_skills_slug", table_name="skills")
    op.drop_table("skills")

    op.drop_index("ix_companies_normalized_name", table_name="companies")
    op.drop_table("companies")

    postgresql.ENUM(name="job_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="rate_period").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="remote_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="seniority_level").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="contract_type").drop(op.get_bind(), checkfirst=True)
