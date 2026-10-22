"""Focused tests for tools/inventory.py's helpers. No link needed; the specimen check skips without the specimen."""
import struct
import types
import unittest

from tools import decomp, inventory


def fake_pe_with_rich(entries, key=0x1234ABCD):
    """MZ header whose e_lfanew points past a Rich header holding ENTRIES [(product, build, count)]."""
    data = bytearray(0x200)
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x100)
    words = [0x536E6144 ^ key, key, key, key]            # "DanS" and three zero words, XORed
    for prod, build, count in entries:
        words += [((prod << 16) | build) ^ key, count ^ key]
    for i, w in enumerate(words):
        struct.pack_into("<I", data, 0x80 + 4 * i, w)
    end = 0x80 + 4 * len(words)
    data[end:end + 4] = b"Rich"
    struct.pack_into("<I", data, end + 4, key)
    return types.SimpleNamespace(data=bytes(data))


class Rich(unittest.TestCase):
    def test_entries_are_decoded_with_the_key(self):
        entries = [(11, 8966, 464), (0x13, 8034, 19), (1, 0, 253)]
        self.assertEqual(inventory.rich(fake_pe_with_rich(entries)), entries)

    def test_no_rich_header(self):
        data = bytearray(0x200)
        struct.pack_into("<I", data, 0x3C, 0x100)
        self.assertEqual(inventory.rich(types.SimpleNamespace(data=bytes(data))), [])

    def test_specimen_lists_the_game_objects_compiler(self):
        if not decomp.SPECIMEN.exists():
            self.skipTest("specimen not present")
        r = inventory.rich(inventory.PeImage(decomp.SPECIMEN, decomp.SPECIMEN_SHA256))
        self.assertTrue(any(p == 11 and b == 8966 for p, b, _n in r))


class Masks(unittest.TestCase):
    def test_address_like_words_and_call_displacements_are_masked(self):
        code = bytes.fromhex("b8" "00104000" "e8" "11223344" "90")      # mov eax, 00401000; call rel32; nop
        m = inventory.addr_mask(code)
        self.assertEqual(list(m[1:5]), [1, 1, 1, 1])                       # the address
        self.assertEqual(list(m[6:10]), [1, 1, 1, 1])                      # the call's displacement
        self.assertEqual(m[10], 0)
        self.assertEqual(inventory.masked(code)[1:5], b"\0\0\0\0")

    def test_tolerant_find_ignores_masked_fields_on_either_side(self):
        needle = bytes.fromhex("55" "b8" "00104000" "c3")
        hay = bytes.fromhex("90909090" "55" "b8" "00205000" "c3" "90")
        self.assertEqual(inventory.tolerant_find(needle, hay, 0, len(hay)), 4)
        self.assertEqual(inventory.tolerant_find(bytes.fromhex("55b80010400090"), hay, 0, len(hay)), -1)

    def test_next_after_and_section_end(self):
        self.assertEqual(inventory.next_after([0x10, 0x20, 0x30], 0x10, 0x100), 0x20)
        self.assertEqual(inventory.next_after([0x10, 0x20], 0x20, 0x28), 0x28)
        table = {".text": (0x401000, 0x402000), ".data": (0x500000, 0x501000)}
        self.assertEqual(inventory.section_end(table, 0x500010), 0x501000)
        self.assertEqual(inventory.section_end(table, 0x600000), 0x600000)


class References(unittest.TestCase):
    in_image = staticmethod(lambda v: 0x400000 <= v < 0x500000)

    def test_absolute_reference_with_corresponding_targets(self):
        translate = lambda r: r + 0x100
        self.assertEqual(inventory.reference_kind(0x401000, 0x401100, 0x402000, 0x402100, translate, self.in_image), 1)

    def test_rel32_reference_with_corresponding_targets(self):
        translate = lambda r: r + 0x100 if r == 0x403000 else None
        # retail call at site 0x402000 to 0x403000: displacement 0x403000 - 0x402004; ours from 0x402010 to 0x403100
        vr, vo = 0x403000 - 0x402004, 0x403100 - 0x402014
        self.assertEqual(inventory.reference_kind(vr, vo, 0x402000, 0x402010, translate, self.in_image), 1)

    def test_targets_that_do_not_correspond(self):
        self.assertEqual(inventory.reference_kind(0x401000, 0x401200, 0x402000, 0x402100,
                                                  lambda r: r + 0x100, self.in_image), 4)
        self.assertEqual(inventory.reference_kind(0x401000, 0x401200, 0x402000, 0x402100,
                                                  lambda r: None, self.in_image), 3)
        self.assertEqual(inventory.reference_kind(0x12345678, 0x9abcdef0, 0x402000, 0x402100,
                                                  lambda r: r, self.in_image), 2)


class ObjectSpans(unittest.TestCase):
    def test_comparable_size_difference_and_order(self):
        points = [(0x1000, 0x2000, "a"), (0x1010, 0x2008, "b"), (0x1020, 0x2018, "c"), (0x1030, 0x2028, "d")]
        spans = {x["object"]: x for x in inventory.object_spans(points, 0x1040, 0x2038)}
        self.assertEqual(spans["a"]["delta"], -8)                 # retail's a is 8 bytes larger
        self.assertTrue(spans["a"]["comparable"])
        self.assertNotIn("b", spans)                             # same span in both
        self.assertNotIn("d", spans)

    def test_objects_in_another_order_are_not_comparable(self):
        points = [(0x1000, 0x2000, "a"), (0x1010, 0x2020, "b"), (0x1020, 0x2018, "c")]
        spans = {x["object"]: x for x in inventory.object_spans(points, 0x1030, 0x2030)}
        self.assertFalse(spans["a"]["comparable"])               # next is b in retail, c in ours


class CoffExtent(unittest.TestCase):
    def test_exact_size_and_relocations_inside_the_symbol(self):
        data = bytes(range(16)) + struct.pack("<I", 8) + bytes(4)
        sec = types.SimpleNamespace(name=".data", data=data, relocs=[(16, 7, 6), (2, 7, 6)])
        sym = lambda name, value: types.SimpleNamespace(name=name, section=1, value=value, storage=2)
        c = types.SimpleNamespace(sections={1: sec}, symbols={0: sym("A", 0), 1: sym("B", 12), 2: sym("C", 16)})
        self.assertEqual(inventory.coff_extent(c, c.symbols[0]), (12, [(2, 7, struct.unpack("<I", data[2:6])[0])]))
        self.assertEqual(inventory.coff_extent(c, c.symbols[2]), (8, [(0, 7, 8)]))

    def test_bss_has_no_extent(self):
        sec = types.SimpleNamespace(name=".bss", data=b"", relocs=[])
        s = types.SimpleNamespace(name="X", section=1, value=0, storage=2)
        self.assertIsNone(inventory.coff_extent(types.SimpleNamespace(sections={1: sec}, symbols={0: s}), s))


def fake_image(layout, base=0x400000):
    """LAYOUT: [(name, va, bytes)]: a PE-like object with those sections laid out one after another in its data."""
    data, sections, off = bytearray(0x400), [], 0x400
    for name, va, body in layout:
        sections.append((name, va, len(body), off, len(body)))
        data += body
        off += len(body)
    return types.SimpleNamespace(image_base=base, sections=sections, data=bytes(data))


class Aligned(unittest.TestCase):
    def test_data_pointers_rebase_and_code_pointers_remain(self):
        w = lambda *v: b"".join(struct.pack("<I", x) for x in v)
        retail = fake_image([(".text", 0x401000, bytes(0x100)),
                             (".rdata", 0x402000, w(0x403010, 0x401020) + b"abcd"),
                             (".data", 0x403000, bytes(0x20))])
        ours = fake_image([(".text", 0x401000, bytes(0x200)),
                           (".rdata", 0x404000, w(0x405010, 0x401030) + b"abcd"),
                           (".data", 0x405000, bytes(0x20))])
        r = inventory.aligned_compare(retail, ours)[".rdata"]
        self.assertEqual(r["compared"], 12)
        self.assertEqual(r["data_pointer"], 0)                   # 0x405010 moved by .data's shift to 0x403010
        self.assertEqual(r["code_pointer"], 1)                   # 0x401020 vs 0x401030: the code still moved
        self.assertEqual(r["content"], 0)
        self.assertEqual(r["equal"], 11)

    def test_rvas_rebase_only_inside_the_given_regions(self):
        w = lambda *v: b"".join(struct.pack("<I", x) for x in v)
        retail = fake_image([(".text", 0x401000, bytes(0x100)), (".rdata", 0x402000, w(0x2008, 0x2008, 0))])
        ours = fake_image([(".text", 0x401000, bytes(0x200)), (".rdata", 0x404000, w(0x4008, 0x4008, 0))])
        r = inventory.aligned_compare(retail, ours, [(0x404000, 0x404004)])[".rdata"]
        self.assertEqual(r["equal"], 12 - 1)                     # the first word is an RVA (rebased); the second is not


if __name__ == "__main__":
    unittest.main()
