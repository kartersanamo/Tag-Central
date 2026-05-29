"""Tests for documentation generation."""

import tempfile
import unittest
from pathlib import Path

from models.tag_record import SYNC_PROFICY_ONLY, SYNC_SYNCED, TagRecord
from services.documentation_service import DocumentationService


class TestDocumentationService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = DocumentationService()
        self.tags = {
            "PUMP_RUN": TagRecord(
                tag_name="PUMP_RUN",
                description="MAIN SEA WATER PUMP RUN",
                vessels={"C-LEGACY"},
                proficy_row_data={"Name": "PUMP_RUN", "IOAddress": "%R00100"},
                linked_address="%R00100",
                sync_status=SYNC_SYNCED,
            ),
            "ALM_PUMP_TRIP": TagRecord(
                tag_name="ALM_PUMP_TRIP",
                description="PUMP TRIP ALARM",
                vessels={"C-LEGACY"},
                proficy_row_data={"Name": "ALM_PUMP_TRIP", "IOAddress": "%G00479"},
                linked_address="%G00479",
                sync_status=SYNC_PROFICY_ONLY,
            ),
        }

    def test_build_io_and_alarm_lists(self) -> None:
        tables = self.service.build_tables(
            self.tags,
            selected_types=["io_list", "alarm_list"],
        )
        by_id = {table.doc_id: table for table in tables}
        self.assertEqual(len(by_id["io_list"].rows), 2)
        self.assertEqual(len(by_id["alarm_list"].rows), 1)
        self.assertEqual(by_id["alarm_list"].rows[0]["tag_name"], "ALM_PUMP_TRIP")

    def test_write_html_package(self) -> None:
        tables = self.service.build_tables(
            self.tags,
            selected_types=["tag_dictionary"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "docs"
            result = self.service.write_package(
                tables,
                output,
                write_html=True,
                write_excel=False,
                write_csv=False,
                write_word=False,
                tag_count=2,
            )
            self.assertTrue((output / "index.html").exists())
            self.assertTrue((output / "tag_dictionary.html").exists())
            self.assertGreater(len(result.written_files), 0)


if __name__ == "__main__":
    unittest.main()
