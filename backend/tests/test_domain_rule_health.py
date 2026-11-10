from datetime import UTC, datetime, timedelta

import pytest

from app.domain.rule_health import summarise

NOW = datetime(2026, 6, 30, tzinfo=UTC)


def d(n):
    return NOW - timedelta(days=n)


def f(state, raised=10, closed=None):
    return ("R01", state, d(raised), d(closed) if closed is not None else None)


ZERO = {"code": "R01", "raised": 0, "open": 0, "under_review": 0, "resolved": 0, "dismissed": 0,
        "dismissed_share": None, "median_days_to_close": None, "oldest_open_days": None}


def one(flags):
    return summarise(["R01"], flags, NOW)[0]


@pytest.mark.parametrize("flags,expect", [
    ([], {}),
    ([f("open", 5), f("open", 9)],
     {"raised": 2, "open": 2, "oldest_open_days": 9}),
    ([f("open", 4), f("under_review", 8), f("resolved", 10, 6), f("dismissed", 10, 8),
      f("dismissed", 10, 7)],
     {"raised": 5, "open": 1, "under_review": 1, "resolved": 1, "dismissed": 2,
      "dismissed_share": 2 / 3, "median_days_to_close": 3.0, "oldest_open_days": 8}),
    ([f("resolved", 10, 8), f("dismissed", 10, 4)],  # closed after 2 and 6 days: even median 4
     {"raised": 2, "resolved": 1, "dismissed": 1, "dismissed_share": 0.5,
      "median_days_to_close": 4.0}),
    ([f("ask_institution", 3)],  # waiting on the institution counts as open and unclosed
     {"raised": 1, "open": 1, "oldest_open_days": 3}),
])
def test_summarise(flags, expect):
    assert one(flags) == ZERO | expect


def test_unflagged_rules_appear_with_zeros_and_unknown_codes_are_ignored():
    out = summarise(["R01", "R02"], [("R99", "open", d(1), None)], NOW)
    assert [r["code"] for r in out] == ["R01", "R02"]
    assert out[1] == ZERO | {"code": "R02"}
