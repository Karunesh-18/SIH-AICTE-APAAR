from datetime import UTC, datetime, timedelta

import pytest

from app.domain.ladder import DEFAULT_LADDER, plan

CLOSE = datetime(2026, 9, 30, tzinfo=UTC)


def at(**kw):
    return CLOSE + timedelta(**kw)


@pytest.mark.parametrize("now,fire,skipped", [
    (at(days=-40), {}, []),
    (at(days=-30), {"institution": "T-30d"}, []),
    (at(days=-20), {"institution": "T-30d"}, []),
    # the clock jumped: only the latest due institution step is sent, earlier ones are skipped
    (at(days=-6), {"institution": "T-7d"}, ["T-30d", "T-14d"]),
    (at(days=0), {"institution": "T0"}, ["T-30d", "T-14d", "T-7d"]),
    (at(days=4), {"institution": "T0", "officer": "T+3d"}, ["T-30d", "T-14d", "T-7d"]),
    (at(days=11), {"institution": "T0", "officer": "T+3d", "admin": "T+10d"},
     ["T-30d", "T-14d", "T-7d"]),
])
def test_only_latest_due_step_per_audience_fires(now, fire, skipped):
    p = plan(DEFAULT_LADDER, CLOSE, now, already=set())
    assert {s["audience"]: s["step"] for s in p.fire} == fire
    assert sorted(s["step"] for s in p.skip) == sorted(skipped)


def test_logged_steps_are_not_planned_again():
    p = plan(DEFAULT_LADDER, CLOSE, at(days=-6), already={"T-30d", "T-14d", "T-7d"})
    assert p.fire == [] and p.skip == []


def test_new_due_step_after_earlier_ones_were_logged():
    p = plan(DEFAULT_LADDER, CLOSE, at(days=0), already={"T-30d", "T-14d", "T-7d"})
    assert [s["step"] for s in p.fire] == ["T0"] and p.skip == []
