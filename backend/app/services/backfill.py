from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingBackend
from app.embeddings.text_builder import build_embedding_text
from app.models.job import Job
from app.normalization.search_index import search_tsv_expression
from app.services.deduplication import compute_dedup_hash, deduplicate_job


@dataclass(slots=True)
class BackfillSummary:
    embedded: int = 0
    skipped: int = 0


async def backfill_embeddings_and_dedup(
    db: AsyncSession, *, embedding_backend: EmbeddingBackend, limit: int = 100
) -> BackfillSummary:
    """Complete `embedding`/`search_tsv`/`dedup_hash` pour les jobs qui n'en
    ont pas encore (normalises avant l'existence de cette phase), puis lance
    la deduplication. N'appelle jamais le LLM : aucun cout d'extraction."""

    jobs = (
        (await db.execute(select(Job).where(Job.embedding.is_(None)).limit(limit)))
        .scalars()
        .all()
    )

    summary = BackfillSummary()
    for job in jobs:
        if not job.title and not job.description_clean:
            summary.skipped += 1
            continue

        text = build_embedding_text(
            title=job.title, description_clean=job.description_clean, tech_stack=[]
        )
        job.embedding = (await embedding_backend.embed_documents([text]))[0]
        job.dedup_hash = compute_dedup_hash(job.title, None, job.description_clean)

        await db.execute(
            update(Job)
            .where(Job.id == job.id)
            .values(search_tsv=search_tsv_expression(job.title, job.description_clean))
        )
        await db.flush()

        await deduplicate_job(db, job)
        summary.embedded += 1

    await db.commit()
    return summary
