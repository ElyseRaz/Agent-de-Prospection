FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir .

# Pre-telecharge le modele d'embedding au build (une fois, en cache dans
# l'image) : les conteneurs n'ont jamais besoin de reseau au demarrage pour
# les embeddings. Augmente la taille de l'image (~1-2 Go) et le temps de
# build, en echange d'un demarrage rapide et hors-ligne des conteneurs.
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')"

FROM base AS dev
RUN pip install --no-cache-dir .[dev]
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
