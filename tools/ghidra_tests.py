#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Tests of tools/ghidra/ApplyOnslaughtNames.py without Ghidra: the table parsing, the corrections, the source scan, the
plate comments, the refusal of a different executable, idempotence, and the mapping from a row to a name and an extent,
which a mutation of either must break. Every row here is synthetic. A stub of the few Ghidra classes the script uses
drives its adapter class as well.

    python3 tools/ghidra_tests.py
"""
import ast
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "ghidra" / "ApplyOnslaughtNames.py"


def load():
    spec = importlib.util.spec_from_file_location("apply_onslaught_names_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load()

GOOD = M.EXPECTED_SHA256
OTHER = "0" * 64

# Synthetic function table: one row per kind of case (plain, template-like name, a name another row repeats, a row the
# correction moves, a row the correction removes, a function the table lacked).
TABLE = (
    "address\tbytes\tname\n"
    "0x00401000\t16\tAlpha__Run\n"
    "0x00401010\t32\tBeta<Unit>__ctor\n"
    "0x00401040\t8\tSame__name\n"
    "0x00401050\t8\tSame__name\n"
    "0x00401060\t24\tOld__extent\n"
    "0x00401080\t4\tNot__a_function\n"
    "0x00402000\t2\tOutside__image\n"
)
CORRECTIONS = (
    "address\tbytes\tname\tevidence\n"
    "0x00401060\t40\tOld__extent\tsynthetic evidence\n"
    "0x00401080\t0\tNot__a_function\tsynthetic evidence\n"
    "0x004010b0\t12\tAdded__function\tsynthetic evidence\n"
)
NO_CORRECTIONS = "address\tbytes\tname\tevidence\n"
SOURCES = {
    "Alpha.cpp": "// FUNCTION: 0x00401000\nvoid Alpha::Run() {}\n",
    "Beta.cpp": "void Beta::Beta() // FUNCTION: 0x00401010\n",
    "Beta.h": "// FUNCTION: 0x00401010\n",
    "sub/Same.cpp": "// FUNCTION: 0x00401040 init:X\n// FUNCTION: 0x00401050\n",
    "note.txt": "// FUNCTION: 0x00401060\n",
}


class FakeProgram(object):
    """Stands in for GhidraProgram; records every write."""

    def __init__(self, sha=GOOD, image=(0x400000, 0x401fff), duplicates_refused=False, refuse_extent_at=()):
        self.sha = sha
        self.image = image
        self.functions = {}      # entry -> [name, size]
        self.plates = {}
        self.writes = 0
        self.duplicates_refused = duplicates_refused
        self.refuse_extent_at = set(refuse_extent_at)

    def sha256(self):
        return self.sha

    def check_cancelled(self):
        pass

    def in_image(self, address):
        return self.image[0] <= address <= self.image[1]

    def function_at(self, address):
        return self.functions.get(address)

    def name_of(self, function):
        return function[0]

    def ensure_code(self, address, size):
        return False

    def _taken(self, name):
        return self.duplicates_refused and any(f[0] == name for f in self.functions.values())

    def create_function(self, address, size, name):
        if self._taken(name):
            raise M.DuplicateName(name)
        self.writes += 1
        self.functions[address] = [name, size]
        return self.functions[address]

    def set_name(self, function, name):
        if self._taken(name):
            raise M.DuplicateName(name)
        self.writes += 1
        function[0] = name

    def extent_is(self, function, address, size):
        return function[1] == size

    def set_extent(self, function, address, size):
        if address in self.refuse_extent_at:
            raise M.AdapterError("overlap")
        self.writes += 1
        function[1] = size

    def plate_at(self, address):
        return self.plates.get(address)

    def set_plate(self, address, text):
        self.writes += 1
        self.plates[address] = text


def make_clone(root, table=TABLE, corrections=CORRECTIONS, sources=SOURCES):
    root = Path(root)
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "functions.tsv").write_text(table)
    (root / "config" / "function-corrections.tsv").write_text(corrections)
    for name, text in sources.items():
        path = root / "src" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def run_clone(program, root, write=True):
    return M.run(program, str(Path(root) / "config"), str(Path(root) / "src"), write)


class TableTests(unittest.TestCase):
    def test_parse_rows_in_order(self):
        rows = M.parse_table(TABLE, "t")
        self.assertEqual(rows[0], (0x401000, 16, "Alpha__Run"))
        self.assertEqual(rows[1], (0x401010, 32, "Beta<Unit>__ctor"))
        self.assertEqual(len(rows), 7)

    def test_crlf_and_blank_lines(self):
        rows = M.parse_table("address\tbytes\tname\r\n\r\n0x00401000\t4\tA\r\n", "t")
        self.assertEqual(rows, [(0x401000, 4, "A")])

    def test_malformed_input_stops_without_echoing_the_row(self):
        for text in ("", "name\tbytes\taddress\n", "address\tbytes\tname\n0x00401000\tfour\tSecretName\n",
                     "address\tbytes\tname\n401000\t4\tSecretName\n", "address\tbytes\tname\n0x00401000\t4\n",
                     "address\tbytes\tname\n0x00401000\t4\tA\n0x00401000\t8\tB\n"):
            with self.assertRaises(M.ToolError) as caught:
                M.parse_table(text, "t")
            self.assertNotIn("SecretName", str(caught.exception))

    def test_corrections_replace_add_and_remove(self):
        rows, count = M.apply_corrections(M.parse_table(TABLE, "t"), M.parse_table(CORRECTIONS, "c"))
        table = dict((a, (s, n)) for a, s, n in rows)
        self.assertEqual(count, 3)
        self.assertEqual(table[0x401060], (40, "Old__extent"))
        self.assertNotIn(0x401080, table)
        self.assertEqual(table[0x4010b0], (12, "Added__function"))
        self.assertEqual([r[0] for r in rows], sorted(table))

    def test_names_are_made_acceptable_to_ghidra(self):
        self.assertEqual(M.sanitize_name("A<B,C>__operator[]"), "A<B,C>__operator[]")
        self.assertEqual(M.sanitize_name("A B\tCé"), "A_B_C_")

    def test_overlap_count(self):
        self.assertEqual(M.overlap_count([(0x10, 0x10, "a"), (0x20, 4, "b")]), 0)
        self.assertEqual(M.overlap_count([(0x10, 0x11, "a"), (0x20, 4, "b")]), 1)

    def test_locate_config_takes_a_root_or_a_config_folder(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            self.assertEqual(M.locate_config([None, str(root)]), str(root / "config"))
            self.assertEqual(M.locate_config([str(root / "config")]), str(root / "config"))
            self.assertIsNone(M.locate_config(["/nonexistent-folder-for-test", None]))

    def test_clone_candidates_order(self):
        got = M.clone_candidates(["arg"], "/c/tools/ghidra", {"BEA_DECOMP_DIR": "env"})
        self.assertEqual(got, ["arg", "env", "/c"])


class SourceTests(unittest.TestCase):
    def test_scan_finds_leading_and_trailing_annotations_in_code_files_only(self):
        with tempfile.TemporaryDirectory() as d:
            make_clone(d)
            found = M.scan_sources(str(Path(d) / "src"))
        self.assertEqual(found[0x401000], ["Alpha.cpp"])
        self.assertEqual(found[0x401010], ["Beta.cpp", "Beta.h"])      # implementation files before headers
        self.assertEqual(found[0x401040], ["sub/Same.cpp"])
        self.assertNotIn(0x401060, found)                                # note.txt is not a source file

    def test_missing_src_folder_is_empty(self):
        self.assertEqual(M.scan_sources("/nonexistent-folder-for-test"), {})

    def test_label_lists_a_few_files(self):
        self.assertEqual(M.source_label(["a.cpp"]), "a.cpp")
        self.assertEqual(M.source_label(["a.cpp", "b.h"]), "a.cpp, b.h")
        self.assertEqual(M.source_label(list("abcdef")), "a, b, c, d (+2 more)")


class PlateTests(unittest.TestCase):
    P = M.COMMENT_PREFIX

    def test_added_updated_unchanged(self):
        text, how = M.merge_plate(None, "A.cpp")
        self.assertEqual((text, how), (self.P + "A.cpp", "added"))
        self.assertEqual(M.merge_plate(text, "A.cpp"), (text, "unchanged"))
        self.assertEqual(M.merge_plate(text, "B.cpp"), (self.P + "B.cpp", "updated"))

    def test_existing_comment_kept(self):
        mine = "my note\nsecond line"
        text, how = M.merge_plate(mine, "A.cpp")
        self.assertEqual(text, mine + "\n" + self.P + "A.cpp")
        self.assertEqual(how, "added")
        again, how = M.merge_plate(text, "A.cpp")
        self.assertEqual((again, how), (text, "unchanged"))
        moved, how = M.merge_plate("top\n" + self.P + "old\nbottom", "new")
        self.assertEqual((moved, how), ("top\n" + self.P + "new\nbottom", "updated"))

    def test_no_duplicate_lines_collapse(self):
        text, how = M.merge_plate(self.P + "x\n" + self.P + "x", "x")
        self.assertEqual(text, self.P + "x")
        self.assertEqual(how, "updated")


class RefusalTests(unittest.TestCase):
    def test_different_hash_refused_and_nothing_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            for sha in (OTHER, None, ""):
                program = FakeProgram(sha=sha)
                with self.assertRaises(M.ToolError) as caught:
                    run_clone(program, root)
                self.assertIn("REFUSED", str(caught.exception))
                self.assertEqual(program.writes, 0)
                self.assertEqual(program.functions, {})

    def test_hash_comparison_ignores_case_and_space(self):
        M.check_program_hash(" " + GOOD.upper() + "\n")

    def test_expected_hash_is_the_one_the_readme_states(self):
        for candidate in (HERE.parent / "public-decomp" / "README.md", HERE.parent / "README.md"):
            if candidate.is_file():
                self.assertIn(M.EXPECTED_SHA256, candidate.read_text())
                return
        self.fail("no README found")


def mapping_check(mod):
    """The assertions that tie a table row to the name, extent and comment Ghidra receives; run on `mod` (the real
    module or a mutant of it)."""
    with tempfile.TemporaryDirectory() as d:
        root = make_clone(d)
        program = FakeProgram()
        summary = mod.run(program, str(Path(d) / "config"), str(Path(d) / "src"), True)
    f = program.functions
    assert f[0x401000] == ["Alpha__Run", 16], f.get(0x401000)
    assert f[0x401010] == ["Beta<Unit>__ctor", 32], f.get(0x401010)
    assert f[0x401060] == ["Old__extent", 40], f.get(0x401060)          # the correction's extent
    assert f[0x4010b0] == ["Added__function", 12], f.get(0x4010b0)      # a function the table lacked
    assert 0x401080 not in f                                             # removed by the correction
    assert 0x402000 not in f and summary["outside_image"] == 1
    assert program.plates[0x401000] == "Onslaught decomp source: Alpha.cpp", program.plates.get(0x401000)
    assert program.plates[0x401010] == "Onslaught decomp source: Beta.cpp, Beta.h"
    assert 0x4010b0 not in program.plates and summary["no_source_file"] >= 1
    assert summary["created"] == 6 and summary["table_rows"] == 7 and summary["corrections_applied"] == 3, summary
    return program, summary


class RunTests(unittest.TestCase):
    def test_mapping(self):
        program, summary = mapping_check(M)
        self.assertEqual(summary["comments_added"], 4)

    def test_second_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = FakeProgram()
            run_clone(program, root)
            after_first = ({k: list(v) for k, v in program.functions.items()}, dict(program.plates), program.writes)
            second = run_clone(program, root)
            self.assertEqual(({k: list(v) for k, v in program.functions.items()}, dict(program.plates),
                              program.writes), after_first)
            for key in ("created", "renamed", "extents_set", "comments_added", "comments_updated",
                        "renamed_with_address_suffix", "errors"):
                self.assertEqual(second.get(key, 0), 0, key)
            self.assertEqual(second["names_unchanged"], 6)
            self.assertEqual(second["extents_unchanged"], 6)
            self.assertEqual(second["comments_unchanged"], 4)

    def test_existing_functions_are_renamed_and_resized(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = FakeProgram()
            program.functions[0x401000] = ["default_name", 3]
            program.plates[0x401000] = "keep me"
            summary = run_clone(program, root)
            self.assertEqual(program.functions[0x401000], ["Alpha__Run", 16])
            self.assertEqual(program.plates[0x401000], "keep me\n" + M.COMMENT_PREFIX + "Alpha.cpp")
            self.assertEqual((summary["renamed"], summary["extents_set"]), (1, 1))
            self.assertEqual(summary["created"], 5)

    def test_check_mode_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = FakeProgram()
            program.functions[0x401000] = ["default_name", 3]
            summary = run_clone(program, root, write=False)
            self.assertEqual(program.writes, 0)
            self.assertEqual(program.functions, {0x401000: ["default_name", 3]})
            self.assertEqual(program.plates, {})
            self.assertEqual(summary["created"], 5)
            self.assertEqual(summary["renamed"], 1)

    def test_repeated_name_gets_an_address_suffix_when_ghidra_refuses_it(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = FakeProgram(duplicates_refused=True)
            summary = run_clone(program, root)
            self.assertEqual(program.functions[0x401040][0], "Same__name")
            self.assertEqual(program.functions[0x401050][0], "Same__name__00401050")
            self.assertEqual(summary["renamed_with_address_suffix"], 1)
            second = run_clone(program, root)
            self.assertEqual(second.get("renamed_with_address_suffix", 0), 0)
            self.assertEqual(second["names_unchanged"], 6)

    def test_refused_extent_is_counted_and_the_rest_continues(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = FakeProgram(refuse_extent_at=[0x401000])
            program.functions[0x401000] = ["x", 3]
            summary = run_clone(program, root)
            self.assertEqual(summary["extents_refused"], 1)
            self.assertEqual(program.functions[0x401000], ["Alpha__Run", 3])
            self.assertEqual(program.functions[0x401010], ["Beta<Unit>__ctor", 32])

    def test_summary_lines_are_counts_only(self):
        lines = M.summary_lines({"table_rows": 3, "created": 2}, True)
        self.assertEqual(lines, ["ApplyOnslaughtNames: applied", "  table_rows: 3", "  created: 2"])
        self.assertIn("check only", M.summary_lines({}, False)[0])


class MutationTests(unittest.TestCase):
    """A change to the name or the extent mapping must fail mapping_check; the unchanged module must pass it."""

    def mutant(self, **replacements):
        mod = load()
        for name, value in replacements.items():
            setattr(mod, name, value)
        return mod

    def test_unmutated_passes(self):
        mapping_check(load())

    def test_name_and_extent_mutants_are_caught(self):
        real_parse = M.parse_table
        mutants = {
            "name column": dict(parse_table=lambda t, l: [(a, s, n.lower()) for a, s, n in real_parse(t, l)]),
            "extent off by one": dict(parse_table=lambda t, l: [(a, s + 1, n) for a, s, n in real_parse(t, l)]),
            "name and size swapped": dict(parse_table=lambda t, l: [(a, len(n), str(s)) for a, s, n in real_parse(t, l)]),
            "sanitize rewrites": dict(sanitize_name=lambda n: n.replace("<", "_")),
            "corrections ignored": dict(apply_corrections=lambda rows, c: (sorted(rows), len(c))),
            "removal ignored": dict(apply_corrections=lambda rows, c: (
                sorted(dict([(r[0], r) for r in rows] + [(a, (a, s or 1, n)) for a, s, n in c]).values()), len(c))),
            "wrong comment prefix": dict(COMMENT_PREFIX="Source: "),
            "label drops headers": dict(source_label=lambda files: files[0]),
            "no comment": dict(label_function=lambda *a: None),
            "no create": dict(create_function=lambda *a: None),
        }
        for label, replacements in mutants.items():
            with self.subTest(mutant=label):
                with self.assertRaises(Exception):
                    mapping_check(self.mutant(**replacements))


# --- a stub of the few Ghidra classes the adapter touches ------------------------------------------------------

class Addr(object):
    def __init__(self, offset):
        self.offset = offset

    def equals(self, other):
        return other.offset == self.offset

    def getOffset(self):
        return self.offset


class AddrSet(object):
    def __init__(self, start, end):
        self.start, self.end = start, end

    def getNumAddressRanges(self):
        return 1

    def getMinAddress(self):
        return self.start

    def getMaxAddress(self):
        return self.end


class Dup(Exception):
    pass


class StubFunction(object):
    def __init__(self, manager, name, body):
        self.manager, self.name, self.body = manager, name, body

    def getName(self):
        return self.name

    def setName(self, name, source):
        if any(f is not self and f.name == name for f in self.manager.by_entry.values()):
            raise self.manager.Dup("duplicate")
        self.name = name

    def getBody(self):
        return self.body

    def setBody(self, body):
        if self.manager.refuse_body:
            raise RuntimeError("overlap")
        self.body = body


class StubManager(object):
    def __init__(self, dup):
        self.by_entry = {}
        self.Dup = dup
        self.refuse_body = False

    def getFunctionAt(self, address):
        return self.by_entry.get(address.offset)

    def createFunction(self, name, entry, body, source):
        if any(f.name == name for f in self.by_entry.values()):
            raise self.Dup("duplicate")
        self.by_entry[entry.offset] = StubFunction(self, name, body)
        return self.by_entry[entry.offset]


class StubDisassemble(object):
    """Stands in for DisassembleCommand: records the entry it was asked to disassemble."""
    calls = []

    def __init__(self, start, restricted, follow):
        StubDisassemble.calls.append((start.start.offset, restricted.end.offset, follow))

    def applyTo(self, program, monitor):
        return True


def install_stub_ghidra():
    """Insert stand-ins for the ghidra.* modules the adapter imports; returns the list of names to remove again."""
    def module(name, **attributes):
        m = types.ModuleType(name)
        m.__dict__.update(attributes)
        sys.modules[name] = m
        return m
    names = ["ghidra", "ghidra.program", "ghidra.program.model", "ghidra.program.model.address",
             "ghidra.program.model.symbol", "ghidra.program.model.listing", "ghidra.util", "ghidra.util.exception",
             "ghidra.app", "ghidra.app.cmd", "ghidra.app.cmd.disassemble"]
    module("ghidra")
    module("ghidra.program")
    module("ghidra.program.model")
    module("ghidra.program.model.address", AddressSet=AddrSet)
    module("ghidra.program.model.symbol", SourceType=types.SimpleNamespace(USER_DEFINED="user"))
    module("ghidra.program.model.listing", CommentType=types.SimpleNamespace(PLATE="plate"))
    module("ghidra.util")
    module("ghidra.util.exception", DuplicateNameException=Dup)
    module("ghidra.app")
    module("ghidra.app.cmd")
    module("ghidra.app.cmd.disassemble", DisassembleCommand=StubDisassemble)
    return names


class LanguageId(object):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class StubProgram(object):
    def __init__(self, base=0x400000, low=0x401000, high=0x401fff, language="x86:LE:32:default", code=True):
        self.manager = StubManager(Dup)
        self.comments = {}
        self.base, self.low, self.high = base, low, high
        self.language = language
        self.code = code
        self.sha = GOOD
        self.disassembled = []

    def getLanguageID(self):
        return LanguageId(self.language)

    def getFunctionManager(self):
        return self.manager

    def getListing(self):
        outer = self
        return types.SimpleNamespace(
            getComment=lambda kind, a: outer.comments.get((kind, a.offset)),
            setComment=lambda a, kind, text: outer.comments.__setitem__((kind, a.offset), text),
            getInstructionAt=lambda a: object() if self.code else None)

    def getMemory(self):
        return types.SimpleNamespace(contains=lambda a: self.low <= a.offset <= self.high)

    def getAddressFactory(self):
        return types.SimpleNamespace(getDefaultAddressSpace=lambda: types.SimpleNamespace(getAddress=Addr))

    def getImageBase(self):
        return Addr(self.base)

    def getExecutableSHA256(self):
        return self.sha


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.names = install_stub_ghidra()

    def tearDown(self):
        for name in self.names:
            sys.modules.pop(name, None)

    def adapter(self, program=None):
        mod = load()
        program = program or StubProgram()
        monitor = types.SimpleNamespace(checkCancelled=lambda: None)
        return mod, program, mod.GhidraProgram(program, monitor)

    def test_extent_covers_exactly_the_row_and_idempotence_through_the_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            mod, program, adapter = self.adapter()
            first = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            f = program.manager.by_entry[0x401000]
            self.assertEqual((f.getName(), f.body.start.offset, f.body.end.offset), ("Alpha__Run", 0x401000, 0x40100f))
            self.assertEqual(program.manager.by_entry[0x4010b0].body.end.offset, 0x4010bb)
            self.assertEqual(program.comments[("plate", 0x401000)], mod.COMMENT_PREFIX + "Alpha.cpp")
            self.assertEqual(first["created"], 6)
            self.assertEqual(first["renamed_with_address_suffix"], 1)       # the stub refuses a repeated name
            second = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            for key in ("created", "renamed", "extents_set", "comments_added", "comments_updated", "errors",
                        "renamed_with_address_suffix"):
                self.assertEqual(second.get(key, 0), 0, key)
            self.assertEqual(second["extents_unchanged"], 6)

    def test_wrong_extent_is_replaced_and_a_refusal_is_counted(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            mod, program, adapter = self.adapter()
            program.manager.by_entry[0x401000] = StubFunction(program.manager, "x", AddrSet(Addr(0x401000), Addr(0x401003)))
            program.manager.refuse_body = True
            summary = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            self.assertEqual(summary["extents_refused"], 1)
            program.manager.refuse_body = False
            summary = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            self.assertEqual(summary["extents_set"], 1)
            self.assertEqual(program.manager.by_entry[0x401000].body.end.offset, 0x40100f)

    def test_an_existing_function_is_renamed_through_the_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            mod, program, adapter = self.adapter()
            program.manager.by_entry[0x401000] = StubFunction(program.manager, "old_name", AddrSet(Addr(0x401000), Addr(0x40100f)))
            summary = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            self.assertEqual(program.manager.by_entry[0x401000].getName(), "Alpha__Run")
            self.assertEqual(summary["renamed"], 1)
            self.assertEqual(summary["extents_unchanged"], 1)
            program.manager.by_entry[0x401000].name = "other_name"
            check = mod.run(adapter, str(root / "config"), str(root / "src"), False)
            self.assertEqual(program.manager.by_entry[0x401000].getName(), "other_name")      # check mode writes nothing
            self.assertEqual(check["renamed"], 1)

    def test_a_repeated_name_on_rename_gets_the_suffix_through_the_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            mod, program, adapter = self.adapter()
            program.manager.by_entry[0x401040] = StubFunction(program.manager, "Same__name", AddrSet(Addr(0x401040), Addr(0x401047)))
            program.manager.by_entry[0x401050] = StubFunction(program.manager, "placeholder_x", AddrSet(Addr(0x401050), Addr(0x401057)))
            summary = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            self.assertEqual(program.manager.by_entry[0x401050].getName(), "Same__name__00401050")
            self.assertEqual(summary["renamed_with_address_suffix"], 1)
            self.assertEqual(summary.get("rename_refused", 0), 0)

    def test_the_entry_is_disassembled_before_a_function_is_created(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            StubDisassemble.calls = []
            mod, program, adapter = self.adapter(StubProgram(code=False))
            summary = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            self.assertEqual(summary["disassembled"], 6)
            self.assertIn((0x401000, 0x40100f, True), StubDisassemble.calls)

    def test_a_32_bit_x86_language_is_required(self):
        for language in ("x86:LE:64:default", "ARM:LE:32:v8", ""):
            with self.assertRaises(Exception) as caught:
                self.adapter(StubProgram(language=language))
            self.assertEqual(type(caught.exception).__name__, "ToolError")

    def test_other_image_base_refused(self):
        with self.assertRaises(Exception) as caught:
            self.adapter(StubProgram(base=0x10000000))
        self.assertEqual(type(caught.exception).__name__, "ToolError")

    def test_outside_image_rows_are_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            mod, program, adapter = self.adapter(StubProgram(high=0x40100f))
            summary = mod.run(adapter, str(root / "config"), str(root / "src"), True)
            self.assertEqual(sorted(program.manager.by_entry), [0x401000])
            self.assertEqual(summary["outside_image"], 6)


class ArgumentTests(unittest.TestCase):
    def test_check_is_honoured_in_any_position_and_is_never_the_path(self):
        self.assertEqual(M.parse_arguments([]), (None, False))
        self.assertEqual(M.parse_arguments(["check"]), (None, True))
        self.assertEqual(M.parse_arguments(["/clone"]), ("/clone", False))
        self.assertEqual(M.parse_arguments(["/clone", "check"]), ("/clone", True))
        self.assertEqual(M.parse_arguments(["check", "/clone"]), ("/clone", True))
        with self.assertRaises(M.ToolError):
            M.parse_arguments(["/one", "/two"])
        with self.assertRaises(M.ToolError):
            M.parse_arguments(["/one", "check", "/two"])

    def test_candidates_never_include_the_word_check(self):
        self.assertEqual(M.clone_candidates(["check"], "/c/tools/ghidra", {}), [None, "/c"])
        self.assertEqual(M.clone_candidates(["check", "/p"], "/c/tools/ghidra", {"BEA_DECOMP_DIR": "e"}), ["/p", "e", "/c"])
        self.assertEqual(M.clone_candidates([], None, {}), [None])

    def test_config_folder_ignores_a_trailing_slash_and_needs_both_tables(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            for given in (str(root) + "/", str(root) + "//", str(root / "config") + "/", str(root / "config" / ".." / "config")):
                self.assertEqual(M.config_folder_of(given), str(root / "config"))
            self.assertIsNone(M.config_folder_of(str(root / "src")))
            self.assertIsNone(M.config_folder_of(""))
            (root / "config" / "function-corrections.tsv").unlink()
            self.assertIsNone(M.config_folder_of(str(root)))


class DamagedTableTests(unittest.TestCase):
    def test_a_digit_that_is_not_ascii_is_a_clean_error(self):
        with self.assertRaises(M.ToolError):
            M.parse_table("address\tbytes\tname\n0x00401000\t\u00b2\tA\n", "t")

    def test_header_only_function_table_stops_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d, table="address\tbytes\tname\n")
            program = FakeProgram()
            with self.assertRaises(M.ToolError):
                run_clone(program, root)
            self.assertEqual(program.writes, 0)

    def test_rows_without_a_size_are_counted_and_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d, table="address\tbytes\tname\n0x00401000\t0\tNoSize\n0x00401010\t4\tA\n", corrections=NO_CORRECTIONS)
            program = FakeProgram()
            summary = run_clone(program, root)
            self.assertEqual(summary["bad_rows"], 1)
            self.assertEqual(sorted(program.functions), [0x401010])

    def test_a_row_that_starts_inside_the_image_and_ends_outside_is_skipped(self):
        table = ("address\tbytes\tname\n0x00401ff0\t32\tCrosses\n0x00401000\t%d\tHuge\n"
                 "0x00401800\t%d\tHuger\n0x00401900\t4\tFine\n" % (0xFFFFFFFF, 1 << 70))
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d, table=table, corrections=NO_CORRECTIONS)
            program = FakeProgram()
            summary = run_clone(program, root)
            self.assertEqual(summary["outside_image"], 3)
            self.assertEqual(sorted(program.functions), [0x401900])

    def test_a_row_past_the_32_bit_space_is_skipped_even_if_the_program_claims_it(self):
        table = "address\tbytes\tname\n0x00401800\t%d\tHuge\n0x00401900\t4\tFine\n" % (1 << 70)
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d, table=table, corrections=NO_CORRECTIONS)
            program = FakeProgram(image=(0, 1 << 80))
            summary = run_clone(program, root)
            self.assertEqual(summary["outside_image"], 1)
            self.assertEqual(sorted(program.functions), [0x401900])


class ErrorHandlingTests(unittest.TestCase):
    def test_an_unexpected_error_is_counted_and_the_run_goes_on(self):
        class Breaks(FakeProgram):
            def create_function(self, address, size, name):
                if address == 0x401010:
                    raise ValueError("unforeseen")
                return FakeProgram.create_function(self, address, size, name)
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = Breaks()
            summary = run_clone(program, root)
            self.assertEqual(summary["errors"], 1)
            self.assertNotIn(0x401010, program.functions)
            self.assertIn(0x4010b0, program.functions)

    def test_a_cancel_after_an_error_still_stops_the_run(self):
        class Cancelled(Exception):
            pass

        class Breaks(FakeProgram):
            def create_function(self, address, size, name):
                raise ValueError("unforeseen")

            def check_cancelled(self):
                if self.writes == 0 and self.functions == {} and getattr(self, "armed", False):
                    raise Cancelled()
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = Breaks()
            program.armed = True
            with self.assertRaises(Cancelled):
                run_clone(program, root)

    def test_a_tool_error_inside_a_row_is_not_swallowed(self):
        class Refuses(FakeProgram):
            def create_function(self, address, size, name):
                raise M.ToolError("stop")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(M.ToolError):
                run_clone(Refuses(), make_clone(d))

    def test_refusal_counters(self):
        class Refuses(FakeProgram):
            def create_function(self, address, size, name):
                if address == 0x401010:
                    raise M.AdapterError("no")
                return FakeProgram.create_function(self, address, size, name)

            def set_name(self, function, name):
                raise M.AdapterError("no")
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = Refuses()
            program.functions[0x401000] = ["old", 16]
            summary = run_clone(program, root)
            self.assertEqual(summary["create_refused"], 1)
            self.assertEqual(summary["rename_refused"], 1)
            self.assertEqual(summary["created"], 4)
            self.assertEqual(program.functions[0x401000][0], "old")

    def test_a_rename_that_hits_a_repeated_name_gets_the_address_suffix(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_clone(d)
            program = FakeProgram(duplicates_refused=True)
            program.functions[0x401040] = ["Same__name", 8]
            program.functions[0x401050] = ["placeholder", 8]
            summary = run_clone(program, root)
            self.assertEqual(program.functions[0x401050][0], "Same__name__00401050")
            self.assertEqual(summary["renamed_with_address_suffix"], 1)

    def test_disassembly_is_counted(self):
        class Needs(FakeProgram):
            def ensure_code(self, address, size):
                return address == 0x401000
        with tempfile.TemporaryDirectory() as d:
            summary = run_clone(Needs(), make_clone(d))
            self.assertEqual(summary["disassembled"], 1)

    def test_headers_come_after_implementation_files(self):
        with tempfile.TemporaryDirectory() as d:
            make_clone(d, sources={"A.h": "// FUNCTION: 0x00401000\n", "B.cpp": "// FUNCTION: 0x00401000\n",
                                   "a.c": "// FUNCTION: 0x00401000\n"})
            found = M.scan_sources(str(Path(d) / "src"))
        self.assertEqual(found[0x401000], ["a.c", "B.cpp", "A.h"])

    def test_the_summary_says_when_changes_were_refused(self):
        text = "\n".join(M.summary_lines({"create_refused": 2}, True))
        self.assertIn("refused", text.split("create_refused")[1])
        self.assertNotIn("Some changes were refused", "\n".join(M.summary_lines({"created": 2}, True)))


class RunInGhidraTests(unittest.TestCase):
    """The entry the script runs inside Ghidra, over the stand-in Ghidra classes: argument handling, which tables are
    used, and the folder picker."""

    def setUp(self):
        self.names = install_stub_ghidra()
        self.mod = load()
        self.dir = tempfile.TemporaryDirectory()
        self.root = make_clone(self.dir.name)
        # a second clone the script "sits in", which a failed explicit path must never fall back to
        self.home = make_clone(os.path.join(self.dir.name, "home"))

    def tearDown(self):
        for name in self.names:
            sys.modules.pop(name, None)
        self.dir.cleanup()

    def go(self, arguments, environ=None, headless=True, picker=None, program=None):
        mod = self.mod
        program = program or StubProgram()
        monitor = types.SimpleNamespace(checkCancelled=lambda: None)
        out = io.StringIO()
        asked = []

        def ask(title, button):
            asked.append(title)
            return picker
        try:
            with contextlib.redirect_stdout(out):
                mod.run_in_ghidra(program, monitor, arguments, str(self.home / "tools" / "ghidra"), headless, ask,
                                  environ or {})
        finally:
            self.out = out.getvalue()
            self.asked = asked
            self.program = program
        return program

    def test_check_alone_writes_nothing(self):
        program = self.go(["check"])
        self.assertEqual(program.manager.by_entry, {})
        self.assertEqual(program.comments, {})
        self.assertIn("check only", self.out)
        self.assertIn(str(self.home / "config"), self.out)          # the folder used is printed

    def test_check_after_the_path_and_before_it(self):
        for arguments in ([str(self.root), "check"], ["check", str(self.root)]):
            program = self.go(arguments)
            self.assertEqual(program.manager.by_entry, {})
            self.assertIn(str(self.root / "config"), self.out)

    def test_a_path_that_does_not_resolve_stops_the_run_instead_of_using_another_clone(self):
        for arguments, environ in ((["/nonexistent-for-test"], {}), ([str(self.root / "src")], {}),
                                   ([], {"BEA_DECOMP_DIR": "/nonexistent-for-test"})):
            program = StubProgram()
            with self.assertRaises(self.mod.ToolError) as caught:
                self.go(arguments, environ, program=program)
            self.assertIn("does not hold", str(caught.exception))
            self.assertEqual(program.manager.by_entry, {})

    def test_a_trailing_slash_still_finds_src_and_adds_comments(self):
        program = self.go([str(self.root) + "/"])
        self.assertEqual(program.comments[("plate", 0x401000)], self.mod.COMMENT_PREFIX + "Alpha.cpp")
        self.assertNotIn("no src/", self.out)
        program = self.go([str(self.root / "config") + "/"])
        self.assertEqual(program.comments[("plate", 0x401000)], self.mod.COMMENT_PREFIX + "Alpha.cpp")

    def test_the_clone_the_script_sits_in_is_the_default(self):
        program = self.go([])
        self.assertIn(("plate", 0x401000), program.comments)
        self.assertIn(str(self.home / "config"), self.out)

    def test_the_folder_picker_result_is_a_file_object_not_a_string(self):
        class JavaFile(object):
            def __init__(self, path):
                self.path = path

            def __str__(self):
                return self.path
        lonely = os.path.join(self.dir.name, "elsewhere")
        os.makedirs(lonely)
        mod = self.mod
        out = io.StringIO()
        program = StubProgram()
        monitor = types.SimpleNamespace(checkCancelled=lambda: None)
        with contextlib.redirect_stdout(out):
            mod.run_in_ghidra(program, monitor, [], os.path.join(lonely, "tools", "ghidra"), False,
                              lambda title, button: JavaFile(str(self.root)), {})
        self.assertIn(0x401000, program.manager.by_entry)

    def test_headless_never_asks_for_a_folder(self):
        lonely = os.path.join(self.dir.name, "elsewhere")
        os.makedirs(lonely)
        mod = self.mod
        asked = []
        with self.assertRaises(self.mod.ToolError):
            mod.run_in_ghidra(StubProgram(), types.SimpleNamespace(checkCancelled=lambda: None), [],
                              os.path.join(lonely, "tools", "ghidra"), True, lambda t, b: asked.append(t), {})
        self.assertEqual(asked, [])

    def test_a_wrong_executable_is_refused_before_anything_is_read_or_written(self):
        program = StubProgram()
        program.sha = OTHER
        with self.assertRaises(self.mod.ToolError):
            self.go([str(self.root)], program=program)
        self.assertEqual(program.manager.by_entry, {})

    def test_a_64_bit_import_is_refused(self):
        with self.assertRaises(self.mod.ToolError) as caught:
            self.go([str(self.root)], program=StubProgram(language="x86:LE:64:default"))
        self.assertIn("32-bit", str(caught.exception))
        self.assertEqual(len(self.program.manager.by_entry), 0)

    def test_an_address_outside_the_address_space_counts_as_outside(self):
        program = StubProgram()
        space = types.SimpleNamespace(getAddress=lambda a: (_ for _ in ()).throw(OverflowError("too big"))
                                      if a > 0xFFFFFFFF else Addr(a))
        program.getAddressFactory = lambda: types.SimpleNamespace(getDefaultAddressSpace=lambda: space)
        adapter = load().GhidraProgram(program, types.SimpleNamespace(checkCancelled=lambda: None))
        self.assertFalse(adapter.in_image(0x100000000))
        self.assertTrue(adapter.in_image(0x401000))


class SyntaxTests(unittest.TestCase):
    def test_script_stays_within_python_2_7_syntax(self):
        """Ghidra's optional Jython provider reads Python 2.7: no f-strings, annotations, nonlocal, keyword-only
        arguments, `raise ... from`, `yield from`, async, unpacking extensions or the walrus."""
        tree = ast.parse(SCRIPT.read_text())
        bad = []
        for node in ast.walk(tree):
            kind = type(node).__name__
            if kind in ("JoinedStr", "AnnAssign", "Nonlocal", "YieldFrom", "AsyncFunctionDef", "Await", "NamedExpr",
                        "MatMult", "TypeAlias", "Match"):
                bad.append((kind, getattr(node, "lineno", 0)))
            if isinstance(node, (ast.FunctionDef, ast.Lambda)):
                a = node.args
                if a.kwonlyargs or getattr(a, "posonlyargs", None):
                    bad.append(("keyword-only or positional-only arguments", node.lineno))
                for arg in a.args + a.kwonlyargs:
                    if getattr(arg, "annotation", None) is not None:
                        bad.append(("annotation", node.lineno))
                if isinstance(node, ast.FunctionDef) and node.returns is not None:
                    bad.append(("return annotation", node.lineno))
            if isinstance(node, ast.Raise) and node.cause is not None:
                bad.append(("raise from", node.lineno))
            if isinstance(node, ast.Starred):
                bad.append(("starred expression", node.lineno))
            if isinstance(node, ast.ExceptHandler) and node.name is None and node.type is None:
                pass
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
