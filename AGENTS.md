# onslaught-decomp: guide for automated agents

Status: active
Last updated: 2026-11-06
Summary: the rules for agents working in this repository.

This repository is generated from the maintainers' working source. Contributors may edit and commit proposals on
branches in public forks and open a pull request against `main` (`CONTRIBUTING.md`). Maintainers import accepted
changes, validate them and regenerate upstream `main`. Access to maintainer-only repositories or an analysis database is
not required for the documented public function-check route.

- Licence: `REUSE.toml` maps each path (code GPL-3.0-only, `COPYING`; notes CC BY-SA 4.0). Its per-file entries and
  `THIRD-PARTY.md` state the terms of `src/d3dapp.cpp`, `src/d3dapp.h`, `src/oggvorbis.h`, `src/OggFileRead.cpp` and
  `notes/divergences.md`, which this summary does not give.
- Never add the game's files or anything derived from them (executables, data, saves, captures, byte dumps), any part
  of the Visual C++ 6 toolchain or the DirectX SDK (the one exception is the sample-framework pair `src/d3dapp.cpp` and
  `src/d3dapp.h`, recorded in `THIRD-PARTY.md` and `REUSE.toml`; add no other SDK file), or decompiler output.
- Files in `src/` seeded from the game's source release keep their line counts: `__LINE__` values are compiled into
  the retail code.
- A function's match is decided by `python3 tools/decomp.py check`, not by reading the source. Report what the
  check printed, before and after a change.
- Inputs come from environment variables (`README.md`, "Reproducing the match"); never write machine paths into a
  tracked file.
- Notes are prose, tables and addresses: no decompiler listings, no retail byte dumps beyond a short signature.
