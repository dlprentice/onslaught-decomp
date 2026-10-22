# The check behind the score

Status: generated with each export
Last updated: 2026-10-22
Summary: the full check this tree's score comes from: how it was run, its log, and its table of matched symbols.

Before each export is published, the maintainers run `python3 tools/decomp.py score` from the exported tree itself,
with the inputs the README lists (each checked against its pin) and the compiler at the README's fixed paths
("The compiler's paths"). The run's output is kept here unchanged:

- [check.log](check.log): what the command printed, standard output and errors together: one line per annotated
  function symbol (`match` or the kind of difference, its address, name and source; symbols the linker folded share an
  address), the score as a JSON line, one line per virtual table, and the compiler's warnings. The command's exit
  status is appended as the last line.
- [matched.tsv](matched.tsv): the run's `build/matched.tsv`, one row per matched symbol (address, retail size, the
  function table's name, the symbol, its demangled form and the source that defines it). Several symbols can share one
  address where the linker folded identical functions, so it has more rows than the score counts functions.

[docs/SCORE.md](../SCORE.md) is the page the same run wrote.
