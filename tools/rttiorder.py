#!/usr/bin/env python3
"""Compare each object's RTTI complete-object locators (??_R4) with retail's order, and search for the creation order
that gives retail's.

When one function brings out many classes' vtables (a factory), Visual C++ 6 lays out their RTTI records close to the
reverse of the order in which the front end created the classes' type records; a forward declaration `class X;` or an
elaborated `class X *` member creates the record (notes/link-reconstruction.md, RTTI order). So a declaration line
naming the classes in the reverse of retail's walk, placed before their definitions, reproduces retail's order where
the records form one batch. That line proves retail's creation order, not where the original's mentions were.

    python3 tools/rttiorder.py survey --expected E.json [--json OUT]
        every object with two or more pinned locators: our order against retail's (E: tools/linkcmp.py
        --write-expected), as the longest run in retail's order
    python3 tools/rttiorder.py search OBJ --expected E.json [--cap N]
        try the reverse-retail declaration line, retail's order, then greedy single additions (at most N compiles,
        default 30), each compiled from a copy of the source in a temporary folder under build/ (src/ is never
        written). A variant is accepted only if it keeps the file's line count (the line replaces a blank line after
        the includes) and every function stays byte-identical to build/'s object.

Reads build/*.obj (run a check first) and the sources; writes only --json.
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import binfmt  # noqa: E402
import bsscreate  # noqa: E402
import decomp  # noqa: E402

PCH_INCLUDE = re.compile(r'\s*#\s*include\s*"(\.\.[\\/])*common\.h"', re.I)


def longest_run(ranks: list[int]) -> int:
    """The length of the longest increasing subsequence: how many items sit in retail's relative order."""
    tails: list[int] = []
    for r in ranks:
        k = bisect.bisect_left(tails, r)
        if k == len(tails):
            tails.append(r)
        else:
            tails[k] = r
    return len(tails)


def locators(obj: Path) -> list[str]:
    """The object's ??_R4 symbols in section order."""
    c = binfmt.parse_coff(obj)
    out = []
    for k in sorted(c.sections):
        out += [x.name for x in c.symbols.values() if x.section == k and x.name.startswith("??_R4")]
    return out


def address(implied: dict, name: str) -> int | None:
    a = implied.get(name)
    return int(a, 16) if isinstance(a, str) else a


def compare(ours: list[str], implied: dict) -> dict | None:
    """Our order and retail's for the pinned locators; None when fewer than two are pinned."""
    pinned = [n for n in ours if address(implied, n) is not None]
    if len(pinned) < 2:
        return None
    retail = sorted(pinned, key=lambda n: address(implied, n))
    rank = {n: i for i, n in enumerate(retail)}
    return {"ours": pinned, "retail": retail, "run": longest_run([rank[n] for n in pinned]), "n": len(pinned)}


def class_of(locator: str) -> str | None:
    """The class a locator belongs to (??_R4CName@@6B@ or @@6BBase@@@); None for templates and nested names."""
    m = re.match(r"\?\?_R4(\w+)@@6B", locator)
    return m.group(1) if m and "?" not in m.group(1) else None


def variant(text: str, decls: list[str], pch: bool) -> tuple[str, bool]:
    """The source with `class X;` for each name on one line after the precompiled-header include (or at the top for
    a source without it), and whether the first blank line after the includes could absorb it (line count kept)."""
    lines = text.split("\n")
    k = next((i for i, l in enumerate(lines) if PCH_INCLUDE.match(l)), None) if pch else None
    at = k + 1 if k is not None else 0
    line = "".join(f"class {d};" for d in decls)
    j = at
    while j < len(lines) and (lines[j].lstrip().startswith("#") or lines[j].strip().startswith("//")):
        j += 1
    kept = j < len(lines) and lines[j].strip() == ""
    if kept:
        del lines[j]
    lines.insert(at, line)
    return "\n".join(lines), kept


def code_bytes(obj: Path) -> dict[str, bytes]:
    c = binfmt.parse_coff(obj)
    out = {}
    for k, s in c.sections.items():
        if s.code:
            name = next((x.name for x in c.symbols.values() if x.section == k and x.value == 0 and x.storage in (2, 3)
                         and not x.name.startswith((".", "$"))), None)
            if name:
                out[name] = bytes(s.data)
    return out


def search(obj: Path, implied: dict, cap: int) -> dict:
    src = bsscreate.source_of(obj)
    if src is None:
        raise SystemExit(f"{obj}: no source")
    base = compare(locators(obj), implied)
    if base is None:
        raise SystemExit(f"{obj}: fewer than two pinned locators")
    rank = {n: i for i, n in enumerate(base["retail"])}
    classes = list(dict.fromkeys(c for c in map(class_of, base["retail"]) if c))
    text = src.read_text(encoding="latin-1")
    flags = decomp.flags_for(src)
    pch = any(f.startswith("/Yu") for f in flags)
    reference = code_bytes(obj)
    tries, results = 0, []
    decomp.BUILD.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=decomp.BUILD, prefix="rttiorder-") as tmp:
        copy = Path(tmp) / src.relative_to(decomp.ROOT / "src")
        copy.parent.mkdir(parents=True, exist_ok=True)
        probe = Path(tmp) / "probe.obj"

        def score(decls: list[str]) -> tuple[int, bool]:
            nonlocal tries
            tries += 1
            body, kept = variant(text, decls, pch)
            copy.write_text(body, encoding="latin-1")
            probe.unlink(missing_ok=True)
            bsscreate._cl(copy, flags + [f"/I{decomp.winpath(src.parent)}"], ["/c", f"/Fo{decomp.winpath(probe)}"])
            if not probe.exists():
                return -1, False
            ours = [n for n in locators(probe) if n in rank]
            run = longest_run([rank[n] for n in ours])
            same = kept and code_bytes(probe) == reference
            results.append({"decls": decls, "run": run, "accepted": same})
            return run, same

        best = (base["run"], [], False)
        for decls in (classes[::-1], classes):
            run, ok = score(decls)
            if (run, ok) > (best[0], best[2]):
                best = (run, decls, ok)
            if run == base["n"]:
                break
        current = best[1] if best[0] > base["run"] else []
        while best[0] < base["n"] and tries < cap:
            step = None
            for c in classes:
                if c in current:
                    continue
                for pos in (0, len(current)):
                    if tries >= cap:
                        break
                    d = current[:pos] + [c] + current[pos:]
                    run, ok = score(d)
                    if step is None or run > step[0]:
                        step = (run, d, ok)
            if not step or step[0] <= best[0]:
                break
            best, current = step, step[1]
    return {"object": obj.name, "n": base["n"], "before": base["run"], "after": best[0], "decls": best[1],
            "accepted": best[2], "compiles": tries, "trials": results}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("survey")
    s.add_argument("--expected", type=Path, required=True)
    s.add_argument("--json", type=Path)
    f = sub.add_parser("search")
    f.add_argument("object")
    f.add_argument("--expected", type=Path, required=True)
    f.add_argument("--cap", type=int, default=30)
    args = ap.parse_args(argv)
    implied = json.loads(args.expected.read_text())["implied"]
    if args.cmd == "survey":
        rows = {}
        for obj in sorted(decomp.BUILD.rglob("*.obj")):
            r = compare(locators(obj), implied)
            if r:
                rows[str(obj.relative_to(decomp.BUILD))] = r
        differ = {k: v for k, v in rows.items() if v["run"] < v["n"]}
        print(f"objects with two or more pinned locators: {len(rows)}; in retail order: {len(rows) - len(differ)}; "
              f"differing: {len(differ)}; locators on the in-order runs: {sum(v['run'] for v in rows.values())} of "
              f"{sum(v['n'] for v in rows.values())}")
        for k, v in sorted(differ.items(), key=lambda kv: kv[1]["run"] - kv[1]["n"]):
            print(f"  {k:40s} {v['run']:4d} of {v['n']:4d}")
        if args.json:
            args.json.write_text(json.dumps(rows, indent=1))
        return 0
    obj = next((p for p in decomp.BUILD.rglob("*.obj") if p.stem.lower() == Path(args.object).stem.lower()), None)
    if obj is None:
        raise SystemExit(f"{args.object}: no such object in {decomp.BUILD}")
    r = search(obj, implied, args.cap)
    print(f"{r['object']}: {r['before']} -> {r['after']} of {r['n']} in retail order after {r['compiles']} compiles; "
          f"{'accepted (line count kept, code identical)' if r['accepted'] else 'not accepted'}")
    if r["decls"]:
        print("".join(f"class {d};" for d in r["decls"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
