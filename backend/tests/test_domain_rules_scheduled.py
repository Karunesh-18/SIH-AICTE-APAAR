from datetime import UTC, datetime, timedelta

import pytest

from app.domain import rules_scheduled as S

CLOSE = datetime(2026, 9, 30, 12, tzinfo=UTC)


def test_r09_only_when_closed_and_nothing_submitted():
    assert S.r09_missing(submitted=False, closed=True, closes_at=CLOSE, params={}) is not None
    assert S.r09_missing(submitted=True, closed=True, closes_at=CLOSE, params={}) is None
    assert S.r09_missing(submitted=False, closed=False, closes_at=CLOSE, params={}) is None


@pytest.mark.parametrize("current,previous,hit", [
    (126, 100, True), (125, 100, False), (80, 100, False), (50, 0, False), (50, None, False)])
def test_r10_jump(current, previous, hit):
    d = S.r10_jump(current, previous, {"jump_pct": 25})
    assert (d is not None) is hit
    if hit:
        assert d.evidence == {"current": current, "previous": previous, "rise_pct": 26.0,
                              "limit_pct": 25}


@pytest.mark.parametrize("pending,total,hit", [(21, 100, True), (20, 100, False), (0, 0, False)])
def test_r11_pending_share(pending, total, hit):
    d = S.r11_pending(pending, total, {"pending_pct": 20})
    assert (d is not None) is hit
    if hit:
        assert d.evidence["share_pct"] == 21.0


def up(hours_before, rows, mix):
    return S.UploadFact(CLOSE - timedelta(hours=hours_before), rows, mix)


P = {"last_hours": 6, "bulk_rows": 50}


def test_r12_bulk_with_one_dominant_category():
    d = S.r12_bulk([up(2, 60, {"OPEN": 55, "OBC": 5})], CLOSE, {}, P)
    assert d.evidence["reason"] == "one_category_above_80pct" and d.evidence["top_category"] == "OPEN"


def test_r12_mix_deviates_from_earlier():
    earlier = {"OPEN": 40, "OBC": 30, "SC": 30}
    d = S.r12_bulk([up(1, 60, {"OPEN": 30, "OBC": 5, "SC": 5, "ST": 20})], CLOSE, earlier, P)
    assert d is not None and d.evidence["reason"] == "mix_deviates_from_earlier"


@pytest.mark.parametrize("facts", [
    [up(2, 49, {"OPEN": 49})],              # too small
    [up(10, 60, {"OPEN": 60})],             # not in the last hours
    [up(2, 60, {"OPEN": 20, "OBC": 20, "SC": 20})],  # even mix
    [],
])
def test_r12_quiet_cases(facts):
    assert S.r12_bulk(facts, CLOSE, {}, P) is None
