"""The ten demonstration cases of the idea document (section 29), end to end.

The database is built by the real migrations and filled by the one-command demo seed
(`python -m app.seed --demo`). Every action and every assertion goes through the HTTP API with the
TestClient. Two things are set up outside HTTP, because the system has no endpoint for them:
the mock registry entry used in case 5 and the direct database edit that is case 9 by definition.

The cases build on one another (one demo database, used in order), so the tests share a
module-scoped environment and must run in file order.

How the document's "six rows, dismiss two" maps onto the platform: a flag is dismissed as a whole,
never row by row. Kaveri's 132 rows raise three flags (R06 intake cap on 6 rows, R04 duplicate ID
on 2 rows, R07 future admission year on 1 row). The officer opens the R06 flag, sees its six rows,
and dismisses the R04 flag (the two duplicate rows) with a note; R06 and R07 stay open.
"""
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, update
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core import clock
from app.models.audit import AuditLog
from app.models.student import RegistryEntry
from app.seed import DEMO_PASSWORD, main
from app.services import notify

BACKEND = Path(__file__).resolve().parents[1]
API = "/api/v1"
KAVERI, MALABAR, NORTHFIELD = ("Kaveri Valley College", "Malabar Pharmacy College",
                               "Northfield Institute")


class Mailbox:
    def __init__(self):
        self.sent = []

    def send(self, to, subject, body):
        self.sent.append((to, subject))


class Env:
    def __init__(self, client, db, mail):
        self.c, self.db, self.mail = client, db, mail
        self._tokens = {}
        self.inst = {i["name"]: i["id"] for i in self.get("admin", "/institutions")}

    def h(self, who):
        if who not in self._tokens:
            r = self.c.post(f"{API}/auth/login", json={"email": f"{who}@demo.test",
                                                       "password": DEMO_PASSWORD})
            assert r.status_code == 200, r.text
            self._tokens[who] = {"Authorization": f"Bearer {r.json()['access_token']}"}
        return self._tokens[who]

    def get(self, who, path, **kw):
        r = self.c.get(API + path, headers=self.h(who), **kw)
        assert r.status_code == 200, (path, r.text)
        return r.json()

    def post(self, who, path, body=None, status=200):
        r = self.c.post(API + path, headers=self.h(who), json=body)
        assert r.status_code == status, (path, r.text)
        return r.json()

    def dashboard_row(self, name):
        rows = self.get("admin", "/dashboards/aicte")["institutions"]
        return next(r for r in rows if r["name"] == name)

    def flags(self, who, **params):
        return self.get(who, "/flags", params={"limit": 200} | params)["items"]


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    from app.db.session import get_db, get_session_factory
    from app.main import create_app

    clock.set_offset(0)
    url = f"sqlite:///{tmp_path_factory.mktemp('e2e') / 'demo.db'}"
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")  # the real migrations, not create_all
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    factory = sessionmaker(engine, expire_on_commit=False)
    main(["--demo"], factory)  # reset + seed + flags + windows + verification
    db = factory()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_session_factory] = lambda: lambda: db
    mail, old = Mailbox(), notify.get_adapter()
    notify.set_adapter(mail)
    from app.core.config import settings
    from app.services import signing
    settings.bcrypt_rounds = 4
    try:
        yield Env(TestClient(app), db, mail)
    finally:
        notify.set_adapter(old)
        clock.set_offset(0)
        signing.reset()
        db.close()
        engine.dispose()


def rows_of(flag_items):
    return {r for f in flag_items for r in f["rows"]}


# ---- 1. a clean upload -------------------------------------------------------------------------

def test_case_01_malabar_clean_upload_is_all_valid_and_clear(env):
    up = next(u for u in env.get("admin", "/uploads?limit=200")["items"]
              if u["institution_id"] == env.inst[MALABAR])
    assert (up["status"], up["row_count"], up["accepted_count"], up["flagged_count"]) == (
        "DONE", 40, 40, 0)
    valid = env.get("admin", f"/institutions/{env.inst[MALABAR]}/records?status=valid&limit=200")
    # the list spans cycles (the 2025 cohort seeded for R10 is in it); this cycle has 40
    assert sum(r["cycle_year"] == 2026 for r in valid["items"]) == 40
    row = env.dashboard_row(MALABAR)
    assert (row["state"], row["enrolled"], row["allowed"], row["open_flags"]) == ("Clear", 40, 42, 0)


# ---- 2. excess intake --------------------------------------------------------------------------

def test_case_02_kaveri_excess_three_flags_eight_rows_officer_dismisses_the_duplicate(env):
    up = next(u for u in env.get("admin", "/uploads?limit=200")["items"]
              if u["institution_id"] == env.inst[KAVERI])
    detail = env.get("admin", f"/uploads/{up['id']}")
    assert up["row_count"] == 132
    assert sorted(f["rule_code"] for f in detail["flag_items"]) == ["R04", "R06", "R07"]
    assert len(rows_of(detail["flag_items"])) == 8
    assert env.dashboard_row(KAVERI)["state"] == "Excess"

    mine = {f["rule_code"]: f for f in env.flags("officer", institution=env.inst[KAVERI])}
    cap = env.get("officer", f"/flags/{mine['R06']['id']}")
    ev = cap["evidence"]
    assert (ev["allowed"], ev["actual"], ev["excess"]) == (126, 132, 6)
    assert "126" in cap["reason"] and "132" in cap["reason"]  # the numbers are in the sentence
    assert cap["record_count"] == 6 and len(cap["records"]) == 6
    opened = env.post("officer", f"/flags/{cap['id']}/review", {"note": "Checking the intake letter"})
    assert opened["state"] == "under_review"

    dup = env.post("officer", f"/flags/{mine['R04']['id']}/dismiss",
                   {"note": "Same student re-entered after a correction; no action needed"})
    assert dup["state"] == "dismissed"
    states = {f["rule_code"]: f["state"] for f in env.flags("officer", institution=env.inst[KAVERI])}
    assert states == {"R04": "dismissed", "R06": "under_review", "R07": "open"}


# ---- 3. bad IDs --------------------------------------------------------------------------------

def test_case_03_bad_ids_come_back_with_rule_and_row_and_nothing_else_is_held(env):
    sah = env.inst["Sahyadri Engineering College"]
    up = next(u for u in env.get("admin", "/uploads?limit=200") ["items"]
              if u["institution_id"] == sah)
    detail = env.get("admin", f"/uploads/{up['id']}")
    by_rule = {f["rule_code"]: f for f in detail["flag_items"]}
    assert set(by_rule) == {"R01", "R02"}
    assert by_rule["R02"]["rows"] == [7] and by_rule["R02"]["evidence"]["digits_found"] == 11
    assert by_rule["R01"]["rows"] == [14]
    assert "Row 7" in by_rule["R02"]["reason"] and "Row 14" in by_rule["R01"]["reason"]
    # the other 28 rows were stored and are valid; the upload was not held up
    assert (up["status"], up["accepted_count"], up["flagged_count"]) == ("DONE", 30, 2)
    valid = env.get("admin", f"/institutions/{sah}/records?status=valid&limit=200")["items"]
    assert len(valid) == 28


# ---- 4. the same student at two institutions ---------------------------------------------------

def test_case_04_both_institutions_hear_about_it_and_the_officer_resolves_after_withdrawal(env):
    nf = env.inst[NORTHFIELD]
    (r05,) = [f for f in env.flags("officer", rule="R05") if f["institution_id"] == nf]
    assert env.dashboard_row(NORTHFIELD)["state"] == "Alert"
    detail = env.get("officer", f"/flags/{r05['id']}")
    other = detail["evidence"]["elsewhere"][0]
    assert other["institution"] == KAVERI and detail["evidence"]["apaar_id"].startswith("XXXX")

    # Kaveri's side is told too (its users get the notification; Northfield has no demo users)
    inbox = env.get("inst-admin", "/notifications")
    assert any(n["subject"] == "Student listed elsewhere" for n in inbox)

    # a made-up phone call: Northfield's record is withdrawn, then the officer resolves the flag
    rec_id = detail["records"][0]["id"]
    env.post("admin", f"/records/{rec_id}/withdraw", {"reason": "Transferred to Kaveri Valley"})
    done = env.post("officer", f"/flags/{r05['id']}/resolve",
                    {"note": "Phone call: student confirmed at Kaveri; Northfield withdrawn"})
    assert done["state"] == "resolved"
    row = env.dashboard_row(NORTHFIELD)
    assert row["enrolled"] == 57 and row["state"] == "Clear"  # withdrawn records count nowhere
    actions = [a["action"] for a in env.get("admin", "/admin/audit?limit=500")["items"]]
    assert "RECORD.WITHDRAWN" in actions and "FLAG.RESOLVED" in actions


# ---- 5. pending APAAR --------------------------------------------------------------------------

def test_case_05_pending_record_has_its_own_figure_and_is_rechecked_when_the_id_arrives(env):
    gomti = env.inst["Gomti Management Institute"]
    dash = env.get("admin", f"/dashboards/institution?institution_id={gomti}")
    assert dash["records"]["pending_apaar"] == 2 and dash["records"]["accepted"] == 25
    pend_before = env.get("admin", "/reports/pending_apaar_share")
    row = next(r for r in pend_before["rows"] if r["institution"] == "Gomti Management Institute")
    assert (row["pending"], row["total"]) == (2, 25)

    todo = dash["todo"]["pending_apaar"][0]
    rec = env.get("admin", f"/records/{todo['record_id']}")  # a single-record view (audited)
    # the mock registry is an external system: give it this student so the new ID is known there
    new_id = "999955550001"
    env.db.add(RegistryEntry(apaar_id=new_id, name=rec["name"], dob=date.fromisoformat(rec["dob"])))
    env.db.commit()
    r = env.c.patch(f"{API}/records/{todo['record_id']}", headers=env.h("admin"),
                    json={"apaar_id": new_id})
    assert r.status_code == 200, r.text
    after = env.get("admin", f"/dashboards/institution?institution_id={gomti}")
    assert after["records"]["pending_apaar"] == 1
    new_rec = r.json()["record"]
    assert new_rec["status"] == "valid" and new_rec["apaar_id"] == new_id
    r01 = [f for f in env.flags("admin", rule="R01", institution=gomti)]
    assert sorted(f["state"] for f in r01) == ["open", "resolved"]  # closed by the system


# ---- 6. near duplicate -------------------------------------------------------------------------

def test_case_06_near_duplicate_suggests_a_link_with_the_score_and_the_officer_dismisses(env):
    nar = env.inst["Narmada School of Management"]
    # the officer's regions are changed through the new user-management endpoint
    officer = next(u for u in env.get("admin", "/admin/users")["items"]
                   if u["email"] == "officer@demo.test")
    r = env.c.patch(f"{API}/admin/users/{officer['id']}", headers=env.h("admin"),
                    json={"regions": ["SOUT", "NORT", "WEST"]})
    assert r.status_code == 200, r.text
    (r08,) = env.flags("officer", rule="R08", institution=nar)
    detail = env.get("officer", f"/flags/{r08['id']}")
    ev = detail["evidence"]
    assert ev["score"] >= ev["threshold"] == 0.85
    assert {ev["a"]["name"], ev["b"]["name"]} == {"Priyanka Deshmukh", "Priyanka Deshmuk"}
    assert ev["a"]["apaar_id"] != ev["b"]["apaar_id"] and detail["record_count"] == 2
    assert "score" in detail["reason"] and "threshold" in detail["reason"]
    done = env.post("officer", f"/flags/{r08['id']}/dismiss",
                    {"note": "Twins in the same batch; different students"})
    assert done["state"] == "dismissed"


# ---- 7. verification with consent --------------------------------------------------------------

def test_case_07_verification_with_consent_gives_three_fields_and_a_token_the_public_can_check(env):
    r = env.post("verifier", "/verifications", {
        "apaar_id": "999900000001", "purpose": "EMPLOYMENT",
        "fields": ["name", "programme", "status"]})
    assert r["outcome"] == "GRANTED" and set(r["fields"]) == {"name", "programme", "status"}
    assert r["token"] and r["qr_url"].endswith("/verify/" + r["token"])
    chk = env.c.get(f"{API}/verify/{r['token']}")  # public: no Authorization header
    assert chk.status_code == 200
    assert chk.json()["status"] == "GENUINE" and chk.json()["fields"] == r["fields"]
    assert any(s.startswith("Student record verified") for _, s in env.mail.sent)


# ---- 8. verification without consent and after withdrawal --------------------------------------

def test_case_08_no_consent_and_withdrawn_consent_are_refused_and_logged(env):
    ask = lambda apaar: env.post("verifier", "/verifications", {
        "apaar_id": apaar, "purpose": "EMPLOYMENT", "fields": ["name"]})
    no_consent, withdrawn = ask("999900000005"), ask("999900000003")
    for r in (no_consent, withdrawn):
        assert r["outcome"] == "REFUSED" and "token" not in r
        assert r["reason"] == "CONSENT_NOT_AVAILABLE"  # the verifier learns nothing more
    refused = [a for a in env.get("admin", "/admin/audit?limit=500")["items"]
               if a["action"] == "VERIFICATION.REFUSED"]
    assert sorted(a["after"]["reason"] for a in refused) == ["NO_CONSENT", "WITHDRAWN"]
    assert sorted(a["after"]["apaar_id"] for a in refused) == ["XXXX XXXX 0003", "XXXX XXXX 0005"]


# ---- 10. the clock -----------------------------------------------------------------------------
# (run before the tamper case so the audit chain is still intact when case 9 edits it)

def test_case_10_clock_past_the_window_close_gives_reminders_the_late_list_and_r09(env):
    adv = env.post("admin", "/admin/clock", {"advance_days": 25})
    assert adv["offset_days"] == pytest.approx(25)
    out = env.post("admin", "/admin/windows/run-cycle")
    assert sorted(out["late"]) == ["Cauvery Polytechnic", "Yamuna Pharmacy Institute"]
    assert out["sent"] >= 1
    # the officer reminder went out through the mail adapter
    assert ("officer@demo.test", "Institution has not submitted") in env.mail.sent
    officer_inbox = env.get("officer", "/notifications")
    assert any(n["subject"] == "Institution has not submitted" for n in officer_inbox)
    late = env.get("admin", "/reports/late_submitters")["rows"]
    assert sorted(r["institution"] for r in late) == ["Cauvery Polytechnic",
                                                      "Yamuna Pharmacy Institute"]
    r09 = env.flags("admin", rule="R09")
    assert sorted(f["institution_name"] for f in r09) == ["Cauvery Polytechnic",
                                                          "Yamuna Pharmacy Institute"]
    # running it again sends nothing new (idempotent)
    assert env.post("admin", "/admin/windows/run-cycle")["sent"] == 0


# ---- 9. tampering ------------------------------------------------------------------------------

def test_case_09_a_value_changed_in_the_database_is_found_at_the_first_broken_row(env):
    assert env.post("admin", "/admin/audit/verify")["ok"] is True
    ids = [i for (i,) in env.db.execute(select(AuditLog.id).order_by(AuditLog.id))]
    victim = ids[len(ids) // 2]
    env.db.execute(update(AuditLog).where(AuditLog.id == victim).values(
        after={"tampered": True}))
    env.db.commit()
    res = env.post("admin", "/admin/audit/verify")
    assert res["ok"] is False and res["first_broken_id"] == victim
    assert res["count"] == ids.index(victim) + 1  # the walk stopped at the break


# ---- the numbers at the end --------------------------------------------------------------------

def test_final_dashboard_numbers(env):
    kav = env.dashboard_row(KAVERI)
    assert kav["state"] == "Excess" and kav["flags"] == {"R06": 1, "R07": 1, "R10": 1}
    assert kav["open_flags"] == 3  # R04 was dismissed in case 2; R10 arrived with case 10
    assert env.dashboard_row(MALABAR)["state"] == "Clear"
    # Northfield was Alert until its R05 was resolved in case 4; nothing else is open there
    assert env.dashboard_row(NORTHFIELD)["state"] == "Clear"
    tiles = env.get("admin", "/dashboards/aicte")["tiles"]
    assert tiles["excess"] >= 1 and tiles["open_flags"] >= 3
