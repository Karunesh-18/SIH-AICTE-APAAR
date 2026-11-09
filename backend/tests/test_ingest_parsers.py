"""Parsing and format sniffing. Pure bytes in, rows out; nothing touches the database."""
import io
import json
from datetime import date

import openpyxl
import pytest

from app.services import ingest
from tests.ingest_helpers import COLS, csv_bytes, row


def test_csv_basic_row_numbers_start_at_one():
    rows = ingest.parse(csv_bytes([row(1), row(2)]))
    assert [r.row_number for r in rows] == [1, 2]
    assert rows[0].apaar_id == "999900000001" and rows[0].dob == date(2001, 3, 4)


def test_csv_with_bom_is_read():
    rows = ingest.parse(csv_bytes([row(1)], bom=True))
    assert rows[0].name == "Student 1"


def test_trailing_spaces_and_id_separators_are_cleaned():
    rows = ingest.parse(csv_bytes([row(1, apaar_id=" 9999 0000-0001 ", name="Asha Rao  ")]))
    assert rows[0].apaar_id == "999900000001" and rows[0].name == "Asha Rao"


def test_devanagari_name_survives():
    rows = ingest.parse(csv_bytes([row(1, name="अनिका शर्मा")], bom=True))
    assert rows[0].name == "अनिका शर्मा"


@pytest.mark.parametrize("text,expected", [
    ("04/03/2001", date(2001, 3, 4)), ("04-03-2001", date(2001, 3, 4)),
    ("2001-03-04", date(2001, 3, 4)), ("31/12/2000", date(2000, 12, 31)),
    ("04.03.2001", date(2001, 3, 4)), ("", None), ("not a date", None),
])
def test_dates_are_day_first_or_iso(text, expected):
    assert ingest.parse(csv_bytes([row(1, dob=text)]))[0].dob == expected


def test_aliases_and_extra_columns_and_programme_optional():
    data = (b"APAAR ID,Student Name,Date of Birth,Date of Admission,Category,Foreign National,"
            b"Hobby\n999900000001,A B,01/02/2000,01/07/2026,OBC,yes,chess\n")
    r = ingest.parse(data)[0]
    assert (r.name, r.dob, r.admission_date, r.admission_category, r.fn) == (
        "A B", date(2000, 2, 1), date(2026, 7, 1), "OBC", True)
    assert r.programme is None and r.nri is False and r.year_of_study == 1


def test_flags_and_year_of_study_parse():
    data = "apaar_id,name,dob,admission_date,admission_category,nri,oci,fn,year_of_study\n" \
           "999900000001,A,2000-01-01,2026-07-01,OPEN,Y,0,true,2\n"
    r = ingest.parse(data.encode())[0]
    assert (r.nri, r.oci, r.fn, r.year_of_study) == (True, False, True, 2)


def test_blank_lines_are_skipped_not_counted():
    data = csv_bytes([row(1)]) + b",,,,\n" + csv_bytes([row(2)]).split(b"\n", 1)[1]
    assert [r.row_number for r in ingest.parse(data)] == [1, 2]


@pytest.mark.parametrize("data,words", [
    (b"", "empty"),
    (b"   \n\n", "empty"),
    (b"\x00\x01\x02\xff\xfe binary rubbish", "read"),
    (b"apaar_id,name\n1,a\n", "missing"),
    (csv_bytes([]), "no data rows"),
])
def test_unusable_files_raise_with_a_clear_message(data, words):
    with pytest.raises(ingest.IngestError) as e:
        ingest.parse(data)
    assert words in str(e.value).lower()


def test_missing_columns_are_named():
    with pytest.raises(ingest.IngestError) as e:
        ingest.parse(b"apaar_id,name\n1,a\n")
    assert "dob" in str(e.value) and "admission_date" in str(e.value)


def _xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COLS)
    for r in rows:
        ws.append([r[c] for c in COLS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_xlsx_with_real_dates_and_numeric_id():
    data = _xlsx([row(1, apaar_id=999900000001, dob=date(2001, 3, 4),
                      admission_date=date(2026, 7, 1))])
    assert ingest.sniff_format(data) == "xlsx"
    r = ingest.parse(data)[0]
    assert (r.apaar_id, r.dob, r.admission_date) == ("999900000001", date(2001, 3, 4),
                                                     date(2026, 7, 1))


def test_xlsx_text_dates_are_day_first():
    assert ingest.parse(_xlsx([row(1, dob="04/03/2001")]))[0].dob == date(2001, 3, 4)


def test_legacy_xls():
    xlwt = pytest.importorskip("xlwt")
    wb = xlwt.Workbook()
    ws = wb.add_sheet("s")
    for c, h in enumerate(COLS):
        ws.write(0, c, h)
    style = xlwt.easyxf(num_format_str="DD/MM/YYYY")
    ws.write(1, 0, "999900000001")
    ws.write(1, 1, "Xls Student")
    ws.write(1, 2, date(2001, 3, 4), style)
    ws.write(1, 3, "01/07/2026")
    ws.write(1, 4, "OPEN")
    buf = io.BytesIO()
    wb.save(buf)
    assert ingest.sniff_format(buf.getvalue()) == "xls"
    r = ingest.parse(buf.getvalue())[0]
    assert (r.name, r.dob, r.admission_date) == ("Xls Student", date(2001, 3, 4), date(2026, 7, 1))


def test_json_list_and_wrapped_object():
    rows = [row(1), row(2)]
    assert len(ingest.parse(json.dumps(rows).encode())) == 2
    assert len(ingest.parse(json.dumps({"students": rows}).encode())) == 2
    assert ingest.sniff_format(b'{"students": []}') == "json"


def test_json_garbage_is_rejected():
    with pytest.raises(ingest.IngestError):
        ingest.parse(b'{"students": 5}')
    with pytest.raises(ingest.IngestError):
        ingest.parse(b"[1, 2")


def test_sniff_prefers_content_over_nothing():
    assert ingest.sniff_format(csv_bytes([row(1)])) == "csv"


def test_templates_round_trip_through_the_parser():
    for data in (ingest.template_csv(), ingest.template_xlsx()):
        rows = ingest.parse(data)
        assert len(rows) == 1 and rows[0].apaar_id.startswith("9999")
