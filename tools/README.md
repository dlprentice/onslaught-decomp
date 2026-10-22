# Matching tools

Status: active reference
Last updated: 2026-10-22
Summary: what each tool in this folder is for, what it reads and writes, and its limits.

Every tool reads its inputs from the environment variables in the top-level README ("Reproducing the match") and
writes only under this checkout's ignored `build/`, `src/data/` and `local-data/` folders, the Wine prefix, and the
system's temporary folder (`BEA_TMP` for `icfsim.py`). `equiv.py` also reads `BEA_MAIN` and `BEA_NAME_TABLE` (see the
top-level README). Each script's docstring
gives its full usage; each `*_tests.py` is its unit tests (`python3 -m unittest tools.decomp_tests`, for example).

## The match

    python3 tools/decomp.py check [src/File.cpp ...] [-v]   # compile and compare
    python3 tools/decomp.py diff 0x004a2a20                 # side-by-side disassembly against retail
    python3 tools/decomp.py dis 0x004a2a20                  # retail disassembly with callee names and import slots
    python3 tools/decomp.py score                           # full check; rewrites docs/SCORE.md

- `decomp.py`: compiles each source with the pinned Visual C++ 6 under Wine and compares every annotated function's
  COMDAT section with the retail bytes at its address; its docstring states the matching rules. `binfmt.py` reads the
  COFF objects and the PE image.
- `equiv.py ADDRESS`: a bounded differential test of one function in an emulator (needs Unicorn,
  `requirements.txt`). Both bodies run at the retail address; exit 0/1/2 = sampled agreement, difference,
  inconclusive. It is a falsifier, not an equivalence proof: unobserved branches, faulting runs and unresolved
  dependencies cannot pass, and its call boundaries are a stub model.
- `witness_scan.py`: header-count witnesses, functions whose bytes depend on how many declarations precede them in
  their translation unit, and the window in which each still matches.

## The link

    python3 tools/link.py && python3 tools/linkcmp.py local-data/link/BEA.exe

- `link.py`: links the compiled objects into a candidate `BEA.exe` with the pinned linker, in retail's object and
  library-member order (`config/link-objects.txt`, `config/link-library-order.txt`); refuses a changed input
  (`config/link-inputs.sha256`, under `BEA_LAB`).
- `linkcmp.py`: compares a linked executable with retail, one number per stage (header, sections, symbols, imports,
  resources).
- Linker models, each checked against the real linker: `icfsim.py` (identical-COMDAT folding and its survivors),
  `iatsim.py` (the import address table's order), `bsscreate.py` (an object's `.bss` layout from symbol creation
  order), `rttiorder.py` (the order of RTTI locators), `rtti.py` (the classes retail's RTTI names).

## The whole executable

- `inventory.py`: charges every byte where a linked executable differs from retail to a root cause, and leads with
  `.text` size against retail.
- `datacontent.py`: compares every initialised data symbol the matched code reaches with retail, value for value.
- `dataorder.py`, `placemap.py`, `objmap.py`, `alignedeq.py`, `constowner.py`: where objects, functions, globals and
  float constants sit against retail, and how much code is equal once each function is compared at its own address.

## The function table

`config/functions.tsv` is the project's function table: addresses and sizes measured from the retail executable,
names from the decompilation ([config/README.md](../config/README.md)). `config/function-corrections.tsv` records each
correction to its extents with its evidence: a wrong extent, a block that is not a function, a function the table
lacked.
