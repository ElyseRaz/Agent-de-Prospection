import httpx

from app.notifications.base import NotificationError


class DiscordWebhookChannel:
    """Envoie un message via un webhook entrant Discord (URL unique pour
    toute l'instance, meme principe que Slack)."""

    def __init__(self, *, webhook_url: str, http_client: httpx.AsyncClient) -> None:
        self._webhook_url = webhook_url
        self._http_client = http_client

    async def send(self, *, to: str, subject: str, body: str) -> None:
        try:
            response = await self._http_client.post(
                self._webhook_url, json={"content": f"**{subject}**\n{body}"}
            )
        except httpx.TransportError as exc:
            raise NotificationError(f"Webhook Discord injoignable: {exc}") from exc

        if response.status_code not in (200, 204):
            raise NotificationError(
                f"Webhook Discord a repondu {response.status_code}: {response.text}"
            )
