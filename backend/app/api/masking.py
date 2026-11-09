"""Serializer-level masking helpers shared by the record, flag and upload endpoints."""
from app.models.enums import AICTE_ROLES


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
