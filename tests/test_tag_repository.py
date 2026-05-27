"""Tests for CSV tag repository."""

import tempfile
import unittest
from pathlib import Path

from models.tag_record import TagRecord
from services.tag_repository import TagRepository


class TestTagRepository(unittest.TestCase):
    """Ensures save/load round-trip integrity."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "tags.csv"
        self.repository = TagRepository(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_then_load_preserves_data(self) -> None:
        original = {
            "A100": TagRecord(
                tag_name="A100",
                description="MAIN PUMP",
                vessels={"V2", "V1"},
                row_data={"Name": "A100", "Description": "MAIN PUMP"},
            )
        }

        self.repository.save(original)
        loaded = self.repository.load()

        self.assertIn("A100", loaded)
        self.assertEqual(loaded["A100"].description, "MAIN PUMP")
        self.assertEqual(loaded["A100"].vessels, {"V1", "V2"})
        self.assertEqual(
            loaded["A100"].row_data, {"Name": "A100", "Description": "MAIN PUMP"}
        )


if __name__ == "__main__":
    unittest.main()
