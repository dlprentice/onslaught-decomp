#!/usr/bin/env python3
"""Compile the decompiled source with the original Visual C++ 6 toolchain and compare it with the retail game.

Each function in src/ carries an annotation naming its retail address:

    // FUNCTION: 0x004a2ff0
    void CMemoryBlock::SetBaseSet(BOOL bs) { ... }

VC6 at /O2 puts every function in its own COMDAT section, padded with NOPs to 16 bytes, and the linker
lays those sections end to end. A function matches when its whole section equals the retail bytes at its
address, relocation fields aside, and every relocation lands where the rest of the evidence says:
  - a reference into the function's own section lands inside it;
  - a call or reference to an annotated function lands on that function's address;
  - a string literal or floating-point constant lands on identical retail bytes;
  - an import reference lands on the retail import slot of the same name;
  - an independently identified library symbol lands on its proven entry, even if
    other reconstructed callers consistently imply a different entry;
  - any other symbol lands on one consistent address wherever it is used (recorded as discovered).

Commands:
  decomp.py build            compile every source file into build/
  decomp.py check [FILE...]  build, compare and print each function's result
  decomp.py score            build, compare all files and rewrite the score in README.md
  decomp.py diff ADDRESS     side-by-side disassembly of one annotated function against retail
  decomp.py dis ADDRESS      retail disassembly of one function, with callee names and import slots
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import fcntl
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from binfmt import (REL_DIR32, REL_DIR32NB, REL_REL32, REL_WIDTH, SYM_EXTERNAL, SYM_STATIC, Coff, PeImage,  # noqa: E402
                    parse_coff)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
BUILD = ROOT / "build"
SPECIMEN_SHA256 = "74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750"
# Input locations: each from an environment variable, else from an optional local tools/site_paths.py (your own
# defaults; this tree has none). Without either, the commands that need an input stop and name its variable.
try:
    import site_paths as _site  # noqa: E402
except ImportError:
    _site = None


# An input that is not set is this path below UNSET (it never exists), so paths can still be formed from it; commands
# that read it stop in require_inputs() with the variable's name.
UNSET = Path("/nonexistent-unset")


def setting(var: str, attr: str, public: Path | None = None) -> Path:
    if os.environ.get(var):
        return Path(os.environ[var])
    if _site is not None and hasattr(_site, attr):
        return Path(getattr(_site, attr))
    return public if public is not None else UNSET / var


def is_unset(path: Path) -> bool:
    return path.is_relative_to(UNSET)


# BEA_LAB: the folder of the link's further inputs (the paths config/link-inputs.sha256 marks "lab" are relative to it).
LAB = setting("BEA_LAB", "LAB")
# BEA_PRISTINE: your own retail BEA.exe, SHA-256 SPECIMEN_SHA256 (read only).
SPECIMEN = setting("BEA_PRISTINE", "PRISTINE")
# BEA_VC6: the Visual C++ 6.0 SP5 install (VC98/, Common/MSDev98/, os/system/), pinned by config/toolchain.sha256.
VC6 = setting("BEA_VC6", "VC6")
# BEA_VC6_AT and BEA_DXSDK_AT: the Windows paths at which the compiler sees its own install and the DirectX SDK. The
# tools link them inside the Wine prefix's drive C (like C:\\dev\\ONSLAUGHT2 for src/), so the paths the compiler
# sees, and the header paths a precompiled header records, are the same wherever the files are. Defaults: VC6's and the
# SDK's own default install folders. "-" runs the compiler from the files' own location instead (Wine's Z: drive).
# The precompiled header is keyed on these paths (pch_file()): a
# header made under one set of paths and used under another changes code (CHud::RenderWorldTargetSprites by 672 bytes).
CANONICAL_VC6_AT = "C:\\Program Files\\Microsoft Visual Studio"
CANONICAL_DXSDK_AT = "C:\\DXSDK"


def windows_location(var: str, attr: str, default: str) -> str | None:
    value = os.environ.get(var) or (getattr(_site, attr, "-") if _site is not None else default)
    if value == "-":
        return None
    if not re.fullmatch(r"C:(?:\\[^\\/:*?\"<>|]+)+", value):
        raise SystemExit(f"{var}={value!r}: expected a folder on drive C, such as {default!r}, or -")
    return value


VC6_AT = windows_location("BEA_VC6_AT", "VC6_AT", CANONICAL_VC6_AT)
DXSDK_AT = windows_location("BEA_DXSDK_AT", "DXSDK_AT", CANONICAL_DXSDK_AT)
# BEA_WINE_BASE: the base Wine prefix (32-bit capable) the compiler runs in; other copies of the tree and the linker
# take copies of it.
BASE_PREFIX = setting("BEA_WINE_BASE", "WINE_BASE",
                      Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "onslaught-decomp/wine")
# BEA_DX9_INCLUDE: the DirectX 9.0 SDK headers (the Include folder of Microsoft's dx9sdk.exe), pinned by
# config/dx9sdk-include.sha256; first on the include path, where the SDK installer put them.
DX9_INCLUDE = setting("BEA_DX9_INCLUDE", "DX9_INCLUDE")
# The DirectX 9.0 SDK sample framework's headers (Samples/C++/Common/Include, from the same dx9sdk.exe): d3dapp.cpp
# includes D3DUtil.h and DXUtil.h from them, as Stuart's d3dapp.cpp does. After the SDK's own headers on the path.
DX9_SAMPLES_INCLUDE = setting("BEA_DX9_SAMPLES_INCLUDE", "DX9_SAMPLES_INCLUDE")
# The variable each input is read from, for require_inputs()' messages.
INPUT_VARS = {"BEA_PRISTINE": "SPECIMEN", "BEA_VC6": "VC6", "BEA_DX9_INCLUDE": "DX9_INCLUDE",
              "BEA_DX9_SAMPLES_INCLUDE": "DX9_SAMPLES_INCLUDE"}


def require_inputs(*names: str) -> None:
    """Stop with the variable's name when an input location is unset or missing (all of them by default)."""
    for var, attr in INPUT_VARS.items():
        if names and attr not in names:
            continue
        path = globals()[attr]
        if is_unset(path):
            raise SystemExit(f"{var} is not set: see the README's 'Reproducing the match'")
        if not path.exists():
            raise SystemExit(f"{var}: {path} does not exist")
GAME_END = 0x0055D6A0          # identified library code starts here
# The linker's import thunks, `jmp dword ptr [IAT slot]` stubs it emits from import libraries for DLL functions the
# game calls without dllimport (DirectSound, AVIFile, zlib, Ogg Vorbis, version.dll). They are library code: each is
# verified against the import table (import_thunks) and counted apart from the game functions, never compiled.
IMPORT_THUNKS = (0x0055D5E0, 0x0055D6A0)
FUNCLETS = 0x005D0F10          # compiler-generated unwind funclets of game functions, to the end of .text
# Specimen-bound CRT identities, independently checked against the pinned library
# and their owning code/data sections.
# Consistent caller relocation inference alone cannot prove a library's identity:
# the old feature/explosion drafts both called acos where retail calls asin.
PROVEN_LIBRARY_SYMBOLS = {
    "__CIasin": 0x0055DCB0, "_asin": 0x0055DCC4,
    "__CIacos": 0x0055F380, "_acos": 0x0055F394,
    "__CIfmod": 0x0055E3EA, "_fmod": 0x0055E3E0,
    "__CIpow": 0x0055FA40, "_pow": 0x0055FA59,
    "_floor": 0x0055DFE7, "_ceil": 0x0055EB3D,
    # Throwing array constructor iterator: complete pinned LIBCMT ehvecctr.obj
    # text/scope sections and their fixed CRT owners, October 3 recheck.
    "??_L@YGXPAXIHP6EX0@Z1@Z": 0x0055DC20,
    # Complete pinned d3dx9.lib gateways and native fast-table initializers,
    # October 8 recheck.
    "_D3DXVec3TransformCoord@12": 0x00576161,
    "_D3DXVec3Project@24": 0x00576297,
    "_D3DXMatrixMultiply@12": 0x005768FE,
    "_D3DXMatrixInverse@12": 0x00576E0A,
    "_D3DXMatrixTranslation@16": 0x00577267,
}
ANNOTATION = re.compile(r"^\s*//\s*FUNCTION:\s*(0x[0-9a-fA-F]{8})(?:\s+(\S+))?\s*$")
# A trailing annotation on the definition line itself, which keeps a seeded file's line numbers intact
# (its __LINE__ values are compiled into the retail code).
TRAILING = re.compile(r"^(?P<code>.*\S)\s*//\s*FUNCTION:\s*(?P<addr>0x[0-9a-fA-F]{8})(?:\s+(?P<sym>\S+))?\s*$")


# ---------------------------------------------------------------------------
# Toolchain
# ---------------------------------------------------------------------------

def winpath(p: Path) -> str:
    return "Z:" + str(p.resolve()).replace("/", "\\")


def check_toolchain() -> None:
    require_inputs("VC6", "DX9_INCLUDE", "DX9_SAMPLES_INCLUDE")
    for line in (CONFIG / "toolchain.sha256").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        if hashlib.sha256((VC6 / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"{VC6 / rel}: differs from the pinned toolchain")
    for root, pin, label in (
            (DX9_INCLUDE, "dx9sdk-include.sha256", "DirectX 9 SDK"),
            (VC6 / "VC98/Include", "vc6-include.sha256", "Visual C++ 6")):
        manifest = "".join(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  ./{f.relative_to(root)}\n"
                           for f in sorted(p for p in root.rglob("*") if p.is_file()))
        if hashlib.sha256(manifest.encode()).hexdigest() != (CONFIG / pin).read_text().split()[0]:
            raise SystemExit(f"{root}: differs from the pinned {label} headers")
    # the sample framework's headers: every file in the folder, each pinned by name and digest
    pinned = {}
    for line in (CONFIG / "dx9samples-include.sha256").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            digest, rel = line.split(maxsplit=1)
            pinned[rel] = digest
    present = {str(f.relative_to(DX9_SAMPLES_INCLUDE)): hashlib.sha256(f.read_bytes()).hexdigest()
               for f in DX9_SAMPLES_INCLUDE.rglob("*") if f.is_file()}
    if present != pinned:
        raise SystemExit(f"{DX9_SAMPLES_INCLUDE}: differs from the pinned DirectX 9 SDK sample framework headers")


def checkout_prefix() -> Path:
    """The Wine prefix this checkout compiles in: BEA_WINEPREFIX when set. Otherwise a clone (a .git folder) uses the
    base prefix, and any other copy of the tree (a Git worktree, an unpacked export) its own copy of the base prefix, made
    on first use, so several copies can compile at the same time."""
    if os.environ.get("BEA_WINEPREFIX"):
        return Path(os.environ["BEA_WINEPREFIX"])
    if (ROOT / ".git").is_dir():
        return BASE_PREFIX
    prefix = BASE_PREFIX.with_name(f"{BASE_PREFIX.name}-{ROOT.name}")
    if not prefix.exists() and BASE_PREFIX.exists():
        staging = prefix.with_name(prefix.name + ".partial")
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(BASE_PREFIX, staging, symlinks=True,
                        ignore=shutil.ignore_patterns(".onslaught-decomp.lock", "ONSLAUGHT2"))
        staging.rename(prefix)
    return prefix


WINEPREFIX = str(checkout_prefix())


def original_path(src: Path) -> str:
    """The retail build compiled from C:\\dev\\ONSLAUGHT2\\ (its __FILE__ strings say so); the Wine prefix maps
    that folder onto src/, so the compiler sees the same path and __FILE__ comes out byte for byte."""
    link = Path(WINEPREFIX) / "drive_c/dev/ONSLAUGHT2"
    if not link.is_symlink() or link.resolve() != (ROOT / "src").resolve():
        link.parent.mkdir(parents=True, exist_ok=True)
        link.unlink(missing_ok=True)
        link.symlink_to(ROOT / "src")
    return "C:\\dev\\ONSLAUGHT2\\" + str(src.relative_to(ROOT / "src")).replace("/", "\\")


def prefix_link(at: str, target: Path) -> None:
    """Point the prefix's drive-C folder AT (a Windows path on C:) at TARGET, as original_path() does for src/."""
    link = Path(WINEPREFIX) / "drive_c" / Path(*at[3:].split("\\"))
    if not link.is_symlink() or link.resolve() != target.resolve():
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            raise SystemExit(f"{link}: exists in the Wine prefix and is not this tool's link; move it or choose another path")
        link.symlink_to(target.resolve())


def compiler_paths(link: bool = True) -> dict[str, str]:
    """The Windows paths the compiler runs with: CL.EXE, and the PATH, INCLUDE and LIB values. With VC6_AT and DXSDK_AT
    set, the inputs are linked into the prefix at those paths (unless link is false; call with the prefix lock held)."""
    if VC6_AT:
        if link:
            prefix_link(VC6_AT, VC6)
        vc6 = VC6_AT
    else:
        vc6 = winpath(VC6)
    if DXSDK_AT:
        dx, samples = DXSDK_AT + "\\Include", DXSDK_AT + "\\Samples\\C++\\Common\\Include"
        if link:
            prefix_link(dx, DX9_INCLUDE)
            prefix_link(samples, DX9_SAMPLES_INCLUDE)
    else:
        dx, samples = winpath(DX9_INCLUDE), winpath(DX9_SAMPLES_INCLUDE)
    return {"CL": vc6 + "\\VC98\\Bin\\CL.EXE", "WINEPATH": f"{vc6}\\VC98\\Bin;{vc6}\\Common\\MSDev98\\Bin",
            "INCLUDE": f"{dx};{samples};{vc6}\\VC98\\Include", "LIB": vc6 + "\\VC98\\Lib"}


def compiler_env(paths: dict[str, str]) -> dict[str, str]:
    env = dict(os.environ, WINEPREFIX=WINEPREFIX, WINEDEBUG="-all", WINEDLLOVERRIDES="mscoree,mshtml=",
               WINEPATH=paths["WINEPATH"], INCLUDE=paths["INCLUDE"], LIB=paths["LIB"])
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    return env


@contextlib.contextmanager
def prefix_lock():
    """A prefix's C:\\dev\\ONSLAUGHT2 link names one src/ at a time (BEA_WINEPREFIX can point checkouts at the
    same prefix): hold this lock from pointing the link at our src/ until the compiler has finished."""
    with open(Path(WINEPREFIX) / ".onslaught-decomp.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def compile_source(src: Path, obj: Path, flags: list[str]) -> subprocess.CompletedProcess:
    obj.parent.mkdir(parents=True, exist_ok=True)
    obj.unlink(missing_ok=True)
    with prefix_lock():
        paths = compiler_paths()
        env = compiler_env(paths)
        cmd = ["wine", paths["CL"], "/nologo", "/c", *flags, f"/Fo{winpath(obj)}", original_path(src)]
        # Wine services can retain inherited pipe writers after CL has exited, delaying communicate() by
        # about four seconds per source. Regular files retain compiler diagnostics without waiting for pipe EOF.
        # Keep the prefix lock until CL exits and its diagnostics are read; no Wine service is killed.
        with tempfile.TemporaryFile(mode="w+", errors="replace", dir=obj.parent) as stdout, \
                tempfile.TemporaryFile(mode="w+", errors="replace", dir=obj.parent) as stderr:
            result = subprocess.run(cmd, env=env, stdout=stdout, stderr=stderr, cwd=src.parent)
            stdout.seek(0)
            stderr.seek(0)
            return subprocess.CompletedProcess(result.args, result.returncode, stdout.read(), stderr.read())


# The retail build used a precompiled header made from common.h, as Stuart's projects do (MoHo's pch.cpp is
# `#include "Common.h"`). It decides the layout of each object's .bss: the compiler lays out a source's uninitialised
# and dynamically initialised definitions in reverse definition order and its explicitly initialised ones after them
# in definition order, where without the PCH it walks the uninitialised ones in a name-hash order
# (measured 2026-10-14 with probe sources). Every source compiles with /Yu on its own include of
# common.h (spelled as the source spells it, e.g. ..\common.h); /Yu skips the text before that include, as retail's
# build did. config/no-pch.txt names the sources that cannot, with the reason. src/pch.cpp makes the PCH (/Yc).
PCH_SOURCE = ROOT / "src/pch.cpp"


def no_pch() -> set[str]:
    return {line.split(":")[0].strip() for line in (CONFIG / "no-pch.txt").read_text().splitlines()
            if line.strip() and not line.startswith("#")}


def pch_file() -> Path:
    """The PCH for the current headers and flags, built when missing. It is named by a digest of what it holds:
    common.h's closure of quoted includes, the flags, the toolchain pin and the compiler's paths (a PCH records the
    paths of the headers it read, and one used under other paths changes the code compiled with it)."""
    seen, todo = [], ["common.h"]
    while todo:
        name = todo.pop()
        if name.lower() in (n.lower() for n in seen):
            continue
        seen.append(name)
        path = next((f for f in (ROOT / "src").iterdir() if f.name.lower() == name.lower()), None)
        if path:
            todo += re.findall(r'^\s*#\s*include\s*"([^"]+)"', path.read_text(errors="replace"), re.M)
    h = hashlib.sha256((CONFIG / "flags.txt").read_bytes() + (CONFIG / "toolchain.sha256").read_bytes())
    h.update(json.dumps(compiler_paths(link=False), sort_keys=True).encode())
    for name in sorted(seen, key=str.lower):
        path = next((f for f in (ROOT / "src").iterdir() if f.name.lower() == name.lower()), None)
        h.update(name.lower().encode() + (path.read_bytes() if path else b""))
    pch = BUILD / "pch" / f"common-{h.hexdigest()[:16]}.pch"
    if not pch.exists():
        obj = pch.with_suffix(".obj")
        p = compile_source(PCH_SOURCE, obj, (CONFIG / "flags.txt").read_text().split() + ["/Yccommon.h", f"/Fp{winpath(pch)}"])
        obj.unlink(missing_ok=True)
        if not pch.exists():
            raise SystemExit("src/pch.cpp: the precompiled header was not made\n" + p.stdout + p.stderr)
    return pch


def flags_for(src: Path) -> list[str]:
    """Default flags from config/flags.txt; a line 'FILE: flags' in config/file-flags.txt replaces them. A source
    with the default flags uses the precompiled header unless config/no-pch.txt names it."""
    default = (CONFIG / "flags.txt").read_text().split()
    override = CONFIG / "file-flags.txt"
    if override.exists():
        for line in override.read_text().splitlines():
            name, _, flags = line.partition(":")
            if name.strip() == src.name:
                return flags.split()
    if src.resolve() == PCH_SOURCE or src.name in no_pch():
        return default
    return default + [f"/Yu{pch_include(src)}", f"/Fp{winpath(pch_file())}"]


def pch_include(src: Path) -> str:
    """The path /Yu must name for the source's include of common.h: its own relative prefix (..\\ in MissionScript/)
    and common.h (the compiler matches the name without regard to case); common.h when the source has no prefix or
    does not include it."""
    m = re.search(r'^\s*#\s*include\s*"((?:\.\.[\\/])*)common\.h"', src.read_text(errors="replace"), re.M | re.I)
    return (m.group(1) if m else "") + "common.h"


def sources() -> list[Path]:
    return sorted(p for p in (ROOT / "src").rglob("*") if p.suffix.lower() in (".c", ".cpp") and p != PCH_SOURCE)


# BEA_GAME: the game folder whose files config/game-data.sha256 pins; by default the folder holding the specimen.
GAME = setting("BEA_GAME", "-", SPECIMEN.parent)


def link_game_data() -> None:
    """Some sources include files the game ships (Career.cpp includes data\\MissionScripts\\onsldef.msl). They stay
    out of the repository: each file pinned in config/game-data.sha256 is linked into the ignored src/data/ from the
    retained game folder after its hash is checked."""
    if is_unset(GAME):
        raise SystemExit("BEA_GAME is not set: see the README's 'Reproducing the match'")
    for line in (CONFIG / "game-data.sha256").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        source = GAME / rel
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise SystemExit(f"{source}: differs from the pinned game data")
        link = ROOT / "src" / rel
        if not (link.is_symlink() and link.resolve() == source.resolve()):
            link.parent.mkdir(parents=True, exist_ok=True)
            link.unlink(missing_ok=True)
            link.symlink_to(source)


SPECIMEN_DATA = (0x634550, 0x63C108)      # retail virtual addresses of the NVIDIA shader-fragment library in .data


def link_specimen_data() -> None:
    """Specimen data: NVIDIA shader-fragment library (no shipped source). Retail's .data holds five serialized vertex-shader
    fragment objects (NVFO: eyespace, lighting, objectspace, miscvertex, custom) between VertexShader's declaration-name
    table and its enable flag; the game ships none of the sources and no code reads the blocks, so the only copy is the
    specimen's. VertexShader.cpp includes them as an initializer from the ignored src/data/NVShaderFragments.inc, written
    here from the pinned specimen's bytes; nothing retail-derived is tracked."""
    lo, hi = SPECIMEN_DATA
    require_inputs("SPECIMEN")
    blob = PeImage(SPECIMEN, SPECIMEN_SHA256).read(lo, hi - lo)
    if blob is None or len(blob) != hi - lo:
        raise SystemExit("the specimen does not map the shader-fragment library")
    rows = [", ".join(f"0x{b:02x}" for b in blob[i:i + 16]) for i in range(0, len(blob), 16)]
    text = ",\n".join(rows) + "\n"
    dest = ROOT / "src" / "data" / "NVShaderFragments.inc"
    if not dest.is_file() or dest.read_text() != text:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)


def remove_case_twins(obj: Path) -> None:
    """Wine opens files case-insensitively, so an object left by a source whose name differed only in case (unit.obj
    after unit.cpp became Unit.cpp) would receive the new output under its old name. Remove such twins first."""
    if obj.parent.is_dir():
        for other in obj.parent.iterdir():
            if other.name.lower() == obj.name.lower() and other.name != obj.name:
                other.unlink()


@dataclass
class ObjectPatch:
    source: str
    symbol: str
    offset: int
    expected: bytes
    replacement: bytes
    reason: str


def object_patches() -> list[ObjectPatch]:
    """config/object-patches.tsv: the build concessions written into compiled objects (see that file's header)."""
    out = []
    for line in (CONFIG / "object-patches.tsv").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        source, symbol, offset, expected, replacement, reason = line.split("\t")
        exp, rep = bytes.fromhex(expected), bytes.fromhex(replacement)
        if len(exp) != len(rep) or exp == rep:
            raise SystemExit(f"config/object-patches.tsv: {symbol}: expected and replacement must differ and be equal length")
        out.append(ObjectPatch(source, symbol, int(offset, 16), exp, rep, reason))
    return out


def apply_object_patches(src: Path, obj: Path, patches: list[ObjectPatch]) -> int:
    """Write each patch for src into obj, in the section that defines its symbol; stop unless the expected bytes are
    exactly at the offset. Returns the number of bytes changed."""
    mine = [p for p in patches if p.source == src.name]
    if not mine:
        return 0
    data = bytearray(obj.read_bytes())
    coff = parse_coff(obj)
    _machine, _nsec, _ts, _psym, _nsym, optsize, _ch = struct.unpack_from("<HHIIIHH", data, 0)
    changed = 0
    for p in mine:
        syms = [s for s in coff.symbols.values() if s.name == p.symbol and s.section > 0]
        if len(syms) != 1:
            raise SystemExit(f"{obj.name}: object patch: {p.symbol} defined {len(syms)} times")
        sym = syms[0]
        rptr = struct.unpack_from("<I", data, 20 + optsize + 40 * (sym.section - 1) + 20)[0]
        at = rptr + sym.value + p.offset
        if bytes(data[at:at + len(p.expected)]) != p.expected:
            raise SystemExit(f"{obj.name}: object patch {p.symbol}+{p.offset:#x}: expected {p.expected.hex()}, "
                             f"found {bytes(data[at:at + len(p.expected)]).hex()} (the source moved; re-measure the concession)")
        data[at:at + len(p.replacement)] = p.replacement
        changed += sum(a != b for a, b in zip(p.expected, p.replacement))
        print(f"{src.name}: build concession {p.symbol}+{p.offset:#x}: {p.expected.hex()} -> {p.replacement.hex()}")
    obj.write_bytes(bytes(data))
    return changed


def build(files: list[Path], concessions: bool = False) -> dict[Path, Path]:
    """Compile each source into build/. With concessions, also write config/object-patches.tsv into the objects: only
    this tool's own CLI (check, score, diff, build) asks for that, so every other caller of build() measures the
    natural compiler output."""
    check_toolchain()
    link_game_data()
    link_specimen_data()
    patches = object_patches() if concessions else []
    out = {}
    for src in files:
        obj = BUILD / src.relative_to(ROOT / "src").with_suffix(".obj")
        remove_case_twins(obj)
        p = compile_source(src, obj, flags_for(src))
        text = (p.stdout + p.stderr).replace("\r", "")
        lines = [l for l in text.splitlines() if l.strip() and l.strip() != src.name
                 and not l.startswith(("MESA", "pci id for fd"))]      # Wine's GPU probe, not the compiler
        if p.returncode != 0 or not obj.exists():
            print("\n".join(lines))
            raise SystemExit(f"{src.relative_to(ROOT)}: compile failed")
        warnings = [l for l in lines if "warning" in l]
        if warnings:
            print("\n".join(warnings))
        apply_object_patches(src, obj, patches)
        out[src] = obj
    return out


# ---------------------------------------------------------------------------
# Retail tables
# ---------------------------------------------------------------------------

@dataclass
class RetailFunction:
    address: int
    size: int
    name: str


def retail_functions() -> dict[int, RetailFunction]:
    """The imported function table, with config/function-corrections.tsv applied: a corrected extent or a function the
    table never defined replaces or adds its row, and 0 bytes removes a row that is not a function. Each correction
    names its evidence."""
    with (CONFIG / "functions.tsv").open() as f:
        table = {int(r["address"], 16): RetailFunction(int(r["address"], 16), int(r["bytes"]), r["name"])
                 for r in csv.DictReader(f, delimiter="\t")}
    with (CONFIG / "function-corrections.tsv").open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            a, size = int(r["address"], 16), int(r["bytes"])
            if size:
                table[a] = RetailFunction(a, size, r["name"])
            else:
                table.pop(a, None)
    return table


# ---------------------------------------------------------------------------
# Annotations and symbols
# ---------------------------------------------------------------------------

@dataclass
class Annotation:
    address: int
    file: Path
    line: int
    qualified: str          # e.g. CMemoryBlock::SetBaseSet, from the definition after the annotation
    symbol: str | None      # an explicit mangled symbol, when the name alone is ambiguous
    params: int | None = None   # the definition's parameter count, to tell overloads apart


_CLASS_HEAD = re.compile(r"^(?:class|struct)\s+(\w+)\b[^;]*$|^DECLARE_\w*CLASS\((\w+)")
_DEF_NAME = re.compile(r"((?:[A-Za-z_]\w*\s*::\s*)*(?:operator\s*(?:\(\)|[^\s(]+)|~?[A-Za-z_]\w*))\s*\(")


def annotations() -> list[Annotation]:
    out = []
    files = sorted(p for p in (ROOT / "src").rglob("*") if p.suffix.lower() in (".c", ".cpp", ".h"))
    for path in files:
        lines = path.read_text(errors="replace").splitlines()
        enclosing = None        # the class whose body we are in: a bare member name is qualified with it
        for i, line in enumerate(lines):
            c = _CLASS_HEAD.match(line)
            if c:
                enclosing = c.group(1) or c.group(2)
            elif line.startswith("};"):
                enclosing = None
            m = ANNOTATION.match(line)
            t = None if m else TRAILING.match(line)
            if not m and not t:
                continue
            qualified, params = "", None
            for follow in ([t.group("code")] if t else lines[i + 1:i + 8]):
                if follow.strip().startswith("//") or not follow.strip():
                    continue
                d = _DEF_NAME.search(follow)
                if d:
                    qualified = re.sub(r"\s+", "", d.group(1))
                    if enclosing and "::" not in qualified:
                        qualified = f"{enclosing}::{qualified}"
                    rest = follow[d.end():]
                    if ")" in rest:     # a parameter list that continues on later lines is not counted
                        inside = rest.split(")")[0].strip()
                        params = 0 if inside in ("", "void") else inside.count(",") + 1
                    break
            if t:
                out.append(Annotation(int(t.group("addr"), 16), path, i + 1, qualified, t.group("sym"), params))
            else:
                out.append(Annotation(int(m.group(1), 16), path, i + 1, qualified, m.group(2), params))
    return out


def demangled_params(text: str | None) -> int | None:
    """The parameter count of a demangled signature, or None when it cannot be read."""
    if not text or "(" not in text:
        return None
    inside = text[text.index("(") + 1:text.rindex(")")].strip()
    if inside in ("", "void"):
        return 0
    depth, commas = 0, 0         # only top-level commas: a function-pointer parameter has its own
    for ch in inside:
        depth += ch in "(<"
        depth -= ch in ")>"
        commas += ch == "," and depth == 0
    return commas + 1


def demangle(symbols: list[str]) -> dict[str, str]:
    mangled = sorted({s for s in symbols if s.startswith("?")})
    if not mangled:
        return {}
    text = subprocess.run(["llvm-undname"], input="\n".join(mangled) + "\n", capture_output=True, text=True).stdout
    lines, want, result = text.split("\n"), set(mangled), {}
    for i, line in enumerate(lines[:-1]):
        if line in want and line not in result and not lines[i + 1].startswith("error:"):
            result[line] = lines[i + 1]
    return result


def qualified_of(symbol: str, demangled: dict[str, str]) -> str:
    """Class::Method (or a plain name) from a mangled or C symbol."""
    text = demangled.get(symbol)
    if text is None:
        return re.sub(r"@\d+$", "", symbol).lstrip("_")
    head = text.split("(")[0]
    return head.split(" ")[-1].replace("`", "")


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

@dataclass
class FunctionResult:
    address: int
    symbol: str
    source: str
    status: str                          # match | bytes | relocations | size | unplaced
    size: int                            # section bytes compared
    differing: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class Checker:
    def __init__(self) -> None:
        self.image = PeImage(SPECIMEN, SPECIMEN_SHA256)
        self.retail = retail_functions()
        self.discovered: dict[str, set[int]] = {}      # proven library entries plus matched-code implications
        self.witness: dict[tuple[str, int], int] = {}  # (symbol, implied address) -> the first function implying it
        self.implied_by: dict[int, set[str]] = {}      # function address -> the symbols its relocations placed
        # Existing scanners consume this map too. Keep independent identities
        # visible even when no reconstructed caller yet matches; their first
        # witness is the identified library entry itself.
        for name, target in PROVEN_LIBRARY_SYMBOLS.items():
            self.record_target(name, target, target)

    def record_target(self, key: str, target: int, witness: int) -> None:
        self.discovered.setdefault(key, set()).add(target)
        self.witness.setdefault((key, target), witness)
        self.implied_by.setdefault(witness, set()).add(key)

    def implied(self, typ: int, site: int, addend: int) -> int | None:
        value = self.image.u32(site)
        if value is None:
            return None
        if typ == REL_DIR32:
            return (value - addend) & 0xFFFFFFFF
        if typ == REL_DIR32NB:
            return (value + self.image.image_base - addend) & 0xFFFFFFFF
        if typ == REL_REL32:
            return (value + site + 4 - addend) & 0xFFFFFFFF
        return None

    def compare(self, coff: Coff, secnum: int, va: int, placed: dict[str, int]) -> tuple[list[int], list[str], bool]:
        """Differing byte offsets, relocation notes, and whether every relocation checks out."""
        sec = coff.sections[secnum]
        extent = self.retail.get(va)
        retail = self.image.read(va, len(sec.data))
        if retail is None:
            return list(range(len(sec.data))), ["outside the image"], False
        masked = set()
        for off, _s, typ in sec.relocs:
            masked.update(range(off, off + REL_WIDTH.get(typ, 4)))
        differing = [i for i, (a, b) in enumerate(zip(sec.data, retail)) if a != b and i not in masked]
        if extent is not None and len(sec.data) < extent.size:
            # Preserve useful prefix differences, but never infer relocation targets or award a whole
            # body for a shorter section. Larger sections still have all their padding compared.
            return differing, [f"compiled section has {len(sec.data)} bytes; retail body requires {extent.size}"], False
        if differing:
            return differing, [], False         # relocations of different code imply nothing
        notes, ok = [], True
        for off, symidx, typ in sec.relocs:
            sym = coff.symbols[symidx]
            addend = int.from_bytes(sec.data[off:off + 4], "little") if REL_WIDTH.get(typ) == 4 else 0
            target = self.implied(typ, va + off, addend)
            verdict = self.check_target(coff, sym, target, va, secnum, placed)
            if verdict is not True:
                ok = False
                notes.append(f"+0x{off:x} {sym.name}: {verdict}")
        return differing, notes, ok

    def check_target(self, coff: Coff, sym, target: int | None, va: int, secnum: int, placed: dict[str, int]):
        if target is None:
            return "unreadable"
        if sym.storage == SYM_EXTERNAL and sym.name in PROVEN_LIBRARY_SYMBOLS:
            expected = PROVEN_LIBRARY_SYMBOLS[sym.name]
            if target != expected:
                return f"lands at {target:08x}, independently identified library entry is {expected:08x}"
            self.record_target(sym.name, expected, va)
            return True
        if sym.section == secnum:
            return True if target == va + sym.value else f"lands at {target:08x}, not inside its own section"
        if sym.section == -1:                   # an absolute symbol, such as __except_list (fs:0)
            return True if target == sym.value else f"lands at {target:08x}, not at absolute {sym.value:08x}"
        name = sym.name
        if sym.section > 0 and name.startswith(("??_C@", "__real@")):
            # a pooled string literal or floating-point constant: the retail bytes there must be the same
            want = coff.sections[sym.section].data
            if self.image.read(target, len(want)) != want:
                return f"{'string' if name.startswith('??_C@') else 'constant'} at {target:08x} differs"
            return True
        if name.startswith("__imp_"):
            slot = self.image.imports.get(target)
            want = re.sub(r"@\d+$", "", name[len("__imp_"):]).lstrip("_")
            got = None if slot is None else re.sub(r"@\d+$", "", slot.split("!")[-1]).lstrip("_")
            return True if got == want else f"import slot {target:08x} is {slot}, not {name}"
        key = symbol_key(coff.path.stem, name, sym.storage)
        if key in placed:
            return True if placed[key] == target else f"lands at {target:08x}, annotated at {placed[key]:08x}"
        self.record_target(key, target, va)
        return True


def symbol_key(stem: str, name: str, storage: int) -> str:
    """Externals are shared by name; a file-local symbol (a static function or variable) is its object's own."""
    return name if storage == SYM_EXTERNAL else f"{stem}:{name}"


def function_sections(coff: Coff) -> list[tuple[int, str]]:
    """(section, symbol) for each code section that defines a function at its start."""
    out = []
    for secnum, sec in coff.sections.items():
        if not sec.code:
            continue
        syms = [s for s in coff.defined_in(secnum)
                if s.value == 0 and s.storage in (SYM_EXTERNAL, SYM_STATIC) and s.name != sec.name
                and (s.type & 0x30) == 0x20]
        if syms:
            out.append((secnum, syms[0].name))
    return out


def check(objects: dict[Path, Path]) -> tuple[list[FunctionResult], Checker]:
    marks = annotations()
    checker = Checker()
    coffs = {src: parse_coff(obj) for src, obj in objects.items()}
    all_symbols = [s.name for c in coffs.values() for s in c.symbols.values()]
    names = demangle(all_symbols)
    by_qualified: dict[str, list[Annotation]] = {}
    for a in marks:
        by_qualified.setdefault(a.qualified, []).append(a)
    # A dynamic initializer is annotated by the variable it constructs: init:NAME is the _$E function that
    # .CRT$XCU calls and that refers to NAME; exit:NAME is the atexit thunk the initializer registers.
    def initializer_symbols(coff: Coff) -> dict[str, str]:
        refs: dict[str, set[str]] = {}
        for secnum, symbol in function_sections(coff):
            if symbol.startswith("_$E"):
                refs[symbol] = {coff.symbols[i].name for _o, i, _t in coff.sections[secnum].relocs}
        called = {coff.symbols[i].name for sec in coff.sections.values() if sec.name.startswith(".CRT$XC")
                  for _o, i, _t in sec.relocs}
        out = {}
        for symbol, names_ in refs.items():
            for name in names_:
                bare = name[1:name.index("@")] if name.startswith("?") and "@" in name else name.lstrip("_")
                if symbol in called:
                    out.setdefault(f"init:{bare}", symbol)
                    for other in names_ & set(refs):
                        out.setdefault(f"exit:{bare}", other)
        # An aggregate array's initializer is a wrapper that .CRT$XCU calls and that only jumps to the body that
        # builds the array: init:NAME is the wrapper and initbody:NAME the body (FEPGoodies' goodies, 0045ac20).
        for symbol in called & set(refs):
            for inner in refs[symbol] & set(refs):
                if inner in called:
                    continue
                for name in refs[inner]:
                    bare = name[1:name.index("@")] if name.startswith("?") and "@" in name else name.lstrip("_")
                    if bare.startswith("$E"):
                        continue
                    out.setdefault(f"init:{bare}", symbol)
                    out.setdefault(f"initbody:{bare}", inner)
        # An empty initializer (a static whose constructor compiles to a bare ret) carries no relocation to name its
        # variable; initorder:K is the K-th entry (from 1) the object's .CRT$XCU sections call, in link order, which
        # follows the declaration order of the object's dynamically initialised globals (MeshPart's cache statics).
        order = []
        for sec in sorted((x for x in coff.sections.values() if x.name.startswith(".CRT$XC")), key=lambda x: x.name):
            for _o, i, _t in sorted(sec.relocs):
                order.append(coff.symbols[i].name)
        for k, symbol in enumerate(order, 1):
            if symbol in refs and not refs[symbol]:
                out.setdefault(f"initorder:{k}", symbol)
        # A function-local static's destructor thunk is an _$E function that the enclosing function registers with
        # atexit, with no .CRT$XCU entry: localexit:CLASS::FUNC names it (#K for the K-th, in relocation order).
        for secnum, symbol in function_sections(coff):
            if symbol.startswith("_$E"):
                continue
            thunks = []
            for _o, i, _t in sorted(coff.sections[secnum].relocs):
                n = coff.symbols[i].name
                if n in refs and n not in called and n not in thunks:
                    thunks.append(n)
            if not thunks:
                continue
            if symbol.startswith("?") and "@@" in symbol:
                owner = "::".join(reversed(symbol[1:symbol.index("@@")].split("@")))
            else:
                owner = symbol.lstrip("_")
            for k, t in enumerate(thunks, 1):
                out.setdefault(f"localexit:{owner}" + (f"#{k}" if k > 1 else ""), t)
        return out

    initializers = {src: initializer_symbols(coff) for src, coff in coffs.items()}
    marks = [Annotation(a.address, a.file, a.line, a.qualified,
                        initializers.get(a.file, {}).get(a.symbol, a.symbol) if a.symbol else a.symbol, a.params)
             for a in marks]
    # Place each annotated function: an explicit symbol wins; otherwise the qualified name must be unique
    placed: dict[str, int] = {}
    candidates: dict[str, list[tuple[Path, int]]] = {}
    homes: dict[str, tuple[Path, int]] = {}
    annotated_in: dict[str, Path] = {}      # the file whose annotation placed the key
    for src, coff in coffs.items():
        for secnum, symbol in function_sections(coff):
            storage = next(x.storage for x in coff.defined_in(secnum) if x.name == symbol)
            key = symbol_key(coff.path.stem, symbol, storage)
            # a file-local function (such as a dynamic initializer, _$E<n>) is annotated in its own source file
            explicit = [a for a in marks if a.symbol == symbol and (storage == SYM_EXTERNAL or a.file == src)]
            q = qualified_of(symbol, names)
            # a member defined inside its class body is annotated by its bare name
            by_name = [a for a in marks if a.symbol is None and a.qualified
                       and (a.qualified == q or ("::" not in a.qualified and q.endswith("::" + a.qualified)))]
            # overloads: keep the annotations whose parameter count agrees (an unannotated overload never takes
            # its sibling's annotation)
            count = demangled_params(names.get(symbol))
            by_name = [a for a in by_name if a.params is None or count is None or a.params == count]
            chosen = explicit or by_name
            # the same COMDAT annotated identically in two objects' files is one claim, not a conflict
            chosen = list({(a.address, a.symbol, a.qualified): a for a in chosen}.values())
            if len(chosen) == 1 and key not in placed:
                placed[key] = chosen[0].address
                annotated_in[key] = chosen[0].file
                candidates[key] = [(src, secnum)]
            elif len(chosen) == 1 and placed.get(key) == chosen[0].address:
                candidates[key].append((src, secnum))   # the same COMDAT emitted by another object
    # The linker keeps one copy of a COMDAT that several objects emit; the retail bytes are whichever copy it kept, so
    # the copy that compares best is the one checked (a match, then clean relocations, then the fewest differing bytes);
    # among equally good copies, the one in the file that carries the annotation (it names where retail's copy came from).
    for key, cands in candidates.items():
        if len(cands) == 1:
            homes[key] = cands[0]
            continue
        scored = []
        for src, secnum in cands:
            state = ({k: set(v) for k, v in checker.discovered.items()}, dict(checker.witness),
                     {k: set(v) for k, v in checker.implied_by.items()})
            differing, _notes, ok = checker.compare(coffs[src], secnum, placed[key], placed)
            checker.discovered, checker.witness, checker.implied_by = state
            scored.append(((0 if not differing and ok else 1 if not differing else 2, len(differing),
                            0 if src == annotated_in.get(key) else 1), src, secnum))
        best = min(scored, key=lambda t: t[0])
        homes[key] = (best[1], best[2])
    results = []
    for src, coff in coffs.items():
        for secnum, symbol in function_sections(coff):
            storage = next(x.storage for x in coff.defined_in(secnum) if x.name == symbol)
            key = symbol_key(coff.path.stem, symbol, storage)
            if key not in placed or homes[key] != (src, secnum):
                continue
            va = placed[key]
            differing, notes, ok = checker.compare(coff, secnum, va, placed)
            sec = coff.sections[secnum]
            extent = checker.retail.get(va)
            status = ("size" if extent is not None and len(sec.data) < extent.size else
                      "match" if not differing and ok else "bytes" if differing else "relocations")
            results.append(FunctionResult(va, symbol, str(src.relative_to(ROOT)), status, len(sec.data), differing, notes))
    # an annotation is unplaced when its own file was compiled (or, for a header, when everything was)
    compiled = set(objects)
    everything = compiled == set(sources())
    unplaced = [a for a in marks if a.address not in {r.address for r in results}
                and (a.file in compiled or (a.file.suffix.lower() == ".h" and everything))]
    for a in unplaced:
        results.append(FunctionResult(a.address, a.symbol or a.qualified, f"{a.file.relative_to(ROOT)}:{a.line}", "unplaced", 0,
                                      notes=["no compiled function matched this annotation"]))
    checker.vtables = check_vtables(coffs, names, placed, checker)
    # Tables also constrain external method identities. Finalize only after their discovery, so a later
    # table cannot contradict a function's target while leaving the earlier function marked as a match.
    # A constructor's exact reference to a table address does not prove that table's contents; the two
    # results remain separate, and only a direct dependency on the conflicted symbol rejects a function.
    conflicted = {k for k, v in checker.discovered.items() if len(v) > 1}
    for r in results:
        bad = sorted(checker.implied_by.get(r.address, set()) & conflicted)
        if r.status == "match" and bad:
            r.status = "relocations"
            r.notes.append("places a symbol other code or tables place elsewhere: " + ", ".join(bad))
    return sorted(results, key=lambda r: r.address), checker


def retail_vtables() -> dict[tuple[str, int], tuple[int, int]]:
    """Unique nonempty (class, subobject offset) tables from the RTTI scan.

    A reference to a complete-object locator with no following code pointers is not a virtual table. Keep
    ambiguous positive-slot candidates unresolved rather than letting file order choose an identity.
    """
    path = CONFIG / "classes.tsv"
    if not path.exists():
        return {}
    candidates: dict[tuple[str, int], set[tuple[int, int]]] = {}
    with path.open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if int(r["slots"]) > 0:
                key = (r["class"], int(r["subobjectOffset"], 16))
                candidates.setdefault(key, set()).add((int(r["vftable"], 16), int(r["slots"])))
    return {key: next(iter(values)) for key, values in candidates.items() if len(values) == 1}


def check_vtables(coffs: dict, names: dict[str, str], placed: dict[str, int], checker) -> list[tuple[str, str]]:
    """Compare every compiled virtual table (??_7Class@@6B@...) with the retail table of the same class and
    subobject: each slot needs one DIR32 relocation, and its target must agree with every other use.
    Under /GR the section opens with a pointer to the table's complete object locator; that pointer is checked
    against the retail dword before the table like any other target.

    VC6 emits relocation-bearing pointer words, including pure virtual slots. An unexplained raw word
    (even zero) is not a verified slot. Defer verdicts until all tables have contributed their identities.
    """
    retail = retail_vtables()
    tables = sorted(retail.items())
    bases_of: dict[str, dict[str, int]] = {}
    with (CONFIG / "classes.tsv").open() as f:
        for r in csv.DictReader(f, delimiter="\t"):
            for b in filter(None, r["bases"].split(";")):
                name, _, off = b.rpartition("@")
                bases_of.setdefault(r["class"], {})[name] = int(off, 16)
    pending = []
    for src, coff in coffs.items():
        for sym in coff.symbols.values():
            if not sym.name.startswith("??_7") or sym.section <= 0:
                continue
            text = names.get(sym.name, "")
            cls = text.replace("const ", "").split("::`vftable'")[0].strip()
            base = text.split("{for `")[1].rstrip("'}") if "{for `" in text else None
            sec = coff.sections[sym.section]
            # With /GR (retail's build) the table's section opens with one pointer to its complete object
            # locator (??_R4...), and the table symbol follows it at offset 4; retail has that pointer in the
            # dword before the table (CActor: 0060c288 before 005d844c).
            head = [r for r in sec.relocs if r[0] < sym.value]
            col = head[0] if sym.value == 4 and len(head) == 1 and head[0][0] == 0 and \
                coff.symbols[head[0][1]].name.startswith("??_R4") else None
            start = 4 if col is not None else 0
            slots = (len(sec.data) - start) // 4
            cands = [(k, v) for k, v in tables if k[0] == cls]
            # a table "for" a base serves the subobject at that base's offset (config/classes.tsv bases)
            if base is not None and base not in bases_of.get(cls, {}):
                pending.append((f"{cls} for {base}", ["no proven secondary-base offset"], None))
                continue
            offset = 0 if base is None else bases_of[cls][base]
            cands = [(k, v) for k, v in cands if k[1] == offset]
            if len(cands) != 1:
                pending.append((f"{cls}{' for ' + base if base else ''}", ["no unique retail table"], None))
                continue
            (_k, (vt, count)) = cands[0]
            problems = []
            if count != slots:
                problems.append(f"{slots} slots, retail {count}")
            if sym.value != start or len(sec.data) % 4:
                problems.append("table is not a complete array of DWORD slots at section start")
            offsets = [off for off, _idx, _typ in sec.relocs]
            if sorted(offsets) != list(range(0, len(sec.data), 4)):
                problems.append("each slot requires exactly one aligned relocation")
            if any(typ != REL_DIR32 for _off, _idx, typ in sec.relocs):
                problems.append("table requires DIR32 relocations")
            label = f"{cls}{' for ' + base if base else ''} @ {vt:08x}"
            if problems:
                # A malformed or differently sized layout cannot establish external identities.
                pending.append((label, problems, None))
                continue
            # The RTTI selection also witnesses the table's own address. Otherwise an exact constructor
            # could place this named table elsewhere without ever meeting the class-table evidence.
            key = symbol_key(coff.path.stem, sym.name, sym.storage)
            if key in placed and placed[key] != vt:
                problems.append(f"table annotated at {placed[key]:08x}, RTTI selects {vt:08x}")
            elif key not in placed:
                checker.record_target(key, vt, vt)
            for off, symidx, typ in sec.relocs:
                value = checker.image.u32(vt - start + off)
                addend = int.from_bytes(sec.data[off:off + 4], "little")
                target = None if value is None else (value - addend) & 0xFFFFFFFF
                rs = coff.symbols[symidx]
                verdict = checker.check_target(coff, rs, target, vt, sym.section, placed) \
                    if not rs.name.startswith("__purecall") else (True if target == 0x0055df1f else "not _purecall")
                if verdict is not True:
                    where = "COL" if off < start else f"slot {(off - start) // 4}"
                    problems.append(f"{where} {names.get(rs.name, rs.name)}: {verdict}")
            pending.append((label, problems, vt))
    conflicted = {key for key, values in checker.discovered.items() if len(values) > 1}
    out = []
    for label, problems, vt in pending:
        bad = sorted(checker.implied_by.get(vt, set()) & conflicted) if vt is not None else []
        if bad:
            problems.append("places a symbol other code or tables place elsewhere: " + ", ".join(bad))
        out.append((label, "match" if not problems else "; ".join(problems[:4])))
    return out


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def unique_matches(results: list[FunctionResult]) -> list[FunctionResult]:
    """Count a folded retail body once, using a stable source/symbol representative.

    Per-symbol results and matched.tsv retain the aliases. A matching alias proves one body,
    not a second function at the same address; an unmatched alias does not erase a separately proven body.
    """
    matches: dict[int, FunctionResult] = {}
    for r in sorted(results, key=lambda r: (r.address, r.source, r.symbol)):
        if r.status == "match":
            matches.setdefault(r.address, r)
    return list(matches.values())


def import_thunks(image, retail: dict[int, RetailFunction]) -> list[tuple[int, str, bool]]:
    """(address, table name, verified) for each function in the import-thunk block. A thunk is verified when it is
    exactly `FF 25` and the address of an IAT slot, and, when that slot imports by name, the name is the function's
    table name. An import by ordinal (DSOUND.dll!#11, zlib.dll!#9) names nothing to compare; the stub is still the
    linker's."""
    out = []
    for a in sorted(x for x in retail if IMPORT_THUNKS[0] <= x < IMPORT_THUNKS[1]):
        f = retail[a]
        code = image.read(a, 6)
        ok = f.size == 6 and code is not None and code[:2] == b"\xff\x25"
        if ok:
            slot = image.imports.get(int.from_bytes(code[2:6], "little"))
            ok = slot is not None and (slot.split("!")[-1].startswith("#") or slot.split("!")[-1] == f.name)
        out.append((a, f.name, ok))
    return out


def score(results: list[FunctionResult], retail: dict[int, RetailFunction],
          thunks: list[tuple[int, str, bool]] = ()) -> dict:
    verified = {a for a, _name, ok in thunks if ok}
    game = [f for f in retail.values() if f.address < GAME_END and f.address not in verified]
    funclets = [f for f in retail.values() if f.address >= FUNCLETS]
    matched = [r for r in unique_matches(results) if r.address in retail]
    matched_game = [r for r in matched if r.address < GAME_END]
    return {
        "gameFunctions": len(game), "gameBytes": sum(f.size for f in game),
        "funclets": len(funclets), "funcletBytes": sum(f.size for f in funclets),
        "matchedFunctions": len(matched_game), "matchedBytes": sum(retail[r.address].size for r in matched_game),
        "attempted": len({r.address for r in results if r.address < GAME_END}),
        "importThunks": len(verified),
        "buildConcessions": len({p.symbol for p in object_patches()}),
    }


def write_readme(s: dict, results: list[FunctionResult], retail: dict[int, RetailFunction]) -> None:
    pct_f = 100.0 * s["matchedFunctions"] / s["gameFunctions"]
    pct_b = 100.0 * s["matchedBytes"] / s["gameBytes"]
    patched = {p.symbol for p in object_patches()}
    rows = ["| Address | Function | Bytes | Source |", "| --- | --- | ---: | --- |"]
    for r in unique_matches(results):
        mark = " (build concession)" if r.symbol in patched else ""
        if r.address in retail:
            rows.append(f"| `{r.address:08x}` | {retail[r.address].name}{mark} | {retail[r.address].size} | {r.source} |")
        else:       # matched code the imported function table lacks (a table gap to fix)
            rows.append(f"| `{r.address:08x}` | ({r.symbol}; not in the function table) | {r.size} | {r.source} |")
    block = (f"**{s['matchedFunctions']:,} of {s['gameFunctions']:,} game functions ({pct_f:.2f}%) and "
             f"{s['matchedBytes']:,} of {s['gameBytes']:,} bytes ({pct_b:.2f}%) match the retail executable byte for "
             f"byte.** " + (f"{s['buildConcessions']:,} matched through a build concession, bytes written into the "
             f"compiled object after compiling (`config/object-patches.tsv`; the source alone leaves "
             f"{s['matchedFunctions'] - s['buildConcessions']:,} matching). " if s.get("buildConcessions") else "") +
             f"{s['attempted']:,} functions are annotated. The {s['funclets']:,} compiler-generated unwind "
             f"funclets ({s['funcletBytes']:,} bytes) are counted with their parent objects once those match. "
             f"{s.get('importThunks', 0):,} import thunks (the linker's `jmp [IAT]` stubs for DLL calls, each verified "
             f"against the import table) are library code and not counted.\n\n"
             "### Matched functions\n\n" + "\n".join(rows) + "\n")
    # The score block lives in README.md here; a tree with docs/SCORE.md (the public export) keeps it there instead.
    readme = ROOT / "docs/SCORE.md" if (ROOT / "docs/SCORE.md").exists() else ROOT / "README.md"
    text = readme.read_text()
    begin, end = "<!-- score:begin -->\n", "<!-- score:end -->"
    i, j = text.index(begin) + len(begin), text.index(end)
    readme.write_text(text[:i] + block + text[j:])


def disassemble(data: bytes, va: int) -> list[str]:
    BUILD.mkdir(parents=True, exist_ok=True)
    # Concurrent idiom searches and excerpts must not overwrite another call's input.
    with tempfile.NamedTemporaryFile(dir=BUILD, prefix="disassembly-", suffix=".bin") as tmp:
        tmp.write(data)
        tmp.flush()
        text = subprocess.run(["objdump", "-D", "-b", "binary", "-m", "i386", "-M", "intel", "--no-show-raw-insn",
                               f"--adjust-vma=0x{va:x}", tmp.name], capture_output=True, text=True).stdout
    return [l.strip() for l in text.splitlines() if re.match(r"^\s*[0-9a-f]+:", l)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    c = sub.add_parser("check")
    c.add_argument("files", nargs="*", type=Path)
    c.add_argument("-v", "--verbose", action="store_true")
    sub.add_parser("score")
    d = sub.add_parser("diff")
    d.add_argument("address")
    d.add_argument("files", nargs="*", type=Path, help="sources to build (default: the one annotating ADDRESS)")
    r = sub.add_parser("dis")
    r.add_argument("address")
    args = ap.parse_args()
    if args.cmd == "dis":
        image, table = PeImage(SPECIMEN, SPECIMEN_SHA256), retail_functions()
        va = int(args.address, 16)
        names = {f"{a:08x}": f.name for a, f in table.items()}
        for line in disassemble(image.read(va, table[va].size), va):
            target = re.search(r"\b0x([0-9a-f]{6,8})\b", line)
            hint = names.get(target.group(1).zfill(8)) if target else None
            slot = image.imports.get(int(target.group(1), 16)) if target else None
            print(line + (f"    ; {hint or slot}" if hint or slot else ""))
        return
    files = [p.resolve() for p in getattr(args, "files", [])]
    if not files and args.cmd == "diff":
        # Build only the file that annotates the address: seconds, not the whole tree.
        tag = f"function: 0x{int(args.address, 16):08x}"
        files = [s for s in sources() if tag in s.read_text(errors="replace").lower()]
    files = files or sources()
    objects = build(files, concessions=True)
    if args.cmd == "build":
        return
    results, checker = check(objects)
    retail = checker.retail
    if args.cmd == "diff":
        want = int(args.address, 16)
        r = next(r for r in results if r.address == want)
        src = next(s for s in objects if str(s.relative_to(ROOT)) == r.source)
        coff = parse_coff(objects[src])
        secnum = next(n for n, sym in function_sections(coff) if sym == r.symbol)
        ours = disassemble(coff.sections[secnum].data, want)
        theirs = disassemble(checker.image.read(want, r.size), want)
        width = max(len(l) for l in ours) + 2
        for k in range(max(len(ours), len(theirs))):
            a = ours[k] if k < len(ours) else ""
            b = theirs[k] if k < len(theirs) else ""
            flag = " " if a.split(":", 1)[-1] == b.split(":", 1)[-1] else "*"
            print(f"{flag} {a:<{width}}| {b}")
        print("\n".join(r.notes))
        return
    for r in results:
        name = retail[r.address].name if r.address in retail else "?"
        line = f"{r.status:12s} {r.address:08x} {name:40s} {r.source}"
        if r.status != "match":
            line += f"  ({len(r.differing)} bytes differ)" if r.differing else ""
        print(line)
        if args.cmd == "check" and args.verbose:
            for n in r.notes:
                print("      ", n)
    s = score(results, retail, import_thunks(checker.image, retail))
    print(json.dumps(s))
    for name, verdict in getattr(checker, "vtables", []):
        print(f"vtable       {name}: {verdict}")
    conflicts = {k: v for k, v in checker.discovered.items() if len(v) > 1}
    for k, v in conflicts.items():
        print(f"conflict: {k} implied at {', '.join(f'{x:08x} (by {checker.witness[(k, x)]:08x})' for x in sorted(v))}")
    if args.cmd == "score":
        write_readme(s, results, retail)
        (BUILD / "discovered.json").write_text(json.dumps({k: sorted(f"{x:08x}" for x in v)
                                                            for k, v in sorted(checker.discovered.items())}, indent=1))
        # Symbol evidence for promotion retains every proven folded alias. This TSV is not the score: several
        # symbols may occupy one retail address, which unique_matches counts only once in the README/totals.
        matched = sorted((r for r in results if r.status == "match"),
                         key=lambda r: (r.address, r.source, r.symbol))
        demangled = demangle([r.symbol for r in matched])
        with (BUILD / "matched.tsv").open("w") as out:
            out.write("address\tbytes\ttableName\tsymbol\tdemangled\tsource\n")
            for r in matched:
                if r.address not in retail:  # matched but not a function in the retail table (no table name)
                    continue
                out.write(f"0x{r.address:08x}\t{retail[r.address].size}\t{retail[r.address].name}\t{r.symbol}\t"
                          f"{demangled.get(r.symbol, r.symbol)}\t{r.source}\n")


if __name__ == "__main__":
    main()
