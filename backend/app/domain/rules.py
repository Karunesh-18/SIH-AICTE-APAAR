"""Rules R01-R07 as pure functions. Each returns FlagDrafts that name the rule and carry the numbers.

The platform is advisory: nothing here rejects, corrects or penalises a row.
"""
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date

from app.domain.apaar import check_format, mask
from app.domain.similarity import similarity


@dataclass(frozen=True)
class Row:
    row_number: int
    apaar_id: str | None
    name: str | None
    dob: date | None
    admission_date: date | None
    admission_category: str | None


@dataclass(frozen=True)
class ProgrammeInfo:
    approved_intake: int
    supernumerary_seats: int


@dataclass(frozen=True)
class RegistryInfo:
    name: str
    dob: date


@dataclass
class FlagDraft:
    rule: str
    reason_key: str
    row_numbers: list[int]
    evidence: dict = field(default_factory=dict)


def r01_missing_id(rows: list[Row], params: Mapping) -> list[FlagDraft]:
    return [FlagDraft("R01", "id_missing", [r.row_number]) for r in rows if not r.apaar_id]


def r02_format(rows: list[Row], params: Mapping) -> list[FlagDraft]:
    digits, checksum = params.get("digits", 12), params.get("checksum", "none")
    return [
        FlagDraft("R02", "id_format", [r.row_number],
                  {"found": r.apaar_id, "expected_digits": digits, "checksum": checksum,
                   "digits_found": len(r.apaar_id)})
        for r in rows if r.apaar_id and not check_format(r.apaar_id, checksum, digits)
    ]


def r03_registry(rows: list[Row], params: Mapping,
                 lookup: Callable[[str], RegistryInfo | None]) -> list[FlagDraft]:
    threshold = params.get("name_threshold", 0.8)
    out = []
    for r in rows:
        if not r.apaar_id or not check_format(r.apaar_id):
            continue  # R01 and R02 already speak for these rows
        hit = lookup(r.apaar_id)
        if hit is None:
            out.append(FlagDraft("R03", "registry_not_found", [r.row_number],
                                 {"apaar_id": r.apaar_id}))
        elif r.name and (sim := similarity(r.name, hit.name)) < threshold:
            out.append(FlagDraft("R03", "registry_name_differs", [r.row_number],
                                 {"submitted": r.name, "registry": hit.name,
                                  "similarity": round(sim, 2), "threshold": threshold}))
        elif r.dob and r.dob != hit.dob:
            out.append(FlagDraft("R03", "registry_dob_differs", [r.row_number],
                                 {"submitted": r.dob.isoformat(), "registry": hit.dob.isoformat()}))
    return out


def r04_duplicate_in_file(rows: list[Row], params: Mapping) -> list[FlagDraft]:
    groups: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        if r.apaar_id:
            groups[r.apaar_id].append(r.row_number)
    return [FlagDraft("R04", "dup_in_file", sorted(nums), {"apaar_id": k, "count": len(nums)})
            for k, nums in groups.items() if len(nums) > 1]


def r05_two_institutions(rows: list[Row], others: Mapping[str, list[dict]]) -> list[FlagDraft]:
    return [FlagDraft("R05", "active_elsewhere", [r.row_number],
                      {"apaar_id": r.apaar_id, "elsewhere": others[r.apaar_id]})
            for r in rows if r.apaar_id and others.get(r.apaar_id)]


def r06_intake_cap(rows: list[Row], programme: ProgrammeInfo, params: Mapping) -> list[FlagDraft]:
    allowed = programme.approved_intake + programme.supernumerary_seats
    excess = len(rows) - allowed
    if excess <= 0:
        return []
    # Only an ordering: the rows that arrived last by admission date, not a finding about them.
    ordered = sorted(rows, key=lambda r: (r.admission_date or date.max, r.row_number))
    last = sorted(r.row_number for r in ordered[-excess:])
    return [FlagDraft("R06", "intake_cap", last,
                      {"approved_intake": programme.approved_intake,
                       "supernumerary_seats": programme.supernumerary_seats, "allowed": allowed,
                       "actual": len(rows), "excess": excess, "ordering_only": True})]


def r07_fields(rows: list[Row], cycle_year: int, params: Mapping) -> list[FlagDraft]:
    out = []
    for r in rows:
        key = None
        if not (r.name or "").strip():
            key = "name_missing"
        elif r.dob is None:
            key = "dob_missing"
        elif r.admission_date is None:
            key = "admission_date_missing"
        elif not (r.admission_category or "").strip():
            key = "category_missing"
        elif r.admission_date.year > cycle_year:
            key = "admission_after_cycle"
        elif r.dob >= r.admission_date:
            key = "dob_after_admission"
        if key:
            ev = {}
            if r.admission_date:
                ev["admission_date"] = r.admission_date.isoformat()
            if key == "admission_after_cycle":
                ev["cycle_year"] = cycle_year
            out.append(FlagDraft("R07", key, [r.row_number], ev))
    return out


@dataclass(frozen=True)
class Person:
    """One side of a possible near-duplicate. row_number is set for rows of the upload being
    checked and None for records already stored."""
    ref: str
    apaar_id: str | None
    name: str
    dob: date | None
    row_number: int | None
    institution_id: str
    institution: str


def _side(x: Person) -> dict:
    return {"record_id": x.ref, "apaar_id": mask(x.apaar_id), "name": x.name,
            "institution_id": x.institution_id, "institution": x.institution,
            "row_number": x.row_number}


def r08_near_duplicate(people: list[Person], params: Mapping) -> list[FlagDraft]:
    """Same date of birth, similar name, different or missing APAAR IDs. Each pair once; a pair
    of two stored records is skipped because it is not new."""
    threshold = params.get("threshold", 0.85)
    by_dob: dict[date, list[Person]] = defaultdict(list)
    for x in people:
        if x.dob and x.dob != date.min and (x.name or "").strip():
            by_dob[x.dob].append(x)
    out = []
    for group in by_dob.values():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.row_number is None and b.row_number is None:
                    continue
                if a.apaar_id and a.apaar_id == b.apaar_id:
                    continue
                if (score := similarity(a.name, b.name)) < threshold:
                    continue
                ids = " / ".join(mask(x.apaar_id) or "no APAAR ID" for x in (a, b))
                out.append(FlagDraft(
                    "R08", "near_duplicate", sorted(x.row_number for x in (a, b) if x.row_number),
                    {"ids": ids, "score": round(score, 2), "threshold": threshold,
                     "a": _side(a), "b": _side(b)}))
    return out
