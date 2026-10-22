#!/usr/bin/env python3
"""Which object holds each float constant (__real@ COMDAT) in retail, against ours.

    python3 tools/constowner.py [--tree DIR] [--link DIR] [--build DIR] [--json FILE] [--sites]

Every input comes from one tree: its source annotations and config, its build/ objects and its link (default
TREE/local-data/link). --tree defaults to the tree that holds --link (a DIR/local-data/link folder), else this checkout;
--build and --link override one input each. Measure another checkout with --tree, e.g.
    python3 tools/constowner.py --tree ../OTHER-CHECKOUT --sites

Output, in order: the summary line; "== missing code" and "== emission" (constants held by another object than
retail's); "== one name, two retail copies" (each name retail keeps at two addresses, with our sites by the copy their
instruction addresses; --sites prints every site in full, one per line, instead of a shortened list). The JSON
(--json) carries all three under "mismatches" and "split".

A float or double literal compiles to a COMDAT constant (__real@4@... / __real@8@...) that every object using it
defines; the linker keeps the first definer in link order, so the object that holds a constant in .rdata says which
objects' code used it. Each constant the matched code references is pinned at its retail address (the retail operand
minus the instruction's addend). Its retail owner is the object our map gives the pinned .rdata items on both sides
of it in retail's order ("boundary" when the two differ); its owner in ours is the map's. For each constant whose
owners differ, the tool reports whether our build of the retail owner references the constant:
- yes: both objects use it and the first definer differs (link order or emission),
- no: retail's object had code that used it and ours does not: a function we have not written (or one /OPT:REF
  dropped from retail, whose constants still stand), or our code spells the value another way (`x / 3.0f` names the
  extended-precision reciprocal, `x * (1.0f / 3.0f)` the float-folded one: same code, another COMDAT).
It also lists each name that retail keeps at two addresses, with our sites by the copy their instruction addresses:
sites of one name at two retail copies had two spellings in retail.
Reads the tree's build/*.obj, sources and config, its link and the specimen at run time.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decomp  # noqa: E402
import placemap  # noqa: E402
from binfmt import PeImage, parse_coff  # noqa: E402

RDATA_LO, RDATA_HI = 0x5D8000, 0x622000
MAP_DATA = re.compile(r"^\s*0002:[0-9a-f]{8}\s+(\S+)\s+([0-9a-f]{8})\s+(?:f\s+)?(?:i\s+)?(\S+)")


def tree_of(link: Path | None) -> Path:
    """The tree a link folder belongs to: DIR for DIR/local-data/link, else this checkout."""
    if link is not None and link.name == "link" and link.parent.name == "local-data":
        return link.parent.parent
    return decomp.ROOT


def use_tree(tree: Path, build: Path | None = None) -> None:
    """Point the decomp module (and so placemap) at TREE: its sources, annotations, config and objects."""
    tree = tree.resolve()
    decomp.ROOT, decomp.CONFIG = tree, tree / "config"
    decomp.BUILD = (build or tree / "build").resolve()
    decomp.PCH_SOURCE = tree / "src/pch.cpp"


def retail_owner(retail_addr: int, pinned: list[tuple[int, str]]) -> str:
    """PINNED: (retail address, our owner object) of the other pinned .rdata items, sorted. The object both
    neighbours belong to, or 'boundary A|B' when they differ."""
    starts = [a for a, _o in pinned]
    k = bisect.bisect_left(starts, retail_addr)
    before = pinned[k - 1][1] if k > 0 else None
    k2 = bisect.bisect_right(starts, retail_addr)
    after = pinned[k2][1] if k2 < len(pinned) else None
    if before == after or after is None:
        return before or "?"
    if before is None:
        return after
    return f"boundary {before}|{after}"


def classify(retail_own: str, our_own: str, users: set[str], rank: dict | None = None) -> str:
    """The mismatch's class: 'same' when the owners agree; 'emission' when our build of retail's owner uses the
    constant too; 'missing code' when it does not. A constant between two objects' items ('boundary A|B') belongs to
    either, or to an object between them in link order (RANK: object -> position) that has no other pinned item:
    ours agrees when it is any of those, and it is missing code when neither neighbour uses it."""
    if retail_own.lower() == our_own.lower():
        return "same"
    owners = retail_own.split(" ", 1)[1].lower().split("|") if retail_own.startswith("boundary") else [retail_own.lower()]
    if our_own.lower() in owners:
        return "same"
    if rank and len(owners) == 2 and all(o in rank for o in owners) and our_own.lower() in rank:
        lo, hi = sorted(rank[o] for o in owners)
        if lo < rank[our_own.lower()] < hi:
            return "same"
    return "emission" if any(o in users for o in owners) else "missing code"


def value_of(name: str) -> str:
    """__real@4@3ffecccccd0000000000 -> its value (the mangled name holds an 80-bit extended number)."""
    m = re.match(r"__real@(\d)@([0-9a-f]{20})", name)
    if not m:
        return "?"
    raw = int(m.group(2), 16)
    sign, exp, mant = raw >> 79, (raw >> 64) & 0x7FFF, raw & ((1 << 64) - 1)
    if exp == 0 and mant == 0:
        return "0"
    v = mant / float(1 << 63) * 2.0 ** (exp - 16383)
    return f"{-v if sign else v:.9g}"


def run(linkdir: Path) -> dict:
    R = PeImage(decomp.SPECIMEN, decomp.SPECIMEN_SHA256)
    exp = placemap.expected_by_object()
    ours_code = {(n, o.lower()): a for a, n, o, _i in placemap.code_symbols(linkdir / "BEA.map")}
    our_owner, our_addr = {}, {}
    for line in (linkdir / "BEA.map").read_text(errors="replace").splitlines():
        m = MAP_DATA.match(line)
        if m:
            our_owner.setdefault(m.group(1), m.group(3).lower())
            our_addr.setdefault(m.group(1), int(m.group(2), 16))
    pins: dict = collections.defaultdict(collections.Counter)
    users: dict = collections.defaultdict(set)          # constant -> objects whose code references it
    sites: dict = collections.defaultdict(lambda: collections.defaultdict(set))   # constant -> retail address -> sites
    for obj in sorted(decomp.BUILD.rglob("*.obj")):
        on = obj.name.lower()
        try:
            c = parse_coff(obj)
        except Exception:
            continue
        for secnum, symbol in decomp.function_sections(c):
            r = exp.get((symbol, on))
            data = c.sections[secnum].data
            for off, si, typ in c.sections[secnum].relocs:
                name = c.symbols[si].name
                if typ != 6:
                    continue
                if name.startswith("__real@"):
                    users[name].add(on)
                if r is None or (symbol, on) not in ours_code:
                    continue
                if name in our_owner:
                    add = struct.unpack("<I", data[off:off + 4])[0]
                    ra = struct.unpack("<I", R.read(r + off, 4))[0] - add
                    if RDATA_LO <= ra < RDATA_HI:
                        pins[name][ra] += 1
                        sites[name][ra].add(f"{on}:{symbol}")
    pinned_all = {n: c.most_common(1)[0][0] for n, c in pins.items()}
    rank = {}
    for line in (linkdir / "link.rsp").read_text(errors="replace").splitlines():
        name = line.strip().strip('"').replace("\\", "/").rsplit("/", 1)[-1].lower()
        if name.endswith(".obj"):
            rank.setdefault(name, len(rank))
    rows = []
    for name, ra in sorted(pinned_all.items(), key=lambda kv: kv[1]):
        if not name.startswith("__real@"):
            continue
        others = sorted((a, our_owner[n]) for n, a in pinned_all.items() if n != name and n in our_owner)
        rown = retail_owner(ra, others)
        oown = our_owner.get(name, "?")
        cls = classify(rown, oown, users.get(name, set()), rank)
        if cls != "same":
            rows.append({"constant": name, "value": value_of(name), "retail": f"{ra:08x}",
                         "ours": f"{our_addr.get(name, 0):08x}", "retail_owner": rown, "our_owner": oown,
                         "retail_owner_uses_it": rown.lower() in users.get(name, set()), "class": cls,
                         "users": sorted(users.get(name, set()))})
    split = [{"constant": n, "value": value_of(n),
               "copies": {f"{a:08x}": sorted(v) for a, v in sorted(sites[n].items())}}
             for n in sorted(sites) if n.startswith("__real@") and len(sites[n]) > 1]
    return {"constants_pinned": sum(1 for n in pinned_all if n.startswith("__real@")), "mismatches": rows,
            "split": split}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__.split("\n\n")[2],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", type=Path, help="the checkout measured (default: the tree holding --link, else this one)")
    ap.add_argument("--link", type=Path, help="a tools/link.py output folder (default: TREE/local-data/link)")
    ap.add_argument("--build", type=Path, help="the compiled objects (default: TREE/build)")
    ap.add_argument("--json", type=Path, help="write the mismatches and the two-copy names as JSON")
    ap.add_argument("--sites", action="store_true", help="print every site of each two-copy name, one per line")
    a = ap.parse_args()
    link = a.link.resolve() if a.link else None
    tree = (a.tree or tree_of(link)).resolve()
    use_tree(tree, a.build)
    link = link or tree / "local-data/link"
    print(f"tree {tree} | build {decomp.BUILD} | link {link}")
    out = run(link)
    rows = out["mismatches"]
    cls = collections.Counter(r["class"] for r in rows)
    print(f"{out['constants_pinned']} float constants pinned; {len(rows)} held by another object than retail's: "
          + ", ".join(f"{k} {v}" for k, v in cls.most_common()))
    for k in ("missing code", "emission"):
        sel = [r for r in rows if r["class"] == k]
        if sel:
            print(f"== {k} ({len(sel)})")
            for r in sel:
                print(f"  {r['retail']} {r['value']:>12s}  retail {r['retail_owner'][:40]:40s} ours {r['our_owner']:24s}"
                      f" users {','.join(r['users'])[:60]}")
    if out["split"]:
        print(f"== one name, two retail copies ({len(out['split'])}): our sites by the retail copy they address")
        for r in out["split"]:
            print(f"  {r['value']:>12s} {r['constant']}")
            for addr, ss in r["copies"].items():
                if a.sites:
                    print(f"    {addr} {len(ss):3d}")
                    for x in ss:
                        print(f"      {x}")
                else:
                    print(f"    {addr} {len(ss):3d}  {', '.join(ss)[:120]}")
    if a.json:
        a.json.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
