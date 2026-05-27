"""Tests for export queue service."""

import unittest

from services.export_queue_service import ExportQueueService, changed_field_labels


class TestExportQueueService(unittest.TestCase):
    def test_add_if_different(self) -> None:
        queue = ExportQueueService()
        original = {"Name": "T1", "Description": "OLD", "IOAddress": "%G1"}
        updated = {"Name": "T1", "Description": "NEW", "IOAddress": "%G1"}
        entry = queue.add_if_different("VESSEL", original, updated)
        self.assertIsNotNone(entry)
        self.assertEqual(changed_field_labels(entry.baseline, entry.row_data), ["Description"])

    def test_remove(self) -> None:
        queue = ExportQueueService()
        entry = queue.add("VESSEL", {"Name": "T1", "Description": "X"})
        self.assertTrue(queue.remove(entry.change_id))
        self.assertEqual(queue.count(), 0)

    def test_duplicate_tag_replaces_instead_of_appending(self) -> None:
        queue = ExportQueueService()
        first = queue.add(
            "C-LEGACY",
            {"Name": "AFT_DRAFT_SETPOINT", "Description": "AFT DRAFT SETPOINT", "IOAddress": "%R00113"},
            baseline={"Name": "AFT_DRAFT_SETPOINT", "Description": "", "IOAddress": "%R00113"},
        )
        second = queue.add_if_different(
            "C-LEGACY",
            {"Name": "AFT_DRAFT_SETPOINT", "Description": "AFT DRAFT SETPOINT", "IOAddress": "%R00113"},
            {
                "Name": "AFT_DRAFT_SETPOINT",
                "Description": "FWD DRAFT OFFSET SET POINT",
                "IOAddress": "%R00113",
            },
        )
        self.assertIs(second, first)
        self.assertEqual(queue.count(), 1)
        self.assertEqual(
            second.row_data["Description"],
            "FWD DRAFT OFFSET SET POINT",
        )
        self.assertEqual(first.baseline["Description"], "")


if __name__ == "__main__":
    unittest.main()
