from datetime import date

import pytest

from app.domain.rules import (
    ProgrammeInfo,
    RegistryInfo,
    Row,
    r01_missing_id,
    r02_format,
    r03_registry,
    r04_duplicate_in_file,
    r05_two_institutions,
    r06_intake_cap,
    r07_fields,
)


def row(n, apaar="999900000001", **kw):
    base = {"row_number": n, "apaar_id": apaar, "name": "Asha Nair", "dob": date(2003, 1, 1),
            "admission_date": date(2026, 7, 1), "admission_category": "OPEN"}
    base.update(kw)
    return Row(**base)


def test_r01_flags_each_row_without_an_id():
    flags = r01_missing_id([row(1), row(2, None), row(3, None)], {})
    assert [f.row_numbers for f in flags] == [[2], [3]]
    assert all(f.rule == "R01" and f.reason_key == "id_missing" for f in flags)


@pytest.mark.parametrize("apaar,flagged", [("99990000004", True), ("9999000000AB", True),
                                           ("999900000041", False), (None, False)])
def test_r02_flags_only_present_ids_with_bad_format(apaar, flagged):
    flags = r02_format([row(7, apaar)], {"digits": 12, "checksum": "none"})
    assert bool(flags) is flagged
    if flagged:
        assert flags[0].row_numbers == [7]
        assert flags[0].evidence["expected_digits"] == 12
        assert flags[0].evidence["found"] == apaar


def test_r04_one_flag_per_repeated_id_listing_every_row():
    rows = [row(41, "999900000041"), row(97, "999900000041", admission_date=date(2026, 7, 21)),
            row(5, "999900000005"), row(6, None), row(7, None)]
    flags = r04_duplicate_in_file(rows, {})
    assert len(flags) == 1
    assert flags[0].row_numbers == [41, 97] and flags[0].evidence["count"] == 2


def test_r06_cap_flags_the_last_rows_by_admission_date_and_says_it_is_only_ordering():
    prog = ProgrammeInfo(approved_intake=3, supernumerary_seats=1)
    rows = [row(i, f"99990000000{i}", admission_date=date(2026, 7, i)) for i in range(1, 7)]
    rows.reverse()  # file order must not matter
    (flag,) = r06_intake_cap(rows, prog, {})
    assert flag.row_numbers == [5, 6]
    assert flag.evidence == {"approved_intake": 3, "supernumerary_seats": 1, "allowed": 4,
                             "actual": 6, "excess": 2, "ordering_only": True}


def test_r06_ties_on_date_break_by_row_number_and_exact_cap_is_fine():
    prog = ProgrammeInfo(approved_intake=2, supernumerary_seats=0)
    same = [row(i, f"99990000000{i}") for i in (1, 2, 3)]
    assert r06_intake_cap(same, prog, {})[0].row_numbers == [3]
    assert r06_intake_cap(same[:2], prog, {}) == []


def test_r07_missing_mandatory_fields_and_contradictions():
    cycle = 2026
    cases = {
        "name_missing": row(1, name=""),
        "dob_missing": row(2, dob=None),
        "admission_date_missing": row(3, admission_date=None),
        "category_missing": row(4, admission_category=""),
        "admission_after_cycle": row(5, admission_date=date(2027, 7, 12)),
        "dob_after_admission": row(6, dob=date(2026, 8, 1)),
    }
    flags = r07_fields(list(cases.values()), cycle, {})
    got = {f.row_numbers[0]: f.reason_key for f in flags}
    assert got == {i + 1: k for i, k in enumerate(cases)}
    assert r07_fields([row(1)], cycle, {}) == []


def test_r03_not_found_and_mismatches_against_the_registry():
    reg = {"999900000001": RegistryInfo("Asha Nair", date(2003, 1, 1)),
           "999900000002": RegistryInfo("Completely Different", date(2003, 1, 1)),
           "999900000003": RegistryInfo("Asha Nair", date(1999, 5, 5))}
    rows = [row(1, "999900000001"), row(2, "999900000002"), row(3, "999900000003"),
            row(4, "999900000009"), row(5, None), row(6, "123")]
    flags = r03_registry(rows, {"name_threshold": 0.8}, reg.get)
    got = {f.row_numbers[0]: f.reason_key for f in flags}
    assert got == {2: "registry_name_differs", 3: "registry_dob_differs", 4: "registry_not_found"}
    assert next(f for f in flags if f.row_numbers == [2]).evidence["similarity"] < 0.8


def test_r03_small_spelling_differences_pass():
    reg = {"999900000001": RegistryInfo("Asha  Nair", date(2003, 1, 1))}
    assert r03_registry([row(1, name="asha nair")], {"name_threshold": 0.8}, reg.get) == []


def test_r05_same_id_active_at_another_institution():
    others = {"999900000012": [{"institution": "Kaveri Valley College", "programme": "MBA",
                                "admission_date": "2026-07-05"}]}
    flags = r05_two_institutions([row(5, "999900000012"), row(6, "999900000013")], others)
    assert len(flags) == 1 and flags[0].row_numbers == [5]
    assert flags[0].evidence["elsewhere"] == others["999900000012"]
