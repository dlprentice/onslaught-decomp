"""Focused tests for tools/constowner.py: owner inference, classification and constant values. No link needed."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import constowner

decomp, placemap = constowner.decomp, constowner.placemap     # the modules constowner itself uses


class Owner(unittest.TestCase):
    pinned = [(0x100, "a.obj"), (0x110, "a.obj"), (0x200, "b.obj"), (0x210, "c.obj")]

    def test_inside_one_object(self):
        self.assertEqual(constowner.retail_owner(0x108, self.pinned), "a.obj")

    def test_between_two_objects_is_a_boundary(self):
        self.assertEqual(constowner.retail_owner(0x180, self.pinned), "boundary a.obj|b.obj")

    def test_past_the_last(self):
        self.assertEqual(constowner.retail_owner(0x300, self.pinned), "c.obj")


class Classify(unittest.TestCase):
    def test_classes(self):
        self.assertEqual(constowner.classify("a.obj", "A.obj", set()), "same")
        self.assertEqual(constowner.classify("boundary a.obj|b.obj", "c.obj", {"c.obj"}), "missing code")
        self.assertEqual(constowner.classify("boundary a.obj|b.obj", "c.obj", {"b.obj", "c.obj"}), "emission")
        self.assertEqual(constowner.classify("boundary a.obj|b.obj", "B.obj", set()), "same")
        self.assertEqual(constowner.classify("menuitem.obj", "planeai.obj", {"planeai.obj", "menuitem.obj"}), "emission")
        self.assertEqual(constowner.classify("menuitem.obj", "planeai.obj", {"planeai.obj"}), "missing code")

    def test_an_object_between_the_neighbours_in_link_order_agrees(self):
        rank = {"thunderheadguide.obj": 1, "tokenarchive.obj": 2, "tree.obj": 3, "umtexture.obj": 4}
        self.assertEqual(constowner.classify("boundary thunderheadguide.obj|tree.obj", "tokenarchive.obj",
                                             {"tokenarchive.obj"}, rank), "same")
        self.assertEqual(constowner.classify("boundary thunderheadguide.obj|tree.obj", "umtexture.obj",
                                             {"umtexture.obj"}, rank), "missing code")


class Values(unittest.TestCase):
    def test_extended_names(self):
        self.assertEqual(constowner.value_of("__real@4@40058c00000000000000"), "70")
        self.assertEqual(constowner.value_of("__real@4@4009c800000000000000"), "1600")
        self.assertEqual(constowner.value_of("__real@4@c008c000000000000000"), "-768")
        self.assertEqual(constowner.value_of("__real@4@00000000000000000000"), "0")


class Trees(unittest.TestCase):
    def setUp(self):
        self.saved = (decomp.ROOT, decomp.CONFIG, decomp.BUILD, decomp.PCH_SOURCE)

    def tearDown(self):
        decomp.ROOT, decomp.CONFIG, decomp.BUILD, decomp.PCH_SOURCE = self.saved

    def test_the_tree_of_a_link_folder(self):
        self.assertEqual(constowner.tree_of(Path("/x/wt/local-data/link")), Path("/x/wt"))
        self.assertEqual(constowner.tree_of(Path("/x/elsewhere")), decomp.ROOT)
        self.assertEqual(constowner.tree_of(None), decomp.ROOT)

    def test_two_trees_read_their_own_objects(self):
        seen = []
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(decomp, "check", side_effect=lambda objs: seen.append(dict(objs)) or ([], None)):
            for name in ("a", "b"):
                tree = Path(d) / name
                (tree / "src").mkdir(parents=True)
                (tree / "build").mkdir()
                (tree / "src" / f"{name}.cpp").write_text("")
                (tree / "build" / f"{name}.obj").write_bytes(b"")
                constowner.use_tree(tree)
                placemap.expected_by_object()
            a, b = seen
            self.assertEqual([p.name for p in a.values()], ["a.obj"])
            self.assertEqual([p.name for p in b.values()], ["b.obj"])
            self.assertTrue(all(str(p).startswith(str(Path(d).resolve() / "b")) for p in b.values()))


if __name__ == "__main__":
    unittest.main()
