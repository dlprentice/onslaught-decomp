# The check behind the score

Status: retained comparison evidence with a documentation-only export
Last updated: 2026-11-02
Summary: the check this tree's score comes from: how it was run, a summary of its log (the full log is not published; its SHA-256 is given here), and its table of matched symbols.

Code-changing exports require `python3 tools/decomp.py score` from the exported tree itself, with the README's pinned
inputs and fixed compiler paths. A documentation-only export may retain a previous result only after all compared
source, configuration, tools and input pins are checked unchanged. Its publication does not imply a new score run.

This documentation-only update retains the comparison evidence published at public commit
`9169f28862ebda0b768cbcc7ec354734af013f5e`. The score, matched table and check summary are unchanged; no new score was
run for these prose changes. The retained records are:

- [check-summary.txt](check-summary.txt): the log reduced to what can be published: the score line, how many function
  symbols matched (the log has one line per annotated function symbol: `match` or the kind of difference, its address,
  name and source; symbols the linker folded share an address), the virtual-table results (one line per table in the log),
  the build concession named by function and offset, the number of compiler warnings, and the command's exit status.
  The export derives it from the full log. Only the score line is copied whole; everything else is a count or a status, apart from the few names it takes from
  single lines: the file, function and offset of the build concession (without its bytes) and, for a virtual table that does not match, its class and result.
- The full log is not published: the compiler's warnings in it name build paths, and the line of the build concession
  carries the bytes it changes. The maintainers keep it with their release logs, and its SHA-256 is
  `365b96af9bfef2efb740751df00e78e739b7513fbfac2d7f414e1917800afcb2`, so that the log can be told from any other.
- [matched.tsv](matched.tsv): the run's `build/matched.tsv`, one row per matched symbol (address, retail size, the
  function table's name, the symbol, its demangled form and the source that defines it). Several symbols can share one
  address where the linker folded identical functions, so it has more rows than the score counts functions.

[docs/SCORE.md](../SCORE.md) is the page the same run wrote.
