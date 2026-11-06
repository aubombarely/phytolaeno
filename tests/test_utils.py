"""Unit tests for the string parsers in app.utils."""
from app.utils import (extract_tool_info, parse_busco, parse_earlgrey,
                       safe_float, safe_int)


def test_parse_busco_full_string():
    assert parse_busco("C:98.1%[S:76.0%,D:22.1%],F:1.2%,M:0.7%") == {
        "complete": 98.1, "single": 76.0, "duplicated": 22.1,
        "fragmented": 1.2, "missing": 0.7,
    }


def test_parse_busco_empty_or_malformed():
    assert parse_busco("") == {}
    assert parse_busco("nan") == {}
    assert parse_busco("not a busco string") == {}


def test_parse_earlgrey():
    assert parse_earlgrey("DNA:7.80%;RC:2.32%;LTR:34.86%") == {
        "DNA": 7.80, "RC": 2.32, "LTR": 34.86,
    }
    assert parse_earlgrey("") == {}
    assert parse_earlgrey("DNA:abc%;LTR:1%") == {"LTR": 1.0}


def test_extract_tool_info():
    assert extract_tool_info("AbI: BRAKER3 v3.0.8 with RNA-seq") == ("BRAKER3", "3.0.8")
    assert extract_tool_info("AbI: Helixer") == ("Helixer", "")
    assert extract_tool_info("") == ("Unknown", "")


def test_safe_converters():
    assert safe_float("1.5") == 1.5
    assert safe_float("nan") is None
    assert safe_float(None) is None
    assert safe_int("3.0") == 3
    assert safe_int("x") is None
