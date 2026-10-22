"""equiv.py ADDR [--trials N] [--seed S] [--verbose]: behaviour test of one function against retail.

Builds the file that annotates ADDR, then runs retail's bytes at ADDR and our compiled section for that function in an
x86-32 emulator (unicorn: requirements.txt) on the same random inputs and compares what they do:
  - the ordered trace of calls leaving the function (target, ecx, the arguments the callee takes);
  - every memory write outside the stack, per stretch between two calls (a stretch's final bytes, so reordered stores
    that no call can observe do not count);
  - eax (unless the function returns void), the x87 depth at return and st0 when it returns a float, and ret n.
Game code the function calls is not executed: each call returns a value derived from (target, the k-th call to it)
through a stub that pops what the callee would. Library code (from GAME_END) and small game helpers (maths members,
accessors: see transparent()) run as retail's own bytes, so inlining differences do not count.
Unplaced callees resolve through their source annotation or, failing that, the function-name table's name.
Floats compare bit-exact. Both bodies execute at the retail virtual address, in separate emulator instances.
Prints bounded agreement over completed trials, the first difference, or INCONCLUSIVE for incomplete execution,
coverage or unsupported observations. Exit codes 0 / 1 / 2 are bounded agreement / difference / inconclusive.
Neither agreement nor block coverage proves equivalence for all inputs. Run from a checkout, with a Python that has
unicorn:
python3 tools/equiv.py 0x004f9490
"""
from __future__ import annotations

import argparse
import bisect
import contextlib
import csv
import hashlib
import io
import json
import os
import random
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decomp                                                   # noqa: E402
from binfmt import REL_DIR32, REL_DIR32NB, REL_REL32, SYM_EXTERNAL  # noqa: E402

try:
    from unicorn import Uc, UcError, UC_ARCH_X86, UC_MODE_32, UC_HOOK_BLOCK, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_UNMAPPED
    from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_EIP,
                                   UC_X86_REG_FPSW, UC_X86_REG_FPCW, UC_X86_REG_FP0, UC_X86_REG_GDTR, UC_X86_REG_FS,
                                   UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_FPTAG,
                                   UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
except ImportError:
    raise SystemExit("equiv.py needs unicorn: pip install -r requirements.txt (or run it with a Python that has it)")

# BEA_MAIN: the checkout whose build/matched.tsv carries the global symbol evidence (default this one).
MAIN = Path(os.environ.get("BEA_MAIN") or decomp.ROOT)
# BEA_NAME_TABLE: the function-name table unplaced callees fall back to (address/name TSV); default config/functions.tsv
# with its corrections.
NAME_TABLE = decomp.setting("BEA_NAME_TABLE", "NAME_TABLE")
NAME_TABLE = None if decomp.is_unset(NAME_TABLE) else NAME_TABLE
HEAP, HEAP_SIZE = 0x20000000, 0x400000
STACK, STACK_SIZE = 0x30000000, 0x100000
DATA = 0x61000000                                           # our object's other sections, when retail has no copy
STUBS = 0x7E000000                                          # return stubs: mov eax,[SLOT]; (fld [FSLOT]); ret n
SLOT, FSLOT = 0x7E0F0000, 0x7E0F0010
TRAPS = 0x7F000000                                          # one address per unresolved symbol
SENTINEL = 0x7D000000                                       # the return address the function is entered with
GDT = 0x7C000000
PAGE = 0x1000
MAX_STEPS = 100000                                          # basic blocks
TINY = 0x20                                                 # game functions this small run natively, see transparent()
MATHS = re.compile(r"^(FVector2?|FMatrix|CEulerAngles|FQuaternion|D3DXVECTOR\d|Vec[234]|Mat34|MathMatrix)(::|__)|"
                   r"^vector_(con|de)structor_iterator|^`vector (con|de)structor iterator'")


def page(a):
    return a & ~(PAGE - 1)


def mix(*parts) -> int:
    return int.from_bytes(hashlib.blake2b(repr(parts).encode(), digest_size=8).digest(), "little")


# ---------------------------------------------------------------------------------------------------------------------
# symbols: where our object's references land in retail
# ---------------------------------------------------------------------------------------------------------------------

class Resolver:
    def __init__(self, image, results, checker, stem: str, entry: int):
        self.image, self.stem = image, stem
        self.entry = entry
        self.by_symbol: dict[str, int] = {}
        with contextlib.suppress(FileNotFoundError):
            for k, v in json.load(open(MAIN / "build/discovered.json")).items():
                if len(v) == 1:
                    self.by_symbol[k] = int(v[0], 16)
        with contextlib.suppress(FileNotFoundError):
            for r in csv.DictReader(open(MAIN / "build/matched.tsv"), delimiter="\t"):
                self.by_symbol.setdefault(r["symbol"], int(r["address"], 16))
        for a in decomp.annotations():
            if a.symbol:
                self.by_symbol.setdefault(a.symbol, a.address)
        for k, v in checker.discovered.items():
            if len(v) == 1:
                self.by_symbol[k] = next(iter(v))
        for r in results:
            self.by_symbol[r.symbol] = r.address
        self.imports = {}
        for slot, name in image.imports.items():
            self.imports[re.sub(r"@\d+$", "", name.split("!")[-1]).lstrip("_")] = slot
        self.traps: dict[str, int] = {}
        self.names: dict[int, str] = {}                     # resolved address -> our symbol name
        self.qualified: dict[str, list] | None = None
        self.table_names: dict[str, set[int]] | None = None
        self.data = bytearray()                             # our constants retail has no copy of, mapped at DATA
        self.name_only: set[str] = set()

    def by_annotation(self, name: str) -> int | None:
        """An unmatched function's address from its source annotation: the demangled Class::Method with the same
        parameter count, when exactly one annotation has it."""
        if not name.startswith("?"):
            return None
        if self.qualified is None:
            self.qualified = {}
            for a in decomp.annotations():
                if a.qualified:
                    self.qualified.setdefault(a.qualified, []).append(a)
        text = decomp.demangle([name]).get(name)
        if not text:
            return None
        qual, n = decomp.qualified_of(name, {name: text}), decomp.demangled_params(text)
        cands = {a.address for a in self.qualified.get(qual, []) if a.params is None or n is None or a.params == n}
        return cands.pop() if len(cands) == 1 else None

    def by_table_name(self, name: str) -> int | None:
        """An unplaced function's address from the function-name table's name (Class__Method, Class__ctor, Class__dtor,
        Class__scalar_deleting_dtor), when exactly one function has it."""
        if self.table_names is None:
            self.table_names = {}
            if NAME_TABLE is not None:
                with contextlib.suppress(FileNotFoundError):
                    for r in csv.DictReader(open(NAME_TABLE), delimiter="\t"):
                        self.table_names.setdefault(r["name"], set()).add(int(r["address"], 16))
            else:
                for f in decomp.retail_functions().values():
                    self.table_names.setdefault(f.name, set()).add(f.address)
        g = re.match(r"\?\?_G(\w+)@@", name)
        text = decomp.demangle([name]).get(name) if name.startswith("?") and not g else None
        if not text and not g:
            return None
        qual = f"{g.group(1)}::scalar_deleting_dtor" if g else decomp.qualified_of(name, {name: text})
        parts = qual.split("::")
        if len(parts) < 2:
            return None
        last = parts[-1]
        if last == parts[-2]:
            last = "ctor"
        elif last == "~" + parts[-2]:
            last = "dtor"
        elif not re.fullmatch(r"\w+", last):
            return None
        cands = self.table_names.get("__".join(parts[:-1] + [last]), set())
        return next(iter(cands)) if len(cands) == 1 else None

    def find_bytes(self, want: bytes) -> int | None:
        for name, base, vsize, rptr, rsize in self.image.sections:
            if name in (".rdata", ".data"):
                i = self.image.data.find(want, rptr, rptr + rsize)
                if i >= 0:
                    return base + i - rptr
        return None

    def resolve(self, coff, sym, ours_secnum: int) -> tuple[int, bool]:
        """(address, resolved)"""
        name = sym.name
        if sym.storage == SYM_EXTERNAL and name in decomp.PROVEN_LIBRARY_SYMBOLS:
            # Proven identities also constrain same-section/absolute definitions;
            # a stale discovery or annotation cannot substitute another math routine.
            at = decomp.PROVEN_LIBRARY_SYMBOLS[name]
            self.names.setdefault(at, name)
            return at, True
        if sym.section == ours_secnum:
            return self.entry + sym.value, True
        if sym.section == -1:
            return sym.value, True
        if name.startswith("__imp_"):
            slot = self.imports.get(re.sub(r"@\d+$", "", name[len("__imp_"):]).lstrip("_"))
            if slot is not None:
                return slot, True
        if sym.section > 0 and name.startswith(("??_C@", "__real@")):
            raw = bytes(coff.sections[sym.section].data)
            at = self.find_bytes(raw)
            if at is None:                                  # a constant retail does not have: ours, at DATA
                self.data += b"\0" * (-len(self.data) % 16)
                at = DATA + len(self.data)
                self.data += raw
            return at + sym.value, True
        key = decomp.symbol_key(self.stem, name, sym.storage)
        for k in (key, name):
            if k in self.by_symbol:
                self.names.setdefault(self.by_symbol[k], name)
                return self.by_symbol[k], True
        at = self.by_annotation(name)
        if at is not None:
            self.names.setdefault(at, name)
            return at, True
        at = self.by_table_name(name)
        if at is not None:
            self.name_only.add(name)                         # a saved name is a lead, not address evidence
            self.names.setdefault(at, name)
            return at, True
        if name not in self.traps:
            self.traps[name] = TRAPS + 0x10 * len(self.traps)
            self.names[self.traps[name]] = name
        return self.traps[name], False


def mangled_return(symbol: str | None) -> str:
    """'f' float, 'd' double, 'v' void, 'p' pointer, 'i' scalar, '?' unknown (MSVC mangling)."""
    if not symbol or not symbol.startswith("?") or "@@" not in symbol:
        return "?"
    i = symbol.index("@@") + 2
    if i >= len(symbol):
        return "?"
    i += 2 if symbol[i] in "CDKLSTYZ" else 3               # static / global: access+cc; members: access+cv+cc
    c = symbol[i:i + 1]
    return {"M": "f", "N": "d", "X": "v", "P": "p", "Q": "p"}.get(c, "i")


# ---------------------------------------------------------------------------------------------------------------------
# call sites: what each callee pops, from the callee's ret n or from how the site builds its arguments
# ---------------------------------------------------------------------------------------------------------------------

INSN = re.compile(r"^\s*([0-9a-f]+):\s*(\S+)\s*(.*)$")


def listing(data: bytes, va: int) -> list[tuple[int, str, str]]:
    out = []
    for line in decomp.disassemble(data, va):
        m = INSN.match(line)
        if m:
            out.append((int(m.group(1), 16), m.group(2), m.group(3).split(";")[0].strip()))
    return out


def ret_n(image, retail: dict, target: int) -> int | None:
    f = retail.get(target)
    if f is None or not 0 < f.size < 0x4000:
        return None
    values = {int(ops, 16) if ops else 0
              for _a, mn, ops in listing(image.read(target, f.size) or b"", target) if mn == "ret"}
    return values.pop() if len(values) == 1 else None


X87_LOADS = ("fld", "fild", "fldz", "fld1", "fldpi", "fldl2e", "fldl2t", "fldlg2", "fldln2")
X87_CONTROL = ("fnstsw", "fstsw", "fldcw", "fnstcw", "fstcw", "fnclex", "fninit", "fwait", "fnop")


def returns_float(insns, k) -> bool:
    """Whether the code after the call at insns[k] takes a result from st0 (a virtual's type is unknown). VC6 leaves
    the x87 stack empty across a call, so the code's depth is tracked from zero: an instruction that needs more
    registers than it has loaded consumes the callee's float."""
    depth = 0
    for _a, mn, ops in insns[k + 1:k + 40]:
        if mn in ("call", "ret") or mn.startswith("j"):
            return False
        if not mn.startswith("f") or mn in X87_CONTROL:
            continue
        regs = [int(x) for x in re.findall(r"st\((\d)\)", ops)]
        need = max(regs, default=-1) + 1
        if mn in X87_LOADS:
            if need > depth:
                return True
            depth += 1
            continue
        pops = 2 if mn in ("fcompp", "fucompp") else 1 if mn.endswith("p") else 0
        need = max(need, 1, pops if mn not in ("fstp", "fistp", "fcomp", "fucomp", "fbstp") else 1)
        if mn.endswith("p") and "," in ops:
            need = max(need, 2)
        if need > depth:
            return True
        depth -= pops
    return False


def site_pops(insns) -> dict[int, tuple[int, int, bool]]:
    """return address -> (bytes the call pushed, bytes the caller removes itself afterwards, st0 used after)."""
    out, written = {}, set()
    callee_saved = ("ebx", "esi", "edi", "ebp")
    for k, (a, mn, ops) in enumerate(insns):
        dst = ops.split(",")[0].strip()
        if mn not in ("push", "cmp", "test") and dst in ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"):
            written.add(dst)
        if mn != "call":
            continue
        nxt = insns[k + 1] if k + 1 < len(insns) else None
        ret = nxt[0] if nxt else a + 5
        cleanup = int(nxt[2].split(",")[1], 16) if nxt and nxt[1] == "add" and nxt[2].startswith("esp,") else 0
        pushed, seen = 0, set()
        for j in range(k - 1, -1, -1):
            _b, m2, o2 = insns[j]
            if m2 in ("call", "ret") or m2.startswith("j") or (m2 == "add" and o2.startswith("esp,")):
                break
            if m2 == "push":
                reg = o2.strip()
                before = {x for (_c, mm, oo) in insns[:j] for x in [oo.split(",")[0].strip()]
                          if mm not in ("push", "cmp", "test")}
                if reg in callee_saved and reg not in before:
                    break                                   # the prologue saving a register it has not written yet
                pushed += 4
            elif m2 == "sub" and o2.startswith("esp,"):
                if not any(mm == "push" and oo.strip() not in callee_saved for (_c, mm, oo) in insns[:j]) and \
                        not any(mm == "call" for (_c, mm, oo) in insns[:j]):
                    break                                   # the frame
                pushed += int(o2.split(",")[1], 16)
            elif m2 == "pop":
                pushed -= 4
        out[ret] = (max(pushed, 0), cleanup, returns_float(insns, k))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------------------------------------------------

SIZES = {"FVector": 16, "FMatrix": 48, "CEulerAngles": 16, "D3DXVECTOR4": 16, "FVector2": 8}


def params(demangled: str | None) -> tuple[bool, list[tuple[str, int]]]:
    """(thiscall, [(kind, bytes)]) with kind 'p' pointer, 'f' float, 'd' double, 'i' integer, 's' struct."""
    if not demangled or "(" not in demangled:
        raise ValueError("unresolved entry signature")
    if "__fastcall" in demangled or "..." in demangled:
        raise ValueError("fastcall/variadic entry ABI is not modeled")
    prefix = demangled.split("__", 1)[0]
    if re.search(r"\b(class|struct|union|__int64)\b", prefix) or "__int64" in demangled:
        raise ValueError("aggregate/64-bit return or argument ABI is not modeled")
    this = "__thiscall" in demangled
    inside = demangled[demangled.rindex("(") + 1:demangled.rindex(")")]
    parts, depth, cur = [], 0, ""
    for ch in inside:
        depth += ch == "<"
        depth -= ch == ">"
        if ch == "," and not depth:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip() and cur.strip() != "void":
        parts.append(cur.strip())
    out = []
    for p in parts:
        if "*" in p or "&" in p:
            out.append(("p", 4))
        elif p == "float":
            out.append(("f", 4))
        elif p == "double":
            out.append(("d", 8))
        elif p.startswith(("class ", "struct ", "union ")):
            name = p.split()[-1]
            if name not in SIZES:
                raise ValueError(f"unmodeled by-value type {name}")
            out.append(("s", SIZES[name]))
        else:
            out.append(("i", 4))
    return this, out


FLOATS: list[float] = []                                      # float constants the function loads or compares with


NEAR = ("c", "c", "up", "down", "neg", 0.25, -0.25, 1.0, -1.0, 0.01, -0.01)


def near_constant(pick: float, how) -> float:
    """A float at a boundary the function compares with: the constant, its neighbours either side, its negation, or
    a small step away. A changed boundary shows when only one build's branch flips."""
    c = FLOATS[int(pick * len(FLOATS)) % len(FLOATS)]
    if how == "c":
        return c
    if how in ("up", "down"):
        return next_float(c, how == "up")
    if how == "neg":
        return -c
    return c + how


def rand_float(rng) -> float:
    r = rng.random()
    if FLOATS and r < 0.25:
        return near_constant(rng.random(), rng.choice(NEAR))
    r = rng.random()
    if r < 0.15:
        return rng.choice([0.0, 1.0, -1.0, 0.5])
    return rng.uniform(-200.0, 200.0) if r < 0.8 else rng.uniform(-2.0, 2.0)


INTERESTING: list[int] = []                                   # immediates from the function's own compares and masks
FOCUS: list[int] = []                                         # this trial's constant, planted often
FLOATY: list[bool] = [False]                                  # this trial fills memory mostly with floats


def rand_dword(rng) -> int:
    r = rng.random()
    if FLOATY[0] and r < 0.6:
        return struct.unpack("<I", struct.pack("<f", rand_float(rng)))[0]
    if FOCUS and r < 0.12:
        return FOCUS[0]
    if r < 0.30:
        return 0
    if r < 0.40 and INTERESTING:
        return rng.choice(INTERESTING)
    if r < 0.52:
        return rng.choice([1, 2, 3, 4, 5, 7, 10, 0xFFFFFFFF])
    if r < 0.78:
        return HEAP + (rng.randrange(HEAP_SIZE // 16 - 64) * 16)
    return struct.unpack("<I", struct.pack("<f", rand_float(rng)))[0]


def harvest(*listings) -> list[int]:
    out = set()
    for insns in listings:
        for _a, mn, ops in insns:
            if mn in ("cmp", "test", "and", "sub", "push", "mov") and "," in ops or mn == "push":
                for m in re.finditer(r"0x([0-9a-f]+)$", ops):
                    v = int(m.group(1), 16)
                    if 0 < v < 0x400000 or v >= 0xFFFFF000:
                        out.update({v, (v - 1) & 0xFFFFFFFF, (v + 1) & 0xFFFFFFFF})
    return sorted(out)


def float_constants(read, *listings) -> list[float]:
    """The finite float and double constants both builds' code reads (fld/fcomp/fmul ... PTR ds:0x...)."""
    out = set()
    for insns in listings:
        for _a, mn, ops in insns:
            m = re.search(r"(DWORD|QWORD) PTR ds:0x([0-9a-f]+)", ops)
            if mn.startswith("f") and m:
                n = 4 if m.group(1) == "DWORD" else 8
                raw = read(int(m.group(2), 16), n)
                if raw and len(raw) == n:
                    v = struct.unpack("<f" if n == 4 else "<d", raw)[0]
                    if v == v and abs(v) < 1e7:
                        out.add(struct.unpack("<f", struct.pack("<f", v))[0])
    return sorted(out)


def next_float(v: float, up: bool) -> float:
    """The neighbouring single-precision value."""
    if v == 0:
        return struct.unpack("<f", struct.pack("<I", 1))[0] * (1 if up else -1)
    bits = struct.unpack("<I", struct.pack("<f", v))[0]
    bits += 1 if (v > 0) == up else -1
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def block_leaders(insns, lo: int, size: int) -> list[int]:
    """Where retail's basic blocks start: the entry, every branch target inside it, whatever follows a branch."""
    out = {lo}
    for k, (a, mn, ops) in enumerate(insns):
        if mn.startswith("j") or mn in ("ret", "call"):
            m = re.fullmatch(r"0x([0-9a-f]+)", ops)
            if m and mn != "call" and lo <= int(m.group(1), 16) < lo + size:
                out.add(int(m.group(1), 16))
            if k + 1 < len(insns) and mn != "call":
                out.add(insns[k + 1][0])
    return sorted(out)


def fill(rng, size: int) -> bytes:
    return b"".join(struct.pack("<I", rand_dword(rng)) for _ in range(size // 4))


def overlay_issue(image, entry: int, extent: int, candidate: bytes) -> str | None:
    """Only the admitted function body may change. Padding outside it must remain byte-identical.

    Running at the same address avoids treating a virtual self-call as a stub in one run, or executing a random
    indirect target that happens to equal the candidate's former synthetic base in the other run. A larger body
    needs a separate address-space model; silently overwriting the next function or its data would be unsound.
    """
    if not candidate or extent <= 0 or image.read(entry, len(candidate)) is None:
        return "candidate lies outside the admitted image"
    if len(candidate) > extent and candidate[extent:] != image.read(entry + extent, len(candidate) - extent):
        return "candidate changes bytes beyond the admitted retail function extent"
    return None


def outcome(agreed: int, incomplete: int, missed: list[int], unresolved: list[str]) -> int:
    """A successful process means completed, observable sampled runs, never general equivalence."""
    return 0 if agreed and not incomplete and not missed and not unresolved else 2


def scalar_return(h: int, kind: str) -> int:
    """Exercise flags/enums as well as pointers. The old all-aligned-pointer stream could never return TRUE=1."""
    ptr = HEAP + (h >> 8) % (HEAP_SIZE // 16 - 64) * 16
    if kind == "p":
        return 0 if h % 7 == 0 else ptr
    choices = (0, 1, 0xFFFFFFFF, 2, 3, 7, 0x80000000, ptr)
    return choices[h % len(choices)]


# ---------------------------------------------------------------------------------------------------------------------
# one run
# ---------------------------------------------------------------------------------------------------------------------

def run(image, code_va: int, code_len: int, ours: bytes | None, trial: int, args: bytes, this: int | None,
        sites: dict, pops_of, returns_of, image_pages: list, heap: bytes, lib_lo: int, lib_hi: int, native,
        max_steps: int = MAX_STEPS):
    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    for base, blob in image_pages:
        uc.mem_map(base, len(blob))
        uc.mem_write(base, blob)
    uc.mem_map(HEAP, HEAP_SIZE)
    uc.mem_write(HEAP, heap)
    uc.mem_map(STACK, STACK_SIZE)
    uc.mem_write(STACK, b"\xCC" * STACK_SIZE)
    for base in (STUBS, TRAPS, SENTINEL):
        uc.mem_map(base, 0x100000)
    if ours is not None:
        uc.mem_write(code_va, ours)                          # replace this function in this run only
    stubs = {}
    blob = b""
    for n in range(0, 0x44, 4):
        for fl in ("i", "f", "d"):
            stubs[(n, fl)] = STUBS + len(blob)
            s = b"\xA1" + struct.pack("<I", SLOT)                                       # mov eax,[SLOT]
            if fl == "f":
                s += b"\xD9\x05" + struct.pack("<I", FSLOT)                             # fld dword [FSLOT]
            if fl == "d":
                s += b"\xDD\x05" + struct.pack("<I", FSLOT)                             # fld qword [FSLOT]
            s += (b"\xC2" + struct.pack("<H", n)) if n else b"\xC3"
            blob += s
    uc.mem_write(STUBS, blob)
    # segments: flat 32-bit code, data and stack; fs a small data segment whose base holds the exception list head
    uc.mem_map(GDT, PAGE * 2)
    fs_base = GDT + PAGE

    def descriptor(base, limit, access, flags):
        return ((limit & 0xFFFF) | ((base & 0xFFFFFF) << 16) | (access << 40) | (((limit >> 16) & 0xF) << 48)
                | (flags << 52) | ((base >> 24) << 56))
    gdt = [0, descriptor(0, 0xFFFFF, 0x9A, 0xC), descriptor(0, 0xFFFFF, 0x92, 0xC), descriptor(fs_base, 0xFFF, 0x92, 0x4)]
    uc.mem_write(GDT, b"".join(struct.pack("<Q", d) for d in gdt))
    uc.reg_write(UC_X86_REG_GDTR, (0, GDT, len(gdt) * 8 - 1, 0x0))
    uc.reg_write(UC_X86_REG_DS, 2 << 3)
    uc.reg_write(UC_X86_REG_ES, 2 << 3)
    uc.reg_write(UC_X86_REG_SS, 2 << 3)
    uc.reg_write(UC_X86_REG_FS, 3 << 3)
    uc.mem_write(fs_base, struct.pack("<I", 0xFFFFFFFF))

    esp0 = STACK + STACK_SIZE - 0x8000
    frame = struct.pack("<I", SENTINEL) + args
    uc.mem_write(esp0, frame)
    uc.reg_write(UC_X86_REG_ESP, esp0)
    if this is not None:
        uc.reg_write(UC_X86_REG_ECX, this)
    uc.reg_write(UC_X86_REG_FPCW, 0x027F)
    saved_regs = (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)
    for i, reg in enumerate(saved_regs):
        uc.reg_write(reg, 0x10203040 + i * 0x01010101)

    trace, writes, segment = [], [{}], [0]
    counts: dict[int, int] = {}
    steps = [0]
    fault = [None]
    unsupported: set[str] = set()

    def stack_token(v):
        if STACK <= v < STACK + STACK_SIZE:
            # Pointee sizes/lifetimes are not admitted. Erasing the pointer identity would hide different values
            # and alias patterns; retain it for diagnostics, and withhold an agreement verdict for this trial.
            unsupported.add("stack-backed external-call argument is not modeled")
            return ("stack", v - esp0)
        return v

    covered = []

    def on_code(uc_, addr, size, _u):
        steps[0] += 1
        if steps[0] > max_steps:
            fault[0] = "steps"
            uc_.emu_stop()
            return
        if code_va <= addr < code_va + code_len:
            covered.append((addr, size))
            return
        if lib_lo <= addr < lib_hi or STUBS <= addr < STUBS + 0x100000:
            return
        if addr == SENTINEL or native(addr):
            return
        if TRAPS <= addr < TRAPS + 0x100000:
            unsupported.add("unresolved external call")
        esp = uc_.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack("<I", uc_.mem_read(esp, 4))[0]
        inside = code_va <= ret < code_va + code_len
        pushed, cleanup, st0 = sites.get(ret, (0, 0, False)) if inside else (0, 0, False)
        n = pops_of(addr)
        if n is None:
            unsupported.add("external-call stack cleanup is inferred, not admitted")
            n = 0 if cleanup else pushed
        if n > 0x40 or n % 4:
            unsupported.add("external-call stack cleanup exceeds the stub model")
        if n == 0 and cleanup == 0 and pushed:
            unsupported.add("delayed cdecl argument cleanup is not modeled")
        take = max(n, cleanup, 0)
        argv = [stack_token(x) for x in struct.unpack(f"<{take // 4}I", bytes(uc_.mem_read(esp + 4, take)))] \
            if take else []
        k = counts.get(addr, 0)
        counts[addr] = k + 1
        fl = returns_of(addr)
        if fl == "?":
            fl = "f" if st0 else "i"
        trace.append((addr, stack_token(uc_.reg_read(UC_X86_REG_ECX)), tuple(argv), fl))
        writes.append({})
        segment[0] += 1
        h = mix(trial, addr, k)
        # Unknown virtual returns may be either scalars or pointers; both are sampled, without claiming a valid
        # object graph. Invalid dereferences are inconclusive through on_unmapped, never repaired into a PASS.
        val = scalar_return(h, fl)
        uc_.mem_write(SLOT, struct.pack("<I", val))
        mode = (h >> 12) % 10
        if mode < 4 or not FLOATS and mode >= 7:
            f = ((h >> 20) % 4001 - 2000) / 10.0
        elif mode < 7:
            f = ((h >> 20) % 801 - 400) / 100.0
        else:
            f = near_constant(((h >> 20) % 1000) / 1000.0, NEAR[(h >> 40) % len(NEAR)])
        uc_.mem_write(FSLOT, struct.pack("<d", f) if fl == "d" else struct.pack("<f", f) + b"\0" * 4)
        uc_.reg_write(UC_X86_REG_EIP, stubs[(min(n, 0x40), fl if fl in ("f", "d") else "i")])

    def on_write(uc_, _acc, addr, size, value, _u):
        if STACK <= addr < STACK + STACK_SIZE or SLOT <= addr < SLOT + 0x20:
            return
        seg = writes[-1]
        for i in range(size):
            seg[addr + i] = (value >> (8 * i)) & 0xFF

    def on_unmapped(uc_, _acc, addr, size, _value, _u):
        unsupported.add("execution required synthetic unmapped memory")
        base = page(addr)
        r = random.Random(mix("page", trial, base))
        try:
            uc_.mem_map(base, PAGE)
            uc_.mem_write(base, fill(r, PAGE))
            if page(addr + size - 1) != base:
                uc_.mem_map(base + PAGE, PAGE)
                uc_.mem_write(base + PAGE, fill(r, PAGE))
        except UcError:
            return False
        return True

    uc.hook_add(UC_HOOK_BLOCK, on_code)
    uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
    uc.hook_add(UC_HOOK_MEM_UNMAPPED, on_unmapped)
    try:
        uc.emu_start(code_va, SENTINEL)
    except UcError as e:
        fault[0] = f"fault {e} at {uc.reg_read(UC_X86_REG_EIP) - code_va:+#x}" \
            if code_va <= uc.reg_read(UC_X86_REG_EIP) < code_va + code_len else f"fault {e}"
    fpsw = uc.reg_read(UC_X86_REG_FPSW)
    fp0 = uc.reg_read(UC_X86_REG_FP0 + ((fpsw >> 11) & 7))  # FP0..7 are the physical registers; st0 is the top one
    return {"trace": trace, "writes": [{k: v for k, v in w.items()} for w in writes], "eax": uc.reg_read(UC_X86_REG_EAX),
            "top": (fpsw >> 11) & 7, "st0": fp0, "esp": uc.reg_read(UC_X86_REG_ESP) - esp0, "fault": fault[0],
            "tags": uc.reg_read(UC_X86_REG_FPTAG),
            "preserved": tuple(uc.reg_read(reg) for reg in saved_regs), "control": uc.reg_read(UC_X86_REG_FPCW),
            "steps": steps[0], "covered": covered, "unsupported": sorted(unsupported)}


# ---------------------------------------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("address")
    ap.add_argument("--trials", type=int, default=128)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--file", help="the source to build (default: the file that annotates ADDRESS)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--only", type=int, help="run just this trial")
    ap.add_argument("--extend", type=int, default=4,
                    help="keep going up to this many times --trials while some of retail's blocks are unreached")
    ap.add_argument("--steps", type=int, default=MAX_STEPS, help="basic blocks per run before a trial is skipped")
    a = ap.parse_args()
    if a.trials <= 0 or a.extend <= 0 or a.steps <= 0 or (a.only is not None and a.only < 0):
        ap.error("trial, extension and step limits must be positive; --only must be nonnegative")
    addr = int(a.address, 16)
    if a.file:
        src = Path(a.file).resolve()
    else:
        tag = f"function: 0x{addr:08x}"
        found = [s for s in decomp.sources() if tag in s.read_text(errors="replace").lower()]
        if not found:
            raise SystemExit(f"no source annotates 0x{addr:08x}")
        src = found[0]
    with contextlib.redirect_stdout(io.StringIO()):
        objects = decomp.build([src])
        results, checker = decomp.check(objects)
    r = next((x for x in results if x.address == addr), None)
    if r is None or r.status == "unplaced":
        print(f"0x{addr:08x}: not placed in {src.name}")
        sys.exit(2)
    obj = next(o for s, o in objects.items() if str(s.relative_to(decomp.ROOT)) == r.source)
    coff = decomp.parse_coff(obj)
    secnum = next(n for n, s in decomp.function_sections(coff) if s == r.symbol)
    sec = coff.sections[secnum]
    image = checker.image
    retail = checker.retail
    rsize = retail[addr].size if addr in retail else r.size
    res = Resolver(image, results, checker, obj.stem, addr)

    # relocate our section
    ours = bytearray(sec.data)
    unresolved, unresolved_data = [], []
    for off, symidx, typ in sec.relocs:
        sym = coff.symbols[symidx]
        target, ok = res.resolve(coff, sym, secnum)
        if not ok:
            unresolved.append(sym.name)
            if sym.type != 0x20:                            # not a function: ours reads a trap page, retail real data
                unresolved_data.append(sym.name)
        addend = int.from_bytes(ours[off:off + 4], "little")
        if typ == REL_DIR32:
            v = (target + addend) & 0xFFFFFFFF
        elif typ == REL_DIR32NB:
            v = (target + addend - image.image_base) & 0xFFFFFFFF
        elif typ == REL_REL32:
            v = (target + addend - (addr + off + 4)) & 0xFFFFFFFF
        else:
            print(f"0x{addr:08x}: INCONCLUSIVE: unsupported relocation type {typ}")
            sys.exit(2)
        ours[off:off + 4] = struct.pack("<I", v)
    ours = bytes(ours)
    assumed = [f"table-name-only: {name}" for name in sorted(res.name_only)]
    unresolved.extend(assumed)
    unresolved_data.extend(assumed)                          # differences under a guessed address are inconclusive too
    issue = overlay_issue(image, addr, rsize, ours)
    if issue:
        print(f"0x{addr:08x}: INCONCLUSIVE: {issue} (candidate {len(ours)}, retail body {rsize} bytes)")
        sys.exit(2)

    # memory: the image as loaded
    image_pages = []
    lo = image.image_base
    hi = max(b + max(vs, rs) for _n, b, vs, _rp, rs in image.sections)
    blob = bytearray((hi - lo + PAGE - 1) & ~(PAGE - 1))
    blob[0:0x1000] = image.data[:0x1000]
    for _n, b, vs, rp, rs in image.sections:
        raw = image.data[rp:rp + min(rs, max(vs, rs))]
        blob[b - lo:b - lo + len(raw)] = raw
    image_pages.append((lo, bytes(blob)))
    if res.data:
        image_pages.append((DATA, bytes(res.data) + b"\0" * (-len(res.data) % PAGE)))

    def read(a, n):
        if DATA <= a < DATA + len(res.data):
            return bytes(res.data[a - DATA:a - DATA + n])
        return image.read(a, n)

    retail_bytes = image.read(addr, rsize)
    ours_list, retail_list = listing(ours, addr), listing(retail_bytes, addr)
    ours_sites, retail_sites = site_pops(ours_list), site_pops(retail_list)
    INTERESTING[:] = harvest(ours_list, retail_list)
    FLOATS[:] = float_constants(read, retail_list, ours_list)
    names = res.names
    pops_cache: dict[int, int | None] = {}

    def pops_of(target):
        if target not in pops_cache:
            pops_cache[target] = ret_n(image, retail, target) if target < decomp.GAME_END else None
        return pops_cache[target]

    def returns_of(target):
        return mangled_return(names.get(target))

    # inline helpers run as retail's own bytes, so a helper one build inlines and the other calls is not a difference
    # in behaviour. A helper is an inline function (a COMDAT our object defines; without /Gy only inline functions
    # and templates are COMDATs), a maths member or vector_constructor_iterator by name (ours, or the function-name
    # table's), or anything of at most TINY bytes, and every direct call it makes is library code or another
    # helper; what it calls indirectly (a virtual, a constructor passed to an iterator) goes through the hook as
    # usual. Ordinary game functions stay stubs: running them natively on fixed image data would feed the function
    # the same value in every trial.
    inline_syms = {s for n, s in decomp.function_sections(coff) if coff.sections[n].comdat and n != secnum}
    inline_at = {res.by_symbol[s] for s in inline_syms if s in res.by_symbol}
    if res.table_names is None:
        res.by_table_name("?x@y@@QAEXXZ")                   # loads the table
    table_name = {a: n for n, addrs in res.table_names.items() for a in addrs}
    demangled_names = decomp.demangle(list(set(names.values())))
    starts = sorted(retail)
    helper: dict[int, bool] = {}
    at: dict[int, bool] = {}

    def is_inline(fn, size):
        if fn in inline_at or size <= TINY:
            return True
        ours_name = names.get(fn)
        text = demangled_names.get(ours_name, ours_name) if ours_name else ""
        qual = text.split("(")[0].split(" ")[-1] if text else ""
        return bool(MATHS.search(qual) or MATHS.search(table_name.get(fn, "")))

    def transparent(fn):
        if fn in helper:
            return helper[fn]
        helper[fn] = False                                   # a recursive helper is not one
        f = retail.get(fn)
        ok = f is not None and fn < decomp.GAME_END and fn != addr and 0 < f.size and is_inline(fn, f.size)
        if ok:
            for _a, mn, ops in listing(image.read(fn, f.size) or b"", fn):
                if mn == "call" and re.fullmatch(r"0x[0-9a-f]+", ops):
                    t = int(ops, 16)
                    if not (decomp.GAME_END <= t < decomp.FUNCLETS or transparent(t)):
                        ok = False
                        break
        helper[fn] = ok
        return ok

    def native(a):
        if a not in at:
            i = bisect.bisect_right(starts, a) - 1
            fn = starts[i] if i >= 0 else None
            at[a] = fn is not None and fn <= a < fn + retail[fn].size and transparent(fn)
        return at[a]

    demangled = decomp.demangle([r.symbol]).get(r.symbol)
    try:
        thiscall, plist = params(demangled)
    except ValueError as error:
        print(f"0x{addr:08x}: INCONCLUSIVE: {error}")
        sys.exit(2)
    rtype = mangled_return(r.symbol)

    leaders = block_leaders(retail_list, addr, rsize)
    reached: set[int] = set()
    failures = 0
    skipped = 0
    faulted = 0                                             # at least one run did not return normally
    ran = 0
    agreed = 0
    unobserved = 0
    limits: set[str] = set()
    for t in ([a.only] if a.only is not None else range(a.trials * a.extend)):
        if t >= a.trials and set(leaders) <= reached:
            break                                           # every block reached: no need for the extra trials
        ran += 1
        seed = a.seed * 100003 + t
        rng = random.Random(seed)
        FOCUS[:] = [INTERESTING[t % len(INTERESTING)]] if INTERESTING and t % 2 else []
        FLOATY[0] = t % 4 == 2                              # float fields that feed an idiv or a loop bound
        heap = fill(rng, HEAP_SIZE)
        this = HEAP + rng.randrange(HEAP_SIZE // 16 - 256) * 16 if thiscall else None
        args = b""
        for kind, size in plist:
            if kind == "p":
                args += struct.pack("<I", HEAP + rng.randrange(HEAP_SIZE // 16 - 256) * 16)
            elif kind == "f":
                args += struct.pack("<f", rand_float(rng))
            elif kind == "d":
                args += struct.pack("<d", rand_float(rng))
            elif kind == "s":
                args += b"".join(struct.pack("<f", rand_float(rng)) for _ in range(size // 4))
            else:
                args += struct.pack("<I", rng.choice([0, 1, 2, 3, 4, 5, 7, 10, 0xFFFFFFFF, rng.getrandbits(8)]))
        args += b"\xCC" * 32
        lib = (decomp.GAME_END, decomp.FUNCLETS)
        if a.verbose:
            import time
            t0 = time.time()
        want = run(image, addr, rsize, None, t, args, this, retail_sites, pops_of, returns_of, image_pages, heap, *lib,
                   native, a.steps)
        got = run(image, addr, len(ours), ours, t, args, this, ours_sites, pops_of, returns_of, image_pages, heap, *lib,
                  native, a.steps)
        if a.verbose:
            print(f"  trial {t}: {time.time() - t0:.1f}s, steps retail {want['steps']} ours {got['steps']}, "
                  f"faults {want['fault']} / {got['fault']}", flush=True)
        for b, n in want["covered"]:
            reached.update(x for x in leaders if b <= x < b + n)
        if want["fault"] is not None or got["fault"] is not None:
            if want["fault"] == "steps" or got["fault"] == "steps":
                skipped += 1
            else:
                faulted += 1
            limits.add(f"non-returning trial: retail {want['fault']}, candidate {got['fault']}")
            continue
        unsupported = set(want["unsupported"]) | set(got["unsupported"])
        if unsupported:
            unobserved += 1
            limits.update(unsupported)
            if a.verbose:
                print(f"  trial {t}: INCONCLUSIVE: {', '.join(sorted(unsupported))}", flush=True)
            continue
        why, trapped = diverge(want, got, rtype, names)
        if why and not trapped and unresolved_data:
            trapped = sorted(set(unresolved_data))[0]
        if why:
            failures += 1
            verdict = f"INCONCLUSIVE (unresolved {trapped})" if trapped else "DIVERGES"
            print(f"0x{addr:08x}: {verdict} in trial {t} (seed {seed}): {why}")
            if a.verbose:
                print("  retail:", summary(want, names))
                print("  ours:  ", summary(got, names))
            if unresolved:
                print("  unresolved symbols (trapped):", ", ".join(sorted(set(unresolved))))
            sys.exit(2 if trapped else 1)
        agreed += 1
    incomplete = skipped + faulted + unobserved
    note = ", ".join(x for x in (f"{faulted} faulting" if faulted else "",
                                 f"{skipped} step-limited" if skipped else "",
                                 f"{unobserved} unsupported observations" if unobserved else "") if x)
    note = f" ({note})" if note else ""
    extra = f"; unresolved (trapped): {', '.join(sorted(set(unresolved)))}" if unresolved else ""
    missed = sorted(set(leaders) - reached)
    cover = f"; reached {len(leaders) - len(missed)}/{len(leaders)} of retail's blocks" + \
        (f" (never: {', '.join(f'{x:08x}' for x in missed[:8])}{' ...' if len(missed) > 8 else ''})" if missed else "")
    status = outcome(agreed, incomplete, missed, unresolved)
    verdict = "INCONCLUSIVE" if status else "NO DIFFERENCE OBSERVED (bounded stub model)"
    print(f"0x{addr:08x} {r.symbol}: {verdict}; {agreed}/{ran} completed observable trials agree{note}{cover}{extra}")
    if limits:
        print("  limits:", "; ".join(sorted(limits)))
    sys.exit(status)


def label(a, names):
    return names.get(a, f"{a:08x}")


def summary(run_, names):
    return {"calls": [(label(c[0], names), c[1], c[2]) for c in run_["trace"]], "eax": hex(run_["eax"]),
            "top": run_["top"], "st0": run_["st0"], "esp": run_["esp"], "fault": run_["fault"]}


def diverge(want, got, rtype, names) -> tuple[str | None, str | None]:
    """(the first difference, the unresolved symbol it involves) or (None, None)."""
    why = first_difference(want, got, rtype, names)
    if why is None:
        return None, None
    for w, g in zip(want["trace"], got["trace"]):
        if w[0] != g[0]:
            trap = next((x for x in (g[0], w[0]) if TRAPS <= x < TRAPS + 0x100000), None)
            return why, label(trap, names) if trap is not None else None
    return why, None


def first_difference(want, got, rtype, names) -> str | None:
    if want["fault"] != got["fault"]:
        return f"fault: retail {want['fault']}, ours {got['fault']}"
    for i, (w, g) in enumerate(zip(want["trace"], got["trace"])):
        if w[0] != g[0]:
            return f"call {i}: retail calls {label(w[0], names)}, ours {label(g[0], names)}"
        if w[1] != g[1]:
            return f"call {i} ({label(w[0], names)}): ecx retail {w[1]}, ours {g[1]}"
        if w[2] != g[2]:
            return f"call {i} ({label(w[0], names)}): arguments retail {w[2]}, ours {g[2]}"
        if w[3] != g[3]:
            return f"call {i} ({label(w[0], names)}): return model retail {w[3]}, ours {g[3]}"
    if len(want["trace"]) != len(got["trace"]):
        return f"call count: retail {len(want['trace'])}, ours {len(got['trace'])}"
    for i, (w, g) in enumerate(zip(want["writes"], got["writes"])):
        if w != g:
            keys = sorted(set(w) ^ set(g) | {k for k in set(w) & set(g) if w[k] != g[k]})
            k = keys[0]
            return (f"memory written after call {i} differs at {k:08x} (retail {w.get(k)}, ours {g.get(k)}; "
                    f"{len(keys)} bytes)")
    if want["fault"] is not None:
        return None
    if want["preserved"] != got["preserved"]:
        return f"callee-saved registers differ: retail {want['preserved']}, ours {got['preserved']}"
    if want["control"] != got["control"]:
        return f"x87 control word differs: retail {want['control']:#x}, ours {got['control']:#x}"
    if rtype != "v" and rtype not in ("f", "d") and want["eax"] != got["eax"]:
        return f"eax: retail {want['eax']:#x}, ours {got['eax']:#x}"
    if want["top"] != got["top"]:
        return f"x87 depth at return: retail top {want['top']}, ours {got['top']}"
    if want["tags"] != got["tags"]:
        return f"x87 occupied registers at return: retail {want['tags']:#x}, ours {got['tags']:#x}"
    if rtype in ("f", "d") and want["st0"] != got["st0"]:
        return f"st0 at return: retail {want['st0']}, ours {got['st0']}"
    if want["esp"] != got["esp"]:
        return f"stack popped at return: retail {want['esp']}, ours {got['esp']}"
    return None


if __name__ == "__main__":
    main()
