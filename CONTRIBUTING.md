# Contributing

Status: active
Last updated: 2026-10-22
Summary: how changes reach this repository, the rules for `src/`, and the licence of contributions.

Thank you for your interest. Please read this before opening an issue or a pull request.

## How changes are made

This repository is generated from the maintainers' working source by an export: it is not edited directly, and its
history is a series of exports. Open an issue describing the problem or change, or a pull request with your change;
the maintainers bring accepted work into the working source, check it there with the full byte comparison, and it
appears here with the next export, credited to you.

## Rules for `src/`

- **Line counts never change** in a file seeded from the game's source release: `__LINE__` values are compiled into
  the retail code, so moving a line moves bytes. Put new annotations on the definition line (`// FUNCTION: 0x...` at
  its end) where a line of its own would shift the file.
- **Every function carries its retail address**: a `// FUNCTION: 0xADDRESS` annotation on the line before the
  definition, or trailing on the definition line.
- **A match is judged by `python3 tools/decomp.py check`**, never by eye: run it on the files you changed before and
  after, and say in the pull request which functions changed status.
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
captures, byte listings beyond a short signature), any part of the Visual C++ 6 toolchain or the DirectX SDK (their
binaries, headers, libraries or sample code), or the output of a decompiler. You supply those from your own copies;
this repository contains none of them and will not accept them.
