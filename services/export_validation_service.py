"""Validates Proficy export CSV files against expected queue rows."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from services.export_queue_service import export_fields_for_compare


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


class ExportValidationService:
    """Reads export CSV and checks Name/Description/Address fields."""

    def validate_export_file(
        self,
        path: Path,
        expected_rows: list[dict[str, str]],
    ) -> ExportValidationResult:
        result = ExportValidationResult(path=path, expected_count=len(expected_rows))
        if not path.exists():
            result.missing = [row.get("Name", "?") for row in expected_rows]
            return result

        frame = pd.read_csv(path, dtype=str).fillna("")
        loaded: list[dict[str, str]] = []
        for _, series in frame.iterrows():
            row = {str(key): str(value) for key, value in series.items()}
            loaded.append(row)
        result.found_count = len(loaded)

        loaded_by_name: dict[str, deque[dict[str, str]]] = defaultdict(deque)
        for row in loaded:
            name = str(row.get("Name", "")).strip().upper()
            if name:
                loaded_by_name[name].append(row)

        for expected in expected_rows:
            name = str(expected.get("Name", "")).strip().upper()
            if not name:
                continue
            bucket = loaded_by_name.get(name)
            if not bucket:
                result.missing.append(name)
                continue
            actual = bucket.popleft()
            if export_fields_for_compare(actual) != export_fields_for_compare(expected):
                if name not in result.field_mismatches:
                    result.field_mismatches.append(name)
        return result
