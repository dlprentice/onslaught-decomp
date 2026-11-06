# Contributing

Status: active
Last updated: 2026-11-06
Summary: where each kind of work goes, what a first contribution needs and runs, how a pull request on this generated repository is taken in, how to report a problem, the rules for `src/`, and the licence of contributions.

Thank you for your interest. Please read this before opening an issue or a pull request.

## Where to contribute

The project is several public repositories, and each kind of work has one home. The
[contributing guide in Onslaught-Career-Editor](https://github.com/dlprentice/Onslaught-Career-Editor/blob/main/CONTRIBUTING.md)
is the canonical map; this is the short version.

| Your work is about | It goes to |
| --- | --- |
| The byte-matching decompilation: functions, tools, matching notes | This repository, onslaught-decomp. It is generated: open issues and pull requests here as usual (see [How a pull request is taken in](#how-a-pull-request-is-taken-in)). Matching work needs your own copy of the game plus the compiler and SDK inputs [Reproducing the match](README.md#reproducing-the-match) names. |
| Playing Onslaught CE: its bugs, Linux and Windows issues, the launcher and updates (Internet multiplayer is planned, not in this version yet) | [onslaught-ce](https://github.com/dlprentice/onslaught-ce). Also generated, with the same route. The port's platform layer (`port/`) lives there. |
| The Godot rebuild | [onslaught-godot](https://github.com/dlprentice/onslaught-godot), edited directly. |
| How the game works: file formats, saves, mechanics, levels, engine | [onslaught-preservation](https://github.com/dlprentice/onslaught-preservation), edited directly. It uses this repository's function names. |
| The Companion (saves, backups, settings, lore, music), and the program's goals and plan (`GOAL.md`, `PROGRAM.md`) | [Onslaught-Career-Editor](https://github.com/dlprentice/Onslaught-Career-Editor). Its `rebuild/` and `reverse-engineering/` folders are frozen copies: rebuild work goes to onslaught-godot, documentation to onslaught-preservation. The Companion's features are moving into Onslaught CE, so new feature work belongs in CE. |

The Onslaught and AYAResourceExtractor forks on the same account are kept as pinned references, not contribution
targets. Security reports follow [SECURITY.md](SECURITY.md). [REUSE.toml](REUSE.toml) says which licence
covers which files, and a contribution comes in under the same terms as the files it changes.

Everyone contributes by fork and pull request. No invitation, collaborator access or maintainer-only repository is
needed, and no response time is promised.

Questions and ideas: https://github.com/dlprentice/onslaught-ce/discussions
(problems and matching findings go to this repository's Issues, using the forms).

## How a pull request is taken in

This repository's `main` is generated: it is written by an export from the maintainers' working source, and nothing is
committed to it by hand. So a pull request here is not merged directly. The maintainer reviews it, imports the accepted
work into the working source with credit to you (a `Co-authored-by` line naming you in the commit that publishes it) and a
reference to your pull request, runs the full check there, and
the next export publishes it. The pull request is closed after the export that carries the change has landed. An
"export" is that regeneration of this tree. Do not hand-edit the generated files: `docs/SCORE.md`, `docs/check/`, every page in `notes/` except
`notes/README.md`, `config/functions.tsv`, `config/function-corrections.tsv`, `config/objects.tsv`,
`config/link-objects.txt`, `COPYING` and the licence texts in `LICENSES/`. The next export replaces them, and a pull
request that changes one is not imported as it stands. To suggest wording or a correction for one of them, put it in the
pull request description or in an issue, and the maintainer makes the change in the working source.

## Your first hour

What you need depends on what you change. There is no hosted CI: the checks below are yours to run, and your pull
request should say which you ran and which you could not.

| You are changing | You need | Run before the pull request |
| --- | --- | --- |
| Text or links, outside the generated files listed above | Git; nothing else | `git diff --check`, then open every link you changed and check that the path or heading it points to exists. For a generated file, describe the change in the pull request instead |
| A tool under `tools/` | Python 3 (the unit tests ran on 3.14; older versions are untested), `llvm-undname` from the LLVM package for the commands that demangle names, and Unicorn (`pip install -r requirements.txt`) only for `equiv.py` | `python3 -m unittest discover -p '*_tests.py' -s tools` from the repository root. It needs no game, compiler or SDK. 9 tests skip here by design (see [tools/README.md](tools/README.md)) |
| `src/` (a function, a match, a fix) | Your own `BEA.exe` (SHA-256 in the README), Visual C++ 6.0 SP5, the DirectX 9.0 SDK, Wine and `llvm-undname`, plus `objdump` for `diff` and `dis` ([Reproducing the match](README.md#reproducing-the-match)) | `python3 tools/decomp.py check` on the files you changed, before and after |

You can do the first two rows with no copy of the game at all. Full reconstruction of the linked executable needs
further inputs that are unavailable, so the function check is the route that works from this tree.

Steps:

1. Fork this repository, clone your fork and create a branch from `main` (`git switch -c my-change`). Note the commit
   you started from (`git rev-parse HEAD`) and any edits you already had (`git status --short`).
2. Read the [README](README.md), the guide for the tool you use ([tools/README.md](tools/README.md)) and the licence
   notices. [AGENTS.md](AGENTS.md) holds the rules automated agents follow; as a person you need this file and the
   README.
3. Run the checks for your kind of change and write down the result before you edit anything.
4. Make one focused change. Commit only the paths you changed and push the branch to your fork. Commit messages
   describe the change itself; keep session links, machine paths and anything copied from the game out of them. A
   `Co-Authored-By` trailer is welcome when someone else wrote part of the change.
5. Run the checks again and open the pull request. The form asks for the base commit, the changed files, the exact
   commands and before/after summaries, and what you could not run. Maintainers run the remaining acceptance gate
   before the work is imported. Do not add hosted CI.

## Reporting a problem

Open an issue; the forms ask for what is needed. For a bug or a matching problem, give:

- the commit you ran (`git rev-parse HEAD`) and the exact command;
- the trimmed output: the lines for the functions or files concerned, not the whole log;
- your system: operating system, Python version, Wine version, and whether you used Visual C++ 6.0 SP5 and the
  DirectX 9.0 SDK from the versions the README names (leave your folder paths out);
- what you expected and what happened.

Do not attach raw compiler logs or disassembly: they can contain personal paths or original material. Do not attach
any of the game's files. For a security problem, use the form [SECURITY.md](SECURITY.md) names, not an issue.

Findings that came from your own work on the game, such as a behaviour you measured or a function's purpose, belong in
an issue or a pull request as text: say what you measured, on which function, and how a maintainer can check it. Do not
attach recordings, saves or files taken from the game.

## Rules for `src/`

- **Line counts never change** in a file seeded from the game's source release: `__LINE__` values are compiled into
  the retail code, so moving a line moves bytes. Put new annotations on the definition line (`// FUNCTION: 0x...` at its end) where a line of its own would shift the file.
- **Every function carries its retail address**: a `// FUNCTION: 0xADDRESS` annotation on the line before the
  definition, or trailing on the definition line.
- **A match is judged by `python3 tools/decomp.py check`**, never by eye: run it on the files you changed before and
  after, and say in the pull request which functions changed status. Include the public base commit, changed files,
  sanitized before/after summaries and unavailable checks. `python3 tools/decomp.py score` rebuilds everything and is
  for the maintainers' acceptance gate; do not run it for prose. Raw compiler logs and disassembly can contain
  personal paths or original material; do not attach them.
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
