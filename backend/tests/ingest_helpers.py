"""Shared builders for ingestion tests. Synthetic data only."""
import csv
import io
import json

from app.models.org import Programme
from app.models.student import RegistryEntry
from app.services import ingest

COLS = ["apaar_id", "name", "dob", "admission_date", "admission_category"]
DOB, ADM = "2001-03-04", "2026-07-01"


def ap(n: int) -> str:
    return f"9999{n:08d}"


def row(n, **kw):
    base = {"apaar_id": ap(n), "name": f"Student {n}", "dob": DOB, "admission_date": ADM,
            "admission_category": "OPEN"}
    return base | kw


def csv_bytes(rows, cols=COLS, bom=False) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return (("﻿" if bom else "") + buf.getvalue()).encode("utf-8")


def json_bytes(rows) -> bytes:
    return json.dumps(rows).encode()


def programme(db, inst, name="MBA", intake=10, seats=0, cycle=2026):
    p = Programme(institution_id=inst.id, name=name, level="PG", cycle_year=cycle,
                  approved_intake=intake, supernumerary_seats=seats)
    db.add(p)
    db.commit()
    return p


def register(db, rows):
    from datetime import date

    for r in rows:
        known = r.get("apaar_id") and len(r["apaar_id"]) == 12 and r["apaar_id"].isdigit()
        if known and db.query(RegistryEntry).filter_by(apaar_id=r["apaar_id"]).first() is None:
            db.add(RegistryEntry(apaar_id=r["apaar_id"], name=r["name"],
                                     dob=date.fromisoformat(r["dob"])))
    db.commit()


def run(db, inst, data, user=None, cycle=2026, **kw):
    """Receive and process one upload synchronously; returns the Upload."""
    return ingest.ingest(db, actor=user, institution_id=inst.id, cycle_year=cycle, data=data, **kw)
