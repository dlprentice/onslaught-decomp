#!/usr/bin/env python3
"""Where our .text layout departs from retail's: walk both images by matched function and list each place where our
address offset to retail changes.

    python3 tools/placemap.py LINKDIR [--expected EXPECTED.json] [--top N] [--json FILE]

LINKDIR is a tools/link.py output folder (its BEA.map). Retail addresses come from the current source's FUNCTION
annotations, resolved to symbols against this checkout's build/*.obj at run time (as the checker does; run a check
first), and are keyed by symbol and object, so a rename cannot drop a pair and statics or initializer funclets of the
same name in different objects stay apart. --expected reads a frozen tools/linkcmp.py --write-expected file instead
(symbol -> address, any object). A function pairs when its symbol and object are in both and no other expected entry
shares its retail address. The pairs, in retail order, keep the longest run that is in order in our image too (the chain); the others sit
elsewhere in our order (out of order).

Objects: each object's contributions lie together and in the same order in both images, so an object's region runs
from its first own (out-of-line) chain function to the next object's. The difference of region lengths is that object's
size difference (extra or missing code, initializer funclets, padding); the differences add up to the offset change, and
order inside an object cannot affect them. Two neighbours with opposite differences usually mark a boundary that moved
because an object's own functions are out of order at its start. Sorted by size, the list is the to-do list for the
executable's byte identity.

Events: between two neighbours on the chain, a change of offset (ours minus retail) is a placement event; each lists
what lies between on each side (our symbols with no retail counterpart there, retail functions with none of ours
there), with items of the same size on both sides cancelled.
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


def code_symbols(map_path: Path) -> list[tuple[int, str, str, bool]]:
    """Our .text publics (section 0001), by address: (address, name, object, inline COMDAT)."""
    out = []
    for line in map_path.read_text(errors="replace").splitlines():
        m = linkcmp.MAP_LINE.match(line)
        if m and m.group(1) == "0001":
            out.append((int(m.group(4), 16), m.group(3), m.group(7) or "", bool(m.group(6))))
    return sorted(out)


def expected_by_object() -> dict[tuple[str, str | None], int]:
    """(symbol, object file name, lower case) -> retail address, from the source annotations and the built objects."""
    objects = {}
    for src in sorted(list((decomp.ROOT / "src").rglob("*.cpp")) + list((decomp.ROOT / "src").rglob("*.c"))):
        obj = decomp.BUILD / src.relative_to(decomp.ROOT / "src").with_suffix(".obj")
        if obj.exists():
            objects[src] = obj
    results, _checker = decomp.check(objects)
    object_of = {str(src.relative_to(decomp.ROOT)): obj.name.lower() for src, obj in objects.items()}
    return {(r.symbol, object_of.get(r.source.split(":")[0])): r.address
            for r in results if r.symbol and r.status != "unplaced"}


def frozen_expected(path: Path) -> dict[tuple[str, str | None], int]:
    """A tools/linkcmp.py --write-expected file: symbol -> address, for whichever object defines the symbol."""
    return {(n, None): a for n, a in json.loads(path.read_text())["functions"].items()}


def lookup(expected: dict[tuple[str, str | None], int], name: str, obj: str) -> int | None:
    """The symbol's retail address in this object; else, for a symbol whose every entry names one address (an
    external, or an inline annotated where another object's copy survived the link), that address."""
    a = expected.get((name, obj.lower()))
    if a is not None:
        return a
    found = {v for (n, _o), v in _by_name(expected).get(name, ())}
    return found.pop() if len(found) == 1 else None


_name_index: dict[int, dict[str, list]] = {}


def _by_name(expected: dict) -> dict[str, list]:
    key = id(expected)
    if key not in _name_index:
        index: dict[str, list] = {}
        for (n, o), v in expected.items():
            index.setdefault(n, []).append(((n, o), v))
        _name_index.clear()
        _name_index[key] = index
    return _name_index[key]


def chain(pairs: list[tuple[int, int, str]]) -> list[int]:
    """Indices of the longest run of pairs (sorted by retail address) whose our-addresses also increase."""
    tails: list[int] = []
    tail_idx: list[int] = []
    prev = [-1] * len(pairs)
    for i, (_r, o, _n) in enumerate(pairs):
        k = bisect.bisect_left(tails, o)
        if k == len(tails):
            tails.append(o)
            tail_idx.append(i)
        else:
            tails[k] = o
            tail_idx[k] = i
        prev[i] = tail_idx[k - 1] if k else -1
    out, i = [], tail_idx[-1] if tail_idx else -1
    while i >= 0:
        out.append(i)
        i = prev[i]
    return out[::-1]


def placement(linkdir: Path, exp: dict[tuple[str, str | None], int]) -> dict:
    ours = code_symbols(linkdir / "BEA.map")
    our_addr: dict[tuple[str, str], int] = {}  # (name, object) -> our address
    paired: dict[tuple[str, str], int] = {}    # (name, object) -> retail address
    for a, n, o, _i in ours:
        if (n, o) not in our_addr:
            our_addr[(n, o)] = a
            r = lookup(exp, n, o)
            if r is not None:
                paired[(n, o)] = r
    our_starts = [a for a, _n, _o, _i in ours]
    names_at: dict[int, int] = {}
    for a in exp.values():
        names_at[a] = names_at.get(a, 0) + 1
    retail = decomp.retail_functions()
    rstarts = sorted(retail)
    pairs = sorted((a, our_addr[k], k) for k, a in paired.items()
                   if names_at[a] == 1 and not k[0].startswith(("_$", ".")))
    keep = chain(pairs)
    on_chain = {pairs[i][2] for i in keep}
    retail_named = set(paired.values())

    def our_span(addr: int) -> int:
        k = bisect.bisect_right(our_starts, addr)
        return (our_starts[k] - addr) if k < len(our_starts) else 0

    def retail_span(addr: int) -> int:
        k = bisect.bisect_right(rstarts, addr)
        return (rstarts[k] - addr) if k < len(rstarts) else retail[addr].size if addr in retail else 0

    events = []
    for i, j in zip(keep, keep[1:]):
        (ra, oa, na), (rb, ob, nb) = pairs[i], pairs[j]
        step = (ob - oa) - (rb - ra)
        if not step:
            continue
        lo, hi = bisect.bisect_right(our_starts, oa), bisect.bisect_left(our_starts, ob)
        ours_only = [(n, our_span(a), o) for a, n, o, _i in ours[lo:hi]
                     if not ra < (lookup(exp, n, o) or 0) < rb]
        rlo, rhi = bisect.bisect_right(rstarts, ra), bisect.bisect_left(rstarts, rb)
        retail_only = [(retail[a].name, retail_span(a)) for a in rstarts[rlo:rhi] if a not in retail_named]
        sizes = [s for _n, s in retail_only]                  # same-size items on both sides (unnamed initializer
        kept = []                                              # funclets, renamed functions) cancel out
        for item in ours_only:
            if item[1] in sizes:
                sizes.remove(item[1])
            else:
                kept.append(item)
        rest = []
        for n, sz in retail_only:
            if sz in sizes:
                sizes.remove(sz)
                rest.append((n, sz))
        ours_only, retail_only = kept, rest
        events.append({"step": step, "retail": [f"{ra:08x}", f"{rb:08x}"], "ours": [f"{oa:08x}", f"{ob:08x}"],
                       "after": na[0], "before": nb[0], "object": na[1], "next_object": nb[1],
                       "after_span": [our_span(oa), retail_span(ra)],
                       "ours_only": ours_only[:12], "ours_only_bytes": sum(s for _n, s, _o in ours_only),
                       "retail_only": retail_only[:12], "retail_only_bytes": sum(s for _n, s in retail_only)})
    misplaced = [(f"{r:08x}", f"{o:08x}", k[0]) for r, o, k in pairs if k not in on_chain]
    first = pairs[keep[0]] if keep else None
    last = pairs[keep[-1]] if keep else None
    # Objects lie contiguously and in the same order in both images, so an object's region runs from its first own
    # (out-of-line) function to the next object's first. Comparing region lengths gives each object's size difference;
    # the differences add up to the offset change, and order inside an object cannot affect them.
    inline = {(n, o) for _a, n, o, i in ours if i}
    first_r: dict[str, int] = {}
    first_o: dict[str, int] = {}
    count: dict[str, int] = {}
    off_chain: dict[str, int] = {}
    for r, o, k in pairs:
        x = k[1]
        if k in inline or not x:
            continue
        count[x] = count.get(x, 0) + 1
        off_chain[x] = off_chain.get(x, 0) + (k not in on_chain)
        if k in on_chain:                     # chain functions keep one order in both images
            first_r[x] = min(first_r.get(x, r), r)
            first_o[x] = min(first_o.get(x, o), o)
    order_r = sorted(first_r, key=first_r.get)
    order_o = sorted(first_o, key=first_o.get)
    regions = []
    if order_r != order_o:
        print("object order differs at", [(x, y) for x, y in zip(order_r, order_o) if x != y][:5], file=sys.stderr)
    if order_r == order_o:
        for x, y in zip(order_r, order_r[1:]):
            lr, lo = first_r[y] - first_r[x], first_o[y] - first_o[x]
            regions.append({"object": x, "delta": lo - lr, "retail": [f"{first_r[x]:08x}", f"{first_r[y]:08x}"],
                            "ours": [f"{first_o[x]:08x}", f"{first_o[y]:08x}"], "own_paired": count[x],
                            "out_of_order": off_chain[x]})
    object_order_differs = order_r != order_o
    return {"pairs": len(pairs), "chain": len(keep), "misplaced": misplaced, "events": events,
            "regions": regions, "object_order_differs": object_order_differs,
            "start_offset": (first[1] - first[0]) if first else 0, "end_offset": (last[1] - last[0]) if last else 0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("linkdir", type=Path)
    ap.add_argument("--expected", type=Path, help="a frozen linkcmp --write-expected file (default: the source now)")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    r = placement(a.linkdir.resolve(), frozen_expected(a.expected) if a.expected else expected_by_object())
    ev = r["events"]
    print(f"{r['pairs']} paired functions, {r['chain']} on the in-order chain, {len(r['misplaced'])} misplaced; "
          f"{len(ev)} placement events; offset {r['start_offset']:+d} at the first pair, "
          f"{r['end_offset']:+d} at the last")
    print(f"steps: {sum(e['step'] for e in ev if e['step'] > 0):+d} bytes ours larger, "
          f"{sum(e['step'] for e in ev if e['step'] < 0):+d} ours smaller")
    reg = r["regions"]
    if r["object_order_differs"]:
        print("objects are not in the same order in both images: no per-object regions")
    else:
        diff = [x for x in reg if x["delta"]]
        print(f"objects whose region differs in size: {len(diff)} of {len(reg)}, net {sum(x['delta'] for x in reg):+d} "
              f"bytes (a region runs from the object's first own function to the next object's):")
        for x in sorted(diff, key=lambda x: -abs(x["delta"]))[:a.top]:
            print(f"  {x['delta']:+7d}  {x['object']:34} retail {x['retail'][0]}..{x['retail'][1]}  "
                  f"ours {x['ours'][0]}..{x['ours'][1]}  "
                  f"({x['own_paired']} own paired, {x['out_of_order']} out of order)")
        moved = [x for x in reg if x["out_of_order"]]
        print(f"objects with own functions in another order: {len(moved)}, "
              f"{sum(x['out_of_order'] for x in moved)} functions")
    print("events:")
    for e in sorted(ev, key=lambda e: -abs(e["step"]))[:a.top]:
        span = e["after_span"]
        print(f"{e['step']:+7d}  retail {e['retail'][0]}..{e['retail'][1]}  ours {e['ours'][0]}..{e['ours'][1]}  "
              f"{e['object']}  after {e['after'][:60]} ({span[0]} ours, {span[1]} retail)")
        if e["ours_only"]:
            print(f"           ours only {e['ours_only_bytes']} bytes: "
                  + ", ".join(f"{n[:40]} {s}" for n, s, _o in e["ours_only"][:4]))
        if e["retail_only"]:
            print(f"           retail only {e['retail_only_bytes']} bytes: "
                  + ", ".join(f"{n[:40]} {s}" for n, s in e["retail_only"][:4]))
    if a.json:
        a.json.write_text(json.dumps(r, indent=1) + "\n")


if __name__ == "__main__":
    main()
