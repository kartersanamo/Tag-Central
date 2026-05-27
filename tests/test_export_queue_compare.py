"""Tests for export queue comparison helpers."""

import unittest

from app_controller import AppController


class TestExportQueueCompare(unittest.TestCase):
    def test_extra_address_column_does_not_count_as_change(self) -> None:
        original = {
            "Name": "AFT_DRAFT",
            "Description": "AFT DRAFT",
            "IOAddress": "%R00111",
            "DataType": "INT",
        }
        updated = {
            "Name": "AFT_DRAFT",
            "Description": "AFT DRAFT",
            "IOAddress": "%R00111",
            "Address": "%R00111",
            "DataType": "INT",
        }
        self.assertEqual(
            AppController._export_fields_for_compare(original),
            AppController._export_fields_for_compare(updated),
        )

    def test_description_change_is_detected(self) -> None:
        before = {"Name": "PUMP", "Description": "OLD", "IOAddress": "%R00001"}
        after = {"Name": "PUMP", "Description": "NEW", "IOAddress": "%R00001"}
        self.assertNotEqual(
            AppController._export_fields_for_compare(before),
            AppController._export_fields_for_compare(after),
        )


if __name__ == "__main__":
    unittest.main()
