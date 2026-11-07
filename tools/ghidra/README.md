# Names for your own Ghidra database

Status: active reference (version 1)
Last updated: 2026-11-06
Summary: a Ghidra script that gives the functions of this tree's function table, in your own copy of the retail
executable, the name, extent and source file this tree records, how to run it in the GUI and headless, and what it
does not do.

If you own *Battle Engine Aquila*, you can import its `BEA.exe` into Ghidra, run one script from this clone, and have
the functions in this tree's function table named as the decompilation names them, sized as the table sizes them, and
commented with the file of `src/` that defines it. A headless run takes seconds. The Ghidra GUI steps below have not
been run.

This repository publishes no Ghidra database, no game bytes and no decompiler output. The script reads only this
tree's own tables: `config/functions.tsv` and `config/function-corrections.tsv` (applied the way `tools/decomp.py`
reads them) for the names and extents, and the `// FUNCTION: 0xADDRESS` annotations in `src/` for the file names.

## What you need

- **Your own copy of the game's executable**, the retail `BEA.exe` whose SHA-256 the top-level [README](../../README.md)
  states. The script checks the hash of the program you run it on and refuses any other file with a message: a patched
  or different build has different code at these addresses. Import the file itself (File, Import File) so Ghidra
  records its hash.
- **Ghidra**, with its PyGhidra script provider (the way current releases run Python scripts; tested on Ghidra 12.1.3
  with PyGhidra 3.1.0). PyGhidra is the tested route. The script's syntax stays within Python 2.7, but Jython is
  not a route to rely on: Ghidra 12.1.3 gives a `.py` script that has no `# @runtime` line to PyGhidra only, so Jython
  runs it only from a copy that carries a `# @runtime Jython` line, and under Jython any change that Ghidra refuses (a
  creation, a rename or an extent) stops the run with Ghidra's Java exception instead of being counted.
- **This clone**, for `config/` and `src/`.

## Run it in the Ghidra GUI

1. Import `BEA.exe` as a new program (format: Portable Executable, language: x86 32-bit, the importer's defaults, which
   put the image at its own base address). The script refuses a program imported at another base or in another
   language, such as a 64-bit one.
2. Open it in the CodeBrowser and, when it offers to analyse, answer No for now: **run the script first, on the fresh
   import.** Every function in the table then ends up with its name and extent, and running it a second time changes
   nothing. You can run Ghidra's analysis afterwards; it keeps the names and comments but may resize a few functions
   to its own idea of their extent. If you run the script on a program that is already analysed, Ghidra may have
   defined data or code where a table function belongs; the script then leaves that function out and counts it as
   `create_refused`, and a second run can still find something to do. For the exact result, start again from a fresh
   import.
3. Window, Script Manager, "Manage Script Directories", and add this folder (`tools/ghidra/` of your clone). The script
   is listed in the "Onslaught" category.
4. Run `ApplyOnslaughtNames.py`. It finds the clone it sits in and prints which `config/` folder it used; if you
   copied the script elsewhere, it asks for the clone's folder (the one holding `config/` and `src/`).
5. Save the program. The Console shows the counts.

## Run it headless

Headless Python scripts need Ghidra started through PyGhidra. Plain `analyzeHeadless` imports the program, then
prints `Ghidra was not started with PyGhidra. Python is not available`, applies nothing and still exits 0. Use
`support/pyghidraRun --headless`, which takes the same arguments, from an environment where `python3` has PyGhidra:

    python3 -m venv /path/to/venv
    /path/to/venv/bin/pip install --no-index --find-links GHIDRA_INSTALL_DIR/Ghidra/Features/PyGhidra/pypkg/dist pyghidra
    PATH=/path/to/venv/bin:$PATH GHIDRA_INSTALL_DIR/support/pyghidraRun --headless PROJECT_FOLDER PROJECT_NAME \
        -import /path/to/BEA.exe -noanalysis \
        -scriptPath /path/to/clone/tools/ghidra -postScript ApplyOnslaughtNames.py /path/to/clone

(`-noanalysis` is the recommended order, see step 2 above; the headless import saves the program when the script
ends.) The script's path argument is the clone's root or its `config/` folder; it can also be given in the
environment as `BEA_DECOMP_DIR`. A path you give that does not resolve stops the run: the script does not fall back
to another clone. The word `check`, before or after the path or alone, makes a run report what it would change and
write nothing:

    ... -postScript ApplyOnslaughtNames.py /path/to/clone check

To run it on a program already in a project, replace `-import /path/to/BEA.exe` with `-process BEA.exe`.

A run on a different executable prints the refusal and changes nothing, but the process still exits with status 0:
read the printed summary, not the exit status.

## What it does

For each function in the table, in address order:

- **no function there**: creates one named as the table names it, with the table's byte count as its extent
  (disassembling the entry first if nothing has been);
- **a function there**: renames it, and replaces its extent with the table's when they differ (one contiguous block of
  the table's byte count, starting at the entry);
- **plate comment**: adds one line, `Onslaught decomp source: File.cpp`, naming the file in `src/` that defines the
  function (a few files, implementation files first, when several annotate the same address). It keeps a comment
  you wrote and replaces only its own line.

Running it twice is safe: it makes no change the second time, and the summary shows only "unchanged" counts.

**Names are not unique.** The table repeats some names (most repeated rows are the initializers of a few constants that
many files include from shared headers; the rest are placeholder names and overloaded constructors and operators),
and Ghidra 12.1.3 accepts repeated function names, so after a run
a few dozen names are each used by more than one function, several hundred functions in all. Identify a function by
its address, never by its name. If a version of Ghidra ever refuses a repeated name, the script appends the function's address to it
(`Name__ADDRESS`, the address in hex) and counts that as `renamed_with_address_suffix`; that path is exercised by the
tests, not by the Ghidra versions tried.

## The summary

Counts only, printed to the Console or the headless log:

| Count | Meaning |
| --- | --- |
| `table_rows`, `corrections_applied` | rows read, and how many corrections were applied to them |
| `overlapping_extents` | neighbouring table rows whose extents overlap (Ghidra will refuse one of each) |
| `outside_image`, `bad_rows` | rows skipped: not inside the imported image, or without a name or size |
| `created`, `create_refused` | functions created, and creations Ghidra refused |
| `renamed`, `names_unchanged`, `rename_refused` | functions renamed, already right, or refused |
| `extents_set`, `extents_unchanged`, `extents_refused` | extents replaced, already right, or refused (another function holds part of the range) |
| `comments_added`, `comments_updated`, `comments_unchanged`, `no_source_file` | plate comments, and functions that no `// FUNCTION:` annotation in `src/` covers (mostly compiler-generated unwind funclets and import thunks; they keep their name and extent, with no comment) |
| `disassembled`, `errors` | entries disassembled before creating a function; rows whose changes raised an unexpected error (the rest of that row is skipped) |

Under PyGhidra, a refused change or an unexpected error in one row does not stop the run, and the changes already made stay. A table
that is damaged (a malformed row, or no rows at all) stops it before any change.

## What it does not include

- **Types and global variables.** Version 1 applies function names, extents and source-file comments only. The script
  keeps its stages in one list (`STAGES`) so that a stage for types or globals, reading its own table from `config/`,
  can be added beside the functions stage without touching the rest.
- **Functions the table does not list.** The table covers the game's own code; it does not list the library code
  linked after it. If you run Ghidra's analysis, the functions it finds there, and any others it adds, keep Ghidra's
  own names.
- **Anything of the game.** The script and tables contain no executable bytes, data, decompiler output or Ghidra
  database. It needs your own copy of the executable at run time.
- **Other tools.** IDA, Binary Ninja or x64dbg maps could be generated from the same tables; none is provided yet.
- **Namespaces and signatures.** Names are flat symbols (`Class__Method`, as in the table); no class namespaces,
  prototypes or calling conventions are set.

## Tests

    python3 -m unittest tools.ghidra_tests

The tests need no Ghidra and no game: they drive the script's logic with synthetic tables, and a stand-in for the few
Ghidra classes its adapter uses. They check the table parsing and corrections, the source scan, the plate comments,
the refusal of a different executable or language, argument handling (`check` in any position, a path that does not
resolve, a trailing slash), damaged tables, that a second run on a fresh import changes nothing, and that a change to
the name or extent mapping fails. They do not test the Ghidra GUI or the folder picker, and the GUI steps above have not
been run; the script itself was run against Ghidra 12.1.3 headless through PyGhidra only.
