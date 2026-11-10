from datetime import UTC, datetime
from types import SimpleNamespace

from app.api.flags import flag_out


def _flag(evidence):
    return SimpleNamespace(
        id="i", rule_code="R06", reason_key="k", reason="r", state="OPEN", institution_id="x",
        assignee_id=None, upload_id="u", lock_version=1, evidence=evidence,
        created_at=datetime.now(UTC))


def test_flag_out_has_clear_hint():
    assert flag_out(_flag({"allowed": 60, "excess": 2}), "Inst", 3)["clear_hint"] == {
        "key": "hint.R06", "values": {"allowed": 60, "excess": 2}}


def test_flag_out_hint_null_without_evidence():
    assert flag_out(_flag({}), "Inst", 3)["clear_hint"] is None
