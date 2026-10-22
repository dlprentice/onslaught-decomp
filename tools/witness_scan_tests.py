"""Unit tests for tools/witness_scan.py (no compiles): `python3 -m unittest tools.witness_scan_tests`."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import witness_scan as ws  # noqa: E402


class Ranges(unittest.TestCase):
    def test_ranges_and_lists(self):
        self.assertEqual(ws.parse_range("0-3,7,9-10"), [0, 1, 2, 3, 7, 9, 10])


class Anchors(unittest.TestCase):
    LINES = ['#include "common.h"', '#include "a.h"', "int x;", "extern SINT\tperforming_stress_test;"]

    def test_first_and_last_include(self):
        self.assertEqual(ws.anchor_line(self.LINES, ws.W["fgr"], "first"), 0)
        self.assertEqual(ws.anchor_line(self.LINES, ws.W["fgr"], "last"), 1)
        self.assertEqual(ws.anchor_line(self.LINES, ws.W["fgr"]), 1)

    def test_spec_anchor_must_match_once(self):
        self.assertEqual(ws.anchor_line(self.LINES, ws.W["dds"]), 3)
        with self.assertRaises(SystemExit):
            ws.anchor_line(self.LINES[:3], ws.W["dds"])


class Judge(unittest.TestCase):
    def test_pass_and_fail(self):
        ok = "match        00470650 CGame__DrawDebugStuff     src/game.cpp\nmatch 00470660 Other src/game.cpp\n"
        bad = "bytes        00470650 CGame__DrawDebugStuff     src/game.cpp  (1 bytes differ)\n"
        self.assertTrue(ws.judge(ok, "", ws.W["dds"])["pass"])
        self.assertFalse(ws.judge(bad, "", ws.W["dds"])["pass"])
        self.assertFalse(ws.judge("", "", ws.W["dds"])["pass"])
        self.assertFalse(ws.judge(ok + "src/game.cpp: compile failed\n", "", ws.W["dds"])["pass"])

    def test_dmg_row(self):
        ok = "match        00440c70 CDamage__LoadDamageTexture   src/damage.cpp\n"
        bad = "bytes        00440c70 CDamage__LoadDamageTexture   src/damage.cpp  (219 bytes differ)\n"
        self.assertTrue(ws.judge(ok, "", ws.W["dmg"])["pass"])
        self.assertFalse(ws.judge(bad, "", ws.W["dmg"])["pass"])

    def test_cpd_rows_all_must_match(self):
        a = "match 004c24c0 CPDTimeline__VFunc_6 src/ParticleDescriptor.cpp\nmatch 004c25c0 CPDTimeline__VFunc_7 src/p.cpp\n"
        b = a + "size  004c2620 CPDTimeline__VFunc_9 src/p.cpp (4 bytes differ)\n"
        self.assertTrue(ws.judge(a, "", ws.W["cpd"])["pass"])
        self.assertFalse(ws.judge(b, "", ws.W["cpd"])["pass"])


if __name__ == "__main__":
    unittest.main()
