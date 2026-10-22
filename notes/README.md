# Notes

Status: active index
Last updated: 2026-10-22
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

Per-function notes (what each retail function does, its callers and data) are not part of this first release. They
will follow after a curated review: each is rewritten from the maintainers' working notes and reviewed on its own
before it is published.
