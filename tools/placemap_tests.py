"""Focused tests for tools/placemap.py: the in-order chain and the map reader. No link or specimen needed."""
import tempfile
import unittest
from pathlib import Path

from tools import placemap


class Chain(unittest.TestCase):
    def test_longest_run_in_order_in_both_images(self):
        pairs = [(0x10, 0x100, "a"), (0x20, 0x300, "b"), (0x30, 0x200, "c"), (0x40, 0x400, "d")]
        self.assertEqual([pairs[i][2] for i in placemap.chain(pairs)], ["a", "c", "d"])

    def test_empty(self):
        self.assertEqual(placemap.chain([]), [])


class Map(unittest.TestCase):
    def test_code_symbols_keep_object_and_inline_flag(self):
        text = (" 0001:00000000       ?F@@YAXXZ                  00401000 f   a.obj\n"
                " 0001:00000010       ?G@@YAXXZ                  00401010 f i b.obj\n"
                " 0002:00000000       ?D@@3HA                    00402000     a.obj\n")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "BEA.map"
            p.write_text(text)
            self.assertEqual(placemap.code_symbols(p), [(0x401000, "?F@@YAXXZ", "a.obj", False),
                                                        (0x401010, "?G@@YAXXZ", "b.obj", True)])


class Expected(unittest.TestCase):
    def test_lookup_prefers_the_symbols_own_object(self):
        exp = {("?S@@YAXXZ", "a.obj"): 0x10, ("?S@@YAXXZ", "b.obj"): 0x20, ("?E@@YAXXZ", None): 0x30}
        self.assertEqual(placemap.lookup(exp, "?S@@YAXXZ", "B.obj"), 0x20)
        self.assertEqual(placemap.lookup(exp, "?E@@YAXXZ", "c.obj"), 0x30)
        self.assertIsNone(placemap.lookup(exp, "?S@@YAXXZ", "c.obj"))   # two objects' statics: ambiguous

    def test_inline_annotated_elsewhere_pairs_by_its_one_address(self):
        exp = {("?I@@YAXXZ", "a.obj"): 0x40, ("?J@@YAXXZ", "a.obj"): 0x50, ("?J@@YAXXZ", "b.obj"): 0x50}
        self.assertEqual(placemap.lookup(exp, "?I@@YAXXZ", "z.obj"), 0x40)
        self.assertEqual(placemap.lookup(exp, "?J@@YAXXZ", "z.obj"), 0x50)

    def test_frozen_file_matches_any_object(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.json"
            p.write_text('{"functions": {"?F@@YAXXZ": 4198400}, "implied": {}}')
            self.assertEqual(placemap.frozen_expected(p), {("?F@@YAXXZ", None): 0x401000})


class Placement(unittest.TestCase):
    def test_same_named_statics_pair_by_object(self):
        # two objects each define a static ?S; b.obj's is the one retail places second in that object
        text = (" 0001:00000000       ?A@@YAXXZ                  00401000 f   a.obj\n"
                " 0001:00000010       ?S@@YAXXZ                  00401010 f   a.obj\n"
                " 0001:00000020       ?B@@YAXXZ                  00401020 f   b.obj\n"
                " 0001:00000030       ?S@@YAXXZ                  00401030 f   b.obj\n"
                " 0001:00000040       ?Z@@YAXXZ                  00401040 f   z.obj\n")
        retail = {a: placemap.decomp.RetailFunction(a, 16, f"r{a:x}") for a in range(0x401000, 0x401050, 0x10)}
        exp = {("?A@@YAXXZ", "a.obj"): 0x401000, ("?S@@YAXXZ", "a.obj"): 0x401010, ("?B@@YAXXZ", "b.obj"): 0x401020,
               ("?S@@YAXXZ", "b.obj"): 0x401030, ("?Z@@YAXXZ", "z.obj"): 0x401040}
        saved = placemap.decomp.retail_functions
        placemap.decomp.retail_functions = lambda: retail
        try:
            with tempfile.TemporaryDirectory() as d:
                (Path(d) / "BEA.map").write_text(text)
                r = placemap.placement(Path(d), exp)
        finally:
            placemap.decomp.retail_functions = saved
        self.assertEqual((r["pairs"], r["chain"], r["misplaced"]), (5, 5, []))
        self.assertEqual([(x["object"], x["delta"], x["own_paired"]) for x in r["regions"]],
                         [("a.obj", 0, 2), ("b.obj", 0, 2)])


if __name__ == "__main__":
    unittest.main()
