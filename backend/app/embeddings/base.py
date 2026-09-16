from typing import Protocol


class EmbeddingBackend(Protocol):
    """Seam injectable : la vraie implementation charge un modele
    sentence-transformers local, les tests injectent un double deterministe
    sans modele ni reseau."""

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...
