"""Consent decision. Pure: no framework imports. Allowed fields = requested, policy and consent.

If any requested field is outside the policy list or the consent, the whole request is refused and
the field is named. Nothing is ever silently trimmed.
"""
from dataclasses import dataclass
from datetime import datetime

REASONS = ("NO_CONSENT", "EXPIRED", "WITHDRAWN", "PURPOSE_NOT_COVERED",
           "FIELD_NOT_ALLOWED_BY_POLICY", "FIELD_NOT_IN_CONSENT", "UNKNOWN_STUDENT",
           "VERIFIER_NOT_APPROVED")


@dataclass(frozen=True)
class ConsentView:
    id: str
    purposes: tuple[str, ...]
    fields: tuple[str, ...]
    given_at: datetime
    expires_at: datetime
    withdrawn_at: datetime | None = None


@dataclass(frozen=True)
class Request:
    purpose: str
    fields: tuple[str, ...]
    verifier_approved: bool = True
    student_exists: bool = True


@dataclass(frozen=True)
class Allow:
    fields: tuple[str, ...]
    consent_id: str


@dataclass(frozen=True)
class Refuse:
    reason: str
    detail: tuple[str, ...] = ()


def _missing(wanted, have) -> tuple[str, ...]:
    return tuple(f for f in wanted if f not in have)


def decide(request: Request, consents: list[ConsentView], policy, now: datetime) -> Allow | Refuse:
    if not request.verifier_approved:
        return Refuse("VERIFIER_NOT_APPROVED")
    # Policy first: it depends only on purpose and fields, never on the student, so a refusal
    # here tells the caller nothing about whether an ID exists.
    if outside := _missing(request.fields, policy):
        return Refuse("FIELD_NOT_ALLOWED_BY_POLICY", outside)
    if not request.student_exists:
        return Refuse("UNKNOWN_STUDENT")
    given = [c for c in consents if c.given_at <= now]
    if not given:
        return Refuse("NO_CONSENT")
    covering = [c for c in given if request.purpose in c.purposes]
    if not covering:
        return Refuse("PURPOSE_NOT_COVERED")
    withdrawn = [c for c in covering if c.withdrawn_at is not None and c.withdrawn_at <= now]
    live = [c for c in covering if c not in withdrawn and c.expires_at > now]
    if not live:
        return Refuse("WITHDRAWN" if withdrawn else "EXPIRED")
    best = None
    for c in sorted(live, key=lambda c: c.given_at, reverse=True):
        gap = _missing(request.fields, c.fields)
        if not gap:
            return Allow(request.fields, c.id)
        if best is None or len(gap) < len(best):
            best = gap
    return Refuse("FIELD_NOT_IN_CONSENT", best)
