"""Tests for find/replace helper behavior."""

import unittest

from app_controller import AppController
from models.tag_record import TagRecord


class TestFindReplaceHelpers(unittest.TestCase):
    def _record(self, tag: str, description: str) -> TagRecord:
        return TagRecord(
            tag_name=tag,
            description=description,
            vessels={"C-LEGACY"},
            row_data={"Name": tag, "Description": description},
        )

    def test_matches_find_scope_tag_only(self) -> None:
        record = self._record("AFT_DRAFT", "FORWARD LEVEL")
        self.assertTrue(AppController._matches_find_scope(record, "draft", "tag"))
        self.assertFalse(AppController._matches_find_scope(record, "draft", "description"))

    def test_matches_find_scope_both(self) -> None:
        record = self._record("PUMP", "SUCTION PUMP")
        self.assertTrue(AppController._matches_find_scope(record, "pump", "both"))

    def test_highlight_find_text_wraps_matches(self) -> None:
        highlighted = AppController._highlight_find_text("AFT_DRAFT", "draft")
        self.assertEqual(highlighted, "AFT_⟦DRAFT⟧")

    def test_format_find_replace_display_respects_scope(self) -> None:
        tag, description = AppController._format_find_replace_display(
            "AFT_DRAFT",
            "AFT DRAFT",
            "draft",
            "tag",
            highlight=True,
        )
        self.assertIn("⟦DRAFT⟧", tag)
        self.assertEqual(description, "AFT DRAFT")
