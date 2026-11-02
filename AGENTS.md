# onslaught-decomp: guide for automated agents

Status: active
Last updated: 2026-11-02
Summary: the rules for agents working in this repository.

This repository is generated from the maintainers' working source. Contributors may edit and commit proposals on
branches in public forks and open a pull request against `main` (`CONTRIBUTING.md`). Maintainers import accepted
changes, validate them and regenerate upstream `main`. Access to maintainer-only repositories or an analysis database is
not required for the documented public function-check route.

- Licence: `REUSE.toml` maps each path (code GPL-3.0-only, `COPYING`; notes CC BY-SA 4.0).
- Never add the game's files or anything derived from them (executables, data, saves, captures, byte dumps), any part
  of the Visual C++ 6 toolchain or the DirectX SDK, or decompiler output.
- `src/` files keep their line counts: `__LINE__` values are compiled into the retail code.
- A function's match is decided by `python3 tools/decomp.py check`, not by reading the source. Report what the
  check printed, before and after a change.
- Inputs come from environment variables (`README.md`, "Reproducing the match"); never write machine paths into a
  tracked file.
- Notes are prose, tables and addresses: no decompiler listings, no retail byte dumps beyond a short signature.
