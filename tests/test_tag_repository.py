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
                proficy_row_data={"Name": "A100", "Description": "MAIN PUMP"},
                proficy_name="A100",
                sync_status="proficy_only",
            )
        }

        self.repository.save(original)
        loaded = self.repository.load()

        self.assertIn("A100", loaded)
        self.assertEqual(loaded["A100"].description, "MAIN PUMP")
        self.assertEqual(loaded["A100"].vessels, {"V1", "V2"})
        self.assertEqual(
            loaded["A100"].proficy_row_data,
            {"Name": "A100", "Description": "MAIN PUMP"},
        )

    def test_legacy_row_data_column_loads(self) -> None:
        legacy_csv = (
            "tag_name,description,vessels,row_data\n"
            'LEGACY1,LEGACY DESC,V1,"{""Name"": ""LEGACY1"", ""IOAddress"": ""%R00001""}"\n'
        )
        self.database_path.write_text(legacy_csv, encoding="utf-8")
        loaded = self.repository.load()
        self.assertIn("LEGACY1", loaded)
        self.assertEqual(loaded["LEGACY1"].proficy_row_data["Name"], "LEGACY1")
        self.assertEqual(loaded["LEGACY1"].linked_address, "%R00001")

    def test_extended_columns_round_trip(self) -> None:
        original = {
            "TAG1": TagRecord(
                tag_name="TAG1",
                description="DESC ONE",
                vessels={"C-LEGACY"},
                proficy_row_data={"Name": "TAG1", "IOAddress": "%R00111"},
                cimplicity_row_data={"PT_ID": "TAG1", "DESC": "Desc One", "ADDR": "%R00111"},
                cimplicity_pt_id="TAG1",
                proficy_name="TAG1",
                linked_address="%R00111",
                sync_status="synced",
                link_method="address",
            )
        }
        self.repository.save(original)
        loaded = self.repository.load()["TAG1"]
        self.assertEqual(loaded.sync_status, "synced")
        self.assertEqual(loaded.cimplicity_pt_id, "TAG1")
        self.assertEqual(loaded.link_method, "address")

    def test_symbolic_linked_address_not_persisted(self) -> None:
        record = TagRecord(
            tag_name="ARRAY_IDX",
            description="TANK LEVEL",
            proficy_row_data={"Name": "ARRAY_IDX", "IOAddress": "<SYMBOLIC>"},
            linked_address="<SYMBOLIC>",
        )
        self.repository.save({"ARRAY_IDX": record})
        loaded = self.repository.load()["ARRAY_IDX"]
        self.assertEqual(loaded.linked_address, "")


if __name__ == "__main__":
    unittest.main()
