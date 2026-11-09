"""Consent-based verification end to end: grant, every refusal, the token, scope and attacks."""
import base64
import hashlib
import hmac
import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import clock
from app.models.audit import AuditLog
from app.models.consent import VerificationRequest
from app.models.notify import Notification
from app.services import audit, signing
from tests.ingest_helpers import ap
from tests.phase6_helpers import V, ask, give, scene, second_verifier

GENERIC = "CONSENT_NOT_AVAILABLE"


@pytest.fixture
def s(db, world):
    return scene(db, world)


@pytest.fixture
def vh(login, s):
    return login("verifier@demo.test")


def actions(db):
    return [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def flip(token: str, part: int) -> str:
    parts = token.split(".")
    mid = len(parts[part]) // 2
    c = parts[part][mid]
    parts[part] = parts[part][:mid] + ("A" if c != "A" else "B") + parts[part][mid + 1:]
    return ".".join(parts)


# --- grant -------------------------------------------------------------------------------

def test_consent_found_returns_three_fields_and_a_signed_token(client, db, vh, world):
    r = ask(client, vh, ap(1))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "GRANTED"
    assert body["fields"] == {"name": "Aarav Nair", "programme": "MBA", "status": "valid"}
    assert body["qr_url"].endswith("/verify/" + body["token"])
    chk = client.get(f"/api/v1/verify/{body['token']}").json()
    assert chk["status"] == "GENUINE" and chk["fields"] == body["fields"]
    assert chk["purpose"] == "EMPLOYMENT" and chk["issuer"] and chk["expires_at"]
    assert "9999" not in json.dumps(chk)  # no raw ID in the public answer
    assert "VERIFICATION.GRANTED" in actions(db)
    assert audit.verify(db)["ok"]


def test_institution_is_told_without_an_unmasked_id(client, db, vh, world):
    ask(client, vh, ap(1))
    notes = db.scalars(select(Notification).where(
        Notification.user_id == world["users"]["inst_admin"].id)).all()
    assert notes and "Fictional Employer" in notes[0].body and "EMPLOYMENT" in notes[0].body
    assert ap(1) not in notes[0].body and ap(1) not in notes[0].subject
    other = db.scalars(select(Notification).where(
        Notification.related_type == "verification")).all()
    assert all(n.user_id != world["users"]["admin"].id for n in other)


def test_id_with_spaces_is_normalised(client, vh):
    assert ask(client, vh, "9999 0000 0001").json()["outcome"] == "GRANTED"


def test_token_carries_only_allowed_fields_and_masked_id(client, vh):
    tok = ask(client, vh, ap(1), fields=("name",)).json()["token"]
    claims = signing.decode_unverified(tok)
    assert claims["fields"] == {"name": "Aarav Nair"}
    assert claims["sub"] == "XXXX XXXX 0001" and claims["purpose"] == "EMPLOYMENT"
    assert {"jti", "iat", "exp", "iss"} <= set(claims)


# --- refusals ----------------------------------------------------------------------------

def refused(client, vh, apaar, **kw):
    r = ask(client, vh, apaar, **kw)
    assert r.status_code == 200
    assert r.json()["outcome"] == "REFUSED"
    return r.json()


def test_no_consent_is_refused_and_audited(client, db, vh):
    assert refused(client, vh, ap(2))["reason"] == GENERIC
    row = db.scalars(select(VerificationRequest)).all()[-1]
    assert row.refusal_reason == "NO_CONSENT" and row.token_jti is None
    assert "VERIFICATION.REFUSED" in actions(db)


def test_withdrawn_and_expired_consent_refuse(client, db, vh, s):
    give(db, ap(2), withdrawn=clock.now() - timedelta(hours=1))
    assert refused(client, vh, ap(2))["reason"] == GENERIC
    give(db, ap(5), days=1)
    clock.set_offset(2 * 86400)
    try:
        assert refused(client, vh, ap(5))["reason"] == GENERIC
    finally:
        clock.set_offset(0)
    reasons = [r.refusal_reason for r in db.scalars(select(VerificationRequest))]
    assert reasons == ["WITHDRAWN", "EXPIRED"]
    assert actions(db).count("VERIFICATION.REFUSED") == 2 and audit.verify(db)["ok"]


def test_other_purpose_only_refuses(client, db, vh):
    give(db, ap(2), purposes=("SCHOLARSHIP",))
    refused(client, vh, ap(2))
    assert db.scalars(select(VerificationRequest)).one().refusal_reason == "PURPOSE_NOT_COVERED"


def test_field_outside_consent_refuses_whole_request_not_trimmed(client, db, vh):
    give(db, ap(2), fields=("name",))
    body = refused(client, vh, ap(2))
    assert "fields" not in body and "token" not in body
    assert db.scalars(select(VerificationRequest)).one().refusal_reason == "FIELD_NOT_IN_CONSENT"


def test_field_outside_policy_names_the_field(client, vh):
    body = refused(client, vh, ap(1), fields=("name", "level", "year_of_study"))
    assert body["reason"] == "FIELD_NOT_ALLOWED_BY_POLICY"  # EMPLOYMENT policy has no level
    assert body["detail"] == ["level", "year_of_study"]


def test_unknown_field_name_and_extra_keys_are_rejected(client, vh):
    assert ask(client, vh, ap(1), fields=("dob",)).status_code == 422
    r = client.post(V, headers=vh, json={"apaar_id": ap(1), "purpose": "EMPLOYMENT",
                                         "fields": ["name"], "verifier_id": "x"})
    assert r.status_code == 422
    assert ask(client, vh, ap(1), purpose="GOSSIP").status_code == 422
    assert ask(client, vh, ap(1), fields=()).status_code == 422


def test_withdrawn_student_record_is_unknown(client, db, vh):
    from app.models.student import StudentRecord
    rec = db.scalars(select(StudentRecord).where(StudentRecord.apaar_id == ap(1))).one()
    rec.status = "withdrawn"
    db.commit()
    refused(client, vh, ap(1))
    assert db.scalars(select(VerificationRequest)).one().refusal_reason == "UNKNOWN_STUDENT"


def test_superseded_record_does_not_count_as_current(client, db, vh):
    from app.models.student import StudentRecord
    rec = db.scalars(select(StudentRecord).where(StudentRecord.apaar_id == ap(1))).one()
    rec.is_current = False
    db.commit()
    refused(client, vh, ap(1))


def test_verifier_that_is_not_approved_is_refused(client, db, login, s):
    s.status = "PENDING"  # an active user whose organisation is not approved
    db.commit()
    r = ask(client, login("verifier@demo.test"), ap(1))
    assert r.json()["outcome"] == "REFUSED" and r.json()["reason"] == "VERIFIER_NOT_APPROVED"
    assert db.scalars(select(VerificationRequest)).one().refusal_reason == "VERIFIER_NOT_APPROVED"


def test_user_without_a_verifier_record_gets_403(client, db, login, world, s):
    from app.models.consent import Verifier
    db.delete(s)
    db.commit()
    assert db.scalars(select(Verifier)).first() is None
    assert ask(client, login("verifier@demo.test"), ap(1)).status_code == 403


# --- enumeration -------------------------------------------------------------------------

def test_unknown_id_and_missing_consent_look_the_same_to_the_verifier(client, db, vh):
    unknown = refused(client, vh, "999999999999")
    no_consent = refused(client, vh, ap(2))
    strip = lambda b: {k: v for k, v in b.items() if k != "id"}  # noqa: E731
    assert strip(unknown) == strip(no_consent)
    # the precise reason is kept in the audit log, not in the verifier's view
    after = [a.after for a in db.scalars(select(AuditLog).where(
        AuditLog.action == "VERIFICATION.REFUSED"))]
    assert {a["reason"] for a in after} == {"UNKNOWN_STUDENT", "NO_CONSENT"}
    hist = client.get(V, headers=vh).json()["items"]
    assert {h["refusal_reason"] for h in hist if h["outcome"] == "REFUSED"} == {GENERIC}
    one = client.get(f"{V}/{unknown['id']}", headers=vh).json()
    assert one["refusal_reason"] == GENERIC


def test_withdrawn_expired_and_other_purpose_look_the_same_too(client, db, vh):
    give(db, ap(2), withdrawn=clock.now() - timedelta(hours=1))
    give(db, ap(5), purposes=("SCHOLARSHIP",))
    a, b = refused(client, vh, ap(2)), refused(client, vh, ap(5))
    assert {k: v for k, v in a.items() if k != "id"} == {k: v for k, v in b.items() if k != "id"}


def test_admin_and_owning_institution_see_the_precise_reason(client, db, login, vh):
    refused(client, vh, ap(2))
    for who in ("admin@demo.test", "kaveri.admin@demo.test"):
        items = client.get(V, headers=login(who)).json()["items"]
        assert [i["refusal_reason"] for i in items] == ["NO_CONSENT"]


def test_repeated_refusals_are_rate_limited(client, vh):
    from app.core.config import settings
    old = settings.verify_max_refusals
    settings.verify_max_refusals = 3
    try:
        for _ in range(3):
            refused(client, vh, "999999999999")
        assert ask(client, vh, "999999999999").status_code == 429
    finally:
        settings.verify_max_refusals = old


# --- the public check --------------------------------------------------------------------

@pytest.fixture
def token(client, vh):
    return ask(client, vh, ap(1)).json()["token"]


def check(client, token):
    return client.get(f"/api/v1/verify/{token}")


@pytest.mark.parametrize("part", [0, 1, 2])
def test_token_altered_by_one_character_is_tampered_and_leaks_nothing(client, token, part):
    r = check(client, flip(token, part))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "TAMPERED"
    assert body["fields"] is None and body["issuer"] is None and body["purpose"] is None
    assert "Aarav" not in r.text


def test_garbage_is_tampered(client):
    for t in ("abc", "a.b.c", "....", "x" * 5000):
        assert check(client, t).json()["status"] == "TAMPERED"


def test_expired_token(client, token):
    clock.set_offset(8 * 86400)
    try:
        body = check(client, token).json()
    finally:
        clock.set_offset(0)
    assert body["status"] == "EXPIRED" and body["fields"] is None
    assert body["purpose"] == "EMPLOYMENT"


def test_token_expiry_boundary(client, token):
    exp = signing.decode_unverified(token)["exp"]
    from datetime import UTC, datetime
    at = lambda sec: datetime.fromtimestamp(sec, UTC)  # noqa: E731
    base = clock.now()
    clock.set_offset((at(exp) - base).total_seconds() - 5)
    try:
        assert check(client, token).json()["status"] == "GENUINE"
        clock.set_offset((at(exp) - base).total_seconds() + 5)
        assert check(client, token).json()["status"] == "EXPIRED"
    finally:
        clock.set_offset(0)


def test_revoked_token(client, db, login, vh, token):
    vid = db.scalars(select(VerificationRequest)).one().id
    assert client.post(f"{V}/{vid}/revoke", headers=vh).status_code == 200
    body = check(client, token).json()
    assert body["status"] == "REVOKED" and body["fields"] is None
    assert "VERIFICATION.REVOKED" in actions(db)
    assert client.post(f"{V}/{vid}/revoke", headers=vh).status_code == 409


def test_alg_none_is_rejected(client, token):
    head, payload, _ = token.split(".")
    h = b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    assert check(client, f"{h}.{payload}.").json()["status"] == "TAMPERED"
    assert check(client, f"{h}.{payload}").json()["status"] == "TAMPERED"


def test_hs256_with_the_public_key_as_secret_is_rejected(client, token):
    _, payload, _ = token.split(".")
    h = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    for secret in (signing.public_pem().encode(), signing.public_raw_bytes()):
        sig = b64(hmac.new(secret, f"{h}.{payload}".encode(), hashlib.sha256).digest())
        assert check(client, f"{h}.{payload}.{sig}").json()["status"] == "TAMPERED"


def test_token_signed_with_another_key_is_tampered(client, token):
    import jwt
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    claims = signing.decode_unverified(token)
    forged = jwt.encode(claims, Ed25519PrivateKey.generate(), algorithm="EdDSA")
    assert check(client, forged).json()["status"] == "TAMPERED"


def test_validly_signed_token_with_unknown_jti_is_tampered(client, db, token):
    row = db.scalars(select(VerificationRequest)).one()
    row.token_jti = "00000000-0000-0000-0000-000000000000"
    db.commit()
    assert check(client, token).json()["status"] == "TAMPERED"


def test_access_token_is_not_a_verification_token(client, vh):
    assert check(client, vh["Authorization"].split()[1]).json()["status"] == "TAMPERED"


def test_every_check_is_audited_without_an_actor(client, db, token):
    check(client, token)
    check(client, flip(token, 1))
    rows = db.scalars(select(AuditLog).where(AuditLog.action == "VERIFICATION.CHECKED")).all()
    assert [r.actor_id for r in rows] == [None, None]
    assert [r.after["status"] for r in rows] == ["GENUINE", "TAMPERED"]
    assert audit.verify(db)["ok"]


def test_public_key_is_public_and_matches(client, token):
    r = client.get("/api/v1/verify/public-key")
    assert r.status_code == 200
    body = r.json()
    assert "BEGIN PUBLIC KEY" in body["pem"]
    assert body["jwk"]["kty"] == "OKP" and body["jwk"]["crv"] == "Ed25519" and "d" not in body["jwk"]
    import jwt
    jwt.decode(token, body["pem"], algorithms=["EdDSA"], options={"verify_exp": False})


def test_private_key_file_is_not_tracked():
    from pathlib import Path
    ignore = (Path(__file__).resolve().parents[2] / ".gitignore").read_text()
    assert "keys/" in ignore


# --- revoke scope, history scope ---------------------------------------------------------

def test_revoke_scope(client, db, login, vh, world):
    tok_ids = []
    for _ in range(4):
        ask(client, vh, ap(1))
    tok_ids = [r.id for r in db.scalars(select(VerificationRequest))]
    other_u, _v = second_verifier(db)
    assert client.post(f"{V}/{tok_ids[0]}/revoke",
                       headers=login(other_u.email)).status_code == 403  # another verifier
    assert client.post(f"{V}/{tok_ids[0]}/revoke", headers=login("officer.south@demo.test")
                       ).status_code == 403
    assert client.post(f"{V}/{tok_ids[0]}/revoke", headers=login("admin@demo.test")
                       ).status_code == 200
    assert client.post(f"{V}/{tok_ids[1]}/revoke", headers=login("kaveri.staff@demo.test")
                       ).status_code == 200  # the student's institution
    assert "ACCESS.REFUSED" in actions(db)
    assert client.post(f"{V}/nope/revoke", headers=vh).status_code == 404


def test_institution_of_another_student_cannot_revoke(client, db, login, vh, world):
    give(db, ap(5))
    r = ask(client, vh, ap(5))
    vid = r.json()["id"]
    assert client.post(f"{V}/{vid}/revoke", headers=login("kaveri.admin@demo.test")
                       ).status_code == 403


def test_refused_request_cannot_be_revoked(client, vh):
    vid = ask(client, vh, ap(2)).json()["id"]
    assert client.post(f"{V}/{vid}/revoke", headers=vh).status_code == 409


def test_history_is_scoped(client, db, login, vh, world):
    give(db, ap(5))
    ask(client, vh, ap(1))
    ask(client, vh, ap(5))
    other_u, _ = second_verifier(db)
    oh = login(other_u.email)
    assert client.get(V, headers=oh).json()["items"] == []
    mine = client.get(V, headers=vh).json()["items"]
    assert len(mine) == 2
    # another verifier gets 404, not 403, for a request that is not theirs
    assert client.get(f"{V}/{mine[0]['id']}", headers=oh).status_code == 404
    kav = client.get(V, headers=login("kaveri.admin@demo.test")).json()["items"]
    assert len(kav) == 1 and kav[0]["apaar_id"] == ap(1)  # their own student: unmasked
    assert len(client.get(V, headers=login("admin@demo.test")).json()["items"]) == 2
    south = client.get(V, headers=login("officer.south@demo.test")).json()["items"]
    assert len(south) == 1  # Northfield is in the North region
    other_inst = [i for i in mine if i["id"] not in {k["id"] for k in kav}][0]["id"]
    assert client.get(f"{V}/{other_inst}", headers=login("kaveri.admin@demo.test")
                      ).status_code == 403
