"""Focused tests for tools/link.py (input pins, object order, response file, unresolved parsing) and tools/linkcmp.py's
import comparison. No linker, specimen or library needed."""
import struct
import tempfile
import unittest
from pathlib import Path

from tools import link, linkcmp


class Inputs(unittest.TestCase):
    def test_pins_keep_their_order_and_roots(self):
        text = "# comment\n\naa vc6 VC98/Lib/KERNEL32.LIB\nbb lab retail-importlibs/ogg.lib\n"
        got = link.read_inputs(text, {"vc6": Path("/v"), "lab": Path("/l")})
        self.assertEqual(got, [(Path("/v/VC98/Lib/KERNEL32.LIB"), "aa"), (Path("/l/retail-importlibs/ogg.lib"), "bb")])

    def test_source_lines_carry_compiler_options(self):
        got = link.read_sources("aa lab x/a.cpp /FIlinklib/h.h /DX\nbb lab x/a.h\n", {"lab": Path("/l")})
        self.assertEqual(got, [(Path("/l/x/a.cpp"), "aa", ["/FIlinklib/h.h", "/DX"]), (Path("/l/x/a.h"), "bb", [])])

    def test_unknown_root_is_refused(self):
        with self.assertRaises(SystemExit):
            link.read_inputs("aa elsewhere x.lib\n", {"vc6": Path("/v")})

    def test_a_changed_or_missing_input_refuses_the_link(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.lib"
            f.write_bytes(b"one")
            link.verify([(f, link.sha256(f))])
            with self.assertRaises(SystemExit):
                link.verify([(f, "0" * 64)])
            with self.assertRaises(SystemExit):
                link.verify([(Path(d) / "b.lib", "0" * 64)])



class NativeCrt(unittest.TestCase):
    def test_link_prefix_copies_the_base_and_holds_the_pinned_crt_and_repairs_it(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "wine"
            (base / "drive_c/windows/syswow64").mkdir(parents=True)
            (base / "drive_c/windows/syswow64/msvcrt.dll").write_bytes(b"builtin")
            (base / "drive_c/ONSLAUGHT2").mkdir()
            crt = Path(d) / "MSVCRT.DLL"
            crt.write_bytes(b"native")
            saved = link.NATIVE_CRT
            link.NATIVE_CRT = crt
            try:
                prefix = link.link_prefix(base)
                self.assertEqual(prefix.name, "wine-link-msvcrt-" + link.sha256(crt)[:12])
                dll = prefix / "drive_c/windows/syswow64/msvcrt.dll"
                self.assertEqual(dll.read_bytes(), b"native")
                self.assertFalse((prefix / "drive_c/ONSLAUGHT2").exists())
                self.assertEqual((base / "drive_c/windows/syswow64/msvcrt.dll").read_bytes(), b"builtin")
                dll.write_bytes(b"changed")
                link.link_prefix(base)
                self.assertEqual(dll.read_bytes(), b"native")
            finally:
                link.NATIVE_CRT = saved

    def test_only_a_native_32_bit_msvcrt_load_counts(self):
        native = '0104:trace:loaddll:build_module Loaded L"C:\\\\windows\\\\system32\\\\MSVCRT.dll" at 78000000: native\n'
        builtin = '0104:trace:loaddll:build_module Loaded L"C:\\\\windows\\\\system32\\\\MSVCRT.dll" at 7B220000: builtin\n'
        wow64 = '0024:trace:loaddll:build_module Loaded L"C:\\\\windows\\\\system32\\\\msvcrt.dll" at 00006FFFFEE20000: builtin\n'
        self.assertTrue(link.native_crt_loaded(wow64 + native))
        self.assertFalse(link.native_crt_loaded(wow64 + builtin))
        self.assertFalse(link.native_crt_loaded(wow64))


class Order(unittest.TestCase):
    def test_objects_sort_by_file_name_ignoring_case_and_folders(self):
        with tempfile.TemporaryDirectory() as d:
            for rel in ("game.obj", "MissionScript/AsmInstruction.obj", "Career.obj", "activereader.obj"):
                (Path(d) / rel).parent.mkdir(parents=True, exist_ok=True)
                (Path(d) / rel).write_bytes(b"")
            names = [p.name for p in link.objects(Path(d))]
        self.assertEqual(names, ["activereader.obj", "AsmInstruction.obj", "Career.obj", "game.obj"])

    def test_response_lists_options_then_objects_then_libraries(self):
        lines = link.response([Path("/b/a.obj")], [Path("/l/x.lib")], Path("/o")).splitlines()
        self.assertEqual(lines[0], "/nologo")
        self.assertTrue(lines[-3].startswith("/OUT:") and lines[-3].endswith("BEA.exe"))
        self.assertEqual(lines[-2:], ["Z:\\b\\a.obj", "Z:\\l\\x.lib"])


class Unresolved(unittest.TestCase):
    def test_decorated_names_are_preferred_and_counted_once(self):
        log = ('a.obj : error LNK2001: unresolved external symbol "int gX" (?gX@@3HA)\n'
               'b.obj : error LNK2001: unresolved external symbol "int gX" (?gX@@3HA)\n'
               'c.obj : error LNK2001: unresolved external symbol _compress\n')
        self.assertEqual(link.unresolved(log), ["?gX@@3HA", "_compress"])


class Imports(unittest.TestCase):
    def test_order_names_hints_and_slots(self):
        retail = [("KERNEL32.dll", [("Sleep", 5, 0x5d8000)]), ("ogg.dll", [("ogg_sync_init", 24, 0x5d8010)])]
        same = [("KERNEL32.dll", [("Sleep", 5, 0x5d8000)]), ("ogg.dll", [("ogg_sync_init", 24, 0x5d8010)])]
        out = linkcmp.compare_imports(retail, same)
        self.assertTrue(out["descriptor_order_equal"])
        self.assertTrue(all(r["names_in_order"] and r["hints"] and r["iat_slots"] for r in out["dlls"]))
        moved = [("ogg.dll", [("ogg_sync_init", 23, 0x5d8020)]), ("KERNEL32.dll", [])]
        out = linkcmp.compare_imports(retail, moved)
        self.assertFalse(out["descriptor_order_equal"])
        k, o = out["dlls"]
        self.assertEqual((k["names_in_order"], k["missing"]), (False, ["Sleep"]))
        self.assertEqual((o["names_in_order"], o["hints"], o["iat_slots"]), (True, False, False))

    def test_a_missing_dll_is_reported(self):
        out = linkcmp.compare_imports([("AVIFIL32.dll", [("AVIStreamWrite", 1, 0x5d8018)])], [])
        self.assertEqual(out["dlls"], [{"dll": "AVIFIL32.dll", "present": False}])


class Aliases(unittest.TestCase):
    def test_aliases_file_skips_comments(self):
        self.assertEqual(link.read_aliases("# x\n?a@@3HA\t?b@@3HA\twhy\n"), [("?a@@3HA", "?b@@3HA")])

    def test_alias_object_makes_each_alias_a_weak_external_of_its_target(self):
        from tools import binfmt
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.obj"
            p.write_bytes(link.alias_object([("?GAME_RENDER_MODE@@3HA", "?mRenderMode@CMeshRenderer@@2W4ERenderMode@@A"),
                                             ("_x", "_y")]))
            c = binfmt.parse_coff(p)
        syms = {s.name: s for s in c.symbols.values()}
        self.assertEqual(syms["?GAME_RENDER_MODE@@3HA"].storage, 105)
        self.assertEqual(syms["_x"].storage, 105)
        self.assertEqual((syms["_y"].storage, syms["_y"].section), (2, 0))
        tag = int.from_bytes(syms["_x"].aux[:4], "little")
        self.assertEqual(c.symbols[tag].name, "_y")


class Resources(unittest.TestCase):
    def test_equal_trees_and_rebased_images(self):
        leaves = [((3, 1, 1033), 1252, b"icon")]
        out = linkcmp.compare_resources((leaves, b"img"), (leaves, b"img"))
        self.assertEqual((out["leaves"], out["leaves_equal_in_order"], out["image_equal_rebased"]), ([1, 1], True, True))
        out = linkcmp.compare_resources((leaves, b"img"), ([], None))
        self.assertEqual((out["leaves_equal_in_order"], out["image_equal_rebased"]), (False, False))


class ObjectOrder(unittest.TestCase):
    def test_listed_objects_follow_the_list_and_the_rest_follow_alphabetically(self):
        with tempfile.TemporaryDirectory() as d:
            for rel in ("game.obj", "ltshell.obj", "MissionScript/vm.obj", "zeta.obj", "Alpha.obj"):
                (Path(d) / rel).parent.mkdir(parents=True, exist_ok=True)
                (Path(d) / rel).write_bytes(b"")
            names = [p.name for p in link.objects(Path(d), "# A\ngame.cpp\n# B\nltshell.cpp\nMissionScript/vm.cpp\n")]
        self.assertEqual(names, ["game.obj", "ltshell.obj", "vm.obj", "Alpha.obj", "zeta.obj"])

    def test_a_listed_c_source_places_its_object(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("game.obj", "adpcm.obj", "credits.obj"):
                (Path(d) / n).write_bytes(b"")
            names = [p.name for p in link.objects(Path(d), "game.cpp\nadpcm.c\ncredits.cpp\n")]
            self.assertEqual(names, ["game.obj", "adpcm.obj", "credits.obj"])
            with self.assertRaises(SystemExit):
                link.objects(Path(d), "adpcm.cpp\nadpcm.c\n")
            (Path(d) / "src").mkdir()
            (Path(d) / "src/adpcm.c").write_text("")
            link.objects(Path(d), "adpcm.c\n", Path(d) / "src")
            (Path(d) / "src/adpcm.cpp").write_text("")
            with self.assertRaises(SystemExit):
                link.objects(Path(d), "adpcm.c\n", Path(d) / "src")
    def test_objects_after_the_libraries_line_link_late(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("game.obj", "pausecommons.obj", "credits.obj"):
                (Path(d) / n).write_bytes(b"")
            order = "game.cpp\ncredits.cpp\n[after libraries]\npausecommons.c\n"
            objs = link.objects(Path(d), order)
            self.assertEqual([p.name for p in objs], ["game.obj", "credits.obj", "pausecommons.obj"])
            self.assertEqual([p.name for p in link.late_objects(objs, Path(d), order)], ["pausecommons.obj"])
            self.assertEqual(link.late_objects(objs, Path(d), "game.cpp\n"), [])

    def test_order_metric_is_the_longest_run_in_retail_order(self):
        self.assertEqual(linkcmp.longest_increasing([5, 1, 2, 9, 3, 4]), 4)


def archive(members: list[tuple[str, bytes]]) -> bytes:
    """A minimal COFF archive: the two symbol directories, a long-names member and the given members."""
    longnames = b"".join(n.encode() + b"\0" for n, _ in members if len(n) > 15)
    out, offsets, off = bytearray(b"!<arch>\n"), {}, 0
    for n, _ in members:
        if len(n) > 15:
            offsets[n] = off
            off += len(n) + 1
    def member(name: str, body: bytes) -> bytes:
        hdr = name.ljust(16).encode() + b" " * 32 + str(len(body)).ljust(10).encode() + b"`\n"
        return hdr + body + (b"\n" if len(body) & 1 else b"")
    out += member("/", b"\0" * 4) + member("/", b"\0" * 4) + member("//", longnames)
    for n, body in members:
        out += member(f"/{offsets[n]}" if n in offsets else n + "/", body)
    return bytes(out)


class LibraryLayout(unittest.TestCase):
    def test_members_are_read_by_file_name_and_import_members_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            lib = Path(d) / "LIBX.LIB"
            lib.write_bytes(archive([("build\\intel\\mt_obj\\memcpy.obj", b"\x4c\x01one"), ("a.obj", b"\x4c\x01two"),
                                     ("KERNEL32.dll", b"\0\0\xff\xffimp")]))
            got = link.archive_members(lib)
        self.assertEqual(got, {"memcpy.obj": b"\x4c\x01one", "a.obj": b"\x4c\x01two"})

    def test_layout_extracts_members_in_order_and_places_third_party(self):
        with tempfile.TemporaryDirectory() as d:
            lib = Path(d) / "LIBX.LIB"
            lib.write_bytes(archive([("a.obj", b"\x4c\x01a"), ("b.obj", b"\x4c\x01b")]))
            third = [Path(d) / "nv.obj"]
            got = link.library_layout("# c\nLIBX\tb.obj\t# 1\nthird-party\nlibx a.obj\n", [lib], Path(d) / "out", third)
            self.assertEqual([p.name for p in got], ["b.obj", "nv.obj", "a.obj"])
            self.assertEqual(got[0].read_bytes(), b"\x4c\x01b")
            self.assertEqual(link.library_layout("LIBX a.obj\n", [lib], Path(d) / "out", third)[-1], third[0])
            with self.assertRaises(SystemExit):
                link.library_layout("LIBX c.obj\n", [lib], Path(d) / "out", third)
            with self.assertRaises(SystemExit):
                link.library_layout("LIBY a.obj\n", [lib], Path(d) / "out", third)


class Thunks(unittest.TestCase):
    def test_thunk_object_defines_each_symbol_as_a_jump_through_its_import(self):
        names = ["_A@4", "_a_much_longer_symbol_name", "_C"]
        obj = link.thunk_object(names)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.obj"
            p.write_bytes(obj)
            coff = link.decomp.parse_coff(p)
        text = [s for s in coff.sections.values() if s.name == ".text"]
        self.assertEqual(len(text), 1)
        self.assertEqual(bytes(text[0].data), b"\xff\x25\0\0\0\0" * 3)
        defined = {s.name: s.value for s in coff.symbols.values() if s.section > 0 and not s.name.startswith(".")}
        self.assertEqual(defined, {"_A@4": 0, "_a_much_longer_symbol_name": 6, "_C": 12})
        self.assertEqual([(off, coff.symbols[si].name) for off, si, ty in text[0].relocs],
                         [(2, "__imp__A@4"), (8, "__imp__a_much_longer_symbol_name"), (14, "__imp__C")])
        self.assertTrue(all(ty == 6 for _o, _s, ty in text[0].relocs))

    def test_thunks_file_skips_comments_and_keeps_order(self):
        self.assertEqual(link.read_thunks("# c\n_X@4\tDLL.dll\tX\n\n_Y\tDLL.dll\t#7\n"), ["_X@4", "_Y"])

    def test_the_config_file_matches_the_specimens_thunk_run_when_present(self):
        if not link.decomp.SPECIMEN.exists():
            self.skipTest("specimen not present")
        import binfmt
        import linkcmp
        rows = [l.split("\t") for l in link.THUNKS.read_text().splitlines() if l.strip() and not l.startswith("#")]
        im = binfmt.PeImage(link.decomp.SPECIMEN)
        slot_name = {s: (dll, n) for dll, ents in linkcmp.import_table(im) for n, _h, s in ents}
        for k, (_sym, dll, imp) in enumerate(rows):
            stub = im.read(0x55D5E0 + 6 * k, 6)
            self.assertEqual(stub[:2], b"\xff\x25")
            self.assertEqual(slot_name[struct.unpack("<I", stub[2:])[0]], (dll, imp.strip()))
        self.assertEqual(len(rows), 32)


if __name__ == "__main__":
    unittest.main()
