"""Serializer-level masking helpers shared by the record, flag and upload endpoints."""
from app.domain.clear_hint import clear_hint
from app.models.enums import AICTE_ROLES


def hint_out(rule_code: str, evidence: dict) -> dict | None:
    """The 'to clear' hint. Its values are counts and limits, never student identifiers."""
    h = clear_hint(rule_code, evidence)
    return {"key": h[0], "values": h[1]} if h else None


def _mask_name(name: str) -> str:
    return " ".join(w[0] + "*" * (len(w) - 1) for w in name.split())


def mask_evidence(evidence: dict, viewer) -> dict:
    """R08 evidence names both records. Names of records held by another institution are masked
    for institution users; AICTE roles see everything."""
    if viewer.role in AICTE_ROLES or "a" not in evidence:
        return evidence
    out = dict(evidence)
    for k in ("a", "b"):
        if out[k]["institution_id"] != viewer.institution_id:
            out[k] = out[k] | {"name": _mask_name(out[k]["name"])}
    return out
