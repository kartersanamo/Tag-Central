"""Proficy export file validation result."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExportValidationResult:
    """Outcome of comparing an export file to expected rows."""

    path: Path
    expected_count: int = 0
    found_count: int = 0
    missing: list[str] = field(default_factory=list)
    field_mismatches: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.field_mismatches
