"""Flag state machine, table-tested. Pure: no database."""
import pytest

from app.domain import flags as F

STATES = ("open", "under_review", "resolved", "dismissed", "ask_institution")
ALLOWED = {
    ("open", "review"), ("open", "resolve"), ("open", "dismiss"), ("open", "ask"),
    ("under_review", "resolve"), ("under_review", "dismiss"), ("under_review", "ask"),
    ("ask_institution", "review"), ("ask_institution", "resolve"),
    ("ask_institution", "dismiss"), ("ask_institution", "reply"),
    ("open", "link"), ("under_review", "link"), ("ask_institution", "link"),
}


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("action", sorted(F.ACTIONS))
def test_transition_table(state, action):
    if (state, action) in ALLOWED:
        assert F.next_state(state, action) == F.ACTIONS[action]
    else:
        with pytest.raises(F.InvalidTransition):
            F.next_state(state, action)


def test_targets():
    assert F.ACTIONS == {"review": "under_review", "resolve": "resolved", "dismiss": "dismissed",
                         "ask": "ask_institution", "reply": "under_review", "link": "resolved"}


def test_terminal_states():
    assert F.is_terminal("resolved") and F.is_terminal("dismissed")
    assert not any(F.is_terminal(s) for s in ("open", "under_review", "ask_institution"))
