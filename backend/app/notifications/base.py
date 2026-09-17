from typing import Protocol


class NotificationError(Exception):
    """Leve quand l'envoi echoue (reseau, credentials invalides, etc.).

    Toujours attrapee par l'appelant (`app/services/alerts.py`) : une panne
    d'un canal ne doit jamais empecher les autres canaux d'etre tentes, ni
    faire echouer l'evaluation complete d'une recherche sauvegardee."""


class NotificationChannel(Protocol):
    """Un canal d'envoi (email, Slack, Telegram, Discord...). Meme esprit que
    `SourceConnector`/`EmbeddingBackend` : implementation injectable, aucun
    appel reseau reel dans les tests (doubles dans `tests/conftest.py`)."""

    async def send(self, *, to: str, subject: str, body: str) -> None: ...
