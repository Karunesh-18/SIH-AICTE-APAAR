"""Impact preview for R08, R10 and R11: run the pure rule with the active and the proposed
parameters over today's data. Computed only; nothing is written and nothing is audited."""
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import rules as R
from app.domain import rules_scheduled as S
from app.models.org import Institution
from app.models.student import StudentRecord
from app.services import anomaly, metrics, rules_admin, validation
from app.services.errors import Invalid

SUPPORTED = ("R08", "R10", "R11")
EXAMPLES = 5


def _r08_people(db: Session, cycle: int) -> list[R.Person]:
    dobs = set(db.scalars(select(StudentRecord.dob).where(*metrics.current_filters(cycle))))
    # stored people carry no row number, which r08 treats as "not new"; mark every one as new
    return [replace(p, row_number=0) for p in validation._stored_people(db, cycle, dobs, None)]


def _runner(db: Session, code: str, cycle: int):
    """Gather the facts once; return run(params) -> {key: (institution ids, example)}."""
    if code == "R08":
        people = _r08_people(db, cycle)

        def run(params):
            out = {}
            for d in R.r08_near_duplicate(people, params):
                a, b = d.evidence["a"], d.evidence["b"]
                key = "|".join(sorted((a["record_id"], b["record_id"])))
                out[key] = ({a["institution_id"], b["institution_id"]},
                            {"institutions": sorted({a["institution"], b["institution"]}),
                             "ids": d.evidence["ids"], "score": d.evidence["score"]})
            return out
        return run
    enrolled = anomaly._enrolled_by_institution(db, cycle)
    if code == "R10":
        previous = anomaly._enrolled_by_institution(db, cycle - 1)

        def fn(i, p):
            return S.r10_jump(enrolled.get(i, 0), previous.get(i), p)
    else:
        pending = anomaly._pending_by_institution(db, cycle)

        def fn(i, p):
            return S.r11_pending(pending.get(i, 0), enrolled.get(i, 0), p)

    def run(params):
        return {i: ({i}, d.evidence) for i in enrolled if (d := fn(i, params))}
    return run


def preview(db: Session, code: str, proposed_params: dict, cycle: int | None = None) -> dict:
    if code not in SUPPORTED:
        raise Invalid("Preview is available for R08, R10, R11")
    active = next((v for r, v in rules_admin.list_rules(db) if r.code == code), None)
    if active is None:
        raise Invalid(f"Rule {code} has no active version")
    cycle = cycle if cycle is not None else metrics.default_cycle(db)
    run = _runner(db, code, cycle)
    cur, new = run(active.params), run({**active.params, **proposed_params})
    names = dict(db.execute(select(Institution.id, Institution.name)).all())
    inst: dict[str, dict] = {}
    for side, flags in (("current", cur), ("proposed", new)):
        for ids, _ in flags.values():
            for i in ids:
                inst.setdefault(i, {"current": 0, "proposed": 0})[side] += 1

    def example(key, flags):
        ev = flags[key][1]
        return ev if code == "R08" else {"institution": names.get(key), **ev}

    added = [k for k in new if k not in cur]
    cleared = [k for k in cur if k not in new]
    return {"code": code, "cycle": cycle, "current_params": active.params,
            "proposed_params": proposed_params, "current_count": len(cur),
            "proposed_count": len(new), "added": len(added), "cleared": len(cleared),
            "added_examples": [example(k, new) for k in added[:EXAMPLES]],
            "cleared_examples": [example(k, cur) for k in cleared[:EXAMPLES]],
            "by_institution": sorted(({"institution_id": i, "name": names.get(i, i), **c}
                                      for i, c in inst.items()), key=lambda x: x["name"])}
