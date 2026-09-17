"""profils freelance, competences de profil, matching, feedback

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSION = 768

DEFAULT_WEIGHTS_JSON = (
    '{"semantic": 25, "skills": 30, "rate": 25, "timezone": 10, "reliability": 10}'
)


def upgrade() -> None:
    skill_level = postgresql.ENUM(
        "beginner", "intermediate", "advanced", "expert", name="skill_level"
    )
    skill_level.create(op.get_bind(), checkfirst=True)

    match_feedback_action = postgresql.ENUM("saved", "rejected", name="match_feedback_action")
    match_feedback_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_rate", sa.Numeric(12, 2), nullable=True),
        sa.Column("floor_rate", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("availability_date", sa.Date(), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("languages", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column(
            "excluded_industries",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "desired_contract_types",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=True),
        sa.Column(
            "weights", postgresql.JSONB(), nullable=False, server_default=DEFAULT_WEIGHTS_JSON
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"])

    op.create_table(
        "profile_skills",
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "level",
            postgresql.ENUM(
                "beginner", "intermediate", "advanced", "expert", name="skill_level", create_type=False
            ),
            nullable=False,
            server_default="intermediate",
        ),
        sa.Column("years", sa.Numeric(4, 1), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "matches",
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
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("profile_id", "job_id", name="uq_matches_profile_job"),
    )
    op.create_index("ix_matches_profile_id", "matches", ["profile_id"])
    op.create_index("ix_matches_job_id", "matches", ["job_id"])

    op.create_table(
        "match_feedback",
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
            "action",
            postgresql.ENUM("saved", "rejected", name="match_feedback_action", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("profile_id", "job_id", name="uq_match_feedback_profile_job"),
    )
    op.create_index("ix_match_feedback_profile_id", "match_feedback", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_match_feedback_profile_id", table_name="match_feedback")
    op.drop_table("match_feedback")

    op.drop_index("ix_matches_job_id", table_name="matches")
    op.drop_index("ix_matches_profile_id", table_name="matches")
    op.drop_table("matches")

    op.drop_table("profile_skills")

    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")

    postgresql.ENUM(name="match_feedback_action").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="skill_level").drop(op.get_bind(), checkfirst=True)
