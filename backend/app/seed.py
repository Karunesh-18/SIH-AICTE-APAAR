"""Synthetic demo data: fictional institutions, students and registry. Run: python -m app.seed [--reset].

Every APAAR ID here starts with 9999 so it cannot be mistaken for a real one. Names are invented.
The ten demonstration cases of the idea document (section 29) are seeded as raw records; the
flags themselves are raised by the checks (Phase 3), not written here.
"""
import argparse
import csv
import hashlib
import io
import random
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.base import Base
from app.models.consent import Consent, PurposePolicy, Verifier
from app.models.org import Institution, Programme, Region
from app.models.rules import Rule, RuleVersion
from app.models.student import (
    FlagEvent,
    FlagRecord,
    RegistryEntry,
    StudentRecord,
    Upload,
    ValidationFlag,
)
from app.models.user import User, UserRegion
from app.models.windows import SubmissionWindow

DEMO_PASSWORD = "Demo@1234"
CYCLE = 2026

FIRST = ["Aarav", "Diya", "Kabir", "Meera", "Rohan", "Isha", "Arjun", "Nisha", "Vihaan", "Tara",
         "Ishaan", "Anaya", "Dev", "Kavya", "Reyansh", "Myra", "Sahil", "Riya", "Neel", "Pooja"]
LAST = ["Nair", "Menon", "Iyer", "Rao", "Kulkarni", "Joshi", "Banerjee", "Sen", "Gill", "Bose",
        "Patel", "Shah", "Reddy", "Pillai", "Das", "Mishra", "Chopra", "Verma", "Naidu", "Khan"]
DEVANAGARI = ["अनिका शर्मा", "रोहित वर्मा", "सीमा यादव", "मोहन लाल"]  # exercises UTF-8 end to end
CATEGORIES = ["OPEN", "OBC", "SC", "ST", "EWS"]

REGIONS = [("SOUT", "South"), ("NORT", "North"), ("EAST", "East"), ("WEST", "West")]

# name, type, region code, programme, level, intake, supernumerary, students
INSTITUTIONS = [
    ("Kaveri Valley College", "MANAGEMENT", "SOUT", "MBA", "PG", 120, 6, 132),
    ("Malabar Pharmacy College", "PHARMACY", "SOUT", "B.Pharm", "UG", 40, 2, 40),
    ("Northfield Institute", "ENGINEERING", "NORT", "B.Tech Computer Science", "UG", 60, 3, 58),
    ("Sahyadri Engineering College", "ENGINEERING", "WEST", "B.Tech Mechanical", "UG", 60, 3, 30),
    ("Gomti Management Institute", "MANAGEMENT", "NORT", "PGDM", "PG", 60, 0, 25),
    ("Narmada School of Management", "MANAGEMENT", "WEST", "MBA", "PG", 60, 0, 30),
    ("Brahmaputra Technical Institute", "ENGINEERING", "EAST", "B.Tech Civil", "UG", 90, 5, 70),
    ("Cauvery Polytechnic", "OTHER", "SOUT", "Diploma Electronics", "DIPLOMA", 60, 0, 48),
    ("Ganga Institute of Pharmacy", "PHARMACY", "EAST", "B.Pharm", "UG", 60, 3, 52),
    ("Himalaya College of Engineering", "ENGINEERING", "NORT", "B.Tech Electrical", "UG", 120, 6, 96),
    ("Konkan School of Business", "MANAGEMENT", "WEST", "MBA", "PG", 90, 0, 71),
    ("Sundarbans Technical Campus", "ENGINEERING", "EAST", "B.Tech IT", "UG", 60, 0, 55),
    ("Tungabhadra Institute", "ENGINEERING", "SOUT", "B.Tech ECE", "UG", 120, 6, 101),
    ("Vindhya Management College", "MANAGEMENT", "NORT", "PGDM", "PG", 60, 0, 44),
    ("Yamuna Pharmacy Institute", "PHARMACY", "NORT", "D.Pharm", "DIPLOMA", 60, 0, 37),
]

RULES = [
    ("R01", "upload", "ID missing", {}, "APAAR ID is missing; the record is held as pending APAAR."),
    ("R02", "upload", "ID format", {"digits": 12, "checksum": "none"},
     "APAAR ID is not {digits} digits."),
    ("R03", "upload", "ID not in registry or details differ", {"name_threshold": 0.8},
     "APAAR ID was not found in the registry, or the name or date of birth differs."),
    ("R04", "upload", "Duplicate ID inside one file", {},
     "The same APAAR ID appears more than once in this file."),
    ("R05", "cross", "Same ID active at two institutions", {},
     "The same APAAR ID is active at two institutions in one cycle."),
    ("R06", "upload", "Enrolment above intake plus supernumerary", {},
     "Enrolment is above approved intake plus supernumerary seats."),
    ("R07", "upload", "Contradicting or missing mandatory fields", {},
     "A mandatory field is missing or contradicts another."),
    ("R08", "cross", "Near-duplicate name and date of birth", {"threshold": 0.85},
     "Two records have a very similar name and the same date of birth."),
    ("R09", "scheduled", "Submission late or missing", {},
     "The submission window closed without a submission."),
    ("R10", "scheduled", "Enrolment jump against previous cycle", {"jump_pct": 25},
     "Enrolment rose by more than {jump_pct} percent against the previous cycle."),
    ("R11", "scheduled", "Share pending APAAR too high", {"pending_pct": 20},
     "More than {pending_pct} percent of records are pending APAAR."),
    ("R12", "scheduled", "Late bulk submission, unusual category mix",
     {"last_hours": 6, "bulk_rows": 50},
     "A bulk submission arrived in the last {last_hours} hours with an unusual category mix."),
]


class _Ids:
    """Hands out invented APAAR IDs (9999 + eight digits), dates of birth that never collide."""

    def __init__(self):
        self.n = 1000

    def next(self):
        self.n += 1
        return f"9999{self.n:08d}", date(2000, 1, 1) + timedelta(days=(self.n * 53) % 1800)


def _reset(db: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(delete(table))
    db.commit()


def seed(db: Session, reset: bool = False) -> None:
    if reset:
        _reset(db)
    elif db.scalar(select(func.count()).select_from(Institution)):
        raise RuntimeError("Database is not empty; use reset=True (--reset) to start over.")

    rng = random.Random(2026)
    ids = _Ids()
    regions = {}
    for code, name in REGIONS:
        regions[code] = Region(code=code, name=name)
        db.add(regions[code])
    db.flush()

    for code, scope, title, params, msg in RULES:
        db.add(Rule(code=code, scope=scope, title=title))
    db.flush()
    for code, _scope, _title, params, msg in RULES:
        db.add(RuleVersion(rule_code=code, version_no=1, enabled=True, params=params,
                           message_en=msg, is_active=True, note="Initial version"))

    registry: dict[str, RegistryEntry] = {}

    def register(apaar, name, dob):
        if apaar not in registry:
            registry[apaar] = RegistryEntry(apaar_id=apaar, name=name, dob=dob)
            db.add(registry[apaar])

    insts: dict[str, Institution] = {}
    progs: dict[str, Programme] = {}
    for i, (name, typ, reg, pname, level, intake, seats, _n) in enumerate(INSTITUTIONS, 1):
        inst = Institution(aicte_id=f"FX-{1000 + i}", name=name, type=typ,
                           region_id=regions[reg].id,
                           contact_email=f"office{i}@demo.test")
        db.add(inst)
        db.flush()
        insts[name] = inst
        progs[name] = Programme(institution_id=inst.id, name=pname, level=level, cycle_year=CYCLE,
                                duration_years=3 if level == "DIPLOMA" else 2 if level == "PG" else 4,
                                approved_intake=intake, supernumerary_seats=seats)
        db.add(progs[name])
    db.flush()

    pw = hash_password(DEMO_PASSWORD)
    kaveri = insts["Kaveri Valley College"]
    demo_users = [
        ("admin@demo.test", "Demo AICTE Admin", "AICTE_ADMIN", None),
        ("officer@demo.test", "Demo AICTE Officer", "AICTE_OFFICER", None),
        ("inst-admin@demo.test", "Demo Institution Admin", "INSTITUTION_ADMIN", kaveri),
        ("staff@demo.test", "Demo Institution Staff", "INSTITUTION_STAFF", kaveri),
        ("verifier@demo.test", "Demo Verifier", "VERIFIER", None),
    ]
    made = {}
    for email, full, role, inst in demo_users:
        made[email] = User(email=email, full_name=full, role=role, password_hash=pw,
                           institution_id=inst.id if inst else None)
        db.add(made[email])
    db.flush()
    for code in ("SOUT", "NORT"):  # the demo officer covers the two regions with the demo cases
        db.add(UserRegion(user_id=made["officer@demo.test"].id, region_id=regions[code].id))

    def student(inst_name, n_row, *, apaar="auto", name=None, dob=None, adm=None, cat=None,
                status=None, **kw):
        prog = progs[inst_name]
        if apaar == "auto":
            apaar, auto_dob = ids.next()
            dob = dob or auto_dob
        else:
            dob = dob or date(2000, 1, 1) + timedelta(days=rng.randrange(1800))
        name = name or (f"{rng.choice(FIRST)} {rng.choice(LAST)}" if rng.random() > 0.03
                        else rng.choice(DEVANAGARI))
        if apaar and len(apaar) == 12:
            register(apaar, name, dob)
        return StudentRecord(
            apaar_id=apaar, name=name, dob=dob, programme_id=prog.id, cycle_year=CYCLE,
            year_of_study=1, admission_date=adm or date(2026, 7, 1) + timedelta(days=n_row // 3),
            admission_category=cat or rng.choice(CATEGORIES),
            status="pending_apaar" if apaar is None else (status or "submitted"),
            row_number=n_row, **kw)

    def upload(inst_name, rows):
        inst, prog = insts[inst_name], progs[inst_name]
        up = Upload(institution_id=inst.id, cycle_year=CYCLE, source="FILE", format="csv",
                    file_hash=hashlib.sha256(f"seed:{inst_name}".encode()).hexdigest(),
                    row_count=len(rows), status="RECEIVED",  # checks run in Phase 3
                    uploaded_by=made["staff@demo.test"].id if inst is kaveri else None)
        db.add(up)
        db.flush()
        for r in rows:
            r.upload_id = up.id
            assert r.programme_id == prog.id
        db.add_all(rows)

    # Case 2: Kaveri Valley, 132 rows against an allowed 126, a duplicate ID, a future-dated row.
    k_rows = []
    for n in range(1, 133):
        k_rows.append(student("Kaveri Valley College", n, apaar=f"9999{n:08d}"))
    k_dup = k_rows[96]  # row 97 repeats row 41's student with a different admission date
    first = k_rows[40]
    k_dup.apaar_id, k_dup.name, k_dup.dob = first.apaar_id, first.name, first.dob
    k_dup.admission_date = first.admission_date + timedelta(days=20)
    k_dup.is_current = False  # held: the database allows one current record per student (ADR-012)
    k_rows[59].admission_date = date(2027, 7, 12)  # row 60: typed the wrong year
    for r in k_rows:
        register(r.apaar_id, r.name, r.dob)
    upload("Kaveri Valley College", k_rows)

    # Case 1: Malabar, 40 of 40, nothing to flag.
    upload("Malabar Pharmacy College",
           [student("Malabar Pharmacy College", n) for n in range(1, 41)])

    # Case 4: Northfield, 58 of 60, one student also listed by Kaveri (a mid-year transfer).
    nf = [student("Northfield Institute", n) for n in range(1, 59)]
    moved = k_rows[11]
    nf[4].apaar_id, nf[4].name, nf[4].dob = moved.apaar_id, moved.name, moved.dob
    upload("Northfield Institute", nf)

    # Case 3: one 11-digit ID, one missing ID, the rest fine.
    sah = [student("Sahyadri Engineering College", n) for n in range(1, 31)]
    sah[6].apaar_id = sah[6].apaar_id[:11]
    sah[13].apaar_id, sah[13].status = None, "pending_apaar"
    upload("Sahyadri Engineering College", sah)

    # Case 5: students whose APAAR ID has not been issued yet.
    gom = [student("Gomti Management Institute", n) for n in range(1, 26)]
    for r in (gom[3], gom[17]):
        r.apaar_id, r.status = None, "pending_apaar"
    upload("Gomti Management Institute", gom)

    # Case 6: near duplicate, similar names and one date of birth with different IDs.
    nar = [student("Narmada School of Management", n) for n in range(1, 31)]
    nar[8].name, nar[9].name = "Priyanka Deshmukh", "Priyanka Deshmuk"
    nar[9].dob = nar[8].dob
    for r in (nar[8], nar[9]):
        register(r.apaar_id, r.name, r.dob)
    upload("Narmada School of Management", nar)

    for name, (*_rest, n_students) in {i[0]: i for i in INSTITUTIONS[6:]}.items():
        upload(name, [student(name, n) for n in range(1, n_students + 1)])

    seed_policies(db, commit=False)
    db.commit()


POLICIES = {
    "EMPLOYMENT": ["name", "programme", "status"],
    "HIGHER_EDUCATION": ["name", "programme", "level", "year_of_study"],
    "REGULATORY": ["name", "programme", "status", "admission_category"],
    "SCHOLARSHIP": ["name", "programme", "status", "admission_category"],
}


def seed_policies(db: Session, commit: bool = True) -> None:
    """Version 1 of the field allow-list for each consent purpose. AICTE can change them."""
    if db.scalar(select(func.count()).select_from(PurposePolicy)):
        raise RuntimeError("Purpose policies already exist.")
    for purpose, fields in POLICIES.items():
        db.add(PurposePolicy(purpose=purpose, allowed_fields=fields, version=1, is_active=True,
                             note="Initial version"))
    if commit:
        db.commit()


def seed_demo_flags(db: Session) -> None:
    """Run the real ingestion and validation pipeline over the seeded rows, so the demo database
    holds real flags and dashboards have something to show. The seeded raw rows are replaced by
    the pipeline's output (Kaveri first, so Northfield's shared student raises R05)."""
    from app.services import ingest

    if db.scalar(select(func.count()).select_from(ValidationFlag)):
        raise RuntimeError("Flags already exist; run on a freshly seeded database.")
    files = []
    for inst in db.scalars(select(Institution)):
        recs = db.scalars(select(StudentRecord).join(Upload, StudentRecord.upload_id == Upload.id)
                          .where(Upload.institution_id == inst.id)
                          .order_by(StudentRecord.row_number)).all()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["apaar_id", "name", "dob", "admission_date", "admission_category"])
        for r in recs:
            w.writerow([r.apaar_id or "", r.name, r.dob.isoformat(), r.admission_date.isoformat(),
                        r.admission_category])
        files.append((inst, buf.getvalue().encode("utf-8")))
    files.sort(key=lambda f: f[0].name != "Kaveri Valley College")
    for model in (FlagEvent, FlagRecord, ValidationFlag, StudentRecord, Upload):
        db.execute(delete(model))
    db.commit()
    for inst, data in files:
        ingest.ingest(db, actor=None, institution_id=inst.id, cycle_year=CYCLE, data=data)


PREVIOUS_CYCLE = {"Kaveri Valley College": 80, "Malabar Pharmacy College": 38,
                  "Northfield Institute": 56}  # 2025 enrolment, so R10 has something to compare
NEVER_SUBMIT = ("Cauvery Polytechnic", "Yamuna Pharmacy Institute")


def seed_demo_windows(db: Session) -> None:
    """A 2026 submission window (closes in 20 days on the demo clock), an older cycle for R10, and
    two institutions that have not submitted (their seeded uploads, records and flags are removed),
    so advancing the clock shows reminders, the late list and R09. Demo data only."""
    from app.core import clock
    from app.domain.ladder import DEFAULT_LADDER

    if db.scalar(select(func.count()).select_from(SubmissionWindow)):
        raise RuntimeError("A submission window already exists; run on a freshly seeded database.")
    by_name = {i.name: i for i in db.scalars(select(Institution))}
    for name in NEVER_SUBMIT:
        inst_id = by_name[name].id
        ups = select(Upload.id).where(Upload.institution_id == inst_id)
        flags = select(ValidationFlag.id).where(ValidationFlag.institution_id == inst_id)
        db.execute(delete(FlagEvent).where(FlagEvent.flag_id.in_(flags)))
        db.execute(delete(FlagRecord).where(FlagRecord.flag_id.in_(flags)))
        db.execute(delete(ValidationFlag).where(ValidationFlag.institution_id == inst_id))
        db.execute(delete(StudentRecord).where(StudentRecord.upload_id.in_(ups)))
        db.execute(delete(Upload).where(Upload.institution_id == inst_id))
    n = 0
    for name, count in PREVIOUS_CYCLE.items():
        cur = db.scalars(select(Programme).where(
            Programme.institution_id == by_name[name].id, Programme.cycle_year == CYCLE)).one()
        old = Programme(institution_id=cur.institution_id, name=cur.name, level=cur.level,
                        cycle_year=CYCLE - 1, duration_years=cur.duration_years,
                        approved_intake=cur.approved_intake,
                        supernumerary_seats=cur.supernumerary_seats)
        db.add(old)
        db.flush()
        for _ in range(count):
            n += 1
            db.add(StudentRecord(apaar_id=f"9999{70000000 + n:08d}", name=f"Earlier cohort {n}",
                                 dob=date(2000, 1, 1), programme_id=old.id, cycle_year=CYCLE - 1,
                                 admission_date=date(2025, 7, 1), admission_category="OPEN",
                                 status="valid", row_number=n))
    now = clock.now()
    db.add(SubmissionWindow(cycle_year=CYCLE, opens_at=now - timedelta(days=30),
                            closes_at=now + timedelta(days=20), ladder=DEFAULT_LADDER))
    db.commit()


def seed_demo_verification(db: Session) -> None:
    """An invented employer (the verifier@demo.test user, approved), one organisation waiting for
    approval, and consents for four Kaveri students: valid for EMPLOYMENT, expired, withdrawn and
    for SCHOLARSHIP only. The fifth student has none. Demo data only."""
    from app.core import clock

    if db.scalar(select(func.count()).select_from(Verifier)):
        raise RuntimeError("Verifiers already exist; run on a freshly seeded database.")
    kaveri = db.scalars(select(Institution).where(Institution.name == "Kaveri Valley College")).one()
    ids = db.scalars(
        select(StudentRecord.apaar_id).join(Programme, Programme.id == StudentRecord.programme_id)
        .where(Programme.institution_id == kaveri.id, StudentRecord.is_current,
               StudentRecord.apaar_id.is_not(None), StudentRecord.status != "withdrawn")
        .order_by(StudentRecord.row_number).limit(5)).all()
    now = clock.now()
    users = {u.email: u for u in db.scalars(select(User))}
    db.add(Verifier(org_name="Meridian Talent Services (fictional)", org_type="EMPLOYER",
                    contact="Hiring desk, hr@meridian-talent.test",
                    requested_purposes=["EMPLOYMENT", "HIGHER_EDUCATION"], status="APPROVED",
                    decided_by=users["admin@demo.test"].id, decision_note="Registration checked",
                    user_id=users["verifier@demo.test"].id))
    pending = User(email="pending.verifier@demo.test", full_name="Pending Verifier",
                   role="VERIFIER", password_hash=hash_password(DEMO_PASSWORD), is_active=False)
    db.add(pending)
    db.flush()
    db.add(Verifier(org_name="Kestrel Scholarship Trust (fictional)", org_type="OTHER",
                    contact="Trustee office, office@kestrel-trust.test",
                    requested_purposes=["SCHOLARSHIP"], status="PENDING", user_id=pending.id))
    basic = ["name", "programme", "status"]

    def consent(apaar, purposes, given_days_ago, valid_days, withdrawn=False):
        db.add(Consent(apaar_id=apaar, purposes=purposes, fields=basic, source="AT_ADMISSION",
                       given_at=now - timedelta(days=given_days_ago),
                       expires_at=now + timedelta(days=valid_days),
                       withdrawn_at=now - timedelta(days=1) if withdrawn else None,
                       recorded_by=users["inst-admin@demo.test"].id))

    consent(ids[0], ["EMPLOYMENT"], 10, 355)
    consent(ids[1], ["EMPLOYMENT"], 400, -35)
    consent(ids[2], ["EMPLOYMENT"], 10, 355, withdrawn=True)
    consent(ids[3], ["SCHOLARSHIP"], 10, 355)
    db.commit()


if __name__ == "__main__":
    from app.db.session import SessionLocal

    ap = argparse.ArgumentParser(description="Seed synthetic demo data")
    ap.add_argument("--reset", action="store_true", help="delete everything first")
    ap.add_argument("--with-flags", action="store_true",
                    help="then run the checks over the seeded uploads so real flags exist")
    ap.add_argument("--with-windows", action="store_true",
                    help="then add a submission window, an older cycle and two non-submitters "
                         "(needs --with-flags)")
    ap.add_argument("--with-verification", action="store_true",
                    help="then add an approved and a pending verifier and sample consents")
    args = ap.parse_args()
    with SessionLocal() as session:
        seed(session, reset=args.reset)
        if args.with_flags:
            seed_demo_flags(session)
        if args.with_windows:
            seed_demo_windows(session)
        if args.with_verification:
            seed_demo_verification(session)
    print("Seeded. Demo users: *@demo.test, password", DEMO_PASSWORD)
