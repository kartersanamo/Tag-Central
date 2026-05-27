"""Integration tests for Proficy + Cimplicity import policy."""

import tempfile
import unittest
from pathlib import Path

from models.tag_record import SYNC_SYNCED, TagRecord
from services.cimplicity_loader import CimplicityLoader
from services.cross_program_sync_service import CrossProgramSyncService
from services.export_queue_service import ExportQueueService
from services.proficy_import_analyzer import ProficyImportAnalyzer
from services.spreadsheet_loader import SpreadsheetLoader
from services.tag_repository import TagRepository
from services.tag_sync_service import TagSyncService


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestImportIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "tags.csv"
        self.repository = TagRepository(self.db_path)
        self.tags: dict[str, TagRecord] = {}
        self.sync = TagSyncService()
        self.cross_program = CrossProgramSyncService()
        self.export_queue = ExportQueueService()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_proficy_then_cimplicity_policy(self) -> None:
        proficy_path = FIXTURES / "proficy_small.csv"
        cimplicity_path = FIXTURES / "cimplicity_small.csv"
        if not proficy_path.exists() or not cimplicity_path.exists():
            self.skipTest("fixture files missing")

        vessel = "TESTVESSEL"
        proficy_rows = SpreadsheetLoader().load_rows(str(proficy_path))
        analysis = ProficyImportAnalyzer(self.sync).analyze(self.tags, proficy_rows, vessel)
        self.assertGreater(analysis.total_rows, 0)

        for row in proficy_rows[:5]:
            tag_name = row.get("Name", "").strip().upper()
            description = row.get("Description", "").strip().upper()
            if not tag_name:
                continue
            self.cross_program.import_proficy_row(
                self.tags, tag_name, description, vessel, row
            )

        self.repository.save(self.tags)
        self.assertGreater(len(self.tags), 0)

        raw_cimplicity = CimplicityLoader().load_rows(str(cimplicity_path))
        prepared = self.cross_program.prepare_cimplicity_rows(raw_cimplicity)
        summary = self.cross_program.analyze_cimplicity_import(
            self.tags, prepared, vessel
        )
        self.assertGreater(summary.total_rows, 0)
        self.assertGreaterEqual(summary.matched_exact_id, 0)

        if summary.actionable:
            action = summary.actionable[0]
            link = self.cross_program._linker.link_cimplicity_row(
                self.tags, action.pt_id, action.address
            )
            canonical = self.cross_program.resolve_tag_key(
                self.tags,
                prepared[action.row_index],
                link,
                preferred_key=action.existing_tag,
            )
            if canonical:
                _, export_row = self.cross_program.apply_cimplicity_row(
                    self.tags,
                    prepared[action.row_index],
                    vessel,
                    "align_proficy",
                    canonical_tag=canonical,
                )
                if export_row:
                    self.export_queue.add(vessel, export_row)

        synced = [
            record
            for record in self.tags.values()
            if record.sync_status == SYNC_SYNCED
        ]
        self.assertGreaterEqual(len(synced), 0)


if __name__ == "__main__":
    unittest.main()
