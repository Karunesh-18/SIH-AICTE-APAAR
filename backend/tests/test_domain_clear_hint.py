import pytest

from app.domain.clear_hint import clear_hint

CASES = [
    ("R01", {}, ("hint.R01", {})),
    ("R02", {"expected_digits": 12, "digits_found": 10}, ("hint.R02", {"digits": 12})),
    ("R03", {"apaar_id": "x"}, ("hint.R03", {})),
    ("R04", {"apaar_id": "x", "count": 3}, ("hint.R04", {"count": 3})),
    ("R05", {"apaar_id": "x", "elsewhere": []}, ("hint.R05", {})),
    ("R06", {"allowed": 60, "excess": 1}, ("hint.R06", {"allowed": 60, "excess": 1})),
    ("R06", {"allowed": 60, "excess": 5}, ("hint.R06", {"allowed": 60, "excess": 5})),
    ("R07", {"admission_date": "2026-01-01"}, ("hint.R07", {})),
    ("R08", {"score": 0.9}, ("hint.R08", {})),
    ("R09", {"closed_at": "2026-01-01"}, ("hint.R09", {})),
    ("R10", {"current": 150, "previous": 100, "rise_pct": 50.0, "limit_pct": 25},
     ("hint.R10", {"rise_pct": 50.0, "limit_pct": 25})),
    ("R11", {"pending": 30, "total": 100, "share_pct": 30.0, "limit_pct": 20},
     ("hint.R11", {"limit_pct": 20, "needed": 10})),
    ("R11", {"pending": 21, "total": 100, "share_pct": 21.0, "limit_pct": 20},
     ("hint.R11", {"limit_pct": 20, "needed": 1})),
    ("R11", {"pending": 5}, ("hint.R11", {})),
    ("R12", {"rows": 80}, ("hint.R12", {})),
]


@pytest.mark.parametrize("rule,ev,want", CASES)
def test_hint(rule, ev, want):
    assert clear_hint(rule, ev) == want


@pytest.mark.parametrize("rule,ev", [
    ("R99", {"a": 1}), ("", {}), (None, {}), ("R06", None), ("R06", {}),
    ("R06", {"allowed": "x", "excess": None}), ("R02", {"expected_digits": None}),
    ("R10", {"rise_pct": "?"}), ("R04", "junk"), ("R01", None),
])
def test_unknown_or_odd_is_none(rule, ev):
    assert clear_hint(rule, ev) is None


def test_r11_odd_numbers_drop_needed_not_hint():
    assert clear_hint("R11", {"pending": "a", "total": [], "limit_pct": {}}) == ("hint.R11", {})
