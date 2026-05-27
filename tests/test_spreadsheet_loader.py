"""Tests for spreadsheet loader schema validation."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from services.spreadsheet_loader import SpreadsheetLoader


class TestSpreadsheetLoader(unittest.TestCase):
    """Validates schema checks and row normalization."""

    def setUp(self) -> None:
        self.loader = SpreadsheetLoader()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_rows_rejects_missing_required_columns(self) -> None:
        csv_path = self.base_path / "missing.csv"
        frame = pd.DataFrame([{"Name": "A100", "Info": "X"}])
        frame.to_csv(csv_path, index=False)

        with self.assertRaises(ValueError):
            self.loader.load_rows(str(csv_path))

    def test_load_rows_rejects_duplicate_headers_case_insensitive(self) -> None:
        csv_path = self.base_path / "duplicate_headers.csv"
        csv_path.write_text("Name,Description,name\nA100,Main,Alt\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            self.loader.load_rows(str(csv_path))

    def test_load_rows_normalizes_whitespace_and_nulls(self) -> None:
        csv_path = self.base_path / "valid.csv"
        frame = pd.DataFrame(
            [{"Name": "  A100  ", "Description": " Main Pump ", "Extra": None}]
        )
        frame.to_csv(csv_path, index=False)

        rows = self.loader.load_rows(str(csv_path))
        self.assertEqual(rows[0]["Name"], "A100")
        self.assertEqual(rows[0]["Description"], "Main Pump")
        self.assertEqual(rows[0]["Extra"], "")


if __name__ == "__main__":
    unittest.main()
