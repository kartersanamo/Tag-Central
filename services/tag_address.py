"""Unified tag address extraction from records and row data."""

from __future__ import annotations

from models.tag_record import TagRecord


def extract_address(row_data: dict[str, str]) -> str:
    """Gets address from row data using common key variants."""
    for key in (
        "Address",
        "ADDRESS",
        "address",
        "IOAddress",
        "IOADDRESS",
        "ioaddress",
    ):
        if key in row_data and str(row_data[key]).strip():
            return str(row_data[key]).strip().upper()
    return ""


def record_address(record: TagRecord) -> str:
    if record.linked_address:
        return record.linked_address
    return extract_address(record.proficy_row_data)
