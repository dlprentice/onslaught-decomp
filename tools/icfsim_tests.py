"""Focused tests for tools/icfsim.py: Microsoft's qsort tie order, the /VERBOSE parsing and the pass-1 record rules.
No linker, specimen or library needed."""
import unittest

from tools import binfmt, icfsim


def lcg_keys(n):
    """The keys of the qsort probe that ran against MSVCRT.DLL 6.00.8797 and Wine's builtin (seed 12345, mod 37)."""
    seed, keys = 12345, []
    for _ in range(n):
        seed = (seed * 1103515245 + 12345) & 0xffffffff
        seed -= (1 << 32) if seed & 0x80000000 else 0
        q = seed >> 16
        keys.append(abs(q) % 37 * (1 if q >= 0 else -1))
    return keys


class Qsort(unittest.TestCase):
    def sort(self, n):
        keys = lcg_keys(n)
        return icfsim.ms_qsort(list(range(n)), lambda a, b: keys[a] - keys[b])

    def test_equal_keys_come_out_in_microsofts_order(self):
        # Original indices after MSVCRT.DLL 6.00.8797's qsort; Wine's builtin gives 14 18 where Microsoft gives 18 14.
        self.assertEqual(self.sort(19), [2, 1, 11, 16, 17, 0, 9, 4, 6, 7, 10, 8, 18, 14, 3, 5, 12, 15, 13])
        self.assertEqual(self.sort(40), [37, 2, 1, 19, 11, 36, 28, 16, 32, 17, 0, 35, 26, 9, 20, 24, 4, 25, 6, 7, 30,
                                         38, 10, 27, 8, 18, 14, 22, 21, 23, 31, 3, 39, 33, 5, 12, 15, 34, 29, 13])

    def test_short_partitions_move_the_largest_to_the_end(self):
        self.assertEqual(icfsim.ms_qsort([(1, "a"), (0, "b"), (1, "c")], lambda x, y: x[0] - y[0]),
                         [(0, "b"), (1, "c"), (1, "a")])


LOG = """Start Pass1
Searching Libraries
    Searching Z:\\x\\LIBCMT.LIB:
      Found _memcpy
        Loaded LIBCMT.LIB(memcpy.obj)
      Found __imp__Sleep@4
        Loaded KERNEL32.LIB(KERNEL32.dll)

    Selected symbol:
        "public: virtual int __thiscall A::F(void)" (?F@A@@UAEHXZ) from a.obj
    Replaced symbol(s):
        ".text" from Cimage.obj
        __fpclear from fpinit.obj
"""


class Log(unittest.TestCase):
    def test_fold_groups_name_symbols_and_objects(self):
        self.assertEqual(icfsim.fold_groups(LOG), [[("?F@A@@UAEHXZ", "a.obj"), (".text", "cimage.obj"),
                                                    ("__fpclear", "fpinit.obj")]])

    def test_loads_keep_their_order(self):
        loads, paths = icfsim.library_loads(LOG)
        self.assertEqual(loads, [("libcmt.lib", "memcpy.obj"), ("kernel32.lib", "kernel32.dll")])
        self.assertIn("libcmt.lib", paths)


def coff(sections, symbols):
    secs = {i: binfmt.Section(i, n, ch, b"\x90" * size, [(0, 0, 6)] * rel)
            for i, (n, ch, size, rel) in sections.items()}
    syms = {i: binfmt.Symbol(i, n, 0, sec, 0x20, st, aux) for i, (n, sec, st, aux) in symbols.items()}
    return binfmt.Coff(None, secs, syms)


def secaux(selection, assoc=0):
    return b"\0" * 12 + assoc.to_bytes(2, "little") + bytes([selection]) + b"\0" * 3


CODE = 0x60501020          # code, execute, read, COMDAT
TEXT = 0x60500020          # the same, not COMDAT


class Records(unittest.TestCase):
    def test_pass_one_rules(self):
        c = coff({1: (".text", TEXT, 32, 0), 2: (".text", CODE, 16, 1), 3: (".text$x", CODE, 18, 3),
                  4: (".text", CODE, 16, 0), 5: (".text", CODE, 21, 2), 6: (".text", CODE, 16, 0)},
                 {0: (".text", 1, 3, secaux(0)),                       # plain .text: never recorded
                  2: (".text", 2, 3, secaux(2)), 3: ("?F@@YAXXZ", 2, 2, b""),
                  4: (".text$x", 3, 3, secaux(5, assoc=2)),            # associative of section 2
                  6: (".text", 4, 3, secaux(2)), 7: ("?G@@YAXXZ", 4, 2, b""),          # already taken
                  8: (".text", 5, 3, secaux(2)), 9: ("_$E12", 5, 3, b""),             # initializer funclet
                  10: (".text", 6, 3, secaux(3)), 11: ("?S@@YAXXZ", 6, 3, b"")})      # static: named .text
        taken = {"?G@@YAXXZ"}
        recs = icfsim.object_records(c, "a.obj", taken)
        self.assertEqual([(r.size, r.relocs, r.name) for r in recs],
                         [(16, 1, "?F@@YAXXZ"), (18, 3, ".text$x"), (16, 0, ".text")])
        self.assertIn("?F@@YAXXZ", taken)

    def test_associative_follows_a_discarded_parent_out(self):
        c = coff({1: (".text", CODE, 16, 0), 2: (".text$x", CODE, 18, 3)},
                 {0: (".text", 1, 3, secaux(2)), 1: ("?F@@YAXXZ", 1, 2, b""), 2: (".text$x", 2, 3, secaux(5, assoc=1))})
        self.assertEqual(icfsim.object_records(c, "b.obj", {"?F@@YAXXZ"}), [])

    def test_selection_is_part_of_the_fold_key(self):
        # identical bodies: an out-of-line copy (NODUPLICATES) and an inline one (ANY) never fold together
        c = coff({1: (".text", CODE, 16, 0), 2: (".text", CODE, 16, 0), 3: (".text", CODE, 16, 0)},
                 {0: (".text", 1, 3, secaux(1)), 1: ("?F@@YAXXZ", 1, 2, b""),
                  2: (".text", 2, 3, secaux(2)), 3: ("?G@@YAXXZ", 2, 2, b""),
                  4: (".text", 3, 3, secaux(2)), 5: ("?H@@YAXXZ", 3, 2, b"")})
        f, g, h = (r.body for r in icfsim.object_records(c, "a.obj", set()))
        self.assertNotEqual(f, g)
        self.assertEqual(g, h)


class Report(unittest.TestCase):
    def test_comdat_symbols_lists_every_copy_with_its_selection(self):
        c = coff({1: (".text", CODE, 16, 0), 2: (".text", CODE, 16, 0), 3: (".text$x", CODE, 18, 3)},
                 {0: (".text", 1, 3, secaux(2)), 1: ("?F@@YAXXZ", 1, 2, b""),
                  2: (".text", 2, 3, secaux(1)), 3: ("?G@@YAXXZ", 2, 2, b""),
                  4: (".text$x", 3, 3, secaux(5, assoc=1))})
        self.assertEqual(icfsim.comdat_symbols(c), [("?F@@YAXXZ", 2, 1), ("?G@@YAXXZ", 1, 2)])


class Survivor(unittest.TestCase):
    def test_first_in_sorted_order_wins(self):
        recs = [icfsim.Record(16, 0, "?A@@YAXXZ", "a.obj", ()), icfsim.Record(48, 2, "?X@@YAXXZ", "a.obj", ()),
                icfsim.Record(16, 0, "?B@@YAXXZ", "b.obj", ("??_EB@@UAEPAXI@Z",))]
        pos = icfsim.sorted_positions(recs)
        self.assertEqual(icfsim.survivor([("?A@@YAXXZ", "a.obj"), ("?B@@YAXXZ", "B.obj")], pos), ("?B@@YAXXZ", "b.obj"))
        self.assertEqual(icfsim.survivor([("??_EB@@UAEPAXI@Z", "b.obj"), ("?A@@YAXXZ", "a.obj")], pos),
                         ("??_EB@@UAEPAXI@Z", "b.obj"))
        self.assertIsNone(icfsim.survivor([("?C@@YAXXZ", "c.obj")], pos))

    def test_groups_with_the_same_names_take_their_shared_keys_in_print_order(self):
        recs = [icfsim.Record(13, 0, ".text", "w.obj", (), 1), icfsim.Record(13, 0, ".text", "o.obj", (), 1),
                icfsim.Record(49, 1, ".text", "o.obj", (), 2), icfsim.Record(49, 1, ".text", "w.obj", (), 2)]
        pos = icfsim.sorted_positions(recs)
        group = [(".text", "w.obj"), (".text", "o.obj")]
        # Four records sort by selection to [1, 0, 3, 2]: o.obj first for the 13-byte key, w.obj for the 49-byte one.
        self.assertEqual(icfsim.survivor(group, pos, 0), (".text", "o.obj"))
        self.assertEqual(icfsim.survivor(group, pos, 1), (".text", "w.obj"))


if __name__ == "__main__":
    unittest.main()
