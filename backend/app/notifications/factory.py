import httpx

from app.core.config import Settings
from app.models.alert import NotificationChannelKind
from app.notifications.base import NotificationChannel
from app.notifications.discord_channel import DiscordWebhookChannel
from app.notifications.email_channel import SMTPEmailChannel
from app.notifications.slack_channel import SlackWebhookChannel
from app.notifications.telegram_channel import TelegramBotChannel


def build_notification_channels(
    settings: Settings, *, http_client: httpx.AsyncClient
) -> dict[str, NotificationChannel]:
    """Construit un canal par type configure. Un canal dont les variables
    d'environnement requises sont absentes est simplement omis (meme
    principe que Trustpilot phase 5 : fonctionnalite optionnelle, pas
    d'erreur au demarrage). `app/services/alerts.py` journalise et ignore
    toute recherche sauvegardee demandant un canal non configure."""

    channels: dict[str, NotificationChannel] = {}

    if settings.smtp_host and settings.smtp_user and settings.smtp_password:
        channels[NotificationChannelKind.EMAIL.value] = SMTPEmailChannel(
            host=settings.smtp_host,
            port=settings.smtp_port or 587,
            user=settings.smtp_user,
            password=settings.smtp_password,
        )

    if settings.slack_webhook_url:
        channels[NotificationChannelKind.SLACK.value] = SlackWebhookChannel(
            webhook_url=settings.slack_webhook_url, http_client=http_client
        )

    if settings.discord_webhook_url:
        channels[NotificationChannelKind.DISCORD.value] = DiscordWebhookChannel(
            webhook_url=settings.discord_webhook_url, http_client=http_client
        )

    if settings.telegram_bot_token and settings.telegram_chat_id:
        channels[NotificationChannelKind.TELEGRAM.value] = TelegramBotChannel(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            http_client=http_client,
        )

    return channels
