"""Tests for backup service workflows."""

import tempfile
import unittest
from pathlib import Path

from services.backup_service import BackupService


class TestBackupService(unittest.TestCase):
    """Validates create/list/restore/revert backup behavior."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.database = base / "tags.csv"
        self.database.write_text(
            "tag_name,description,vessels,row_data\nA1,ONE,V1,{}\n", encoding="utf-8"
        )
        self.service = BackupService(base / "backups", self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_and_list_backup(self) -> None:
        created = self.service.create_backup_from_database(prefix="manual")
        self.assertIsNotNone(created)
        listed = self.service.list_backups()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["name"], created.name)  # type: ignore[union-attr]

    def test_preload_revert_restores_previous_database(self) -> None:
        self.service.create_preload_backup()
        self.database.write_text(
            "tag_name,description,vessels,row_data\nA1,CHANGED,V1,{}\n", encoding="utf-8"
        )
        restored = self.service.restore_preload_backup()
        self.assertTrue(restored)
        self.assertIn("ONE", self.database.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
