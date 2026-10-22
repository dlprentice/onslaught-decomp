#!/usr/bin/env python3
"""Predict the import address table (IAT) layout of a tools/link.py link from its /VERBOSE log, and compare it with the
linked exe (and with the specimen's).

    python3 tools/iatsim.py [LINKDIR] [--retail] [-v]

LINKDIR is a tools/link.py output folder (default local-data/link/): link.log (pass-1 loads) and BEA.exe.

Model (LINK.EXE 6.00.8447; qsort and member-pull models in notes/link-reconstruction.md):
- Each short-import member LINK loads in pass 1 contributes one 4-byte dword to .idata$5 (an import: __imp_NAME or its
  thunk NAME) or the DLL's null terminator (the member defining DLL_NULL_THUNK_DATA); __IMPORT_DESCRIPTOR_DLL and
  __NULL_IMPORT_DESCRIPTOR members add nothing there. The records are in pass-1 load order.
- The linker sorts the .idata$5 contributions with MSVCRT qsort (Microsoft's, tools/link.py's native-msvcrt prefix) on the
  DLL name (strcmp), keeping Microsoft's order for equal keys (qsort is not stable).
- /OPT:REF then drops the imports whose __imp_ symbol nothing references ("Discarded __imp_X"); the survivors' slots close up.
The IAT is the concatenation, so each DLL's block is its sorted imports followed by its null thunk.

Prints, per DLL, whether the predicted order equals the exe's; with -v the sequences. --retail compares the specimen's IAT
with the prediction as well (what differs is an input the retail link had that ours does not).
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import binfmt  # noqa: E402
import decomp  # noqa: E402
import linkcmp  # noqa: E402

CUTOFF = 8


def ms_qsort(a: list, cmp) -> list:
    """Microsoft C runtime qsort (VC6 msvcrt 6.00): quicksort, middle element as the pivot swapped to lo, CUTOFF 8 short
    sort (select the maximum, swap it to the end), explicit stack, the smaller partition first. Sorts a in place."""
    n = len(a)
    if n < 2:
        return a

    def shortsort(lo: int, hi: int) -> None:
        while hi > lo:
            mx = lo
            for p in range(lo + 1, hi + 1):
                if cmp(a[p], a[mx]) > 0:
                    mx = p
            a[mx], a[hi] = a[hi], a[mx]
            hi -= 1
    stack: list[tuple[int, int]] = []
    lo, hi = 0, n - 1
    while True:
        size = hi - lo + 1
        if size <= CUTOFF:
            shortsort(lo, hi)
        else:
            mid = lo + size // 2
            a[mid], a[lo] = a[lo], a[mid]
            loguy, higuy = lo, hi + 1
            while True:
                loguy += 1
                while loguy <= hi and cmp(a[loguy], a[lo]) <= 0:
                    loguy += 1
                higuy -= 1
                while higuy > lo and cmp(a[higuy], a[lo]) >= 0:
                    higuy -= 1
                if higuy < loguy:
                    break
                a[loguy], a[higuy] = a[higuy], a[loguy]
            a[lo], a[higuy] = a[higuy], a[lo]
            if higuy - 1 - lo >= hi - loguy:
                if lo + 1 < higuy:
                    stack.append((lo, higuy - 1))
                if loguy < hi:
                    lo = loguy
                    continue
            else:
                if loguy < hi:
                    stack.append((loguy, hi))
                if lo + 1 < higuy:
                    hi = higuy - 1
                    continue
        if not stack:
            return a
        lo, hi = stack.pop()


def norm(name: str) -> str:
    """A symbol's import name: no __imp_/_ prefix, no @N suffix."""
    return re.sub(r"@\d+$", "", re.sub(r"^_", "", re.sub(r"^__imp_", "", name)))


def pass1_records(log: str) -> tuple[list[tuple[str, str | None]], set[str]]:
    """([(dll, name or None for a null thunk)] in load order, the discarded imports' names)."""
    records, found, discarded = [], None, set()
    for line in log.splitlines():
        m = re.match(r"\s+Found (\S+)", line)
        if m:
            found = m.group(1)
            continue
        m = re.match(r"\s+Loaded (\S+)\((\S+\.dll)\)", line, re.I)
        if m and found:
            if not found.startswith("__IMPORT_DESCRIPTOR") and found != "__NULL_IMPORT_DESCRIPTOR":
                records.append((m.group(2), None if "NULL_THUNK" in found else norm(found)))
            found = None
        m = re.match(r"\s+Discarded (__imp_\S+) from \S+\((\S+\.dll)\)", line, re.I)
        if m:
            discarded.add((m.group(2), norm(m.group(1))))
    return records, discarded


def predict(records: list, discarded: set) -> list[tuple[str, str | None]]:
    """The IAT's slot sequence: sorted by DLL name with Microsoft's qsort, dropped imports removed."""
    idx = list(range(len(records)))
    ms_qsort(idx, lambda a, b: (records[a][0] > records[b][0]) - (records[a][0] < records[b][0]))
    ordered = [records[i] for i in idx if (records[i][0], records[i][1]) not in discarded]
    # a DLL's null terminator is its table's last dword wherever qsort left it among the DLL's records: the null thunk is
    # a separate section (.idata$5 of the null-thunk member) that the linker places after the DLL's imports
    out: list[tuple[str, str | None]] = []
    for dll in dict.fromkeys(d for d, _ in ordered):
        out += [r for r in ordered if r[0] == dll and r[1] is not None] + [r for r in ordered if r[0] == dll and r[1] is None]
    return out


def actual(path: Path) -> list[tuple[str, str | None, int]]:
    """(dll, import name or None for a null slot, slot address) for every slot of the image's IAT, by address."""
    img = binfmt.PeImage(path)
    slots = {}
    for dll, ents in linkcmp.import_table(img):
        last = 0
        for n, _h, s in ents:
            slots[s] = (dll, norm(n) if not n.startswith("#") else n)
            last = max(last, s)
        slots[last + 4] = (dll, None)
    return [(d, n, s) for s, (d, n) in sorted(slots.items())]


def compare(pred: list, act: list, verbose: bool) -> int:
    """Print the per-DLL verdict; ordinal imports compare by position only. Returns the number of DLLs that differ."""
    bad = 0
    dlls = []
    for d, _n, _s in act:
        if d not in dlls:
            dlls.append(d)
    for dll in dlls:
        a = [n for d, n, _ in act if d == dll]
        p = [n for d, n in pred if d == dll]
        if any(n and n.startswith("#") for n in a):
            ok = len(a) == len(p)         # names unknown: only the count is testable
        else:
            ok = a == p
        bad += not ok
        print(f"  {dll:14} {len(a) - 1:3} imports  {'equal' if ok else 'DIFFERS'}")
        if verbose and not ok:
            print("     actual   ", a)
            print("     predicted", p)
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("linkdir", nargs="?", type=Path, default=decomp.ROOT / "local-data/link")
    ap.add_argument("--retail", action="store_true", help="also compare the specimen's IAT with the prediction")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    records, discarded = pass1_records((a.linkdir / "link.log").read_text(errors="replace"))
    pred = predict(records, discarded)
    print(f"{len(records)} pass-1 records, {len(discarded)} discarded, {len(pred)} slots predicted")
    act = actual(a.linkdir / "BEA.exe")
    print(f"our exe: {len(act)} slots (incl. null terminators)")
    bad = compare(pred, act, a.v)
    blocks = [(d, sum(1 for dd, _n, _s in act if dd == d)) for d in dict.fromkeys(d for d, _n, _s in act)]
    pblocks = [(d, sum(1 for dd, _n in pred if dd == d)) for d in dict.fromkeys(d for d, _n in pred)]
    print(f"ours: {'all DLLs equal' if not bad else f'{bad} DLLs differ'}; DLL blocks (order and slot counts) equal: {blocks == pblocks}")
    if a.retail:
        ract = actual(decomp.SPECIMEN)
        print(f"retail: {len(ract)} slots")
        bad = compare(pred, ract, a.v)
        print(f"retail vs prediction: {bad} DLLs differ")


if __name__ == "__main__":
    main()
