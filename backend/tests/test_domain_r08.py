"""Shared name similarity and the R08 near-duplicate rule (pure functions)."""
from datetime import date

import pytest

from app.domain.rules import Person, r08_near_duplicate
from app.domain.similarity import similarity

DOB = date(2003, 5, 6)


def p(ref, name, apaar, row=None, dob=DOB, inst="i1"):
    return Person(ref=ref, apaar_id=apaar, name=name, dob=dob, row_number=row,
                  institution_id=inst, institution=f"Inst {inst}")


@pytest.mark.parametrize("a,b,lo,hi", [
    ("Priyanka Deshmukh", "Priyanka Deshmuk", 0.85, 1.0),
    ("Priyanka Deshmukh", "  priyanka   DESHMUKH ", 1.0, 1.0),
    ("Asha Nair", "Ravi Kumar", 0.0, 0.2),
    ("Aarav Nair", "Aarav Menon", 0.0, 0.5),
    ("", "Asha", 0.0, 0.0),
    ("A", "B", 0.0, 0.0),
])
def test_similarity_scores(a, b, lo, hi):
    assert lo <= similarity(a, b) <= hi


def test_similarity_is_symmetric():
    assert similarity("Asha Nair", "Asha Nayar") == pytest.approx(similarity("Asha Nayar", "Asha Nair"))


def test_pair_with_same_dob_and_similar_name_flags_once_with_numbers():
    out = r08_near_duplicate([p("a", "Priyanka Deshmukh", "999900000001", 9),
                              p("b", "Priyanka Deshmuk", "999900000002", 10)], {"threshold": 0.85})
    assert len(out) == 1
    d = out[0]
    assert d.rule == "R08" and d.row_numbers == [9, 10]
    assert d.evidence["threshold"] == 0.85 and d.evidence["score"] >= 0.85
    assert d.evidence["a"]["apaar_id"] == "XXXX XXXX 0001"
    assert d.evidence["b"]["apaar_id"] == "XXXX XXXX 0002"
    assert d.evidence["a"]["name"] == "Priyanka Deshmukh"


def test_other_institution_record_is_evidence_only():
    out = r08_near_duplicate([p("a", "Priyanka Deshmukh", "999900000001", 3),
                              p("z", "Priyanka Deshmuk", None, None, inst="i2")], {"threshold": 0.85})
    assert len(out) == 1 and out[0].row_numbers == [3]
    assert out[0].evidence["b"]["apaar_id"] is None and out[0].evidence["b"]["institution_id"] == "i2"


@pytest.mark.parametrize("b", [
    p("b", "Priyanka Deshmuk", "999900000001", 2),            # same ID: not R08's business
    p("b", "Priyanka Deshmuk", "999900000002", 2, dob=date(2003, 5, 7)),  # other dob
    p("b", "Rahul Verma", "999900000002", 2),                 # different name
])
def test_no_flag(b):
    assert r08_near_duplicate([p("a", "Priyanka Deshmukh", "999900000001", 1), b],
                              {"threshold": 0.85}) == []


def test_two_stored_records_never_flag_each_other():
    # neither belongs to this upload: nothing new to say
    assert r08_near_duplicate([p("a", "Priyanka Deshmukh", "999900000001"),
                               p("b", "Priyanka Deshmuk", "999900000002")], {"threshold": 0.85}) == []


def test_missing_ids_on_both_sides_still_flag():
    assert len(r08_near_duplicate([p("a", "Priyanka Deshmukh", None, 1),
                                   p("b", "Priyanka Deshmuk", None, 2)], {"threshold": 0.85})) == 1
