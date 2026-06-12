"""Cimplicity import row and sync action models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CimplicityImportRow:
    """Prepared Cimplicity import row for sync processing."""

    pt_id: str
    description: str
    address: str
    row_data: dict[str, str]
    row_index: int


@dataclass
class CimplicitySyncAction:
    """One row requiring user decision during Cimplicity import."""

    row_index: int
    pt_id: str
    cimplicity_description: str
    address: str
    row_data: dict[str, str]
    existing_tag: str
    existing_description: str
    proficy_name: str
    issue: str
    default_action: str = "align_proficy"


@dataclass
class CimplicityImportSummary:
    """Aggregated results from a Cimplicity import pass."""

    total_rows: int = 0
    linked_synced: int = 0
    auto_aligned: int = 0
    review_queue_added: int = 0
    skipped: int = 0
    proficy_exports_queued: int = 0
    manual_cimplicity_flags: int = 0
    actionable: list[CimplicitySyncAction] = field(default_factory=list)
    matched_exact_id: int = 0
    matched_cimplicity_pt_id: int = 0
    matched_address: int = 0
    matched_alias: int = 0
    ambiguous_address: int = 0
    unmatched: int = 0
    report_lines: list[str] = field(default_factory=list)
