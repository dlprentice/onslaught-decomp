# The check behind the score

Status: generated comparison-evidence documentation
Last updated: 2026-11-21
Summary: the check this tree's score comes from: how it was run, a summary of its log (the full log is not published; its SHA-256 is given here), and its table of matched symbols.

Code-changing exports carry a `python3 tools/decomp.py score` run from the exported tree itself, with the README's
pinned inputs and fixed compiler paths; the maintainers run it when they import a change. A pull request owes the
`check` run on its changed files (CONTRIBUTING.md), not a score. A documentation-only export may retain a previous
result only after all compared source, configuration, tools and input pins are checked unchanged. Its publication does
not imply a new score run.

When retaining evidence for a documentation-only export, record its originating public commit and verify that the
score, matched table and summary remain unchanged. The records below describe the measured run, not an implied new
run for every prose edit:

- [check-summary.txt](check-summary.txt): the log reduced to what can be published: the score line, how many function
  symbols matched (the log has one line per annotated function symbol: `match` or the kind of difference, its address,
  name and source; symbols the linker folded share an address), the virtual-table results (one line per table in the log),
  any build concessions named by function and offset (currently 0), the number of compiler warnings, and the command's exit status.
  The export derives it from the full log. Only the score line is copied whole; everything else is a count or a status, apart from the few names it takes from
  single lines: the file, function and offset of any build concession (without its bytes) and, for a virtual table that does not match, its class and result.
- The full log is not published: the compiler's warnings in it name build paths, and any build-concession line would
  carry the bytes it changes. The maintainers keep it with their release logs, and its SHA-256 is
  `c009f05cd430944458440ce7b217a9ab39662ad20b54cd3c78bd99e98ab871d8`, so that the log can be told from any other.
- [matched.tsv](matched.tsv): the run's `build/matched.tsv`, one row per matched symbol (address, retail size, the
  function table's name, the symbol, its demangled form and the source that defines it). Several symbols can share one
  address where the linker folded identical functions, so it has more rows than the score counts functions.

[docs/SCORE.md](../SCORE.md) is the page the same run wrote.
