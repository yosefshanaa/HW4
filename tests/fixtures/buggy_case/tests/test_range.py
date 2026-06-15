"""Spec for the byte-range parser — pins inclusive-range semantics.

Imports httprange.parser so the extractor records a `tested_by` edge the
debug loop follows to localize the defect. Passes on the fixed parser;
the same assertions fail on parser_buggy (off-by-one).
"""

import pytest
from httprange.parser import parse_byte_range


def test_inclusive_range_length():
    assert parse_byte_range("bytes=0-499", 1000) == (0, 499, 500)


def test_suffix_open_end():
    assert parse_byte_range("bytes=500-", 1000) == (500, 999, 500)


def test_single_byte():
    assert parse_byte_range("bytes=0-0", 1000) == (0, 0, 1)


def test_rejects_unsatisfiable():
    with pytest.raises(ValueError):
        parse_byte_range("bytes=0-2000", 1000)
