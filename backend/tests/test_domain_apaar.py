import pytest

from app.domain.apaar import check_format, mask, normalize, verhoeff_ok


@pytest.mark.parametrize("raw,expected", [
    ("9999 0000 0041", "999900000041"),
    ("9999-0000-0041", "999900000041"),
    ("  9999 0000 0041 ", "999900000041"),
    ("", None), ("   ", None), (None, None),
])
def test_normalize_strips_spaces_hyphens_and_blanks(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize("value,ok", [
    ("999900000041", True),
    ("99990000004", False),       # 11 digits
    ("9999000000411", False),     # 13 digits
    ("9999000000AB", False),
    ("९९९९०००००००१", False),       # Devanagari digits are not accepted
    ("", False),
])
def test_check_format_requires_twelve_ascii_digits(value, ok):
    assert check_format(value) is ok


def test_check_format_digits_is_a_parameter():
    assert check_format("12345678", digits=8)


def test_verhoeff_known_values():
    assert verhoeff_ok("2363")        # 236 + check digit 3
    assert not verhoeff_ok("2364")


def test_check_format_with_verhoeff_checksum():
    # 11 digits + the Verhoeff check digit of those 11
    from app.domain.apaar import verhoeff_digit
    body = "99990000004"
    full = body + str(verhoeff_digit(body))
    assert check_format(full, checksum="verhoeff")
    bad = body + str((verhoeff_digit(body) + 1) % 10)
    assert not check_format(bad, checksum="verhoeff")
    assert check_format(bad, checksum="none")


@pytest.mark.parametrize("value,masked", [
    ("999900000041", "XXXX XXXX 0041"),
    ("99990000004", "XXXXXXX0004"),
    ("123", "XXX"),
    (None, None),
])
def test_mask_shows_only_last_four(value, masked):
    assert mask(value) == masked
