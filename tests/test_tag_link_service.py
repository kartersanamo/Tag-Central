"""Tests for Cimplicity-to-canonical linking."""

import unittest

from models.tag_record import TagRecord
from services.tag_link_service import TagLinkService


class TestTagLinkService(unittest.TestCase):
    def setUp(self) -> None:
        self.linker = TagLinkService()
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
            ),
            "ALM_ECOPC1_ACKN": TagRecord(
                tag_name="ALM_ECOPC1_ACKN",
                description="CIMPLICITY ALARM ACKNOWLEGE",
                vessels={"C-LEGACY"},
                proficy_row_data={
                    "Name": "ALM_ECOPC1_ACKN",
                    "IOAddress": "%G00479",
                },
                proficy_name="ALM_ECOPC1_ACKN",
                linked_address="%G00479",
            ),
        }

    def test_link_by_address_when_names_differ(self) -> None:
        result = self.linker.link_cimplicity_row(
            self.tags, pt_id="AFT_DRAFT", address="%R00111"
        )
        self.assertEqual(result.canonical_tag, "AFT_DRAFT_INCHES")
        self.assertEqual(result.method, "address")

    def test_link_by_alias_and_address(self) -> None:
        result = self.linker.link_cimplicity_row(
            self.tags, pt_id="ALARM_ECOPC1_ACKN", address="%G0479"
        )
        self.assertEqual(result.canonical_tag, "ALM_ECOPC1_ACKN")
        self.assertIn(result.method, ("alias", "address"))
