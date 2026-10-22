# Toolchain and flags

Status: reference, exported from the working repository's notes
Last updated: 2026-10-22
Summary: The compiler, flags and inputs the retail build used, and how each was established.

- Compiler: Visual C++ 6.0 SP5 Professional, the retail build exactly: CL 12.00.8804 driving C1 12.00.8867,
  C1XX 12.00.8964 and C2 12.00.8966. Compiled objects stamp `@comp.id` 0x000b2306 (build 8966), as the retail Rich
  header records for the game's 464 C++ and 3 C objects. SP5 installs that `c2.dll` from `msvcep.dll`
  (`sp598ent.inf`). Linker 6.00.8447, as retail.
- Flags: `/O2 /Ob2 /GX /MT /QIfist /GR` (`config/flags.txt`); `/QIfist` because retail converts float to int with an
  inline `fistp` rather than `__ftol` (CActor::HandleEvent, `00401ac4`). The one exception is cframetimer.obj, built without it
  (`config/file-flags.txt`): CFrameTimer::Start calls `__ftol` (`0042369f`), the only game-code call. `/O2` implies `/Gy`, so every function is its own
  NOP-padded COMDAT section; `/Ob2` is required (the retail code inlines non-inline member functions).
  `/GR` because retail carries RTTI: the dword before each virtual table points to its complete object locator, which
  names the class's type descriptor (CActor: table `005d844c`, locator `0060c288`, type descriptor `.?AVCActor@@` at
  `00622c48`). It changes no code: against the same source without it, the full check keeps every match it had then, with identical status
  lines, and across all 327 objects only EH label names, each table's leading locator pointer and the `??_R` records
  differ. `check_vtables` reads the slots after the locator pointer and checks that pointer against retail's dword
  before the table (889 tables match, as before; 721 locators placed, none conflicting).
- Inputs: `check_toolchain()` pins the six tool binaries and both complete include trees, including
  extensionless VC6 headers. The VC6 tree's 993 files (25,438,712 bytes) were independently checked file by file before adding `config/vc6-include.sha256`.
  Authored fixtures refuse changed, missing and added files in either include tree. The link's library
  inputs are pinned in `config/link-inputs.sha256` (path and SHA-256, in command-line order, the import
  libraries in retail's import-descriptor order); `tools/link.py` refuses to link if one differs. The
  retail-derived ones (import libraries made from the game's DLLs) stay in the untracked inputs folder.
  `config/link-sources.sha256` pins third-party sources the link compiles; it lists none at present,
  because NVIDIA's NvTriStrip links as its prebuilt library (`config/link-inputs.sha256`). `linklib/`
  also holds the link's provisional, link-only pieces, labelled as such: definitions whose owner or layout is open,
  and weak-external aliases for second names the source still uses. They let the linked executable run and are
  never part of the score.
  `config/link-library-order.txt` lists the library members in retail's `.text` order, each found in retail by its
  code with the relocation fields wildcarded: a first LIBCMT block from `0055d6a0`, NvTriStrip and its STL code from
  `0056eb50`, d3dx9, DxErr9, then the LIBCMT members only D3DX and DxErr9 need, from `005d04ec`. `tools/link.py`
  links those members as objects in that order (312 of 313 in retail order, against 272 with `--no-lib-order`, when
  the linker pulls them).
- Build folder: `C:\dev\ONSLAUGHT2\`, from the retail `__FILE__` strings; the Wine prefix maps it onto `src/`.

The matching compiler core is not a recovered original project. Original project/PCH settings, the full
link/resource command and initialized-data reconstruction remain open. `src/common.h` and other missing
game headers are reconstructed; `src/stdafx.h` is empty. The SP5 compiler DLLs were installed over the Visual C++ 6.0 header and library tree.
Matching function bodies supports this configuration without proving that entire installation equals
the original developer's. Missing source/header/translation-unit context is a stronger current lead for
shared inlining discrepancies than another indiscriminate compiler-version or source-permutation sweep.

A bounded September 30 PCH experiment made `common.h` with `/Yc` in Sphere.cpp and used it with `/Yu` in Sphere.cpp, Geometry.cpp and console.cpp. All 84 exact controls survive; the three selected unmatched bodies are unchanged. The two apparent changed functions have identical instruction bytes and only renumbered local exception labels; unused `operator new` emission also changes. This specific PCH configuration does not explain the target mismatches, and no production flag is changed. Other original header contents or PCH boundaries remain unknown.
