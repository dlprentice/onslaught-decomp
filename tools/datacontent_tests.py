"""Focused tests for tools/datacontent.py: the byte classifier. No link or specimen needed."""
import unittest

from tools import datacontent


class Classify(unittest.TestCase):
    def test_equal(self):
        self.assertEqual(datacontent.classify(b"abcd", b"abcd", set()), (0, 0))

    def test_differences_inside_relocated_fields_are_references(self):
        retail = b"\x00\x10\x40\x00" + b"xy"
        ours = b"\x08\x00\x00\x00" + b"xy"                  # our object holds the addend where retail has the address
        self.assertEqual(datacontent.classify(retail, ours, {0}), (3, 0))

    def test_other_differences_are_content(self):
        self.assertEqual(datacontent.classify(b"\x9a\x99\x59\x3f", b"\x9b\x99\x59\x3f", set()), (0, 1))
        self.assertEqual(datacontent.classify(b"AAAAzz", b"BBBBzq", {0}), (4, 1))


if __name__ == "__main__":
    unittest.main()
