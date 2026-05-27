"""Spreadsheet import utilities."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class SpreadsheetLoader:
    """Loads and normalizes spreadsheet rows for import."""

    SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

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
        return [self._normalize_row(row) for _, row in frame.iterrows()]

    @staticmethod
    def _normalize_row(row: pd.Series) -> dict[str, str]:
        return {
            key: ("" if pd.isna(value) else str(value).strip())
            for key, value in row.to_dict().items()
        }
