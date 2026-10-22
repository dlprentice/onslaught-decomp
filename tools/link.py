#!/usr/bin/env python3
"""Link the compiled objects into a candidate BEA.exe with the pinned VC6 linker, then compare it with retail.

    python3 tools/link.py [--build DIR] [--out DIR] [--expected EXPECTED.json] [--order FILE]
                          [--lib-order FILE | --no-lib-order] [--no-provisional] [--no-compare]

Objects: every .obj under the build directory (default build/, as decomp.py check leaves it), in retail's link order
as config/link-objects.txt lists it (six groups, each case-insensitive alphabetical); any object it does not list
links after the listed ones, alphabetically. The objects listed after a line "[after libraries]" link after the
library members instead (LINK CONCESSION, see late_objects). Libraries: config/link-inputs.sha256, in its order (the
static libraries, then the import libraries in retail's import-descriptor order); each file is checked against its
SHA-256 first, and the link is refused if one differs or is missing. The retail-derived inputs (the import libraries
made from the game's DLLs) live in the untracked inputs folder (BEA_LAB); only their pins are tracked.

Third-party sources (config/link-sources.sha256, none at present) are checked against their pins, compiled with the
pinned compiler and linked. NVIDIA's NvTriStrip, which retail links as library code, is the prebuilt library retail used
(Visual C++ 6 with the Processor Pack, Rich comp.id (49, 9044) twice): the copy in Unreal Tournament 2003's Engine/Lib,
pinned in link-inputs.sha256 and laid out by the library order. Residual: its NvStripifier::RemoveSmallStrips is 672
bytes where retail's is 654; retail's exact release is not found (71 of retail's 72 NvTriStrip functions are identical). Provisional link-only pieces (linklib/, on unless
--no-provisional): each linklib/*.cpp is compiled and linked, and each alias in linklib/aliases.tsv becomes a weak
external of its target, for references the matched source makes whose retail owner, layout or body is still open.
They let the executable run; they are not part of the decompilation and never match.

Library layout (config/link-library-order.txt unless --lib-order names another file or --no-lib-order): the listed
library members, extracted from the pinned libraries, link as objects in that order after the game's objects, with
`third-party` marking where the compiled third-party objects go; members it does not list still come from the
libraries as the linker pulls them.

Import thunks (config/link-thunks.txt; LINK CONCESSION, on with the library layout): retail has 32 of its import thunks as one
run directly before its first CRT member, because it loaded those import-library members before the CRT members. Ours
are command-line objects, and LINK loads library members only after every object, so they would land at the end of
.text. link.py writes a COFF object (thunk_object) defining each thunk symbol as `jmp [__imp_SYMBOL]`, in retail's
order, and links it before the first library member; the import libraries then supply only the __imp_ data.

/VERBOSE is always on: link.log holds the library search (which members pass 1 loaded, in order), the /OPT:REF
discards and every identical-COMDAT fold, which tools/icfsim.py reads; it does not change the executable.

Writes BEA.exe, BEA.map, link.rsp, link.log and manifest.json (every input with its SHA-256, the unresolved and
multiply-defined symbols) to --out (default local-data/link/), then runs tools/linkcmp.py on the result (with
--expected, the symbol comparison too; tools/linkcmp.py --write-expected makes that file). Runs nothing it links.

The linker runs on Microsoft's C runtime, not Wine's: LINK.EXE imports qsort from MSVCRT.dll, and its identical-COMDAT
folding sorts the code contributions with it by (size, a 16-bit word) and keeps the first identical copy in the sorted
order, so the order qsort leaves equal keys in decides which copy survives (see tools/icfsim.py for the model of
its fold groups). Wine's builtin qsort orders equal keys differently from Microsoft's from 19 elements up; on one
frozen object set the two runtimes keep different survivors in 171 of 248 fold groups, and Microsoft's 6.00.8397 and
6.00.8797 agree in all of them. msvcrt is one of Wine's known DLLs, so a copy beside LINK.EXE is never loaded: link.py
links in its own prefix (link_prefix: a copy of the base prefix whose syswow64/msvcrt.dll is the pinned MSVCRT.DLL,
VC6 SP5's os/system/msvcrt.dll 6.00.8797.0; config/toolchain.sha256), never in a checkout's compile prefix, with
msvcrt=n,b for the process (the linker takes the native DLL; Wine's 64-bit helpers, which have none, fall back to the
builtin), and refuses a link whose loader trace does not show the native DLL.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import struct
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decomp  # noqa: E402

INPUTS = decomp.CONFIG / "link-inputs.sha256"
SOURCES = decomp.CONFIG / "link-sources.sha256"
LINKLIB = decomp.ROOT / "linklib"
OBJECT_ORDER = decomp.CONFIG / "link-objects.txt"
LIBRARY_ORDER = decomp.CONFIG / "link-library-order.txt"
THUNKS = decomp.CONFIG / "link-thunks.txt"
ROOTS = {"vc6": decomp.VC6, "lab": decomp.LAB}
# Stage options: the remaining unresolved symbols are forced (held rows and libraries not yet admitted); the DirectX 8
# libraries some objects name by default are not inputs.
OPTIONS = ["/nologo", "/VERBOSE", "/MACHINE:IX86", "/SUBSYSTEM:WINDOWS", "/FIXED", "/OPT:REF", "/OPT:ICF",
           "/INCREMENTAL:NO", "/FORCE:UNRESOLVED", "/FORCE:MULTIPLE",
           "/NODEFAULTLIB:d3dx8.lib", "/NODEFAULTLIB:d3d8.lib", "/NODEFAULTLIB:d3dxof.lib",
           "/NODEFAULTLIB:nvtristrip.lib"]    # NvTriStrip's own object names its library; it links as listed members


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_inputs(text: str, roots: dict[str, Path]) -> list[tuple[Path, str]]:
    """(path, pinned SHA-256) per line of a link-inputs file, in order; '#' lines are comments."""
    return [(path, digest) for path, digest, _opts in read_sources(text, roots)]


def read_sources(text: str, roots: dict[str, Path]) -> list[tuple[Path, str, list[str]]]:
    """(path, pinned SHA-256, compiler options) per line: <digest> <root> <path> [options]."""
    out = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, root, rel, *opts = line.split()
        if root not in roots:
            raise SystemExit(f"unknown root {root!r} in: {line}")
        out.append((roots[root] / rel, digest, opts))
    return out


def verify(inputs: list[tuple[Path, str]]) -> None:
    for path, digest in inputs:
        if not path.is_file():
            raise SystemExit(f"{path}: missing (pinned in {INPUTS.name})")
        if sha256(path) != digest:
            raise SystemExit(f"{path}: differs from its pin in {INPUTS.name}")


def archive_members(lib: Path) -> dict[str, bytes]:
    """A static library's COFF object members by lower-case file name (import members are skipped)."""
    data = lib.read_bytes()
    if data[:8] != b"!<arch>\n":
        raise SystemExit(f"{lib}: not an archive")
    members, longnames, pos = {}, b"", 8
    while pos + 60 <= len(data):
        name, size = data[pos:pos + 16].decode("latin-1").rstrip(), int(data[pos + 48:pos + 58])
        body = data[pos + 60:pos + 60 + size]
        if name == "//":
            longnames = body
        elif name != "/" and body[:2] == b"\x4c\x01":     # i386 COFF; import members start 00 00 ff ff
            if name.startswith("/") and name[1:].isdigit():
                off = int(name[1:])
                name = longnames[off:longnames.index(b"\0", off)].decode("latin-1")
            members.setdefault(name.rstrip("/").replace("\\", "/").rsplit("/", 1)[-1].lower(), body)
        pos += 60 + size + (size & 1)
    return members


def library_layout(text: str, libs: list[Path], out: Path, third: list[Path]) -> list[Path]:
    """The objects a --lib-order file names, in its order: LIB<TAB>member lines become that member, extracted from the
    pinned library whose file stem is LIB into out/libmembers/LIB/; a `third-party` line places the third-party
    objects. '#' starts a comment."""
    by_stem = {p.stem.lower(): p for p in libs}
    cache: dict[str, dict[str, bytes]] = {}
    objs, placed = [], False
    for line in text.splitlines():
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        if fields == ["third-party"]:
            objs += third
            placed = True
            continue
        lib, member = fields[0].lower(), fields[1].lower()
        if lib not in by_stem:
            raise SystemExit(f"--lib-order: {fields[0]} is not a pinned library")
        members = cache.setdefault(lib, archive_members(by_stem[lib]))
        if member not in members:
            raise SystemExit(f"--lib-order: {by_stem[lib].name} has no member {fields[1]}")
        path = out / "libmembers" / lib / member
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(members[member])
        objs.append(path)
    return objs + ([] if placed else third)


def objects(build: Path, order: str | None = None, src: Path | None = None) -> list[Path]:
    """build's objects: in the order's listing (source paths relative to src/, .cpp or .c, one per line, '#' comments),
    then any unlisted ones alphabetically by file name. An object names one source: a listing that gives both X.cpp and
    X.c is refused, as is an object src (when given) has both sources for."""
    rank = {}
    for line in (order or "").splitlines():
        if line.strip() and not line.startswith("#") and line.strip() != "[after libraries]":
            rank.setdefault(line.strip().replace("\\", "/").lower(), len(rank))
    for name in rank:
        if name.endswith(".c") and name + "pp" in rank:
            raise SystemExit(f"link-objects: {name} and {name}pp would both name {name[:-2]}.obj")
    if src is not None:
        for c in src.rglob("*.c"):
            if c.with_suffix(".cpp").exists():
                raise SystemExit(f"{c} and {c.with_suffix('.cpp')} would both build {c.stem}.obj")
    def key(p: Path):
        rel = p.relative_to(build).with_suffix("").as_posix().lower()
        place = rank.get(rel + ".cpp", rank.get(rel + ".c", len(rank)))
        return (place, p.name.lower(), str(p))
    return sorted(build.rglob("*.obj"), key=key)


def late_objects(objs: list[Path], build: Path, order: str | None = None) -> list[Path]:
    """The objects the order lists after its "[after libraries]" line, which link after the library members.
    LINK CONCESSION, compensating for our tooling: LINK allocates COMMON symbols in reverse input order of their defining
    objects, with commons from library-searched members after every object's. Retail searched LIBCMT as a library, so
    its CRT commons came after the game's; we link the extracted members as objects, after the game's objects, so a
    game object holding commons (pausecommons.c) has to link after them to keep its commons ahead of the CRT's."""
    late, after = set(), False
    for line in (order or "").splitlines():
        if line.strip() == "[after libraries]":
            after = True
        elif after and line.strip() and not line.startswith("#"):
            late.add(line.strip().replace("\\", "/").lower())
    def name(p: Path) -> str:
        return p.relative_to(build).with_suffix("").as_posix().lower()
    return [p for p in objs if name(p) + ".cpp" in late or name(p) + ".c" in late]


def response(objs: list[Path], libs: list[Path], out: Path, order: Path | None = None) -> str:
    opts = OPTIONS + ([f"/ORDER:@{decomp.winpath(order)}"] if order else []) + [f"/MAP:{decomp.winpath(out / 'BEA.map')}", f"/OUT:{decomp.winpath(out / 'BEA.exe')}"]
    return "\n".join(opts + [decomp.winpath(p) for p in objs] + [decomp.winpath(p) for p in libs]) + "\n"


def read_aliases(text: str) -> list[tuple[str, str]]:
    """(alias, target) per line of an aliases file: alias<TAB>target<TAB>why; '#' lines are comments."""
    return [tuple(line.split("\t")[:2]) for line in text.splitlines() if line.strip() and not line.startswith("#")]


def alias_object(pairs: list[tuple[str, str]]) -> bytes:
    """A COFF object with one empty section in which each alias is a weak external searched for its target
    (IMAGE_WEAK_EXTERN_SEARCH_ALIAS): the linker resolves the alias to the target's definition."""
    strtab, recs = bytearray(4), []

    def name(n: str) -> bytes:
        b = n.encode("latin-1")
        if len(b) <= 8:
            return b.ljust(8, b"\0")
        off = len(strtab)
        strtab.extend(b + b"\0")
        return struct.pack("<II", 0, off)
    for alias, target in pairs:
        tag = len(recs)
        recs.append(struct.pack("<8sIhHBB", name(target), 0, 0, 0, 2, 0))      # the target, an undefined external
        recs.append(struct.pack("<8sIhHBB", name(alias), 0, 0, 0, 105, 1))     # the alias, a weak external
        recs.append(struct.pack("<II10x", tag, 3))                             # its aux record: search for the target
    struct.pack_into("<I", strtab, 0, len(strtab))
    section = struct.pack("<8sIIIIIIHHI", b".data", 0, 0, 0, 0, 0, 0, 0, 0, 0xC0300040)
    header = struct.pack("<HHIIIHH", 0x14C, 1, 0, 20 + 40, len(recs), 0, 0)
    return header + section + b"".join(recs) + bytes(strtab)


def read_thunks(text: str) -> list[str]:
    """The thunk symbols of a link-thunks file, in order: SYMBOL<TAB>DLL<TAB>import name; '#' lines are comments."""
    return [line.split("\t")[0] for line in text.splitlines() if line.strip() and not line.startswith("#")]


def thunk_object(names: list[str]) -> bytes:
    """A COFF object with one .text section of `jmp [__imp_NAME]` stubs, six bytes each and contiguous, defining NAME for
    each name (the symbols the import libraries' short-import members would define); each stub's operand is a DIR32
    relocation against the undefined external __imp_NAME."""
    strtab = bytearray(4)

    def name(n: str) -> bytes:
        b = n.encode("latin-1")
        if len(b) <= 8:
            return b.ljust(8, b"\0")
        off = len(strtab)
        strtab.extend(b + b"\0")
        return struct.pack("<II", 0, off)
    code = b"\xff\x25\0\0\0\0" * len(names)
    recs = [struct.pack("<8sIhHBB", name(n), 6 * i, 1, 0x20, 2, 0) for i, n in enumerate(names)]      # the thunks
    relocs = []
    for i, n in enumerate(names):
        recs.append(struct.pack("<8sIhHBB", name("__imp_" + n), 0, 0, 0, 2, 0))                      # the undefined __imp_
        relocs.append(struct.pack("<IIH", 6 * i + 2, len(names) + i, 6))                              # IMAGE_REL_I386_DIR32
    struct.pack_into("<I", strtab, 0, len(strtab))
    raw = 20 + 40
    section = struct.pack("<8sIIIIIIHHI", b".text", 0, 0, len(code), raw, raw + len(code), 0, len(relocs), 0, 0x60100020)
    header = struct.pack("<HHIIIHH", 0x14C, 1, 0, raw + len(code) + 10 * len(relocs), len(recs), 0, 0)
    return header + section + code + b"".join(relocs) + b"".join(recs) + bytes(strtab)


def compile_cpp(src: Path, obj: Path, options: list[str]) -> Path:
    """Compile one source with the pinned compiler and the project's flags (config/flags.txt) plus options."""
    flags = (decomp.CONFIG / "flags.txt").read_text().split()
    env = dict(os.environ, WINEPREFIX=decomp.WINEPREFIX, WINEDEBUG="-all", WINEDLLOVERRIDES="mscoree,mshtml=",
               WINEPATH=f"{decomp.winpath(decomp.VC6 / 'VC98/Bin')};{decomp.winpath(decomp.VC6 / 'Common/MSDev98/Bin')}",
               INCLUDE=f"{decomp.winpath(decomp.DX9_INCLUDE)};{decomp.winpath(decomp.VC6 / 'VC98/Include')}")
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    opts = [f"/FI{decomp.winpath(decomp.ROOT / o[3:])}" if o.startswith("/FI") else o for o in options]
    obj.parent.mkdir(parents=True, exist_ok=True)
    obj.unlink(missing_ok=True)
    with decomp.prefix_lock():
        r = subprocess.run(["wine", str(decomp.VC6 / "VC98/Bin/CL.EXE"), "/nologo", "/c", *flags, *opts,
                            f"/Fo{decomp.winpath(obj)}", decomp.winpath(src)], env=env, cwd=src.parent,
                           capture_output=True, text=True, errors="replace", timeout=600)
    if not obj.exists():
        raise SystemExit(f"{src}: compile failed\n{r.stdout}{r.stderr}")
    return obj


def third_party(out: Path) -> list[Path]:
    """Compile config/link-sources.sha256's sources (each checked against its pin first) into out/third-party."""
    if not SOURCES.exists():
        return []
    sources = read_sources(SOURCES.read_text(), ROOTS)
    verify([(p, d) for p, d, _o in sources])
    return [compile_cpp(p, out / "third-party" / p.with_suffix(".obj").name, opts)
            for p, _d, opts in sources if p.suffix.lower() == ".cpp"]


def provisional(out: Path) -> list[Path]:
    """Compile linklib/*.cpp and write the alias object into out/linklib; the objects to link."""
    lib = out / "linklib"
    lib.mkdir(parents=True, exist_ok=True)
    objs = [compile_cpp(src, lib / src.with_suffix(".obj").name, []) for src in sorted(LINKLIB.glob("*.cpp"))]
    aliases = LINKLIB / "aliases.tsv"
    if aliases.exists():
        obj = lib / "aliases.obj"
        obj.write_bytes(alias_object(read_aliases(aliases.read_text())))
        objs.append(obj)
    return objs


NATIVE_CRT = decomp.VC6 / "os/system/MSVCRT.DLL"


def link_prefix(base: Path | None = None) -> Path:
    """The Wine prefix the linker runs in: a copy of the base prefix (made on first use, like decomp.checkout_prefix)
    whose 32-bit msvcrt.dll is the pinned native one. Named by the DLL's digest, shared by every checkout (the linker
    reads and writes only Z: paths), and repaired if the DLL there no longer matches the pin."""
    base = base or decomp.BASE_PREFIX
    digest = sha256(NATIVE_CRT)
    prefix = base.with_name(f"{base.name}-link-msvcrt-{digest[:12]}")
    crt = prefix / "drive_c/windows/syswow64/msvcrt.dll"
    if not prefix.exists():
        staging = prefix.with_name(prefix.name + ".partial")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(base, staging, symlinks=True, ignore=shutil.ignore_patterns(".onslaught-decomp.lock", "ONSLAUGHT2"))
        (staging / "drive_c/windows/syswow64/msvcrt.dll").write_bytes(NATIVE_CRT.read_bytes())
        staging.rename(prefix)
    if sha256(crt) != digest:
        crt.write_bytes(NATIVE_CRT.read_bytes())
    return prefix


def native_crt_loaded(trace: str) -> bool:
    """Whether a +loaddll trace shows the 32-bit MSVCRT.dll loaded as native (the linker's), never as builtin."""
    loads = [l for l in trace.splitlines() if "loaddll" in l and re.search(r'\\msvcrt\.dll" at [0-9A-F]{8}:', l, re.I)]
    return bool(loads) and all(l.rstrip().endswith("native") for l in loads)


def unresolved(log: str) -> list[str]:
    """Each unresolved symbol once, by its decorated name where the linker gives one."""
    found = set()
    for line in log.splitlines():
        if "LNK2001" in line or "LNK2019" in line:
            m = re.search(r"\((\?\S+)\)\s*$", line) or re.search(r"unresolved external symbol (\S+)", line)
            if m:
                found.add(m.group(1))
    return sorted(found)


def link(build: Path, out: Path, with_provisional: bool = True, order: Path | None = None,
         lib_order: Path | None = None) -> dict:
    decomp.check_toolchain()
    inputs = read_inputs(INPUTS.read_text(), ROOTS)
    verify(inputs)
    objs = objects(build, OBJECT_ORDER.read_text() if OBJECT_ORDER.exists() else None, decomp.ROOT / "src")
    if not objs:
        raise SystemExit(f"{build}: no objects (run tools/decomp.py check first)")
    out.mkdir(parents=True, exist_ok=True)
    third = third_party(out)
    members = library_layout(lib_order.read_text(), [p for p, _ in inputs], out, third) if lib_order else third
    if lib_order and THUNKS.exists():       # LINK CONCESSION (config/link-thunks.txt): retail's 32 thunks before the CRT
        (out / "thunks.obj").write_bytes(thunk_object(read_thunks(THUNKS.read_text())))
        members = [out / "thunks.obj"] + members
    late = late_objects(objs, build, OBJECT_ORDER.read_text() if OBJECT_ORDER.exists() else None)
    objs = [o for o in objs if o not in late]
    extra = members + (provisional(out) if with_provisional else []) + late
    for name in ("BEA.exe", "BEA.map"):
        (out / name).unlink(missing_ok=True)
    rsp = out / "link.rsp"
    rsp.write_text(response(objs + extra, [p for p, _ in inputs], out, order))
    prefix = link_prefix()
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG="-all,+loaddll", WINEDLLOVERRIDES="mscoree,mshtml=;msvcrt=n,b",
               WINEPATH=f"{decomp.winpath(decomp.VC6 / 'VC98/Bin')};{decomp.winpath(decomp.VC6 / 'Common/MSDev98/Bin')}",
               LIB=decomp.winpath(decomp.VC6 / "VC98/Lib"))
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    with open(prefix / ".onslaught-decomp.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        r = subprocess.run(["wine", str(decomp.VC6 / "VC98/Bin/LINK.EXE"), "@" + decomp.winpath(rsp)], env=env,
                           cwd=out, capture_output=True, text=True, errors="replace", timeout=1800)
    if not native_crt_loaded(r.stderr):
        raise SystemExit(f"{prefix}: the linker did not load the native MSVCRT.dll; its fold order would be Wine's")
    log = (r.stdout + "\n".join(l for l in r.stderr.splitlines() if ":loaddll:" not in l)).replace("\r", "")
    (out / "link.log").write_text(log)
    exe = out / "BEA.exe"
    manifest = {"linker": [str(decomp.VC6 / "VC98/Bin/LINK.EXE"), sha256(decomp.VC6 / "VC98/Bin/LINK.EXE")],
                "crt": [str(NATIVE_CRT), sha256(prefix / "drive_c/windows/syswow64/msvcrt.dll"), str(prefix)],
                "options": OPTIONS, "objects": [[str(p), sha256(p)] for p in objs],
                "lib_order": str(lib_order) if lib_order else None,
                "provisional": [[str(p), sha256(p)] for p in extra],
                "libraries": [[str(p), d] for p, d in inputs], "returncode": r.returncode,
                "unresolved": unresolved(log),
                "multiply_defined": sorted(set(re.findall(r"LNK(?:2005|4006): .*?\((\S+)\) already defined", log))),
                "exe_sha256": sha256(exe) if exe.exists() else None}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(objs)} objects, {len(extra)} library members, third-party and provisional, {len(inputs)} libraries | "
          f"link return code {r.returncode} | "
          f"unresolved {len(manifest['unresolved'])} | multiply defined {len(manifest['multiply_defined'])} | "
          f"{exe if exe.exists() else 'no executable'}", flush=True)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", type=Path, default=decomp.BUILD)
    ap.add_argument("--out", type=Path, default=decomp.ROOT / "local-data/link")
    ap.add_argument("--expected", type=Path, help="tools/linkcmp.py --write-expected output, for the symbol comparison")
    ap.add_argument("--no-compare", action="store_true")
    ap.add_argument("--order", type=Path, help="a /ORDER file: COMDAT (function) names, one per line, in link order")
    lib = ap.add_mutually_exclusive_group()
    lib.add_argument("--lib-order", type=Path, help=f"library members in link order (default {LIBRARY_ORDER.name})")
    lib.add_argument("--no-lib-order", action="store_true", help="leave the library members to the linker's own pulls")
    ap.add_argument("--no-provisional", action="store_true", help="leave out linklib/ (the link then leaves symbols unresolved)")
    a = ap.parse_args()
    out = a.out.resolve()
    lib_order = None if a.no_lib_order else (a.lib_order or (LIBRARY_ORDER if LIBRARY_ORDER.exists() else None))
    manifest = link(a.build.resolve(), out, not a.no_provisional, a.order.resolve() if a.order else None,
                    lib_order.resolve() if lib_order else None)
    if manifest["exe_sha256"] and not a.no_compare:
        cmd = [sys.executable, str(Path(__file__).with_name("linkcmp.py")), str(out / "BEA.exe"),
               "--map", str(out / "BEA.map"), "--json", str(out / "linkcmp.json")]
        if a.expected:
            cmd += ["--expected", str(a.expected)]
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
