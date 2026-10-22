#!/usr/bin/env python3
"""Predict an object's .bss layout from the points where Visual C++ 6's front end creates its symbols.

Under /Yu (the precompiled header retail was built with) the compiler lays out a source's .bss in two groups:

  1. uninitialized definitions and objects of classes with constructors (however initialized), in REVERSE order of
     symbol creation;
  2. definitions with an explicit zero initializer (`= 0`, `= NULL`; nonzero ones go to .data) and plain-data
     aggregates initialized with braces, even at run time (`WCHAR key[50] = {..}`), in definition order.

A file-scope or class-static symbol is created at its definition, or earlier at its first mention inside a function
body: an inline body in a header counts whether or not anything calls it (a class static through an in-class
accessor, a global through an `extern` declaration). A bare `extern` declaration creates nothing. A function-local
static is created at its first use in an expression; its declaration creates it only when it has an initializer.
Probes and the validation (this predicts every multi-symbol object of the build): notes/link-reconstruction.md.

    python3 tools/bsscreate.py OBJ...            our order, the prediction and each symbol's creation point
    python3 tools/bsscreate.py --all             the count of objects predicted exactly
    python3 tools/bsscreate.py --expected E.json OBJ...   also retail's rank per symbol (tools/linkcmp.py
                                                  --write-expected), with the creation point retail's order implies

Preprocessor output is cached under build/bsscreate/. Sources on config/no-pch.txt are skipped (their order is a
name hash). Reads only.
"""
from __future__ import annotations

import argparse
import json
import ntpath
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import binfmt  # noqa: E402
import decomp  # noqa: E402

TOKEN = re.compile(r'L?"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|0[xX][0-9a-fA-F]+\w*|\d[\w.]*|::|->|<<|>>|[^\s\w]')
MATHS = {"ZERO_FVECTOR", "ID_FMATRIX", "ZERO_FVECTOR2", "ID_FMATRIX2"}


def _cl(src: Path, flags: list[str], output: list[str]) -> subprocess.CompletedProcess:
    """Run CL on src as the build does. A source outside src/ (a test's probe) is named by its own path, with src/
    on the include path; a source in src/ by the path the retail build used (decomp.original_path)."""
    inside = (decomp.ROOT / "src") in src.resolve().parents
    name = decomp.original_path(src) if inside else decomp.winpath(src)
    extra = [] if inside else [f"/I{decomp.winpath(decomp.ROOT / 'src')}"]
    with decomp.prefix_lock(), tempfile.TemporaryFile(mode="w+", errors="replace") as so, \
            tempfile.TemporaryFile(mode="w+", errors="replace") as se:
        paths = decomp.compiler_paths()
        r = subprocess.run(["wine", paths["CL"], "/nologo", *output, *flags, *extra, name],
                           env=decomp.compiler_env(paths), stdout=so, stderr=se, cwd=src.parent)
        so.seek(0)
        se.seek(0)
        return subprocess.CompletedProcess(r.args, r.returncode, so.read(), se.read())


def compile_probe(src: Path, obj: Path) -> subprocess.CompletedProcess:
    """Compile a probe source (anywhere) with the build's flags and precompiled header, for tests."""
    obj.unlink(missing_ok=True)
    return _cl(src, decomp.flags_for(src), ["/c", f"/Fo{decomp.winpath(obj)}"])


def preprocess(src: Path, cache: Path | None = None) -> str:
    """The source as the compiler sees it (CL /E with its build flags, the precompiled-header switches dropped)."""
    out = (cache / (src.stem + ".i")) if cache else None
    if out and out.exists() and out.stat().st_mtime > src.stat().st_mtime:
        return out.read_text(errors="replace")
    flags = [f for f in decomp.flags_for(src) if not f.startswith(("/Yu", "/Fp", "/Yc"))]
    text = _cl(src, flags, ["/E"]).stdout
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    return text


def tokens(text: str):
    """(token, file, line), following the preprocessor's #line markers."""
    f, ln = "?", 0
    for raw in text.split("\n"):
        ln += 1
        s = raw.strip()
        if s.startswith("#"):
            m = re.match(r'#\s*(?:line\s+)?(\d+)\s+"([^"]*)"', s)
            if m:
                ln, f = int(m.group(1)) - 1, m.group(2)
            continue
        for t in TOKEN.findall(raw):
            yield t, f, ln


def parse_target(name: str):
    """(identifier, kind, class, function) for a .bss symbol: kind local, member or global."""
    m = re.match(r"_\?(\w+)@\?[0-9A-Z]+@?\?\?(\w+)@(?:(\w+)@)?@", name)
    if m:
        return m.group(1), "local", m.group(3), m.group(2)
    m = re.match(r"\?(\w+)@(\w+)@(?:\w+@)*@[012]", name)
    if m:
        return m.group(1), "member", m.group(2), None
    m = re.match(r"\?(\w+)@@3", name)
    if m:
        return m.group(1), "global", None, None
    if name.startswith("_") and not name.startswith(("_?", "_$")):
        return name[1:], "global", None, None
    return None


class Point:
    """Where a symbol is created and defined; its initializer form."""
    def __init__(self):
        self.created = None      # token index
        self.where = None        # 'file:line (how)'
        self.defined = None      # token index of the definition (a local's declaration)
        self.def_where = None
        self.init = None         # None (no initializer), 'const', 'brace' (plain aggregate), 'other'


def analyse(text: str, targets: dict) -> dict:
    """targets: symbol -> parse_target(). Returns symbol -> Point."""
    want = {}
    for sym, (ident, *_rest) in targets.items():
        want.setdefault(ident, []).append(sym)
    pts = {s: Point() for s in targets}
    toks = list(tokens(text))
    stack = []                       # ('class', name) | ('func', name, class) | ('block',) | ('init',) | ('ns',) | ('enum',)
    stmts = [[]]
    for idx, (t, f, ln) in enumerate(toks):
        stmt = stmts[-1]
        func = next((s for s in reversed(stack) if s[0] == "func"), None)
        if t == "{":
            if func:
                stack.append(("block",))
            elif "namespace" in stmt or (stmt[:1] == ["extern"] and len(stmt) > 1 and stmt[1].startswith('"')):
                stack.append(("ns",))
            elif any(k in stmt for k in ("class", "struct", "union")) and "(" not in stmt and "=" not in stmt:
                name = next((stmt[i + 1] for i, x in enumerate(stmt) if x in ("class", "struct", "union")
                             and i + 1 < len(stmt) and re.match(r"[A-Za-z_]", stmt[i + 1])), "?")
                stack.append(("class", name))
            elif "enum" in stmt:
                stack.append(("enum",))
            elif "=" in stmt:
                stack.append(("init",))
            elif ")" in stmt:
                p = stmt.index("(")
                cls = stmt[p - 3] if p >= 3 and stmt[p - 2] == "::" else next(
                    (s[1] for s in reversed(stack) if s[0] == "class"), None)
                stack.append(("func", stmt[p - 1] if p else "?", cls))
            else:
                stack.append(("ns",))
            stmts.append([])
            continue
        if t == "}":
            if stack:
                stack.pop()
            if len(stmts) > 1:
                stmts.pop()
            stmts[-1].clear()
            continue
        if t == ";":
            stmt.clear()
            continue
        stmt.append(t)
        for sym in want.get(t, ()):
            ident, kind, cls, fn = targets[sym]
            pt = pts[sym]
            place = f"{ntpath.basename(f)}:{ln}"
            if kind == "local":
                if func and func[1] == fn:
                    if "static" in stmt and pt.defined is None:
                        pt.defined, pt.def_where = idx, place
                    elif "static" not in stmt and pt.defined is not None and pt.created is None:
                        pt.created, pt.where = idx, f"{place} (first use in {fn})"
                continue
            if func:
                if kind == "member" and not (stmt[-3:-1] == [cls, "::"] or func[2] == cls
                                             or any(s[0] == "class" and s[1] == cls for s in stack)):
                    continue
                if pt.created is None:
                    pt.created, pt.where = idx, f"{place} (body of {func[1]})"
                continue
            if any(s[0] in ("class", "init", "enum") for s in stack) or "extern" in stmt or "typedef" in stmt:
                continue
            if kind == "member" and not (len(stmt) >= 3 and stmt[-2] == "::" and stmt[-3] == cls):
                continue
            if pt.defined is None:
                pt.defined, pt.def_where = idx, place
                if pt.created is None:
                    pt.created, pt.where = idx, f"{place} (definition)"
    names = {v[0] for v in targets.values()} | MATHS
    for sym, pt in pts.items():
        if pt.defined is not None:
            pt.init = initializer(toks, pt.defined, names)
            if targets[sym][1] == "local" and (pt.init or pt.created is None):
                pt.created, pt.where = pt.defined, f"{pt.def_where} (declaration" + (
                    " with initializer)" if pt.init else ", never used)")
    return pts


def initializer(toks, i: int, names: set) -> str | None:
    """The initializer form of the declarator at token i: None, 'const', 'brace' (no constructor calls) or 'other'."""
    j, depth, eq = i + 1, 0, None
    while j < len(toks):
        x = toks[j][0]
        if x in "([{":
            depth += 1
        elif x in ")]}":
            depth -= 1
        elif depth == 0 and x == "=":
            eq = j
        elif depth == 0 and x in (";", ","):
            break
        j += 1
    if eq is None:
        return None
    init = [t for t, _f, _l in toks[eq + 1:j]]
    if all(re.match(r'(?:\d|0[xX]|["\']|L")', a) or a in ("NULL", "TRUE", "FALSE", "true", "false")
           or re.fullmatch(r"[^\w\s]+", a) or (re.fullmatch(r"[A-Z][A-Z0-9_]+", a) and a not in names) for a in init):
        return "const"
    if "{" in init and not any(re.match(r"[A-Za-z_]", a) and b == "(" for a, b in zip(init, init[1:])):
        return "brace"
    return "other"


def bss_symbols(obj: Path):
    """The object's .bss symbols in our order, and those its dynamic initializers or guards make run-time ones."""
    c = binfmt.parse_coff(obj)
    syms = []
    for k, sec in c.sections.items():
        if sec.name == ".bss":
            s = sorted((x.value, x.name) for x in c.symbols.values()
                       if x.section == k and not x.name.startswith((".", "??_C", "$")))
            if s:
                syms = [n for _v, n in s]
    names = {i: s.name for i, s in c.symbols.items()}
    dyn = set()
    for k, sec in c.sections.items():
        if any(s.section == k and s.name.startswith("_$E") for s in c.symbols.values()):
            dyn.update(names[r[1]] for r in sec.relocs if r[1] in names)
    guards = {m.group(1) for n in syms for m in [re.match(r"_\?\$S\d+@\?[0-9A-Z]+@?\?\?(\w+)@", n)] if m}
    return syms, dyn, guards


def predict(obj: Path, text: str):
    """(ours, predicted, points) for the object's resolvable .bss symbols; None when fewer than two."""
    syms, dyn, guards = bss_symbols(obj)
    targets = {n: t for n in syms for t in [parse_target(n)] if t}
    if len(targets) < 2:
        return None
    pts = analyse(text, targets)
    group1, group2 = [], []
    for n, (ident, kind, cls, fn) in targets.items():
        pt = pts[n]
        if pt.created is None or pt.defined is None:
            continue
        if kind == "local":
            second = pt.init is not None and fn not in guards
        else:
            second = pt.init == "const" or pt.init == "brace" or (pt.init == "other" and n not in dyn)
        (group2 if second else group1).append(n)
    order = sorted(group1, key=lambda n: -pts[n].created) + sorted(group2, key=lambda n: pts[n].defined)
    ours = [n for n in syms if n in order]
    return ours, order, pts, set(group2)


def source_of(obj: Path) -> Path | None:
    return next((p for p in decomp.sources() if p.stem.lower() == obj.stem.lower()), None)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("objects", nargs="*", help="object names (e.g. DXWater)")
    ap.add_argument("--all", action="store_true", help="every object of the build; prints the count predicted exactly")
    ap.add_argument("--build", type=Path, default=decomp.BUILD, help="the objects (default: build/)")
    ap.add_argument("--expected", type=Path, help="a tools/linkcmp.py --write-expected file: show retail's order")
    args = ap.parse_args(argv)
    cache = decomp.BUILD / "bsscreate"
    nopch = {n.lower() for n in decomp.no_pch()}
    implied = json.loads(args.expected.read_text())["implied"] if args.expected else None
    objs = sorted(args.build.rglob("*.obj")) if args.all else [
        next(p for p in args.build.rglob("*.obj") if p.stem.lower() == o.lower()) for o in args.objects]
    exact, differ = 0, []
    for obj in objs:
        src = source_of(obj)
        if not src or src.name.lower() in nopch:
            continue
        r = predict(obj, preprocess(src, cache))
        if not r:
            continue
        ours, order, pts, second = r
        if ours == order:
            exact += 1
        else:
            differ.append(obj.stem)
        if args.all:
            continue
        print(f"== {obj.stem}: {'predicted exactly' if ours == order else 'prediction differs'}")
        rank = {}
        if implied is not None:
            addr = {n: implied.get(n) or implied.get(f"{obj.stem.lower()}:{n}") or implied.get(f"{obj.stem}:{n}") for n in order}
            rank = {n: i for i, n in enumerate(sorted((n for n in order if addr[n]), key=lambda n: addr[n]))}
            g2_ranks = [rank[n] for n in second if n in rank]
            late = [n for n in order if n not in second and n in rank and g2_ranks and rank[n] > min(g2_ranks)]
            if late:
                print(f"   retail places group-1 symbols among the initialized group: {[n[:40] for n in late]}")
        for i, n in enumerate(order):
            r_ = f" retail#{rank[n]:2d}" if n in rank else (" retail# -" if implied is not None else "")
            grp = "2" if n in second else "1"
            print(f"   ours#{ours.index(n):2d}{r_}  g{grp}  {n[:48]:48s} {pts[n].where}")
    print(f"objects predicted exactly: {exact}; differing: {len(differ)}" + (f" {differ}" if differ else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
