"""PE image and COFF object readers for the matching harness (i386 only)."""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path

SCN_CNT_CODE = 0x20
SCN_LNK_COMDAT = 0x1000
SYM_EXTERNAL, SYM_STATIC, SYM_LABEL, SYM_FUNCTION, SYM_WEAK = 2, 3, 6, 101, 105
REL_DIR32, REL_DIR32NB, REL_SECTION, REL_SECREL, REL_REL32 = 0x06, 0x07, 0x0A, 0x0B, 0x14
REL_WIDTH = {0x06: 4, 0x07: 4, 0x0A: 2, 0x0B: 4, 0x14: 4}


class PeImage:
    """A read-only view of a PE image: sections, virtual-address reads and the import table."""

    def __init__(self, path: Path, sha256: str | None = None) -> None:
        self.data = path.read_bytes()
        if sha256 is not None and hashlib.sha256(self.data).hexdigest() != sha256:
            raise SystemExit(f"{path}: SHA-256 differs from the pinned specimen")
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        nsec = struct.unpack_from("<H", self.data, pe + 6)[0]
        optsize = struct.unpack_from("<H", self.data, pe + 20)[0]
        self.image_base = struct.unpack_from("<I", self.data, pe + 52)[0]
        self.sections = []
        for i in range(nsec):
            o = pe + 24 + optsize + 40 * i
            name = self.data[o:o + 8].rstrip(b"\0").decode("latin-1")
            vsize, rva, rsize, rptr = struct.unpack_from("<IIII", self.data, o + 8)
            self.sections.append((name, self.image_base + rva, vsize, rptr, rsize))
        imp_rva = struct.unpack_from("<I", self.data, pe + 24 + 104)[0]
        self.imports = self._imports(imp_rva) if imp_rva else {}

    def offset(self, va: int) -> int | None:
        for _name, base, vsize, rptr, rsize in self.sections:
            if base <= va < base + max(vsize, rsize):
                return rptr + va - base if va - base < rsize else None
        return None

    def read(self, va: int, n: int) -> bytes | None:
        """Bytes as loaded: a section's tail beyond its raw data is zero-filled (the linker stores no trailing
        zero bytes, so a zero-valued literal such as "" can live there)."""
        for _name, base, vsize, rptr, rsize in self.sections:
            if base <= va and va + n <= base + max(vsize, rsize):
                start = va - base
                raw = self.data[rptr + start:rptr + min(start + n, rsize)] if start < rsize else b""
                return raw + b"\0" * (n - len(raw))
        return None

    def u32(self, va: int) -> int | None:
        b = self.read(va, 4)
        return None if b is None else struct.unpack("<I", b)[0]

    def cstr(self, va: int, limit: int = 4096) -> bytes | None:
        o = self.offset(va)
        if o is None:
            return b"\0" if self.read(va, 1) == b"\0" else None
        end = self.data.find(b"\0", o, o + limit)
        return None if end < 0 else self.data[o:end + 1]

    def _imports(self, rva: int) -> dict[int, str]:
        """IAT slot address -> 'dll!name' (or 'dll!#ordinal')."""
        out, d = {}, self.image_base + rva
        while True:
            ilt, _ts, _fw, name_rva, iat = struct.unpack("<IIIII", self.read(d, 20))
            if not name_rva:
                return out
            dll = self.cstr(self.image_base + name_rva).rstrip(b"\0").decode("latin-1")
            k = 0
            while True:
                entry = self.u32(self.image_base + (ilt or iat) + 4 * k)
                if not entry:
                    break
                if entry & 0x80000000:
                    label = f"#{entry & 0xFFFF}"
                else:
                    label = self.cstr(self.image_base + entry + 2).rstrip(b"\0").decode("latin-1")
                out[self.image_base + iat + 4 * k] = f"{dll}!{label}"
                k += 1
            d += 20


@dataclass
class Symbol:
    index: int
    name: str
    value: int
    section: int        # 1-based; 0 undefined, -1 absolute, -2 debug
    type: int
    storage: int
    aux: bytes


@dataclass
class Section:
    index: int
    name: str
    chars: int
    data: bytes
    relocs: list[tuple[int, int, int]] = field(default_factory=list)    # (offset, symbol index, type)

    @property
    def code(self) -> bool:
        return bool(self.chars & SCN_CNT_CODE)

    @property
    def comdat(self) -> bool:
        return bool(self.chars & SCN_LNK_COMDAT)

    @property
    def align(self) -> int:
        a = (self.chars >> 20) & 0xF
        return 1 << (a - 1) if a else 16


@dataclass
class Coff:
    path: Path
    sections: dict[int, Section]
    symbols: dict[int, Symbol]

    def defined_in(self, secnum: int) -> list[Symbol]:
        return [s for s in self.symbols.values() if s.section == secnum]


def parse_coff(path: Path) -> Coff:
    data = path.read_bytes()
    machine, nsec, _ts, psym, nsym, optsize, _ch = struct.unpack_from("<HHIIIHH", data, 0)
    if machine != 0x14C:
        raise ValueError(f"{path}: not an i386 COFF object")
    strtab = data[psym + 18 * nsym:]

    def longname(o: int) -> str:
        return strtab[o:strtab.index(b"\0", o)].decode("latin-1")

    sections = {}
    for i in range(nsec):
        raw = data[20 + optsize + 40 * i:20 + optsize + 40 * (i + 1)]
        name = raw[:8].rstrip(b"\0").decode("latin-1")
        if name.startswith("/") and name[1:].isdigit():
            name = longname(int(name[1:]))
        _vs, _va, rsize, rptr, prel, _pl, nrel, _nl, chars = struct.unpack_from("<IIIIIIHHI", raw, 8)
        body = data[rptr:rptr + rsize] if rptr else b"\0" * rsize
        relocs = [struct.unpack_from("<IIH", data, prel + 10 * k) for k in range(nrel)]
        sections[i + 1] = Section(i + 1, name, chars, body, relocs)
    symbols = {}
    k = 0
    while k < nsym:
        raw = data[psym + 18 * k:psym + 18 * (k + 1)]
        value, secnum, typ, storage, naux = struct.unpack_from("<IhHBB", raw, 8)
        name = longname(struct.unpack_from("<I", raw, 4)[0]) if raw[:4] == b"\0\0\0\0" else raw[:8].rstrip(b"\0").decode("latin-1")
        symbols[k] = Symbol(k, name, value, secnum, typ, storage, data[psym + 18 * (k + 1):psym + 18 * (k + 1 + naux)])
        k += 1 + naux
    return Coff(path, sections, symbols)
