"""Tests for tag synchronization service."""

import unittest

from models.tag_record import TagRecord
from services.tag_sync_service import TagSyncService


class TestTagSyncService(unittest.TestCase):
    """Validates conflict detection and mutation behavior."""

    def setUp(self) -> None:
        self.service = TagSyncService()
        self.tags = {
            "T100": TagRecord(
                tag_name="T100",
                description="PUMP SUCTION",
                vessels={"V1"},
                row_data={"Name": "T100", "Description": "PUMP SUCTION"},
            )
        }

    def test_find_conflict_returns_none_for_exact_match(self) -> None:
        conflict = self.service.find_conflict(self.tags, "T100", "PUMP SUCTION")
        self.assertIsNone(conflict)

    def test_find_conflict_detects_same_tag_different_description(self) -> None:
        conflict = self.service.find_conflict(self.tags, "T100", "PUMP DISCHARGE")
        self.assertIsNotNone(conflict)

    def test_add_or_update_imported_updates_existing_tag(self) -> None:
        self.service.add_or_update_imported(
            self.tags,
            tag_name="T100",
            description="PUMP DISCHARGE",
            vessel="V2",
            row_data={"Name": "T100", "Description": "PUMP DISCHARGE"},
        )
        self.assertEqual(self.tags["T100"].description, "PUMP DISCHARGE")
        self.assertIn("V2", self.tags["T100"].vessels)

    def test_unique_suffix_name_increments_until_available(self) -> None:
        self.tags["T100_2"] = TagRecord("T100_2", "ALT", {"V1"}, {})
        self.tags["T100_3"] = TagRecord("T100_3", "ALT2", {"V1"}, {})
        result = self.service.unique_suffix_name(self.tags, "T100")
        self.assertEqual(result, "T100_4")


if __name__ == "__main__":
    unittest.main()
