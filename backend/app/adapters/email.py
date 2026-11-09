import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

from app.domain.apaar import mask

log = logging.getLogger("email")


class EmailAdapter(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmail:
    """Stub: logs the message and remembers it. Swap for SMTP when a real gateway is approved."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})
        log.info("EMAIL to=%s subject=%s", to, subject)


class EmailSendError(Exception):
    """A send failed. The message is safe to store: the SMTP password is stripped."""


class SmtpEmail:
    """Plain-text email over SMTP (stdlib only). Port 465 uses implicit SSL, otherwise STARTTLS
    when use_tls. Any 12-digit run in the body is masked as a last line of defence against
    leaking a full APAAR ID. Tested against a fake SMTP only."""

    def __init__(self, *, host: str, port: int, username: str, password: str, use_tls: bool,
                 sender: str, timeout: float = 15.0) -> None:
        self._host, self._port, self._user, self._pw = host, port, username, password
        self._tls, self._from, self._timeout = use_tls, sender, timeout

    def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self._from, to, subject
        msg.set_content(re.sub(r"\b\d{12}\b", lambda m: mask(m.group()), body))
        try:
            ctx = ssl.create_default_context()
            if self._port == 465:
                conn = smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=ctx)
            else:
                conn = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
            with conn:
                if self._port != 465 and self._tls:
                    conn.starttls(context=ctx)
                if self._user:
                    conn.login(self._user, self._pw)
                conn.send_message(msg)
        except Exception as e:  # noqa: BLE001  anything can fail; re-raise without the secret
            text = f"{type(e).__name__}: {e}"
            if self._pw:
                text = text.replace(self._pw, "***")
            raise EmailSendError(text[:300]) from None


def build_email_adapter(cfg) -> EmailAdapter:
    if cfg.email_backend == "smtp":
        return SmtpEmail(host=cfg.smtp_host, port=cfg.smtp_port, username=cfg.smtp_username,
                         password=cfg.smtp_password.get_secret_value(), use_tls=cfg.smtp_use_tls,
                         sender=cfg.email_from)
    return ConsoleEmail()
