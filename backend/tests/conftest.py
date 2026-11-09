import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers all tables)
from app.core.config import settings
from app.db.base import Base

settings.bcrypt_rounds = 4  # tests only: fast hashing
PASSWORD = "Demo@1234"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def world(db):
    """Two regions, three institutions, one user per role. Test data only."""
    from app.core.security import hash_password
    from app.models.org import Institution, Region
    from app.models.user import User, UserRegion

    south = Region(code="SOUT", name="South")
    north = Region(code="NORT", name="North")
    db.add_all([south, north])
    db.flush()
    kaveri = Institution(aicte_id="FX-1001", name="Kaveri Valley College",
                         type="MANAGEMENT", region_id=south.id)
    malabar = Institution(aicte_id="FX-1002", name="Malabar Pharmacy College",
                          type="PHARMACY", region_id=south.id)
    northfield = Institution(aicte_id="FX-1003", name="Northfield Institute",
                             type="ENGINEERING", region_id=north.id)
    db.add_all([kaveri, malabar, northfield])
    db.flush()

    def user(email, role, inst=None):
        u = User(email=email, password_hash=hash_password(PASSWORD), full_name=email,
                 role=role, institution_id=inst.id if inst else None)
        db.add(u)
        db.flush()
        return u

    users = {
        "admin": user("admin@demo.test", "AICTE_ADMIN"),
        "officer_south": user("officer.south@demo.test", "AICTE_OFFICER"),
        "inst_admin": user("kaveri.admin@demo.test", "INSTITUTION_ADMIN", kaveri),
        "inst_staff": user("kaveri.staff@demo.test", "INSTITUTION_STAFF", kaveri),
        "verifier": user("verifier@demo.test", "VERIFIER"),
    }
    db.add(UserRegion(user_id=users["officer_south"].id, region_id=south.id))
    db.commit()
    return {"users": users, "kaveri": kaveri, "malabar": malabar,
            "northfield": northfield, "south": south, "north": north}


@pytest.fixture
def client(db, world):
    from app.db.session import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.fixture
def login(client):
    def _login(email):
        r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _login
