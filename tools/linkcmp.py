#!/usr/bin/env python3
"""Compare a linked BEA.exe with the pinned retail specimen: one number per stage of the link route.

    python3 tools/linkcmp.py CANDIDATE.exe [--map CANDIDATE.map --expected EXPECTED.json] [--json OUT.json] [--diffs N]
    python3 tools/linkcmp.py --write-expected EXPECTED.json      # from this checkout's build/*.obj (run a check first)

Header: every optional-header and file-header field, the timestamp masked (it records the link time).
Sections: for each retail section, the bytes the candidate holds at the same virtual addresses (as loaded: a
section's tail past its raw data reads as zero), equal or not, and the first differing ranges.
Symbols (with the linker's /MAP file): each compiled function's decorated name against its retail address, and each
symbol the matched code's relocations imply (decomp.check's discovered map) against that address.
Imports: the descriptor (DLL) order, and per DLL its entries in order (name or ordinal, hint) and IAT slot addresses.
Resources: the resource tree's leaves in order (type/name/language path, data bytes, code page), and the resource
image with its data RVAs taken relative to the section, so a resource section at another address can still be equal.
Reads only; runs nothing.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from binfmt import PeImage  # noqa: E402
import decomp  # noqa: E402

HEADER_FIELDS = [   # (name, offset from the PE signature, struct format)
    ("Machine", 4, "<H"), ("NumberOfSections", 6, "<H"), ("TimeDateStamp", 8, "<I"),
    ("Characteristics", 22, "<H"), ("Magic", 24, "<H"), ("LinkerVersion", 26, "<H"),
    ("SizeOfCode", 28, "<I"), ("SizeOfInitializedData", 32, "<I"), ("SizeOfUninitializedData", 36, "<I"),
    ("AddressOfEntryPoint", 40, "<I"), ("BaseOfCode", 44, "<I"), ("BaseOfData", 48, "<I"),
    ("ImageBase", 52, "<I"), ("SectionAlignment", 56, "<I"), ("FileAlignment", 60, "<I"),
    ("OSVersion", 64, "<I"), ("ImageVersion", 68, "<I"), ("SubsystemVersion", 72, "<I"),
    ("SizeOfImage", 80, "<I"), ("SizeOfHeaders", 84, "<I"), ("CheckSum", 88, "<I"), ("Subsystem", 92, "<H"),
    ("DllCharacteristics", 94, "<H"), ("StackReserve", 96, "<I"), ("StackCommit", 100, "<I"),
    ("HeapReserve", 104, "<I"), ("HeapCommit", 108, "<I"),
] + [(f"DataDirectory{i}", 120 + 8 * i, "<II") for i in range(16)]
MASKED = {"TimeDateStamp"}


def header(image: PeImage) -> dict[str, object]:
    pe = struct.unpack_from("<I", image.data, 0x3C)[0]
    out = {}
    for name, off, fmt in HEADER_FIELDS:
        v = struct.unpack_from(fmt, image.data, pe + off)
        out[name] = v[0] if len(v) == 1 else list(v)
    return out


def ranges(addrs: list[int]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for a in addrs:
        if out and a == out[-1][1]:
            out[-1][1] = a + 1
        else:
            out.append([a, a + 1])
    return [(a, b - a) for a, b in out]


def loaded(image: PeImage, base: int, size: int) -> tuple[bytearray, bytearray]:
    """The image's bytes over [base, base + size) as the loader maps them, and a mask of the mapped addresses."""
    out, mask = bytearray(size), bytearray(size)
    for _name, sbase, vsize, rptr, rsize in image.sections:
        lo, hi = max(base, sbase), min(base + size, sbase + max(vsize, rsize))
        if lo >= hi:
            continue
        raw = image.data[rptr:rptr + rsize]
        a0, a1 = lo - sbase, hi - sbase
        chunk = raw[a0:a1] + b"\0" * max(0, (a1 - a0) - len(raw[a0:a1]))
        out[lo - base:hi - base] = chunk
        mask[lo - base:hi - base] = b"\1" * (hi - lo)
    return out, mask


def compare_sections(retail: PeImage, cand: PeImage, ndiffs: int) -> list[dict]:
    rows = []
    for name, base, vsize, _rptr, rsize in retail.sections:
        size = vsize
        want, _ = loaded(retail, base, size)
        got, mask = loaded(cand, base, size)
        diffs = [base + i for i in range(size) if not mask[i] or want[i] != got[i]]
        rows.append({"section": name, "va": base, "bytes": size, "equal": size - len(diffs),
                     "first_diffs": [(f"{a:08x}", n) for a, n in ranges(diffs)[:ndiffs]]})
    return rows


MAP_LINE = re.compile(r"^\s*([0-9a-fA-F]{4}):([0-9a-fA-F]{8})\s+(\S+)\s+([0-9a-fA-F]{8})\s+(f\s+)?(i\s+)?(\S+)?")


def read_map(path: Path) -> dict[str, tuple[int, str]]:
    """VC6 /MAP publics: ' 0001:00000000  ?Name@@...  00401000 f   object.obj' -> {name: (address, object)}."""
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        m = MAP_LINE.match(line)
        if m and m.group(1) != "0000":
            out[m.group(3)] = (int(m.group(4), 16), m.group(7) or "")
    return out


def longest_increasing(values: list[int]) -> int:
    import bisect
    tails: list[int] = []
    for v in values:
        i = bisect.bisect_left(tails, v)
        tails[i:i + 1] = [v]
    return len(tails)


def compare_symbols(publics: dict[str, tuple[int, str]], implied: dict[str, int], functions: dict[str, int]) -> dict:
    def tally(want: dict[str, int]) -> dict:
        seen = [k for k in want if k in publics]
        ok = [k for k in seen if publics[k][0] == want[k]]
        bad = [k for k in seen if publics[k][0] != want[k]]
        return {"expected": len(want), "in_map": len(seen), "at_retail_address": len(ok),
                "elsewhere": [(k, f"{publics[k][0]:08x}", f"{want[k]:08x}") for k in bad[:20]]}
    out = {"implied_symbols": tally(implied), "annotated_functions": tally(functions)}
    # order: the annotated functions sorted by their linked address; the longest run in retail's address order
    seen = sorted((publics[k][0], functions[k]) for k in functions if k in publics)
    out["annotated_functions"]["in_retail_order"] = longest_increasing([r for _c, r in seen])
    return out


def import_table(image: PeImage) -> list[tuple[str, list[tuple[str, int | None, int]]]]:
    """Descriptor order: [(dll, [(name or '#ordinal', hint or None, IAT slot address)])]."""
    pe = struct.unpack_from("<I", image.data, 0x3C)[0]
    rva = struct.unpack_from("<I", image.data, pe + 128)[0]
    out, d = [], image.image_base + rva
    while rva:
        ilt, _ts, _fw, name_rva, iat = struct.unpack("<IIIII", image.read(d, 20))
        if not name_rva:
            break
        dll = image.cstr(image.image_base + name_rva).rstrip(b"\0").decode("latin-1")
        entries, k = [], 0
        while True:
            entry = image.u32(image.image_base + (ilt or iat) + 4 * k)
            if not entry:
                break
            slot = image.image_base + iat + 4 * k
            if entry & 0x80000000:
                entries.append((f"#{entry & 0xFFFF}", None, slot))
            else:
                hint = struct.unpack("<H", image.read(image.image_base + entry, 2))[0]
                entries.append((image.cstr(image.image_base + entry + 2).rstrip(b"\0").decode("latin-1"), hint, slot))
            k += 1
        out.append((dll, entries))
        d += 20
    return out


def resources(image: PeImage) -> tuple[list[tuple], bytes | None]:
    """The resource tree's leaves in directory order, [(path, codepage, data)], and the resource image with each data
    entry's RVA made relative to the directory (so two images at different addresses compare)."""
    pe = struct.unpack_from("<I", image.data, 0x3C)[0]
    rva, size = struct.unpack_from("<II", image.data, pe + 136)
    if not rva:
        return [], None
    base = image.image_base + rva
    raw = bytearray(image.read(base, size))
    leaves = []

    def walk(off: int, path: tuple) -> None:
        named, ids = struct.unpack_from("<HH", raw, off + 12)
        for k in range(named + ids):
            name, target = struct.unpack_from("<II", raw, off + 16 + 8 * k)
            if name & 0x80000000:
                n = name & 0x7FFFFFFF
                length = struct.unpack_from("<H", raw, n)[0]
                key = raw[n + 2:n + 2 + 2 * length].decode("utf-16-le")
            else:
                key = name
            if target & 0x80000000:
                walk(target & 0x7FFFFFFF, path + (key,))
            else:
                data_rva, data_size, codepage, _ = struct.unpack_from("<IIII", raw, target)
                leaves.append((path + (key,), codepage, bytes(image.read(image.image_base + data_rva, data_size))))
                struct.pack_into("<I", raw, target, data_rva - rva)
    walk(0, ())
    return leaves, bytes(raw)


def compare_resources(retail: tuple, cand: tuple) -> dict:
    rl, rimg = retail
    cl, cimg = cand
    return {"leaves": [len(rl), len(cl)], "leaves_equal_in_order": rl == cl,
            "paths_equal": [x[0] for x in rl] == [x[0] for x in cl],
            "image_equal_rebased": rimg is not None and rimg == cimg}


def compare_imports(retail: list, cand: list) -> dict:
    """Descriptor order, then per retail DLL: the same names in the same order, the same hints, the same IAT slots."""
    rd, cd = [d.lower() for d, _ in retail], [d.lower() for d, _ in cand]
    cm = {d.lower(): e for d, e in cand}
    rows = []
    for dll, want in retail:
        got = cm.get(dll.lower())
        if got is None:
            rows.append({"dll": dll, "present": False})
            continue
        names = [e[0] for e in want] == [e[0] for e in got]
        rows.append({"dll": dll, "present": True, "entries": [len(want), len(got)], "names_in_order": names,
                     "hints": names and [e[1] for e in want] == [e[1] for e in got],
                     "iat_slots": [e[2] for e in want] == [e[2] for e in got],
                     "missing": sorted({e[0] for e in want} - {e[0] for e in got}),
                     "extra": sorted({e[0] for e in got} - {e[0] for e in want})})
    return {"descriptor_order_equal": rd == cd, "retail_order": rd, "candidate_order": cd, "dlls": rows}


def write_expected(out: Path) -> None:
    objects = {}
    for src in sorted(list((decomp.ROOT / "src").rglob("*.cpp")) + list((decomp.ROOT / "src").rglob("*.c"))):
        obj = decomp.BUILD / src.relative_to(decomp.ROOT / "src").with_suffix(".obj")
        if obj.exists():
            objects[src] = obj
    results, checker = decomp.check(objects)
    functions = {r.symbol: r.address for r in results if r.symbol and r.status != "unplaced"}
    implied = {k: next(iter(v)) for k, v in checker.discovered.items() if len(v) == 1}
    out.write_text(json.dumps({"functions": functions, "implied": implied}, indent=0, sort_keys=True) + "\n")
    print(f"{out}: {len(functions)} functions, {len(implied)} implied symbols from {len(objects)} objects")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("candidate", type=Path, nargs="?")
    ap.add_argument("--map", type=Path)
    ap.add_argument("--expected", type=Path, help="JSON written by --write-expected")
    ap.add_argument("--write-expected", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--diffs", type=int, default=8)
    a = ap.parse_args()
    if a.write_expected:
        return write_expected(a.write_expected)
    if a.candidate is None:
        ap.error("a candidate executable is required")
    retail = PeImage(decomp.SPECIMEN, decomp.SPECIMEN_SHA256)
    cand = PeImage(a.candidate)
    hr, hc = header(retail), header(cand)
    head = {k: {"retail": hr[k], "candidate": hc[k], "equal": hr[k] == hc[k]} for k in hr if k not in MASKED}
    report = {"header_equal": sum(v["equal"] for v in head.values()), "header_fields": len(head),
              "header_differences": {k: v for k, v in head.items() if not v["equal"]},
              "sections": compare_sections(retail, cand, a.diffs)}
    report["whole_file_equal_masked"] = (report["header_equal"] == len(head) and
                                         all(r["equal"] == r["bytes"] for r in report["sections"]) and
                                         len(retail.data) == len(cand.data))
    report["imports"] = compare_imports(import_table(retail), import_table(cand))
    report["resources"] = compare_resources(resources(retail), resources(cand))
    if a.map:
        publics = read_map(a.map)
        expected = json.loads(a.expected.read_text()) if a.expected else {"functions": {}, "implied": {}}
        report["symbols"] = compare_symbols(publics, expected["implied"], expected["functions"])
    print(f"header: {report['header_equal']} of {report['header_fields']} fields equal (timestamp masked)")
    for k, v in report["header_differences"].items():
        print(f"  {k}: retail {v['retail']} candidate {v['candidate']}")
    for r in report["sections"]:
        pct = 100.0 * r["equal"] / r["bytes"] if r["bytes"] else 100.0
        print(f"{r['section']:7s} {r['va']:08x} {r['equal']:9d} of {r['bytes']:9d} bytes equal ({pct:6.2f}%)"
              + (f"  first differences {r['first_diffs']}" if r["first_diffs"] else ""))
    if "symbols" in report:
        for k, v in report["symbols"].items():
            print(f"{k}: {v['at_retail_address']} of {v['expected']} at the retail address ({v['in_map']} in the map)"
                  + (f"; {v['in_retail_order']} in retail's order" if "in_retail_order" in v else ""))
    imp = report["imports"]
    full = [r for r in imp["dlls"] if r.get("names_in_order") and r["hints"] and r["iat_slots"]]
    print(f"imports: descriptor order {'equal' if imp['descriptor_order_equal'] else 'differs'}; "
          f"{len(full)} of {len(imp['dlls'])} DLLs equal in names, order, hints and IAT slots")
    for r in imp["dlls"]:
        if r not in full:
            print(f"  {r['dll']}: " + ("absent" if not r["present"] else
                  f"entries {r['entries'][0]}/{r['entries'][1]}, names in order {r['names_in_order']}, hints {r['hints']}, "
                  f"IAT slots {r['iat_slots']}" + (f", missing {r['missing'][:6]}" if r["missing"] else "")
                  + (f", extra {r['extra'][:6]}" if r["extra"] else "")))
    res = report["resources"]
    print(f"resources: {res['leaves'][1]} of {res['leaves'][0]} leaves; leaves equal in order {res['leaves_equal_in_order']}; "
          f"image equal with its RVAs rebased {res['image_equal_rebased']}")
    print("whole file equal (timestamp masked):", report["whole_file_equal_masked"])
    if a.json:
        a.json.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
