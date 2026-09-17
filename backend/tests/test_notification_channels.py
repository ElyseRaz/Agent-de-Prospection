import json
import smtplib

import httpx
import pytest

from app.notifications.base import NotificationError
from app.notifications.discord_channel import DiscordWebhookChannel
from app.notifications.email_channel import SMTPEmailChannel
from app.notifications.slack_channel import SlackWebhookChannel
from app.notifications.telegram_channel import TelegramBotChannel

pytestmark = pytest.mark.asyncio


async def test_slack_channel_sends_expected_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    channel = SlackWebhookChannel(webhook_url="https://hooks.slack.test/abc", http_client=client)

    await channel.send(to="ignored", subject="Nouvelle offre", body="Details ici")
    await client.aclose()

    assert captured["url"] == "https://hooks.slack.test/abc"
    assert "Nouvelle offre" in captured["json"]["text"]
    assert "Details ici" in captured["json"]["text"]


async def test_slack_channel_raises_notification_error_on_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    channel = SlackWebhookChannel(webhook_url="https://hooks.slack.test/abc", http_client=client)

    with pytest.raises(NotificationError):
        await channel.send(to="ignored", subject="s", body="b")
    await client.aclose()


async def test_discord_channel_sends_expected_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = json.loads(request.content)
        return httpx.Response(204)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    channel = DiscordWebhookChannel(webhook_url="https://discord.test/webhook", http_client=client)

    await channel.send(to="ignored", subject="Alerte", body="Corps")
    await client.aclose()

    assert "Alerte" in captured["json"]["content"]


async def test_telegram_channel_sends_chat_id_and_text():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    channel = TelegramBotChannel(bot_token="123:ABC", chat_id="999", http_client=client)

    await channel.send(to="ignored", subject="Alerte", body="Corps")
    await client.aclose()

    assert captured["url"] == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert captured["json"]["chat_id"] == "999"
    assert "Alerte" in captured["json"]["text"]


async def test_telegram_channel_raises_on_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns fail", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    channel = TelegramBotChannel(bot_token="123:ABC", chat_id="999", http_client=client)

    with pytest.raises(NotificationError):
        await channel.send(to="ignored", subject="s", body="b")
    await client.aclose()


class _FakeSMTP:
    """Double de `smtplib.SMTP` : capture les appels, aucun socket ouvert."""

    instances: list["_FakeSMTP"] = []

    def __init__(self, host, port, timeout=10):
        self.host = host
        self.port = port
        self.started_tls = False
        self.logged_in = None
        self.sent_message = None
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = (user, password)

    def send_message(self, message):
        self.sent_message = message


async def test_email_channel_sends_via_smtp(monkeypatch):
    _FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

    channel = SMTPEmailChannel(
        host="smtp.test", port=587, user="bot@example.com", password="secret"
    )
    await channel.send(to="dest@example.com", subject="Sujet", body="Corps du message")

    assert len(_FakeSMTP.instances) == 1
    instance = _FakeSMTP.instances[0]
    assert instance.started_tls is True
    assert instance.logged_in == ("bot@example.com", "secret")
    assert instance.sent_message["To"] == "dest@example.com"
    assert instance.sent_message["Subject"] == "Sujet"


async def test_email_channel_wraps_smtp_errors(monkeypatch):
    class _FailingSMTP(_FakeSMTP):
        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr(smtplib, "SMTP", _FailingSMTP)

    channel = SMTPEmailChannel(
        host="smtp.test", port=587, user="bot@example.com", password="wrong"
    )
    with pytest.raises(NotificationError):
        await channel.send(to="dest@example.com", subject="s", body="b")
