# Contributing

Status: active
Last updated: 2026-11-02
Summary: how changes reach this repository, the rules for `src/`, and the licence of contributions.

Thank you for your interest. Please read this before opening an issue or a pull request.

## How changes are made

Fork this public repository, clone your fork, create a branch and commit your focused proposal there. Open an issue
or a pull request against this repository's `main`. No collaborator invitation, maintainer-only repository access
or analysis database is needed. The upstream branch is generated: maintainers import accepted changes into
the working source, validate them and regenerate this tree with credit.

Read `AGENTS.md`, [Reproducing the match](README.md#reproducing-the-match), licence notices and the relevant tool guide.
Record your upstream commit and existing edits, and preserve unrelated work. Public function checks require your own
appropriately licensed game, compiler and SDK inputs; full executable reconstruction has additional unavailable inputs.
For documentation changes, check links and `git diff --check`; do not run a score just for prose. Do not add hosted CI.

## Rules for `src/`

- **Line counts never change** in a file seeded from the game's source release: `__LINE__` values are compiled into
  the retail code, so moving a line moves bytes. Put new annotations on the definition line (`// FUNCTION: 0x...` at
  its end) where a line of its own would shift the file.
- **Every function carries its retail address**: a `// FUNCTION: 0xADDRESS` annotation on the line before the
  definition, or trailing on the definition line.
- **A match is judged by `python3 tools/decomp.py check`**, never by eye: run it on the files you changed before and
  after, and say in the pull request which functions changed status. Include the public base commit, changed files,
  sanitized before/after summaries and unavailable checks. Maintainers run the remaining acceptance gate before
  integration. Raw compiler logs and disassembly can contain personal paths or original material; do not attach them.
- **Concessions are labelled.** Where the source takes a form the original authors would not have written in order to
  reproduce the compiler's output (a stand-in, an ordering forced by the compiler's allocator), mark it with a
  `STAND-IN`, `RECONSTRUCTED` or `CONCESSION` comment that says why and what proved it.
- Claims about behaviour cite their evidence: a byte comparison, an emulator run (`tools/equiv.py`), a capture, or a
  file and line of the game's source release.

## Licence of contributions

Inbound = outbound: by contributing you agree that your contribution is licensed under the licence of the path it
changes (`REUSE.toml`: the GNU General Public License version 3 only for code, CC BY-SA 4.0 for the notes), and that
you have the right to license it so.

## Never include game or toolchain files

Never attach or commit any of the game's files or anything derived from them (executables, data, text dumps, saves,
captures, byte listings beyond a short signature), Visual C++ 6 toolchain files, additional DirectX SDK binaries,
headers, libraries or sample code, or decompiler output. The existing `d3dapp.cpp`/`.h` sample-framework exception has
its own notice in [THIRD-PARTY.md](THIRD-PARTY.md) and `REUSE.toml`; it does not permit adding other SDK files.
Supply required external inputs from your own appropriately licensed copies.
