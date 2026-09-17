import asyncio
import smtplib
from email.mime.text import MIMEText

from app.notifications.base import NotificationError


class SMTPEmailChannel:
    """Envoie un email via SMTP. `smtplib` est synchrone : l'appel bloquant
    est deporte dans un thread (`asyncio.to_thread`) pour ne jamais bloquer
    la boucle d'evenements asyncio du serveur/worker."""

    def __init__(
        self, *, host: str, port: int, user: str, password: str, use_tls: bool = True
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._use_tls = use_tls

    async def send(self, *, to: str, subject: str, body: str) -> None:
        try:
            await asyncio.to_thread(self._send_sync, to, subject, body)
        except (OSError, smtplib.SMTPException) as exc:
            raise NotificationError(f"Envoi email echoue vers {to}: {exc}") from exc

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        message = MIMEText(body, "plain", "utf-8")
        message["Subject"] = subject
        message["From"] = self._user
        message["To"] = to

        with smtplib.SMTP(self._host, self._port, timeout=10) as server:
            if self._use_tls:
                server.starttls()
            server.login(self._user, self._password)
            server.send_message(message)
