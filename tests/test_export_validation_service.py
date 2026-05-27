"""Tests for export file validation."""

import csv
import tempfile
import unittest
from pathlib import Path

from services.export_validation_service import ExportValidationService


class TestExportValidationService(unittest.TestCase):
    def test_duplicate_names_in_file_match_in_order(self) -> None:
        service = ExportValidationService()
        expected = [
            {
                "Name": "AFT_DRAFT_SETPOINT",
                "Description": "AFT DRAFT SETPOINT",
                "IOAddress": "%R00113",
            },
            {
                "Name": "AFT_DRAFT_SETPOINT",
                "Description": "FWD DRAFT OFFSET SET POINT",
                "IOAddress": "%R00113",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "C-LEGACY_BATCH_EXPORT.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["Name", "Description", "IOAddress"],
                )
                writer.writeheader()
                writer.writerows(expected)

            result = service.validate_export_file(path, expected)
            self.assertTrue(result.ok)
            self.assertEqual(result.expected_count, 2)
            self.assertEqual(result.found_count, 2)


if __name__ == "__main__":
    unittest.main()
