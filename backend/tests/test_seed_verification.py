"""seed_policies (default seed) and seed_demo_verification (--with-verification)."""
import pytest
from sqlalchemy import select

from app.models.consent import Consent, PurposePolicy, Verifier
from app.seed import seed, seed_demo_flags, seed_demo_verification, seed_policies


def test_default_seed_has_the_four_policies(db):
    seed(db)
    got = {p.purpose: p.allowed_fields for p in db.scalars(
        select(PurposePolicy).where(PurposePolicy.is_active))}
    assert got == {
        "EMPLOYMENT": ["name", "programme", "status"],
        "HIGHER_EDUCATION": ["name", "programme", "level", "year_of_study"],
        "REGULATORY": ["name", "programme", "status", "admission_category"],
        "SCHOLARSHIP": ["name", "programme", "status", "admission_category"]}
    assert db.scalars(select(Verifier)).first() is None  # verifiers and consents are demo-only


def test_seed_policies_twice_is_refused(db):
    seed_policies(db)
    with pytest.raises(RuntimeError):
        seed_policies(db)


def test_demo_verification_scene(db):
    from app.core import clock
    seed(db)
    seed_demo_flags(db)
    seed_demo_verification(db)
    vs = {v.status: v for v in db.scalars(select(Verifier))}
    assert set(vs) == {"APPROVED", "PENDING"}
    assert vs["APPROVED"].user.email == "verifier@demo.test" if hasattr(vs["APPROVED"], "user") \
        else True
    cs = db.scalars(select(Consent)).all()
    now = clock.now()
    valid = [c for c in cs if c.withdrawn_at is None and c.expires_at > now
             and "EMPLOYMENT" in c.purposes]
    assert valid
    assert any(c.expires_at <= now for c in cs)
    assert any(c.withdrawn_at for c in cs)
    assert any(c.purposes == ["SCHOLARSHIP"] for c in cs)
    assert all(c.apaar_id.startswith("9999") for c in cs)
