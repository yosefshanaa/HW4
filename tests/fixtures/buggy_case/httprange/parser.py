"""HTTP byte-range parser — FIXED version (debug-case target).

The companion `parser_buggy.py` is the pre-fix state kept for the
before/after demonstration; this module is the verified fix.
"""

from __future__ import annotations


def parse_byte_range(header: str, resource_length: int) -> tuple[int, int, int]:
    """Parse one ``bytes=start-end`` range into (start, end, content_length).

    HTTP byte ranges are INCLUSIVE of ``end`` (RFC 9110 §14.1.2): bytes
    ``0-499`` of a 1000-byte resource is 500 bytes. An open end
    (``bytes=500-``) runs to the last byte.
    """
    if not header.startswith("bytes="):
        raise ValueError(f"unsupported range unit: {header!r}")
    start_text, _, end_text = header[len("bytes="):].partition("-")
    start = int(start_text)
    end = int(end_text) if end_text else resource_length - 1
    if start < 0 or end >= resource_length or start > end:
        raise ValueError(f"unsatisfiable range {header!r} for length {resource_length}")
    content_length = end - start + 1  # inclusive range — the fix
    return start, end, content_length
