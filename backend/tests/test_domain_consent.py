"""decide(): every refusal reason, the allow path, and the exact expiry boundary."""
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.consent import Allow, ConsentView, Refuse, Request, decide

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
POLICY = ["name", "programme", "status"]


def consent(id="c1", purposes=("EMPLOYMENT",), fields=("name", "programme", "status"),
            given=NOW - timedelta(days=1), expires=NOW + timedelta(days=30), withdrawn=None):
    return ConsentView(id, tuple(purposes), tuple(fields), given, expires, withdrawn)


def req(fields=("name", "programme"), **kw):
    return Request(purpose=kw.pop("purpose", "EMPLOYMENT"), fields=tuple(fields), **kw)


def test_allow_returns_requested_fields_and_the_consent_used():
    out = decide(req(), [consent()], POLICY, NOW)
    assert out == Allow(fields=("name", "programme"), consent_id="c1")


@pytest.mark.parametrize("case,request_,consents,policy,reason,detail", [
    ("verifier not approved", req(verifier_approved=False), [consent()], POLICY,
     "VERIFIER_NOT_APPROVED", ()),
    ("unknown student", req(student_exists=False), [consent()], POLICY, "UNKNOWN_STUDENT", ()),
    ("no consent at all", req(), [], POLICY, "NO_CONSENT", ()),
    ("consent not yet given", req(), [consent(given=NOW + timedelta(seconds=1))], POLICY,
     "NO_CONSENT", ()),
    ("other purpose only", req(), [consent(purposes=("SCHOLARSHIP",))], POLICY,
     "PURPOSE_NOT_COVERED", ()),
    ("expired", req(), [consent(expires=NOW - timedelta(days=1))], POLICY, "EXPIRED", ()),
    ("expires exactly now", req(), [consent(expires=NOW)], POLICY, "EXPIRED", ()),
    ("withdrawn", req(), [consent(withdrawn=NOW - timedelta(hours=1))], POLICY, "WITHDRAWN", ()),
    ("withdrawn and expired", req(), [consent(withdrawn=NOW - timedelta(hours=1),
                                              expires=NOW - timedelta(days=1))], POLICY,
     "WITHDRAWN", ()),
    ("field outside policy", req(fields=("name", "dob")), [consent(fields=("name", "dob"))],
     POLICY, "FIELD_NOT_ALLOWED_BY_POLICY", ("dob",)),
    ("policy wins over unknown student", req(fields=("dob",), student_exists=False), [], POLICY,
     "FIELD_NOT_ALLOWED_BY_POLICY", ("dob",)),
    ("field outside consent", req(fields=("name", "status")), [consent(fields=("name",))],
     POLICY, "FIELD_NOT_IN_CONSENT", ("status",)),
    ("empty policy", req(), [consent()], [], "FIELD_NOT_ALLOWED_BY_POLICY", ("name", "programme")),
])
def test_refusals(case, request_, consents, policy, reason, detail):
    out = decide(request_, consents, policy, NOW)
    assert out == Refuse(reason=reason, detail=detail), case


def test_one_second_before_expiry_is_still_allowed():
    assert isinstance(decide(req(), [consent(expires=NOW + timedelta(seconds=1))], POLICY, NOW),
                      Allow)


def test_withdrawal_in_the_future_is_not_yet_a_withdrawal():
    c = consent(withdrawn=NOW + timedelta(hours=1))
    assert isinstance(decide(req(), [c], POLICY, NOW), Allow)


def test_never_silently_trimmed():
    out = decide(req(fields=("name", "status")), [consent(fields=("name",))], POLICY, NOW)
    assert isinstance(out, Refuse)  # not Allow(("name",))


def test_a_valid_consent_beats_an_expired_or_withdrawn_one():
    old = consent("old", expires=NOW - timedelta(days=1))
    gone = consent("gone", withdrawn=NOW - timedelta(days=1))
    assert decide(req(), [old, gone, consent("ok")], POLICY, NOW).consent_id == "ok"


def test_consent_must_cover_all_fields_in_one_record():
    a = consent("a", fields=("name",))
    b = consent("b", fields=("programme",))
    out = decide(req(), [a, b], POLICY, NOW)  # two partial consents do not add up
    assert out == Refuse("FIELD_NOT_IN_CONSENT", ("programme",))
