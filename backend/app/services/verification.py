"""Consent-based verification: request, signed token, revoke, public check, scoped history.

Refusal semantics (ADR-021): the precise reason is stored in verification_request and the audit
log. A verifier is told the precise reason only where it cannot reveal anything about a student
(approval state, or a field the public policy does not allow). Everything that depends on the
student or the consent (unknown ID, no consent, expired, withdrawn, purpose or field outside the
consent) is one generic answer, so a verifier cannot use refusals to find out which IDs exist.
"""
import uuid
from datetime import timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import settings
from app.domain.apaar import mask, normalize
from app.domain.consent import Allow, ConsentView, Request, decide
from app.models.consent import Consent, VerificationRequest, Verifier
from app.models.enums import INSTITUTION_ROLES, Role
from app.models.user import User
from app.services import audit, consents, notify, ratelimit, signing, verifiers
from app.services.errors import Conflict, Forbidden, NotFound, RateLimited

GENERIC = "CONSENT_NOT_AVAILABLE"
GENERIC_TEXT = "No valid consent is on record that covers this request."
EXPLICIT = {"FIELD_NOT_ALLOWED_BY_POLICY": "A requested field is not allowed for this purpose.",
            "VERIFIER_NOT_APPROVED": "Your organisation is not approved to verify for this purpose."}
REFUSAL_WINDOW = timedelta(minutes=5)


def public_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    return reason if reason in EXPLICIT else GENERIC


def public_message(reason: str) -> str:
    return EXPLICIT.get(reason, GENERIC_TEXT)


def verifier_of(db: Session, user: User) -> Verifier | None:
    return db.scalars(select(Verifier).where(Verifier.user_id == user.id)).first()


def _values(rec, prog) -> dict:
    return {"name": rec.name, "programme": prog.name, "status": rec.status, "level": prog.level,
            "year_of_study": rec.year_of_study, "admission_category": rec.admission_category}


def _view(c: Consent) -> ConsentView:
    return ConsentView(c.id, tuple(c.purposes), tuple(c.fields), c.given_at, c.expires_at,
                       c.withdrawn_at)


def request_verification(db: Session, user: User, *, apaar_id: str, purpose: str,
                         fields: list[str]) -> dict:
    verifier = verifier_of(db, user)
    if verifier is None:
        raise Forbidden("Not a registered verifier")
    key = f"vref:{verifier.id}"
    if ratelimit.blocked(key, settings.verify_max_refusals, REFUSAL_WINDOW):
        raise RateLimited("Too many refused requests. Try again in a few minutes.")
    apaar = normalize(apaar_id) or ""
    found = consents.current_record(db, apaar)
    held = db.scalars(select(Consent).where(Consent.apaar_id == apaar)).all() if apaar else []
    policy = verifiers.active_policy(db, purpose)
    now = clock.now()
    wanted = tuple(dict.fromkeys(fields))
    outcome = decide(Request(purpose, wanted, verifier_approved=(verifier.status == "APPROVED"
                                                  and purpose in verifier.requested_purposes),
                             student_exists=found is not None),
                     [_view(c) for c in held], policy.allowed_fields if policy else [], now)
    row = VerificationRequest(verifier_id=verifier.id, apaar_id=apaar, purpose=purpose,
                              fields_requested=list(wanted), outcome="REFUSED")
    db.add(row)
    db.flush()
    if not isinstance(outcome, Allow):
        row.refusal_reason, row.refusal_detail = outcome.reason, list(outcome.detail)
        audit.append(db, actor_id=user.id, actor_role=user.role, action="VERIFICATION.REFUSED",
                     entity_type="verification_request", entity_id=row.id,
                     after={"reason": outcome.reason, "detail": list(outcome.detail),
                            "purpose": purpose, "fields": list(wanted), "apaar_id": mask(apaar),
                            "verifier": verifier.org_name})
        ratelimit.hit(key, REFUSAL_WINDOW)
        return {"id": row.id, "outcome": "REFUSED", "reason": public_reason(outcome.reason),
                "message": public_message(outcome.reason),
                **({"detail": list(outcome.detail)} if outcome.reason in EXPLICIT else {})}

    rec, prog = found
    answer = {f: v for f, v in _values(rec, prog).items() if f in outcome.fields}
    row.outcome, row.consent_id = "GRANTED", outcome.consent_id
    row.token_jti, row.issued_at = str(uuid.uuid4()), now
    row.expires_at = now + timedelta(days=settings.verify_token_days)
    token = signing.sign({"jti": row.token_jti, "sub": mask(apaar), "purpose": purpose,
                          "fields": answer, "iat": row.issued_at, "exp": row.expires_at,
                          "iss": settings.verify_issuer})
    audit.append(db, actor_id=user.id, actor_role=user.role, action="VERIFICATION.GRANTED",
                 entity_type="verification_request", entity_id=row.id,
                 after={"purpose": purpose, "fields": list(outcome.fields),
                        "consent_id": outcome.consent_id, "jti": row.token_jti,
                        "apaar_id": mask(apaar), "verifier": verifier.org_name,
                        "expires_at": row.expires_at.isoformat()})
    staff = db.scalars(select(User).where(User.institution_id == prog.institution_id,
                                          User.role.in_([r.value for r in INSTITUTION_ROLES]),
                                          User.is_active)).all()
    notify.enqueue(db, list(staff), subject=f"Student record verified for {purpose}",
                   body=(f"A student's record ({mask(apaar)}) was verified for {purpose} by "
                         f"{verifier.org_name}. Fields shared: {', '.join(outcome.fields)}."),
                   related_type="verification", related_id=row.id)
    return {"id": row.id, "outcome": "GRANTED", "purpose": purpose, "fields": answer,
            "token": token, "qr_url": f"{settings.public_base_url.rstrip('/')}/verify/{token}",
            "issued_at": row.issued_at, "expires_at": row.expires_at}


def check(db: Session, token: str) -> dict:
    """Public. TAMPERED carries nothing at all. Every check is audited, with no actor."""
    empty = {"status": "TAMPERED", "fields": None, "issuer": None, "issued_at": None,
             "expires_at": None, "purpose": None}
    claims, row = None, None
    try:
        claims = signing.verify(token) if len(token) <= 4096 else None
    except jwt.PyJWTError:
        claims = None
    if claims is not None:
        row = db.scalars(select(VerificationRequest).where(
            VerificationRequest.token_jti == str(claims["jti"]))).first()
    if claims is None or row is None:
        out, entity = empty, "invalid"
    else:
        exp = claims["exp"]
        status = ("REVOKED" if row.revoked_at is not None
                  else "EXPIRED" if exp <= clock.now().timestamp() else "GENUINE")
        out = {"status": status, "fields": claims["fields"] if status == "GENUINE" else None,
               "issuer": claims["iss"], "issued_at": row.issued_at, "expires_at": row.expires_at,
               "purpose": claims["purpose"]}
        entity = row.id
    audit.append(db, actor_id=None, actor_role="PUBLIC", action="VERIFICATION.CHECKED",
                 entity_type="verification_request", entity_id=entity,
                 after={"status": out["status"]})
    return out


def revoke(db: Session, user: User, request_id: str) -> VerificationRequest:
    row = db.get(VerificationRequest, request_id)
    if row is None:
        raise NotFound("Verification not found")
    v = db.get(Verifier, row.verifier_id)
    allowed = (user.role == Role.AICTE_ADMIN
               or (user.role == Role.VERIFIER and v.user_id == user.id)
               or (user.role in INSTITUTION_ROLES
                   and consents.holds_student(db, user.institution_id, row.apaar_id)))
    if not allowed:
        raise Forbidden("Outside your scope")
    if row.outcome != "GRANTED":
        raise Conflict("No token was issued for this request")
    if row.revoked_at is not None:
        raise Conflict("Already revoked")
    row.revoked_at = clock.now()
    audit.append(db, actor_id=user.id, actor_role=user.role, action="VERIFICATION.REVOKED",
                 entity_type="verification_request", entity_id=row.id,
                 after={"jti": row.token_jti, "apaar_id": mask(row.apaar_id)})
    return row


def _scoped(db: Session, user: User):
    q = select(VerificationRequest, Verifier).join(Verifier, Verifier.id == VerificationRequest.verifier_id)
    if user.role == Role.VERIFIER:
        return q.where(Verifier.user_id == user.id)
    if (scope := consents.student_scope(db, user)) is not None:
        q = q.where(VerificationRequest.apaar_id.in_(scope))
    return q


def list_scoped(db: Session, user: User, limit: int, offset: int):
    rows = db.execute(_scoped(db, user).order_by(VerificationRequest.created_at.desc(),
                                                 VerificationRequest.id).limit(limit)
                      .offset(offset)).all()
    return [out(user, r, v) for r, v in rows]


def get_one(db: Session, user: User, request_id: str) -> dict:
    row = db.get(VerificationRequest, request_id)
    if row is None:
        raise NotFound("Verification not found")
    hit = db.execute(_scoped(db, user).where(VerificationRequest.id == request_id)).first()
    if hit is None:
        if user.role == Role.VERIFIER:  # someone else's request: indistinguishable from absent
            raise NotFound("Verification not found")
        raise Forbidden("Outside your scope")
    audit.append(db, actor_id=user.id, actor_role=user.role, action="VERIFICATION.VIEWED",
                 entity_type="verification_request", entity_id=row.id)
    return out(user, *hit)


def out(user: User, r: VerificationRequest, v: Verifier) -> dict:
    is_verifier = user.role == Role.VERIFIER
    reason = public_reason(r.refusal_reason) if is_verifier else r.refusal_reason
    show_detail = r.refusal_reason in EXPLICIT or not is_verifier
    d = {"id": r.id, "outcome": r.outcome, "purpose": r.purpose, "apaar_id": r.apaar_id,
         "fields_requested": r.fields_requested, "refusal_reason": reason,
         "refusal_detail": r.refusal_detail if show_detail and r.refusal_detail else None,
         "issued_at": r.issued_at, "expires_at": r.expires_at, "revoked_at": r.revoked_at,
         "created_at": r.created_at}
    if not is_verifier:
        d |= {"verifier": v.org_name, "consent_id": r.consent_id}
    return d

