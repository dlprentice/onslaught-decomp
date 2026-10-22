#!/usr/bin/env python3
"""Measure how close a linked BEA.exe's data layout is to retail's, from the linker's /MAP publics and the symbols the
matched code implies (tools/linkcmp.py --write-expected): where objects sit, and how their globals are ordered.

    python3 tools/dataorder.py BEA.map EXPECTED.json [--json OUT.json] [--objects N] [--section .data]

linkcmp.py compares bytes at equal addresses and counts symbols at their retail address; both read zero once the layout
shifts. This reads order instead. For every symbol in the map that the matched code pins to a retail data address
(0x5d8000 and up: .rdata, .data, .bss), per retail section:

  exact       the symbol sits at its retail address
  order       the longest run of symbols that are in retail's relative order when sorted by candidate address
  objects     the same for objects: each object is placed by the lowest retail (and candidate) address of its pinned
              symbols; 'order' is the longest run of objects in retail's order
  within      among objects with two or more pinned symbols, the share of adjacent symbol pairs (by candidate
              address) that retail also has adjacent-in-order, and the objects whose own symbols are reordered
  spread      an object's pinned symbols should be contiguous in retail: the other objects' symbols that fall between
              its first and last pinned symbol (retail's view) show where an object is split or interleaved

--objects N lists the first N objects, in retail order, where the candidate order breaks. Reads only; runs nothing.
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from pathlib import Path

DATA_START = 0x5D8000
SECTIONS = [(".rdata", 0x5D8000, 0x622000), (".data", 0x622000, 0x9D5000)]    # retail sections; .bss is merged into .data
MAP_LINE = re.compile(r"^\s*([0-9a-fA-F]{4}):([0-9a-fA-F]{8})\s+(\S+)\s+([0-9a-fA-F]{8})\s+(f\s+)?(i\s+)?(\S+)?")


def read_map(path: Path) -> dict[str, tuple[int, str]]:
    """{name: (address, object)}; a file-local name defined in several objects is also keyed 'object-stem:name' (the
    form tools/linkcmp.py --write-expected uses for them)."""
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        m = MAP_LINE.match(line)
        if m and m.group(1) != "0000":
            obj = (m.group(7) or "").split(":")[-1].lower()
            rec = (int(m.group(4), 16), obj)
            out[m.group(3)] = rec
            out[obj[:-4] + ":" + m.group(3)] = rec if obj.endswith(".obj") else rec
    return out


def lis(values: list[int]) -> int:
    tails: list[int] = []
    for v in values:
        i = bisect.bisect_left(tails, v)
        tails[i:i + 1] = [v]
    return len(tails)


def rows_of(publics: dict[str, tuple[int, str]], implied: dict[str, int]):
    """(name, object, candidate address, retail address) for symbols both pinned and linked into data."""
    rows = []
    for name, want in implied.items():
        if want < DATA_START:
            continue
        key = name
        if ":" in name and not name.startswith("?"):
            key = name.split(":", 1)[0].lower() + ":" + name.split(":", 1)[1]
        if key not in publics:
            continue
        addr, obj = publics[key]
        if addr >= DATA_START and obj:
            rows.append((name, obj, addr, want))
    return rows


def section_of(retail: int) -> str:
    for name, lo, hi in SECTIONS:
        if lo <= retail < hi:
            return name
    return "other"


def measure(rows, top: int = 0) -> dict:
    out = {}
    for sec, _lo, _hi in SECTIONS:
        r = [x for x in rows if section_of(x[3]) == sec]
        if not r:
            continue
        by_cand = sorted(r, key=lambda x: x[2])
        res = {"symbols": len(r), "exact": sum(x[2] == x[3] for x in r),
               "order": lis([x[3] for x in by_cand])}
        objs: dict[str, list] = {}
        for x in r:
            objs.setdefault(x[1], []).append(x)
        lo_r = {o: min(x[3] for x in v) for o, v in objs.items()}
        lo_c = {o: min(x[2] for x in v) for o, v in objs.items()}
        by_obj_c = sorted(objs, key=lambda o: lo_c[o])
        res["objects"] = {"count": len(objs), "order": lis([lo_r[o] for o in by_obj_c])}
        # within-object: pairs adjacent by candidate address, in retail's order?
        pairs = ok = 0
        reordered = []
        for o, v in objs.items():
            if len(v) < 2:
                continue
            s = sorted(v, key=lambda x: x[2])
            good = sum(a[3] < b[3] for a, b in zip(s, s[1:]))
            pairs += len(s) - 1
            ok += good
            if good != len(s) - 1:
                reordered.append((o, len(s), good))
        res["within"] = {"pairs": pairs, "in_order": ok, "objects_reordered": len(reordered),
                         "worst": sorted(reordered, key=lambda t: t[2] - t[1])[:8]}
        # spread: retail-sorted symbols; for each object, foreign symbols between its first and last pinned symbol
        by_retail = sorted(r, key=lambda x: x[3])
        pos = {id(x): i for i, x in enumerate(by_retail)}
        inter = []
        for o, v in objs.items():
            a, b = min(pos[id(x)] for x in v), max(pos[id(x)] for x in v)
            foreign = (b - a + 1) - len(v)
            if foreign > 0:
                inter.append((foreign, o, len(v)))
        inter.sort(reverse=True)
        res["spread"] = {"objects_interleaved": len(inter), "foreign_symbols": sum(t[0] for t in inter),
                         "worst": [(o, n, f) for f, o, n in inter[:8]]}
        if top:
            seq = sorted(objs, key=lambda o: lo_r[o])
            cpos = {o: i for i, o in enumerate(by_obj_c)}
            breaks = []
            top_obj = None    # the object furthest along in the candidate among those before this one in retail's order
            for o in seq:
                if top_obj is not None and cpos[o] < cpos[top_obj]:
                    breaks.append((o, top_obj, f"{lo_r[o]:08x}", f"{lo_c[o]:08x}"))
                    if len(breaks) >= top:
                        break
                elif top_obj is None or cpos[o] > cpos[top_obj]:
                    top_obj = o
            res["first_breaks"] = breaks
        out[sec] = res
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("map", type=Path)
    ap.add_argument("expected", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--objects", type=int, default=0)
    a = ap.parse_args()
    implied = json.loads(a.expected.read_text())["implied"]
    rows = rows_of(read_map(a.map), implied)
    rep = measure(rows, a.objects)
    for sec, r in rep.items():
        o, w, s = r["objects"], r["within"], r["spread"]
        print(f"{sec}: {r['symbols']} pinned symbols; exact {r['exact']}; in retail order {r['order']}; "
              f"objects {o['count']} (in order {o['order']}); within-object pairs {w['in_order']} of {w['pairs']} "
              f"({w['objects_reordered']} objects reordered); interleaved objects {s['objects_interleaved']} "
              f"({s['foreign_symbols']} foreign symbols inside them)")
        for t in w["worst"][:5]:
            print(f"    reordered {t[0]}: {t[2]} of {t[1] - 1} pairs in order")
        for t in s["worst"][:5]:
            print(f"    interleaved {t[0]}: {t[1]} symbols with {t[2]} foreign inside")
        for t in r.get("first_breaks", []):
            print(f"    order break: {t[0]} (retail {t[2]}, candidate {t[3]}) sits before {t[1]} in the candidate")
    if a.json:
        a.json.write_text(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
