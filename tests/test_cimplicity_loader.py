"""Tests for Cimplicity Shared Name File loader."""

import unittest
from pathlib import Path

from services.cimplicity_loader import CimplicityLoader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTCIM = PROJECT_ROOT / "TESTCIM.csv"


class TestCimplicityLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = CimplicityLoader()

    @unittest.skipUnless(TESTCIM.exists(), "TESTCIM.csv not present")
    def test_load_testcim_rows(self) -> None:
        rows = self.loader.load_rows(str(TESTCIM))
        self.assertGreater(len(rows), 2000)
        first = rows[0]
        self.assertIn("PT_ID", first)
        self.assertIn("DESC", first)
        self.assertTrue(first["PT_ID"])
