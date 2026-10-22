#!/usr/bin/env python3
"""Compare every initialised data symbol the matched code reaches with the pinned specimen, value for value.

    python3 tools/datacontent.py [--link DIR] [--json FILE]

Each DIR32 relocation of a matched function that targets an initialised data symbol (.data or .rdata, literals and
other COMDAT constants included) pins that symbol at its retail address: the retail operand minus the instruction's
own addend. Pinned symbols pin the symbols their own relocations reach in the same way, to a fixed point. Each pinned
symbol is compared with retail over its exact size from our COFF (to the next symbol in its section, or the section's
end). A differing byte inside one of our relocated fields is a reference; the reference is right when the retail
value is the target's retail address plus the same addend, the target being a matched function or a pinned symbol.
Any other differing byte is content: a wrong initial value or string. Reads this checkout's build/*.obj, the link in
DIR (default local-data/link) and the specimen at run time; writes only FILE.
"""
from __future__ import annotations

import argparse
import collections
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decomp  # noqa: E402
import placemap  # noqa: E402
from binfmt import PeImage, parse_coff  # noqa: E402
from inventory import coff_extent  # noqa: E402

DATA_LO, DATA_HI_DEFAULT = 0x5D8000, 0x661000   # .rdata start .. end of retail's initialised .data


def classify(retail: bytes, ours: bytes, relocated: set[int]) -> tuple[int, int]:
    """(bytes inside one of our relocated 4-byte fields, other differing bytes) between two equal-length images of
    a symbol; RELOCATED holds the fields' start offsets."""
    refs = content = 0
    for i in range(min(len(retail), len(ours))):
        if retail[i] == ours[i]:
            continue
        if any(o <= i < o + 4 for o in relocated):
            refs += 1
        else:
            content += 1
    return refs, content


def run(linkdir: Path) -> dict:
    R = PeImage(decomp.SPECIMEN, decomp.SPECIMEN_SHA256)
    C = PeImage(linkdir / "BEA.exe")
    init_end = next(s[1] + s[4] for s in R.sections if s[0] == ".data")
    objects = {}
    for src in sorted(list((decomp.ROOT / "src").rglob("*.cpp")) + list((decomp.ROOT / "src").rglob("*.c"))):
        obj = decomp.BUILD / src.relative_to(decomp.ROOT / "src").with_suffix(".obj")
        if obj.exists():
            objects[src] = obj
    results, _ = decomp.check(objects)
    object_of = {str(src.relative_to(decomp.ROOT)): obj.name.lower() for src, obj in objects.items()}
    exp = {(r.symbol, object_of.get(r.source.split(":")[0])): r.address
           for r in results if r.symbol and r.status == "match"}
    fn_retail = collections.defaultdict(set)
    for (n, _o), a in exp.items():
        fn_retail[n].add(a)
    coffs = {obj.name.lower(): parse_coff(obj) for obj in objects.values()}
    ours_code = {(n, o.lower()): a for a, n, o, _i in placemap.code_symbols(linkdir / "BEA.map")}
    pins: dict = collections.defaultdict(collections.Counter)   # (symbol, object) -> Counter(retail address)
    where: dict = {}                                            # (symbol, object) -> (COFF, symbol)
    for on, c in coffs.items():
        for secnum, symbol in decomp.function_sections(c):
            r = exp.get((symbol, on))
            if r is None:
                continue
            data = c.sections[secnum].data
            for off, si, typ in c.sections[secnum].relocs:
                s = c.symbols[si]
                if typ != 6 or s.section <= 0 or coff_extent(c, s) is None:
                    continue
                add = struct.unpack("<I", data[off:off + 4])[0]
                key = (s.name, on)
                pins[key][struct.unpack("<I", R.read(r + off, 4))[0] - add] += 1
                where[key] = (c, s)
    by_name = collections.defaultdict(list)
    for on, c in coffs.items():
        for s in c.symbols.values():
            if s.section > 0 and s.storage in (2, 3) and not s.name.startswith("."):
                by_name[s.name].append((on, c, s))
    done: set = set()
    for _round in range(8):                                     # through the pinned symbols' own relocations
        new = 0
        for key, cnt in list(pins.items()):
            if key in done:
                continue
            done.add(key)
            ra = cnt.most_common(1)[0][0]
            if not DATA_LO <= ra < init_end:
                continue
            c, s = where[key]
            _size, rels = coff_extent(c, s)
            for o, si, add in rels:
                target = c.symbols[si]
                cands = [x for x in by_name.get(target.name, []) if x[2].storage == 2 or x[0] == key[1]]
                if len(cands) != 1 or coff_extent(cands[0][1], cands[0][2]) is None:
                    continue
                k2 = (target.name, cands[0][0])
                if k2 not in pins:
                    new += 1
                pins[k2][struct.unpack("<I", R.read(ra + o, 4))[0] - add] += 1
                where[k2] = (cands[0][1], cands[0][2])
        if not new:
            break
    pinned = {k: c.most_common(1)[0][0] for k, c in pins.items()}
    by_target = collections.defaultdict(set)
    for (n, _o), a in pinned.items():
        by_target[n].add(a)
    stats = collections.Counter()
    content = []
    for key, ra in pinned.items():
        if not DATA_LO <= ra < init_end:
            continue
        c, s = where[key]
        size, rels = coff_extent(c, s)
        if not 0 < size <= 65536:
            continue
        ours = c.sections[s.section].data[s.value:s.value + size]
        retail = R.read(ra, size)
        stats["checked"] += 1
        stats["bytes"] += size
        if retail == ours:
            stats["equal"] += 1
            continue
        refs, diff = classify(retail, ours, {o for o, _i, _a in rels})
        if diff:
            content.append({"symbol": key[0], "object": key[1], "retail": f"{ra:08x}", "size": size,
                            "content_bytes": diff})
            continue
        stats["reference-only"] += 1
        for o, si, add in rels:
            if o + 4 > size:
                continue
            rv = struct.unpack("<I", retail[o:o + 4])[0]
            name = c.symbols[si].name
            targets = fn_retail.get(name) or by_target.get(name)
            if not targets:
                stats["references into unpinned targets"] += 1
            elif any(rv == t + add for t in targets):
                stats["references right"] += 1
            else:
                stats["references WRONG"] += 1
                content.append({"symbol": key[0], "object": key[1], "retail": f"{ra:08x}", "size": size,
                                "wrong_reference_at": o, "target": name})
    return {"pinned": len(pinned), "stats": dict(stats), "content": content}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--link", type=Path, default=decomp.ROOT / "local-data/link", help="a tools/link.py output folder")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    out = run(a.link.resolve())
    s = out["stats"]
    print(f"{out['pinned']} pinned data symbols; {s.get('checked', 0)} initialised ones compared "
          f"({s.get('bytes', 0):,} bytes): {s.get('equal', 0)} equal, {s.get('reference-only', 0)} differing only in "
          f"references ({s.get('references right', 0)} right, {s.get('references WRONG', 0)} wrong, "
          f"{s.get('references into unpinned targets', 0)} into unpinned targets); "
          f"{len(out['content'])} with a content difference")
    for x in out["content"][:40]:
        print(" ", x)
    if a.json:
        a.json.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
