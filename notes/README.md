# Notes

Status: active index
Last updated: 2026-11-06
Summary: the matching knowledge behind the decompilation, by area.

The source's own comments hold the per-function knowledge that shaped it (the `STAND-IN`, `RECONSTRUCTED` and
`CONCESSION` marks in `src/`); these notes hold what applies more widely. Addresses are the retail executable's
(`BEA.exe`, SHA-256 `74154bfa…`). The notes are exported from the maintainers' working notes and cleaned for
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
