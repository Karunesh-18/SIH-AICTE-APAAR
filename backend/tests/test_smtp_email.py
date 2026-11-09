"""SMTP adapter, tested against a recording fake of smtplib only (no real provider)."""
import smtplib
import socket
from typing import ClassVar

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select

from app.adapters import email as email_mod
from app.adapters.email import ConsoleEmail, SmtpEmail
from app.core.config import Settings
from app.db.session import uow
from app.models.notify import Outbox
from app.services import notify

SECRET = "hunter2-very-secret"


class FakeSMTP:
    log: ClassVar[list] = []
    fail = False

    def __init__(self, host, port, timeout=None, **kw):
        self.kw = dict(host=host, port=port, timeout=timeout, **kw)
        FakeSMTP.log.append(("connect", self.kw))

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, **kw):
        FakeSMTP.log.append(("starttls",))

    def login(self, u, p):
        FakeSMTP.log.append(("login", u))
        if FakeSMTP.fail:
            raise smtplib.SMTPAuthenticationError(535, f"bad credentials {p}".encode())

    def send_message(self, msg):
        FakeSMTP.log.append(("send", msg))


@pytest.fixture
def fake(monkeypatch):
    FakeSMTP.log, FakeSMTP.fail = [], False
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def _adapter(**kw):
    args = {"host": "mail.example.test", "port": 587, "username": "u", "password": SECRET,
            "use_tls": True, "sender": "hub@example.test"}
    return SmtpEmail(**{**args, **kw})


def test_message_sent_once_with_headers_and_masked_plain_body(fake):
    _adapter().send("a@demo.test", "Flag raised", "Student 123456789012 flagged.")
    sends = [e[1] for e in fake.log if e[0] == "send"]
    assert len(sends) == 1
    m = sends[0]
    assert (m["To"], m["From"], m["Subject"]) == ("a@demo.test", "hub@example.test", "Flag raised")
    assert not m.is_multipart() and m.get_content_type() == "text/plain"
    body = m.get_content()
    assert "123456789012" not in body and "XXXX XXXX 9012" in body
    assert ("starttls",) in fake.log and ("login", "u") in fake.log
    assert fake.log[0][1]["timeout"] > 0


def test_port_465_uses_ssl_not_starttls(fake):
    _adapter(port=465).send("a@demo.test", "s", "b")
    assert ("starttls",) not in fake.log


def test_failure_keeps_outbox_pending_with_attempts_and_clean_error(db, world, fake):
    fake.fail = True
    notify.set_adapter(_adapter())
    try:
        with uow(db):
            notify.enqueue(db, [world["users"]["admin"]], subject="s", body="b")
        notify.dispatch_now(db)
        row = db.scalars(select(Outbox)).one()
        assert row.dispatched_at is None and row.attempts == 1
        assert row.last_error and SECRET not in row.last_error
    finally:
        notify.set_adapter(ConsoleEmail())


def test_retry_cap_stops_retries(db, world, fake):
    fake.fail = True
    notify.set_adapter(_adapter())
    try:
        with uow(db):
            notify.enqueue(db, [world["users"]["admin"]], subject="s", body="b")
        for _ in range(notify.MAX_ATTEMPTS + 3):
            notify.dispatch_now(db)
        assert sum(1 for e in fake.log if e[0] == "send") == 0
        assert sum(1 for e in fake.log if e[0] == "login") == notify.MAX_ATTEMPTS
        assert db.scalars(select(Outbox)).one().attempts == notify.MAX_ATTEMPTS
    finally:
        notify.set_adapter(ConsoleEmail())


def test_console_default_opens_no_socket(db, world, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network touched")
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket.socket, "connect", boom)
    assert Settings(_env_file=None).email_backend == "console"
    assert isinstance(email_mod.build_email_adapter(Settings(_env_file=None)), ConsoleEmail)
    with uow(db):
        notify.enqueue(db, [world["users"]["admin"]], subject="s", body="b")
    assert notify.dispatch_now(db)["sent"] == 1


@pytest.mark.parametrize("missing", ["smtp_host", "email_from"])
def test_smtp_backend_refuses_to_start_without_host_or_from(missing):
    kw = {"email_backend": "smtp", "smtp_host": "h", "email_from": "a@b.test"}
    kw[missing] = ""
    with pytest.raises(ValidationError, match="SMTP_HOST|EMAIL_FROM"):
        Settings(_env_file=None, **kw)


def test_password_is_secret_and_never_echoed():
    s = Settings(_env_file=None, email_backend="smtp", smtp_host="h", email_from="a@b.test",
                 smtp_password=SECRET)
    assert isinstance(s.smtp_password, SecretStr)
    assert SECRET not in repr(s) and SECRET not in str(s.model_dump())


def test_build_adapter_selects_smtp():
    s = Settings(_env_file=None, email_backend="smtp", smtp_host="h", email_from="a@b.test")
    assert isinstance(email_mod.build_email_adapter(s), SmtpEmail)
