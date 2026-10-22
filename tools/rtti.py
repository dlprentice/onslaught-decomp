#!/usr/bin/env python3
"""List every polymorphic class from the retail executable's RTTI (the build used /GR).

Each virtual table is preceded by a pointer to its Complete Object Locator, which names the class's
TypeDescriptor (the decorated name, such as .?AVCThing@@) and its Class Hierarchy Descriptor (every base class
with its offset). Writes config/classes.tsv: one row per virtual table with the class, the subobject offset the
table serves, the table's address and slot count, and the base classes in hierarchy order.

    python3 tools/rtti.py              # write config/classes.tsv
    python3 tools/rtti.py CThing       # print one class's tables and slots, with callee names
"""
from __future__ import annotations

import csv
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from binfmt import PeImage  # noqa: E402
from decomp import CONFIG, SPECIMEN, SPECIMEN_SHA256, retail_functions  # noqa: E402


def undecorate(names: list[str]) -> dict[str, str]:
    """.?AVCThing@@ -> CThing (through llvm-undname on a synthesized ??_7 vftable name)."""
    wanted = {n: "??_7" + n[4:] + "6B@" for n in names if n.startswith(".?A")}
    text = subprocess.run(["llvm-undname"], input="\n".join(wanted.values()) + "\n", capture_output=True, text=True).stdout
    lines = text.split("\n")
    out = {}
    for n, m in wanted.items():
        try:
            k = lines.index(m)
            out[n] = lines[k + 1].replace("const ", "").replace("::`vftable'", "").strip()
        except (ValueError, IndexError):
            out[n] = n
    return out


def main() -> None:
    image = PeImage(SPECIMEN, SPECIMEN_SHA256)
    table = retail_functions()
    text_lo, text_hi = image.sections[0][1], image.sections[0][1] + image.sections[0][2]
    code = lambda v: v is not None and text_lo <= v < text_hi

    def type_name(td: int) -> str | None:
        raw = image.read(td + 8, 256)
        if raw is None or not raw.startswith(b".?A"):
            return None
        return raw.split(b"\0")[0].decode("latin-1")

    # first pass: every dword that points at a valid Complete Object Locator
    locators: dict[int, tuple[str, int, int]] = {}          # address of the pointer -> (class, offset, hierarchy)
    for name, base, vsize, rptr, rsize in image.sections[1:3]:           # .rdata and .data
        for off in range(0, rsize - 8, 4):
            col = struct.unpack_from("<I", image.data, rptr + off)[0]
            head = image.read(col, 20)
            if head is None:
                continue
            sig, offset, _cd, td, chd = struct.unpack("<IIIII", head)
            if sig != 0 or offset > 0x10000:
                continue
            cls = type_name(td)
            if cls is not None:
                locators[base + off] = (cls, offset, chd)
    rows = []
    for at, (cls, offset, chd) in locators.items():
        vt = at + 4
        slots = 0
        while code(image.u32(vt + 4 * slots)) and (vt + 4 * slots) not in locators:
            slots += 1
        hd = image.read(chd, 16)
        bases = []
        if hd is not None:
            _s, _attr, count, arr = struct.unpack("<IIII", hd)
            for k in range(min(count, 64)):
                bcd = image.u32(arr + 4 * k)
                rec = image.read(bcd, 24) if bcd else None
                if rec is None:
                    break
                btd, _contained, mdisp, _pdisp, _vdisp, _battr = struct.unpack("<IIiiiI", rec)
                bases.append((type_name(btd) or "?", mdisp))
        rows.append((cls, offset, vt, slots, bases))
    names = undecorate(sorted({r[0] for r in rows} | {b for r in rows for b, _ in r[4]}))
    rows.sort(key=lambda r: (names.get(r[0], r[0]), r[1]))
    if len(sys.argv) > 1:
        want = sys.argv[1]
        for cls, offset, vt, slots, bases in rows:
            if names.get(cls) != want:
                continue
            print(f"{want} +{offset:#x}: vftable {vt:08x}, {slots} slots; bases: "
                  + ", ".join(f"{names.get(b, b)}@{m:#x}" for b, m in bases[1:]))
            for k in range(slots):
                f = image.u32(vt + 4 * k)
                print(f"   [{k:3d}] +{4 * k:#05x} {f:08x} {table[f].name if f in table else ''}")
        return
    with (CONFIG / "classes.tsv").open("w") as out:
        out.write("class\tsubobjectOffset\tvftable\tslots\tbases\n")
        for cls, offset, vt, slots, bases in rows:
            out.write(f"{names.get(cls, cls)}\t{offset:#x}\t0x{vt:08x}\t{slots}\t"
                      + ";".join(f"{names.get(b, b)}@{m:#x}" for b, m in bases[1:]) + "\n")
    print(f"{len(rows)} virtual tables, {len({r[0] for r in rows})} classes -> config/classes.tsv")


if __name__ == "__main__":
    main()
