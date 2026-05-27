"""Tests for cross-program sync policy."""

import unittest

from models.tag_record import SYNC_PROFICY_ONLY, SYNC_SYNCED, TagRecord
from services.cross_program_sync_service import (
    CimplicityImportRow,
    CrossProgramSyncService,
    normalize_description,
)


class TestCrossProgramSyncService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CrossProgramSyncService()
        self.tags = {
            "AFT_DRAFT_INCHES": TagRecord(
                tag_name="AFT_DRAFT_INCHES",
                description="AFT DRAFT INCHES",
                vessels={"C-LEGACY"},
                proficy_row_data={
                    "Name": "AFT_DRAFT_INCHES",
                    "Description": "AFT DRAFT INCHES",
                    "IOAddress": "%R00111",
                },
                proficy_name="AFT_DRAFT_INCHES",
                linked_address="%R00111",
                sync_status=SYNC_PROFICY_ONLY,
            )
        }

    def test_align_proficy_renames_to_cimplicity_pt_id(self) -> None:
        row = CimplicityImportRow(
            pt_id="AFT_DRAFT",
            description=normalize_description("Aft Draft"),
            address="%R00111",
            row_data={"PT_ID": "AFT_DRAFT", "DESC": "Aft Draft", "ADDR": "%R00111"},
            row_index=0,
        )
        export_row = self.service.align_proficy_to_cimplicity(
            self.tags, "AFT_DRAFT_INCHES", row, "C-LEGACY"
        )
        self.assertIn("AFT_DRAFT", self.tags)
        record = self.tags["AFT_DRAFT"]
        self.assertEqual(record.sync_status, SYNC_SYNCED)
        self.assertEqual(record.description, "AFT DRAFT")
        self.assertIsNotNone(export_row)
        self.assertEqual(export_row["Name"], "AFT_DRAFT")
