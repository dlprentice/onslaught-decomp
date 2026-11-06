<!-- Thank you for the pull request. This repository's main branch is generated from the maintainers' working source, so
     an accepted change is imported there and reaches this repository with the next export, with credit; the pull
     request is closed once the export that carries it has landed. There is no hosted CI: the checks below are yours to
     report. -->

**Problem**

What is wrong or missing, and how you saw it.

**Change**

What this changes and which files.

**Base commit**

The commit of this repository your branch started from (`git rev-parse HEAD` before your first change):

**Checks run**

Exact commands and results. For a tool or script: `python3 -m unittest discover -p '*_tests.py' -s tools`. For `src/`:
`python3 tools/decomp.py check` on the changed files, before and after, with which functions changed status.

**Checks not run**

What you could not run and why (no compiler, no SDK, no copy of the game).

- [ ] I attached no game files, raw compiler logs, disassembly, captures or anything derived from the game.
- [ ] No file seeded from the game's source release changed its line count (CONTRIBUTING.md, "Rules for `src/`").
- [ ] I did not hand-edit generated files (the list is in CONTRIBUTING.md, "How a pull request is taken in": `docs/SCORE.md`, `docs/check/`, `notes/` pages other than `notes/README.md`, four files under `config/`, `COPYING`, `LICENSES/`). Suggested wording for them is in this description.
- [ ] My contribution may be licensed under the licence of the paths it changes, and I have the right to license it so.
