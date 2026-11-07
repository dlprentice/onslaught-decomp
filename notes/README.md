# Notes

Status: active index
Last updated: 2026-11-06
Summary: the matching knowledge behind the decompilation, by area.

The source's own comments hold the per-function knowledge that shaped it (the `STAND-IN`, `RECONSTRUCTED` and
`CONCESSION` marks in `src/`); these notes hold what applies more widely. Addresses are the retail executable's
(`BEA.exe`, SHA-256 `74154bfa…`) unless a passage says otherwise: `link-reconstruction.md` also gives addresses of the rebuilt link, in its survivor passages and where it says "ours", not all of them labelled. The notes are exported from the maintainers' working notes and cleaned for
publication: who did what, the working repository's commits and paths, and anything read from inside Microsoft's
compiler or linker are left out, and the compiler's and linker's behaviour is described from what they produce. Each
finding states what was measured and on which function.

- [toolchain.md](toolchain.md): the compiler, flags and inputs the retail build used, and how each was established.
- [compiler-findings.md](compiler-findings.md): what the compiler, linker and retail evidence showed about the
  source's form, finding by finding.
- [matching-techniques.md](matching-techniques.md): the working rules for reaching a byte match, each with the
  function that proved it.
- [divergences.md](divergences.md): where the retail build differs from Stuart Gillam's published source.
- [link-reconstruction.md](link-reconstruction.md): how the link is rebuilt, what is proven, conceded and open.

Per-function notes (what each retail function does, its callers and data) are not published. They
will follow after a curated review: each is rewritten from the maintainers' working notes and reviewed on its own
before it is published.

## Words these notes use

- **Match** (a function "matches"): its whole compiled section equals the retail bytes at its address, relocation fields
  aside, and every relocation lands where the rest of the evidence says. The top-level README states the rule.
- **Specimen**: the retail `BEA.exe` the tools compare against, identified by its SHA-256 (`74154bfa…`).
- **COMDAT**: a function or data item the compiler writes into its own named section of an object file, so the linker
  can fold identical copies or drop unused ones. The check compares each function's section with the retail bytes.
- **Relocation**: a field in an object file that the linker fills in with a final address.
- **PCH**: the precompiled header. Code compiled with a header made under other paths can differ, so the tools fix the
  paths (README, "The compiler's paths").
- **IAT** and **import thunk**: the import address table holds the addresses of functions imported from DLLs; an
  import thunk is the small stub in the executable that jumps through one of its slots.
- **RTTI**, **vtable**: run-time type information the compiler stores for classes with virtual functions, and the
  table of a class's virtual function addresses. `tools/rtti.py` reads the class names from the RTTI.
- **Funclet**: a small compiler-generated cleanup routine run while an exception unwinds. The function table names
  them `Unwind@ADDRESS`.
- **Concession** (and the `STAND-IN`, `RECONSTRUCTED` and `CONCESSION` marks): a place where reproducing the retail bytes
  needed something other than the form the original authors would have written. Each is labelled with what proved it.
  One function matches through a build concession recorded in `config/object-patches.tsv`.
- **PC24, PC53 and PC64**: the x87 precision-control settings for 24-, 53- and 64-bit significands (single, double and extended precision).
- **RN**: round to nearest, the x87 default rounding mode.
- **CW**: the x87 control word, which holds the precision and rounding settings above.
- **Exact control**: a function already matched in its object, which a check compares again after a change to show the match survives.
- **Sibling graph**: another callable function in the same object, whose compiled bytes are compared again after a change.
- **IL tuple**: an entry in the compiler's internal intermediate language. Adding tuples can move where the compiler's scheduling regions end.
- **FPO**: the frame-pointer-omission record the compiler writes in an object's debug data for a function without a frame pointer.
- **thiscall**: the x86 calling convention for member functions, which passes `this` in ECX.
- **Shell**: the `Shell.cpp` object, `src/Shell.cpp` and `src/shell.h` (class `CShell`, a projectile actor). The application shell is `ltshell` (class `PCLTShell`, in `src/ltshell.h`).
- **Credit** and **uncredited**: a function is credited when the score counts it as matched (`docs/SCORE.md`); a candidate or draft that the score does not count is uncredited.
- **Harness**: the compile-and-compare machinery of `tools/decomp.py check`, which reads the objects with `tools/binfmt.py`; `tools/equiv.py` has its own differential harness.
- **Near miss**: an annotated function that the check reports as `bytes`, `relocations` or `size` (compiled, but not matching; `size` means its section is shorter than retail's); each note says what differs and how far it is from a match.
- **Pristine specimen**: the unmodified retail `BEA.exe` that the `BEA_PRISTINE` setting names (README, Settings), the baseline every byte comparison reads.
- **Probe**: a small test source compiled with the pinned toolchain to see what the compiler emits for one construct. Probes are measurements, not part of `src/`; a probe kept as a fixture is named, such as `tools/tests/inline_budget.cpp`.
- **Relaxed squad**: the squad interface of the `CRelaxedSquad` class (`src/SquadRelaxed.cpp`), which the notes compare with the normal one, `CNormalSquad` (`src/SquadNormal.cpp`).
- **Rich header**: the block of build-tool records that a Microsoft linker writes into a PE file; `tools/inventory.py` reads it.
- **Stock build**: a build made with the pinned Visual C++ 6 toolchain (`config/toolchain.sha256`) unchanged.
- **.CRT$XCU**: the object-file section that calls an object's static initializers; the C runtime runs those calls at start-up in link order. `tools/decomp.py` reads these sections for the `initorder:` annotations.
