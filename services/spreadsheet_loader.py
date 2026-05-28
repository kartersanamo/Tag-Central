"""Spreadsheet import utilities."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from services.pandas_lazy import get_pandas


class SpreadsheetLoader:
    """Loads and normalizes spreadsheet rows for import."""

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
    REQUIRED_COLUMNS = {"Name", "Description"}

    def load_rows(self, file_path: str) -> list[dict[str, str]]:
        """Loads spreadsheet rows as normalized dictionaries."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {extension}")

        if extension == ".csv":
            return self._load_csv_rows(path)
        return self._load_excel_rows(path)

    def _load_csv_rows(self, path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise ValueError("Spreadsheet has no columns.")
            columns = [str(column).strip() for column in reader.fieldnames]
            self._validate_schema(columns)
            return [self._normalize_row(dict(row)) for row in reader]

    def _load_excel_rows(self, path: Path) -> list[dict[str, str]]:
        pd = get_pandas()
        frame = pd.read_excel(path, dtype=str)
        frame.columns = frame.columns.str.strip()
        self._validate_schema([str(column).strip() for column in frame.columns.tolist()])
        return [self._normalize_row(row) for _, row in frame.iterrows()]

    def _validate_schema(self, columns: list[str]) -> None:
        if not columns:
            raise ValueError("Spreadsheet has no columns.")

        empty_headers = [column for column in columns if not column]
        if empty_headers:
            raise ValueError("Spreadsheet contains empty column headers.")

        lower_columns = [column.lower() for column in columns]
        duplicate_headers = {
            column for column in lower_columns if lower_columns.count(column) > 1
        }
        if duplicate_headers:
            duplicates = ", ".join(sorted(duplicate_headers))
            raise ValueError(f"Spreadsheet has duplicate headers: {duplicates}")

        missing_columns = self.REQUIRED_COLUMNS - set(columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(
                "Spreadsheet is missing required columns: "
                f"{missing}. Required columns are Name and Description."
            )

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            column = str(key).strip()
            if value is None:
                normalized[column] = ""
            elif isinstance(value, str):
                normalized[column] = value.strip()
            else:
                pd = get_pandas()
                normalized[column] = (
                    "" if pd.isna(value) else str(value).strip()
                )
        return normalized
