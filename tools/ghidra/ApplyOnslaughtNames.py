# Apply the decompilation's function table (names, extents, source files) to your own copy of BEA.exe.
# SPDX-License-Identifier: GPL-3.0-only
# @category Onslaught
"""Apply the decompilation's function names to Battle Engine Aquila's retail executable in Ghidra.

Import your own BEA.exe (SHA-256 in the top-level README) into a Ghidra project, open it, and run this script. For
every row of this clone's config/functions.tsv (with config/function-corrections.tsv applied, as tools/decomp.py reads
them) it creates or renames the function at that address, sets its extent from the row's byte count where Ghidra
allows, and adds a plate comment naming the source file of src/ that defines it. Nothing is read from anywhere else:
the names and extents are the decompilation's own public tables, the file names come from the
`// FUNCTION: 0xADDRESS` annotations in src/. Running it again changes nothing.

Where it finds the clone: a path given as a script argument (headless: `ApplyOnslaughtNames.py PATH`), else the
environment variable BEA_DECOMP_DIR, else the clone this file sits in (tools/ghidra/ is two folders below its root),
else, in the GUI, a folder you pick. PATH may be the clone's root or its config/ folder. A path you give (as an
argument or in BEA_DECOMP_DIR) that does not hold the tables stops the run: it is never replaced by another clone.
The word `check`, in any position, only reports what a run would change and writes nothing. The run prints the config
folder it used.

It runs under PyGhidra (Python 3), the tested route. The syntax stays within Python 2.7, but README.md explains why
Jython is not a route to rely on. All logic that does not touch Ghidra is in plain functions above `GhidraProgram`,
driven by tools/ghidra_tests.py without Ghidra.

Version 1 covers function names, extents and plate comments for the one executable the decompilation matches. Types and
global variables are not applied: add a stage to STAGES for them.
"""
from __future__ import print_function

import io
import os
import re
import sys

# The one retail executable the decompilation matches (the top-level README states this hash).
EXPECTED_SHA256 = "74154bfae14ddc8ecb87a0766f5bc381c7b7f1ab334ed7a753040eda1e1e7750"
# The image base the tables' addresses are written for (a PE's default).
IMAGE_BASE = 0x400000
COMMENT_PREFIX = "Onslaught decomp source: "
MAX_FILES_IN_COMMENT = 4
SOURCE_SUFFIXES = (".c", ".cpp", ".h")

ADDRESS = re.compile(r"^0x[0-9a-fA-F]{1,8}$")
DIGITS = re.compile(r"^[0-9]+$")
IMAGE_LIMIT = 0xFFFFFFFF      # the 32-bit address space the tables' addresses live in
ANNOTATION = re.compile(r"//\s*FUNCTION:\s*0x([0-9a-fA-F]{8})")

# Counters, in the order they are printed.
COUNTERS = (
    "table_rows", "corrections_applied", "overlapping_extents",
    "outside_image", "bad_rows",
    "created", "create_refused",
    "renamed", "renamed_with_address_suffix", "names_unchanged", "rename_refused",
    "extents_set", "extents_unchanged", "extents_refused",
    "comments_added", "comments_updated", "comments_unchanged", "no_source_file",
    "disassembled", "errors",
)


class ToolError(Exception):
    """The run cannot start or continue: the message says what to change."""


class AdapterError(Exception):
    """Ghidra refused one change; the run counts it and goes on."""


class DuplicateName(AdapterError):
    """Ghidra holds another function of that name already."""


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def read_text(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_table(text, label):
    """The rows of a tab-separated function table (address, bytes, name, ...) as (address, size, name) tuples, in file
    order. A malformed row stops the run with its line number; the row itself is not echoed."""
    lines = text.splitlines()
    if not lines:
        raise ToolError("%s is empty" % label)
    header = lines[0].rstrip("\r").split("\t")
    if header[:3] != ["address", "bytes", "name"]:
        raise ToolError("%s: the header is not address, bytes, name" % label)
    rows = []
    seen = set()
    for number, line in enumerate(lines[1:], 2):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) < 3 or not ADDRESS.match(cells[0]) or not DIGITS.match(cells[1]):
            raise ToolError("%s line %d: not an address, a byte count and a name" % (label, number))
        address = int(cells[0], 16)
        if address in seen:
            raise ToolError("%s line %d: an address listed twice" % (label, number))
        seen.add(address)
        rows.append((address, int(cells[1]), cells[2]))
    return rows


def apply_corrections(rows, corrections):
    """The table with each correction applied the way tools/decomp.py reads it: a corrected extent or a function the
    table never listed replaces or adds its row, and 0 bytes removes a row that is not a function. Returns the rows
    in address order and how many corrections there were."""
    table = {}
    for address, size, name in rows:
        table[address] = (address, size, name)
    for address, size, name in corrections:
        if size:
            table[address] = (address, size, name)
        else:
            table.pop(address, None)
    return [table[a] for a in sorted(table)], len(corrections)


def sanitize_name(name):
    """A name Ghidra accepts: it rejects whitespace, control and non-ASCII characters in a symbol name."""
    return "".join(c if 32 < ord(c) < 127 else "_" for c in name)


def extent_end(address, size):
    """The last address a function of `size` bytes at `address` covers."""
    return address + size - 1


def overlap_count(rows):
    """How many neighbouring rows' extents overlap (rows in address order)."""
    return sum(1 for a, b in zip(rows, rows[1:]) if extent_end(a[0], a[1]) >= b[0])


def config_folder_of(candidate):
    """The config/ folder a clone's root or config folder names (a trailing slash does not matter), else None."""
    if not candidate:
        return None
    candidate = os.path.normpath(str(candidate))
    for path in (os.path.join(candidate, "config"), candidate):
        if os.path.isfile(os.path.join(path, "functions.tsv")) and \
                os.path.isfile(os.path.join(path, "function-corrections.tsv")):
            return path
    return None


def locate_config(candidates):
    """The config/ folder of the first candidate (a clone's root, or its config folder) that holds the tables."""
    for c in candidates:
        found = config_folder_of(c)
        if found:
            return found
    return None


def parse_arguments(arguments):
    """(path or None, check) from the script arguments: the word `check` anywhere asks for a check-only run; the first
    other argument is the clone's path. More than one path is an error."""
    paths = [a for a in arguments if a != "check"]
    if len(paths) > 1:
        raise ToolError("Expected at most one path and the word check, but got %d arguments besides check." % len(paths))
    return (paths[0] if paths else None), ("check" in arguments)


def load_function_table(config_dir):
    """(rows in address order, number of corrections) from config/functions.tsv and function-corrections.tsv."""
    table = parse_table(read_text(os.path.join(config_dir, "functions.tsv")), "functions.tsv")
    if not table:
        raise ToolError("functions.tsv has a header and no rows: the table is damaged or cut short, so nothing is applied")
    corrections = parse_table(read_text(os.path.join(config_dir, "function-corrections.tsv")),
                              "function-corrections.tsv")
    return apply_corrections(table, corrections)


# ---------------------------------------------------------------------------
# Source files
# ---------------------------------------------------------------------------

def scan_annotations(text):
    """The addresses a source file annotates with `// FUNCTION: 0xADDRESS`."""
    return [int(m.group(1), 16) for line in text.splitlines() for m in ANNOTATION.finditer(line)]


def scan_sources(src_dir):
    """address -> sorted list of the files (relative to src/, with `/`) that annotate it."""
    found = {}
    if not src_dir or not os.path.isdir(src_dir):
        return found
    for folder, dirs, files in os.walk(src_dir):
        dirs.sort()
        for filename in sorted(files):
            if not filename.lower().endswith(SOURCE_SUFFIXES):
                continue
            path = os.path.join(folder, filename)
            relative = os.path.relpath(path, src_dir).replace(os.sep, "/")
            for address in scan_annotations(read_text(path)):
                names = found.setdefault(address, [])
                if relative not in names:
                    names.append(relative)
    for names in found.values():
        names.sort(key=lambda n: (n.lower().endswith(".h"), n.lower()))
    return found


def source_label(files):
    """The text after the comment prefix: the source files, implementation files before headers, a few at most."""
    shown = list(files[:MAX_FILES_IN_COMMENT])
    label = ", ".join(shown)
    if len(files) > len(shown):
        label += " (+%d more)" % (len(files) - len(shown))
    return label


def merge_plate(existing, label):
    """(new plate comment, what happened) for a function whose plate comment is `existing` (None or text): our line
    is added after any comment already there, or replaces our earlier line; other lines are kept. The second value
    is "added", "updated" or "unchanged"."""
    ours = COMMENT_PREFIX + label
    if not existing:
        return ours, "added"
    lines = existing.split("\n")
    kept = [l for l in lines if not l.startswith(COMMENT_PREFIX)]
    if len(kept) == len(lines):
        return existing + "\n" + ours, "added"
    first = next(i for i, l in enumerate(lines) if l.startswith(COMMENT_PREFIX))
    merged = []
    for i, l in enumerate(lines):
        if l.startswith(COMMENT_PREFIX):
            if i == first:
                merged.append(ours)
        else:
            merged.append(l)
    new = "\n".join(merged)
    return new, ("unchanged" if new == existing else "updated")


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

def check_program_hash(actual):
    """Refuse any file but the one the decompilation matches."""
    if not actual:
        raise ToolError("REFUSED: the program records no SHA-256, so it cannot be checked against the one the "
                        "decompilation matches. Import BEA.exe itself (File, Import File) and run again.")
    if actual.strip().lower() != EXPECTED_SHA256:
        raise ToolError("REFUSED: this program is not the executable the decompilation matches (its SHA-256 differs "
                        "from the one in the README, which begins %s). Import the unmodified retail BEA.exe; a "
                        "patched or other build has different code at these addresses." % EXPECTED_SHA256[:8])


def bump(summary, key, n=1):
    summary[key] = summary.get(key, 0) + n


def stage_functions(program, rows, sources, summary, write=True):
    """Create or rename each function at its address, set its extent and add its plate comment. `program` is a
    GhidraProgram, or anything with the same methods."""
    for address, size, table_name in rows:
        program.check_cancelled()
        name = sanitize_name(table_name)
        if not name or size <= 0:
            bump(summary, "bad_rows")
            continue
        if extent_end(address, size) > IMAGE_LIMIT or not program.in_image(address) or \
                not program.in_image(extent_end(address, size)):
            bump(summary, "outside_image")
            continue
        try:
            function = program.function_at(address)
            if function is None:
                function = create_function(program, address, size, name, summary, write)
                if function is None:
                    continue
            else:
                rename_function(program, function, address, name, summary, write)
                set_extent(program, function, address, size, summary, write)
            label_function(program, address, sources.get(address), summary, write)
        except ToolError:
            raise
        except Exception:       # a row Ghidra's API rejects in some unforeseen way: count it, keep the rest
            bump(summary, "errors")
            program.check_cancelled()       # a cancel (Ghidra's own exception) must still stop the run


def create_function(program, address, size, name, summary, write):
    try:
        if not write:
            bump(summary, "created")
            return False
        if program.ensure_code(address, size):
            bump(summary, "disassembled")
        try:
            function = program.create_function(address, size, name)
        except DuplicateName:
            function = program.create_function(address, size, address_suffixed(name, address))
            bump(summary, "renamed_with_address_suffix")
        bump(summary, "created")
        return function
    except AdapterError:
        bump(summary, "create_refused")
        return None


def address_suffixed(name, address):
    return "%s__%08x" % (name, address)


def rename_function(program, function, address, name, summary, write):
    current = program.name_of(function)
    if current == name or current == address_suffixed(name, address):
        bump(summary, "names_unchanged")
        return
    if not write:
        bump(summary, "renamed")
        return
    try:
        try:
            program.set_name(function, name)
            bump(summary, "renamed")
        except DuplicateName:
            program.set_name(function, address_suffixed(name, address))
            bump(summary, "renamed_with_address_suffix")
    except AdapterError:
        bump(summary, "rename_refused")


def set_extent(program, function, address, size, summary, write):
    if program.extent_is(function, address, size):
        bump(summary, "extents_unchanged")
        return
    if not write:
        bump(summary, "extents_set")
        return
    try:
        program.set_extent(function, address, size)
        bump(summary, "extents_set")
    except AdapterError:
        bump(summary, "extents_refused")


def label_function(program, address, files, summary, write):
    if not files:
        bump(summary, "no_source_file")
        return
    text, outcome = merge_plate(program.plate_at(address), source_label(files))
    if outcome != "unchanged" and write:
        program.set_plate(address, text)
    bump(summary, "comments_" + outcome)


STAGES = (
    ("functions", stage_functions),
    # Types and global variables are not part of version 1: a stage added here receives the same arguments and
    # reads its own table from config/ (see the README in this folder).
)


def run(program, config_dir, src_dir, write=True):
    """Check the program, then apply every stage. Returns the summary: counter name -> count."""
    check_program_hash(program.sha256())
    rows, corrections = load_function_table(config_dir)
    sources = scan_sources(src_dir)
    summary = {"table_rows": len(rows), "corrections_applied": corrections,
               "overlapping_extents": overlap_count(rows)}
    for _, stage in STAGES:
        stage(program, rows, sources, summary, write)
    return summary


def summary_lines(summary, write):
    lines = ["ApplyOnslaughtNames: %s" % ("applied" if write else "check only, nothing written")]
    for key in COUNTERS:
        if summary.get(key):
            lines.append("  %s: %d" % (key, summary[key]))
    if write and any(summary.get(k) for k in ("create_refused", "rename_refused", "extents_refused", "errors")):
        lines.append("  Some changes were refused. A program that Ghidra has already analysed can hold data or code "
                     "where a function belongs; a fresh import run before analysis takes all of them.")
    return lines


# ---------------------------------------------------------------------------
# Ghidra
# ---------------------------------------------------------------------------

class GhidraProgram(object):
    """The calls the stages make, over Ghidra's API. Addresses are the tables' (image base 0x400000)."""

    def __init__(self, program, monitor):
        from ghidra.program.model.address import AddressSet
        from ghidra.program.model.symbol import SourceType
        from ghidra.util.exception import DuplicateNameException
        self.program = program
        self.monitor = monitor
        self.AddressSet = AddressSet
        self.USER = SourceType.USER_DEFINED
        self.DuplicateNameException = DuplicateNameException
        self.functions = program.getFunctionManager()
        self.listing = program.getListing()
        self.memory = program.getMemory()
        self.space = program.getAddressFactory().getDefaultAddressSpace()
        try:
            from ghidra.program.model.listing import CommentType
            self.plate = CommentType.PLATE
        except ImportError:
            from ghidra.program.model.listing import CodeUnit
            self.plate = CodeUnit.PLATE_COMMENT
        language = str(program.getLanguageID())
        if not language.startswith("x86:LE:32:"):
            raise ToolError("REFUSED: the program's language is not 32-bit x86 (little endian), which the executable "
                            "is. Import BEA.exe again as Portable Executable with the x86 32-bit language.")
        if program.getImageBase().getOffset() != IMAGE_BASE:
            raise ToolError("REFUSED: the program's image base is not the executable's own, which the tables' "
                            "addresses are written for. Import BEA.exe again with its default base address.")

    def sha256(self):
        return self.program.getExecutableSHA256()

    def check_cancelled(self):
        self.monitor.checkCancelled()

    def addr(self, address):
        return self.space.getAddress(address)

    def in_image(self, address):
        try:
            return self.memory.contains(self.addr(address))
        except Exception:       # an address outside the address space
            return False

    def function_at(self, address):
        return self.functions.getFunctionAt(self.addr(address))

    def name_of(self, function):
        return function.getName()

    def ensure_code(self, address, size):
        """Disassemble the entry if no instruction is there yet. True when it did."""
        start = self.addr(address)
        if self.listing.getInstructionAt(start) is not None:
            return False
        from ghidra.app.cmd.disassemble import DisassembleCommand
        command = DisassembleCommand(self.AddressSet(start, start), self.AddressSet(start, self.addr(extent_end(address, size))), True)
        return bool(command.applyTo(self.program, self.monitor))

    def create_function(self, address, size, name):
        body = self.AddressSet(self.addr(address), self.addr(extent_end(address, size)))
        try:
            return self.functions.createFunction(name, self.addr(address), body, self.USER)
        except self.DuplicateNameException as e:
            raise DuplicateName(str(e))
        except Exception as e:      # Ghidra's InvalidInputException, OverlappingFunctionException, ...
            raise AdapterError(str(e))

    def set_name(self, function, name):
        try:
            function.setName(name, self.USER)
        except self.DuplicateNameException as e:
            raise DuplicateName(str(e))
        except Exception as e:
            raise AdapterError(str(e))

    def extent_is(self, function, address, size):
        body = function.getBody()
        return (body.getNumAddressRanges() == 1 and body.getMinAddress().equals(self.addr(address)) and
                body.getMaxAddress().equals(self.addr(extent_end(address, size))))

    def set_extent(self, function, address, size):
        try:
            function.setBody(self.AddressSet(self.addr(address), self.addr(extent_end(address, size))))
        except Exception as e:      # OverlappingFunctionException: another function holds part of the range
            raise AdapterError(str(e))

    def plate_at(self, address):
        return self.listing.getComment(self.plate, self.addr(address))

    def set_plate(self, address, text):
        self.listing.setComment(self.addr(address), self.plate, text)


def clone_candidates(arguments, source_dir, environ):
    """Where to look for the clone, in order: the argument, the environment, the clone this file sits in."""
    found = []
    path = parse_arguments(arguments)[0]
    if path:
        found.append(path)
    found.append(environ.get("BEA_DECOMP_DIR"))
    if source_dir:
        found.append(os.path.dirname(os.path.dirname(source_dir)))
    return found


def run_in_ghidra(program, monitor, arguments, source_dir, headless, ask_directory, environ=None):
    if program is None:
        raise ToolError("No program is open: import BEA.exe and open it (headless: use -process or -import with "
                        "-postScript).")
    environ = os.environ if environ is None else environ
    path, check_only = parse_arguments(arguments)
    check_program_hash(program.getExecutableSHA256())
    gp = GhidraProgram(program, monitor)
    config_dir = None
    explicit = path or environ.get("BEA_DECOMP_DIR")
    if explicit:
        config_dir = config_folder_of(explicit)
        if config_dir is None:
            raise ToolError("The folder you gave (%s, from %s) does not hold functions.tsv and "
                            "function-corrections.tsv, directly or in a config/ folder. Give the decompilation "
                            "clone's root or its config/ folder." % (explicit, "the script argument" if path
                                                                    else "BEA_DECOMP_DIR"))
    else:
        config_dir = locate_config(clone_candidates(arguments, source_dir, environ))
        if config_dir is None and not headless:
            picked = ask_directory("Select the onslaught-decomp clone (the folder holding config/ and src/)", "Select")
            if picked:
                config_dir = config_folder_of(str(picked))
    if config_dir is None:
        raise ToolError("Cannot find the decompilation's config/ folder (config/functions.tsv). Give the clone's path "
                        "as the first script argument or in BEA_DECOMP_DIR.")
    write = not check_only
    src_dir = os.path.join(os.path.dirname(config_dir), "src")
    print("ApplyOnslaughtNames: tables from %s" % config_dir)
    if not os.path.isdir(src_dir):
        print("ApplyOnslaughtNames: no src/ folder beside config/, so no plate comments will be added")
    summary = run(gp, config_dir, src_dir, write)
    for line in summary_lines(summary, write):
        print(line)
    return summary


def _ghidra_entry():
    """Runs when Ghidra executes this file as a script (its globals are defined); does nothing when imported."""
    try:
        program = currentProgram            # noqa: F821
    except NameError:
        return
    try:
        source_dir = str(getSourceFile().getParentFile().getAbsolutePath())     # noqa: F821
    except Exception:
        source_dir = None
        if globals().get("__file__"):
            source_dir = os.path.dirname(os.path.abspath(globals()["__file__"]))
    try:
        run_in_ghidra(program, monitor, [str(a) for a in getScriptArgs()], source_dir,      # noqa: F821
                      isRunningHeadless(), askDirectory)                                    # noqa: F821
    except ToolError as e:
        print("ApplyOnslaughtNames: %s" % e)
        raise


_ghidra_entry()
