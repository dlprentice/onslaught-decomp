#!/usr/bin/env python3
"""Map the retail code to its object files.

Two kinds of evidence, both read from the pristine executable:
  - __FILE__ strings ("C:\\dev\\ONSLAUGHT2\\X.cpp") pushed by code: every function that pushes one belongs to
    X.cpp's object (or inlines code from X.h when the string names a header);
  - the dynamic initializers of the maths header's per-file constants (the zero vector: three zeroing
    stores and a RET), which the compiler emits at the end of each object that includes the header.

The linker keeps each object's functions together and in order, so a file's functions span one range, and a
range ends at its object's initializers. Writes config/objects.tsv: one row per source file with the span of
its string-referencing functions, the count of those functions, and the end marker that closes the span.
"""
from __future__ import annotations

import bisect
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from binfmt import PeImage  # noqa: E402
from decomp import CONFIG, GAME_END, SPECIMEN, SPECIMEN_SHA256, retail_functions  # noqa: E402

PREFIX = b"C:\\dev\\ONSLAUGHT2\\"


def main() -> None:
    image = PeImage(SPECIMEN, SPECIMEN_SHA256)
    table = retail_functions()
    starts = sorted(a for a in table if a < GAME_END)

    def owner(va: int) -> int | None:
        i = bisect.bisect_right(starts, va) - 1
        if i >= 0 and va < starts[i] + table[starts[i]].size:
            return starts[i]
        return None

    # the source-path strings and their addresses
    paths: dict[int, str] = {}
    for name, base, _vs, rptr, rsize in image.sections[1:3]:
        blob = image.data[rptr:rptr + rsize]
        for m in re.finditer(re.escape(PREFIX) + rb"[^\0]+\0", blob):
            paths[base + m.start()] = m.group()[len(PREFIX):-1].decode("latin-1")
    _n, tbase, _v, trptr, trsize = image.sections[0]
    text = image.data[trptr:trptr + trsize]
    users: dict[str, set[int]] = {}
    for m in re.finditer(rb"\x68(....)", text, re.S):
        target = int.from_bytes(m.group(1), "little")
        if target in paths:
            f = owner(tbase + m.start())
            if f is not None:
                users.setdefault(paths[target], set()).add(f)
    # the zero-vector initializers that close objects
    zero3 = re.compile(rb"\xc7\x05....\x00\x00\x00\x00\xc7\x05....\x00\x00\x00\x00\xc7\x05....\x00\x00\x00\x00\xc3", re.S)
    ends = sorted(tbase + m.start() for m in zero3.finditer(text) if tbase + m.start() < GAME_END)
    rows = []
    for path, fns in users.items():
        lo, hi = min(fns), max(fns)
        k = bisect.bisect_left(ends, hi)
        end = ends[k] if k < len(ends) else None
        rows.append((lo, hi, path, len(fns), end))
    rows.sort()
    with (CONFIG / "objects.tsv").open("w") as out:
        out.write("first\tlast\tfile\tfunctions\tnextInitializer\n")
        for lo, hi, path, n, end in rows:
            out.write(f"0x{lo:08x}\t0x{hi:08x}\t{path}\t{n}\t{'' if end is None else f'0x{end:08x}'}\n")
    overlaps = [(a, b) for a, b in zip(rows, rows[1:]) if b[0] <= a[1]]
    print(f"{len(paths)} source-path strings, {len(rows)} files referenced from code, {len(ends)} initializer ends, "
          f"{len(overlaps)} overlapping spans")
    for a, b in overlaps[:20]:
        print(f"  overlap: {a[2]} {a[0]:08x}-{a[1]:08x} and {b[2]} {b[0]:08x}-{b[1]:08x}")


if __name__ == "__main__":
    main()
