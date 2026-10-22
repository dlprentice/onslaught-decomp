"""Focused tests for tools/linkcmp.py: map parsing, the loaded view, section and symbol tallies. No specimen needed."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools import linkcmp


def image(sections):
    """sections: [(name, va, vsize, raw bytes)] laid out one after another in the file."""
    data, rows = bytearray(), []
    for name, va, vsize, raw in sections:
        rows.append((name, va, vsize, len(data), len(raw)))
        data += raw
    return SimpleNamespace(data=bytes(data), sections=rows)


class MapFile(unittest.TestCase):
    def test_publics_with_object_and_flags(self):
        text = (" Timestamp is 3ed21313 (Mon May 26 09:13:55 2003)\n\n"
                "  Address         Publics by Value              Rva+Base     Lib:Object\n\n"
                " 0001:00000000       ?Set@C@@QAEXXZ             00401000 f   activereader.obj\n"
                " 0002:00000010       ?gValue@@3HA               005d8010     game.obj\n"
                " 0000:00000000       ___ImageBase               00400000     <linker-defined>\n")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.map"
            p.write_text(text)
            self.assertEqual(linkcmp.read_map(p), {"?Set@C@@QAEXXZ": (0x401000, "activereader.obj"),
                                                   "?gValue@@3HA": (0x5D8010, "game.obj")})


class Sections(unittest.TestCase):
    def test_tail_past_raw_data_reads_as_zero_and_unmapped_bytes_differ(self):
        retail = image([(".data", 0x1000, 8, b"\1\2\0\0")])
        same = image([(".data", 0x1000, 8, b"\1\2")])
        short = image([(".data", 0x1000, 4, b"\1\2\0\0")])
        self.assertEqual(linkcmp.compare_sections(retail, same, 4)[0]["equal"], 8)
        row = linkcmp.compare_sections(retail, short, 4)[0]
        self.assertEqual((row["equal"], row["first_diffs"]), (4, [("00001004", 4)]))

    def test_differing_bytes_are_reported_as_ranges(self):
        retail = image([(".text", 0x401000, 6, b"\x90" * 6)])
        cand = image([(".text", 0x401000, 6, b"\x90\xcc\xcc\x90\x90\xcc")])
        row = linkcmp.compare_sections(retail, cand, 8)[0]
        self.assertEqual((row["equal"], row["first_diffs"]), (3, [("00401001", 2), ("00401005", 1)]))


class Symbols(unittest.TestCase):
    def test_tally_counts_present_matching_and_moved_symbols(self):
        publics = {"a": (0x10, "x.obj"), "b": (0x24, "x.obj")}
        out = linkcmp.compare_symbols(publics, {"a": 0x10, "c": 0x30}, {"b": 0x20})
        self.assertEqual(out["implied_symbols"]["at_retail_address"], 1)
        self.assertEqual(out["implied_symbols"]["in_map"], 1)
        self.assertEqual(out["annotated_functions"]["elsewhere"], [("b", "00000024", "00000020")])


if __name__ == "__main__":
    unittest.main()
