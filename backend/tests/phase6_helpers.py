"""Shared scene for the Phase 6 tests. Synthetic data only."""
from datetime import date, timedelta

from app.core import clock
from app.core.security import hash_password
from app.models.consent import Consent, Verifier
from app.models.student import StudentRecord
from app.models.user import User
from app.seed import seed_policies
from tests.conftest import PASSWORD
from tests.ingest_helpers import ap, programme

V = "/api/v1/verifications"


def scene(db, world):
    """Kaveri holds ap(1) and ap(2); Northfield holds ap(5). The demo verifier is approved.
    ap(1) has a valid EMPLOYMENT consent for name, programme and status."""
    seed_policies(db)
    kp = programme(db, world["kaveri"])
    npg = programme(db, world["northfield"], name="B.Tech")
    for n, prog, name in ((1, kp, "Aarav Nair"), (2, kp, "Diya Menon"), (5, npg, "Kabir Gill")):
        db.add(StudentRecord(apaar_id=ap(n), name=name, dob=date(2001, 3, 4), programme_id=prog.id,
                             cycle_year=2026, admission_date=date(2026, 7, 1),
                             admission_category="OPEN", status="valid"))
    verifier = Verifier(org_name="Fictional Employer Pvt Ltd", org_type="EMPLOYER",
                        contact="hr@fictional-employer.test", requested_purposes=["EMPLOYMENT"],
                        status="APPROVED", user_id=world["users"]["verifier"].id)
    db.add(verifier)
    db.commit()
    give(db, ap(1))
    return verifier


def give(db, apaar, purposes=("EMPLOYMENT",), fields=("name", "programme", "status"),
         days=30, withdrawn=None):
    now = clock.now()
    c = Consent(apaar_id=apaar, purposes=list(purposes), fields=list(fields), source="TEST",
                given_at=now - timedelta(days=1), expires_at=now + timedelta(days=days),
                withdrawn_at=withdrawn)
    db.add(c)
    db.commit()
    return c


def second_verifier(db, email="other.verifier@demo.test"):
    u = User(email=email, password_hash=hash_password(PASSWORD), full_name="Other", role="VERIFIER")
    db.add(u)
    db.flush()
    v = Verifier(org_name="Other Org", org_type="OTHER", contact="x@y.test",
                 requested_purposes=["EMPLOYMENT"], status="APPROVED", user_id=u.id)
    db.add(v)
    db.commit()
    return u, v


def ask(client, headers, apaar, purpose="EMPLOYMENT", fields=("name", "programme", "status")):
    return client.post(V, headers=headers,
                       json={"apaar_id": apaar, "purpose": purpose, "fields": list(fields)})
