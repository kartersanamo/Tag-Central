"""Spreadsheet import utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


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

        if extension in {".xlsx", ".xls"}:
            frame = pd.read_excel(path, dtype=str)
        else:
            frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str)

        frame.columns = frame.columns.str.strip()
        self._validate_schema(frame)
        return [self._normalize_row(row) for _, row in frame.iterrows()]

    def _validate_schema(self, frame: pd.DataFrame) -> None:
        columns = [str(column).strip() for column in frame.columns.tolist()]

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
    def _normalize_row(row: pd.Series) -> dict[str, str]:
        return {
            key: ("" if pd.isna(value) else str(value).strip())
            for key, value in row.to_dict().items()
        }
