#!/usr/bin/env python3
"""Simulate LINK 6.00's identical-COMDAT folding (/OPT:ICF): which copy of each group of identical functions survives.

    python3 tools/icfsim.py [LINKDIR]
    python3 tools/icfsim.py [LINKDIR] --report --expected EXPECTED.json

LINKDIR is a tools/link.py output folder (default local-data/link/): its link.rsp names the objects, and its link.log
(LINK's /VERBOSE output) gives the order library members were loaded in and the fold groups LINK chose. The tool
rebuilds LINK's array of foldable contributions from those inputs, sorts it as LINK does, predicts each group's
survivor and compares the prediction with the log.

Survivors behave like a hash of the whole array (deleting any one record changes about half of them), so they match
retail's only once every record does. --report measures that convergence instead, with EXPECTED.json from
tools/linkcmp.py --write-expected (symbol -> retail address) and the retail function table:
- (a) keys: game COMDATs whose raw size is neither their retail function's size rounded up to 16 nor the distance
  to the next retail function (a COMDAT carries its switch jump tables and any code after a call that does not
  return, which the function table's extents leave out); relocation counts are not visible in retail;
- (b) emission: for an inline COMDAT whose retail address lies between two out-of-line functions of one object,
  retail's first definer is that object (functions our link folds are left out: an ICF survivor's address
  belongs to whichever identical copy won), so our objects earlier in link order that define it emit a copy
  retail's did not, and that object not defining it is a missing emission;
- (c) library: the library members' records, which match retail's only with retail's library builds (not yet pinned).

How LINK chooses (LINK.EXE 6.00.8447; --report --expected measures this model against retail's fold groups):
- Pass 1 records each COMDAT once, by its first definer, as it selects it: the response-file objects in
  order, then the library members in the order the log's "Loaded LIB(member)" lines give; within an object, in
  symbol-table order. A duplicate COMDAT adds nothing. An associative COMDAT (selection 5, such as the .text$x
  exception funclets) is recorded at its section symbol when its parent section was selected. Only non-empty
  executable sections qualify, and names starting with _$E do not. Non-COMDAT .text is never recorded.
- The ICF pass sorts the records with MSVCRT qsort (Microsoft's, see tools/link.py) by (raw section size,
  relocation count), ascending. In each run of equal keys, every element absorbs the later
  elements identical to it, so a group's survivor is its first member in sorted order.
- Which elements are identical is the log's business here: besides equal bytes and relocation targets, LINK requires
  both copies to be referenced (with /OPT:REF) and the compilers' COMDAT checksums (the section symbol's aux bytes
  8..11) to be equal, so identical bytes with different checksums never fold. The COMDAT selection (aux byte 14) must
  match too: an out-of-line function (NODUPLICATES, 1) never folds with an inline one (ANY, 2). Measured on our own
  link (2026-10-15): of 19 groups of identical bodies that mix the two, none shares an address across them, while 61 of
  63 single-selection groups fold fully. A retail fold of an out-of-line function with an inline one therefore means
  our inline-ness differs from the original (CSphere::CollideWithMesh, ~CMapWhoEntry).
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import struct
import sys
import tempfile
from pathlib import Path
from typing import Callable, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import binfmt  # noqa: E402
import decomp  # noqa: E402
import link  # noqa: E402

CUTOFF = 8   # Microsoft's qsort sorts partitions of up to 8 elements by selection (shortsort)


def ms_qsort(a: list, cmp: Callable[[object, object], int]) -> list:
    """Sort a in place exactly as MSVCRT 6.00's qsort orders it, ties included: quicksort on the middle element
    swapped to the front, the smaller partition first through an explicit stack, short partitions by repeatedly
    moving the largest element to the end."""
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

    stack, lo, hi = [], 0, n - 1
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


class Record(NamedTuple):
    size: int                   # raw section size
    relocs: int                 # relocation count
    name: str                   # as LINK names it: the COMDAT symbol, or the section name for a static or associative
    obj: str                    # object as the log names it: file name, or lib(member) for a pulled member
    aliases: tuple[str, ...]    # every external defined at the section start, weak externals that default to it
    body: int = 0               # fingerprint of what folding compares (fold groups share it)


def fingerprint(sec: binfmt.Section, checksum: int, selection: int = 0) -> int:
    """What identical-COMDAT folding compares, short of resolving relocation targets: the bytes with relocation
    fields masked, the relocation offsets and types, the compiler's COMDAT checksum and the COMDAT selection."""
    data = bytearray(sec.data)
    for off, _sym, typ in sec.relocs:
        width = binfmt.REL_WIDTH.get(typ, 4)
        data[off:off + width] = bytes(width)
    return hash((bytes(data), tuple((off, typ) for off, _sym, typ in sec.relocs), checksum, selection))


def member_key(text: str) -> tuple[str, str] | None:
    """A /VERBOSE fold line's symbol and object: '"undecorated" (decorated) from obj', '"name" from obj' or
    'name from obj'."""
    text = text.strip()
    m = (re.search(r'\((\?[^)]*|[^)]*)\) from (\S+)$', text) or re.search(r'"(.*)" from (\S+)$', text)
         or re.match(r'(\S+) from (\S+)$', text))
    return (m.group(1), m.group(2).lower()) if m else None


def fold_groups(log: str) -> list[list[tuple[str, str]]]:
    """The fold groups /VERBOSE prints, each as [selected, replaced...], in the order printed."""
    out, lines, i = [], log.splitlines(), 0
    while i < len(lines):
        if lines[i].strip() == "Selected symbol:" and i + 2 < len(lines):
            group = [member_key(lines[i + 1])]
            i += 3
            while i < len(lines) and lines[i].startswith("        "):
                group.append(member_key(lines[i]))
                i += 1
            out.append([g for g in group if g])
        else:
            i += 1
    return out


def library_loads(log: str) -> tuple[list[tuple[str, str]], dict[str, Path]]:
    """The library members pass 1 loaded, in order, as (library file name, member), and each searched library's
    path, both lower-cased by file name."""
    paths = {}
    for m in re.finditer(r'Searching (\S+):', log):
        p = Path(m.group(1).replace("Z:", "").replace("\\", "/"))
        if not p.exists() and p.parent.is_dir():
            p = next((q for q in p.parent.iterdir() if q.name.lower() == p.name.lower()), p)
        paths[p.name.lower()] = p
    loads = [(m.group(1).lower(), m.group(2).lower()) for m in re.finditer(r'Loaded (\S+)\((\S+)\)', log)]
    return loads, paths


def object_records(c: binfmt.Coff, obj: str, taken: set[str]) -> list[Record]:
    """One object's records in pass-1 order; taken holds the external COMDAT names already selected."""
    def eligible(sec: binfmt.Section) -> bool:
        return (len(sec.data) > 0 and bool(sec.chars & 0x20000000)
                and (not sec.chars & 0x80000000 or bool(sec.chars & 0x20)))

    defined = {s.name: s for s in c.symbols.values() if s.section > 0 and s.storage == 2}
    aliases: dict[int, set[str]] = {}
    for s in c.symbols.values():
        if s.section > 0 and s.value == 0 and s.storage == 2:
            aliases.setdefault(s.section, set()).add(s.name)
        if s.storage == binfmt.SYM_WEAK and len(s.aux) >= 4:      # a weak external names its default in aux
            t = c.symbols.get(struct.unpack_from("<I", s.aux, 0)[0])
            if t is not None and t.section <= 0:
                t = defined.get(t.name)
            if t is not None and t.section > 0:
                aliases.setdefault(t.section, set()).add(s.name)
    out, sectioned, chosen, kept, checksum, selection = [], set(), set(), set(), {}, {}
    for s in sorted(c.symbols.values(), key=lambda s: s.index):
        if s.section <= 0:
            continue
        sec = c.sections[s.section]
        if s.storage == binfmt.SYM_STATIC and s.name == sec.name and s.value == 0 and s.aux:
            sectioned.add(s.section)
            checksum[s.section] = struct.unpack_from("<I", s.aux, 8)[0] if len(s.aux) >= 12 else 0
            selection[s.section] = s.aux[14] if len(s.aux) > 14 else 0
            if sec.comdat and len(s.aux) > 14 and s.aux[14] == 5:     # associative: follows its parent
                if int.from_bytes(s.aux[12:14], "little") in kept and eligible(sec):
                    out.append(Record(len(sec.data), len(sec.relocs), sec.name, obj, (),
                                      fingerprint(sec, checksum[s.section], selection[s.section])))
            continue
        if not sec.comdat or s.section not in sectioned or s.section in chosen or s.storage not in (2, 3):
            continue
        chosen.add(s.section)                # the first symbol after the section symbol is its COMDAT symbol
        if s.storage == 2:
            if s.name in taken:
                continue
            taken.add(s.name)
        kept.add(s.section)
        if eligible(sec) and not s.name.startswith("_$E"):
            out.append(Record(len(sec.data), len(sec.relocs), s.name if s.storage == 2 else sec.name, obj,
                              tuple(sorted(aliases.get(s.section, ()))),
                              fingerprint(sec, checksum[s.section], selection[s.section])))
    return out


def records(objs: list[Path], loads: list[tuple[str, str]], libpaths: dict[str, Path]) -> list[Record]:
    """LINK's pass-1 array: the response-file objects, then each loaded library member (import members add
    nothing to it)."""
    taken: set[str] = set()
    out = []
    for p in objs:
        out += object_records(binfmt.parse_coff(p), p.name.lower(), taken)
    cache: dict[str, dict[str, bytes]] = {}
    with tempfile.TemporaryDirectory(dir=os.environ.get("BEA_TMP")) as tmp:
        for lib, member in loads:
            if member.endswith(".dll") or lib not in libpaths:
                continue
            members = cache.setdefault(lib, link.archive_members(libpaths[lib]))
            body = members.get(member.replace("\\", "/").rsplit("/", 1)[-1])
            if body is None:            # alias-only members (OLDNAMES) are not COFF objects
                continue
            path = Path(tmp) / "m.obj"
            path.write_bytes(body)
            out += object_records(binfmt.parse_coff(path), f"{lib}({member})", taken)
    return out


def sorted_positions(recs: list[Record]) -> dict[tuple[str, str], list[tuple[int, tuple[int, int, int]]]]:
    """Each (name, object) and alias to its places in LINK's sorted array, with their key and body: a static
    COMDAT is named by its section (.text), so one object can hold several."""
    order = ms_qsort(list(range(len(recs))),
                     lambda a, b: (recs[a].size - recs[b].size) or (recs[a].relocs - recs[b].relocs))
    pos: dict[tuple[str, str], list[tuple[int, tuple[int, int, int]]]] = {}
    for i, r in enumerate(order):
        rec = recs[r]
        for name in (rec.name,) + rec.aliases:
            pos.setdefault((name, rec.obj), []).append((i, (rec.size, rec.relocs, rec.body)))
    return pos


def survivor(group: list[tuple[str, str]], pos: dict, nth: int = 0) -> tuple[str, str] | None:
    """The member LINK keeps: the first in sorted order (None if a member is not in the array). Members of a group
    share one key and body. When several groups carry the same names (static functions are all .text), LINK prints
    them in sorted order, so the nth such group takes the nth smallest key they share."""
    norm = [(n, o.lower()) for n, o in group]
    if any(m not in pos for m in norm):
        return None
    keys = sorted(set.intersection(*({k for _i, k in pos[m]} for m in norm)))
    if not keys:
        return None
    key = keys[min(nth, len(keys) - 1)]
    return min(norm, key=lambda m: min(i for i, k in pos[m] if k == key))


def ambiguous(group: list[tuple[str, str]], pos: dict) -> bool:
    """Whether a member's place is a guess: its name occurs more than once in its object with the group's key and
    body."""
    norm = [(n, o.lower()) for n, o in group]
    keys = set.intersection(*({k for _i, k in pos.get(m, [])} for m in norm)) if all(m in pos for m in norm) else set()
    return any(sum(1 for _i, k in pos[m] if k in keys) > 1 for m in norm) if keys else False


def check(linkdir: Path) -> tuple[int, list[tuple[tuple[str, str], tuple[str, str] | None, bool]]]:
    """(groups predicted right, [(LINK's survivor, the prediction, whether a member's place was a guess) for each
    other group])."""
    log = (linkdir / "link.log").read_text(errors="replace")
    objs = [Path(l.strip().replace("Z:", "").replace("\\", "/"))
            for l in (linkdir / "link.rsp").read_text().splitlines() if l.strip().lower().endswith(".obj")]
    loads, libpaths = library_loads(log)
    pos = sorted_positions(records(objs, loads, libpaths))
    ok, wrong, seen = 0, [], {}
    for group in fold_groups(log):
        names = tuple(sorted((n, o.lower()) for n, o in group))
        seen[names] = seen.get(names, -1) + 1
        pred = survivor(group, pos, seen[names])
        if pred == (group[0][0], group[0][1].lower()):
            ok += 1
        else:
            wrong.append((group[0], pred, ambiguous(group, pos)))
    return ok, wrong


def comdat_symbols(c: binfmt.Coff) -> list[tuple[str, int, int]]:
    """Every COMDAT's (symbol, selection, section) in an object, duplicates included."""
    out, sel = [], {}
    for s in sorted(c.symbols.values(), key=lambda s: s.index):
        if s.section <= 0:
            continue
        sec = c.sections[s.section]
        if s.storage == binfmt.SYM_STATIC and s.name == sec.name and s.value == 0 and s.aux and sec.comdat:
            sel[s.section] = s.aux[14] if len(s.aux) > 14 else 0
        elif s.section in sel and s.storage == 2 and s.value == 0 and sec.code:
            out.append((s.name, sel.pop(s.section), s.section))
    return out


def report(linkdir: Path, expected: Path) -> dict:
    """The three convergence counts and their worst objects (see the module docstring)."""
    log = (linkdir / "link.log").read_text(errors="replace")
    paths = [Path(l.strip().replace("Z:", "").replace("\\", "/"))
             for l in (linkdir / "link.rsp").read_text().splitlines() if l.strip().lower().endswith(".obj")]
    game = [p for p in paths if not any(part in ("libmembers", "third-party", "linklib") for part in p.parts)]
    gameset = {p.name.lower() for p in game}
    order = {p.name.lower(): i for i, p in enumerate(game)}
    loads, libpaths = library_loads(log)
    recs = records(paths, loads, libpaths)
    exp = json.loads(expected.read_text())["functions"]
    names_at: dict[int, int] = {}
    for a in exp.values():
        names_at[a] = names_at.get(a, 0) + 1
    retail = decomp.retail_functions()
    starts = sorted(retail)

    # (a) keys
    checked, wrong_keys = 0, {}
    for r in recs:
        a = exp.get(r.name)
        if r.obj not in gameset or a is None or names_at[a] != 1 or a not in retail:
            continue
        checked += 1
        size = retail[a].size
        i = bisect.bisect_right(starts, a)
        span = starts[i] - a if i < len(starts) else None        # the whole contribution, tables included
        if r.size not in (size, (size + 15) // 16 * 16, span):
            wrong_keys.setdefault(r.obj, []).append((r.name, r.size, size))

    # (b) emission
    defines: dict[str, list[str]] = {}
    anywhere: dict[str, set[str]] = {}       # every object defining the name, inline or out of line
    own: dict[str, list[int]] = {}
    for p in game:
        for name, sel, _sec in comdat_symbols(binfmt.parse_coff(p)):
            obj = p.name.lower()
            anywhere.setdefault(name, set()).add(obj)
            if sel == 2:
                defines.setdefault(name, []).append(obj)
            elif sel == 1 and name in exp and names_at[exp[name]] == 1:
                own.setdefault(obj, []).append(exp[name])
    anchors = sorted((a, o) for o, addrs in own.items() for a in addrs)
    keys = [a for a, _o in anchors]
    folded = {n for g in fold_groups(log) for n, _o in g}   # an identical function's retail address may be another's
    folded |= {'??_G' + n[4:] for n in folded if n.startswith('??_E')}    # the log names a ??_G body by its ??_E alias
    extra, missing, placed = {}, {}, 0
    for name, objs in defines.items():
        a = exp.get(name)
        if a is None or names_at[a] != 1 or name in folded:
            continue
        i = bisect.bisect_left(keys, a)        # an object's contributions are contiguous: the out-of-line functions
        if i == 0 or i == len(keys) or anchors[i - 1][1] != anchors[i][1]:     # on both sides must be one object's
            continue
        placed += 1
        home = anchors[i][1]
        for o in objs:
            if order[o] < order[home]:
                extra.setdefault(o, []).append(name)
        if home not in anywhere.get(name, ()):      # an out-of-line definition there is the same emission
            missing.setdefault(home, []).append(name)

    # (c) library
    library = sum(1 for r in recs if r.obj not in gameset)
    return {"records": len(recs), "game_records": len(recs) - library, "library_records": library,
            "keys_checked": checked, "keys_wrong": sum(len(v) for v in wrong_keys.values()),
            "keys_by_object": wrong_keys,
            "inline_placed": placed, "extra_emissions": sum(len(v) for v in extra.values()), "extra_by_object": extra,
            "missing_emissions": sum(len(v) for v in missing.values()), "missing_by_object": missing,
            "library_members": len({r.obj for r in recs if r.obj not in gameset})}


def print_report(r: dict) -> None:
    print(f"records {r['records']}: game {r['game_records']}, library {r['library_records']}")
    print(f"(a) keys: {r['keys_wrong']} of {r['keys_checked']} game COMDATs with a known retail size differ")
    print(f"(b) emission: of {r['inline_placed']} inline COMDATs placed in one retail region, "
          f"{r['extra_emissions']} copies emitted by objects retail's did not, {r['missing_emissions']} missing")
    print(f"(c) library: {r['library_records']} records from {r['library_members']} members; identical to retail: "
          "unknown until retail's library builds are pinned")
    for key, title in (("keys_by_object", "(a)"), ("extra_by_object", "(b) extra"),
                       ("missing_by_object", "(b) missing")):
        worst = sorted(r[key].items(), key=lambda kv: -len(kv[1]))[:8]
        if worst:
            print(f"  {title} by object: " + ", ".join(f"{o} {len(v)}" for o, v in worst))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("linkdir", nargs="?", type=Path, default=decomp.ROOT / "local-data/link")
    ap.add_argument("--report", action="store_true", help="print the array-convergence counts instead")
    ap.add_argument("--expected", type=Path, help="tools/linkcmp.py --write-expected output (needed by --report)")
    ap.add_argument("--json", type=Path, help="with --report: also write the full lists here")
    a = ap.parse_args()
    if a.report:
        if not a.expected:
            raise SystemExit("--report needs --expected (tools/linkcmp.py --write-expected makes it)")
        r = report(a.linkdir.resolve(), a.expected)
        print_report(r)
        if a.json:
            a.json.write_text(json.dumps(r, indent=1) + "\n")
        return
    ok, wrong = check(a.linkdir.resolve())
    print(f"{ok} of {ok + len(wrong)} fold groups predicted")
    for actual, pred, guess in wrong:
        guessed = f"{pred[0]} from {pred[1]}" if pred else "nothing"
        print(f"  LINK kept {actual[0]} from {actual[1]}; predicted {guessed}"
              + (" (ambiguous: a static name occurs twice in one object with this key and body)" if guess else ""))
    sys.exit(1 if any(not guess for _a, _p, guess in wrong) else 0)


if __name__ == "__main__":
    main()
