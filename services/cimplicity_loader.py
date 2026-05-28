"""Cimplicity Shared Name File import utilities."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from services.address_normalizer import normalize_address


class CimplicityLoader:
    """Loads Cimplicity 6.x Shared Name File CSV exports."""

    REQUIRED_COLUMNS = {"PT_ID", "DESC"}

    def load_rows(self, file_path: str) -> list[dict[str, str]]:
        """Loads Cimplicity rows, skipping comment header lines."""
        path = Path(file_path)
        if path.suffix.lower() != ".csv":
            raise ValueError("Cimplicity imports must be .csv Shared Name Files.")

        raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        data_lines = [line for line in raw_lines if not line.startswith("##")]
        if not data_lines:
            raise ValueError("Cimplicity file has no data rows.")

        reader = csv.DictReader(StringIO("\n".join(data_lines)))
        if reader.fieldnames is None:
            raise ValueError("Cimplicity file has no column headers.")

        columns = [str(column).strip() for column in reader.fieldnames]
        self._validate_schema(columns)

        rows: list[dict[str, str]] = []
        for row in reader:
            normalized = {
                str(key).strip(): str(value).strip()
                for key, value in row.items()
                if key is not None
            }
            pt_id = normalized.get("PT_ID", "").strip().upper()
            if not pt_id:
                continue
            normalized["PT_ID"] = pt_id
            if "ADDR" in normalized:
                normalized["ADDR"] = normalize_address(normalized["ADDR"])
            rows.append(normalized)
        return rows

    def _validate_schema(self, columns: list[str]) -> None:
        missing = self.REQUIRED_COLUMNS - set(columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(
                "Cimplicity file is missing required columns: "
                f"{missing_text}. Required: PT_ID, DESC."
            )
