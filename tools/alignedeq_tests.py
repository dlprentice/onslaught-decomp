"""Focused tests for tools/alignedeq.py: the three equality counts on synthetic bytes and the pairing/shift logic on a fake map and
fake images. No compiler, no specimen."""
import tempfile
import unittest
from pathlib import Path

from tools import alignedeq

REL32, DIR32 = 0x14, 0x06


class Image:
    """A flat fake image: read(address, size) over a bytearray based at 0x1000."""
    def __init__(self, data: bytes, base: int = 0x1000):
        self.data, self.base = bytes(data), base

    def read(self, addr: int, size: int) -> bytes:
        return self.data[addr - self.base:addr - self.base + size]


class MaskedEqual(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(alignedeq.masked_equal(b"abcdef", b"abcdef", []), (6, 6, 6, 6))

    def test_plain_difference_counts_in_none(self):
        self.assertEqual(alignedeq.masked_equal(b"abcdef", b"abXdef", []), (6, 5, 5, 5))

    def test_rel32_operand_masked_by_both_masks(self):
        ours = b"\xe8\x01\x02\x03\x04\xc3"
        retail = b"\xe8\x99\x99\x99\x99\xc3"
        self.assertEqual(alignedeq.masked_equal(ours, retail, [(1, REL32)]), (6, 2, 6, 6))

    def test_absolute_operand_masked_only_by_all(self):
        ours = b"\xa1\x10\x00\x62\x00\xc3"
        retail = b"\xa1\x20\x00\x62\x00\xc3"
        self.assertEqual(alignedeq.masked_equal(ours, retail, [(1, DIR32)]), (6, 5, 5, 6))

    def test_length_mismatch_is_unequal(self):
        n, raw, r32, every = alignedeq.masked_equal(b"abc", b"abcde", [])
        self.assertEqual((n, raw, r32, every), (5, 3, 3, 3))

    def test_mask_never_reaches_past_the_shorter_string(self):
        self.assertEqual(alignedeq.masked_equal(b"\xe8\x01", b"\xe8\x02\x03\x04\x05", [(1, REL32)]), (5, 1, 2, 2))


class Compare(unittest.TestCase):
    MAP = ("  Address         Publics by Value              Rva+Base     Lib:Object\n\n"
           " 0001:00000000       ?A@@YAXXZ                  00001000 f   a.obj\n"
           " 0001:00000010       ?B@@YAXXZ                  00001010 f   a.obj\n"
           " 0001:00000020       ?C@@YAXXZ                  00001020 f   b.obj\n")

    def test_functions_compared_at_their_own_addresses(self):
        # ours: A at 0x1000, B at 0x1010, C at 0x1020; retail has the same functions shifted by 0x40/0x30 (an unrelated function came first)
        ours = Image(b"A" * 8 + b"\0" * 8 + b"\xe8\x11\x11\x11\x11XYZ\0\0\0" + b"\0" * 5 + b"C" * 4 + b"\0" * 12)
        retail_bytes = bytearray(0x100)
        retail_bytes[0x40:0x48] = b"A" * 8
        retail_bytes[0x50:0x5b] = b"\xe8\x22\x22\x22\x22XYZ\0\0\0"
        retail_bytes[0x70:0x74] = b"C" * 4
        retail = Image(retail_bytes)
        expected = {("?A@@YAXXZ", None): 0x1040, ("?B@@YAXXZ", None): 0x1050, ("?C@@YAXXZ", None): 0x1070}
        relocs = {("?B@@YAXXZ", "a.obj"): [(1, REL32)]}
        sizes = {0x1040: 8, 0x1050: 11, 0x1070: 4}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "BEA.map").write_text(self.MAP)
            res = alignedeq.compare(Path(d), expected, relocs, retail, ours, sizes)
        self.assertEqual(res["functions"], 3)
        self.assertEqual(res["bytes"], 23)
        self.assertEqual(res["raw"], 19)        # B's four operand bytes differ
        self.assertEqual(res["rel32"], 23)
        self.assertEqual(res["all"], 23)

    def test_folded_name_takes_relocations_of_the_name_that_has_a_section(self):
        # B folded onto A's body (same address in the map); only A has an object section with relocations
        fold = ("  Address         Publics by Value              Rva+Base     Lib:Object\n\n"
                " 0001:00000000       ?A@@YAXXZ                  00001000 f   a.obj\n"
                " 0001:00000000       ?B@@YAXXZ                  00001000 f   b.obj\n")
        ours = Image(b"\xe8\x11\x11\x11\x11\xc3")
        retail = Image(b"\xe8\x22\x22\x22\x22\xc3")
        expected = {("?B@@YAXXZ", None): 0x1000}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "BEA.map").write_text(fold)
            res = alignedeq.compare(Path(d), expected, {("?A@@YAXXZ", "a.obj"): [(1, REL32)]}, retail, ours, {0x1000: 6})
        self.assertEqual((res["raw"], res["all"]), (2, 6))

    def test_ambiguous_retail_address_is_skipped(self):
        ours = Image(b"A" * 8 + b"\0" * 8)
        retail = Image(b"A" * 16)
        expected = {("?A@@YAXXZ", None): 0x1000, ("?Other@@YAXXZ", None): 0x1000}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "BEA.map").write_text(self.MAP)
            res = alignedeq.compare(Path(d), expected, {}, retail, ours, {0x1000: 8})
        self.assertEqual(res["functions"], 0)


class Kinds(unittest.TestCase):
    MAP = ("  Address         Publics by Value              Rva+Base     Lib:Object\n\n"
           " 0001:00000000       ?A@@YAXXZ                  00401000 f   a.obj\n"
           " 0001:00000100       ?B@@YAXXZ                  00401100 f   b.obj\n"
           " 0001:00000200       _lib@0                     00401200 f   crt.obj\n"
           " 0001:00000300       _imp@4                     00401300 f   thunks.obj\n")
    SECTIONS = [(".text", 0x401000, 0x400, 0, 0x400), (".data", 0x500000, 0x200, 0, 0x100)]

    def kinds(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.map").write_text(self.MAP)
            return alignedeq.TargetKinds(Path(d) / "a.map", {"a.obj", "b.obj"}, self.SECTIONS)

    def test_text_targets(self):
        k = self.kinds()
        self.assertEqual([k.kind(0x401010, "a.obj"), k.kind(0x401110, "a.obj"), k.kind(0x401210, "a.obj"), k.kind(0x401310, "a.obj")],
                         ["same object", "other game object", "library", "import thunk"])

    def test_data_targets(self):
        k = self.kinds()
        self.assertEqual([k.kind(0x500010, "a.obj"), k.kind(0x500180, "a.obj"), k.kind(0x700000, "a.obj")], [".data", ".bss", "outside"])


class DataEvents(unittest.TestCase):
    class K:
        def region(self, a): return ".bss"
        def symbol(self, a): return "sym%x" % a

    def test_chain_steps_and_fill_curve(self):
        # ours - retail: -10 for 3 words, then -30 (a 20-byte shortfall appears), then one outlier reference at +500
        pairs = [(0x100, 0x10A, "a"), (0x100, 0x10A, "a"), (0x104, 0x10E, "a"), (0x200, 0x21E, "b"), (0x300, 0x2FC - 500, "c")]
        res = alignedeq.data_events(pairs, self.K(), None)[".bss"]
        self.assertEqual([e["offset"] for e in res["events"]], [-10, -30])
        self.assertEqual([e["step"] for e in res["events"]], [-10, -20])
        self.assertEqual((res["words"], res["chain_words"]), (5, 4))
        self.assertEqual(res["bytes_to_fill_all_chain_steps"], 30)
        self.assertEqual([c["equal_words"] for c in res["prefix_fill_curve"]], [3, 4])

    def test_first_datum_offset_is_not_the_chains_start(self):
        # the lowest datum is already at offset 0, the heaviest non-increasing run starts later at +32 (3 words), then drops to 0 (1 word)
        pairs = [(0x100, 0x100, "a"), (0x200, 0x1E0, "b"), (0x200, 0x1E0, "b"), (0x200, 0x1E0, "b"), (0x300, 0x300, "c")]
        res = alignedeq.data_events(pairs, self.K(), None)[".bss"]
        self.assertEqual(res["first_datum_offset"], 0)
        self.assertEqual(res["chain_start_excess"], 32)


if __name__ == "__main__":
    unittest.main()
