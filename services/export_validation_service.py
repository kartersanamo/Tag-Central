"""Validates Proficy export CSV files against expected queue rows."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

from services.export_queue_service import export_fields_for_compare
from services.pandas_lazy import get_pandas


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
        pd = get_pandas()
        result = ExportValidationResult(path=path, expected_count=len(expected_rows))
        if not path.exists():
            result.missing = [row.get("Name", "?") for row in expected_rows]
            return result

        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        result.found_count = len(frame)

        expected_by_name: dict[str, deque[dict[str, str]]] = defaultdict(deque)
        for row in expected_rows:
            name = str(row.get("Name", "")).strip().upper()
            if name:
                expected_by_name[name].append(row)

        for _, series in frame.iterrows():
            row = {
                key: ("" if pd.isna(value) else str(value).strip())
                for key, value in series.to_dict().items()
            }
            name = str(row.get("Name", "")).strip().upper()
            if not name:
                continue
            queue = expected_by_name.get(name)
            if not queue:
                if name not in result.missing:
                    result.missing.append(name)
                continue
            expected = queue.popleft()
            if export_fields_for_compare(row) != export_fields_for_compare(expected):
                if name not in result.field_mismatches:
                    result.field_mismatches.append(name)

        for name, queue in expected_by_name.items():
            for _ in queue:
                if name not in result.missing:
                    result.missing.append(name)

        return result
