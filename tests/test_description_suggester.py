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

    def test_unique_suggestion_uses_tag_number_hint(self) -> None:
        used = {"XDUCER ZERO"}
        result = self.suggester.suggest_unique("XDUCER_ZERO_137", used)
        self.assertEqual(result, "XDUCER ZERO 137")

    def test_unique_suggestion_falls_back_to_increment(self) -> None:
        used = {"PUMP STATUS", "PUMP STATUS 2", "PUMP STATUS 2-2"}
        result = self.suggester.suggest_unique("PUMP_STATUS_2", used)
        self.assertEqual(result, "PUMP STATUS 2-3")


if __name__ == "__main__":
    unittest.main()
