"""Proficy import dry-run analysis."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProficyImportAnalysis:
    """Dry-run summary for a Proficy import."""

    total_rows: int = 0
    rows_missing_name: int = 0
    rows_missing_description: int = 0
    new_tags: int = 0
    updated_unchanged: int = 0
    updated_with_export: int = 0
    conflicts: int = 0
    estimated_export_rows: int = 0
    lines: list[str] = field(default_factory=list)
