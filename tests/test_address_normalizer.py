"""Tests for IO address normalization."""

import unittest

from services.address_normalizer import (
    addresses_equivalent,
    is_resolvable_address,
    normalize_address,
)


class TestAddressNormalizer(unittest.TestCase):
    def test_g_address_padding(self) -> None:
        self.assertEqual(normalize_address("%G0479"), "%G00479")
        self.assertEqual(normalize_address("%G00479"), "%G00479")

    def test_addresses_equivalent_proficy_cimplicity(self) -> None:
        self.assertTrue(addresses_equivalent("%G00479", "%G0479"))
        self.assertTrue(addresses_equivalent("%R00111", "%R00111"))

    def test_ai_address(self) -> None:
        self.assertEqual(normalize_address("%ai0137"), "%AI137")

    def test_symbolic_placeholder_is_not_resolvable(self) -> None:
        self.assertEqual(normalize_address("<Symbolic>"), "<SYMBOLIC>")
        self.assertFalse(is_resolvable_address("<Symbolic>"))
        self.assertFalse(addresses_equivalent("<Symbolic>", "<Symbolic>"))
