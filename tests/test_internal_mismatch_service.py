"""Tests for internal mismatch detection."""

import unittest

from models.tag_record import TagRecord
from services.internal_mismatch_service import (
    MISMATCH_DUPLICATE_DESCRIPTION,
    MISMATCH_SHARED_ADDRESS,
    InternalMismatchService,
)


class TestInternalMismatchService(unittest.TestCase):
    def test_duplicate_description_group(self) -> None:
        tags = {
            "TAG_A": TagRecord(
                tag_name="TAG_A",
                description="PUMP SUCTION",
                proficy_row_data={"IOAddress": "%G0001"},
                linked_address="%G0001",
            ),
            "TAG_B": TagRecord(
                tag_name="TAG_B",
                description="PUMP SUCTION",
                proficy_row_data={"IOAddress": "%G0002"},
                linked_address="%G0002",
            ),
        }
        result = InternalMismatchService().calculate(tags)
        self.assertIn("TAG_A", result.conflicted_tags)
        self.assertEqual(
            result.mismatch_types["TAG_A"], MISMATCH_DUPLICATE_DESCRIPTION
        )
        self.assertTrue(result.group_labels["TAG_A"].startswith("G"))

    def test_shared_address_group(self) -> None:
        tags = {
            "TAG_A": TagRecord(
                tag_name="TAG_A",
                description="DESC ONE",
                proficy_row_data={"IOAddress": "%G0100"},
                linked_address="%G0100",
            ),
            "TAG_B": TagRecord(
                tag_name="TAG_B",
                description="DESC TWO",
                proficy_row_data={"IOAddress": "%G0100"},
                linked_address="%G0100",
            ),
        }
        result = InternalMismatchService().calculate(tags)
        self.assertEqual(result.mismatch_types["TAG_A"], MISMATCH_SHARED_ADDRESS)
        self.assertTrue(result.group_labels["TAG_A"].startswith("A"))

    def test_symbolic_array_indices_are_not_shared_address_conflicts(self) -> None:
        tags = {}
        for tank in ("BS_1P", "BS_1S", "BS_6P"):
            tag_name = f"{tank}_TANK_TABLE[299]"
            tags[tag_name] = TagRecord(
                tag_name=tag_name,
                description=f"{tank} TANK VOLUME @ 299",
                proficy_row_data={"IOAddress": "<Symbolic>"},
                linked_address="<SYMBOLIC>",
            )
        result = InternalMismatchService().calculate(tags)
        self.assertEqual(result.conflicted_tags, set())
        self.assertNotIn(MISMATCH_SHARED_ADDRESS, result.mismatch_types.values())


if __name__ == "__main__":
    unittest.main()
