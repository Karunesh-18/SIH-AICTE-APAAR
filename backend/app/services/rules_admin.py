"""Rule versions. A change is always a new row; the old one is deactivated, never edited, so flags
raised earlier keep the version they were raised under."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import uow
from app.models.rules import Rule, RuleVersion
from app.models.user import User
from app.services import audit

FIELDS = ("enabled", "params", "hard_stop", "message_en", "message_hi")


class NotFound(Exception):
    pass


def _rule(db: Session, code: str) -> Rule:
    rule = db.scalars(select(Rule).where(Rule.code == code)).first()
    if rule is None:
        raise NotFound(f"Rule {code} not found")
    return rule


def list_rules(db: Session) -> list[tuple[Rule, RuleVersion | None]]:
    out = []
    for rule in db.scalars(select(Rule).order_by(Rule.code)):
        active = db.scalars(select(RuleVersion).where(RuleVersion.rule_code == rule.code,
                                                      RuleVersion.is_active)).first()
        out.append((rule, active))
    return out


def versions(db: Session, code: str) -> list[RuleVersion]:
    _rule(db, code)
    return list(db.scalars(select(RuleVersion).where(RuleVersion.rule_code == code)
                           .order_by(RuleVersion.version_no.desc())))


def get_version(db: Session, code: str, version_no: int) -> RuleVersion:
    _rule(db, code)
    v = db.scalars(select(RuleVersion).where(RuleVersion.rule_code == code,
                                             RuleVersion.version_no == version_no)).first()
    if v is None:
        raise NotFound(f"Rule {code} has no version {version_no}")
    return v


def _new_version(db: Session, actor: User, code: str, values: dict, note: str, action: str,
                 extra: dict) -> RuleVersion:
    _rule(db, code)
    with uow(db):
        current = db.scalars(select(RuleVersion).where(RuleVersion.rule_code == code,
                                                       RuleVersion.is_active)).first()
        top = max(v.version_no for v in db.scalars(
            select(RuleVersion).where(RuleVersion.rule_code == code)))
        if current:
            current.is_active = False
            db.flush()  # one active version per rule, enforced by the database
        v = RuleVersion(rule_code=code, version_no=top + 1, is_active=True, created_by=actor.id,
                        note=note, **values)
        db.add(v)
        db.flush()
        audit.append(db, actor_id=actor.id, actor_role=actor.role, action=action,
                     entity_type="rule_version", entity_id=v.id,
                     before={"version_no": current.version_no} if current else None,
                     after={"rule": code, "version_no": v.version_no, "note": note, **extra})
    return v


def update(db: Session, actor: User, code: str, changes: dict, note: str) -> RuleVersion:
    base = next((v for r, v in list_rules(db) if r.code == code), None)
    _rule(db, code)
    values = {f: getattr(base, f) for f in FIELDS} if base else {}
    values.update({k: v for k, v in changes.items() if k in FIELDS and v is not None})
    return _new_version(db, actor, code, values, note, "RULE.UPDATED",
                        {"changed": sorted(changes)})


def revert(db: Session, actor: User, code: str, to_version: int, note: str) -> RuleVersion:
    old = get_version(db, code, to_version)
    return _new_version(db, actor, code, {f: getattr(old, f) for f in FIELDS}, note,
                        "RULE.REVERTED", {"copied_from": to_version})


def diff(db: Session, code: str, a: int, b: int) -> dict:
    va, vb = get_version(db, code, a), get_version(db, code, b)
    changes = {f: {"from": getattr(va, f), "to": getattr(vb, f)}
               for f in FIELDS if getattr(va, f) != getattr(vb, f)}
    return {"code": code, "from": a, "to": b, "changes": changes}
