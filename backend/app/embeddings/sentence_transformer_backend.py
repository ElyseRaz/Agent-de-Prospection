import asyncio

from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"


class SentenceTransformerEmbeddingBackend:
    """Implementation reelle : modele local sentence-transformers (fr+en),
    aucune cle API, aucun appel reseau a l'execution. Le modele est telecharge
    a la construction : l'image Docker le pre-telecharge au build pour eviter
    tout appel reseau au demarrage des conteneurs (voir backend/Dockerfile)."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self._model = SentenceTransformer(model_name)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        vectors = await loop.run_in_executor(None, self._encode, texts)
        return [vector.tolist() for vector in vectors]

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0]

    def _encode(self, texts: list[str]):
        return self._model.encode(texts, normalize_embeddings=True)
