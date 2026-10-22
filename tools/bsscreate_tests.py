"""Focused test for tools/bsscreate.py: one synthetic source, compiled with the real toolchain under the precompiled
header, pins the creation rules (definition order reversed; an extern-declared object mentioned in an earlier body;
a class static through an in-class accessor; function-local statics at first use; constant and plain-aggregate
initializers in a second group) and checks that the prediction equals the compiled order. Skipped without the
toolchain. One compile and one preprocessing pass."""
import re
import tempfile
import unittest
from pathlib import Path

from tools import bsscreate, decomp

SOURCE = """#include "common.h"
struct BcV { BcV(); int x; };
extern BcV bcEarly;
inline int BcUseEarly() { return bcEarly.x; }
struct BcK { static int ks; static int Get() { return ks; } };
static int bcA;
BcV bcObj;
static int bcB;
BcV bcEarly;
int BcK::ks;
static int bcConst = 0;
static int bcArr[2] = { 0, 0 };
BcV bcCopy = bcObj;
int BcLocals(int k) { static int la; static int lb; lb = k; la = k + 1; return la + lb; }
static int bcC;
int BcUse() { return bcA + bcB + bcC + bcConst + bcArr[1] + bcObj.x + bcCopy.x + BcUseEarly() + BcK::Get() + BcLocals(1); }
"""
# reverse creation: bcEarly (BcUseEarly's body), ks (BcK's accessor), bcA, bcObj, bcB, bcCopy (a class object stays in
# the first group however initialized), lb then la (first use), bcC; then the initialized ones in definition order
EXPECTED = ["bcC", "la", "lb", "bcCopy", "bcB", "bcObj", "bcA", "ks", "bcEarly", "bcConst", "bcArr"]


def ident(name: str) -> str:
    return re.match(r"[_?]*(\w+)", name).group(1)


@unittest.skipUnless((decomp.VC6 / "VC98/Bin/CL.EXE").exists(), "needs the Visual C++ 6 toolchain")
class CreationOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # the probe lives under build/ (ignored), never in src/: compile_probe puts src/ on the include path
        with tempfile.TemporaryDirectory(prefix="bsscreate-test-", dir=decomp.BUILD) as temp:
            src = Path(temp) / "bsscreate_probe.cpp"
            obj = Path(temp) / "bsscreate_probe.obj"
            src.write_text(SOURCE)
            result = bsscreate.compile_probe(src, obj)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            cls.text = bsscreate.preprocess(src)
            cls.ours = [ident(n) for n in bsscreate.bss_symbols(obj)[0]]
            cls.prediction = bsscreate.predict(obj, cls.text)

    def test_compiler_lays_out_by_creation(self):
        self.assertEqual(self.ours, EXPECTED)

    def test_prediction_matches_the_compiler(self):
        ours, order, _points, _second = self.prediction
        self.assertEqual(order, ours)
        self.assertEqual([ident(n) for n in order], EXPECTED)


class Targets(unittest.TestCase):
    def test_symbol_kinds(self):
        self.assertEqual(bsscreate.parse_target("_?count@?1??BuildGrid@CDXWater@@QAEXMK@Z@4HA"),
                         ("count", "local", "CDXWater", "BuildGrid"))
        self.assertEqual(bsscreate.parse_target("?sConfigurations@UBattleEngineConfigurations@@0JA"),
                         ("sConfigurations", "member", "UBattleEngineConfigurations", None))
        self.assertEqual(bsscreate.parse_target("?SOUND@@3VCPCSoundManager@@A"), ("SOUND", "global", None, None))
        self.assertEqual(bsscreate.parse_target("_sShader"), ("sShader", "global", None, None))
        self.assertIsNone(bsscreate.parse_target("_$S46"))


if __name__ == "__main__":
    unittest.main()
