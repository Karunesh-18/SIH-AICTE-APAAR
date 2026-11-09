"""Flag review state machine. Pure: no framework imports."""

ACTIONS = {"review": "under_review", "resolve": "resolved", "dismiss": "dismissed",
           "ask": "ask_institution", "reply": "under_review", "link": "resolved"}
TERMINAL = frozenset({"resolved", "dismissed"})
# state -> states it may move to
TRANSITIONS = {
    "open": {"under_review", "resolved", "dismissed", "ask_institution"},
    "under_review": {"resolved", "dismissed", "ask_institution"},
    "ask_institution": {"under_review", "resolved", "dismissed"},
    "resolved": set(),
    "dismissed": set(),
}
# 'reply' only answers an ask; 'review' on an under_review flag is not a move.
_ONLY_FROM = {"reply": {"ask_institution"}}


class InvalidTransition(ValueError):
    pass


def is_terminal(state: str) -> bool:
    return state in TERMINAL


def next_state(state: str, action: str) -> str:
    target = ACTIONS[action]
    if target not in TRANSITIONS.get(state, set()) or state not in _ONLY_FROM.get(action, {state}):
        raise InvalidTransition(f"A flag that is {state.replace('_', ' ')} cannot take the "
                                f"'{action}' action.")
    return target
