"""Tests for description suggestion heuristics."""

import unittest

from services.description_suggester import DescriptionSuggester


class TestDescriptionSuggester(unittest.TestCase):
    """Validates generated descriptions for common tag formats."""

    def setUp(self) -> None:
        self.suggester = DescriptionSuggester()

    def test_ballast_tag_suggestion(self) -> None:
        result = self.suggester.suggest("BS_1P_TANK_GRAVITY")
        self.assertEqual(result, "BALLAST #1-P TANK GRAVITY")

    def test_percentage_suffix_suggestion(self) -> None:
        result = self.suggester.suggest("BS_6PC_TANK_PERCENT")
        self.assertEqual(result, "BALLAST #6-P-C TANK PERCENTAGE")


if __name__ == "__main__":
    unittest.main()
