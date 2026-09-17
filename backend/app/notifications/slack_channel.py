import httpx

from app.notifications.base import NotificationError


class SlackWebhookChannel:
    """Envoie un message via un webhook entrant Slack (URL unique pour toute
    l'instance, pas de credential par utilisateur - voir README § Alertes)."""

    def __init__(self, *, webhook_url: str, http_client: httpx.AsyncClient) -> None:
        self._webhook_url = webhook_url
        self._http_client = http_client

    async def send(self, *, to: str, subject: str, body: str) -> None:
        try:
            response = await self._http_client.post(
                self._webhook_url, json={"text": f"*{subject}*\n{body}"}
            )
        except httpx.TransportError as exc:
            raise NotificationError(f"Webhook Slack injoignable: {exc}") from exc

        if response.status_code != 200:
            raise NotificationError(
                f"Webhook Slack a repondu {response.status_code}: {response.text}"
            )
