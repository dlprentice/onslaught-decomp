# Configuration

Status: active reference
Last updated: 2026-10-22
Summary: what each file in this folder pins or lists, where it came from, and which tools read it.

| File | What it holds |
| --- | --- |
| `flags.txt`, `file-flags.txt`, `no-pch.txt` | the compiler flags retail used, the files that take other flags, and the files that cannot use the precompiled header (with the reason) |
| `toolchain.sha256`, `vc6-include.sha256` | the SHA-256 of each Visual C++ 6.0 SP5 binary the tools run, and of the manifest of its `VC98/Include` tree |
| `dx9sdk-include.sha256`, `dx9samples-include.sha256` | the DirectX 9.0 SDK's `Include` tree (a manifest digest) and its sample framework's headers (one digest per file) |
| `game-data.sha256` | the two mission-script files of the game folder that the build compiles in |
| `functions.tsv`, `function-corrections.tsv` | the project's function table (address, size, name) and each correction made to its extents, with its evidence |
| `objects.tsv` | retail's objects: the address range of each source's functions and where its static initializers start |
| `classes.tsv` | retail's classes and their virtual tables, as the check compares them |
| `object-patches.tsv` | the one build concession: bytes written into a compiled object after compiling |
| `link-objects.txt`, `link-library-order.txt`, `link-thunks.txt` | retail's link order of objects and library members, and its import thunks |
| `link-inputs.sha256`, `link-sources.sha256` | the link's library inputs, each pinned (the toolchain's, and the further ones under `BEA_LAB`, among them NVIDIA's prebuilt NvTriStrip library), and the third-party sources it would compile (none at present) |

## The function table

`functions.tsv` is the project's table of retail's functions: one row per function of the game's code, of the import
thunks and of the compiler's unwind funclets. Its columns are:

- **address** and **bytes**: measured from the retail executable. The check holds them to the bytes: every matched
  function's compiled size equals its row, and `function-corrections.tsv` records, with its evidence, each extent the
  executable showed wrong, each block that is not a function and each function the table lacked.
- **name**: from the decompilation, which is the naming authority. A game function is named by the symbol its source
  compiles to, in the table's `Class__Method` form (`Class__ctor`, `Class__dtor`, `Class__scalar_deleting_dtor` for
  constructors, destructors and deleting destructors; `NAME__init` and `NAME__exit` for the compiler-generated
  initializer and exit functions, named by the `init:` and `exit:` annotations that place them). An import thunk is
  named by the import it jumps through, read from the executable's import table; an unwind funclet by its address
  (`Unwind@ADDRESS`).

The tools key on the addresses: the check counts and sizes retail's functions from the table, and the names are what
the score, `diff`, `dis` and `equiv.py` print.

## Files named here that this tree leaves out

`link-objects.txt` describes retail's link, so it names all five sources this tree does not carry (`wavread.cpp`,
`dxutil.cpp`, `d3dutil.cpp`, `DXFont.cpp`, `splinebasis.c`: the top-level README's "What is left out"), each under a
comment line saying so. `objects.tsv` has a row only for an object whose code names its own source file (a `__FILE__`
string, which is how `tools/objmap.py` finds it), so it lists two of them, `wavread.cpp` and `DXFont.cpp`, each with a
`note` saying so. The check skips a source that is not present, and its functions are not counted as matched; the link needs
those objects and cannot run from this tree alone.
