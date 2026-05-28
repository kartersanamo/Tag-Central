"""Normalizes PLC IO addresses for cross-program matching."""

from __future__ import annotations

import re

_GMR_PATTERN = re.compile(r"^%([GMR])(\d+)$", re.IGNORECASE)
_AI_PATTERN = re.compile(r"^%AI(\d+)$", re.IGNORECASE)
_PLACEHOLDER_ADDRESSES = frozenset({"<SYMBOLIC>", "SYMBOLIC"})


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


def is_resolvable_address(address: str) -> bool:
    """
    Returns True when an address is a real PLC reference.

    Proficy array table elements often use ``<Symbolic>`` as a placeholder; those
    must not participate in address linking or mismatch grouping.
    """
    normalized = normalize_address(address)
    if not normalized:
        return False
    if normalized in _PLACEHOLDER_ADDRESSES:
        return False
    if normalized.startswith("<") and normalized.endswith(">"):
        return False
    return True


def addresses_equivalent(left: str, right: str) -> bool:
    """Returns True when two addresses normalize to the same value."""
    left_norm = normalize_address(left)
    right_norm = normalize_address(right)
    if not is_resolvable_address(left_norm) or not is_resolvable_address(right_norm):
        return False
    return left_norm == right_norm
