"""Tests for export file writer behavior."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from services.export_service import ExportService


class TestExportService(unittest.TestCase):
    """Validates output format for vessel batch exports."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.export_dir = Path(self.temp_dir.name) / "exports"
        self.service = ExportService(self.export_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_export_rows_do_not_include_old_or_new_tag_columns(self) -> None:
        exports = {
            "NANUQ": [
                {
                    "row": {
                        "Name": "BS_1P_TANK_GRAVITY",
                        "Description": "BALLAST #1-P TANK GRAVITY",
                        "Unit": "SG",
                    }
                }
            ]
        }

        written = self.service.write_exports(exports)
        self.assertEqual(len(written), 1)

        frame = pd.read_csv(written[0], dtype=str).fillna("")
        self.assertIn("Name", frame.columns)
        self.assertIn("Description", frame.columns)
        self.assertIn("Unit", frame.columns)
        self.assertNotIn("old_tag", frame.columns)
        self.assertNotIn("new_tag", frame.columns)

    def test_export_writes_one_file_per_vessel(self) -> None:
        exports = {
            "A": [{"row": {"Name": "A1", "Description": "A DESC"}}],
            "B": [{"row": {"Name": "B1", "Description": "B DESC"}}],
        }

        written = self.service.write_exports(exports)
        names = sorted(path.name for path in written)
        self.assertEqual(names, ["A_BATCH_EXPORT.csv", "B_BATCH_EXPORT.csv"])

    def test_export_never_overwrites_existing_file(self) -> None:
        exports = {"NANUQ": [{"row": {"Name": "N1", "Description": "DESC"}}]}

        first = self.service.write_exports(exports)
        second = self.service.write_exports(exports)

        self.assertEqual(first[0].name, "NANUQ_BATCH_EXPORT.csv")
        self.assertEqual(second[0].name, "NANUQ_BATCH_EXPORT-1.csv")


if __name__ == "__main__":
    unittest.main()
