#!/usr/bin/env python3
"""Whole-executable difference inventory: every byte where a linked BEA.exe differs from the pinned retail specimen,
attributed to a root-cause class, so the remaining work for byte identity is one list.

    python3 tools/inventory.py [--link DIR] [--out DIR]

Reads this checkout's build/*.obj (run a check first) and the link in DIR (default local-data/link: BEA.exe, BEA.map,
link.log; run tools/link.py first). Writes OUT/inventory.json and OUT/INVENTORY.md (default local-data/inventory/).
Reads the pinned specimen at run time; writes nothing else.

Pairing (which retail bytes are which of our items): matched game functions (placemap's lookup); data symbols the
matched code implies, and every data symbol a matched function's DIR32 relocation reaches, sized exactly from our
COFF (one more level through those symbols' own relocations); library functions by their bytes with address-like
fields masked; the unwind funclets as one block of equal length; the EH tables through the handler stubs in that
block (mov eax, FuncInfo; jmp); and the remaining unnamed data and library code by 256-byte content chunks near the
displacement of the items around them.

Two views:
1. Bytes at the same address (what linkcmp counts): per section, every retail byte is equal, or it belongs to
   - a paired item at the same address whose bytes differ only in references to moved targets ("ref"), or in
     content ("content");
   - a paired item at another address ("displaced": it moved because something before it changed size), with its
     own bytes, compared at its own address: identical, ref-only or content;
   - an unpaired range: imports, header, padding, or "unpaired".
2. Root causes: the events that make the layout differ (per-object size differences in .text, .rdata, .data and
   .bss, items out of order inside an object, the library members, imports, the Rich header and header fields), each
   with bytes, items, the area and whether source can fix it. The .bss is compared per object: an object starts at
   its lowest retail operand point (a matched function's operand, or a paired library function's for library
   objects), and two neighbours that are neighbours in both images compare their spans.
"""
from __future__ import annotations

import argparse
import array
import bisect
import collections
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decomp  # noqa: E402
import linkcmp  # noqa: E402
import placemap  # noqa: E402
from binfmt import PeImage, parse_coff  # noqa: E402

KIND_RANK = {2: 0, 3: 1, 4: 2}   # content < ref to an unpaired target < ref to a different target


def rich(img: PeImage) -> list[tuple[int, int, int]]:
    d = img.data
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    end = d.find(b"Rich", 0x80, pe)
    if end < 0:
        return []
    key = struct.unpack_from("<I", d, end + 4)[0]
    start = next(i for i in range(0x80, end, 4) if struct.unpack_from("<I", d, i)[0] ^ key == 0x536E6144)
    out = []
    for i in range(start + 16, end, 8):
        cid, cnt = struct.unpack_from("<II", d, i)
        cid ^= key
        cnt ^= key
        out.append((cid >> 16, cid & 0xFFFF, cnt))
    return out


def next_after(starts: list[int], a: int, limit: int) -> int:
    k = bisect.bisect_right(starts, a)
    return min(starts[k], limit) if k < len(starts) else limit


def section_end(table: dict, a: int) -> int:
    for lo, hi in table.values():
        if lo <= a < hi:
            return hi
    return a


def masked(b: bytes) -> bytes:
    m = bytearray(b)
    for i in range(len(b) - 3):
        v = struct.unpack_from("<I", b, i)[0]
        if 0x400000 <= v < 0xA00000:
            m[i:i + 4] = b"\0\0\0\0"
    for i in range(len(b) - 4):
        if b[i] in (0xE8, 0xE9):
            m[i + 1:i + 5] = b"\0\0\0\0"
    return bytes(m)


def addr_mask(b: bytes) -> bytearray:
    m = bytearray(len(b))
    for i in range(len(b) - 3):
        if 0x400000 <= struct.unpack_from("<I", b, i)[0] < 0xA00000:
            m[i:i + 4] = b"\1\1\1\1"
    for i in range(len(b) - 4):
        if b[i] in (0xE8, 0xE9):
            m[i + 1:i + 5] = b"\1\1\1\1"
    return m


def tolerant_find(needle: bytes, hay: bytes, lo: int, hi: int) -> int:
    """First h in [lo, hi) where needle matches hay[h:] byte for byte, except where either side holds an
    address-like field or a call/jump displacement."""
    nm = addr_mask(needle)
    n = len(needle)
    first = next((i for i in range(n) if not nm[i]), None)
    if first is None:
        return -1
    for h in range(lo, min(hi, len(hay) - n + 1)):
        if hay[h + first] != needle[first]:
            continue
        seg = hay[h:h + n]
        if seg == needle:
            return h
        sm = addr_mask(seg)
        if all(nm[i] or sm[i] or seg[i] == needle[i] for i in range(n)):
            return h
    return -1


def reference_kind(vr: int, vo: int, r_site: int, o_site: int, translate, in_image) -> int:
    """One 4-byte window, retail value VR at R_SITE and ours VO at O_SITE, read as an absolute address and as a rel32
    displacement: 1 when the targets correspond (TRANSLATE maps retail to ours), 4 when the retail target is another
    paired item's, 3 when it is in the image but unpaired, 2 when neither reading is a reference into the image."""
    best = 2
    sr = struct.unpack("<i", struct.pack("<I", vr))[0]
    so = struct.unpack("<i", struct.pack("<I", vo))[0]
    for tr, to in ((vr, vo), ((r_site + 4 + sr) & 0xFFFFFFFF, (o_site + 4 + so) & 0xFFFFFFFF)):
        if in_image(tr) and in_image(to):
            t = translate(tr)
            if t == to:
                return 1
            if t is None:
                best = 3 if best == 2 else best
            else:
                best = 4
    return best


def object_spans(points, r_end: int, o_end: int) -> list[dict]:
    """POINTS: (retail address, our address, object). Each object starts at its lowest point on each side; its span
    runs to the next object's start (or the section end). Returns the objects whose spans differ, with "comparable"
    when the next object is the same in both images (a size difference) and not otherwise (order)."""
    first_r, first_o = {}, {}
    for rv, ov, ob in points:
        first_r[ob] = min(first_r.get(ob, rv), rv)
        first_o[ob] = min(first_o.get(ob, ov), ov)
    order_r = sorted(first_r, key=first_r.get)
    order_o = sorted(first_o, key=first_o.get)
    next_o = {x: y for x, y in zip(order_o, order_o[1:])}
    out = []
    for i, ob in enumerate(order_r):
        nxt = order_r[i + 1] if i + 1 < len(order_r) else None
        rs = (first_r[nxt] if nxt else r_end) - first_r[ob]
        no = next_o.get(ob)
        os_ = (first_o[no] if no else o_end) - first_o[ob]
        if os_ != rs:
            out.append({"object": ob, "retail": f"{first_r[ob]:08x}", "retail_span": rs, "our_span": os_,
                        "delta": os_ - rs, "next_retail": nxt, "next_ours": no, "comparable": no == nxt})
    return out


def coff_extent(c_, s_):
    """A COFF symbol's exact extent in its initialised section: (size to the next symbol or the section's end, its
    DIR32 relocations as (offset inside the symbol, symbol index, addend)); None for .bss or an empty section."""
    sec_ = c_.sections[s_.section]
    if sec_.name.startswith(".bss") or not getattr(sec_, "data", None):
        return None
    vals = sorted({x.value for x in c_.symbols.values() if x.section == s_.section and x.storage in (2, 3)
                   and not x.name.startswith(".")} | {len(sec_.data)})
    end = next((v for v in vals if v > s_.value), len(sec_.data))
    return end - s_.value, [(o - s_.value, i, struct.unpack("<I", sec_.data[o:o + 4])[0]) for o, i, t in sec_.relocs
                            if t == 6 and s_.value <= o < end]


ALIGNED_SECTIONS = (".rdata", ".data", ".rsrc")


def aligned_compare(R, C, rva_regions=()) -> dict:
    """What the data sections would compare like if .text had retail's size, so every later section started at its
    retail address: each of .rdata, .data and .rsrc compared at the same offset from its section start. Our aligned
    4-byte words that hold an address inside one of our data sections are first moved by that section's shift (our
    base to retail's), and so are the words in RVA_REGIONS (our (lo, hi) virtual address ranges: the import tables and
    the resource directory, which hold RVAs) that hold an RVA inside one of our data sections. A remaining difference
    is a code pointer (both words inside retail's .text: the code still moved), a data pointer (both inside the image)
    or content."""
    base = R.image_base
    rs = {s[0]: (s[1], max(s[2], s[4])) for s in R.sections}
    cs = {s[0]: (s[1], max(s[2], s[4])) for s in C.sections}
    shift = [(cs[n][0], cs[n][0] + cs[n][1], rs[n][0] - cs[n][0]) for n in ALIGNED_SECTIONS if n in rs and n in cs]
    text_lo, text_hi = rs[".text"][0], rs[".text"][0] + rs[".text"][1]
    image_hi = max(lo + n for lo, n in rs.values())
    our_hi = max(lo + n for lo, n in cs.values())

    def rebased(v: int, rva: bool) -> int:
        a = v + base if rva else v
        for lo, hi, d in shift:
            if lo <= a < hi:
                return v + d
        return v

    out = {}
    for name in ALIGNED_SECTIONS:
        if name not in rs or name not in cs:
            continue
        n = min(rs[name][1], cs[name][1])
        rb_, _m = linkcmp.loaded(R, rs[name][0], n)
        cb_, _m = linkcmp.loaded(C, cs[name][0], n)
        cats = collections.Counter()
        first = None
        for i in range(0, n, 4):
            rw, ow = bytes(rb_[i:i + 4]), bytes(cb_[i:i + 4])
            if rw == ow:
                cats["equal"] += len(rw)
                continue
            if len(rw) == 4:
                v = struct.unpack("<I", ow)[0]
                va = cs[name][0] + i
                in_rva = any(lo <= va < hi for lo, hi in rva_regions)
                w = rebased(v, True) if (in_rva and v < our_hi - base) else rebased(v, False)
                if struct.pack("<I", w & 0xFFFFFFFF) == rw:      # a pointer to the same item, once sections align
                    cats["equal"] += 4
                    continue
                vr = struct.unpack("<I", rw)[0]
                kind = ("code pointer" if text_lo <= vr < text_hi and text_lo <= w < text_hi else
                        "data pointer" if base <= vr < image_hi and base <= w < image_hi else "content")
            else:
                kind = "content"
            diff = sum(1 for x, y in zip(rw, ow) if x != y)
            if kind == "content" and first is None:
                first = rs[name][0] + i
            cats[kind] += diff
            cats["equal"] += len(rw) - diff
        out[name] = {"retail_bytes": rs[name][1], "our_bytes": cs[name][1], "compared": n,
                     "equal": cats["equal"], "code_pointer": cats["code pointer"],
                     "data_pointer": cats["data pointer"], "content": cats["content"],
                     "first_content_difference": f"{first:08x}" if first is not None else None}
    return out


def run(linkdir: Path, out: Path) -> dict:
    CHECKOUT, LINKDIR, OUT = decomp.ROOT, linkdir, out
    OUT.mkdir(parents=True, exist_ok=True)

    R = PeImage(decomp.SPECIMEN, decomp.SPECIMEN_SHA256)
    C = PeImage(LINKDIR / "BEA.exe")
    BASE = R.image_base
    report: dict = {"checkout": str(CHECKOUT), "linkdir": str(LINKDIR)}


    def subprocess_head() -> str:
        return subprocess.run(["git", "-C", str(CHECKOUT), "log", "--oneline", "-1"], capture_output=True, text=True).stdout.strip()


    report["head"] = subprocess_head()


    def loaded_all(img: PeImage) -> tuple[bytearray, bytearray]:
        end = max(s[1] + max(s[2], s[4]) for s in img.sections)
        return linkcmp.loaded(img, BASE, end - BASE)


    RB, RM = loaded_all(R)
    CB, CM = loaded_all(C)
    if len(CB) < len(RB):
        CB += bytearray(len(RB) - len(CB))
        CM += bytearray(len(RB) - len(CM))
    RB[:R.sections[0][3]] = R.data[:R.sections[0][3]]          # the headers, as mapped at the image base
    CB[:C.sections[0][3]] = C.data[:C.sections[0][3]]
    RM[:R.sections[0][3]] = b"\1" * R.sections[0][3]
    CM[:C.sections[0][3]] = b"\1" * C.sections[0][3]


    def rb(a: int, n: int = 1) -> bytes:
        return bytes(RB[a - BASE:a - BASE + n])


    def cb(a: int, n: int = 1) -> bytes:
        i = a - BASE
        return bytes(CB[i:i + n]) if 0 <= i < len(CB) else b""


    # ---------------------------------------------------------------- Rich header
    # ---------------------------------------------------------------- pairing
    def map_publics() -> list[tuple[int, int, str, str, bool]]:
        """(section, address, name, object, inline) for every public in our map."""
        out = []
        for line in (LINKDIR / "BEA.map").read_text(errors="replace").splitlines():
            m = linkcmp.MAP_LINE.match(line)
            if m and m.group(1) != "0000":
                out.append((int(m.group(1), 16), int(m.group(4), 16), m.group(3), m.group(7) or "", bool(m.group(6))))
        return out


    def map_statics() -> list[tuple[int, int, str, str]]:
        """The map's static symbols section (file-local functions and data)."""
        out, on = [], False
        for line in (LINKDIR / "BEA.map").read_text(errors="replace").splitlines():
            if line.strip().startswith("Static symbols"):
                on = True
                continue
            if on:
                m = linkcmp.MAP_LINE.match(line)
                if m and m.group(1) != "0000":
                    out.append((int(m.group(1), 16), int(m.group(4), 16), m.group(3), m.group(7) or ""))
        return out


    objects = {}
    for src in sorted(list((CHECKOUT / "src").rglob("*.cpp")) + list((CHECKOUT / "src").rglob("*.c"))):
        obj = CHECKOUT / "build" / src.relative_to(CHECKOUT / "src").with_suffix(".obj")
        if obj.exists():
            objects[src] = obj
    results, checker = decomp.check(objects)
    object_of = {str(src.relative_to(CHECKOUT)): obj.name.lower() for src, obj in objects.items()}
    exp_code = {(r.symbol, object_of.get(r.source.split(":")[0])): r.address
                for r in results if r.symbol and r.status != "unplaced"}
    implied = {k: next(iter(v)) for k, v in checker.discovered.items() if len(v) == 1}
    retail_fn = decomp.retail_functions()
    rstarts = sorted(retail_fn)
    GAME_END = decomp.GAME_END
    pubs = map_publics()
    stats = map_statics()
    sect_of = {1: ".text", 2: ".rdata", 3: ".data"}
    rsec = {s[0]: (s[1], s[1] + s[2]) for s in R.sections}
    csec = {s[0]: (s[1], s[1] + s[2]) for s in C.sections}

    # code pairs: (retail start, our start, size, name, object, kind)
    code_pairs = []
    seen = set()
    for sec, a, n, o, inl in sorted(pubs + [(s, a, n, o, False) for s, a, n, o in stats]):
        if sec != 1 or (n, o) in seen:
            continue
        seen.add((n, o))
        r = placemap.lookup(exp_code, n, o)
        if r is not None and r in retail_fn:
            code_pairs.append((r, a, retail_fn[r].size, n, o, "game"))

    # data pairs from the symbols the matched code implies; sizes run to the next known symbol on each side
    data_r = sorted({a for a in implied.values() if a >= rsec[".rdata"][0]})
    our_data = sorted((a, n, o) for sec, a, n, o, _i in pubs if sec in (2, 3)) + \
        sorted((a, n, o) for sec, a, n, o in stats if sec in (2, 3))
    our_data.sort()
    our_data_addr = {}
    for a, n, o in our_data:
        our_data_addr.setdefault(n, a)
    our_dstarts = sorted({a for a, _n, _o in our_data})


    data_pairs = []
    for n, r in implied.items():
        if r < rsec[".rdata"][0] or n not in our_data_addr:
            continue
        o = our_data_addr[n]
        rs = next_after(data_r, r, section_end(rsec, r)) - r
        os_ = next_after(our_dstarts, o, section_end(csec, o)) - o
        data_pairs.append((r, o, min(rs, os_), n, "", "data"))


    # library code: our library members' functions, paired by bytes with address-like fields masked
    our_code = sorted({(a, n, o) for sec, a, n, o, _i in pubs if sec == 1} |
                      {(a, n, o) for sec, a, n, o in stats if sec == 1})
    our_cstarts = sorted({a for a, _n, _o in our_code})
    game_objs = {obj.name.lower() for obj in objects.values()}
    c_text_end = csec[".text"][1]
    lib_r_lo = GAME_END
    lib_r_hi = min(a for a in rstarts if a >= GAME_END) if any(a >= GAME_END for a in rstarts) else rsec[".text"][1]
    retail_lib = bytes(rb(lib_r_lo, lib_r_hi - lib_r_lo))
    retail_lib_m = masked(retail_lib)
    lib_pairs, lib_unpaired = [], []
    paired_code_ours = {p[1] for p in code_pairs}
    cursor = 0
    done = set()
    for a, n, o in our_code:
        if a in done or a in paired_code_ours or o.lower() in game_objs or n.startswith("Unwind"):
            continue
        done.add(a)
        size = next_after(our_cstarts, a, c_text_end) - a
        if size <= 0:
            continue
        sig = masked(cb(a, size))
        key = sig[:min(len(sig), 48)]
        if len(key) < 6:
            lib_unpaired.append((a, size, n, o))
            continue
        hit = retail_lib_m.find(sig, cursor) if len(sig) <= 4096 else -1
        if hit < 0:
            hit = retail_lib_m.find(sig)
        if hit < 0 and size <= 2048:
            hit = tolerant_find(cb(a, size), retail_lib, cursor, cursor + 0x2000)
        if hit < 0:
            lib_unpaired.append((a, size, n, o))
            continue
        cursor = hit + size
        lib_pairs.append((lib_r_lo + hit, a, size, n, o, "library"))

    # unwind funclets: no symbols in our map; pair retail's in order by masked bytes within our .text tail
    funclet_pairs, funclet_unpaired = [], []
    fr = [a for a in rstarts if a >= GAME_END]
    tail_lo = c_text_end - (rsec[".text"][1] - min(fr)) - 0x1000
    our_tail = cb(tail_lo, c_text_end - tail_lo)
    our_tail_m = masked(our_tail)
    # the funclets lie in one block at the end of .text (.text$x), in function order; locate ours by the first one and
    # pair each retail funclet at the block's displacement when the blocks have the same length
    f0 = tolerant_find(rb(fr[0], retail_fn[fr[0]].size), our_tail, 0, len(our_tail)) if fr else -1
    funclet_block = None
    if f0 >= 0:
        our_f = tail_lo + f0
        funclet_block = {"retail": [f"{fr[0]:08x}", f"{rsec['.text'][1]:08x}"], "ours": [f"{our_f:08x}", f"{c_text_end:08x}"],
                         "retail_bytes": rsec[".text"][1] - fr[0], "our_bytes": c_text_end - our_f}
        for a in fr:
            funclet_pairs.append((a, our_f + (a - fr[0]), retail_fn[a].size, retail_fn[a].name, "", "funclet"))
    # v3.1: data pairs from the matched code's own relocations (datacontent.py's method): each DIR32 operand of a matched
    # function that targets an initialised data symbol pins it (retail address = retail operand - addend; ours likewise),
    # sized exactly from our COFF (next symbol in its section, or the section's end); then one level through the pinned
    # symbols' own relocations. Covers the statics and literals the checker's implied set leaves out.
    init_end = rsec[".data"][0] + next(s_[4] for s_ in R.sections if s_[0] == ".data")
    _coffs = {obj.name.lower(): parse_coff(obj) for obj in objects.values()}
    _fn_ours = {(n, o.lower()): a_ for sec, a_, n, o, _i in pubs if sec == 1}
    _extent = coff_extent
    _seen_r = set()
    _new, _frontier = [], []
    for on, c_ in _coffs.items():
        for secnum, symbol in decomp.function_sections(c_):
            r_ = exp_code.get((symbol, on)); a_ = _fn_ours.get((symbol, on))
            if r_ is None or a_ is None:
                continue
            sd = c_.sections[secnum].data
            for off, si, typ in c_.sections[secnum].relocs:
                s_ = c_.symbols[si]
                if typ != 6 or s_.section <= 0:
                    continue
                ext = _extent(c_, s_)
                if ext is None:
                    continue
                add_ = struct.unpack("<I", sd[off:off + 4])[0]
                ra_ = struct.unpack("<I", rb(r_ + off, 4))[0] - add_
                oa_ = struct.unpack("<I", cb(a_ + off, 4))[0] - add_
                if rsec[".rdata"][0] <= ra_ < init_end and ra_ not in _seen_r and ext[0] > 0:
                    _seen_r.add(ra_); _new.append((ra_, oa_, ext[0], s_.name, on, "data")); _frontier.append((ra_, oa_, c_, ext[1]))
    for ra_, oa_, c_, rels in _frontier:
        for o, si, add_ in rels:
            s_ = c_.symbols[si]
            if s_.section <= 0:
                continue
            ext = _extent(c_, s_)
            if ext is None:
                continue
            rv = struct.unpack("<I", rb(ra_ + o, 4))[0] - add_; ov = struct.unpack("<I", cb(oa_ + o, 4))[0] - add_
            if rsec[".rdata"][0] <= rv < init_end and rv not in _seen_r and ext[0] > 0:
                _seen_r.add(rv); _new.append((rv, ov, ext[0], s_.name, "", "data"))
    _exact = {p[0] for p in _new}
    data_pairs = [p for p in data_pairs if p[0] not in _exact] + _new     # exact COFF sizes replace span-sized pairs
    report["data_pairs_from_relocations"] = len(_new)
    pairs = sorted(code_pairs + data_pairs + lib_pairs + funclet_pairs)
    pstarts = [p[0] for p in pairs]


    import array as _array
    _cover = None


    def _build_cover() -> None:
        """Per retail byte, the index of the pair that holds it: larger pairs first, so a smaller (more specific) pair
        inside a larger one wins."""
        nonlocal _cover
        _cover = _array.array("i", [-1]) * len(RB)
        for idx in sorted(range(len(pairs)), key=lambda i: -max(pairs[i][2], 1)):
            lo_ = pairs[idx][0] - BASE
            n_ = max(pairs[idx][2], 1)
            if 0 <= lo_ < len(RB):
                hi_ = min(lo_ + n_, len(RB))
                _cover[lo_:hi_] = _array.array("i", [idx]) * (hi_ - lo_)


    def item_of(r: int):
        """The pair whose retail range holds r."""
        if _cover is None:
            _build_cover()
        i = r - BASE
        if not 0 <= i < len(RB):
            return None
        k = _cover[i]
        return pairs[k] if k >= 0 else None


    def translate(r: int) -> int | None:
        p = item_of(r)
        return None if p is None else p[1] + (r - p[0])


    def in_image(v: int) -> bool:
        return BASE <= v < BASE + len(RB)


    def explain(r: int, o: int, i: int, n: int, mask: bytearray) -> int:
        """Classify the differing byte r+i by the 4-byte windows that cover it (see reference_kind); a window whose
        targets correspond marks its four bytes in MASK."""
        best = 2
        for j in range(max(0, i - 3), min(i, n - 4) + 1):
            vo = cb(o + j, 4)
            if len(vo) < 4:
                break
            k = reference_kind(struct.unpack("<I", rb(r + j, 4))[0], struct.unpack("<I", vo)[0], r + j, o + j,
                               translate, in_image)
            if k == 1:
                mask[j:j + 4] = b"\1\1\1\1"
                return 1
            best = k if KIND_RANK[k] > KIND_RANK[best] else best
        return best


    LABELS = ("identical", "ref", "content", "ref to unpaired target", "ref to a different target")


    def interpolated(a: int):
        """For a retail byte in no paired item: the displacement of the paired items on both sides, when they agree
        (or either, when the byte matches under it), as a one-byte pseudo pair."""
        k = bisect.bisect_right(pstarts, a) - 1
        prev = pairs[k] if k >= 0 else None
        nxt = pairs[k + 1] if k + 1 < len(pairs) else None
        deltas = []
        for q in (prev, nxt):
            if q is not None and section_end(rsec, q[0]) == section_end(rsec, a):
                deltas.append(q[1] - q[0])
        for dlt in dict.fromkeys(deltas):
            if RB[a - BASE] == (cb(a + dlt) or b"\0")[0]:
                return dlt, True
        return (deltas[0], False) if deltas and len(set(deltas)) == 1 else (None, False)


    def compare_item(r: int, o: int, n: int) -> bytearray:
        """Per byte of the item: 0 equal at its own address, 1 reference to a corresponding target, 3 reference to an
        unpaired target, 2 content."""
        rr, oo = rb(r, n), cb(o, n)
        mask = bytearray(n)
        if rr == oo:
            return mask
        for i in range(n):
            if i >= len(oo) or rr[i] != oo[i]:
                if mask[i] != 1:
                    mask[i] = explain(r, o, i, n, mask)
        return mask


    FUNCLETS = min((a for a in rstarts if a >= GAME_END), default=rsec[".text"][1])


    def region_of(a: int) -> str:
        if rsec[".text"][0] <= a < rsec[".text"][1]:
            return "game code" if a < GAME_END else ("library code" if a < FUNCLETS else "unwind funclets")
        for nm, (lo, hi) in rsec.items():
            if lo <= a < hi:
                return nm
        return "?"


    init_end = rsec[".data"][0] + next(s_[4] for s_ in R.sections if s_[0] == ".data")


    # ---------------------------------------------------------------- v2: EH tables and unnamed data by content
    def rset(new: list) -> None:
        nonlocal pairs, pstarts, _cover
        pairs = sorted(pairs + new)
        pstarts = [p[0] for p in pairs]
        _cover = None


    # EH: each handler stub in the funclet block is "mov eax, FuncInfo; jmp ___CxxFrameHandler"; the blocks correspond
    # byte for byte, so the stub at the same block offset names the same function's FuncInfo on both sides
    eh_pairs = []
    if funclet_block:
        rf0, of0 = fr[0], funclet_pairs[0][1]
        blk = funclet_block["retail_bytes"]
        rblk, oblk = rb(rf0, blk), cb(of0, blk)
        seen_eh = set()

        def eh_add(r_: int, o_: int, n: int, what: str) -> None:
            if n > 0 and r_ not in seen_eh and in_image(r_) and in_image(o_):
                seen_eh.add(r_)
                eh_pairs.append((r_, o_, n, what, "", "eh"))

        for m in re.finditer(rb"\xb8....\xe9", rblk, re.S):
            i = m.start()
            if oblk[i:i + 1] != b"\xb8" or oblk[i + 5:i + 6] != b"\xe9":
                continue
            fr_, fo = struct.unpack_from("<I", rblk, i + 1)[0], struct.unpack_from("<I", oblk, i + 1)[0]
            if not (in_image(fr_) and in_image(fo)) or struct.unpack("<I", rb(fr_, 4))[0] != 0x19930520:
                continue
            eh_add(fr_, fo, 28, "FuncInfo")
            ri_ = struct.unpack("<7I", rb(fr_, 28))
            oi_ = struct.unpack("<7I", cb(fo, 28))
            eh_add(ri_[2], oi_[2], 8 * ri_[1], "UnwindMap")
            eh_add(ri_[4], oi_[4], 20 * ri_[3], "TryBlockMap")
            eh_add(ri_[6], oi_[6], 8 * ri_[5], "IPtoStateMap")
            for t in range(min(ri_[3], oi_[3])):
                rt = struct.unpack("<5I", rb(ri_[4] + 20 * t, 20))
                ot = struct.unpack("<5I", cb(oi_[4] + 20 * t, 20))
                eh_add(rt[4], ot[4], 16 * rt[3], "HandlerArray")
    rset(eh_pairs)

    # unnamed data: maximal runs of retail .rdata and initialized .data bytes in no item, cut into chunks and found in our
    # image near the displacement of the paired items around them (exact first, then the tolerant compare)
    content_pairs = []
    for secname in (".text", ".rdata", ".data"):
        lo, hi = rsec[secname]
        if secname == ".data":
            hi = init_end
        if secname == ".text":
            lo, hi = GAME_END, FUNCLETS
        a = lo
        while a < hi:
            if item_of(a) is not None:
                a += 1
                continue
            b = a
            while b < hi and item_of(b) is None:
                b += 1
            run_lo, run_hi = a, b
            a = b
            dlt = None
            k = bisect.bisect_right(pstarts, run_lo) - 1
            guesses = []
            for q in (pairs[k] if k >= 0 else None, pairs[k + 1] if k + 1 < len(pairs) else None):
                if q is not None and section_end(rsec, q[0]) == section_end(rsec, run_lo):
                    guesses.append(q[1] - q[0])
            c = run_lo
            while c < run_hi:
                n = min(256, run_hi - c)
                chunk = rb(c, n)
                if chunk.count(0) == n:
                    c += n
                    continue
                hit = None
                for g in ([dlt] if dlt is not None else []) + guesses:
                    if cb(c + g, n) == chunk:
                        hit = c + g
                        break
                if hit is None:
                    am = addr_mask(chunk)
                    key_at = next((i for i in range(0, n - 12) if not any(am[i:i + 12]) and len(set(chunk[i:i + 12])) > 3), None)
                    if key_at is not None:
                        centre = c + (dlt if dlt is not None else (guesses[0] if guesses else 0)) - BASE
                        lo_s, hi_s = max(0, centre - 0x4000), min(len(CB), centre + 0x4000 + n)
                        key = chunk[key_at:key_at + 12]
                        for wlo, whi in ((lo_s, hi_s), (0, len(CB))):     # near the guess, then anywhere
                            hay = bytes(CB[wlo:whi])
                            pos = hay.find(key)
                            while pos >= 0 and hit is None:
                                cand = BASE + wlo + pos - key_at
                                seg = cb(cand, n)
                                sm = addr_mask(seg)
                                if len(seg) == n and all(am[i] or sm[i] or seg[i] == chunk[i] for i in range(n)):
                                    hit = cand
                                    break
                                pos = hay.find(key, pos + 1)
                            if hit is not None:
                                break
                if hit is not None:
                    dlt = hit - c
                    content_pairs.append((c, hit, n, f"content@{c:08x}", "", "content"))
                c += n
    rset(content_pairs)
    report["v2_pairs"] = {"eh": len(eh_pairs), "eh_bytes": sum(p[2] for p in eh_pairs),
                          "content_chunks": len(content_pairs), "content_bytes": sum(p[2] for p in content_pairs)}


    # ---------------------------------------------------------------- view 1: bytes at the same address
    pe = struct.unpack_from("<I", R.data, 0x3C)[0]
    hdr = linkcmp.header(R)
    ranges_known = []   # (lo, hi, label)
    iat = hdr["DataDirectory12"]
    ranges_known.append((BASE + iat[0], BASE + iat[0] + iat[1], "imports: IAT"))
    imp = hdr["DataDirectory1"]
    ranges_known.append((BASE + imp[0], BASE + imp[0] + imp[1], "imports: descriptors"))
    # the import name tables and hint/name strings follow the descriptors in .rdata
    ilt_lo = BASE + imp[0] + imp[1]
    names = []
    for dll, entries in linkcmp.import_table(R):
        pass
    d = BASE + imp[0]
    lo_names, hi_names = 1 << 40, 0
    while True:
        ilt, _t, _f, nrva, iatrva = struct.unpack("<IIIII", rb(d, 20))
        if not nrva:
            break
        lo_names, hi_names = min(lo_names, BASE + nrva, BASE + ilt), max(hi_names, BASE + nrva + 16)
        k = 0
        while True:
            e = struct.unpack("<I", rb(BASE + ilt + 4 * k, 4))[0]
            hi_names = max(hi_names, BASE + ilt + 4 * k + 4)
            if not e:
                break
            if not e & 0x80000000:
                s = R.cstr(BASE + e + 2)
                hi_names = max(hi_names, BASE + e + 2 + len(s) + 1 + 1)
            k += 1
        d += 20
    ranges_known.append((lo_names, hi_names, "imports: name tables and strings"))
    ranges_known.sort()

    per_section = {}
    detail_content = []
    for name, va, vsize, _p, _rs in [("headers", BASE, R.sections[0][1] - BASE, 0, 0)] + list(R.sections):
        lo, hi = va, va + vsize
        cats = collections.Counter()
        i = lo
        k = bisect.bisect_right(pstarts, lo) - 1
        item_cache = {}
        # walk by items: equal bytes counted directly, differing bytes attributed to the enclosing pair or range
        diffs = [a for a in range(lo, hi) if RB[a - BASE] != CB[a - BASE] or not CM[a - BASE]]
        cats["equal"] = (hi - lo) - len(diffs)
        for a in diffs:
            p = item_of(a)
            if p is None:
                lab = next((l for x, y, l in ranges_known if x <= a < y), None)
                if lab is None and name in (".text", ".rdata", ".data") and not (name == ".data" and a >= va + _rs):
                    dlt, same = interpolated(a)
                    if dlt is not None:
                        region = region_of(a)
                        if same:
                            lab = f"between items, displaced: identical ({region})"
                        else:
                            tmp = bytearray(8)
                            lo4 = max(a - 3, BASE)
                            m = explain(lo4, lo4 + dlt, a - lo4, 8, tmp) if True else 2
                            lab = f"between items, displaced: {LABELS[m]} ({region})"
                if lab is None:
                    if name == ".text" and RB[a - BASE] in (0xCC, 0x90, 0x00):
                        lab = "padding (int3/nop/zero)"
                    elif name == ".data" and a >= va + _rs:
                        lab = ".bss (uninitialized; zero in both)" if not CB[a - BASE] else ".bss: ours nonzero"
                    elif name == ".rsrc":
                        lab = "resources (section at another RVA; rebased image equal)"
                    elif name == "headers":
                        lab = "header"
                    else:
                        lab = f"unpaired ({region_of(a)})"
                cats[lab] += 1
                continue
            pr, po, size = p[:3]
            key = p[:2]
            if key not in item_cache:
                item_cache[key] = compare_item(pr, po, size)
            m = item_cache[key][a - pr]
            where = "same address" if po == pr else "displaced"
            cats[f"{where}: " + LABELS[m]] += 1
        per_section[name] = {"va": va, "bytes": vsize, "categories": dict(cats.most_common())}
        if name in (".text", ".rdata", ".data"):
            for key, m in item_cache.items():
                content = m.count(2)
                if content:
                    p = next(x for x in pairs if x[:2] == key)
                    detail_content.append({"section": name, "retail": f"{p[0]:08x}", "ours": f"{p[1]:08x}", "size": p[2],
                                           "name": p[3], "kind": p[5], "content_bytes": content, "ref_bytes": m.count(1),
                                           "unpaired_ref_bytes": m.count(3)})
    report["same_address"] = per_section
    report["content_items"] = sorted(detail_content, key=lambda x: -x["content_bytes"])


    # ---------------------------------------------------------------- view 2: root causes
    classes: dict[str, dict] = {}


    def add(cls: str, nbytes: int, item: dict) -> None:
        c = classes.setdefault(cls, {"bytes": 0, "items": 0, "list": []})
        c["bytes"] += abs(nbytes)
        c["items"] += 1
        c["list"].append(item)


    # .text game code: placement events (offset changes between neighbouring chain functions), from tools/placemap.py
    pm = placemap.placement(LINKDIR, exp_code)
    inline_ours = {(n, o) for sec, a, n, o, i in pubs if sec == 1 and i}
    our_by_addr = collections.defaultdict(list)
    for a_, n, o in our_code:
        our_by_addr[a_].append((n, o))
    r2o = {p[0]: p[1] for p in code_pairs}
    r_inline = {p[0] for p in code_pairs if (p[3], p[4]) in inline_ours}
    paired_r = set(r2o)


    def rspan(a_: int) -> int:
        k = bisect.bisect_right(rstarts, a_)
        return (rstarts[k] - a_) if k < len(rstarts) else 0


    def ospan(a_: int) -> int:
        k = bisect.bisect_right(our_cstarts, a_)
        return (our_cstarts[k] - a_) if k < len(our_cstarts) else 0


    for e in pm["events"]:
        ra, rb_ = (int(x, 16) for x in e["retail"])
        oa, ob = (int(x, 16) for x in e["ours"])
        parts = []
        # ours: every address strictly between the two chain neighbours (one entry per address: folded names share it)
        for a_ in our_cstarts[bisect.bisect_right(our_cstarts, oa):bisect.bisect_left(our_cstarts, ob)]:
            names_ = our_by_addr[a_]
            rs_ = [placemap.lookup(exp_code, n, o) for n, o in names_]
            if any(r is not None and ra < r < rb_ for r in rs_):
                continue                                   # in this span on both sides
            n, o = names_[0]
            size = ospan(a_)
            r = next((r for r in rs_ if r is not None), None)
            if n.startswith("_$E"):
                kind = "initializer funclets (set and position)"
            elif r is not None and (n, o) not in inline_ours:
                kind = "own function out of order (moved in/out of this span)"
            elif r is not None:
                kind = "inline/ICF: emitted or kept in another object than retail's"
            else:
                kind = "extra code (no retail counterpart)"
            parts.append([kind, size, f"{n} ({o})", n.startswith("_$E") or r is None])
        # retail: every function strictly between, not placed in our span
        for a_ in rstarts[bisect.bisect_right(rstarts, ra):bisect.bisect_left(rstarts, rb_)]:
            o_ = r2o.get(a_)
            if o_ is not None and oa < o_ < ob:
                continue
            size = rspan(a_)
            nm = retail_fn[a_].name
            if o_ is not None and a_ in r_inline:
                kind = "inline/ICF: emitted or kept in another object than retail's"
            elif o_ is not None:
                kind = "own function out of order (moved in/out of this span)"
            else:
                kind = "missing code (retail item with no counterpart here)"
            parts.append([kind, -size, nm, o_ is None])
        # unnamed items of equal size on both sides cancel (initializer funclets, unannotated functions)
        pos = [x for x in parts if x[1] > 0 and x[3]]
        neg = [x for x in parts if x[1] < 0 and x[3]]
        for x in pos:
            y = next((y for y in neg if -y[1] == x[1]), None)
            if y is not None:
                neg.remove(y)
                parts.remove(x)
                parts.remove(y)
        listed = sum(x[1] for x in parts)
        if e["step"] - listed:
            parts.append(["function size or alignment padding in the span", e["step"] - listed,
                          f"{e['after']} .. {e['before']}", False])
        for kind, size, what, _u in parts:
            add(".text game: " + kind, size, {"at_retail": e["retail"][0], "object": e["object"], "bytes": size,
                                              "what": what})
    report["misplaced_functions"] = pm["misplaced"]

    # library code: per library, the region sizes and the members we could not pair by bytes
    member_lib = {}
    for lib in (LINKDIR / "libmembers").iterdir() if (LINKDIR / "libmembers").exists() else []:
        for f in lib.rglob("*.obj"):
            member_lib[f.name.lower()] = lib.name
    for f in (LINKDIR / "third-party").glob("*.obj") if (LINKDIR / "third-party").exists() else []:
        member_lib[f.name.lower()] = "nvtristrip (third-party objects)"
    lib_ours_lo = min((p[1] for p in lib_pairs), default=0)
    our_funclet_lo = funclet_pairs[0][1] if funclet_pairs else c_text_end
    report["library_region"] = {"retail": [f"{lib_r_lo:08x}", f"{FUNCLETS:08x}"], "retail_bytes": FUNCLETS - lib_r_lo,
                                "funclet_block": funclet_block}
    # library members keep retail's order: compare each span between consecutive paired functions (on the longest run
    # that is in order on both sides): a size step, or at equal size the content of the span
    lp = sorted(lib_pairs, key=lambda p: p[1])
    lchain = [lp[i] for i in placemap.chain([(p[1], p[0], p[3]) for p in lp])]   # increasing in ours and in retail
    lchain.sort(key=lambda p: p[1])
    game_end_ours = lchain[0][1] - (lchain[0][0] - lib_r_lo) if lchain else 0
    for x, y in zip(lchain, lchain[1:]):
        rs, os_ = y[0] - x[0], y[1] - x[1]
        lib = member_lib.get(x[4].lower(), x[4] or "other")
        if os_ != rs:
            add(f"library: {lib}: span size differs", os_ - rs,
                {"after": x[3], "before": y[3], "retail": f"{x[0]:08x}", "ours": f"{x[1]:08x}", "retail_span": rs,
                 "our_span": os_, "step": os_ - rs})
        else:
            m = compare_item(x[0], x[1], rs)
            if m.count(2):
                add(f"library: {lib}: same span size, content differs", m.count(2),
                    {"after": x[3], "before": y[3], "retail": f"{x[0]:08x}", "content": m.count(2), "ref": m.count(1),
                     "unpaired_ref": m.count(3), "other_target": m.count(4)})
    if lchain:
        last = lchain[-1]
        rs, os_ = FUNCLETS - last[0], our_funclet_lo - last[1]
        if rs != os_:
            add(f"library: {member_lib.get(last[4].lower(), last[4] or 'other')}: span size differs", os_ - rs,
                {"after": last[3], "before": "(funclet block)", "retail_span": rs, "our_span": os_, "step": os_ - rs})
    report["library_region"]["ours"] = [f"{lchain[0][1] - (lchain[0][0] - lib_r_lo):08x}" if lchain else None,
                                        f"{our_funclet_lo:08x}"]
    for a_, size, n, o in lib_unpaired:
        if o.lower() in ("provisional.obj", "aliases.obj"):
            add("missing objects: provisional stand-in code (linklib/provisional.obj)", 0,
                {"ours": f"{a_:08x}", "name": n})

    # data sections: offset changes between neighbouring paired symbols (in retail order), charged to the symbol before
    obj_of_data = {}
    for sec, a, n, o, _i in pubs:
        if sec in (2, 3):
            obj_of_data.setdefault(n, o)
    for sec, a, n, o in stats:
        if sec in (2, 3):
            obj_of_data.setdefault(n, o)
    for secname in (".rdata", ".data"):
        lo, hi = rsec[secname]
        dp = sorted(p for p in data_pairs if lo <= p[0] < hi)
        # the longest run in our order too, as in placemap; the rest are out of order
        chain_idx = placemap.chain([(p[0], p[1], p[3]) for p in dp])
        on = [dp[i] for i in chain_idx]
        for a_, b_ in zip(on, on[1:]):
            step = (b_[1] - b_[0]) - (a_[1] - a_[0])
            if step:
                part = secname if secname == ".rdata" else (".data (initialized)" if a_[0] < init_end else ".bss")
                add(f"{part}: order churn (offset change between neighbouring symbols)", step,
                    {"after": a_[3], "object": obj_of_data.get(a_[3], "?"), "before": b_[3],
                     "retail": f"{a_[0]:08x}", "step": step})
        for i in set(range(len(dp))) - set(chain_idx):
            part = secname if secname == ".rdata" else (".data (initialized)" if dp[i][0] < init_end else ".bss")
            add(f"{part}: symbol out of retail's order", 0, {"name": dp[i][3], "object": obj_of_data.get(dp[i][3], "?"),
                                                            "retail": f"{dp[i][0]:08x}", "ours": f"{dp[i][1]:08x}"})
    # .bss extent: each retail symbol the matched code pins owns the slot up to the next pinned symbol; our counterpart's
    # size (to our next symbol) leaves the retail storage beside it with no counterpart of ours; our .bss symbols with no
    # retail pin are the other side. Order does not change these sums; it only moves items (the churn class above).
    contrib = {}
    for line in (LINKDIR / "BEA.map").read_text(errors="replace").splitlines()[:60]:
        m_ = re.match(r"^\s*0003:([0-9a-f]{8})\s+([0-9a-f]{8})H\s+(\S+)", line)
        if m_:
            contrib[m_.group(3)] = (int(m_.group(1), 16), int(m_.group(2), 16))
    our_bss_lo = csec[".data"][0] + contrib[".bss"][0]
    our_bss_hi = our_bss_lo + contrib[".bss"][1]
    r_data_hi = rsec[".data"][1]
    bss_p = sorted((p[0], p[1], p[3]) for p in data_pairs if our_bss_lo <= p[1] < our_bss_hi)
    our3 = sorted({a for a, _n, _o in our_data if csec[".data"][0] <= a < csec[".data"][1]} | {our_bss_hi})
    first = min(bss_p, key=lambda x: x[1])
    retail_bss_lo = first[0] - (first[1] - our_bss_lo)
    rpins = sorted({p[0] for p in data_pairs if p[0] >= retail_bss_lo})
    # v3: per-object .bss extents (pinned-to-pinned slots cross displaced blocks; C, 2026-10-15). Points: every DIR32
    # operand of a matched game function into .bss (retail address = retail operand - addend; a static belongs to the
    # referencing object, a public to the map's), and every 4-byte window of a paired library function where both values
    # fall in .bss (owner: our map's object at our value). An object starts at its lowest retail point; its span runs to
    # the next object's start. Two neighbours that are neighbours in ours too compare their spans (a size difference);
    # otherwise the difference is order.
    pts = []
    our_bss_syms = sorted((a_, o) for a_, n, o in our_data if our_bss_lo <= a_ < our_bss_hi)
    our_bss_starts = [x[0] for x in our_bss_syms]
    code_addr = {(n, o.lower()): a_ for sec, a_, n, o, _i in pubs if sec == 1}
    for src, obj in objects.items():
        c_ = parse_coff(obj); on = obj.name.lower()
        for secnum, symbol in decomp.function_sections(c_):
            r = exp_code.get((symbol, on)); a_ = code_addr.get((symbol, on))
            if r is None or a_ is None:
                continue
            sdata = c_.sections[secnum].data
            for off, si, typ in c_.sections[secnum].relocs:
                if typ != 6:
                    continue
                s_ = c_.symbols[si]
                rv = struct.unpack("<I", rb(r + off, 4))[0]
                if not retail_bss_lo <= rv < r_data_hi:
                    continue
                ov = struct.unpack("<I", cb(a_ + off, 4))[0]
                if not our_bss_lo <= ov < our_bss_hi:
                    continue
                owner_ = on if s_.storage == 3 else obj_of_data.get(s_.name, "?").lower()
                pts.append((rv, ov, owner_))
    for r_, o_, n_, nm, ob, _k in lib_pairs:
        rr, oo = rb(r_, n_), cb(o_, n_)
        for i in range(n_ - 3):
            rv = struct.unpack_from("<I", rr, i)[0]; ov = struct.unpack_from("<I", oo, i)[0]
            if retail_bss_lo <= rv < r_data_hi and our_bss_lo <= ov < our_bss_hi:
                k = bisect.bisect_right(our_bss_starts, ov) - 1
                if k >= 0:
                    own = (our_bss_syms[k][1] or "?").lower()
                    if own not in game_objs and own != "provisional.obj":   # windows are not exact operands: library
                        pts.append((rv, ov, own))                           # points only own library .bss
    spans = object_spans(pts, r_data_hi, our_bss_hi)
    size_net = order_net = 0
    for x in spans:
        if x["comparable"]:
            size_net += x["delta"]
            add(".bss object size: " + ("retail larger" if x["delta"] < 0 else "ours larger"), x["delta"],
                {"object": x["object"], "retail": x["retail"], "retail_span": x["retail_span"], "our_span": x["our_span"],
                 "bytes": x["delta"]})
        else:
            order_net += x["delta"]
            add(".bss object order (span not comparable: next object differs)", x["delta"],
                {"object": x["object"], "retail": x["retail"], "next_retail": x["next_retail"], "next_ours": x["next_ours"],
                 "bytes": x["delta"]})
    bss_objects = spans
    first_r = {}
    first_o = {}
    for rv, ov, ob in pts:
        first_r[ob] = min(first_r.get(ob, rv), rv)
        first_o[ob] = min(first_o.get(ob, ov), ov)
    order_r = sorted(first_r, key=first_r.get)
    order_o = sorted(first_o, key=first_o.get)
    head_r = (first_r[order_r[0]] - retail_bss_lo) if order_r else 0
    head_o = (first_o[order_o[0]] - our_bss_lo) if order_o else 0
    report["bss_split"] = {"retail_bss": [f"{retail_bss_lo:08x}", f"{r_data_hi:08x}"], "retail_bytes": r_data_hi - retail_bss_lo,
                           "our_bss": [f"{our_bss_lo:08x}", f"{our_bss_hi:08x}"], "our_bytes": our_bss_hi - our_bss_lo,
                           "difference": (our_bss_hi - our_bss_lo) - (r_data_hi - retail_bss_lo),
                           "objects": len(order_r), "points": len(pts), "size_net": size_net, "order_net": order_net,
                           "head": [head_r, head_o], "per_object": bss_objects,
                           "note": "retail .bss start estimated from the first pinned symbol's offset in ours; per-object "
                                   "spans from code operands (game) and library-function operands (library)"}

    dsz_r = next(s_[2] for s_ in R.sections if s_[0] == ".data")
    dsz_c = next(s_[2] for s_ in C.sections if s_[0] == ".data")
    report["data_extent"] = {"retail_vsize": dsz_r, "our_vsize": dsz_c, "difference": dsz_c - dsz_r,
                             "retail_initialized_end": f"{init_end:08x}"}

    # imports
    ri, ci = linkcmp.import_table(R), linkcmp.import_table(C)
    imps = linkcmp.compare_imports(ri, ci)
    for d in imps["dlls"]:
        if not d.get("present"):
            add("imports/IAT", 0, {"dll": d["dll"], "missing": True})
            continue
        if not (d["names_in_order"] and d["hints"]):
            add("imports/IAT: entry order or hints differ", 0, {"dll": d["dll"], "entries": d["entries"],
                                                                "names_in_order": d["names_in_order"], "hints": d["hints"]})
    hc = linkcmp.header(C)
    add("imports/IAT: directory size", hc["DataDirectory12"][1] - hdr["DataDirectory12"][1],
        {"retail": hdr["DataDirectory12"], "ours": hc["DataDirectory12"]})
    report["imports"] = imps

    # Rich header
    rr_, rc_ = rich(R), rich(C)
    cr, cc = collections.Counter({(a, b): n for a, b, n in rr_}), collections.Counter({(a, b): n for a, b, n in rc_})
    for k in sorted(set(cr) | set(cc)):
        if cr[k] != cc[k]:
            add("Rich header", 8, {"comp_id": f"{k[0]:#x}/{k[1]}", "retail": cr[k], "ours": cc[k]})
    report["rich"] = {"retail": rr_, "ours": rc_}

    # header fields (all derive from the layout)
    for k in hdr:
        if k != "TimeDateStamp" and hdr[k] != hc[k]:
            add("header fields (derived from section sizes and addresses)", 4, {"field": k, "retail": hdr[k], "ours": hc[k]})

    # resources
    res = linkcmp.compare_resources(linkcmp.resources(R), linkcmp.resources(C))
    report["resources"] = res
    _imp = hc["DataDirectory1"]
    _iat = hc["DataDirectory12"]
    _rsrc = hc["DataDirectory2"]
    _rd = next(s_ for s_ in C.sections if s_[0] == ".rdata")
    report["aligned"] = aligned_compare(R, C, [(BASE + _iat[0], BASE + _iat[0] + _iat[1]),
                                               (BASE + _imp[0], _rd[1] + max(_rd[2], _rd[4])),
                                               (BASE + _rsrc[0], BASE + _rsrc[0] + _rsrc[1])])
    add(".rsrc: whole section at another address (derived from the .data/.bss extent)", 0,
        {"retail_rva": hdr["DataDirectory2"][0], "our_rva": hc["DataDirectory2"][0], **res})

    report["library_pairs"] = [[f"{p[0]:08x}", f"{p[1]:08x}", p[2], p[3], p[4]] for p in lib_pairs]
    report["root_causes"] = {k: {"bytes": v["bytes"], "items": v["items"], "list": v["list"]} for k, v in
                             sorted(classes.items(), key=lambda kv: -kv[1]["bytes"])}
    report["pairs"] = {"code": len(code_pairs), "data": len(data_pairs), "library": len(lib_pairs),
                       "library_unpaired_ours": len(lib_unpaired), "funclets": len(funclet_pairs)}

    # ---------------------------------------------------------------- areas and fixability
    OWNERS = [   # (class prefix, area, fixable from source?)
        (".text game: initializer funclets", "initializer set", "source; mixermap/texture ZERO_FVECTOR are a candidate concession"),
        (".text game: inline/ICF", "emission / ICF", "source (inline-ness, defining object), then ICF survivors follow"),
        (".text game: extra code", "placement + the rows' owners", "source (our helpers retail inlined or lacks)"),
        (".text game: missing code", "placement + the rows' owners", "source"),
        (".text game: function size", "placement + the rows' owners", "source (unmatched rows, COMDAT carries, padding)"),
        (".text game: large span", "placement", "source; listing truncated, inspect the event"),
        (".text game: own function out of order", "in-object order", "source (definition order, statics after first caller); net 0 when only order"),
        ("library: libcmt", "CRT identity", "not source: needs retail's exact LIBCMT build; else concession"),
        ("library: d3dx9", "library identity", "not source: d3dx9 build/version; pairing churn among similar codecs inflates abs"),
        ("library: nvtristrip", "NvTriStrip prebuilt library", "not source: prebuilt UT2003 lib (RemoveSmallStrips differs)"),
        ("library: dxerr9", "library identity", "not source"),
        ("missing objects", "missing objects", "source: write the missing objects"),
        (".rdata", "link data", "source (definition order of strings/constants/vtables per object); some follow code"),
        (".data (initialized)", "link data", "source"),
        (".bss extent: retail storage", "link data + missing objects", "source: the missing statics/objects named by the object column"),
        (".bss extent: our storage", "link data", "source: our .bss symbols retail's code never pins (counterparts of the missing side, or extra)"),
        (".bss extent: our item larger", "link data", "source (our declared size)"),
        (".bss", "link data", "source (PCH LIFO order rule); dynamic-init family has candidate concessions"),
        ("imports/IAT", "imports", "link inputs (import-lib member order); bounded open puzzle"),
        ("Rich header", "imports/objects", "derived: object and import counts (13x 0x0b, import pulls)"),
        ("header fields", "derived", "follows section sizes"),
        (".rsrc", "derived", "follows the .data/.bss extent; resource bytes equal when rebased"),
    ]


    def owner(cls: str) -> tuple[str, str]:
        return next(((o, f) for k, o, f in OWNERS if cls.startswith(k)), ("?", "?"))


    def net_of(v: dict) -> int:
        return sum(x.get("step", x.get("bytes", 0)) for x in v["list"] if isinstance(x.get("step", x.get("bytes", 0)), int))


    L = []
    w = L.append
    w("# Whole-exe difference inventory")
    w("")
    _tx = next(s_[2] for s_ in C.sections if s_[0] == ".text") - next(s_[2] for s_ in R.sections if s_[0] == ".text")
    w(f"**Headline: .text size vs retail {_tx:+,} bytes (0 needed so .rdata/.data land at retail's RVAs; any value "
      f"inside the same 4 KB rounding also works, which is {0x1000 - (next(s_[2] for s_ in R.sections if s_[0] == '.text') % 0x1000):,} "
      f"bytes of slack above retail's size and {(next(s_[2] for s_ in R.sections if s_[0] == '.text') - 1) % 0x1000:,} below).** "
      f".bss extent {report['bss_split']['difference']:+,} bytes (moves .rsrc).")
    w("")
    w(f"Candidate: `{LINKDIR}/BEA.exe` (checkout `{CHECKOUT}`, {subprocess_head()}), against the pinned retail specimen. "
      "Generated by `tools/inventory.py`; rerun after each integration (see the end).")
    w("")
    w("## 1. Bytes at the same address")
    w("")
    w("Each retail byte that differs at its own address is charged to the item that holds it. *displaced* = a paired "
      "function or symbol that sits at another address (moved by an earlier size change); its own bytes, compared at its "
      "own address, are identical, differ only in references (*ref*: target corresponds; *ref to unpaired target*: the "
      "retail target is an item we have not paired; *ref to a different target*: the target corresponds to another item, "
      "typically an ICF survivor or a different symbol), or in *content*. *between items*: unnamed bytes (strings, "
      "constants, unannotated code) compared at the displacement of the paired items on both sides.")
    w("")
    w("| section | bytes | equal | displaced, identical | ref (target corresponds) | ref to unpaired target | ref to a different target | content | unpaired | other |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for sec, v in report["same_address"].items():
        c = v["categories"]
        def tot(pred):
            return sum(n for k, n in c.items() if pred(k))
        ident = tot(lambda k: k.endswith("identical") or "identical (" in k)
        ref = tot(lambda k: k.endswith(": ref") or ": ref (" in k)
        unp_t = tot(lambda k: "ref to unpaired target" in k)
        diff_t = tot(lambda k: "ref to a different target" in k)
        content = tot(lambda k: k.endswith("content") or "content (" in k)
        unp = tot(lambda k: k.startswith("unpaired"))
        other = v["bytes"] - c.get("equal", 0) - ident - ref - unp_t - diff_t - content - unp
        w(f"| {sec} | {v['bytes']:,} | {c.get('equal', 0):,} | {ident:,} | {ref:,} | {unp_t:,} | {diff_t:,} | {content:,} | {unp:,} | {other:,} |")
    w("")
    w("*other*: header fields and Rich bytes, import tables, int3/zero padding, .bss zero in both, and the relocated "
      ".rsrc. Full categories in the JSON (`same_address`).")
    w("")
    w("**.rsrc** (0 of 12,112 equal): the section sits at RVA "
      f"{hc['DataDirectory2'][0]:#x} instead of {hdr['DataDirectory2'][0]:#x} because .data's virtual size (with .bss) "
      f"is {report['data_extent']['our_vsize']:#x} instead of {report['data_extent']['retail_vsize']:#x} "
      f"({report['data_extent']['difference']:+,} bytes); resource leaves equal in order: {res['leaves_equal_in_order']}, "
      f"image equal with RVAs rebased: {res['image_equal_rebased']}. So .rsrc has no difference of its own: it follows "
      "the .bss extent, and becomes equal when that does.")
    w("")
    w(f"**Layout totals.** .text: our game code ends {lchain[0][1] - lib_r_lo if lchain else 0:+} bytes from retail "
      f"(library starts {report['library_region']['ours'][0]} vs {lib_r_lo:08x}); the funclet block moves "
      f"{(our_funclet_lo - FUNCLETS):+} and has the same length ({funclet_block['retail_bytes'] if funclet_block else '?'} bytes). "
      f".rdata starts at {csec['.rdata'][0]:08x} (retail {rsec['.rdata'][0]:08x}), .data at {csec['.data'][0]:08x} "
      f"(retail {rsec['.data'][0]:08x}): the .text growth crosses a 4 KB boundary, so every later section moves by 0x1000.")
    w("")
    w(f"Placement chain (tools/placemap.py): {pm['pairs']} paired game functions, {pm['chain']} in order on both sides, "
      f"offset {pm['start_offset']:+} at the first and {pm['end_offset']:+} at the last; {len(pm['misplaced'])} functions "
      "out of order (JSON `misplaced_functions`).")
    w("")
    w("## 2. Root causes")
    w("")
    w("*net* = signed bytes the class adds (+) or removes (−) from the layout; *abs* = sum of |step| (order churn "
      "counts both ways, so abs overstates where items swap); *items* = events or entries. Every class below is an "
      "open item for byte identity.")
    w("")
    w("| class | net | abs | items | owner | fix |")
    w("|---|---:|---:|---:|---|---|")
    for k, v in report["root_causes"].items():
        o, f = owner(k)
        w(f"| {k} | {net_of(v):+,} | {v['bytes']:,} | {v['items']} | {o} | {f} |")
    w("")
    uc = report["same_address"]
    unexplained = sum(n for sec in uc.values() for k, n in sec["categories"].items() if k.startswith("unpaired"))
    between_content = sum(n for sec in uc.values() for k, n in sec["categories"].items() if k.startswith("between items, displaced: content"))
    content_b = sum(x["content_bytes"] for x in report["content_items"])
    b_ = report["bss_split"]
    w("### .bss extent split")
    w("")
    w(f"Retail .bss {b_['retail_bss'][0]}..{b_['retail_bss'][1]} ({b_['retail_bytes']:,} bytes; start estimated), ours "
      f"{b_['our_bss'][0]}..{b_['our_bss'][1]} ({b_['our_bytes']:,}): **{b_['difference']:+,}**. Per object ({b_['objects']} objects, "
      f"{b_['points']:,} operand points, game and library): spans of neighbours that are neighbours in both images differ by "
      f"{b_['size_net']:+,} (size); the rest, {b_['order_net']:+,}, sits where the next object differs (order). Head before the "
      f"first object: retail {b_['head'][0]:,}, ours {b_['head'][1]:,}. Size items are listed below (`.bss object size`); "
      "the unreferenced placeholders in notes/link-reconstruction.md account for most of the retail-larger side.")
    w("")
    w("### If .text were aligned")
    w("")
    w("What the data sections compare like once `.text` is inside the window, so every later section starts at its "
      "retail address: each compared at the same offset from its start, our pointers into our own data sections moved "
      "by their section's shift (addresses, and RVAs in the import tables and the resource directory). The remaining "
      "differences are the next layer: code pointers (the code inside `.text` still moved), data pointers (data order "
      "and sizes) and content.")
    w("")
    w("| section | retail bytes | ours | compared | equal | code pointer | data pointer | content | first content difference |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for _n, _v in report["aligned"].items():
        w(f"| {_n} | {_v['retail_bytes']:,} | {_v['our_bytes']:,} | {_v['compared']:,} | {_v['equal']:,} "
          f"({100.0 * _v['equal'] / max(_v['compared'], 1):.2f}%) | {_v['code_pointer']:,} | {_v['data_pointer']:,} | {_v['content']:,} "
          f"| {_v['first_content_difference'] or '-'} |")
    w("")
    w("## 3. Unexplained (reported, not yet attributed)")
    w("")
    w(f"- Retail bytes in no paired item and not interpolable: **{unexplained:,}** "
      + ", ".join(f"{sec} {sum(n for k, n in v['categories'].items() if k.startswith('unpaired')):,}"
                  for sec, v in uc.items()) + ".")
    w(f"- Unnamed bytes between items that match under neither neighbour's displacement: **{between_content:,}** "
      "(interpolated, not paired; lenient: a byte counts as identical if it matches under either neighbour's displacement).")
    w(f"- Pairing added in v2: {report['v2_pairs']['eh']} EH tables ({report['v2_pairs']['eh_bytes']:,} bytes: FuncInfo, "
      f"unwind, try-block, IP-to-state and handler arrays, from the handler stubs in the paired funclet block) and "
      f"{report['v2_pairs']['content_chunks']} unnamed data chunks ({report['v2_pairs']['content_bytes']:,} bytes) found by "
      "content near their neighbours' displacement.")
    w(f"- Bytes inside paired items that differ in content (not a reference): **{content_b:,}** in "
      f"{len(report['content_items'])} items (mostly data spans that run into neighbouring unnamed data; list in JSON "
      "`content_items`).")
    w("- Classes whose listing was truncated (`large span`) or whose sign mixes order churn with size (abs ≫ |net|).")
    w("")
    w("## 4. Details (top items per class)")
    for k, v in report["root_causes"].items():
        w("")
        w(f"### {k} ({v['items']} items)")
        for x in sorted(v["list"], key=lambda x: -abs(x.get("step", x.get("bytes", 0)) if isinstance(x.get("step", x.get("bytes", 0)), int) else 0))[:8]:
            w("- " + ", ".join(f"{a}: {str(b)[:90]}" for a, b in x.items()))
    w("")
    w("## Rerun")
    w("")
    w("```")
    w("python3 tools/decomp.py check && python3 tools/link.py && python3 tools/inventory.py")
    w("```")
    (OUT / "INVENTORY.md").write_text("\n".join(L) + "\n")

    # unpaired ranges by 16 KB bucket, for the report
    ub = collections.Counter()
    for sec in (".rdata", ".data"):
        lo, hi = rsec[sec]
        for a in range(lo, hi):
            if (RB[a - BASE] != CB[a - BASE] or not CM[a - BASE]) and item_of(a) is None and \
                    not any(x <= a < y for x, y, _l in ranges_known) and interpolated(a)[0] is None and \
                    not (sec == ".data" and a >= init_end):
                ub[(sec, a & ~0x3FFF)] += 1
    runs_ = []
    for sec in (".text", ".rdata", ".data"):
        lo, hi = rsec[sec]
        if sec == ".data":
            hi = init_end
        a = lo
        while a < hi:
            if (RB[a - BASE] != CB[a - BASE] or not CM[a - BASE]) and item_of(a) is None and \
                    not any(x <= a < y for x, y, _l in ranges_known) and interpolated(a)[0] is None:
                b = a
                while b < hi and item_of(b) is None and not any(x <= b < y for x, y, _l in ranges_known) and \
                        interpolated(b)[0] is None:
                    b += 1
                k = bisect.bisect_right(pstarts, a) - 1
                prev_ = pairs[k] if k >= 0 else None
                nxt_ = pairs[k + 1] if k + 1 < len(pairs) else None
                runs_.append({"section": sec, "retail": f"{a:08x}", "bytes": b - a, "region": region_of(a),
                              "after": prev_[3] if prev_ else None, "before": nxt_[3] if nxt_ else None,
                              "preview": rb(a, min(b - a, 48)).hex(),
                              "text": "".join(chr(x) if 32 <= x < 127 else "." for x in rb(a, min(b - a, 48)))})
                a = b
            else:
                a += 1
    report["unpaired_runs"] = sorted(runs_, key=lambda x: -x["bytes"])
    report["unpaired_buckets"] = {f"{s_} {b:08x}": n for (s_, b), n in sorted(ub.items())}
    json.dump(report, open(OUT / "inventory.json", "w"), indent=1, default=str)
    with open(OUT / "INVENTORY.md", "a") as f:
        f.write("\n## Unpaired bytes by 16 KB bucket (retail address)\n\n")
        f.write("First version: the large .rdata buckets 005f4000..0060c000 hold library data (DxErr9's error-name and\n"
                "description strings, d3dx9 tables) and the EH FuncInfo/unwind tables (0x5f0000, 0x610000); 005e8000 holds\n"
                "float tables. None of these are pinned by symbols the matched game code implies, so they are not paired\n"
                "yet; next step: pair library data by our map's library publics and EH tables by their parent function.\n\n")
        f.write("| bucket | unpaired bytes |\n|---|---:|\n")
        for k, n in sorted(ub.items(), key=lambda kv: -kv[1])[:20]:
            f.write(f"| {k[0]} {k[1]:08x} | {n:,} |\n")

    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--link", type=Path, default=decomp.ROOT / "local-data/link", help="a tools/link.py output folder")
    ap.add_argument("--out", type=Path, default=decomp.ROOT / "local-data/inventory")
    a = ap.parse_args()
    report = run(a.link.resolve(), a.out.resolve())
    print(f"{a.out / 'INVENTORY.md'}: {len(report['root_causes'])} root-cause classes, "
          f"bss {report['bss_split']['difference']:+,} bytes")


if __name__ == "__main__":
    main()
