"""Normalizes PLC IO addresses for cross-program matching."""

from __future__ import annotations

import re

_GMR_PATTERN = re.compile(r"^%([GMR])(\d+)$", re.IGNORECASE)
_AI_PATTERN = re.compile(r"^%AI(\d+)$", re.IGNORECASE)


def normalize_address(address: str) -> str:
    """
    Normalizes addresses so Proficy %G00479 and Cimplicity %G0479 compare equal.
    """
    cleaned = address.strip().upper()
    if not cleaned:
        return ""

    ai_match = _AI_PATTERN.match(cleaned)
    if ai_match:
        return f"%AI{int(ai_match.group(1))}"

    gmr_match = _GMR_PATTERN.match(cleaned)
    if gmr_match:
        kind = gmr_match.group(1).upper()
        number = int(gmr_match.group(2))
        return f"%{kind}{number:05d}"

    if cleaned.startswith("%"):
        return cleaned
    return cleaned


def addresses_equivalent(left: str, right: str) -> bool:
    """Returns True when two addresses normalize to the same value."""
    left_norm = normalize_address(left)
    right_norm = normalize_address(right)
    return bool(left_norm) and left_norm == right_norm
