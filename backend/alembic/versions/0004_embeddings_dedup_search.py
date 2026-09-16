"""embeddings, recherche plein texte, deduplication

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSION = 768


def upgrade() -> None:
    op.add_column("jobs", sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=True))
    op.add_column("jobs", sa.Column("search_tsv", postgresql.TSVECTOR(), nullable=True))
    op.add_column("jobs", sa.Column("dedup_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_jobs_dedup_hash", "jobs", ["dedup_hash"])

    # HNSW pour la recherche vectorielle approximative (cosinus).
    op.execute(
        "CREATE INDEX ix_jobs_embedding_hnsw ON jobs "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    # GIN pour la recherche plein texte.
    op.execute("CREATE INDEX ix_jobs_search_tsv_gin ON jobs USING gin (search_tsv)")
    # GIN trigramme pour la similarite de titre (niveau 2 de deduplication).
    op.execute("CREATE INDEX ix_jobs_title_trgm ON jobs USING gin (title gin_trgm_ops)")

    op.create_table(
        "job_duplicate_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "canonical_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "duplicate_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("similarity_score", sa.Numeric(5, 4), nullable=False),
        sa.Column(
            "detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("duplicate_job_id", name="uq_job_duplicate_links_duplicate"),
    )
    op.create_index(
        "ix_job_duplicate_links_canonical_job_id", "job_duplicate_links", ["canonical_job_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_job_duplicate_links_canonical_job_id", table_name="job_duplicate_links")
    op.drop_table("job_duplicate_links")

    op.execute("DROP INDEX IF EXISTS ix_jobs_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_jobs_search_tsv_gin")
    op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw")

    op.drop_index("ix_jobs_dedup_hash", table_name="jobs")
    op.drop_column("jobs", "dedup_hash")
    op.drop_column("jobs", "search_tsv")
    op.drop_column("jobs", "embedding")
