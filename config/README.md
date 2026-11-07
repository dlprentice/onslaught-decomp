# Configuration

Status: active reference
Last updated: 2026-11-06
Summary: what each file in this folder pins or lists, where it came from, and which tools read it.

| File | What it holds |
| --- | --- |
| `flags.txt`, `file-flags.txt`, `no-pch.txt` | the compiler flags retail used, the files that take other flags, and the files that cannot use the precompiled header (with the reason) |
| `toolchain.sha256`, `vc6-include.sha256` | the SHA-256 of each Visual C++ 6.0 SP5 binary the tools run, and of the manifest of its `VC98/Include` tree |
| `dx9sdk-include.sha256`, `dx9samples-include.sha256` | the DirectX 9.0 SDK's `Include` tree (a manifest digest) and its sample framework's headers (one digest per file) |
| `game-data.sha256` | the two mission-script files of the game folder that the build compiles in |
| `functions.tsv`, `function-corrections.tsv` | the project's function table (address, bytes, name) and each correction made to it (an extent, an added function or a removed block), with its evidence |
| `objects.tsv` | retail's objects: the address range of each source's functions and where its static initializers start |
| `classes.tsv` | retail's classes and their virtual tables: one row per table the RTTI scan finds (`tools/rtti.py`), 729 rows for 656 classes. The check compares compiled tables with the 724 rows that have slots (the other five are not used), and it reports one line per compiled table, so its count (888 in `docs/check/check-summary.txt`) is not a row count |
| `object-patches.tsv` | the one build concession: bytes written into a compiled object after compiling |
| `link-objects.txt`, `link-library-order.txt`, `link-thunks.txt` | retail's link order of objects and library members, and its import thunks |
| `link-inputs.sha256`, `link-sources.sha256` | the link's library inputs, each pinned (the toolchain's, and the further ones under `BEA_LAB`, among them NVIDIA's prebuilt NvTriStrip library), and the third-party sources it would compile (none at present) |

## The function table

`functions.tsv` is the project's table of retail's functions: one row for each game function the table records
(including the 33 that the left-out sample files define), each import thunk and each compiler-generated unwind funclet,
plus one block row that `function-corrections.tsv` removes as not a function. `function-corrections.tsv` adds the 16 game
functions the table lacks. Its columns are:

- **address** and **bytes**: measured from the retail executable. `function-corrections.tsv` applies on top of this
  table, and the check uses the corrected extents. That file records, with its evidence, each extent the executable
  showed wrong (this table keeps the uncorrected value), each block that is not a function, each function the table
  lacked, and one row that confirms an extent already right (`TEXTURE_ZERO__init`). A matched function's compiled
  section must be at least its extent, and its bytes must agree with the executable apart from relocation fields.
- **name**: from the decompilation, which is the naming authority. A game function is named by the symbol its source
  compiles to. A class member takes the table's `Class__Method` form: `Class__ctor`, `Class__dtor` and
  `Class__scalar_deleting_dtor` for constructors, destructors and deleting destructors, and `Class__vector_deleting_dtor`
  for array (vector) deleting destructors. `NAME__init` and `NAME__exit` are the compiler-generated initializer and exit
  functions, named by the `init:` and `exit:` annotations that place them. `N__initorder` names a lone-`ret` initializer that
  `initorder:N` places, and `NAME__initbody` names the body that builds an aggregate array's dynamic initializer
  (`initbody:NAME`; see [matching-techniques.md](../notes/matching-techniques.md) and
  [compiler-findings.md](../notes/compiler-findings.md)).
  A free function keeps its own symbol, such as `AngleDifference`. An import thunk is named by the import it jumps
  through, read from the executable's import table. An unwind funclet is named by its address (`Unwind@ADDRESS`), except
  six that carry a function's name with an `_Unwind` or `_unwind` suffix (for example `CFastVB__Create__Unwind`); for
  three of those six, the function whose name it carries has no row in this table.

The tools key on the addresses: the check counts and sizes retail's functions from the table, and the names are what
the score, `diff`, `dis` and `equiv.py` print.

## Files named here that this tree leaves out

`link-objects.txt` describes retail's link, so it names all five sources this tree does not carry (`wavread.cpp`,
`dxutil.cpp`, `d3dutil.cpp`, `DXFont.cpp`, `splinebasis.c`: the top-level README's "What is left out"), each under a
comment line saying so. `objects.tsv` has a row only for an object whose code names its own source file (a `__FILE__`
string, which is how `tools/objmap.py` finds it), so it lists two of them, `wavread.cpp` and `DXFont.cpp`, each with a
`note` saying so. The check skips a source that is not present, and its functions are not counted as matched; the link needs
those objects and cannot run from this tree alone.
