import logging
from typing import Protocol

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
