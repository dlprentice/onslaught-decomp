"""Focused tests for tools/rttiorder.py: order scoring, locator names and the declaration variant. No compiler."""
import unittest

from tools import rttiorder


class Order(unittest.TestCase):
    def test_longest_run_counts_items_in_retail_order(self):
        self.assertEqual(rttiorder.longest_run([0, 1, 2, 3]), 4)
        self.assertEqual(rttiorder.longest_run([3, 2, 1, 0]), 1)
        self.assertEqual(rttiorder.longest_run([7, 9, 8, 1, 0, 3, 5, 6, 2, 4, 10]), 5)

    def test_compare_uses_pinned_locators_only(self):
        implied = {"??_R4CA@@6B@": 0x30, "??_R4CB@@6B@": "10", "??_R4CC@@6B@": 0x20}
        r = rttiorder.compare(["??_R4CA@@6B@", "??_R4CX@@6B@", "??_R4CB@@6B@", "??_R4CC@@6B@"], implied)
        self.assertEqual(r["retail"], ["??_R4CB@@6B@", "??_R4CC@@6B@", "??_R4CA@@6B@"])
        self.assertEqual((r["run"], r["n"]), (2, 3))
        self.assertIsNone(rttiorder.compare(["??_R4CA@@6B@"], implied))

    def test_class_of_skips_templates(self):
        self.assertEqual(rttiorder.class_of("??_R4CUnitInitThing@@6B@"), "CUnitInitThing")
        self.assertEqual(rttiorder.class_of("??_R4CRocket@@6BIRenderableThing@@@"), "CRocket")
        self.assertIsNone(rttiorder.class_of("??_R4?$CArray@H@@6B@"))


class Variant(unittest.TestCase):
    TEXT = '#include\t"Common.h"\n#include\t"InitThing.h"\n\nvoid f()\n{\n}\n'

    def test_line_goes_after_the_pch_include_and_absorbs_a_blank_line(self):
        body, kept = rttiorder.variant(self.TEXT, ["CB", "CA"], pch=True)
        self.assertTrue(kept)
        self.assertEqual(body.split("\n")[1], "class CB;class CA;")
        self.assertEqual(len(body.split("\n")), len(self.TEXT.split("\n")))

    def test_no_blank_line_means_the_line_count_changes(self):
        body, kept = rttiorder.variant('#include "common.h"\nvoid f();\n', ["CA"], pch=True)
        self.assertFalse(kept)
        self.assertEqual(body.split("\n")[1], "class CA;")

    def test_without_the_pch_the_line_goes_first(self):
        body, kept = rttiorder.variant('#include "asminstruction.h"\n\nint x;\n', ["CA"], pch=False)
        self.assertEqual(body.split("\n")[0], "class CA;")
        self.assertTrue(kept)


if __name__ == "__main__":
    unittest.main()
