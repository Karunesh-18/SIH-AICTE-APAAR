"""Certificate record: a signed CERTIFICATE token for one student record, checked publicly."""
import pytest
from sqlalchemy import select

from app.core import clock
from app.core.security import hash_password
from app.models.audit import AuditLog
from app.models.certificate import CertificateToken
from app.models.student import StudentRecord
from app.models.user import User
from app.services import signing
from tests.phase6_helpers import scene

PRINTED = {"institution", "name", "apaar_id", "student_id", "programme", "year_of_study"}


@pytest.fixture
def rec(db, world):
    scene(db, world)
    return db.scalars(select(StudentRecord).where(StudentRecord.name == "Aarav Nair")).one()


def mint(client, headers, rid):
    return client.post(f"/api/v1/records/{rid}/certificate", headers=headers)


@pytest.mark.parametrize("who", ["kaveri.admin@demo.test", "kaveri.staff@demo.test",
                                 "admin@demo.test", "officer.south@demo.test"])
def test_allowed_roles_mint_and_token_checks_genuine(client, login, rec, who):
    r = mint(client, login(who), rec.id)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["fields"]) == PRINTED
    assert body["fields"]["institution"] == "Kaveri Valley College"
    assert body["fields"]["student_id"] == rec.id
    assert body["qr_url"].endswith("/verify/" + body["token"])
    c = client.get(f"/api/v1/verify/{body['token']}").json()
    assert c["status"] == "GENUINE" and c["purpose"] == "CERTIFICATE"
    assert set(c["fields"]) == PRINTED


def test_token_claims_carry_only_printed_fields(client, login, rec):
    tok = mint(client, login("kaveri.admin@demo.test"), rec.id).json()["token"]
    claims = signing.decode_unverified(tok)
    assert claims["purpose"] == "CERTIFICATE" and set(claims["fields"]) == PRINTED
    assert "dob" not in str(claims)


def test_verifier_role_denied(client, login, rec):
    assert mint(client, login("verifier@demo.test"), rec.id).status_code == 403


def test_cross_institution_403_and_audited(client, db, login, rec, world):
    db.add(User(email="nf.admin@demo.test", password_hash=hash_password("Demo@1234"),
                full_name="nf", role="INSTITUTION_ADMIN", institution_id=world["northfield"].id))
    db.commit()
    assert mint(client, login("nf.admin@demo.test"), rec.id).status_code == 403
    acts = [a.action for a in db.scalars(select(AuditLog))]
    assert "ACCESS.REFUSED" in acts and "CERTIFICATE.ISSUED" not in acts


def test_unknown_record_404_and_anonymous_refused(client, login, rec):
    assert mint(client, login("kaveri.admin@demo.test"), "nope").status_code == 404
    assert client.post(f"/api/v1/records/{rec.id}/certificate").status_code in (401, 403)


def test_mint_writes_audit_row(client, db, login, rec):
    mint(client, login("kaveri.admin@demo.test"), rec.id)
    row = db.scalars(select(AuditLog).where(AuditLog.action == "CERTIFICATE.ISSUED")).one()
    assert row.entity_id == rec.id


def test_tampered_token_rejected(client, login, rec):
    tok = mint(client, login("kaveri.admin@demo.test"), rec.id).json()["token"]
    h, p, s = tok.split(".")
    bad = ".".join([h, p[:-2] + ("AA" if p[-2:] != "AA" else "BB"), s])
    c = client.get(f"/api/v1/verify/{bad}").json()
    assert c["status"] == "TAMPERED" and c["fields"] is None


def test_expiry_follows_setting(client, login, rec, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "certificate_token_days", 10)
    b = mint(client, login("kaveri.admin@demo.test"), rec.id).json()
    claims = signing.decode_unverified(b["token"])
    assert 9 * 86400 < claims["exp"] - claims["iat"] <= 10 * 86400


def test_revoked_certificate_not_genuine(client, db, login, rec):
    tok = mint(client, login("kaveri.admin@demo.test"), rec.id).json()["token"]
    db.scalars(select(CertificateToken)).one().revoked_at = clock.now()
    db.commit()
    c = client.get(f"/api/v1/verify/{tok}").json()
    assert c["status"] == "REVOKED" and c["fields"] is None


def test_record_without_apaar_id_409(client, db, login, rec):
    rec.apaar_id = None
    db.commit()
    assert mint(client, login("kaveri.admin@demo.test"), rec.id).status_code == 409
