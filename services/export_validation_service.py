"""Validates Proficy export CSV files against expected queue rows."""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path

from models.export_validation_result import ExportValidationResult
from services.export_queue_service import export_fields_for_compare
from services.pandas_lazy import get_pandas


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
            expected_by_name[name].append(row)

        for _, csv_row in frame.iterrows():
            name = str(csv_row.get("Name", "")).strip().upper()
            if name not in expected_by_name or not expected_by_name[name]:
                continue
            expected = expected_by_name[name].popleft()
            expected_fields = export_fields_for_compare(expected)
            actual_fields = export_fields_for_compare(dict(csv_row))
            for field_name, expected_value in expected_fields.items():
                if actual_fields.get(field_name, "") != expected_value:
                    result.field_mismatches.append(
                        f"{name}: {field_name} expected {expected_value!r}, "
                        f"found {actual_fields.get(field_name, '')!r}"
                    )

        for name, remaining in expected_by_name.items():
            result.missing.extend([name] * len(remaining))

        return result
