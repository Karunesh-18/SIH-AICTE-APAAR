"""Receive a file or JSON batch, parse it, store the records as new versions, then validate.

Nothing is rejected row by row: a whole upload is REJECTED only when it cannot be read at all
(empty, unreadable, missing required columns, no way to tell the programme). Everything readable is
stored, and the rules flag it (advisory only).
"""
import csv
import hashlib
import io
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.registry import MockRegistry, RegistryAdapter
from app.core import clock
from app.db.base import new_id
from app.db.session import uow
from app.domain.apaar import normalize
from app.domain.rules import Row
from app.models.org import Programme
from app.models.student import StudentRecord, Upload
from app.models.user import User
from app.services import audit, notify, validation

log = logging.getLogger(__name__)

# Required: apaar_id (the column, values may be blank), name, dob, admission_date, admission_category.
ALIASES = {
    "apaar_id": ["apaar_id", "apaar", "apaarid", "apaar_no", "apaar_number"],
    "name": ["name", "student_name", "full_name"],
    "dob": ["dob", "date_of_birth", "birth_date"],
    "programme": ["programme", "program", "course"],
    "admission_date": ["admission_date", "date_of_admission", "admitted_on"],
    "admission_category": ["admission_category", "category", "admission_cat"],
    "nri": ["nri"],
    "oci": ["oci"],
    "fn": ["fn", "foreign_national"],
    "year_of_study": ["year_of_study", "year"],
}
REQUIRED = ["apaar_id", "name", "dob", "admission_date", "admission_category"]
_CANON = {alias: canon for canon, aliases in ALIASES.items() for alias in aliases}
TEMPLATE_COLUMNS = ["apaar_id", "name", "dob", "programme", "admission_date",
                    "admission_category", "nri", "oci", "fn", "year_of_study"]
TEMPLATE_EXAMPLE = ["999900000001", "Asha Rao", "2004-03-18", "", "2026-07-01", "OPEN",
                    "no", "no", "no", "1"]
PLACEHOLDER_DATE = date.min  # stored when a date cannot be read; R07 flags the row (NOT NULL column)


class IngestError(Exception):
    """The whole upload cannot be used. The message goes back to the institution as written."""


@dataclass(frozen=True)
class ParsedRow(Row):
    programme: str | None = None
    nri: bool = False
    oci: bool = False
    fn: bool = False
    year_of_study: int = 1


# ---- parsing ----------------------------------------------------------------------------------

def sniff_format(data: bytes) -> str:
    if data[:4] == b"PK\x03\x04":
        return "xlsx"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "xls"
    if data.lstrip(b"\xef\xbb\xbf \t\r\n")[:1] in (b"[", b"{"):
        return "json"
    return "csv"


def _key(h) -> str:
    return re.sub(r"[\s\-]+", "_", str(h or "").strip().lower())


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


_DMY = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})")
_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")


def parse_date(v) -> date | None:
    """Day-first (dd/mm/yyyy, dd-mm-yyyy) or ISO. Anything else is None, never guessed."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = _text(v)
    try:
        if m := _ISO.match(s):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if m := _DMY.match(s):
            return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        pass
    return None


def _bool(v) -> bool:
    return _text(v).lower() in {"y", "yes", "true", "t", "1"}


def _year(v) -> int:
    try:
        return max(int(float(_text(v))), 1)
    except ValueError:
        return 1


def _csv_table(data: bytes) -> list[list]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise IngestError("The file could not be read: it is not UTF-8 text. "
                          "Save it as CSV (UTF-8) or upload XLSX.") from None
    if "\x00" in text:
        raise IngestError("The file could not be read as CSV.")
    return list(csv.reader(io.StringIO(text)))


def _xlsx_table(data: bytes) -> list[list]:
    import openpyxl

    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        return [list(r) for r in wb.active.iter_rows(values_only=True)]
    except Exception:  # noqa: BLE001  any library failure means an unreadable file
        raise IngestError("The file could not be read as an XLSX workbook.") from None


def _xls_table(data: bytes) -> list[list]:
    import xlrd

    try:
        book = xlrd.open_workbook(file_contents=data)
        sheet = book.sheet_by_index(0)
        out = []
        for r in range(sheet.nrows):
            row = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    row.append(xlrd.xldate_as_datetime(cell.value, book.datemode).date())
                elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    row.append(None)
                else:
                    row.append(cell.value)
            out.append(row)
        return out
    except Exception:  # noqa: BLE001
        raise IngestError("The file could not be read as a legacy XLS workbook.") from None


def _json_table(data: bytes) -> list[list]:
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        raise IngestError("The file could not be read as JSON.") from None
    items = obj.get("students") if isinstance(obj, dict) else obj
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise IngestError('JSON must be a list of student objects or {"students": [...]}.')
    headers: list = []
    for i in items:
        headers += [k for k in i if k not in headers]
    return [headers] + [[i.get(h) for h in headers] for i in items]


_READERS = {"csv": _csv_table, "xlsx": _xlsx_table, "xls": _xls_table, "json": _json_table,
            "api": _json_table}


def parse(data: bytes, fmt: str | None = None) -> list[ParsedRow]:
    if not data.strip():
        raise IngestError("The file is empty.")
    table = [r for r in _READERS[fmt or sniff_format(data)](data)
             if any(_text(c) for c in r)]
    if not table:
        raise IngestError("The file is empty.")
    cols: dict[str, int] = {}
    for i, h in enumerate(table[0]):
        if (canon := _CANON.get(_key(h))) and canon not in cols:
            cols[canon] = i  # extra columns are ignored
    if missing := [c for c in REQUIRED if c not in cols]:
        raise IngestError("Missing required columns: " + ", ".join(missing)
                          + ". Download the template for the expected layout.")
    if len(table) == 1:
        raise IngestError("The file has no data rows.")

    def cell(r, name):
        i = cols.get(name)
        return r[i] if i is not None and i < len(r) else None

    out = []
    for n, r in enumerate(table[1:], 1):
        out.append(ParsedRow(
            row_number=n, apaar_id=normalize(_text(cell(r, "apaar_id"))),
            name=_text(cell(r, "name")) or None, dob=parse_date(cell(r, "dob")),
            admission_date=parse_date(cell(r, "admission_date")),
            admission_category=_text(cell(r, "admission_category")) or None,
            programme=_text(cell(r, "programme")) or None, nri=_bool(cell(r, "nri")),
            oci=_bool(cell(r, "oci")), fn=_bool(cell(r, "fn")),
            year_of_study=_year(cell(r, "year_of_study")) if cell(r, "year_of_study") else 1))
    return out


def template_csv() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(TEMPLATE_COLUMNS)
    w.writerow(TEMPLATE_EXAMPLE)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def template_xlsx() -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "students"
    ws.append(TEMPLATE_COLUMNS)
    ws.append(TEMPLATE_EXAMPLE)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---- use cases --------------------------------------------------------------------------------

def receive(db: Session, *, actor: User | None, institution_id: str, cycle_year: int,
            data: bytes, source: str = "FILE", fmt: str | None = None,
            api_key_id: str | None = None) -> Upload:
    """Store the upload row (RECEIVED) and audit it. Parsing happens in process()."""
    with uow(db):
        up = Upload(institution_id=institution_id, cycle_year=cycle_year, source=source,
                    format=fmt or sniff_format(data), file_hash=hashlib.sha256(data).hexdigest(),
                    status="RECEIVED", uploaded_by=actor.id if actor else None)
        db.add(up)
        db.flush()
        audit.append(db, actor_id=actor.id if actor else None,
                     actor_role=actor.role if actor else "API_KEY", action="UPLOAD.RECEIVED",
                     entity_type="upload", entity_id=up.id,
                     after={"institution_id": institution_id, "cycle_year": cycle_year,
                            "format": up.format, "bytes": len(data), "api_key_id": api_key_id})
    return up


def _programmes_for(db: Session, up: Upload, parsed: list[ParsedRow]) -> dict[int, Programme]:
    progs = db.scalars(select(Programme).where(
        Programme.institution_id == up.institution_id,
        Programme.cycle_year == up.cycle_year)).all()
    if not progs:
        raise IngestError(f"No programme is set up for this institution in the {up.cycle_year} "
                          "cycle. AICTE sets approved intake; please contact your regional officer.")
    by_name = {p.name.strip().lower(): p for p in progs}
    out, unknown = {}, set()
    for r in parsed:
        if r.programme:
            p = by_name.get(r.programme.strip().lower())
            if p is None:
                unknown.add(r.programme)
            else:
                out[r.row_number] = p
        elif len(progs) == 1:
            out[r.row_number] = progs[0]
        else:
            raise IngestError("This institution has several programmes, so the file needs a "
                              "programme column. Known programmes: "
                              + ", ".join(sorted(p.name for p in progs)) + ".")
    if unknown:
        raise IngestError("Unknown programme in the file: " + ", ".join(sorted(unknown))
                          + ". Known programmes: " + ", ".join(sorted(p.name for p in progs)) + ".")
    return out


def _store(db: Session, up: Upload, parsed: list[ParsedRow],
           prog_of: dict[int, Programme]) -> tuple[dict[int, StudentRecord], int]:
    """Insert records. The first row of an ID is current and supersedes the earlier current row
    (version + 1). A later row of the same ID in the same file is stored not current (ADR-012)."""
    ids = {r.apaar_id for r in parsed if r.apaar_id}
    old_by_key: dict[tuple, StudentRecord] = {}
    if ids:
        for o in db.scalars(select(StudentRecord).where(
                StudentRecord.is_current, StudentRecord.cycle_year == up.cycle_year,
                StudentRecord.apaar_id.in_(ids))):  # ponytail: one IN list, chunk at ~30k ids
            old_by_key[(o.apaar_id, o.programme_id)] = o
    seen: set[tuple] = set()
    plan = []
    for r in parsed:
        key = (r.apaar_id, prog_of[r.row_number].id)
        first = r.apaar_id is None or key not in seen
        seen.add(key)
        old = old_by_key.get(key) if r.apaar_id and first else None
        plan.append((r, first, old))
    now = clock.now()
    for _r, _first, old in plan:
        if old:
            old.is_current, old.superseded_at = False, now
    db.flush()  # free the unique "one current record" slot before the new rows go in
    records: dict[int, StudentRecord] = {}
    superseded = 0
    for r, first, old in plan:
        rec = StudentRecord(
            id=new_id(), apaar_id=r.apaar_id[:32] if r.apaar_id else None,
            name=r.name or "", dob=r.dob or PLACEHOLDER_DATE,
            programme_id=prog_of[r.row_number].id, cycle_year=up.cycle_year,
            year_of_study=r.year_of_study, admission_date=r.admission_date or PLACEHOLDER_DATE,
            admission_category=r.admission_category or "UNSPECIFIED",
            nri=r.nri, oci=r.oci, fn=r.fn,
            status="pending_apaar" if r.apaar_id is None else "submitted",
            version=old.version + 1 if old else 1, is_current=first,
            continues_record_id=old.id if old else None,
            upload_id=up.id, row_number=r.row_number)
        db.add(rec)
        records[r.row_number] = rec
    db.flush()
    for r, _first, old in plan:
        if old:
            old.superseded_by = records[r.row_number].id
            superseded += 1
    db.flush()
    return records, superseded


def _reject(db: Session, up: Upload, message: str) -> None:
    db.rollback()
    with uow(db):
        up.status, up.error = "REJECTED", message
        audit.append(db, **validation.actor_of(db, up), action="UPLOAD.REJECTED", entity_type="upload",
                     entity_id=up.id, after={"reason": message})
        notify.enqueue(db, validation.institution_users(db, up.institution_id),
                       subject="Upload rejected", body=message,
                       related_type="upload", related_id=up.id)


def process(db: Session, upload_id: str, data: bytes,
            registry: RegistryAdapter | None = None) -> Upload:
    """Synchronous core. The API runs it from a background task; tests call it directly."""
    up = db.get(Upload, upload_id)
    up.status = "PROCESSING"
    db.commit()
    try:
        with uow(db):
            parsed = parse(data, up.format)
            prog_of = _programmes_for(db, up, parsed)
            up.row_count = len(parsed)
            records, superseded = _store(db, up, parsed, prog_of)
            validation.validate(db, up, parsed, records, prog_of,
                                registry or MockRegistry(db), superseded=superseded)
    except IngestError as e:
        _reject(db, up, str(e))
    except Exception:
        db.rollback()
        up.status, up.error = "REJECTED", "Processing failed unexpectedly; nothing was stored."
        db.commit()
        log.exception("upload %s failed", upload_id)
        raise
    return up


def ingest(db: Session, *, registry: RegistryAdapter | None = None, **kw) -> Upload:
    """receive + process in one call (used by tests and the synchronous JSON push)."""
    data = kw["data"]
    up = receive(db, **kw)
    return process(db, up.id, data, registry)
