"""HTTP byte-range parser — BUGGY version (the planted defect, "before").

Identical to parser.py except the content-length computation treats the
range as end-EXCLUSIVE, dropping the last byte of every range. Kept for the
before/after demonstration in results/BUG_ANALYSIS.md.
"""

from __future__ import annotations


def parse_byte_range(header: str, resource_length: int) -> tuple[int, int, int]:
    """Same contract as the fixed parser — but with the off-by-one bug."""
    if not header.startswith("bytes="):
        raise ValueError(f"unsupported range unit: {header!r}")
    start_text, _, end_text = header[len("bytes="):].partition("-")
    start = int(start_text)
    end = int(end_text) if end_text else resource_length - 1
    if start < 0 or end >= resource_length or start > end:
        raise ValueError(f"unsatisfiable range {header!r} for length {resource_length}")
    content_length = end - start  # BUG: inclusive range needs +1; drops the last byte
    return start, end, content_length
