import logging
from typing import Protocol

log = logging.getLogger("sms")


class SmsAdapter(Protocol):
    def send(self, to: str, body: str) -> None: ...


class StubSms:
    """Stub: only logs. No SMS provider is connected."""

    def send(self, to: str, body: str) -> None:
        log.info("SMS to=%s (stub, not sent)", to)
