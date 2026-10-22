#!/usr/bin/env python3
"""witness_scan.py CHECKOUT WITNESS [--k 0-40|0,2,4] [--state-only] [--json OUT]

Header-count witnesses: functions whose bytes depend on how many declarations (symbols) precede them in their translation
unit. For each, report the current state and the window of k extra dead declarations (`void PchProbeDeclN();` x k,
inserted at a fixed point before the witness) at which it still matches. Measurement only: the source file is restored.

WITNESS is one of:
  dds   game.cpp            00470650 CGame::DrawDebugStuff        (anchor: after `extern SINT performing_stress_test;`)
  bdl   d3dapp.cpp          00529350 CD3DApplication::BuildDeviceList (anchor: after the APPMSGTYPE enum line)
  cpd   ParticleDescriptor.cpp  CPDTimeline rows (every row naming CPDTimeline, plus its vtable line) (anchor: after the last #include)
  fgr   FEPGoodies.cpp      0045e0d0 CFEPGoodies::Render           (anchor: after the last #include)
  dmg   damage.cpp          00440c70 CDamageTexture::Load          (anchor: after the last #include)

Findings: DrawDebugStuff and BuildDeviceList are exactly periodic in k with period 64 (one declaration = one
32-id block, 64 x 32 = 2048 ids, the rotl16(id, 5) field-symbol key period); DrawDebugStuff has no margin (k = +1 and -1 fail).

CDamageTexture::Load (dmg) passes for every k in 0..63 at its anchor: dead declarations in damage.cpp
do not move it, but a change inside the precompiled header does (CMemoryManager's destructor moved out of
MemoryManager.h's class cost it 219 bytes while the other four still passed), so it is a state check (--state-only).

Run one instance per checkout (a checkout owns one Wine prefix; a check compiles one file). State per k is the witness rows'
status words from `decomp.py check src/FILE.cpp`: PASS when every witness row says `match`.
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

W = {
    "dds": dict(file="game.cpp", rows=["00470650"], anchor=r"^extern SINT\tperforming_stress_test;"),
    "bdl": dict(file="d3dapp.cpp", rows=["00529350"], anchor=r"^enum APPMSGTYPE \{ MSG_NONE, MSGERR_APPMUSTEXIT, MSGWARN_SWITCHEDTOREF \};"),
    "cpd": dict(file="ParticleDescriptor.cpp", rows=["CPDTimeline"], anchor=None),
    "fgr": dict(file="FEPGoodies.cpp", rows=["0045e0d0"], anchor=None),
    "dmg": dict(file="damage.cpp", rows=["00440c70"], anchor=None),
}


def anchor_line(lines: list[str], spec: dict, where: str = "spec") -> int:
    """Index of the line after which the dead declarations go."""
    if where == "first":
        return [i for i, l in enumerate(lines) if re.match(r"\s*#\s*include", l)][0]
    if where == "last":
        return [i for i, l in enumerate(lines) if re.match(r"\s*#\s*include", l)][-1]
    if spec["anchor"]:
        hits = [i for i, l in enumerate(lines) if re.match(spec["anchor"], l)]
        if len(hits) != 1:
            raise SystemExit(f"anchor for {spec['file']} matches {len(hits)} lines")
        return hits[0]
    inc = [i for i, l in enumerate(lines) if re.match(r"\s*#\s*include", l)]
    return inc[-1]


def parse_range(s: str) -> list[int]:
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def judge(stdout: str, stderr: str, spec: dict) -> dict:
    """State of the witness rows in one `decomp.py check` output."""
    status = {}
    failed = "compile failed" in stdout or "compile failed" in stderr
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        if parts[0] == "vtable" and "CPDTimeline" in line:
            status["vtable:" + " ".join(parts[1:-1])] = parts[-1]
        elif re.fullmatch(r"[0-9a-f]{8}", parts[1]):
            if any(parts[1] == k or (k in line and not re.fullmatch(r"[0-9a-f]{8}", k)) for k in spec["rows"]):
                status[parts[1]] = parts[0]
    ok = (not failed) and bool(status) and all(v == "match" for k, v in status.items() if not k.startswith("vtable"))
    ok = ok and all(v == "match" for k, v in status.items() if k.startswith("vtable"))
    return {"compile_failed": failed, "rows": status, "pass": ok}


def check(wt: Path, spec: dict) -> dict:
    r = subprocess.run([sys.executable, "-B", "tools/decomp.py", "check", f"src/{spec['file']}"], cwd=wt,
                       capture_output=True, text=True, timeout=3000)
    return judge(r.stdout, r.stderr, spec)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout", type=Path)
    ap.add_argument("witness", choices=W)
    ap.add_argument("--k", default="0-40")
    ap.add_argument("--state-only", action="store_true")
    ap.add_argument("--where", choices=("spec", "first", "last"), default="spec", help="insertion point: the witness anchor, after the first #include (common.h), or after the last")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    wt, spec = a.checkout.resolve(), W[a.witness]
    path = wt / "src" / spec["file"]
    orig = path.read_text()
    lines = orig.split("\n")
    at = anchor_line(lines, spec, a.where)
    ks = [0] if a.state_only else parse_range(a.k)
    results = {}
    try:
        for k in ks:
            decl = "".join(f" void PchProbeDecl{i}();" for i in range(k))
            new = list(lines)
            if k:
                new[at] = new[at] + decl
            path.write_text("\n".join(new))
            t0 = time.time()
            res = check(wt, spec)
            results[k] = res
            print(f"{a.witness} k={k:<3} {'PASS' if res['pass'] else 'FAIL'} {res['rows']} {'(compile failed)' if res['compile_failed'] else ''} {time.time()-t0:.0f}s", flush=True)
    finally:
        path.write_text(orig)
    passing = [k for k, v in results.items() if v["pass"]]
    print(f"{a.witness}: passing k = {passing}")
    if a.json:
        a.json.write_text(json.dumps({"witness": a.witness, "results": results, "passing": passing}, indent=1))


if __name__ == "__main__":
    main()
