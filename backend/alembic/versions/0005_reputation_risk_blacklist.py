"""reputation entreprise, score de risque, liste noire

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("domain", sa.String(length=255), nullable=True))

    op.add_column("jobs", sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "jobs", sa.Column("risk_reasons", postgresql.JSONB(), nullable=False, server_default="[]")
    )
    op.add_column("jobs", sa.Column("risk_assessed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "company_reputation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("trend_90d", sa.Numeric(4, 2), nullable=True),
        sa.Column("profile_age_days", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "company_id", "provider", name="uq_company_reputation_company_provider"
        ),
    )
    op.create_index("ix_company_reputation_company_id", "company_reputation", ["company_id"])

    blacklist_entity_type = postgresql.ENUM(
        "company", "recruiter", name="blacklist_entity_type"
    )
    blacklist_entity_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "entity_type",
            postgresql.ENUM("company", "recruiter", name="blacklist_entity_type", create_type=False),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_blacklist_user_id", "blacklist", ["user_id"])
    op.create_index("ix_blacklist_value", "blacklist", ["value"])


def downgrade() -> None:
    op.drop_index("ix_blacklist_value", table_name="blacklist")
    op.drop_index("ix_blacklist_user_id", table_name="blacklist")
    op.drop_table("blacklist")
    postgresql.ENUM(name="blacklist_entity_type").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_company_reputation_company_id", table_name="company_reputation")
    op.drop_table("company_reputation")

    op.drop_column("jobs", "risk_assessed_at")
    op.drop_column("jobs", "risk_reasons")
    op.drop_column("jobs", "risk_score")

    op.drop_column("companies", "domain")
