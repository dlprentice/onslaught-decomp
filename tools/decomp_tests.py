"""Regression checks for reporting, RTTI candidates and diagnostics; no retail compiler or game run."""
import tempfile
import collections
import unittest
import contextlib
import hashlib
import os
import stat
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from tools import decomp
from tools.binfmt import Coff, Section, Symbol, SCN_CNT_CODE, SYM_EXTERNAL


class DisassemblyInputs(unittest.TestCase):
    def test_overlapping_calls_read_their_own_bytes_and_address(self):
        with tempfile.TemporaryDirectory(prefix="bea-disassembly-test-") as temp:
            root = Path(temp)
            barrier = threading.Barrier(2)
            paths = []

            def objdump(command, **kwargs):
                path = Path(command[-1])
                address = int(command[-2].split("=", 1)[1], 16)
                paths.append(path)
                barrier.wait(timeout=5)
                return SimpleNamespace(stdout=f"{address:x}:\t{path.read_bytes().hex()}\n")

            with patch.object(decomp, "BUILD", root), patch.object(decomp.subprocess, "run", side_effect=objdump):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    first = pool.submit(decomp.disassemble, b"\x90\xc3", 0x401000)
                    second = pool.submit(decomp.disassemble, b"\x40\x40\xc3", 0x502000)
                    self.assertEqual(first.result(timeout=10), ["401000:\t90c3"])
                    self.assertEqual(second.result(timeout=10), ["502000:\t4040c3"])
            self.assertEqual(len(set(paths)), 2)
            self.assertEqual(list(root.iterdir()), [])

    def test_failed_objdump_removes_its_private_input(self):
        with tempfile.TemporaryDirectory(prefix="bea-disassembly-test-") as temp:
            root = Path(temp)
            with patch.object(decomp, "BUILD", root), \
                    patch.object(decomp.subprocess, "run", side_effect=OSError("authored launch failure")):
                with self.assertRaisesRegex(OSError, "authored launch failure"):
                    decomp.disassemble(b"\xc3", 0x401000)
            self.assertEqual(list(root.iterdir()), [])


class ToolchainHeaders(unittest.TestCase):
    def test_every_include_tree_refuses_changed_missing_or_extra_files(self):
        # Include extensionless headers: restricting validation to *.h silently misses STL inputs.
        with tempfile.TemporaryDirectory(prefix="bea-headers-test-") as temp:
            root = Path(temp)
            config, vc6, dx9, samples = root / "config", root / "vc6", root / "dx9", root / "samples"
            config.mkdir()
            tool = vc6 / "VC98/Bin/CL.EXE"
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b"authored compiler fixture")
            (config / "toolchain.sha256").write_text(
                hashlib.sha256(tool.read_bytes()).hexdigest() + " VC98/Bin/CL.EXE\n")
            fixtures = {"MATH.H": b"authored math header\n", "VECTOR": b"authored vector header\n"}
            manifest = "".join(hashlib.sha256(data).hexdigest() + "  ./" + name + "\n"
                               for name, data in sorted(fixtures.items()))
            digest = hashlib.sha256(manifest.encode()).hexdigest()
            for headers, pin in ((vc6 / "VC98/Include", "vc6-include.sha256"),
                                 (dx9, "dx9sdk-include.sha256")):
                headers.mkdir(parents=True)
                for name, data in fixtures.items():
                    (headers / name).write_bytes(data)
                (config / pin).write_text(digest + " fixture\n")
            # the sample framework's headers are pinned file by file, with comment lines for their provenance
            samples.mkdir()
            for name, data in fixtures.items():
                (samples / name).write_bytes(data)
            (config / "dx9samples-include.sha256").write_text("# fixture provenance\n" + "".join(
                hashlib.sha256(data).hexdigest() + " " + name + "\n" for name, data in sorted(fixtures.items())))
            with patch.object(decomp, "CONFIG", config), patch.object(decomp, "VC6", vc6), \
                    patch.object(decomp, "DX9_INCLUDE", dx9), patch.object(decomp, "DX9_SAMPLES_INCLUDE", samples):
                decomp.check_toolchain()
                for headers in (vc6 / "VC98/Include", dx9, samples):
                    for mutation in ("content", "missing", "extra"):
                        with self.subTest(headers=headers.name, mutation=mutation):
                            target = headers / "VECTOR"
                            if mutation == "content":
                                target.write_bytes(b"changed vector header\n")
                            elif mutation == "missing":
                                target.unlink()
                            else:
                                (headers / "SHADOW.H").write_bytes(b"unexpected include candidate\n")
                            with self.assertRaisesRegex(SystemExit, "pinned .* headers"):
                                decomp.check_toolchain()
                            target.write_bytes(fixtures["VECTOR"])
                            (headers / "SHADOW.H").unlink(missing_ok=True)
                            decomp.check_toolchain()


class PrecompiledHeader(unittest.TestCase):
    def test_default_sources_use_the_pch_unless_listed(self):
        with tempfile.TemporaryDirectory(prefix="bea-pch-test-") as temp:
            config = Path(temp)
            (config / "flags.txt").write_text("/O2 /GX\n")
            (config / "file-flags.txt").write_text("own.cpp: /O1\n")
            (config / "no-pch.txt").write_text("# fixture\nplain.cpp: opens with windows.h, not common.h\n")
            pch = Path(temp) / "common-fixture.pch"
            with patch.object(decomp, "CONFIG", config), patch.object(decomp, "pch_file", lambda: pch):
                src = decomp.ROOT / "src"
                self.assertEqual(decomp.flags_for(src / "game.cpp"),
                                 ["/O2", "/GX", "/Yucommon.h", f"/Fp{decomp.winpath(pch)}"])
                self.assertEqual(decomp.flags_for(src / "plain.cpp"), ["/O2", "/GX"])
                self.assertEqual(decomp.flags_for(src / "own.cpp"), ["/O1"])
                self.assertEqual(decomp.flags_for(decomp.PCH_SOURCE), ["/O2", "/GX"])
        self.assertNotIn(decomp.PCH_SOURCE, decomp.sources())

    def test_pch_include_keeps_the_sources_relative_prefix(self):
        with tempfile.TemporaryDirectory(prefix="bea-pch-test-") as temp:
            sub = Path(temp) / "sub.cpp"
            sub.write_text('#define ISCRIPT_CPP\n#include "..\\common.h"\n#include "..\\monitor.h"\n')
            root = Path(temp) / "root.cpp"
            root.write_text('#include\t"Common.h"\n')
            none = Path(temp) / "none.cpp"
            none.write_text('#include "asminstruction.h"\n')
            self.assertEqual(decomp.pch_include(sub), "..\\common.h")
            self.assertEqual(decomp.pch_include(root), "common.h")
            self.assertEqual(decomp.pch_include(none), "common.h")


class ObjectPatches(unittest.TestCase):
    @staticmethod
    def write_object(path: Path, body: bytes) -> None:
        """A one-section i386 COFF with a function symbol `_f` at offset 0 of its code section."""
        import struct
        nsym, sec_hdr, raw = 1, 40, 20 + 40
        header = struct.pack("<HHIIIHH", 0x14C, 1, 0, raw + len(body), nsym, 0, 0)
        section = b".text\0\0\0" + struct.pack("<IIIIIIHHI", 0, 0, len(body), raw, 0, 0, 0, 0, 0x60000020)
        symbol = b"_f\0\0\0\0\0\0" + struct.pack("<IhHBB", 0, 1, 0x20, 2, 0)
        path.write_bytes(header + section + body + symbol + struct.pack("<I", 4))

    def test_expected_bytes_are_replaced_and_anything_else_stops_the_build(self):
        with tempfile.TemporaryDirectory() as d:
            obj, src = Path(d) / "a.obj", Path(d) / "a.cpp"
            patch_ = decomp.ObjectPatch("a.cpp", "_f", 2, bytes.fromhex("c64401ff00"), bytes.fromhex("c64408ff00"), "test")
            self.write_object(obj, bytes.fromhex("9090c64401ff00c3"))
            with contextlib.redirect_stdout(open(os.devnull, "w")):
                self.assertEqual(decomp.apply_object_patches(src, obj, [patch_]), 1)
            self.assertIn(bytes.fromhex("9090c64408ff00c3"), obj.read_bytes())
            # applying it again finds the patched bytes, not the expected ones: the build stops
            with self.assertRaises(SystemExit):
                decomp.apply_object_patches(src, obj, [patch_])
            # another source's patch leaves the object alone
            self.assertEqual(decomp.apply_object_patches(Path(d) / "b.cpp", obj, [patch_]), 0)

    def test_the_config_rows_parse(self):
        rows = decomp.object_patches()
        self.assertTrue(all(len(r.expected) == len(r.replacement) for r in rows))


class WholeFunctionExtent(unittest.TestCase):
    def compare(self, compiled, retail, extent, address=0x401000, relocs=None):
        checker = decomp.Checker.__new__(decomp.Checker)
        checker.retail = {address: decomp.RetailFunction(address, extent, "authored")}
        checker.discovered, checker.witness, checker.implied_by = {}, {}, {}
        checker.image = SimpleNamespace(read=lambda va, size: retail[:size] if va == address else None)
        coff = SimpleNamespace(sections={1: SimpleNamespace(data=compiled, relocs=relocs or [])})
        result = checker.compare(coff, 1, address, {})
        return result, checker

    def test_identical_prefix_cannot_match_or_discover_relocations(self):
        # The relocation deliberately lacks a symbol table: refusal must precede target discovery.
        result, checker = self.compare(b"\x90" * 16, b"\x90" * 16 + b"\xb8\x01\x00\x00\x00\xc3",
                                       22, relocs=[(0, 0, decomp.REL_DIR32)])
        self.assertFalse(result[2])
        self.assertIn("requires 22", result[1][0])
        self.assertEqual((checker.discovered, checker.witness, checker.implied_by), ({}, {}, {}))

    def test_exact_body_matches(self):
        self.assertEqual(self.compare(b"\x31\xc0\xc3", b"\x31\xc0\xc3", 3)[0], ([], [], True))

    def test_short_section_retains_useful_byte_diagnostics(self):
        result, _ = self.compare(b"\x90\x90", b"\x90\x31\xc0\xc3", 4)
        self.assertEqual(result[0], [1])
        self.assertIn("requires 4", result[1][0])
        self.assertFalse(result[2])

    def test_matching_comdat_padding_is_allowed(self):
        data = b"\x31\xc0\xc3" + b"\x90" * 13
        self.assertEqual(self.compare(data, data, 3)[0], ([], [], True))

    def test_padding_is_not_ignored(self):
        result, _ = self.compare(b"\x31\xc0\xc3\xcc", b"\x31\xc0\xc3\x90", 3)
        self.assertEqual(result[0], [3])
        self.assertFalse(result[2])

    def test_separate_funclet_uses_its_own_extent(self):
        self.assertTrue(self.compare(b"\xc3", b"\xc3", 1, address=decomp.FUNCLETS)[0][2])
        self.assertFalse(self.compare(b"\x90", b"\x90\xc3", 2, address=decomp.FUNCLETS)[0][2])


class ProvenLibraryBindings(unittest.TestCase):
    def test_proven_entries_reach_existing_scanners_without_an_exact_caller(self):
        with patch.object(decomp,'PeImage',return_value=SimpleNamespace()), \
                patch.object(decomp,'retail_functions',return_value={}):
            checker = decomp.Checker()
        self.assertEqual(checker.discovered['__CIacos'], {0x55f380})
        self.assertEqual(checker.discovered['__CIasin'], {0x55dcb0})
        self.assertEqual(checker.discovered['__CIfmod'], {0x55e3ea})
        self.assertEqual(checker.discovered['_fmod'], {0x55e3e0})
        self.assertEqual(checker.discovered['__CIpow'], {0x55fa40})
        self.assertEqual(checker.discovered['_pow'], {0x55fa59})
        self.assertEqual(checker.discovered['_floor'], {0x55dfe7})
        self.assertEqual(checker.discovered['_ceil'], {0x55eb3d})
        self.assertEqual(checker.discovered['??_L@YGXPAXIHP6EX0@Z1@Z'], {0x55dc20})
        self.assertEqual(checker.witness[('__CIacos',0x55f380)], 0x55f380)

    def compare_call(self, name, destination, placed=None):
        address = 0x401000
        raw = b'\xe8' + ((destination-address-5) & 0xffffffff).to_bytes(4,'little') + b'\xc3'
        checker = decomp.Checker.__new__(decomp.Checker)
        checker.retail = {address: decomp.RetailFunction(address, 6, 'authored caller')}
        checker.discovered, checker.witness, checker.implied_by = {}, {}, {}
        checker.image = SimpleNamespace(
            read=lambda a,n: raw[a-address:a-address+n],
            u32=lambda a: int.from_bytes(raw[a-address:a-address+4], 'little'))
        coff = Coff(Path('Authored.obj'),
                    {1: Section(1, '.text', SCN_CNT_CODE, b'\xe8\0\0\0\0\xc3',
                                [(1,0,decomp.REL_REL32)])},
                    {0: Symbol(0,name,0,0,0x20,SYM_EXTERNAL,b'')})
        return checker.compare(coff,1,address,placed or {}), checker

    def test_consistent_wrong_inverse_trig_name_is_not_a_match(self):
        result, checker = self.compare_call('__CIacos', 0x55dcb0)
        self.assertEqual(result[0], [])  # All nonrelocation bytes really agree.
        self.assertFalse(result[2])
        self.assertIn('independently identified library entry is 0055f380', result[1][0])
        self.assertEqual(checker.discovered, {})

    def test_proven_entry_identities_and_their_swaps(self):
        pairs = [('__CIasin',0x55dcb0,0x55f380), ('__CIacos',0x55f380,0x55dcb0),
                 ('_asin',0x55dcc4,0x55f394), ('_acos',0x55f394,0x55dcc4),
                 ('__CIfmod',0x55e3ea,0x55e3e0), ('_fmod',0x55e3e0,0x55e3ea),
                 ('__CIpow',0x55fa40,0x55fa59), ('_pow',0x55fa59,0x55fa40),
                 ('_floor',0x55dfe7,0x55eb3d), ('_ceil',0x55eb3d,0x55dfe7)]
        # Constructor and destructor iteration are different CRT entries. A
        # consistent caller or stale annotation must not substitute the latter.
        pairs.append(('??_L@YGXPAXIHP6EX0@Z1@Z',0x55dc20,0x55db8a))
        for name,right,wrong in pairs:
            with self.subTest(name=name):
                result, checker = self.compare_call(name,right)
                self.assertEqual(result, ([],[],True))
                self.assertEqual(checker.discovered, {name:{right}})
                self.assertEqual(checker.implied_by[0x401000], {name})
                self.assertFalse(self.compare_call(name,wrong)[0][2])
                # A stale source annotation cannot overrule independently proved identity.
                self.assertFalse(self.compare_call(name,wrong,{name:wrong})[0][2])

    def test_sdk_dispatch_bindings_reject_swaps_even_with_stale_placement(self):
        entries = [('_D3DXVec3TransformCoord@12', 0x576161),
                   ('_D3DXVec3Project@24', 0x576297),
                   ('_D3DXMatrixMultiply@12', 0x5768fe),
                   ('_D3DXMatrixInverse@12', 0x576e0a),
                   ('_D3DXMatrixTranslation@16', 0x577267)]
        for index, (name, right) in enumerate(entries):
            wrong = entries[(index + 1) % len(entries)][1]
            with self.subTest(name=name):
                self.assertEqual(self.compare_call(name, right)[0], ([], [], True))
                self.assertFalse(self.compare_call(name, wrong)[0][2])
                self.assertFalse(self.compare_call(name, wrong, {name: wrong})[0][2])

    def test_normal_and_intrinsic_abi_entries_cannot_be_interchanged(self):
        self.assertFalse(self.compare_call('__CIacos',0x55f394)[0][2])
        self.assertFalse(self.compare_call('_asin',0x55dcb0)[0][2])

    def test_same_section_and_absolute_definitions_cannot_override_identity(self):
        checker = decomp.Checker.__new__(decomp.Checker)
        for section,value in ((1,0),(-1,0x55dcb0)):
            with self.subTest(section=section):
                sym = Symbol(0,'__CIacos',value,section,0x20,SYM_EXTERNAL,b'')
                result = checker.check_target(SimpleNamespace(),sym,0x55dcb0,0x55dcb0,1,{})
                self.assertIsNot(result,True)
                self.assertIn('0055f380',result)

    def test_unidentified_external_remains_explicit_discovery(self):
        result, checker = self.compare_call('_authored_unknown',0x550000)
        self.assertEqual(result, ([],[],True))
        self.assertEqual(checker.discovered, {'_authored_unknown':{0x550000}})


class FoldedBodyReports(unittest.TestCase):
    def setUp(self):
        self.address = 0x00505D00
        self.retail = {
            self.address: decomp.RetailFunction(self.address, 9, "CSPtrSet__ctor"),
            0x00505D10: decomp.RetailFunction(0x00505D10, 7, "Other"),
            decomp.FUNCLETS: decomp.RetailFunction(decomp.FUNCLETS, 5, "Unwind"),
        }
        self.results = [
            decomp.FunctionResult(self.address, "waypoint_alias", "src/WaypointManager.cpp", "match", 16),
            decomp.FunctionResult(self.address, "camera_alias", "src/Camera.cpp", "match", 16),
            decomp.FunctionResult(self.address, "wrong_alias", "src/A.cpp", "bytes", 16, [3]),
            decomp.FunctionResult(0x00505D10, "other", "src/A.cpp", "relocations", 16),
            decomp.FunctionResult(0x00505D10, "unplaced", "src/A.h:1", "unplaced", 0),
            decomp.FunctionResult(decomp.FUNCLETS, "unwind", "src/A.cpp", "match", 16),
        ]

    def test_folded_aliases_count_one_address_and_extent(self):
        score = decomp.score(self.results, self.retail)
        self.assertEqual(score["matchedFunctions"], 1)
        self.assertEqual(score["matchedBytes"], 9)
        self.assertEqual(score["attempted"], 2)
        self.assertEqual(score["gameFunctions"], 2)
        self.assertEqual(score["funclets"], 1)

    def test_representative_is_stable_and_nonmatch_does_not_hide_match(self):
        for results in (self.results, list(reversed(self.results))):
            matches = decomp.unique_matches(results)
            self.assertEqual([r.address for r in matches], [self.address, decomp.FUNCLETS])
            self.assertEqual(matches[0].symbol, "camera_alias")

    def test_unmapped_exact_body_is_visible_but_not_scored(self):
        results = self.results + [decomp.FunctionResult(0x00505D20, "gap", "src/A.cpp", "match", 16)]
        self.assertEqual(decomp.score(results, self.retail)["matchedFunctions"], 1)
        self.assertEqual(len(decomp.unique_matches(results)), 3)

    def test_readme_emits_one_row_per_body(self):
        with tempfile.TemporaryDirectory(prefix="onslaught-decomp-test-") as temp:
            root = Path(temp)
            readme = root / "README.md"
            readme.write_text("before\n<!-- score:begin -->\nold\n<!-- score:end -->\nafter\n")
            with patch.object(decomp, "ROOT", root):
                decomp.write_readme(decomp.score(self.results, self.retail), self.results, self.retail)
            text = readme.read_text()
            self.assertEqual(text.count("| `00505d00` |"), 1)
            self.assertIn("src/Camera.cpp", text)
            self.assertNotIn("waypoint_alias", text)
            self.assertTrue(text.endswith("<!-- score:end -->\nafter\n"))


class UnplacedAnnotationReports(unittest.TestCase):
    def test_explicit_missing_symbol_is_not_reported_as_the_next_definition(self):
        source = decomp.ROOT / "src/Authored.cpp"
        coff = Coff(Path("Authored.obj"), {}, {})
        checker = SimpleNamespace(discovered={}, implied_by={})
        for explicit, expected in (("??1Part@@QAE@XZ", "??1Part@@QAE@XZ"),
                                   (None, "Nearby::Unrelated")):
            with self.subTest(explicit=explicit):
                mark = decomp.Annotation(0x401000, source, 4, "Nearby::Unrelated", explicit, 0)
                with patch.object(decomp, "annotations", return_value=[mark]), \
                        patch.object(decomp, "Checker", return_value=checker), \
                        patch.object(decomp, "sources", return_value=[source]), \
                        patch.object(decomp, "parse_coff", return_value=coff), \
                        patch.object(decomp, "demangle", return_value={}), \
                        patch.object(decomp, "check_vtables", return_value=[]):
                    results, _ = decomp.check({source: coff.path})
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0].status, "unplaced")
                self.assertEqual(results[0].symbol, expected)
                self.assertEqual(results[0].size, 0)


class RetailVtableSelection(unittest.TestCase):
    def select(self, rows):
        with tempfile.TemporaryDirectory(prefix="onslaught-decomp-test-") as temp:
            config = Path(temp)
            (config / "classes.tsv").write_text(
                "class\tsubobjectOffset\tvftable\tslots\n" + "\n".join("\t".join(row) for row in rows) + "\n")
            with patch.object(decomp, "CONFIG", config):
                return decomp.retail_vtables()

    def test_empty_scan_hits_do_not_replace_real_table(self):
        rows = [("Value", "0", "005da278", "4"), ("Value", "0", "0065a420", "0"),
                ("Value", "0", "0065c364", "0")]
        for order in (rows, list(reversed(rows))):
            self.assertEqual(self.select(order), {("Value", 0): (0x005DA278, 4)})

    def test_conflicting_nonempty_tables_stay_unresolved(self):
        for second in (("005da280", "4"), ("005da278", "5")):
            rows = [("Value", "0", "005da278", "4"), ("Value", "0", *second)]
            self.assertEqual(self.select(rows), {})

    def test_repeated_rows_and_secondary_subobjects(self):
        row = ("Value", "0", "005da278", "4")
        self.assertEqual(self.select([row, row, ("Value", "8", "005da290", "3")]),
                         {("Value", 0): (0x005DA278, 4), ("Value", 8): (0x005DA290, 3)})

    def test_only_empty_hits_prove_nothing(self):
        self.assertEqual(self.select([("Value", "0", "0065a420", "0")]), {})


class VtableConsistency(unittest.TestCase):
    """Authored objects exercise the real whole-check path, without VC6 or a retail specimen."""

    def run_case(self, entries, caller_target=None, caller_table=False, reverse=False):
        checker = decomp.Checker.__new__(decomp.Checker)
        checker.discovered, checker.witness, checker.implied_by = {}, {}, {}
        checker.retail = {0x401000: decomp.RetailFunction(0x401000, 6, "Caller")}
        raw, coffs, names, retail = {}, {}, {}, {}
        class_rows = []

        def put(address, data):
            raw.update({address + i: value for i, value in enumerate(data)})

        def read(address, size):
            return bytes(raw[address + i] for i in range(size)) if all(address + i in raw for i in range(size)) else None

        def u32(address):
            value = read(address, 4)
            return int.from_bytes(value, "little") if value is not None else None

        checker.image = SimpleNamespace(read=read, u32=u32, imports={})
        first_source = decomp.ROOT / "src/First.cpp"
        for i, entry in enumerate(entries):
            cls = "First" if i == 0 else "Second"
            vt = 0x600000 + 0x100 * i
            table_name = f"??_7{cls}@@6B@"
            source = decomp.ROOT / f"src/{cls}.cpp"
            col = entry.get("col")          # /GR: a complete object locator pointer before the table
            data = entry.get("data", b"\0" * (8 if col is not None else 4))
            relocs = entry.get("relocs", [(0, 3, decomp.REL_DIR32), (4, 1, decomp.REL_DIR32)] if col is not None
                               else [(0, 1, decomp.REL_DIR32)])
            sections = {1: Section(1, ".rdata", 0, data, relocs)}
            symbols = {
                0: Symbol(0, table_name, entry.get("symbol_offset", 4 if col is not None else 0), 1, 0, SYM_EXTERNAL, b""),
                1: Symbol(1, "?Step@Base@@UAEXXZ", 0, 0, 0x20, SYM_EXTERNAL, b""),
                3: Symbol(3, entry.get("col_name", f"??_R4{cls}@@6B@"), 0, 0, 0, SYM_EXTERNAL, b""),
            }
            if col is not None:
                put(vt - 4, col.to_bytes(4, "little"))
            if i == 0 and caller_target is not None:
                target_symbol = 0 if caller_table else 1
                sections[2] = Section(2, ".text", SCN_CNT_CODE, b"\xb8\0\0\0\0\xc3",
                                      [(1, target_symbol, decomp.REL_DIR32)])
                symbols[2] = Symbol(2, "_Caller", 0, 2, 0x20, SYM_EXTERNAL, b"")
                put(0x401000, b"\xb8" + caller_target.to_bytes(4, "little") + b"\xc3")
            coffs[source] = Coff(Path(f"{cls}.obj"), sections, symbols)
            names[table_name] = f"const {cls}::`vftable'"
            if "base" in entry:
                names[table_name] += "{for `" + entry["base"] + "'}"
            retail[(cls, entry.get("offset", 0))] = (vt, entry.get("count", 1))
            class_rows.append(f"{cls}\t0\t{vt:08x}\t1\t{entry.get('bases', '')}\n")
            put(vt, entry["target"].to_bytes(4, "little") + b"\0" * 12)
        if reverse:
            coffs = dict(reversed(list(coffs.items())))
        objects = {source: coff.path for source, coff in coffs.items()}
        by_object = {coff.path: coff for coff in coffs.values()}
        marks = ([decomp.Annotation(0x401000, first_source, 1, "Caller", "_Caller", 0)]
                 if caller_target is not None else [])
        with tempfile.TemporaryDirectory(prefix="bea-vtable-test-") as temp:
            config = Path(temp)
            (config / "classes.tsv").write_text("class\tsubobjectOffset\tvftable\tslots\tbases\n" +
                                                "".join(class_rows))
            with patch.object(decomp, "CONFIG", config), \
                    patch.object(decomp, "Checker", return_value=checker), \
                    patch.object(decomp, "retail_vtables", return_value=retail), \
                    patch.object(decomp, "annotations", return_value=marks), \
                    patch.object(decomp, "sources", return_value=list(objects)), \
                    patch.object(decomp, "parse_coff", side_effect=by_object.__getitem__), \
                    patch.object(decomp, "demangle", return_value=names):
                results, checker = decomp.check(objects)
        return results, checker

    def test_table_conflict_rejects_both_tables_in_either_order(self):
        for reverse in (False, True):
            _, checker = self.run_case([{"target": 0x401100}, {"target": 0x401200}], reverse=reverse)
            self.assertTrue(all("places a symbol" in verdict for _, verdict in checker.vtables))

    def test_late_table_conflict_rejects_direct_function_dependency(self):
        results, checker = self.run_case([{"target": 0x401200}], caller_target=0x401100)
        self.assertEqual(results[0].status, "relocations")
        self.assertIn("Step@Base", results[0].notes[0])
        self.assertNotEqual(checker.vtables[0][1], "match")

    def test_exact_constructor_is_separate_from_bad_method_table(self):
        results, checker = self.run_case([{"target": 0x401100}, {"target": 0x401200}],
                                         caller_target=0x600000, caller_table=True)
        self.assertEqual(results[0].status, "match")
        self.assertTrue(all(verdict != "match" for _, verdict in checker.vtables))

    def test_constructor_table_address_must_agree_with_rtti(self):
        results, checker = self.run_case([{"target": 0x401100}], caller_target=0x600004, caller_table=True)
        self.assertEqual(results[0].status, "relocations")
        self.assertIn("??_7First", results[0].notes[0])
        self.assertNotEqual(checker.vtables[0][1], "match")

    def test_consistent_repeated_placements_match(self):
        results, checker = self.run_case([{"target": 0x401100}, {"target": 0x401100}],
                                         caller_target=0x401100)
        self.assertEqual(results[0].status, "match")
        self.assertEqual([verdict for _, verdict in checker.vtables], ["match", "match"])

    def test_malformed_tables_cannot_place_symbols(self):
        bad_entries = [
            {"data": b"\0" * 4, "relocs": []},
            {"data": b"\x11\x11\x11\x11", "relocs": []},
            {"relocs": [(0, 1, decomp.REL_DIR32)] * 2},
            {"relocs": [(1, 1, decomp.REL_DIR32)]},
            {"relocs": [(0, 1, decomp.REL_REL32)]},
            {"data": b"\0" * 5},
            {"symbol_offset": 4},
            {"count": 2},
        ]
        for entry in bad_entries:
            with self.subTest(entry=entry):
                _, checker = self.run_case([dict(target=0x401100, **entry)])
                self.assertNotEqual(checker.vtables[0][1], "match")
                self.assertEqual(checker.discovered, {})

    def test_addend_is_removed_before_consistency_check(self):
        results, checker = self.run_case([{"target": 0x401104, "data": (4).to_bytes(4, "little")}],
                                         caller_target=0x401100)
        self.assertEqual(results[0].status, "match")
        self.assertEqual(checker.discovered["?Step@Base@@UAEXXZ"], {0x401100})
        self.assertEqual(checker.vtables[0][1], "match")

    def test_table_after_complete_object_locator_matches(self):
        # /GR: the section is COL pointer, then the slots; the table symbol sits at offset 4
        _, checker = self.run_case([{"target": 0x401100, "col": 0x610000}])
        self.assertEqual(checker.vtables[0][1], "match")
        self.assertEqual(checker.discovered["??_R4First@@6B@"], {0x610000})
        self.assertEqual(checker.discovered["?Step@Base@@UAEXXZ"], {0x401100})

    def test_complete_object_locator_conflict_rejects_the_table(self):
        # two tables whose sections point at one COL symbol that retail places at two addresses
        _, checker = self.run_case([{"target": 0x401100, "col": 0x610000, "col_name": "??_R4Shared@@6B@"},
                                    {"target": 0x401100, "col": 0x610010, "col_name": "??_R4Shared@@6B@"}])
        self.assertTrue(all(verdict != "match" for _, verdict in checker.vtables))

    def test_offset_four_needs_a_locator_relocation(self):
        for entry in ({"col": 0x610000, "col_name": "?NotALocator@@3HA"},
                      {"col": 0x610000, "relocs": [(4, 1, decomp.REL_DIR32)]}):
            with self.subTest(entry=entry):
                _, checker = self.run_case([dict(target=0x401100, **entry)])
                self.assertNotEqual(checker.vtables[0][1], "match")

    def test_missing_secondary_base_cannot_fall_back_to_primary_table(self):
        _, checker = self.run_case([{"target": 0x401100, "base": "MissingBase"}])
        self.assertEqual(checker.vtables[0][1], "no proven secondary-base offset")
        self.assertEqual(checker.discovered, {})

    def test_explicit_secondary_base_offset_is_admitted(self):
        _, checker = self.run_case([{"target": 0x401100, "base": "KnownBase", "offset": 8,
                                     "bases": "KnownBase@0x8"}])
        self.assertEqual(checker.vtables[0][1], "match")
        self.assertEqual(checker.discovered["??_7First@@6B@"], {0x600000})


class CompilerDiagnostics(unittest.TestCase):
    def compile_with(self, replacement):
        with tempfile.TemporaryDirectory(prefix="onslaught-decomp-test-") as temp:
            src = Path(temp) / "probe.cpp"
            obj = Path(temp) / "probe.obj"
            obj.write_bytes(b"stale object")
            with patch.object(decomp, "prefix_lock", contextlib.nullcontext), \
                    patch.object(decomp, "original_path", return_value="probe.cpp"), \
                    patch.object(decomp.subprocess, "run", side_effect=replacement):
                result = decomp.compile_source(src, obj, ["/O2"])
            self.assertFalse(obj.exists(), "a failed compile must not retain the old object")
            return result

    def test_failed_compiler_retains_both_diagnostic_streams(self):
        real_run = subprocess.run

        def compiler(args, **kwargs):
            self.assertTrue(stat.S_ISREG(os.fstat(kwargs["stdout"].fileno()).st_mode))
            self.assertTrue(stat.S_ISREG(os.fstat(kwargs["stderr"].fileno()).st_mode))
            self.assertNotIn("capture_output", kwargs)
            self.assertNotIn("DISPLAY", kwargs["env"])
            self.assertNotIn("WAYLAND_DISPLAY", kwargs["env"])
            return real_run([sys.executable, "-c", "import os; os.write(1,b'warning\\r\\n'); "
                             "os.write(2,b'error\\r\\n'); raise SystemExit(2)"], **kwargs)

        result = self.compile_with(compiler)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "warning\n")
        self.assertEqual(result.stderr, "error\n")

    def test_open_descendant_writer_does_not_hold_up_diagnostics(self):
        children = []

        def compiler(args, **kwargs):
            os.write(kwargs["stdout"].fileno(), b"compiler finished\n")
            # This helper models a Wine service that retains the handles after the compiler exits.
            children.append(subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                             stdout=kwargs["stdout"], stderr=kwargs["stderr"]))
            return subprocess.CompletedProcess(args, 0)

        try:
            result = self.compile_with(compiler)
            self.assertEqual(result.stdout, "compiler finished\n")
            self.assertIsNone(children[0].poll(), "the retained writer is still open when capture returns")
        finally:
            for child in children:
                child.terminate()
                child.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()


class CaseTwins(unittest.TestCase):
    """An object left by a source whose name differed only in case is removed before the new compile (Wine opens
    files case-insensitively and would write the new output under the old name)."""

    def test_removes_only_the_differently_cased_twin(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name in ("unit.obj", "Unit2.obj", "other.obj"):
                (d / name).write_bytes(b"x")
            decomp.remove_case_twins(d / "Unit.obj")
            self.assertEqual(sorted(p.name for p in d.iterdir()), ["Unit2.obj", "other.obj"])

    def test_keeps_the_same_name_and_a_missing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "Unit.obj").write_bytes(b"x")
            decomp.remove_case_twins(d / "Unit.obj")
            self.assertTrue((d / "Unit.obj").exists())
            decomp.remove_case_twins(d / "missing" / "Unit.obj")


class ImportThunks(unittest.TestCase):
    """The linker's `jmp [IAT]` stubs are library code: verified against the import table, counted apart."""

    def image(self):
        # authored fixture: thunk code by address, IAT slots by address
        code = {0x0055D5E0: b"\xff\x25\x00\x80\x5d\x00", 0x0055D5E6: b"\xff\x25\x04\x80\x5d\x00",
                0x0055D5EC: b"\xff\x25\x08\x80\x5d\x00", 0x0055D5F2: b"\xe9\x00\x00\x00\x00\x90"}
        imports = {0x005D8000: "zlib.dll!compress", 0x005D8004: "DSOUND.dll!#11", 0x005D8008: "zlib.dll!compress"}
        return SimpleNamespace(read=lambda va, n: code.get(va, b"\0" * n)[:n], imports=imports)

    def table(self):
        f = decomp.RetailFunction
        return {0x0055D5E0: f(0x0055D5E0, 6, "compress"), 0x0055D5E6: f(0x0055D5E6, 6, "DirectSoundCreate8"),
                0x0055D5EC: f(0x0055D5EC, 6, "uncompress"), 0x0055D5F2: f(0x0055D5F2, 6, "AVIStreamWrite"),
                0x00401000: f(0x00401000, 52, "GameFunction")}

    def test_named_ordinal_and_refused_thunks(self):
        got = {a: ok for a, _n, ok in decomp.import_thunks(self.image(), self.table())}
        self.assertEqual(got, {0x0055D5E0: True,     # named slot, same name
                               0x0055D5E6: True,     # ordinal import: nothing to compare, still a linker stub
                               0x0055D5EC: False,    # named slot, different name: the table is wrong
                               0x0055D5F2: False})   # not a jmp [IAT]

    def test_wrong_size_is_refused(self):
        table = self.table()
        table[0x0055D5E0] = decomp.RetailFunction(0x0055D5E0, 12, "compress")
        got = {a: ok for a, _n, ok in decomp.import_thunks(self.image(), table)}
        self.assertFalse(got[0x0055D5E0])

    def test_only_verified_thunks_leave_the_game_count(self):
        table = self.table()
        s = decomp.score([], table, decomp.import_thunks(self.image(), table))
        self.assertEqual(s["importThunks"], 2)
        self.assertEqual(s["gameFunctions"], 3)          # the game function and the two refused thunks
        self.assertEqual(decomp.score([], table)["gameFunctions"], 5)


@unittest.skipUnless((Path(__file__).resolve().parent / "scans/triage.py").exists(),
                     "tools/scans/ (the research scanners) is not in this tree")
class TriageCallDiagnostics(unittest.TestCase):
    def test_decoding_excludes_embedded_e8_but_keeps_unnamed_call(self):
        from tools.scans import triage
        # MOV immediate contains an E8 byte; actual CALL goes to an unknown target.
        data = bytes.fromhex('b8 e8 00 00 00 e8 00 00 00 00 ff d0 c3')
        direct, indirect, targets, unresolved = triage.call_inventory(data, 0x401000)
        self.assertEqual((direct, indirect), (1, 1))
        self.assertEqual(dict(targets), {0x40100a: 1})
        self.assertFalse(unresolved)

    def test_unresolved_library_keeps_count_without_false_missing_call(self):
        from tools.scans import triage
        coff = SimpleNamespace(symbols={0: SimpleNamespace(name='_authored_lib')})
        data = bytes.fromhex('e8 00 00 00 00 c3')
        direct, indirect, targets, unresolved = triage.call_inventory(
            data, 0x401000, {}, coff, [(1, 0, decomp.REL_REL32)],
            ['401000: call 0x401005', '401005: ret'])
        self.assertEqual((direct, indirect), (1, 0))
        self.assertEqual(dict(unresolved), {'_authored_lib': 1})
        self.assertEqual(triage.call_differences(targets, {0x550000: 1}, unresolved), {})

    def test_relocation_addend_and_ambiguous_bindings(self):
        from tools.scans import triage
        coff = SimpleNamespace(symbols={0: SimpleNamespace(name='_authored_lib')})
        data = bytes.fromhex('e8 04 00 00 00 c3')
        args = (data, 0x401000, {'_authored_lib': {0x550000}}, coff,
                [(1, 0, decomp.REL_REL32)], ['401000: call 0x401009'])
        direct, _, targets, unresolved = triage.call_inventory(*args)
        self.assertEqual((direct, dict(targets), dict(unresolved)), (1, {0x550004: 1}, {}))
        args = list(args); args[2] = {'_authored_lib': {0x550000, 0x560000}}
        _, _, targets, unresolved = triage.call_inventory(*args)
        self.assertFalse(targets)
        self.assertEqual(dict(unresolved), {'_authored_lib': 1})

    def test_resolved_target_differences_retain_sign_and_counts(self):
        from tools.scans import triage
        mine = collections.Counter({0x401010: 2})
        theirs = collections.Counter({0x401010: 1, 0x401020: 1})
        self.assertEqual(triage.call_differences(mine, theirs, {}),
                         {0x401010: -1, 0x401020: 1})
