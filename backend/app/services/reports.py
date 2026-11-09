"""Built-in reports (idea doc section 13), all computed by services/metrics.py so the figures
match the dashboards. Every report is aggregate: no name, date of birth or APAAR ID appears,
except the masked ID that duplicate cases already carry. Reports run only inside the caller's scope."""
import csv
import io
from collections import defaultdict

from sqlalchemy.orm import Session

from app.db.session import uow
from app.models.enums import Role
from app.models.user import User
from app.models.windows import SavedReport
from app.services import audit, metrics
from app.services.access import can_access_institution
from app.services.errors import Forbidden, Invalid, NotFound

GROUPS = ("programme", "institution", "programme_type", "region")
FILTERS = ["region", "type", "cycle_year", "institution_id"]
CATALOGUE = {
    "enrolment_vs_intake": ("Enrolment against approved intake", FILTERS + ["group_by"]),
    "flags_by_rule_month": ("Flags by rule and month", FILTERS[:2] + ["institution_id"]),
    "late_submitters": ("Late or non-submitting institutions", FILTERS),
    "pending_apaar_share": ("Share of records pending APAAR", FILTERS),
    "duplicate_cases": ("Duplicate enrolment cases and their resolution", FILTERS[:2]
                        + ["institution_id"]),
    "category_counts": ("Category, NRI, OCI and foreign national counts by programme", FILTERS),
}


def catalogue() -> list[dict]:
    return [{"key": k, "title": t, "filters": f} for k, (t, f) in CATALOGUE.items()]


def _scope(db: Session, user: User, f: dict):
    iid = f.get("institution_id")
    if iid:
        from app.models.org import Institution
        inst = db.get(Institution, iid)
        if inst is None:
            raise NotFound("Institution not found")
        if not can_access_institution(db, user, inst):
            raise Forbidden("You do not have access to this institution")
    insts = metrics.scoped_institutions(db, user, region=f.get("region"), type_=f.get("type"),
                                        institution_id=iid)
    cycle = int(f["cycle_year"]) if f.get("cycle_year") else metrics.default_cycle(db)
    return insts, cycle


def _enrolment(db, insts, cycle, f):
    group = f.get("group_by") or "programme"
    if group not in GROUPS:
        raise Invalid(f"group_by must be one of {', '.join(GROUPS)}")
    key = {"programme": ("institution", "programme"), "institution": ("institution",),
           "programme_type": ("level",), "region": ("region",)}[group]
    acc: dict[tuple, dict] = defaultdict(lambda: {"enrolled": 0, "approved_intake": 0, "allowed": 0})
    for p in metrics.programme_rows(db, [i.id for i in insts], cycle):
        a = acc[tuple(p[k] for k in key)]
        for m in ("enrolled", "approved_intake", "allowed"):
            a[m] += p[m]
    label = {"level": "programme_type"}
    rows = [{**{label.get(k, k): v for k, v in zip(key, ks, strict=True)}, **a,
             "over_allowed": max(a["enrolled"] - a["allowed"], 0)} for ks, a in acc.items()]
    cols = [label.get(k, k) for k in key] + ["enrolled", "approved_intake", "allowed", "over_allowed"]
    return cols, rows, {}


def _flags(db, insts, cycle, f):
    return ["month", "rule", "count"], metrics.flags_by_rule_month(db, [i.id for i in insts]), {}


def _late(db, insts, cycle, f):
    rows = [r for r in metrics.submission_status(db, insts, cycle) if r["status"] != "on_time"]
    rows = [{"institution": r["institution"], "region": r["region"], "status": r["status"],
             "first_upload": r["first_upload"].isoformat() if r["first_upload"] else None,
             "closes_at": r["closes_at"].isoformat() if r["closes_at"] else None} for r in rows]
    return ["institution", "region", "status", "first_upload", "closes_at"], rows, {}


def _pending(db, insts, cycle, f):
    share = metrics.pending_share(db, [i.id for i in insts], cycle)
    rows = []
    for i in insts:
        s = metrics.pending_share(db, [i.id], cycle)
        rows.append({"institution": i.name, **s})
    return ["institution", "pending", "total", "share_pct"], rows, {"total": share}


def _dups(db, insts, cycle, f):
    return (["institution", "rule", "state", "apaar_id", "raised", "resolved"],
            metrics.duplicate_cases(db, [i.id for i in insts]), {})


def _categories(db, insts, cycle, f):
    return (["institution", "programme", "category", "records", "nri", "oci", "foreign_national"],
            metrics.category_counts(db, [i.id for i in insts], cycle), {})


_RUN = {"enrolment_vs_intake": _enrolment, "flags_by_rule_month": _flags,
        "late_submitters": _late, "pending_apaar_share": _pending, "duplicate_cases": _dups,
        "category_counts": _categories}


def run(db: Session, user: User, key: str, filters: dict, fmt: str = "json") -> dict:
    """Run one report and audit it (every export is logged, with filters and row count)."""
    if key not in CATALOGUE:
        raise NotFound("Unknown report")
    if user.role == Role.VERIFIER:
        raise Forbidden("Not allowed for your role")
    insts, cycle = _scope(db, user, filters)
    cols, rows, extra = _RUN[key](db, insts, cycle, filters)
    with uow(db):
        audit.append(db, actor_id=user.id, actor_role=user.role, action="REPORT.EXPORTED",
                     entity_type="report", entity_id=key,
                     after={"filters": filters, "format": fmt, "rows": len(rows),
                            "cycle_year": cycle})
    return {"key": key, "title": CATALOGUE[key][0], "cycle_year": cycle, "columns": cols,
            "rows": rows, **extra}


def to_csv(result: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(result["columns"])
    for r in result["rows"]:
        w.writerow([r.get(c, "") if r.get(c) is not None else "" for c in result["columns"]])
    return buf.getvalue()


def save(db: Session, user: User, name: str, key: str, filters: dict) -> SavedReport:
    if key not in CATALOGUE:
        raise Invalid("Unknown report")
    with uow(db):
        row = SavedReport(user_id=user.id, name=name, report_key=key, filters=filters)
        db.add(row)
        db.flush()
        audit.append(db, actor_id=user.id, actor_role=user.role, action="REPORT.SAVED",
                     entity_type="saved_report", entity_id=row.id,
                     after={"name": name, "report_key": key, "filters": filters})
    return row

