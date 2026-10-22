#!/usr/bin/env python3
"""Shift-aligned code equality: how much of our linked .text equals retail's once each function is compared at its own address.

    python3 tools/alignedeq.py LINKDIR [--expected EXPECTED.json] [--build DIR] [--json FILE]

LINKDIR is a tools/link.py output folder (BEA.exe and BEA.map). Retail addresses come, as in tools/placemap.py, from the
current source's FUNCTION annotations resolved against this checkout's build/*.obj (run a check first), or from a frozen
tools/linkcmp.py --write-expected file. A function counts when our symbol pairs with a retail function whose address no other
expected entry shares; its length is retail's own extent (config/functions.tsv with the corrections applied) and the bytes
compared are ours at our address against retail's at its address.

Same-address equality (the plain section comparison) loses a whole object's bytes whenever anything before it moves by a few
bytes; comparing each function at its own address does not, so this is the metric for "the code is identical". Three numbers:

  raw      every byte equal.
  rel32    bytes equal after masking the operands of REL32 relocations (calls and jumps to other symbols: their distance moves
           with the layout).
  all      bytes equal after masking the operands of every relocation of the function (REL32 and absolute DIR32 addresses of
           data and code). "Code identical except addresses": the real target. The retail image carries no base-relocation
           table (RELOCS_STRIPPED), so the masks come from our objects' COFF relocations, at the same function-relative offsets
           in both images. A function folded onto another's body (ICF) takes the relocations of whichever name at its address
           has an object section.
"""
from __future__ import annotations

import argparse
import bisect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decomp  # noqa: E402
import linkcmp  # noqa: E402
import placemap  # noqa: E402
from binfmt import PeImage, parse_coff  # noqa: E402

REL32 = 0x14            # IMAGE_REL_I386_REL32
OPERAND = 4             # every relocation here patches a dword


def masked_equal(ours: bytes, retail: bytes, relocs: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    """(length, raw equal, rel32-masked equal, all-relocations-masked equal) for two byte strings of one function.
    relocs: (function-relative offset, COFF type). Bytes past the shorter string count as unequal."""
    n = max(len(ours), len(retail))
    short = min(len(ours), len(retail))
    equal = [i < short and ours[i] == retail[i] for i in range(n)]
    rel32, every = list(equal), list(equal)
    for off, typ in relocs:
        for i in range(off, min(off + OPERAND, short)):
            every[i] = True
            if typ == REL32:
                rel32[i] = True
    return n, sum(equal), sum(rel32), sum(every)


def function_relocs(build: Path, objects: dict[str, Path] | None = None) -> dict[tuple[str, str], list[tuple[int, int]]]:
    """(symbol, lower case object file name) -> [(function-relative offset, type)] for every function the objects under build/
    define. A COMDAT code section holds one function; a plain .text section holds many, so its relocations are split at the
    function symbols' offsets (a function runs to the next function symbol or the section's end)."""
    out = {}
    for obj in sorted(build.rglob("*.obj")):
        try:
            coff = parse_coff(obj)
        except (ValueError, OSError):
            continue
        for secnum, sec in coff.sections.items():
            if not sec.code:
                continue
            funcs = sorted({(s.value, s.name) for s in coff.defined_in(secnum)
                            if s.storage in (decomp.SYM_EXTERNAL, decomp.SYM_STATIC) and s.name != sec.name
                            and (s.type & 0x30) == 0x20})
            for k, (start, name) in enumerate(funcs):
                end = funcs[k + 1][0] if k + 1 < len(funcs) else len(sec.data)
                out[(name, obj.name.lower())] = [(off - start, typ) for off, _sym, typ in sec.relocs if start <= off < end]
    return out


def compare(linkdir: Path, expected: dict, relocs: dict, retail_image, our_image, retail_sizes: dict[int, int], visit=None) -> dict:
    ours = placemap.code_symbols(linkdir / "BEA.map")
    count: dict[tuple[str, str], int] = {}
    for _a, n, o, _i in ours:
        count[(n, o)] = count.get((n, o), 0) + 1
    names_at: dict[int, int] = {}
    for a in expected.values():
        names_at[a] = names_at.get(a, 0) + 1
    # ICF folds several functions onto one body; the map lists each name, but only the surviving object's section carries the relocations
    at_address: dict[int, list[tuple[str, str]]] = {}
    for a, n, o, _i in ours:
        at_address.setdefault(a, []).append((n, o.lower()))
    seen, totals = set(), [0, 0, 0, 0]
    pairs = 0
    per_object: dict[str, list[int]] = {}
    for addr, name, obj, _inline in ours:
        if (name, obj) in seen or name.startswith(("_$", ".")):
            continue
        seen.add((name, obj))
        r = placemap.lookup(expected, name, obj)
        size = retail_sizes.get(r) if r is not None else None
        if r is None or not size or names_at.get(r, 0) != 1:
            continue
        a = our_image.read(addr, size)
        b = retail_image.read(r, size)
        mine = relocs.get((name, obj.lower()))
        if mine is None:
            mine = next((relocs[k] for k in at_address[addr] if k in relocs), [])
        if visit:
            visit(obj, addr, a, b, mine, r)
        n, e, e32, ea = masked_equal(a, b, mine)
        pairs += 1
        for k, v in enumerate((n, e, e32, ea)):
            totals[k] += v
        row = per_object.setdefault(obj, [0, 0, 0, 0])
        for k, v in enumerate((n, e, e32, ea)):
            row[k] += v
    n = totals[0] or 1
    return {"functions": pairs, "bytes": totals[0], "raw": totals[1], "rel32": totals[2], "all": totals[3],
            "raw_pct": 100 * totals[1] / n, "rel32_pct": 100 * totals[2] / n, "all_pct": 100 * totals[3] / n,
            "objects": {o: v for o, v in sorted(per_object.items())}}


THUNK_OBJECT = "thunks.obj"


class TargetKinds:
    """Classifies an address of our image by the map: the public symbol at or before it, its object, and where it lies."""

    def __init__(self, map_path: Path, game_objects: set[str], image_sections: list):
        self.game = game_objects
        self.rows = []      # (address, object lower case)
        self.names: dict[int, list[tuple[str, str]]] = {}   # address -> [(symbol, object)]
        for line in map_path.read_text(errors="replace").splitlines():
            m = linkcmp.MAP_LINE.match(line)
            if m and m.group(7) and not m.group(7).startswith("<"):
                self.rows.append((int(m.group(4), 16), m.group(7).lower()))
                self.names.setdefault(int(m.group(4), 16), []).append((m.group(3), m.group(7)))
        self.rows.sort()
        self.starts = [a for a, _o in self.rows]
        self.sections = image_sections        # (name, va, vsize, rawoff, rawsize)

    def symbol(self, addr: int) -> str:
        k = bisect.bisect_right(self.starts, addr) - 1
        if k < 0:
            return "?"
        names = self.names.get(self.starts[k], [("?", "?")])
        return f"{names[0][0][:40]} ({names[0][1]})"

    def region(self, addr: int) -> str:
        for name, va, vsize, _off, rawsize in self.sections:
            if va <= addr < va + vsize:
                if name == ".data" and addr >= va + rawsize:
                    return ".bss"
                return name
        return "outside"

    def kind(self, addr: int, caller: str) -> str:
        """Text targets: same object / other game object / thunk (import) / library; data targets: the section."""
        region = self.region(addr)
        if region != ".text":
            return region
        k = bisect.bisect_right(self.starts, addr) - 1
        obj = self.rows[k][1] if k >= 0 else "?"
        if obj == THUNK_OBJECT:
            return "import thunk"
        if obj == caller:
            return "same object"
        return "other game object" if obj in self.game else "library"


def breakdown(linkdir: Path, expected: dict, relocs: dict, retail_image, our_image, sizes: dict[int, int], game_objects: set[str]) -> dict:
    """Unequal relocated words of the paired functions, by relocation type and what our word's target is.
    rel32 words differ when the displacement differs; dir32 words (absolute addresses) when the address differs."""
    kinds = TargetKinds(linkdir / "BEA.map", game_objects, our_image.sections)
    table: dict[str, dict[str, list[int]]] = {"rel32": {}, "dir32": {}}   # type -> kind -> [words unequal, bytes unequal, words total]
    per_object: dict[str, dict[str, int]] = {}
    wiring = {"same function": 0, "different function": 0, "not a paired function start": 0}

    def visit(obj, addr, ours, retail, mine, retail_addr):
        lower = obj.lower()
        for off, typ in mine:
            if off + OPERAND > min(len(ours), len(retail)):
                continue
            w, r = ours[off:off + 4], retail[off:off + 4]
            word = int.from_bytes(w, "little")
            target = (addr + off + 4 + word) & 0xFFFFFFFF if typ == REL32 else word
            if typ not in (REL32, 0x06):
                continue
            row = table["rel32" if typ == REL32 else "dir32"].setdefault(kinds.kind(target, lower), [0, 0, 0])
            row[2] += 1
            if w != r:
                if kinds.region(target) == ".text":
                    rword = int.from_bytes(r, "little")
                    rtarget = (retail_addr + off + 4 + rword) & 0xFFFFFFFF if typ == REL32 else rword
                    want = {placemap.lookup(expected, n, o) for n, o in kinds.names.get(target, ())} - {None}
                    wiring["not a paired function start" if not want else "same function" if rtarget in want else "different function"] += 1
                row[0] += 1
                row[1] += sum(x != y for x, y in zip(w, r))
                po = per_object.setdefault(obj, {})
                key = ("rel32 " if typ == REL32 else "dir32 ") + kinds.kind(target, lower)
                po[key] = po.get(key, 0) + 1

    res = compare(linkdir, expected, relocs, retail_image, our_image, sizes, visit)
    return {"summary": res, "kinds": table, "per_object": per_object, "wiring": wiring}


def data_pairs(linkdir: Path, expected: dict, relocs: dict, retail_image, our_image, sizes: dict[int, int]) -> list[tuple[int, int, str]]:
    """(our data address, retail data address, calling object) for every DIR32 word whose target lies in our data sections:
    the code's own references pair the two images' data without symbol names."""
    kinds = TargetKinds(linkdir / "BEA.map", set(), our_image.sections)
    out = []

    def visit(obj, addr, ours, retail, mine, retail_addr):
        for off, typ in mine:
            if typ == 0x06 and off + OPERAND <= min(len(ours), len(retail)):
                t = int.from_bytes(ours[off:off + 4], "little")
                if kinds.region(t) in (".rdata", ".data", ".bss"):
                    out.append((t, int.from_bytes(retail[off:off + 4], "little"), obj))

    compare(linkdir, expected, relocs, retail_image, our_image, sizes, visit)
    return out


def data_events(pairs: list[tuple[int, int, str]], kinds: "TargetKinds", retail_regions) -> dict:
    """Runs of constant (ours - retail) offset per data region, in our address order, with the step at each boundary and how
    many words would be equal if every negative step (retail has bytes we lack) were filled with that many bytes."""
    by_region: dict[str, dict[int, set]] = {}
    for t, rt, _obj in pairs:
        by_region.setdefault(kinds.region(t), {}).setdefault(t, set()).add(t - rt)
    words: dict[str, dict[int, int]] = {}
    for t, _rt, _obj in pairs:
        r = kinds.region(t)
        words.setdefault(r, {})[t] = words.setdefault(r, {}).get(t, 0) + 1
    result = {}
    for region, targets in sorted(by_region.items()):
        runs = []   # [first address, last address, offset, words, symbol at first, symbol at last]
        conflicts = 0
        for t in sorted(targets):
            offs = targets[t]
            conflicts += len(offs) > 1
            off = min(offs, key=abs)
            if runs and runs[-1][2] == off:
                runs[-1][1] = t
                runs[-1][3] += words[region][t]
            else:
                runs.append([t, t, off, words[region][t]])
        # The chain: the heaviest run of runs whose offset never increases with the address (a missing byte only ever pushes
        # later data further below retail's address); the others are references to data that is placed elsewhere (or not paired).
        best, prev_i = [r[3] for r in runs], [-1] * len(runs)
        for j in range(len(runs)):
            for i in range(j):
                if runs[i][2] >= runs[j][2] and best[i] + runs[j][3] > best[j]:
                    best[j], prev_i[j] = best[i] + runs[j][3], i
        end = max(range(len(runs)), key=lambda j: best[j])
        chain, j = [], end
        while j >= 0:
            chain.append(j)
            j = prev_i[j]
        chain.reverse()
        total = sum(r[3] for r in runs)
        events, prev = [], 0
        for j in chain:
            first, last, off, w = runs[j]
            events.append({"first": first, "last": last, "offset": off, "step": off - prev, "words": w,
                           "symbol_first": kinds.symbol(first), "symbol_last": kinds.symbol(last)})
            prev = off
        # Sizing the fill: inserting bytes at a boundary moves everything after it, so filling the steps from the section start in
        # address order (a prefix) makes each run equal exactly when the bytes filled so far equal its missing offset.
        # Two different starts. The lowest referenced datum (runs[0]) says how many bytes ours has before the first thing the code
        # reaches; the chain's first run can begin later (the chain is the heaviest non-increasing run and may skip the first
        # runs), and the fill curve is anchored there.
        first_datum_offset = runs[0][2] if runs else 0
        chain_start_excess = max(0, events[0]["offset"]) if events else 0
        curve, add, equal = [], chain_start_excess * -1, 0
        for e in events:
            if e["step"] < 0:
                add += -e["step"]
            if e["offset"] + add == 0:
                equal += e["words"]
            curve.append({"through": e["first"], "symbol": e["symbol_first"], "bytes_filled": add, "equal_words": equal})
        result[region] = {"words": total, "runs": len(runs), "chain_runs": len(chain), "chain_words": sum(events_["words"] for events_ in events),
                          "equal_now": sum(e["words"] for e in events if e["offset"] == 0),
                          "first_datum_offset": first_datum_offset, "chain_start_excess": chain_start_excess, "bytes_to_fill_all_chain_steps": sum(-e["step"] for e in events if e["step"] < 0),
                          "conflicting_targets": conflicts, "events": events, "prefix_fill_curve": curve}
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("linkdir", type=Path)
    ap.add_argument("--expected", type=Path)
    ap.add_argument("--build", type=Path, default=decomp.BUILD)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--data-events", action="store_true", help="runs of constant data offset to retail, with the .bss/.rdata/.data steps")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--breakdown", action="store_true", help="classify the unequal relocated words by what they point at")
    a = ap.parse_args()
    expected = placemap.frozen_expected(a.expected) if a.expected else placemap.expected_by_object()
    relocs = function_relocs(a.build)
    sizes = {addr: f.size for addr, f in decomp.retail_functions().items()}
    retail = PeImage(decomp.SPECIMEN, decomp.SPECIMEN_SHA256)
    ours = PeImage(a.linkdir / "BEA.exe")
    if a.data_events:
        pairs = data_pairs(a.linkdir, expected, relocs, retail, ours, sizes)
        kinds = TargetKinds(a.linkdir / "BEA.map", set(), ours.sections)
        ev = data_events(pairs, kinds, retail.sections)
        for region, d in ev.items():
            print(f"{region}: {d['words']} data-address words; EQUAL at their own address {d['equal_now']} ({100 * d['equal_now'] / max(d['words'], 1):.1f}%); "
                  f"{d['runs']} constant-offset runs; chain {d['chain_runs']} runs / {d['chain_words']} words (off the chain: {d['words'] - d['chain_words']}); "
                  f"the lowest referenced datum sits at offset {d['first_datum_offset']:+d} (ours minus retail); the chain starts with {d['chain_start_excess']} bytes too many; filling every chain step = {d['bytes_to_fill_all_chain_steps']} bytes "
                  f"(chain words can fall while the image improves: the chain is the heaviest non-increasing run; compare equal-at-own-address and the runs)")
            for e in sorted(d["events"], key=lambda e: e["step"])[:a.top]:
                print(f"   {e['first']:#x}..{e['last']:#x} offset {e['offset']:+d} step {e['step']:+d} words {e['words']}  {e['symbol_first']}")
            curve = d["prefix_fill_curve"]
            marks = [c for i, c in enumerate(curve) if i == len(curve) - 1 or c["equal_words"] != curve[i + 1]["equal_words"]]
            print("   fill/remove in address order (bytes inserted so far -> words equal):", [(c["bytes_filled"], c["equal_words"]) for c in marks][:a.top or 12])
        if a.json:
            a.json.write_text(json.dumps(ev, indent=1))
        return
    if a.breakdown:
        game = {p.name.lower() for p in a.build.rglob("*.obj")}
        bd = breakdown(a.linkdir, expected, relocs, retail, ours, sizes, game)
        res = bd["summary"]
    else:
        res = compare(a.linkdir, expected, relocs, retail, ours, sizes)
    print(f"{res['functions']} paired functions, {res['bytes']} bytes compared against retail at each function's own address:")
    print(f"  raw aligned            {res['raw']:>9}  {res['raw_pct']:.2f}%")
    print(f"  rel32 operands masked  {res['rel32']:>9}  {res['rel32_pct']:.2f}%")
    print(f"  all relocations masked {res['all']:>9}  {res['all_pct']:.2f}%   (code identical except addresses)")
    if a.breakdown:
        for typ, rows in bd["kinds"].items():
            print(f"unequal {typ} words, by what our word points at (unequal words / bytes / all words):")
            for kind, (w, b, t) in sorted(rows.items(), key=lambda kv: -kv[1][0]):
                print(f"  {kind:18} {w:>8} {b:>8} {t:>8}")
        print("unequal words pointing into .text: is our target the function retail's word points at?")
        for k, v in bd["wiring"].items():
            print(f"  {k:28} {v:>8}")
        res = dict(res, breakdown=bd["kinds"], wiring=bd["wiring"], per_object_unequal=bd["per_object"])
    if a.json:
        a.json.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
