import httpx

from app.notifications.base import NotificationError


class TelegramBotChannel:
    """Envoie un message via un bot Telegram (`sendMessage`), vers le
    `chat_id` configure pour l'instance (bot + chat uniques, pas de
    credential par utilisateur - voir README § Alertes)."""

    def __init__(self, *, bot_token: str, chat_id: str, http_client: httpx.AsyncClient) -> None:
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._http_client = http_client

    async def send(self, *, to: str, subject: str, body: str) -> None:
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        try:
            response = await self._http_client.post(
                url, json={"chat_id": self._chat_id, "text": f"{subject}\n\n{body}"}
            )
        except httpx.TransportError as exc:
            raise NotificationError(f"API Telegram injoignable: {exc}") from exc

        if response.status_code != 200:
            raise NotificationError(
                f"API Telegram a repondu {response.status_code}: {response.text}"
            )
